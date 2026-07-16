---
name: research-pipeline
description: Orchestrate the full research lifecycle (literature → ideation → novelty check → idea critique → experiments → paper writing → review simulation → rebuttal → thesis) with human decision cards between stages. Use when the user asks to start/resume a research project, run the research pipeline, or asks "what's the next step" in an ongoing research effort. Do not use for a single isolated task (use the stage-specific skill directly).
---

# Research Pipeline（科研流水线编排）

把一个研究方向推进为一篇可投稿论文。你（agent）负责全部执行；人类只在决策卡处做选择。

## 运行目录约定

一个课题 = 一个目录：`research_run/<课题slug>/`，结构：

```
research_run/<slug>/
  state.md               # 流水线状态（当前阶段、已完成阶段、人类批示记录）
  stage0_literature/     # 文献表、缺口矩阵
  stage1_ideas/          # 候选 idea 卡
  stage2_scoop/          # 撞车检查报告
  stage3_critique/       # idea 评审卡
  stage4_experiments/    # 实验假设树、结果、消融、evidence_summary.md
  stage5_paper/          # 论文草稿（main.tex / draft.md）
  stage6_review/         # 模拟审稿报告、kill_argument.md、citation_audit.md、verification_report.md
  stage7_rebuttal/       # rebuttal.md（会议）或 response_letter.md + 修改稿 diff（期刊 revision）
  stage8_thesis/         # 学位论文工程（thesis/）
  radar_log.md           # arxiv-radar 持续监控日志（课题根目录）
  decision_cards/        # 决策卡（等待人类批示）
```

## 启动自检清单（进入任何阶段前必须执行，不可凭记忆跳过）

试跑教训：agent 凭记忆行事会绕过状态机和脚本化检索，直接手写检索漏掉过关键威胁
论文。因此每次启动/恢复一个 run，先依次执行这三条（结果记入 state.md）：

```bash
# 1. 包自检：依赖、脚本语法、（可选 --online）检索源存活
python3 tools/self_check.py --online
# 2. 注册/恢复状态机（阶段推进只认 run_state，不认 agent 口头声明）
python3 tools/run_state.py start research_run/<slug> <run_id> --phases "stage0,...,stage8"
python3 tools/run_state.py resume research_run/<slug> <run_id>
# 3. 定位领域文件（见下文"领域模块"节）；无对应文件则记录缺失
```

任何一条失败：能修则修（pip install -r requirements.txt）；不能修则在 state.md
记录降级原因与影响面（例：openreview 源不可用 → 本 run 所有 scoop 结论只能为
provisional）。**禁止静默降级。**

**事实流水线补注册（试跑教训）**：很多 run 不是从"启动流水线"开始的——用户先让
你收集文献，再让你挖创新点，不知不觉已经走到阶段 2。**判定规则：一旦第二个阶段
的工作开始（例如文献收集之后接着做 idea 挖掘），就已经是一个事实上的流水线 run。**
此时必须立即补执行启动自检清单（self_check + run_state start + 领域模块）并把已
完成阶段的产物补登记到规范路径与 state.md，而不是等到某个晚期阶段才补建状态机
（试跑中 state.md 直到阶段 4 才被补写，前三个阶段的决策卡记录全靠事后回忆）。

## 阶段图与对应 skill

| 阶段 | Skill | 产物 | 决策卡 |
|---|---|---|---|
| 0 文献与缺口 | literature-gap-mining（检索引擎用 paper-search） | lit_table.md, gap_matrix.md | — |
| 1 创新点挖掘 | idea-spark（脚本化重型，首选）或 idea-mining（轻量无依赖） | stage1_ideas/idea_cards.md | **#1 选 idea**。idea-spark = 单点深挖（一次深入一个方向，产 1 张高质量卡）；需要一次产出多个候选做决策卡#1 时用 idea-mining。两者产物都落 stage1_ideas/。 |
| 2 防撞车 | scoop-check（脚本化，依赖 paper-search） | scoop_report.md（每个入选 idea 一份） | — |
| 3 洞察评审 | idea-critic | critique_card.md | **#2 立项拍板** |
| 4 实验循环 | experiment-loop（子技能：reproduce / compare / debug / experiment-design / ablation-planner / analyze-results / statistical-testing / dataset-curation / launch；无人值守用 night-loop，大批量任务用 experiment-queue / run-experiment / monitor-experiment，参数探索用 dse-loop） | hypothesis_tree.md, results/, ablations/ | **#3 结果定夺** |
| 5 写作 | paper-writing（+ references/ccfa-structure.md）；图表用 data-visualization；LaTeX 用 latex-workflow / latex-setup；理论部分用 formula-derivation / proof-checker | main.tex / draft.md | — |
| 6 投稿自审 | reviewer-simulation + paper-verification + citation-audit + kill-argument（稳定后跑一次）+ deai-polish；多轮自动改进用 auto-paper-improvement-loop（≤ 2 轮，评审器按 reviewer-adapter 适配） | mock_reviews.md, kill_argument.md, citation_audit.md | **#4 投稿决定** |
| 7 Rebuttal / Revision | rebuttal-writing。两条路径：**会议 rebuttal**（不可改稿的短周期辩护 → rebuttal.md）；**期刊 major revision / 重投**（可改稿 → response_letter.md + 修改稿 diff，按 rebuttal-writing 的期刊模板与 cover letter 节执行）。被拒转投：消化全部审稿意见 → 回阶段 6 重审 → 出临时决策卡定新 venue 后按新格式重排。 | stage7_rebuttal/ | — |
| 8 学位论文 | thesis-convert + deai-polish | thesis/ | — |
| ⊕ 录用后 | research-publishing（开源代码/复现包）；宣传用 paper2poster / paper2video / paper2reel / paper2blog 或 paper-poster-html / paper-slides / paper-talk | 代码仓库、宣传物料 | — |
| ⊕ 专利 | patent-pipeline（编排 invention-structuring → prior-art-search → patent-novelty-check → claims-drafting → specification-writing → patent-review → jurisdiction-format），建议与投稿并行启动（专利优先权日越早越好） | 专利申请文件 | — |
| ⊕ 持续 | arxiv-radar（阶段4起每 2 周；投稿前/rebuttal 期必跑） | radar_log.md | 红色预警时临时决策卡 |

