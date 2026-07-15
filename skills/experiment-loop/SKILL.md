---
name: experiment-loop
description: Hypothesis-driven experiment loop with fair-comparison discipline - reproduce baselines, run minimal validation, iterate via hypothesis tree, and build the ablation/evidence base for a paper. Use when the user asks to run experiments, validate an idea, reproduce a baseline, design ablations, or improve a method iteratively. Do not use for pure idea generation (idea-mining) or paper drafting (paper-writing).
---

# Experiment Loop（实验循环）

完整红线见 `shared-references/research-integrity.md`。

把一个已立项的 idea 变成一条闭合的证据链。核心纪律：**假设先行、公平对比、失败归因**。

本 skill 是实验阶段的编排层；具体操作委托给同包的四个专项 skill：
`reproduce`（论文复现七阶段法）、`compare`（同 epoch 公平对比）、
`debug`（证据优先的训练问题诊断）、`experiment-design`（消融矩阵设计）。
对应环节直接按它们的 SKILL.md 执行。

## 阶段 A — 基线复现（不可跳过）

1. 按领域模块 `domains/<领域>.md` 指定的代码底座、数据集与评测协议搭环境。
2. 复现 2-4 个关键 baseline，结果与原论文对表；偏差 >5% 必须归因（数据切分、
   归一化、超参、库版本），归因前不得开始新方法实验。
3. **失败切片分析**：baseline 在哪类样本/条件下系统性失败？这既校准直觉，也常反哺创新点。
4. 固化实验基建：统一 config、固定随机种子集合（≥3 个）、结果自动落盘
   （`results/<exp_id>/` 含 config + metrics + git commit hash）。

## 阶段 B — 最小验证实验

跑 idea card 里的"证伪计划"和"最小验证实验"（≤1 GPU·天）。
结果为否 → 不粉饰，直接走失败归因（阶段 C 的否定分支）。

## 阶段 C — 假设树迭代

维护 `hypothesis_tree.md`，每轮循环：

```
假设 H<N>：<机制性陈述，含预期现象>
  实验：<最小可判定实验>
  结果：证实 / 证伪 / 不确定
  证实 → 派生子假设（加消融、扩数据集、探边界条件）
  证伪 → 归因分析（按数据切片/训练曲线/中间表征定位原因）→ 修正假设 H<N+1>
  不确定 → 检查实验设计（统计功效不足？混淆变量？）
```

硬规则：

- **一次只改一个变量**。同时改两处的实验结果不入证据链。
- **公平对比**：新方法与 baseline 同 epoch/同预算/同调参努力对比；给 baseline
  的调参努力必须不少于给自己方法的。
- **禁止指标漂移**：结果不好不得悄悄换指标/换数据集/换切分讲故事。评测协议在
  阶段 A 冻结，变更需记录理由并全量重跑。
- **显著性**：主结果报 ≥3 种子的均值±方差；提升幅度小于种子间方差的结论不成立。
- 连续两轮假设证伪且归因指向核心机制本身 → 停止，出决策卡（继续 pivot 还是回选题）。

## 阶段 D — 论文级证据构建

主假设证实后，补齐审稿人必查的证据：

1. **主表**：全部标准数据集 × 全部 baseline（含最新 SOTA 与最强简单基线）
2. **消融**：每个创新组件单独去除；证明"最小性"（去核心组件应显著掉点）
3. **敏感性**：关键超参扫描，证明不是精调出来的脆弱点
4. **效率表**：参数量/训练成本/推理延迟 vs baseline
5. **失败案例分析**：主动展示方法在哪些条件下不 work（审稿人视角的诚实加分项）
6. **可复现包**：一条命令跑通主表的脚本 + 固定种子 + 环境锁定

## 输出

- `hypothesis_tree.md`（全部假设与结果，含被证伪的——它们进论文的 analysis 节）
- `results/` 全部实验记录
- `evidence_summary.md`：主张→证据映射表（`Claim | Experiment ID | Status`），
  直接供 paper-writing 使用
- 决策卡 #3：核心结果、证据链完整度、建议（写作 / 补实验 / pivot）

**本整合包契约：**产物写
`research_run/<课题slug>/stage4_experiments/`（`hypothesis_tree.md`、`results/`、
`ablations/`）；脱离 `research-pipeline` 单独调用时，退当前工作目录。

## 纪律

- debug 训练问题时证据优先：先看数据样本、loss 曲线、梯度范数，再改代码；禁止无归因的"魔法调参"。
- 每个实验先写预期再看结果；预期落空即记入假设树，不得当作没发生。
- 结果只汇报落盘数字，禁止凭记忆复述。
