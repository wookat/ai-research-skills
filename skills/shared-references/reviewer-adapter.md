# Reviewer Adapter（本整合包：评审后端适配层）

ARIS 系 skill（auto-review-loop / auto-paper-improvement-loop / kill-argument /
citation-audit / patent-review / proof-checker 等）在调用外部评审器
（`mcp__codex__codex` / `mcp__manual_review__review`）时，按下表自上而下选择
第一个可用后端，语义等价替换。**prompt 内容一字不改**，只换调用通道。

| 优先级 | 后端 | 检测方式 | 调用方式 |
|---|---|---|---|
| 1 | Codex MCP | 工具列表含 `mcp__codex__codex` | 按原文调用（threadId 语义原样保留） |
| 2 | Codex CLI | `command -v codex` | `codex exec --sandbox read-only "<prompt>"`；多轮续评用 `codex exec resume <session-id>` |
| 3 | Gemini CLI | `command -v gemini` | `gemini -p "<prompt>"`（无线程语义：每轮把此前评审记录文件路径附在 prompt 里） |
| 4 | 子智能体 / 子会话（四平台均可） | Claude Code = Task 子智能体；Cursor = 后台 agent；Codex = `codex exec` 子进程；Devin = child session | 派生一个**零上下文**子智能体/子会话，只喂被评审文件 + prompt，取其最终报告。这是四平台通用的 fresh-context 首选降级路径 |
| 5 | 新对话（人工中转） | 上述子智能体机制都不可用时 | 请用户在新窗口/新 chat 粘贴 prompt + 文件，把回复存为 `review-stage/round<N>_review.md` 后继续（即 ARIS "manual backend" 的通用化） |
| 6 | 同模型降级 | 以上皆不可用 | 同模型执行评审 prompt，但报告头部标注 `⚠ same-model self-review, scores may be inflated`，且结论不得作为决策卡的唯一依据 |

**关于后端 4（推荐）**：Claude Code / Cursor / Codex / Devin 网页版**都**能派生子智能体或子会话，因此"新鲜零上下文评审器"在四个平台都可自动实现，无需人工中转。子智能体优先用与主 agent **不同的模型**（真正跨模型）；即便同模型，只要是零上下文新实例，也已消除"同上下文自评刷分"的失效模式。仅当平台确实无法派生子智能体时才降到后端 5/6。

## 通道无关的硬规则（无论用哪个后端）

- **fresh-thread 边界不许破**：原文标注"NOT codex-reply / fresh thread"的调用，
  在任何后端都必须是零上下文新调用（cross-model-review 协议）。
- **续评（threadId 复用）的等价实现**：后端 2 用 resume；后端 3/5 靠把
  `review-stage/` 里的历史评审文件列为输入；后端 4 在同一子智能体/子会话内追问。
- 评审输入输出全部落盘到 `review-stage/`，与后端无关；换后端不改产物格式。
- REVIEWER_DIFFICULTY=nightmare（评审器直读仓库）仅后端 1/2/4 支持；其余降为 hard。

## 平台适配注记

- **Claude Code**：skill 放 `.claude/skills/`；评审器首选后端 1/2，否则后端 4（Task 子智能体，零上下文）。
- **Codex CLI**：skill 放 `.codex/skills/` 并在 AGENTS.md 引用；首选后端 1/2，否则后端 4（`codex exec` 子进程）。
- **Devin（网页版）**：skill 放 `.agents/skills/`；后端 4 首选（child session 天然零上下文、可跨模型）。
- **Cursor**：skill 内容放 `.cursor/rules/` 或项目文档引用；首选后端 2，否则后端 4（后台 agent）。
- 四平台都支持后端 4，所以"新鲜/跨模型评审"在哪个平台都能自动跑，人工中转（后端 5）只是最后兜底。
- SSH/GPU 相关 skill（experiment-queue / run-experiment / monitor-experiment）
  需要用户提供可 SSH 的 GPU 服务器；无远端时把命令降级到本机 shell 执行
  （screen/tmux 语义不变），Devin 上可直接用其虚拟机作为"本机"。

## 非评审类 MCP 的降级

- `mcp__tavily__*`、`mcp__claude_ai_Hugging_Face__*` 等检索类 MCP 缺失时，
  退化到本包 `paper-search` 脚本或 agent 自带 web 检索，并在产物中记录降级。
- `mcp__oracle__consult`、`mcp__gemini_review__review` 属于评审后端，按上表的
  fresh-thread 与降级规则处理，不按检索类 MCP 处理。