**全局强制说明：**每个阶段 skill 结束后，编排者负责确认产物已落到
`research_run/<slug>/stageN/` 规范路径，缺失则搬运；下一阶段只从规范路径读取，
不依赖对话记忆。

阶段 2 失败（撞车）→ 回到阶段 1 换 idea；阶段 3 判"需 pivot" → 回阶段 1；
阶段 4 假设被证伪 → 在阶段 4 内部迭代（见 experiment-loop），连续两轮无进展 → 出决策卡回阶段 1。

## 决策卡格式（硬约束）

写入 `decision_cards/card_<N>_<阶段名>.md`：

```markdown
# 决策卡 #N — <阶段名>
## 阶段结论（≤5 行）
## 证据摘要（链接到产物文件，不要长篇复述）
## 选项
- A. <选项>：预期收益 / 风险 / 预估工作量
- B. ...
## Agent 推荐：<选项及一句话理由>
## 等待批示的问题（明确、可一句话回答）
```

所有 verdict 类评审（idea-critic / reviewer-simulation / kill-argument / citation-audit /
paper-verification）必须遵守 **cross-model-review 协议**：零上下文新线程、优先跨模型、
禁止同线程续评、禁止按时钟重跑刷分。

决策卡**用工具生成而非手写**（模板一致、并自动在 state.md 记一条"等待批示"条目）：

```bash
python3 tools/run_state.py new-card research_run/<slug> card_<N>_<名称> --title "<标题>"
```

产出决策卡后**停止推进并通知人类**（Devin：用 user_question 消息附选项；Claude Code：
AskUserQuestion；其他平台：明文列选项等待回复——只把卡写进文件不算通知）。
人类批示记入 `state.md` 后才能进入下一阶段，**批示行必须是结构化格式**（run_state.py
只认这一格式，否定句/单纯提及卡号不构成授权）：

```
人类批示：card_<N>_<名称> → <选项/裁决>     # 或英文：APPROVED card_<N>_<名称> -> <裁决>
```

决策卡以外的一切执行细节不要询问人类，自行决定并记录。

**结构性强制（run_state.py）**：若本包 `tools/run_state.py` 可用（按
`skills/shared-references/integration-contract.md` §2 的 canonical 四层解析链解析），
用它维护阶段状态机（Policy B：不可用时 warn-and-skip，退回 state.md 手工记录，
并在 state.md 如实标注"结构性强制不可用，本 run 退化为文档约束"）。真实 CLI：

```bash
# run 启动时（一次）：注册阶段序列
python3 tools/run_state.py start research_run/<slug> <run_id> --phases "stage0,stage1,...,stage8"
# 阶段产物完成时
python3 tools/run_state.py set research_run/<slug> <run_id> <stageN> done --artifact <产物路径>
# 决策卡产出后（同族/降级评审只能到 provisional）
python3 tools/run_state.py mark-provisional research_run/<slug> <run_id> <stageN> \
  --verdict-id <评审verdict id> --reviewer <reviewer模型名>
# 仅当人类批示已记入 state.md 且评审为跨族/deterministic 时
python3 tools/run_state.py accept research_run/<slug> <run_id> <stageN> \
  --verdict-id <评审verdict id> --reviewer <reviewer模型名>
```

状态非 accepted 时**禁止推进下一阶段**。这把决策卡从 prose 约束升级为可验证的
artifact 检查。**逃生口需人类授权（硬校验）**：`start --provisional-advances` 与
`accept --force` 属绕过强制的逃生口，必须 `--decision-card <卡号>`，且
run_state.py 会实际读取 `research_run/<slug>/state.md` 校验该卡号确实已被人类
批示记录——卡号不存在即拒绝执行，agent 编造卡号无法绕过。

