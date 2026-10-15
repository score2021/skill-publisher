# Skill Publisher · 从认可的会话流程到可验收的 Skill

面向希望把成功工作方法变成可复用工具的 PM、开发者、个人创作者与开源维护者的中文 Agent Skill。根据需求或可访问会话中用户认可的做法创建 skill，完成精简设计、README、本地安装与验收；用户明确要求后才执行 GitHub 发布及下载复验。

公开仓库：[score2021/skill-publisher](https://github.com/score2021/skill-publisher)。仓库名为 `skill-publisher`，技能名称与调用名为 `z-skill-publisher` / `$z-skill-publisher`。

## 适用场景

- “把刚才我认可的需求分析/文档审校/资料整理流程做成 skill。”
- 创建新 skill，或改进已有 skill 并验证行为。
- 为 skill 准备开源目录、许可证、安装说明和真实测试证据。
- 明确授权后，发布到指定账户与仓库，再从外部用户视角下载验收。

适合重复执行、具有明确输入输出的工作方法；单次任务无需强行封装。没有提供或无法访问的历史会话，不能自动推断为已读取。

## 六步工作流

| 步骤 | 主要产物或判断 |
| --- | --- |
| 1 提炼需求与认可经验 | 目标用户、输入输出、认可依据、候选经验、停止范围 |
| 2 编写与精简 | SKILL.md、按需参考、必要脚本；不复制整段聊天 |
| 3 整理独立目录 | README、许可证、.gitignore、必要资源及合成 eval |
| 4 本地验收 | 结构、脚本、真实加载及代表性任务结果 |
| 5 检查并发布 | 来源与公司信息检查、秘密扫描、明确范围和已授权的远端操作 |
| 6 下载复验与清理 | 全新远端下载、原样安装、实际任务、版本核对及临时文件清理 |

“只本地”完成本地部分后结束；“先方案”不写文件。六步不是六轮确认，已明确授权的工作连续完成。具体发布目标和权限必须来自本次请求，不能从 skill 文本或旧任务继承。

## 新建技能的 `z-` 前缀

**为什么未指定名称时默认以 `z-` 开头？** 这是本用户的个人技能命名约定：输入 `z-` 可缩小调用候选范围，方便查找自己创建的技能、区别官方/插件技能；连字符也符合 Agent Skills 标准，无需采用非标准下划线。该默认值不是官方强制要求。

用户未指定名称时，按用途生成 `z-<简短用途名>`；只提供基础名且未要求原样保留时也添加一次前缀。例如要求创建 `release-note-helper`，实际生成目录和名称为 `z-release-note-helper`，用 `$z-release-note-helper` 调用；输入已经是 `z-daily-notes` 时不再加前缀。

frontmatter name、目录、安装路径、README 调用示例，以及 UI display_name/default_prompt（存在时）保持一致；遇到同名文件或安装不覆盖。用户明确指定完整且符合标准的名称、要求原样保留时，尊重指定名称。默认规则不会自动迁移已有技能。

`z-` 符合 [Agent Skills 命名规范](https://agentskills.io/specification)：仅使用小写字母、数字与连字符，含前缀总长最多 64，不能有连续连字符、首尾不能是连字符，目录与 name 一致。旧式下划线输入规范化为单连字符后再去重前缀，不保留标准命名例外。格式校验通过仍需实际客户端行为验收；具体实测范围见下方。

## 生成 README 的“样例”要求

每个生成物的 README 都必须有“样例”一节，包含至少一个能直接复制的完整对话请求：实际调用名（默认 `$z-技能名`）、具体需求和必要的最小合成输入。不能只写“我的需求是 xxx”或引用用户没有的文件。样例后给出预期结果、是否写文件和必要前置条件，让第一次使用的人不用自己构思用法。

## 如何提炼你认可的流程

把用户明确保留的做法、工具执行成功但未评价的做法、用户否定的做法和一次性绕路分开。明确认可只覆盖所指内容；最新纠正优先。不把“曾用 Python”“临时命令成功”变成所有项目的默认要求。

先使用当前可见上下文；跨会话请提供脱敏摘要或指定可访问记录。发布目录只保留通用方法和合成例子，不包含真实会话或公司项目代码。它不能保证历史知识产权归属，扫描也不能证明完全没有敏感内容。

## 安装到本地 Codex

需要可用且已登录的 Codex；机械检查脚本需要 Python 3.10+，仅使用标准库。下面适用于 macOS/Linux 的 sh/bash/zsh；仅使用桌面端时也可完成同样的文件安装。

先从 GitHub 下载（需要 Git；目标目录已存在时请另选空目录）：

```sh
git clone https://github.com/score2021/skill-publisher.git z-skill-publisher
cd z-skill-publisher
```

显式指定下载目录 `z-skill-publisher`，使目录与技能名称一致。然后在该目录整块运行：

```sh
(
  set -eu
  test -f SKILL.md
  test -f LICENSE
  test -f agents/openai.yaml
  test -d references
  test -d scripts
  skill_dest="$HOME/.agents/skills/z-skill-publisher"
  if [ -e "$skill_dest" ] || [ -L "$skill_dest" ]; then
    printf '%s\n' "已存在 $skill_dest，请先核对原版本；本次未覆盖。" >&2
    exit 1
  fi
  mkdir -p "$skill_dest"
  cp SKILL.md LICENSE "$skill_dest/"
  cp -R agents references scripts "$skill_dest/"
  printf '%s\n' "已安装到 $skill_dest"
)
```

这会安装到 `~/.agents/skills/z-skill-publisher/`，所有本地项目共用。若原有安装在 `~/.codex/skills/z-skill-publisher/` 且发现目录是它的软链接，先检查实际位置，避免重复同名安装。更新前保留自定义内容；不要盲目覆盖偏好或手工修改。

Codex 下一轮可尝试使用；未刷新时重启，在 CLI 输入 `$` 或 `/skills` 查找。发现目录和软链接机制参见 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)。独立 skill 安装不会注册 `/z-skill-publisher` 自定义斜杠命令。

## 样例

CLI 在目标项目目录执行 `codex`，或在桌面端打开该项目，然后输入以下对话内容：

```text
$z-skill-publisher 创建一个把变更材料整理成发布说明的 skill，基础名 release-note-helper，面向互联网公司的 PM 和开发者。
我认可的流程：先写用户可感知变化，再写限制和需要采取的操作；没有证据的性能数据标为“未验证”；默认直接输出 Markdown，只有明确要求保存才写文件。
请在当前目录的 output/z-release-note-helper 完成本地编写，包含 README（含可直接复制的内联样例）、MIT LICENSE、.gitignore 和本地静态检查。
本次不要安装到真实用户目录、不要上传或发送；独立客户端验收留到后续步骤，本次不启动其他模型会话。
```

预期在指定目录得到可安装的 `z-release-note-helper` 及说明文档；会写入该目录，不会执行发布或修改用户的全局安装。需要对当前目录有写权限。
新会话请补充认可摘要，不要要求猜测不可见历史。只做设计：

```text
$z-skill-publisher 根据下面的需求和我认可的流程先给设计方案，不修改文件。
```

日后需要发布时，明确账户、仓库和可见性，例如：

```text
$z-skill-publisher 将指定的本地 skill 发布到我当前 GitHub 账户，
创建名为 <仓库名> 的公开仓库，上传前核对文件范围和公司信息，下载后再次验收。
```

这只是调用示例，不是本次或未来其他任务的发布授权。仓库未创建前不会提供虚构的下载地址。

最短提炼演示：在对话中说明“先列用户变化、再列限制”是你认可的，“临时使用某个脚本”只是工具成功记录，要求只给方案。预期会区分认可与候选经验，产出通用流程建议并停在写文件之前，而非强制使用该脚本。

## 检查工具与边界

先由用户/Agent 核对发布文件，再在目录外保存相对路径 JSON 数组。不要把自动枚举整个工作区当作已获准上传。

```sh
python3 scripts/check-release.py /path/to/release --manifest /path/to/approved-files.json
```

可加 `--terms-file /path/to/local-terms.txt`，词表留本地；可加 `--gitleaks` 使用现有本地 Gitleaks，检查目录及存在的根 Git 历史。不会自动安装扫描器或读取凭据。

基础检查检测清单差异、软链接、特殊文件、部分私人路径/内部地址/密钥模式、二进制及大文件，并输出哈希和脱敏类别。默认 `secret_scanner=NOT_RUN`；缺工具为 UNAVAILABLE，不能写成秘密审计通过。退出码 0 仅表示已执行的本地机械检查通过，`publication_readiness` 始终为 NOT_DETERMINED。公司代码/业务语义、许可来源及扫描盲区仍需人工判断。

测试只用合成资料，常规 eval 不创建真实公开仓库。真实发布后的复验须验证远端提交、副本、安装和行为，不只检查下载成功。清理只删除本轮记录的临时根，不触碰用户安装、原始认证或未知目录。

## 目录与渐进式披露

```text
z-skill-publisher/
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore
├── agents/openai.yaml
├── references/
│   ├── authoring.md
│   ├── readme.md
│   ├── testing.md
│   └── publishing.md
├── scripts/check-release.py
├── evals/
│   ├── evals.json
│   └── fixtures/
│       ├── approved-flow.md
│       └── change-notes.md
└── tests/test_check_release.py
```

主文件保留核心行为与导航，复杂细则命中再读；README 面向使用者，eval 留存可公开的合成回归材料，原始日志放临时目录。

## 设计参考

方法参考 [OpenAI skill-creator](https://github.com/openai/skills/tree/main/skills/.system/skill-creator)、[Anthropic skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator)、[Agent Skills 设计建议](https://agentskills.io/skill-creation/best-practices)与[评测指南](https://agentskills.io/skill-creation/evaluating-skills)。发布检查参考 [Open Source Launch Skill](https://github.com/OMARVII/open-source-launch-skill) 的定位与首次使用路径、[Gitleaks](https://github.com/gitleaks/gitleaks) 的秘密扫描能力。这里使用独立编写的工作指引，不捆绑这些项目源码或假设它们已安装。

## 运行本地回归

在发布目录中运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

这验证检查脚本的正反场景；Gitleaks 状态分支使用模拟工具，不能作为实际 Gitleaks 检出率的证据。`evals/evals.json` 定义真实客户端的行为回归任务，结果需实际执行和检查产物，不能只运行 unittest 就称技能整体通过。

## 验证范围

本地验收覆盖：15 项检查脚本回归、README 安装及重复安装保护、真实 Codex 名称发现与调用、从认可流程生成新技能、生成技能的实际任务、标准命名和元数据一致性。测试材料为合成资料，原始日志与隔离安装不随包发布。

发布流程还要求从 GitHub 全新下载、核对远端版本、原样安装并在干净会话执行任务。下载验收的结果与本地测试分别记录，不能只以下载成功作为可用证据。

实际 Gitleaks 秘密扫描未运行；单元测试中的扫描器状态分支使用模拟工具。基础模式扫描与来源复核不等于全量秘密审计或知识产权归属保证。其他客户端未实测，少量成功用例也不代表所有场景可靠。

## 许可证

[MIT](LICENSE)。
