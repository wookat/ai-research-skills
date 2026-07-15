# 按任务找 Skill（一页式路由表）

不知道用哪个 skill 时先查这张表。完整清单见 [SKILLS_CATALOG.md](SKILLS_CATALOG.md)；
全流程编排（决策卡 / autopilot / 状态机）见
[research-pipeline](../skills/research-pipeline/SKILL.md)。

## 我要……

| 任务 | 用哪个 skill（按顺序） |
|---|---|
| 从零开始一个课题（全流程） | `research-pipeline`（它会按阶段路由到下面所有 skill） |
| 做文献综述、找研究缺口 | `literature-gap-mining`（检索引擎用 `paper-search`）；系统综述用 `systematic-review`，定量汇总用 `meta-analysis` |
| 想创新点 / 产出候选 idea | 单点深挖用 `idea-spark`（脚本化重型）；一次要多个候选用 `idea-mining`（轻量） |
| 查撞车 / 查新（这个 idea 有没有人做过） | `scoop-check`（依赖 `paper-search`）；立项后持续监控用 `arxiv-radar` |
| 判断 idea 是真洞察还是缝合 | `idea-critic`（四检验 + 领域陷阱体检 + 审稿模拟） |
| 复现一篇论文 / baseline | `reproduce`；训练出问题用 `debug` |
| 设计实验 / 消融 | `experiment-design`；投稿级消融用 `ablation-planner` |
| 跑实验循环（假设→验证→迭代） | `experiment-loop`；无人值守夜跑用 `night-loop`；批量任务用 `experiment-queue` + `run-experiment` + `monitor-experiment`；参数探索用 `dse-loop`；长训练启动前用 `launch` |
| 对比两个 run / 公平对比 | `compare`；结果分析用 `analyze-results`；显著性检验用 `statistical-testing`（n<5 不给 p 值） |
| 数据集整理 | `dataset-curation`；时序分析方法用 `time-series-analysis` |
| 写论文 | `paper-writing`；图表用 `data-visualization`；插图用 `paper-illustration` / `mermaid-diagram` / `figure-description`；公式/证明用 `formula-derivation` / `proof-writer` / `proof-checker` |
| LaTeX 工程 | `latex-setup`（环境/模板）→ `latex-workflow`（写作/编译）→ `paper-compile`；Overleaf 用 `overleaf-sync` |
| 投稿前自审 | `reviewer-simulation` + `paper-verification` + `paper-claim-audit` + `citation-audit` + `kill-argument`；多轮自动改进用 `auto-paper-improvement-loop` / `auto-review-loop`（评审后端按 `shared-references/reviewer-adapter.md`） |
| 降 AI 味 / 过 AIGC 检测 | `deai-polish` |
| 写 rebuttal / 期刊 revision | `rebuttal-writing`（会议/期刊/转投三模式） |
| 把结论写成可辩护的 claim | `result-to-claim` + `claims-drafting` |
| 转硕士学位论文 | `thesis-convert`（需学校 LaTeX 模板）+ `deai-polish` |
| 申请专利 | `patent-pipeline`（编排 `invention-structuring` → `prior-art-search` → `patent-novelty-check` → `claims-drafting` → `specification-writing` → `patent-review` → `jurisdiction-format`） |
| 录用后开源 | `research-publishing` |
| 做海报 / 视频 / 博客宣传 | `paper2poster` / `paper2video` / `paper2reel` / `paper2blog` / `paper2assets`；HTML 单页海报用 `paper-poster-html`；幻灯/讲稿用 `paper-slides` / `paper-talk` / `slides-polish`；HTML 渲染用 `render-html` |
| 写基金申请书 | `grant-proposal` |
| 维护课题知识库 | `research-wiki`（helper：`tools/research_wiki.py`） |
| 跨模型评审 / 防自嗨 | `cross-model-review`（协议）+ `shared-references/reviewer-adapter.md`（后端选择） |

## 常用顺序（主线）

```
literature-gap-mining → idea-spark/idea-mining →（决策卡#1）→ scoop-check
→ idea-critic →（决策卡#2）→ experiment-loop →（决策卡#3）→ paper-writing
→ reviewer-simulation + kill-argument + citation-audit + paper-verification
→（决策卡#4）→ 投稿 → rebuttal-writing
```

时序预测课题启动时先读 `domains/time-series-forecasting.md`（数据集/协议/
baseline/陷阱/3447 篇论文热度统计）。
