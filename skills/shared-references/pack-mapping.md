# 本整合包的 skill 映射表（ARIS 原件引用 → 包内等价物）

ARIS 系原件中引用的以下 skill 未按原名收录，遇到引用时按此表替换：

| 原件引用 | 本包等价物 |
|---|---|
| `/research-lit`, `/comm-lit-review` | `literature-gap-mining`（检索引擎用 `paper-search`） |
| `/novelty-check` | `scoop-check` |
| `/idea-discovery`, `/idea-creator` | `idea-spark`（重型）或 `idea-mining`（轻量） |
| `/research-review` | 已收录 `research-review`；评审隔离遵守 `cross-model-review` 协议 |
| `/auto-review-loop`, `/auto-paper-improvement-loop` | 已收录原件；评审器后端按 `reviewer-adapter.md` 适配 |
| `/paper-write`, `/paper-plan` | `paper-writing`（Master-cai 写作法 + ccfa-structure 参考） |
| `/run-experiment`, `/experiment-queue`, `/monitor-experiment`, `/dse-loop` | 已收录原件（含脚本）；编排层仍用 `experiment-loop` + `night-loop` |
| `/experiment-bridge` | `experiment-loop` |
| `/experiment-plan` | `experiment-design` |
| `/check-gpu` | `monitor-experiment` |
| `/experiment-audit`, `/training-check` | `paper-verification` + `compare` / `debug` |
| `/research-pipeline`（ARIS 版） | 本包 `research-pipeline`（决策卡编排） |
| `/research-wiki` | 已收录 `research-wiki`；轻量场景用 `research_run/<slug>/state.md` |
| `/figure-spec`, `/paper-figure` | `data-visualization` + `paper-illustration` / `figure-description` |
| `/resubmit-pipeline` | `rebuttal-writing`（会议 rebuttal / 期刊 major revision 两模式，产物落 `stage7_rebuttal/`）+ 重跑阶段 6 自审；被拒转投按 `research-pipeline` 阶段 7 的转投路径处理 |
| `/phd-skills:debug` | `debug` |
| `/phd-skills:launch` | `launch` |
| `/phd-skills:compare` | `compare` |
| `/phd-skills:reproduce` | `reproduce` |

其余未列出的引用（如 `/schedule`、`/loop`、`/serverless-modal`、feishu/minimax 相关）为 ARIS 平台专属机制，
在本包环境中忽略即可，不影响所在 skill 的主流程。
