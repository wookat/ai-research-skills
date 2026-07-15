# ai-research-skills — 全流程科研 Skill 包（整合版）

面向"人做决策、AI 做执行"的科研工作流，从选题到 CCF-A 论文再到学位论文。
**通用实证研究方法为核心，领域模块可插拔**——凡是走"文献→创新点→基线复现→消融→
顶会投稿"这套研究方法的方向都适用，尤其适合时序预测（time-series forecasting）
这类实证 ML 方向（已内置该领域模块，见 `domains/`）。

**整合而非重写**：直接收录各开源项目中最强的 skill 原件（含脚本、参考文件、
证据基础），统一命名与触发规则、消除冲突，用自研的编排层（research-pipeline +
决策卡机制）粘合成一条流水线。来源与修改范围见 [ATTRIBUTION.md](ATTRIBUTION.md)。
Claude Code / Codex / Devin（含网页版）/ Cursor 通用。

## 流水线总览

```
阶段0 文献与缺口挖掘  literature-gap-mining（检索引擎：paper-search※）
阶段1 创新点挖掘      idea-spark※（重型首选）/ idea-mining（轻量）→ 决策卡#1（人筛选）
阶段2 防撞车检查      scoop-check※
阶段3 洞察性评审      idea-critic                              → 决策卡#2（人拍板立项）
阶段4 实验循环        experiment-loop（子技能 reproduce/compare/debug/experiment-design※）
                                                               → 决策卡#3（人定夺结果）
阶段5 论文写作        paper-writing（Master-cai 原件 + CCF-A 结构参考）
阶段6 投稿前自审      reviewer-simulation                      → 决策卡#4（人决定投稿）
阶段7 Rebuttal        rebuttal-writing
阶段8 学位论文转化    thesis-convert + deai-polish
辅助：data-visualization（科研绘图）/ latex-workflow + latex-setup（LaTeX 工程）
      / paper-verification（数字与代码核验）/ citation-audit（引用核查）
      / kill-argument（最强拒稿论证演习）/ launch（长训练任务检查单）
      / night-loop（无人值守夜跑）/ cross-model-review（评审防自嗨协议）
      / research-publishing（录用后开源复现包）/ arxiv-radar（在研期间持续监控撞车）
编排：research-pipeline（阶段推进 + 决策卡机制）

附加层（科研全周期扩展，均为原件收录）：
专利：patent-pipeline（总编排）→ invention-structuring → prior-art-search →
      patent-novelty-check → claims-drafting → specification-writing →
      patent-review → jurisdiction-format（中/美/欧格式，含 shared-references 中的各国范本）
宣传：paper2poster / paper2video / paper2reel / paper2blog / paper2assets（微软 Reel 套件：
      论文 PDF → 海报/讲解视频/交互 reel/双语博客）；paper-poster-html / paper-slides /
      paper-talk / render-html / mermaid-diagram（ARIS 展示套件：HTML 海报/幻灯/报告讲稿/方法图）
基金：grant-proposal（申请书撰写，含外部评审环节）
文献增强：systematic-review（系统综述）/ meta-analysis（元分析）/ time-series-analysis（时序分析方法）
实验增强：statistical-testing（显著性检验）/ dataset-curation（数据集偏差审计）
      / ablation-planner（消融规划）/ analyze-results（结果分析）
理论：formula-derivation（公式推导）/ proof-writer（证明撰写）/ proof-checker（证明逐步核验）
自动循环（ARIS 原件 + 适配层）：auto-review-loop / auto-review-loop-llm（多轮评审→修复→再评）
      / auto-paper-improvement-loop（论文打磨循环，≤ 2 轮）/ dse-loop（目标导向参数探索）
      / run-experiment + monitor-experiment + experiment-queue（GPU 实验排队/监控，含脚本）
      —— 评审器后端按 shared-references/reviewer-adapter.md 适配：
      Codex MCP → codex/gemini CLI → Devin 子会话 → 新对话人工中转 → 同模型降级并标注，
      四平台（Claude Code / Codex / Devin / Cursor）均可用，接不接 MCP 都能跑
写作/展示增强：result-to-claim（实验结果→论文主张）/ paper-claim-audit（逐主张证据核验）
      / research-review（深度技术评审）/ paper-illustration + figure-description（插图）
      / slides-polish（幻灯打磨）/ embodiment-description（专利实施例）
      / paper-compile + overleaf-sync（LaTeX 编译/Overleaf 同步）/ research-wiki（长期研究记忆）

※ = 原件收录（含脚本/参考文件）。idea-spark、paper-search、scoop-check 来自
microsoft/ResearchStudio，具备 6 源检索、全文抓取与程序化校验能力，首次使用需
安装 Python 依赖（见各自 SKILL.md 的 Setup 节）；未安装时流水线自动降级为轻量模式。
ARIS 系原件引用的 `mcp__codex__codex` 跨模型评审为可选增强：无该 MCP 时按各
SKILL.md 内的 fallback 说明跳过外部评审或改用本包 cross-model-review 协议替代。
ARIS 原件中引用未收录 skill 的地方，按 `skills/shared-references/pack-mapping.md` 替换表处理。
海报默认用 paper2poster（完整渲染链）；paper-poster-html 仅在用户明确要 HTML 单页海报时用。
```

## 安装

- **Claude Code**：`cp -r skills/* ~/.claude/skills/`（或项目级 `.claude/skills/`）
- **Codex**：拷贝到项目内，在 `AGENTS.md` 中列出各 SKILL.md 路径
- **Devin（含网页版）**：拷贝到仓库 `.agents/skills/`
- **Cursor**：拷贝到项目内，在 `.cursor/rules/`（或 `AGENTS.md`）中引用各 SKILL.md 路径

`tools/` 目录（experiment-queue 等的脚本）与 `skills/` 平级拷贝。评审器后端适配见
`skills/shared-references/reviewer-adapter.md`：有 MCP 走 MCP，没有则自动降到
CLI / 子会话 / 新对话人工中转，四平台都能用。

`domains/` 目录与 skills 平级放置；各 skill 会按需读取 `domains/<领域>.md`。

## 用法

对 agent 说自然语言即可，例如：

- "启动科研流水线，方向：长序列多变量时序预测" → research-pipeline 接管
- "帮我挖 10 个候选创新点" → idea-mining
- "查一下这个 idea 有没有撞车：……" → scoop-check
- "评审这个 idea 是否有真洞察" → idea-critic
- "为 idea X 设计并执行实验" → experiment-loop

## 决策卡机制

每个关键阶段结束时，agent 必须产出一张**决策卡**（Markdown 文件，存于
`research_run/<课题slug>/decision_cards/`），包含：阶段结论、证据摘要、
可选项（含各自风险）、agent 推荐项、等待人类批示的明确问题。
**人未批示前不得跨阶段推进。** 这是"人做监督者"模式的硬约束。
