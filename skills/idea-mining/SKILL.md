---
name: idea-mining
description: Lightweight pattern-driven research ideation with no script dependencies - generates 5-10 candidate ideas from a direction or gap matrix using proven ideation patterns, each with mechanism, falsification plan, and minimal validation experiment. Use for quick brainstorming of research ideas or when the scripted idea-spark skill is unavailable or not yet set up; prefer idea-spark for a single deeply-grounded reviewer-defensible idea card. Do not use for judging an existing idea (use idea-critic) or checking novelty (use scoop-check).
---

# Idea Mining（创新点挖掘）

不做自由联想。每个候选 idea 必须由**构思模式 × 具体缺口**结合而成，且自带证伪计划。

## 输入

- 研究方向（必需）
- `gap_matrix.md`（若无，先调用 literature-gap-mining 或做一轮轻量检索）
- 领域模块 `domains/<领域>.md`（若有，其"已知陷阱/被固化假设"节是重点原料）

## 构思模式库（逐个套用，每模式至少认真尝试一次）

提炼自 ICLR/ICML/NeurIPS 高分论文的常见创新模式：

1. **打破固化假设**：领域默认了什么假设（平稳性、通道独立、固定 lookback、点预测……）？打破它会怎样？
2. **外部约束内化**：把靠外部模块/后处理保证的性质（物理约束、单调性、频域特性）内化进结构，by construction 成立。
3. **启发式→可学习**：把手工设计的组件（patch 大小、分解规则、归一化策略）换成自适应/可学习的最优化。
4. **跨域机制迁移**：把别的领域被验证的机制（检索增强、MoE、状态空间、扩散）迁移过来——必须回答"迁移中什么发生了本质变化"，否则是缝合。
5. **失败驱动**：baseline 在哪类样本/条件下系统性失败？失败归因 → 修复机制。（最容易出真洞察）
6. **矛盾解释**：缺口矩阵中的矛盾格——两篇论文结论冲突，提出解释框架并预测新现象。
7. **诊断/度量创新**：现有评测度量不到的能力，设计受控诊断，往往顺带发现方法缺口。
8. **尺度/成本轴翻转**：同等性能下降低一个数量级成本，或极端小/大数据条件下的行为。
9. **理论补位**：经验上 work 但无解释的方法，给出理论刻画并由理论导出可检验的改进。
10. **任务重构**：改变问题的输入/输出/评测框架本身（如点预测→分布预测、单变量→变量间因果结构感知）。

## 每个候选 idea 的产出格式（idea card）

```markdown
## Idea <N>: <标题>
- 构思模式：<上表编号+名称>
- 针对缺口：<gap_matrix 中的具体格 / 失败现象>
- 核心机制（3-5 行，须具体到可实现）
- 关键洞察：现有方法为什么在此失败，本方法为什么能解决（禁止"A+B 应该更好"式表述）
- 证伪计划：一个最小实验，若结果为 X 则该 idea 直接否定
- 最小验证实验：数据集 / baseline / 指标 / 预期现象（≤1 GPU·天量级）
- 预判风险：最可能被审稿人攻击的一点
```

## 流程

1. 读缺口矩阵与领域模块，列出 3-6 个候选缺口（优先矛盾格、脆弱格、失败现象）。
2. 10 个模式 × 候选缺口做笛卡尔扫描，粗筛出 12-20 个组合。
3. 每个组合展开成 idea card 草稿；淘汰：机制说不具体的、洞察一栏写不出失败归因的、证伪计划写不出来的。
4. 留 5-10 张卡，按"洞察强度 × 可行性 × 撞车风险（拥挤格降权）"排序。
5. 输出到 `research_run/<课题slug>/stage1_ideas/idea_cards.md`，并提示下一步：入选卡逐个过 scoop-check + idea-critic。

**本整合包契约：**产物写 `research_run/<课题slug>/stage1_ideas/idea_cards.md`（单文件，
包含多个候选卡）；脱离 `research-pipeline` 单独调用时，退当前工作目录。

## 纪律

- "关键洞察"与"证伪计划"两栏写不出来的 idea 一律丢弃，不得用套话填充。
- 每张卡引用的现有工作必须真实；模式 4（跨域迁移）必须写明"本质变化"。
- 不要向人类中途提问；产出全部卡片后由人类在决策卡上筛选。
