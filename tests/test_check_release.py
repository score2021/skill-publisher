"""Synthetic regression tests; no external service or real secret required."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-release.py'


class ReleaseChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='publisher-check-test-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'candidate'
        self.root.mkdir()
        (self.root / 'SKILL.md').write_text('A synthetic public workflow.\n')
        self.manifest = self.base / 'approved.json'
        self.manifest.write_text(json.dumps(['SKILL.md']))

    def run_check(self, *args, env=None):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.root),
                            '--manifest', str(self.manifest), *args],
                           capture_output=True, text=True, env=env)
        return p.returncode, json.loads(p.stdout)

    def categories(self, report):
        return {x['category'] for x in report.get('findings', [])}

    def test_clean_scope_never_claims_publication_or_full_scan(self):
        code, out = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(out['local_checks'], 'PASS')
        self.assertEqual(out['secret_scanner'], 'NOT_RUN')
        self.assertEqual(out['company_semantics'], 'MANUAL_REVIEW_REQUIRED')
        self.assertEqual(out['publication_readiness'], 'NOT_DETERMINED')
        self.assertEqual(len(out['sha256']['SKILL.md']), 64)

    def test_extra_file_is_blocked_without_reading_its_value(self):
        marker = 'UNAPPROVED_VALUE_SHOULD_NOT_APPEAR'
        (self.root / 'private.txt').write_text(marker)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('unapproved_file', self.categories(out))
        self.assertNotIn(marker, json.dumps(out))
        self.assertNotIn('private.txt', out['sha256'])

    def test_missing_file(self):
        (self.root / 'SKILL.md').unlink()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('missing_file', self.categories(out))

    def test_symlink_never_reads_or_changes_target(self):
        target = self.base / 'outside.txt'
        target.write_text('untouched')
        (self.root / 'SKILL.md').unlink()
        (self.root / 'SKILL.md').symlink_to(target)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('symlink_not_followed', self.categories(out))
        self.assertEqual(target.read_text(), 'untouched')
        self.assertEqual(out['sha256'], {})

    def test_broken_link(self):
        (self.root / 'SKILL.md').unlink()
        (self.root / 'SKILL.md').symlink_to(self.base / 'absent')
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('symlink_not_followed', self.categories(out))

    def test_nested_git_rejected(self):
        (self.root / 'nested/.git').mkdir(parents=True)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('git_metadata_requires_review', self.categories(out))

    def test_root_history_is_not_silently_verified(self):
        (self.root / '.git').mkdir()
        code, out = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(out['git_history'], 'NOT_VERIFIED')

    def test_binary_and_large_inputs_are_unverified(self):
        for data, category in [(b'\x00\x01', 'binary_not_scanned'),
                               (b'x' * (2 * 1024 * 1024 + 1), 'oversize_not_scanned')]:
            with self.subTest(category=category):
                (self.root / 'SKILL.md').write_bytes(data)
                code, out = self.run_check()
                self.assertEqual(code, 1)
                self.assertIn(category, self.categories(out))

    def test_bad_manifests_fail_closed(self):
        for raw in [['../escape'], ['/absolute'], ['SKILL.md', 'SKILL.md'], [],
                    ['C:' + '/file'], ['folder\\file'], {'files': []}, [12]]:
            with self.subTest(raw=raw):
                self.manifest.write_text(json.dumps(raw))
                code, out = self.run_check()
                self.assertEqual(code, 2)
                self.assertEqual(out['local_checks'], 'ERROR')

    def test_manifest_inside_release_rejected(self):
        self.manifest = self.root / 'approved.json'
        self.manifest.write_text('["SKILL.md"]')
        code, out = self.run_check()
        self.assertEqual(code, 2)

    def test_secret_and_terms_redacted(self):
        fake_secret = 'gh' + 'p_' + 'A' * 32
        fake_term = 'Example' + 'RestrictedPhrase'
        (self.root / 'SKILL.md').write_text(fake_secret + '\n' + fake_term + '\n')
        terms = self.base / 'local-terms.txt'
        terms.write_text(fake_term)
        code, out = self.run_check('--terms-file', str(terms))
        self.assertEqual(code, 1)
        self.assertTrue({'secret_pattern', 'local_sensitive_term'} <= self.categories(out))
        self.assertNotIn(fake_secret, json.dumps(out))
        self.assertNotIn(fake_term, json.dumps(out))
        self.assertTrue(all('line' in f for f in out['findings']))

    def test_private_paths_hosts_and_ips(self):
        text = '/' + 'home' + '/demo/private.txt\n'
        text += 'https://' + 'service' + '.internal/api\n'
        text += '.'.join(['192', '168', '1', '2'])
        (self.root / 'SKILL.md').write_text(text)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertTrue({'private_path', 'internal_host', 'private_ip'} <= self.categories(out))

    def test_missing_gitleaks_not_pass(self):
        env = dict(os.environ, PATH=str(self.base / 'empty-bin'))
        code, out = self.run_check('--gitleaks', env=env)
        self.assertEqual(code, 1)
        self.assertEqual(out['secret_scanner'], 'UNAVAILABLE')

    def test_secret_scan_blocked_for_unapproved_content(self):
        (self.root / 'extra').write_text('unapproved')
        code, out = self.run_check('--gitleaks')
        self.assertEqual(code, 1)
        self.assertEqual(out['secret_scanner'], 'BLOCKED_BY_LOCAL_CHECKS')

    def test_gitleaks_success_failure_error_are_distinct(self):
        tool_dir = self.base / 'bin'
        tool_dir.mkdir()
        tool = tool_dir / 'gitleaks'
        env = dict(os.environ, PATH=str(tool_dir))
        for result, expected in [(0, 'PASS'), (1, 'FAIL'), (2, 'ERROR')]:
            with self.subTest(result=result):
                tool.write_text('#!/bin/sh\nexit ' + str(result) + '\n')
                tool.chmod(0o755)
                code, out = self.run_check('--gitleaks', env=env)
                self.assertEqual(out['secret_scanner'], expected)
                self.assertEqual(code, 0 if result == 0 else 1)


if __name__ == '__main__':
    unittest.main()
