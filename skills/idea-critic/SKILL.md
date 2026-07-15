---
name: idea-critic
description: Judge whether a research idea contains genuine insight (vs. combinatorial stitching), passes domain-intuition sanity checks, and would survive peer review. Three-layer critique - insight tests, domain pitfall checks, multi-persona reviewer simulation - producing a structured critique card with an accept/pivot/abandon verdict. Use when the user asks to evaluate, critique, or stress-test a research idea before committing to it. Do not use for finished paper review (use reviewer-simulation) or novelty search (use scoop-check).
---

# Idea Critic（洞察性评审）

⚠ 本 skill 属 verdict 类评审，必须遵守
`../cross-model-review` 协议：在零上下文新线程、优先跨模型的条件下出具评审，
只读被评对象，禁止在产生/修改该对象的同一上下文里自评（否则会把真实 3/10 刷成虚假 8/10）。
无法换线程/换模型时，按 `shared-references/reviewer-adapter.md` 降级并在结论标注
self-review 可能虚高。

在投入实验和写作之前，判定一个 idea 是**真洞察**还是**排列组合式缝合**，并预演审稿人的攻击。
输入：一张 idea card（或等价描述）+ 可选的 scoop_report.md + 领域模块 `domains/<领域>.md`。

## 第一层：洞察性判定（通用，四项检验）

1. **机制性检验**：该 idea 是否解释了"现有方法为什么在某处失败"？
   真洞察必有失败归因；只有"A+B 应该更好 / X 很火所以用 X"的是缝合。
   要求写出一句因果链："因为现有方法做了 <假设/设计>，所以在 <条件> 下失败；本方法通过 <机制> 消除该失败。"写不出即不通过。
2. **可证伪性检验**：能否设计一个实验，结果为 X 则 idea 直接被否定？
   不可证伪的 idea（怎么解释都通）没有科学内容。
3. **最小性检验**：想象消融——去掉核心创新组件后性能应显著下降。
   若预期"去掉也差不多"，创新点是伪贡献。
4. **反事实检验**：若实验结论恰好相反，原 motivation 是否同样"讲得通"？
   两边都讲得通说明 motivation 是事后叙事，不含预测力。

每项给 pass / weak / fail + 一句依据。**两项及以上 fail → 直接判缝合，跳到输出。**

## 第二层：领域直觉体检（读取领域模块）

从 `domains/<领域>.md` 的"已知陷阱"与"增益来源审查"清单逐条核对，典型问题：

- 是否撞已知陷阱（如时序领域：复杂结构 vs 线性基线之问、归一化/窗口泄漏、小数据集过拟合假象、分布漂移敏感）？
- 预期增益来源是否可信：来自机制本身，还是可能来自调参余地、随机种子、不公平对比？
- 与领域近期共识的关系：顺势增量（CCF-A 相弱）还是挑战默认假设（强，但需更硬的证据）？
- 计算/数据代价是否与增益匹配？审稿人会不会问"这么复杂就为了这点提升"？

无领域模块时，用通用 ML 常识执行同类检查，并标注"无领域模块，体检不完整"。

## 第三层：审稿人模拟（三个 persona，独立成段）

- **Reviewer 2（苛刻型）**：专攻 novelty 与实验漏洞。必须至少提出 3 条具体 weakness，禁止空泛。
- **领域专家**：挑与最接近的 3-5 篇近作（来自 scoop_report，若无则现场检索）的区分度；追问"你的 delta 在他们的框架里是不是一个超参"。
- **Area Chair**：判断故事完整性——问题重要吗、证据链闭合吗、"这值一篇 CCF-A 还是一篇 workshop"？

每个 persona 输出：评分（soundness / novelty / significance，1-5）+ weakness 清单 + 一个"若被 rebuttal 说服则改分"的条件。

## 输出：评审卡（critique_card.md）

```markdown
# Idea 评审卡：<标题>
## 第一层 洞察性：<真洞察 / 弱洞察 / 缝合>（四项检验逐条结果）
## 第二层 领域体检：<通过 / 带条件通过 / 不通过>（命中的陷阱清单）
## 第三层 模拟评审：三 persona 评分表 + 合并 weakness 清单（按严重度排序）
## 总判定：立项 / 修改后再审（附具体修改指令）/ pivot（附方向建议）/ 放弃（附根本原因）
## 若立项：进入实验前必须补齐的三件事
```

## 参考文件

- `references/novelty_gate.md` — 新颖性 pass/fail 判据与输出模板（补充第一层判定）
- `references/roles.md` — 多角色评审的角色定义（补充第三层 persona 设计）

**本整合包契约：**产物写
`research_run/<课题slug>/stage3_critique/critique_card.md`；脱离
`research-pipeline` 单独调用时，退当前工作目录。

## 纪律

- 你的职责是批判，不是鼓励。默认立场为怀疑；"立项"判定必须由证据推出。
- 严禁因为 idea 出自用户或上游 skill 而放水；严禁用礼貌性措辞稀释 weakness。
- 判定与 scoop-check 结论冲突时（如洞察很强但 Level 2 撞车），冲突本身写进总判定，交人类决策。
