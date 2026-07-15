# Reviewer Independence Protocol

## Core Principle

**Content must reach the reviewer unfiltered. The executor points to files and sets the review task; the reviewer reads and judges independently.**

Cross-model adversarial collaboration only works if the reviewer forms its own assessment from primary artifacts. If the executor pre-digests, summarizes, or interprets content before passing it to the reviewer, the reviewer is evaluating the executor's framing — not the actual work. This re-introduces the correlated blind spots that heterogeneous review is designed to avoid.

## What CAN be passed to the reviewer

- **Role/persona** — e.g., "Review as a NeurIPS-level reviewer"
- **Review objective** — e.g., "Evaluate publishability", "Check code correctness", "Score 1-10 on clarity"
- **File paths** — let the reviewer read file contents directly
- **Structural metadata** — e.g., "The paper has 8 sections", "Experiments are in experiments/"
- **Venue constraints** — e.g., "ICLR format, 9-page limit"

## What CANNOT be passed (counts as "subjective interference")

- ❌ Executor's summary or paraphrase of file contents
- ❌ Executor's interpretation of results (e.g., "I think the problem is...", "This suggests...")
- ❌ Executor's recommendations or conclusions (e.g., "I suggest changing...", "The likely cause is...")
- ❌ Key findings or bullet points extracted by the executor
- ❌ Leading questions (e.g., "Is this publishable?", "Is this trade-off reasonable?")
- ❌ Previous review rounds' feedback or critique (let the reviewer assess the current state fresh)
- ❌ Executor's description of what was changed since last round (e.g., "I fixed X, Y, Z")
- ❌ Statements asserting the current approach's strengths

## Why this matters

| With filtering | Without filtering |
|---|---|
| Reviewer sees executor's framing | Reviewer sees raw artifacts |
| Correlated blind spots persist | Genuinely independent assessment |
| Executor can "coach" favorable review | Review probes real weaknesses |
| Defeats the purpose of cross-model | Achieves adversarial collaboration |

## Correct pattern

```
mcp__codex__codex:
  prompt: |
    Review the following research project as a senior ML reviewer.

    Files to read:
    - Proposal: /path/to/PROPOSAL.md
    - Experiment results: /path/to/EXPERIMENT_LOG.md
    - Paper draft: /path/to/paper/main.tex
    - Code: /path/to/src/

    Please read all files yourself and provide a complete review.
    Score 1-10 on: novelty, soundness, clarity, significance.
```

## Incorrect pattern

```
mcp__codex__codex:
  prompt: |
    The main contribution is a new loss function that improves by 15%.
    However, I noticed the ablation is incomplete.
    Here's my summary of the key results: [...]
    Please review whether this is publishable.
```

## When to apply

This protocol applies to ALL cross-model review calls in ARIS:
- `/research-review` — paper review
- `/auto-review-loop` — iterative review
- `/paper-plan` — outline review
- `/paper-write` — section review
- `/paper-figure` — figure quality review
- `/rebuttal` — stress test
- `/meta-optimize` — patch review
- Any skill that sends artifacts to `mcp__codex__codex` or `mcp__codex__codex-reply`

## Exception

Multi-round review within the SAME thread (`codex-reply`) may reference the reviewer's own previous feedback to check resolution — but still must not include executor interpretations of that feedback.

**本整合包收紧（hard rules）**：

- 该 Exception 仅覆盖 *resolution check*（逐项确认旧 issue 是否已解决）与同一轮内的
  Debate 裁决；同线程续评**不得产生新的 verdict/score**，不得作为任何循环的正向
  停止条件——新一轮 verdict 必须是零上下文新调用（见 reviewer-adapter.md）。
- **REVIEWER_MEMORY 边界**：向"新鲜零上下文评审器"注入跨轮 memory 时，只允许
  客观可核查事实（未解决 issue ID、文件路径/行号、待复核的具体 claim）；历史
  分数、verdict、主观怀疑与评分轨迹不得注入（锚定效应）。注入过 memory 的轮次
  属于 memory-informed resolution check，verdict 元数据须标注 `context:
  memory-informed`；循环最终的正向 verdict 必须来自一次未注入 memory 的真正
  零上下文跨族评审。
