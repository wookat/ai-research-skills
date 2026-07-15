---
name: cross-model-review
description: Fresh-context cross-model review protocol that prevents self-congratulatory score inflation - routes verdict-bearing reviews (idea critique, paper review, claim audits) to a different model or a zero-context fresh thread with a bias guard. Use when running any review/audit step of the pipeline, when the user asks for an unbiased second opinion, cross-model review, or mentions review score inflation.
---

# Cross-Model Review（跨模型/零上下文评审协议）

完整红线见 `shared-references/research-integrity.md`。

评审最大的失效模式是**自我开脱**：同一个上下文里"改完再评"，分数会虚高。
ARIS 的实证结论：同线程续评把真实 3/10 的论文逐轮刷到虚假 8/10；换成零上下文
新线程后恢复真实 3/10。本 skill 把这条纪律固化为协议，供包内所有 verdict 类
skill（idea-critic / reviewer-simulation / kill-argument / citation-audit /
paper-verification）调用。

## 协议（按可用资源降级）

1. **首选：不同模型**。若环境有第二个模型 CLI（如 `codex exec`、`gemini`），
   把评审 prompt + 文件路径交给它，只读模式，输出落盘。
2. **次选：零上下文子任务**。同模型但开全新上下文（子 agent / 新会话），
   只给被评审的文件本身。
3. **兜底：自我评审 + 显式声明**。实在无法隔离时照常评审，但在报告头部写明
   `⚠ same-context review, scores may be inflated`，且该评审不得作为决策卡 #2/#4 的唯一依据。

## 铁律（REVIEWER_BIAS_GUARD）

- 评审线程**只读被评审对象本身**：不给上轮评审、不给修改清单、不给"我们已经修了 X"的说明。
  这些信息会诱导评审者确认改进而非独立判断。
- 禁止在同一评审线程里"续问"（相当于让被告当法官）。每轮评审 = 一次全新调用。
- 评审结论必须落盘（`stage6_review/` 或对应阶段目录），主上下文只读结论文件。
- **verdict 类 skill 不得定时自动重跑**：评审只在被评对象变化后才有新信号，
  按时钟重刷分数 = 自我开脱。自动循环只允许用于有客观机器可判停止条件的任务（见 night-loop）。

## 停止条件的两类划分（决定能否无人值守）

- **Type-A（客观指标）**：MSE 降到阈值、编译通过、测试全绿 —— 机器可判，可自动循环。
- **Type-B（评审裁决）**：论文分数、novelty 判定、立项结论 —— 必须新鲜上下文出具，
  且循环轮数有硬上限（写作改进 ≤2 轮，收益递减），最终裁决走决策卡交人类。
