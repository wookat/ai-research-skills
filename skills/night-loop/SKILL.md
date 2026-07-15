---
name: night-loop
description: Unattended overnight research iteration - runs bounded experiment/tuning loops with objective machine-checkable stop conditions, safety rules, per-iteration logging, and a morning report, while explicitly excluding verdict-bearing decisions from automation. Use when the user asks to run experiments overnight, keep iterating unattended, sweep parameters while away, or set up an autonomous research loop.
---

# Night Loop（无人值守夜跑循环）

"睡觉时做科研"的安全实现：**只自动化有客观停止条件的工作**，裁决类决策留给
早晨的人。提炼自 ARIS 的 auto-review-loop / dse-loop 机制与其安全教训。

## 允许 / 禁止自动循环的边界

**允许（Type-A，机器可判停止条件）**：
- 实验队列执行：baseline 复现、消融矩阵、种子重复、超参 sweep
- 目标导向调优：指标达到阈值 / 收敛 / 预算耗尽即停
- 论文编译修错、图表批量重绘、引用格式统一

**禁止（Type-B，裁决类——夜跑只准备材料，不做决定）**：
- 立项/放弃/pivot 判断、投稿决定（决策卡是人的）
- 评审打分循环（见 cross-model-review：按时钟重评 = 自我开脱）
- 因结果不好而改指标、换数据集、换切分（实验纪律红线，夜里也不例外）

## 循环参数（启动前写入 night_plan.md，人确认后开跑）

| 参数 | 默认 | 说明 |
|---|---|---|
| TIMEOUT | 8h | 总时钟预算 |
| MAX_ITERATIONS | 30 | 评估的配置/实验数上限 |
| PATIENCE | 8 | 连续无改进即早停 |
| OBJECTIVE | 领域模块指标 | 必须机器可判（如 val MSE） |

## 安全铁律

- 禁止：`sudo`、递归删除、删除非本会话创建的文件、覆盖未读过的源文件、
  任何 git push/reset、杀死非本会话启动的进程。需要其中任何一项 → 停止并留言。
- 每次迭代前检查磁盘/显存余量；资源不足优雅收尾而不是崩掉半夜的队列。
- 崩溃可恢复：迭代状态落盘（`night_runs/<日期>/state.json`），重启后从断点续跑。

## 每迭代日志（night_runs/<日期>/iteration_log.md）

`迭代号 | 改动的唯一变量 | 预期 | 实际指标 | 判定（改进/退化/持平）| 下一步依据`。
一次只改一个变量的纪律在无人值守时同样生效。

## 晨报（morning_report.md，人醒来后 5 分钟能读完）

1. 总览：跑了多少实验、最优配置与指标、对比昨晚基线的 delta
2. 证实/证伪的假设（挂回 hypothesis_tree.md 对应节点）
3. 异常与失败（含日志路径），未消耗完预算的原因
4. **待裁决事项**：夜里准备好材料但需要人拍板的 Type-B 决定（格式同决策卡）

## 与流水线的关系

night-loop 只在阶段 4（experiment-loop）内部使用；启动前必须已有获批的
决策卡 #2（立项）。晨报中的显著结论按流程走决策卡 #3。
