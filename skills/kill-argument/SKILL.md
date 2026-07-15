---
name: kill-argument
description: Adversarial attack-defense exercise on a near-final paper - a fresh reviewer writes the single strongest 200-word rejection memo, a second fresh reviewer defends point-by-point, and an adjudicator classifies each attack point as answered / partially answered / still unresolved. Use once before submission after standard reviews have stabilized, or when the user says kill argument, hostile review, or asks what would make an area chair reject this paper.
---

# Kill Argument（最强拒稿论证演习）

常规评审给出"均衡的弱点列表"，但真正杀死论文的往往是**一段话**——审稿人写进
拒稿意见、让 AC 一读就倾向 reject 的那个单一最强论证。本 skill 强制把它找出来。
（ARIS 实证：论文经多轮常规改进稳定在 7-8/10 后，此演习仍暴露出所有此前评审
都没抓到的 framing 硬伤。）

## 何时用

标准评审（reviewer-simulation）稳定后、投稿前**跑一次**。它是 verdict 类 skill：
禁止定时重跑（攻击只随论文变化而变化）。每个线程遵守 cross-model-review 协议
（零上下文、优先跨模型）。

## 三线程流程

**线程 1 — 攻击（fresh）**：只读论文源文件（tex/PDF），不读任何历史评审。
任务：写**约 200 词（≤250）的单一连贯拒稿论证**——不是弱点列表，是你作为敌意
审稿人要说服 AC 拒稿的那一段。优先攻击面：标题/摘要主张 vs 实际证据的落差、
条件性结论被表述为一般性结论、假设与主张不匹配、baseline 与真实场景无关。

**线程 2 — 防御（fresh）**：把攻击 memo 拆成 3-7 个原子拒稿点，逐点对照**当前
论文文本**判定：`answered_by_current_text` / `partially_answered` / `still_unresolved`。
防御只能引用论文里已有的内容，不得引用"我们打算改"的意图。

**线程 3 — 裁决**：汇总两方，输出：
- 攻击 memo 全文 + 逐点分类表
- `still_unresolved` 点的修复方案（改正文的具体位置与措辞，通常是收窄 scope、
  在 abstract/discussion 加显式限定——这类修复成本低、防御价值高）
- 判定：可投 / 修复后可投 / 该攻击成立且不可修复（如实上报，出临时决策卡）

## 输出

`stage6_review/kill_argument.md`（memo + 分类表 + 修复清单）。修复执行后**不重跑
本演习刷结论**；修复是否到位由下一轮 reviewer-simulation 检验。

## 纪律

- 攻击线程必须"必须下注"：只许一个最强论证，禁止摊平成弱点清单。
- 防御不得稻草人化攻击；每个原子点原文引用后再回应。
- `still_unresolved` 为空时要警惕评审隔离是否失效（同上下文互相放水）。
