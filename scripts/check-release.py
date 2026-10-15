#!/usr/bin/env python3
"""Read-only release scope/hash/pattern checks; never authorizes publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile

MAX_BYTES = 2 * 1024 * 1024
PATTERNS = {
    'private_path': re.compile(r'/(?:Users|home)/[^\s`"<>]+'),
    'internal_host': re.compile(r'https?://[^\s/"<>]+\.(?:internal|corp|lan)(?=[:/\s"<>]|$)', re.I),
    'private_ip': re.compile(r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'),
    'secret_pattern': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}'),
}


def valid_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and all(x not in ('', '.', '..', '.git') for x in value.split('/'))


def inspect(root, approved, terms):
    findings, hashes, present = [], {}, set()
    history = False

    def finding(path, kind, line=None):
        item = {'path': path, 'category': kind}
        if line is not None:
            item['line'] = line
        findings.append(item)

    def walk(directory):
        nonlocal history
        for p in sorted(directory.iterdir()):
            rel = p.relative_to(root).as_posix()
            mode = p.lstat().st_mode
            if stat.S_ISLNK(mode):
                present.add(rel)
                finding(rel, 'symlink_not_followed')
            elif p.name == '.git':
                if directory == root and stat.S_ISDIR(mode):
                    history = True
                else:
                    finding(rel, 'git_metadata_requires_review')
            elif stat.S_ISDIR(mode):
                walk(p)
            elif stat.S_ISREG(mode):
                present.add(rel)
                if rel not in approved:
                    finding(rel, 'unapproved_file')
                    continue  # Do not read files outside the approved scope.
                if p.stat().st_size > MAX_BYTES:
                    finding(rel, 'oversize_not_scanned')
                    continue
                data = p.read_bytes()
                hashes[rel] = hashlib.sha256(data).hexdigest()
                try:
                    text = data.decode('utf-8')
                    if '\x00' in text:
                        raise UnicodeError()
                except UnicodeError:
                    finding(rel, 'binary_not_scanned')
                    continue
                if p.name in ('auth.json', 'credentials.json', '.env'):
                    finding(rel, 'sensitive_filename')
                for number, line in enumerate(text.splitlines(), 1):
                    for kind, pattern in PATTERNS.items():
                        if pattern.search(line):
                            finding(rel, kind, number)
                    if any(term.casefold() in line.casefold() for term in terms):
                        finding(rel, 'local_sensitive_term', number)
            else:
                present.add(rel)
                finding(rel, 'special_file_not_read')
    walk(root)
    for rel in sorted(approved - present):
        finding(rel, 'missing_file')
    return findings, hashes, history


def scan_secrets(root, history):
    tool = shutil.which('gitleaks')
    if not tool:
        return 'UNAVAILABLE', []
    findings = []
    # Do not inherit settings/baselines capable of suppressing the vendor rules.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GITLEAKS_')}
    with tempfile.TemporaryDirectory(prefix='skill-secret-scan-') as td:
        temp = Path(td)
        config = temp / 'rules.toml'
        config.write_text('[extend]\nuseDefault = true\n')
        modes = ['dir', 'git'] if history else ['dir']
        for mode in modes:
            report = temp / (mode + '.json')
            cmd = [tool, mode, str(root), '--redact=100', '--no-banner',
                   '--ignore-gitleaks-allow', '--gitleaks-ignore-path', str(temp / 'no-ignore'),
                   '--config', str(config), '--report-format', 'json', '--report-path', str(report)]
            try:
                run = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, timeout=120)
            except (OSError, subprocess.TimeoutExpired):
                return 'ERROR', findings
            if run.returncode not in (0, 1):
                return 'ERROR', findings
            if run.returncode == 1:
                findings.append({'path': '.', 'category': 'gitleaks_' + mode + '_findings'})
    return ('FAIL' if findings else 'PASS'), findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--manifest', required=True, type=Path,
                        help='JSON array of explicitly approved relative file paths, stored outside root')
    parser.add_argument('--terms-file', type=Path, help='Local-only sensitive terms, one per line')
    parser.add_argument('--gitleaks', action='store_true')
    args = parser.parse_args()
    try:
        if args.root.is_symlink() or not args.root.is_dir():
            raise ValueError()
        root = args.root.resolve()
        for p in [args.manifest, args.terms_file]:
            if p and p.resolve().is_relative_to(root):
                raise ValueError()
        raw = json.loads(args.manifest.read_text())
        if not isinstance(raw, list) or not raw or not all(valid_relative(x) for x in raw):
            raise ValueError()
        if len(raw) != len(set(raw)):
            raise ValueError()
        terms = []
        if args.terms_file:
            terms = [x.strip() for x in args.terms_file.read_text().splitlines()
                     if x.strip() and not x.lstrip().startswith('#')]
        findings, hashes, history = inspect(root, set(raw), terms)
        secret_status = 'NOT_RUN'
        if args.gitleaks:
            # Refuse to scan unapproved/linked content via a second tool.
            if findings:
                secret_status = 'BLOCKED_BY_LOCAL_CHECKS'
            else:
                secret_status, secret_findings = scan_secrets(root, history)
                findings.extend(secret_findings)
        output = {
            'local_checks': 'FAIL' if findings else 'PASS',
            'secret_scanner': secret_status,
            'git_history': ('included_in_secret_scan' if history and secret_status == 'PASS'
                            else 'NOT_VERIFIED' if history else 'not_present'),
            'company_semantics': 'MANUAL_REVIEW_REQUIRED',
            'publication_readiness': 'NOT_DETERMINED',
            'findings': findings,
            'sha256': hashes,
        }
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 1 if findings or (args.gitleaks and secret_status != 'PASS') else 0
    except (OSError, UnicodeError, ValueError, RecursionError):
        print(json.dumps({'local_checks': 'ERROR', 'publication_readiness': 'NOT_DETERMINED',
                          'error': 'Invalid inputs or unreadable scope; no content echoed.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
