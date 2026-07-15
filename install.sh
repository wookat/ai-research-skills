#!/usr/bin/env bash
# ai-research-skills 最小安装器。
#
# 作用：把本包根目录的绝对路径写入 ~/.aris/repo（全局指针文件），使
# shared-references/integration-contract.md §2 解析链的最后一层
# （$HOME/.aris/repo → $ARIS_REPO/tools/<helper>）在“全局拷贝安装”
# （如 cp -r skills/* ~/.claude/skills/）场景下也能解析到本包 tools/ 与 domains/。
#
# 用法：在本包根目录执行  bash install.sh
# 等价手动方案：export ARIS_REPO=<本包绝对路径>（或 AI_RESEARCH_SKILLS_HOME）。
set -eu

PACK_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$PACK_ROOT/tools" ] || [ ! -d "$PACK_ROOT/skills" ]; then
    echo "ERROR: $PACK_ROOT 下未找到 tools/ 与 skills/，请在 ai-research-skills 包根目录运行本脚本。" >&2
    exit 1
fi

mkdir -p "$HOME/.aris"
printf '%s\n' "$PACK_ROOT" > "$HOME/.aris/repo"
echo "OK: 已写入 $HOME/.aris/repo -> $PACK_ROOT"
echo "    helper 解析链（.aris/tools/ -> tools/ -> \$ARIS_REPO/tools/ -> ~/.aris/repo）现可在全局安装下解析本包 tools/。"
