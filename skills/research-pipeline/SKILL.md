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

产出决策卡后**停止推进并通知人类**。人类批示记入 `state.md` 后才能进入下一阶段。
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
artifact 检查。**逃生口需人类授权**：`start --provisional-advances` 与
`accept --force` 属绕过强制的逃生口，只有当 state.md 中已记录对应决策卡编号的
人类批示时才允许使用，agent 不得自行开启。

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
