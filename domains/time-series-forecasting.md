# 领域模块：时序预测（Time-Series Forecasting）

被各 skill 读取的领域知识注入文件。内容随领域进展需定期更新（建议每 1-2 月核对一次 SOTA 与在审论文）。

## 实验底座

- 首选 [thuml/Time-Series-Library (TSLib)](https://github.com/thuml/Time-Series-Library)：
  统一的数据加载、训练与评测框架，内置主流模型实现，社区公认的公平对比基础。
- 新方法以 TSLib 模型接口实现，保证与 baseline 共享全部训练/评测代码路径。

## 标准数据集（长序列预测主线）

| 数据集 | 变量数 | 粒度 | 备注 |
|---|---|---|---|
| ETTh1/ETTh2/ETTm1/ETTm2 | 7 | 时/分 | 最常用但小，单独在 ETT 上的结论不可信 |
| Weather | 21 | 10min | |
| Electricity (ECL) | 321 | 时 | 变量多，考验通道建模 |
| Traffic | 862 | 时 | 变量最多、最难 |
| Exchange | 8 | 日 | 近随机游走，深度模型常输给 naive；慎用作主证据 |
| ILI | 7 | 周 | 极小，仅作补充 |
| Solar-Energy | 137 | 10min | |

短序列/概率预测另有 M4、M5、GIFT-Eval、Monash 库；根据任务设定选用。

## 评测协议（冻结项）

- 指标：MSE / MAE（z-score 归一化后计算——注意不同论文归一化口径不一致是复现偏差主因）
- 预测长度：{96, 192, 336, 720}；lookback 统一（96 或统一调优并对 baseline 同等调优——
  lookback 不一致是该领域最常见的不公平对比）
- 切分：train/val/test = 7:1:2（ETT 为 6:2:2），按时间顺序，禁止随机切分
- 报 ≥3 随机种子均值±标准差（std）；n=3 不报 p 值（见 statistical-testing 的小样本规则）

## 必比 baseline 清单（2026 年时点，使用前核对最新 SOTA）

- 简单基线（**必须包含**，领域教训）：DLinear、NLinear、朴素重复（last-value / seasonal-naive）
- Transformer 系：iTransformer、PatchTST、FEDformer、Autoformer
- 非 Transformer：TimesNet、TiDE、TSMixer、SegRNN
- 基础模型（若相关设定）：TimesFM、Chronos、Moirai、Time-MoE
- 检索最近两届 NeurIPS/ICLR/ICML/KDD 的时序 oral/spotlight 补充最新 SOTA

## 已知陷阱（idea-critic / experiment-loop 逐条核对）

1. **DLinear 之问**：复杂结构常打不过线性模型（Zeng et al., AAAI 2023）。任何新架构必须先回答"为什么线性不够"。
2. **数据泄漏**：归一化统计量用了 test 段；lookback 窗口跨切分边界；早停用了 test 指标。
3. **小数据过拟合假象**：仅在 ETT 上的提升大概率是噪声；主结论必须覆盖 Traffic/Electricity 级别数据集。
4. **不公平 lookback**：自己用 512、baseline 用 96。
5. **分布漂移**：train/test 分布差异大（尤其 Exchange/ILI），提升可能来自对漂移的偶然适应；建议做时间上的滚动评测验证稳健性。
6. **提升幅度 vs 方差**：该领域 SOTA 间差距常在 1-3%，小于种子方差的"提升"无意义。
7. **通道独立 vs 混合之争**：PatchTST（独立）与 iTransformer（混合）结论在不同数据集上互斥——这是活跃的矛盾格，也是撞车高发区。
8. **Drop-last 陷阱**：test loader 的 drop_last=True 会截断测试集导致不可比（TFB, VLDB 2024 指出）；务必 drop_last=False。

## 增益来源审查清单

新方法提升必须归因到机制：做"机制关闭"消融、跨数据集一致性检查、
与"同参数量的加宽 baseline"对比（排除纯容量增益）、与"同训练预算的调参 baseline"对比。

## 研究路线图谱（3447 篇论文实证，2021–2026）

`references/ts-forecasting-survey/` 收录一份基于 3447 篇时序预测论文
（2021–2026，含 CCF 分级与年份热度）的领域统计，是本模块拥挤区/空白区判断的证据基础：

- `route_summary.md` — 17 条技术路线的"研究思路—模型—改进—趋势"四段式总结
  + 代表性论文 + 年份热度曲线（阶段0 缺口挖掘、阶段1 构思的首要输入）
- `type_summary.md` — 模型范式/任务类型/应用领域/CCF 等级的分布统计
- `comprehensive_report.md` — 全量论文清单（标题/摘要/创新点，scoop-check
  的本地 prior-art 初筛库，先查这里再上线上检索）

按论文数的拥挤度梯度（撞车风险 ∝ 论文数，机会 ∝ 热度上升且基数小）：

| 梯度 | 路线（论文数） | 判读 |
|---|---|---|
| 高度拥挤 | 通道/变量关系建模(1222)、Transformer 注意力改进(1022)、时序分解(903)、线性/MLP 极简(747) | 增量改进难过审稿人阈值，需真机制洞察 |
| 拥挤但仍活跃 | GNN/时空(971)、SSM/Mamba/RNN(647)、LLM/基础模型(499，2024 起爆发) | 需与最新 SOTA 明确区分 |
| 中等 | Patch/Token 化(386)、频率/小波(372)、Conformal/不确定性(350)、在线/持续学习(335)、因果/XAI(281) | 有空间，选好切入角 |
| 低基数上升区 | 扩散/生成(209)、KAN/神经算子(32)、检索增强 RAG-TS(51) | 机会区，但需论证必要性而非追新 |

**使用规则**：该统计截止 2026 年（自动关键词匹配，可能少量误判）；
idea-mining / literature-gap-mining 引用它判断拥挤度时必须注明数据时点，
最终撞车判定仍以 scoop-check 线上检索 + arxiv-radar 增量监控为准。

## 拥挤区警告（撞车高危，2026 年时点）

- 通用 patch/分解/频域 Transformer 变体（已饱和；实证：注意力改进 1022 篇、分解 903 篇）
- 通道独立 vs 交互的通用变体（变量关系建模 1222 篇，为最大拥挤区）
- LLM-for-TS 提示工程类（爆发后已现疲态，审稿人阈值极高）
- 时序基础模型预训练（大厂主导，学术单兵难有算力优势）
相对空地：分布漂移下的稳健预测、变量间因果/物理约束、不规则采样（Irregular TS 任务占 8.4% 但方法少）、
多分辨率联合建模、预测不确定性的可用性（决策下游）、检索增强与 KAN/神经算子等低基数上升区
——使用前用 scoop-check 现场核实。

## 目标会议（CCF-A，时序常投）

NeurIPS / ICML / ICLR（方法创新）、KDD / WWW(CCF-A) / VLDB（数据挖掘叙事+大规模实验）、
AAAI / IJCAI（相对友好）。按 idea 的"方法 vs 应用"倾向选择叙事框架。