## 全自主模式（autopilot）

默认模式是"人类在 4 张决策卡处批示"。当人类明确要求**全流程放权**时，切换到
autopilot 模式，规则如下：

1. **总授权卡**：人类在 `state.md` 中记录一张 `card_0_autopilot` 授权卡，写明
   放权范围与边界（允许自裁的阶段、预算/时间上限、终止条件）。没有这张卡记录在
   state.md 中，agent 不得进入 autopilot——这与逃生口共用同一硬校验机制
   （run_state.py 会读 state.md 验证卡号）。
2. **AI 自裁决策卡**：每到决策卡节点，仍然照常产出决策卡文件，但不等待人类——
   为该卡开一个**零上下文、优先跨族**的子会话/子智能体（按
   shared-references/reviewer-adapter.md 选后端）做独立评估，按其结论选定选项，
   并把"裁决选项 + 理由 + 裁决者（模型/后端）+ 时间"追加记入 `state.md`。
   禁止主上下文自问自答式裁决。
3. **不可逆动作仍留给人类**：真实投稿（提交到会议/期刊系统）、公开发布
   （开源仓库转 public、发布宣传物料）、任何花钱动作，在 autopilot 下也必须停下
   出决策卡等人类批示——总授权卡不覆盖这些。
4. **可审计、可叫停**：所有自裁记录集中在 state.md，人类可随时回看；人类发出
   任何暂停/收回指令后，立即退回默认决策卡模式，并对收回后的第一张卡重新等待
   人类批示。
5. **失败保护**：同一阶段连续 2 次自裁后仍无进展（阶段回退循环），强制出临时
   决策卡等人类——autopilot 不允许无限自旋。

## 脚本化 skill 的初始化（首次使用）

idea-spark / paper-search / scoop-check 是携带脚本的重型 skill（源自 microsoft/ResearchStudio），
首次使用前按各自 SKILL.md 的 Setup 节安装依赖（`pip install feedparser openreview-py
beautifulsoup4 pymupdf`，可选 OpenReview/Semantic Scholar 凭证写入 `.env`）并跑连接器自检。
环境不具备时降级：阶段 1 用 idea-mining，阶段 0/2 的检索由 agent 自行多源搜索完成，
并在 state.md 标注“未用脚本化检索，覆盖面受限”。

## 领域模块

`domains/` 的解析顺序（全局安装时同样适用，与 helper 四层链对齐）：① 当前项目根的
`domains/`；② 相对本 SKILL.md 定位——`<本文件所在目录>/../../domains/`（即包安装
目录内，与 skills/ 平级）；③ 环境变量 `AI_RESEARCH_SKILLS_HOME`（或兼容旧名
`ARIS_REPO`）指向的包根目录；④ 全局指针文件 `~/.aris/repo` 指向的包根目录
（包根执行过 `bash install.sh` 即有）。四者均无时按下述缺失处理。

启动时读取 `domains/<领域>.md`（如 `domains/time-series-forecasting.md`），
将其中的数据集、评测协议、基线、已知陷阱注入到各阶段 skill 的上下文中。
若无对应领域文件，按通用 ML 研究处理，并在 state.md 中记录该缺失。

## 恢复运行

被要求"继续"时：读 `state.md` → 找到当前阶段与未批示的决策卡 →
若有未批示卡，向人类复述该卡的问题；若已批示，按批示执行下一阶段。

## 纪律

- 每阶段产物必须落盘为文件，禁止只存在于对话中。
- 阶段产物是下一阶段的唯一输入接口；跨阶段不要依赖对话记忆。
- 长实验/长检索在独立上下文或子任务中执行，主上下文只保留文件路径与结论。
- 任何阶段发现"更早阶段的结论被新证据推翻"，立即出临时决策卡，不得静默继续。

## Token 纪律（全阶段适用）

目标：主上下文只装"结论 + 文件路径"，原始数据一律落盘。

- **检索结果不进对话**：`search_papers.py` 一律加 `--out <file>.jsonl`，终端只看
  计数与 SOURCE HEALTH；后续筛选用脚本/grep 对文件做，不把成百条记录粘进上下文。
- **报告类产物（scoop 报告、评审卡、实验设计）**：全文写文件，对话里只给
  verdict/要点 + 文件路径；下一阶段从文件读，不从对话重建。
- **不重复加载**：领域模块/证据库按需读相关小节（grep 定位），不整文件载入；
  已落盘的阶段产物不在后续对话中整段复述。
- **子会话隔离重负载**：批量抓取、全文深读、多轮评审等高 token 工作交给子会话/
  子智能体，主会话只收结论文件。
- **避免返工即省 token**：最大的 token 浪费是整轮返工（idea 撞车后重来）——严格
  执行阶段 1 的快速撞车预查与命名界线核验、阶段 2 的界线论文全文核验，把撞车
  尽量拦截在最便宜的阶段。
