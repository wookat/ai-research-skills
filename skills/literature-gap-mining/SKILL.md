---
name: literature-gap-mining
description: Systematic literature survey plus research-gap mining. Builds a structured literature table and a method-problem-dataset gap matrix, surfacing contradictions and unexplored cells that seed research ideas. Use when the user asks for a literature review, survey of a research area, "what has been done", or to find research gaps/opportunities. Do not use for checking one specific novelty claim (use scoop-check).
---

# Literature & Gap Mining（文献综述与缺口挖掘）

目标不是"读过多少论文"，而是产出两个可供选题使用的结构化资产：**文献表**和**缺口矩阵**。

## Step 1 — 检索

围绕研究方向构造 4 类互补 query，多源检索（arXiv、Semantic Scholar、DBLP、
OpenReview、Google Scholar，可用则全用；至少 2 源）：

1. 问题原述 query（用户方向的直接改写）
2. 宽领域 query（3-5 词的上位领域）
3. 方法签名 query（具体技术动作，5-8 词）
4. 综述 query（"survey/benchmark + 领域"）

**优先用同包的 `paper-search` skill**（脚本化，跨 arXiv/DBLP/OpenAlex/OpenReview/
Semantic Scholar/Crossref 六源检索+去重，返回结构化 JSON）；未安装依赖时降级为
agent 自行多源搜索并标注覆盖受限。

范围：近 3 年为主 + 领域奠基论文。按标题归一化去重后，**再用自身知识补召回**
0-5 篇检索未命中但你确信存在的关键论文（标注 `source: model-recall`，
不确定的字段留空，禁止编造）。目标池 30-80 篇。

## Step 2 — 文献表（lit_table.md）

每篇提取（只读 abstract 即可，重点论文再读全文）：

| 字段 | 说明 |
|---|---|
| 标题 / 年份 / 会议 | OpenReview 上在审的标 (submitted) |
| 问题框架 | 任务定义、输入输出、评测口径 |
| 核心机制 | 架构/算法/理论/数据构造 |
| 关键洞察 | 为什么 work、先前 SOTA 缺什么 |
| 主张 vs 证据 | 声称的贡献与实验是否匹配，有无夸大 |
| 局限（作者自认 + 你发现的） | |

## Step 3 — 缺口矩阵（gap_matrix.md）

以"方法机制 × 问题设定 × 数据/评测条件"建三维矩阵（实际写成分组表格），逐格标注：

- **空格**：无人做过的组合 → 候选缺口（先判断是"没价值"还是"没人做"）
- **矛盾格**：不同论文结论冲突（A 说有效、B 说无效且无人解释）→ 高价值缺口
- **拥挤格**：>5 篇近作扎堆 → 撞车高危区，标红
- **脆弱格**：结论只在特定数据集/设定下成立、换条件即翻车 → 可挑战的假设

矛盾格与脆弱格是最好的选题来源；空格其次；拥挤格只有在能推翻共识时才碰。

## Step 4 — 输出

1. `lit_table.md` — 全量文献表
2. `gap_matrix.md` — 缺口矩阵 + 每个高价值缺口一段"为什么值得做/风险"
3. 摘要（≤15 行）：领域主线叙事、3-5 个最有潜力的缺口、拥挤区警告

## 纪律

- 每条主张必须可溯源到具体论文；无法溯源的判断显式标注"模型推断"。
- 引用只用真实存在且已核对标题的论文；宁缺毋滥。
- 读到与领域模块（domains/*.md）矛盾的新证据时，在输出中显式指出。
