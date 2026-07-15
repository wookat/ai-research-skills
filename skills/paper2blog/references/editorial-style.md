# Editorial Style

This skill ships **two** articles per paper — a Chinese WeChat version (`_zh`) and an English research-blog version (`_en`). They report the same facts, figures, and numbers, but each is written natively in its own voice. Use the matching section below per language; never machine-translate one into the other.

---

# Chinese WeChat Voice (`_zh`)

## Language

- 主体使用中文。
- 专业名词、方法名、数据集、模型、论文标题、benchmark 名称可以保留英文。
- 首次出现的关键英文术语建议采用「English Term（中文解释）」或「中文解释（English Term）」。
- 不要为了中文化而误译固定名称，如 OpenReview、FineWeb-Edu、HumanEval、Mistral、Qwen。

## Tone

- 目标是“专业、清楚、有传播性”，不是营销稿。
- 可以使用一个贴近读者的类比，但类比只负责帮助理解，不要替代技术解释。
- 避免过度词：颠覆、革命性、史无前例、彻底解决、首次证明、完美、碾压，除非论文明确且证据足够。
- 多用“本文提出/验证/观察到/显示”，少用“我们发现真理式”的绝对表达。
- 如果某句话是从结果推导出的解释，用“这说明/这表明/一种可能解释是”，不要伪装成论文原文结论。

## Narrative Rhythm

推荐节奏：

1. 从读者熟悉的问题切入。
2. 说明为什么现在这个问题更重要。
3. 引出论文的核心问题。
4. 用一句话概括论文贡献。
5. 用图解释整体框架。
6. 分段解释方法或原则。
7. 用关键实验支撑每个重要观点。
8. 收束到实践意义和边界。

## Paragraph Rules

- 每段只承担一个清晰功能：提出问题、解释概念、连接图、描述方法、解释结果、总结意义。
- 段落之间要有推进关系，不要把论文摘要拆成松散中文段落。
- 典型段落长度控制在 80 到 180 个中文字符左右；复杂技术段落可以略长。
- 图前段落负责“教读者怎么看图”，图后段落负责“解释图说明了什么”。

## Titles

标题应当同时包含论文主题和读者利益点。常见模式：

- `会议/机构 | 主题判断句`
- `不只是 X，还要 Y`
- `从 X 到 Y：论文提出 Z`
- `让模型学得更好，数据顺序也很关键`

副标题用于补充机构、会议、方法名称或一句更正式的价值说明。

## Accuracy Rules

- 保留论文的约束条件：数据集、模型规模、训练阶段、评测任务。
- 数字必须能追溯到论文或用户材料。
- 不要把 baseline 的局部胜出写成总体失败。
- 不要把“相关工作”写成“本文首次提出”。
- 如果输入材料没有论文链接、代码链接、接受状态或作者信息，直接省略该元素，不要凭空补，也不要留「待补充」占位——这些是会被直接发布的硬事实。其余属于编辑判断的内容自行决定即可。

---

# English Research-Blog Voice (`_en`)

This is **not** a translation of the Chinese version. Write it natively for a Western technical audience — the kind of reader who follows research blogs like The Gradient, Distill, a lab's announcement post, or a thoughtful Substack. Same facts and figures as `_zh`; different rhythm, idiom, and structure as the language naturally demands.

## Language

- Write fluent, idiomatic English. Avoid translationese — phrasings that are grammatical but betray a word-by-word mapping from Chinese (e.g. "Aiming at the problem of...", "has very important significance", "carried out experiments").
- Keep technical terms, method names, benchmarks, datasets, and model names exactly as the paper writes them (FineWeb-Edu, HumanEval, Qwen, Mistral, OpenReview).
- Define a term once, in plain language, the first time it carries weight — then use it freely.
- Use American spelling and standard ML-writing conventions unless the user says otherwise.

## Tone

- Professional, clear, and genuinely interesting — informative, not promotional.
- One reader-facing analogy is welcome to build intuition, but it supports the technical explanation rather than replacing it.
- Avoid hype words: revolutionary, groundbreaking, game-changing, unprecedented, solves once and for all, perfect, crushes/destroys — unless the paper makes the claim explicitly and backs it with evidence.
- Prefer grounded verbs: "the paper proposes / shows / observes / finds." When a sentence is your interpretation of a result rather than the paper's stated conclusion, signal it ("this suggests", "one reading is", "the authors argue").
- Active voice and concrete subjects over abstract nominalizations ("the model forgets rare tokens", not "a phenomenon of forgetting is observed").

## Narrative Rhythm

A workable shape (adapt to the paper, don't force it):

1. Open with a hook the reader already feels — a familiar tension, a surprising result, or a question the field keeps tripping over.
2. Say why it matters now.
3. State the paper's core question or contribution in one crisp sentence.
4. Use the overview figure to ground the framework.
5. Walk through the method or named components one at a time.
6. Support each important claim with a key experiment.
7. Close on the practical significance and the honest boundary of the result.

## Paragraph Rules

- One job per paragraph: pose a question, explain a concept, set up a figure, describe a method, interpret a result, or land the takeaway.
- Paragraphs should advance the argument — each one earns the next. Don't dissolve the abstract into a loose list of restated sentences.
- Vary sentence length; let a short sentence land a point. English research-blog paragraphs typically run a touch longer than the WeChat version's — that's fine.
- The paragraph before a figure teaches the reader how to read it; the paragraph after says what it means.

## Titles

The title should name the topic and the reader's payoff. Common patterns:

- `Venue/Org: a claim-shaped headline`
- `Not just X — Y too`
- `From X to Y: the paper proposes Z`
- `Why <surprising thing>, and what to do about it`

Use the subtitle for the institution, venue, method name, or a more formal one-line value statement.

## Accuracy Rules

- Preserve the paper's constraints: datasets, model scale, training stage, evaluation tasks.
- Every number must trace to the paper or the user's materials — and must match the figure in the `_zh` version exactly.
- Don't inflate a baseline's local win into an overall loss, or describe prior work as the paper's own first contribution.
- If a paper link, code link, acceptance status, or author detail is missing from the inputs, omit that element rather than inventing a value or leaving a "to be confirmed" placeholder — these are hard facts that ship straight to publication. Everything that's editorial judgment, decide yourself.
