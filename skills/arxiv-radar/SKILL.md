---
name: arxiv-radar
description: Periodic literature monitoring and re-scooping check for an ongoing research project. Scans arXiv/OpenReview for new papers matching the project's topic signatures, triages threats to the project's novelty claim, and updates the domain module. Use when the user asks to check for new papers, monitor the field, re-run a novelty check on an in-progress project, or on a recurring schedule during stages 4-7 of the pipeline.
---

# arXiv Radar（在研课题的文献监控）

立项不等于安全：从立项到投稿的几个月里，撞车论文随时可能挂出。本 skill 定期扫描并分级预警。

## 输入

- 项目的 `scoop_report.md`（含四轴分解与检索 query——直接复用其方法签名）
- 上次扫描日期（记录在 `research_run/<slug>/radar_log.md`；首次运行 = 立项日）

## 流程

1. **增量检索**：用项目的三类 query（问题原述/宽领域/方法签名）检索自上次扫描以来的
   新论文，源：arXiv（按提交日期过滤）+ OpenReview 当季在审。优先用包内 `paper-search`。
2. **威胁分级**（复用 scoop-check 四轴）：
   - **红**：核心机制轴撞 → 立即出临时决策卡（抢发 arXiv / 调整 delta / pivot）
   - **黄**：洞察或问题框架撞 → 记入 related work 必比清单，评估是否需补对比实验
   - **绿**：仅领域相关 → 记入 lit_table.md 增量
3. **领域模块更新**：新出现的 SOTA baseline、新数据集/评测协议变化写入
   `domains/<领域>.md` 的对应节（标注日期）。
4. 追加 `radar_log.md`：扫描日期、新论文数、分级结果、采取的行动。

## 建议频率

阶段 4（实验）期间每 2 周一次；投稿前 1 周必跑一次全量（含补召回）；
rebuttal 期间跑一次（审稿人可能引用最新论文）。

## 纪律

- 红色预警不得降级处理或延迟上报；抢发窗口以天计。
- 只报增量，不重复历史结论；radar_log 保持可追溯。
