# 2021–2026 时序预测论文研究路线总结

基于《TS_Forecasting_2021_2026_Comprehensive_Report.md》共 **3447** 篇论文的标题、摘要和创新点，归纳主要技术路线如下。

> 说明：以下路线按「研究思路—使用模型—改进方向—发展趋势」四段式描述；同一篇论文可能同时属于多条路线。

## 1. 时序分解（Seasonal-Trend Decomposition）

**匹配论文数**：903

**主要怎么做（研究思路）**：将时间序列分解为趋势、季节、残差分量，分别建模再融合。

**使用什么模型**：Autoformer、N-BEATS、N-HiTS、FEDformer、TimesNet、TSDEcomp、MICN、Scaleformer 等。

**怎么改进 / 解决了什么问题**：缓解复杂混合模式导致建模困难的问题，增强对长期依赖和周期变化的捕捉；改进包括自动学习基函数、显式周期建模、多尺度分解。

**发展方向 / 趋势**：从 handcrafted 分解走向数据驱动/端到端分解，与 Transformer、MLP、State Space 结合。

**代表性论文**：
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 ICLR 2026 | GTR: Enhancing Multivariate Time Series Forecasting with Global Temporal Retrieval | [paper](https://arxiv.org/abs/2602.10847)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | ReCast: Reliability-aware Codebook Assisted Lightweight Time Series Forecasting | [paper](https://arxiv.org/pdf/2511.11991)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 AAAI 2026 | interPDN: Time Series Forecasting via Direct Per-Step Probability Distribution Modeling | [paper](https://arxiv.org/abs/2511.23260)
- 2026 KDD 2026 | LoFT-LLM: Low-Frequency Time-series Forecasting with Large Language Models | [paper](https://arxiv.org/abs/2512.20002)
- 2026 KDD 2026 | Under-Cali: Online Irregular Multivariate Time Series Forecasting via Uncertainty-Driven Dual-Expert Calibration | [paper](https://arxiv.org/abs/2605.28603)

**年份热度**：2021: 76, 2022: 104, 2023: 156, 2024: 197, 2025: 245, 2026: 125

## 2. Patch / Token 化表示

**匹配论文数**：386

**主要怎么做（研究思路）**：把序列切分为 patch 或 token，借鉴 NLP/CV 的序列/块表示方式。

**使用什么模型**：PatchTST、TimesNet（2D 视图）、ModernTCN、Koopa、SOFTS、RLinear。

**怎么改进 / 解决了什么问题**：通过局部块内建模降低复杂度、保留语义，PatchTST 证明 channel-independence + patching 可优于复杂 Transformer；后续改进块大小自适应、跨 patch 关系建模。

**发展方向 / 趋势**：从点/单步表示转向局部块表示，并与通道独立、频率分析结合。

**代表性论文**：
- 2026 ICLR 2026 | GTR: Enhancing Multivariate Time Series Forecasting with Global Temporal Retrieval | [paper](https://arxiv.org/abs/2602.10847)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | ReCast: Reliability-aware Codebook Assisted Lightweight Time Series Forecasting | [paper](https://arxiv.org/pdf/2511.11991)
- 2026 KDD 2026 | From Tokenizer Bias to Backbone Capability: A Controlled Study of LLMs for Time Series Forecasting | [paper](https://arxiv.org/abs/2504.08818)
- 2026 KDD 2026 | LoFT-LLM: Low-Frequency Time-series Forecasting with Large Language Models | [paper](https://arxiv.org/abs/2512.20002)
- 2026 KDD 2026 | SARAF: Stationarity-Aware Retrieval-Augmented Time Series Forecasting | [paper](https://arxiv.org/abs/2606.04135)
- 2026 WWW 2026 | SEMixer: Semantics Enhanced MLP-Mixer for Multiscale Mixing and Long-term Time Series Forecasting | [paper](https://arxiv.org/abs/2602.16220)
- 2026 WWW 2026 | Time-TK: A Multi-Offset Temporal Interaction Framework Combining Transformer and Kolmogorov-Arnold Networks for Time Series Forecasting | [paper](https://arxiv.org/abs/2602.11190)

**年份热度**：2021: 4, 2022: 14, 2023: 37, 2024: 92, 2025: 151, 2026: 88

## 3. Transformer 注意力机制改进

**匹配论文数**：1022

**主要怎么做（研究思路）**：在 Transformer 基础上设计更适合时间序列的注意力，降低复杂度并提升长序列建模能力。

**使用什么模型**：Informer（ProbSparse）、Autoformer（Auto-Correlation）、FEDformer（Fourier Enhancement）、Crossformer（Cross-Dim/Time）、iTransformer（Channel-wise）。

**怎么改进 / 解决了什么问题**：从全连接自注意力 → 稀疏/低秩/频域/自动相关注意力，再到「倒置」Transformer 把变量维当 token，以更好建模多变量关联。

**发展方向 / 趋势**：注意力设计从时间维转向变量维；与 MLP/线性模型竞争，逐步收敛为「必要才用注意力」。

**代表性论文**：
- 2026 ICML 2026 | PRO-DYN: Time Series Forecasting Through the Lens of Dynamics | [paper](https://arxiv.org/abs/2507.15774)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | CometNet: Contextual Motif-guided Long-term Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08049)
- 2026 AAAI 2026 | EMAformer: Enhancing Transformer through Embedding Armor for Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08396)
- 2026 AAAI 2026 | PFRP: Predicting the Future by Retrieving the Past | [paper](https://arxiv.org/abs/2511.05859)
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 KDD 2026 | TimeDistill: Efficient Long-Term Time Series Forecasting with MLP via Cross-Architecture Distillation | [paper](https://arxiv.org/abs/2502.15016)

**年份热度**：2021: 38, 2022: 83, 2023: 159, 2024: 264, 2025: 331, 2026: 147

## 4. 线性 / MLP 极简路线

**匹配论文数**：747

**主要怎么做（研究思路）**：用单个或少层线性/MLP 直接建模时间维，质疑 Transformer 的必要性。

**使用什么模型**：DLinear、NLinear、RLinear、TSMixer、FITS、SegRNN、Koopa。

**怎么改进 / 解决了什么问题**：参数极少、训练快、长程预测强；改进包括通道混合、频率域线性、变量交互、自适应归一化。

**发展方向 / 趋势**：推动领域反思「到底需要多复杂的模型」，并催生出对组件级归因（CombinationTS）和结构先验的研究。

**代表性论文**：
- 2026 ICML 2026 | PRO-DYN: Time Series Forecasting Through the Lens of Dynamics | [paper](https://arxiv.org/abs/2507.15774)
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | CometNet: Contextual Motif-guided Long-term Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08049)
- 2026 AAAI 2026 | EMAformer: Enhancing Transformer through Embedding Armor for Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08396)
- 2026 AAAI 2026 | PFRP: Predicting the Future by Retrieving the Past | [paper](https://arxiv.org/abs/2511.05859)
- 2026 KDD 2026 | SARAF: Stationarity-Aware Retrieval-Augmented Time Series Forecasting | [paper](https://arxiv.org/abs/2606.04135)
- 2026 KDD 2026 | TimeDistill: Efficient Long-Term Time Series Forecasting with MLP via Cross-Architecture Distillation | [paper](https://arxiv.org/abs/2502.15016)

**年份热度**：2021: 66, 2022: 87, 2023: 127, 2024: 173, 2025: 190, 2026: 104

## 5. 通道 / 变量关系建模

**匹配论文数**：1222

**主要怎么做（研究思路）**：专门研究多变量预测中「变量间关系」该独立还是交互。

**使用什么模型**：iTransformer、PatchTST（独立）、SOFTS、GPPooler、MSGNet、Crossformer、TFB。

**怎么改进 / 解决了什么问题**：从全通道共享到通道独立，再到有选择/可学习的变量交互；解决过拟合、分布偏移和变量异质性问题。

**发展方向 / 趋势**：动态/稀疏/图结构化的变量关系建模成为重点。

**代表性论文**：
- 2026 ICML 2026 | CGTFra: Robust Inter-Series Dependency Modeling for Time Series Forecasting via Information-Theoretic Alignment | [paper](https://openreview.net/forum?id=YQPQuHVLLQ)
- 2026 ICML 2026 | DAG: A Dual Correlation Network for Time Series Forecasting with Exogenous Variables | [paper](https://arxiv.org/pdf/2509.14933)
- 2026 ICML 2026 | PPM: Parametric Prior Mapping Framework for Non-stationary Probabilistic Time Series Forecasting | [paper](https://arxiv.org/abs/2605.23402)
- 2026 ICLR 2026 | GTR: Enhancing Multivariate Time Series Forecasting with Global Temporal Retrieval | [paper](https://arxiv.org/abs/2602.10847)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | EMAformer: Enhancing Transformer through Embedding Armor for Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08396)
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)

**年份热度**：2021: 77, 2022: 140, 2023: 221, 2024: 267, 2025: 345, 2026: 172

## 6. 频率 / 小波 / 频谱分析

**匹配论文数**：681

**主要怎么做（研究思路）**：把序列变换到频域或小波域，显式建模周期/频率成分。

**使用什么模型**：FEDformer、FiLM、TimesNet、FreTS、WaveForM、ST-NCDE、Sonnet（Spectral Operator）。

**怎么改进 / 解决了什么问题**：利用频域稀疏性减少噪声干扰、捕获多尺度周期；改进包括自适应频率选择、混合时频特征、小波多分辨率。

**发展方向 / 趋势**：与时域深度学习互补，尤其擅长季节性/周期性数据。

**代表性论文**：
- 2026 ICLR 2026 | GTR: Enhancing Multivariate Time Series Forecasting with Global Temporal Retrieval | [paper](https://arxiv.org/abs/2602.10847)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 KDD 2026 | LoFT-LLM: Low-Frequency Time-series Forecasting with Large Language Models | [paper](https://arxiv.org/abs/2512.20002)
- 2026 KDD 2026 | TimeDistill: Efficient Long-Term Time Series Forecasting with MLP via Cross-Architecture Distillation | [paper](https://arxiv.org/abs/2502.15016)
- 2026 KDD 2026 | Under-Cali: Online Irregular Multivariate Time Series Forecasting via Uncertainty-Driven Dual-Expert Calibration | [paper](https://arxiv.org/abs/2605.28603)
- 2026 ICDE 2026 | Effective Dataset Distillation for Spatio-Temporal Forecasting with Bi-dimensional Compression | [paper](https://arxiv.org/abs/2603.10410)

**年份热度**：2021: 58, 2022: 72, 2023: 94, 2024: 130, 2025: 206, 2026: 121

## 7. 图神经网络 / 时空预测

**匹配论文数**：1167

**主要怎么做（研究思路）**：用图结构显式建模变量/传感器之间的空间关系，并联合时间演化。

**使用什么模型**：STGNN、Graph WaveNet、AGCRN、DCRNN、Z-GCNETs、MTGNN、STGODE、GTS。

**怎么改进 / 解决了什么问题**：从预定义图到自适应图学习、动态图、解耦时空模块；在交通、传感器网络、电力网格上效果显著。

**发展方向 / 趋势**：与 Transformer、扩散模型、LLM 结合，走向大规模动态图预测。

**代表性论文**：
- 2026 ICLR 2026 | Tackling Time-Series Forecasting Generalization via Mitigating Concept Drift | [paper](https://openreview.net/forum?id=emkvZ7NanK)
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 AAAI 2026 | interPDN: Time Series Forecasting via Direct Per-Step Probability Distribution Modeling | [paper](https://arxiv.org/abs/2511.23260)
- 2026 KDD 2026 | From Tokenizer Bias to Backbone Capability: A Controlled Study of LLMs for Time Series Forecasting | [paper](https://arxiv.org/abs/2504.08818)
- 2026 KDD 2026 | SARAF: Stationarity-Aware Retrieval-Augmented Time Series Forecasting | [paper](https://arxiv.org/abs/2606.04135)
- 2026 KDD 2026 | STM3: Mixture of Multiscale Mamba for Long-Term Spatio-Temporal Time-Series Prediction | [paper](https://arxiv.org/abs/2508.12247)
- 2026 ICDE 2026 | Damba-ST: Domain-Adaptive Mamba for Efficient Urban Spatio-Temporal Prediction | [paper](https://arxiv.org/abs/2506.18939)

**年份热度**：2021: 82, 2022: 139, 2023: 196, 2024: 254, 2025: 312, 2026: 184

## 8. 状态空间 / Mamba / RNN 路线

**匹配论文数**：702

**主要怎么做（研究思路）**：用状态空间模型或长程 RNN 替代注意力，线性复杂度捕获长程依赖。

**使用什么模型**：Mamba（Vmamba/S5）、S4、RWKV、LSTM/GRU、DeepAR、SegRNN、S-Mixer。

**怎么改进 / 解决了什么问题**：O(L) 复杂度、稳定长序列建模；Mamba 凭借硬件感知扫描机制成为 Transformer 的有力替代。

**发展方向 / 趋势**：2024-2025 出现大量 Mamba-for-Time-Series 工作，强调效率与长上下文。

**代表性论文**：
- 2026 ICLR 2026 | Online time series prediction using feature adjustment | [paper](https://openreview.net/forum?id=s4U2FWEMTU)
- 2026 AAAI 2026 | CometNet: Contextual Motif-guided Long-term Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08049)
- 2026 KDD 2026 | How to Train Your Mamba for Time Series Forecasting | [paper](https://dl.acm.org/doi/10.1145/3770854.3780279)
- 2026 KDD 2026 | STM3: Mixture of Multiscale Mamba for Long-Term Spatio-Temporal Time-Series Prediction | [paper](https://arxiv.org/abs/2508.12247)
- 2026 ICDE 2026 | Damba-ST: Domain-Adaptive Mamba for Efficient Urban Spatio-Temporal Prediction | [paper](https://arxiv.org/abs/2506.18939)
- 2026 PAKDD 2026 | Bridging Statistical Seasonality and Diffusion-Based Deep Learning for Multivariate Time Series Forecasting | [paper](https://doi.org/10.1007/978-981-92-1947-6_4)
- 2025 ICML 2025 | TimePro: Efficient Multivariate Long-term Time Series Forecasting with Variable- and Time-Aware Hyper-state | [paper](https://arxiv.org/abs/2505.20774)
- 2025 Proceedings of the AAAI Conference on Artificial Intelligence 2025 | Affirm: Interactive Mamba with Adaptive Fourier Filters for Long-term Time Series Forecasting | [paper](https://ojs.aaai.org/index.php/AAAI/article/download/35463/37618)

**年份热度**：2021: 88, 2022: 103, 2023: 129, 2024: 163, 2025: 162, 2026: 57

## 9. 大语言模型 / 基础模型 / 零样本

**匹配论文数**：485

**主要怎么做（研究思路）**：把时序数据 token 化，利用预训练语言模型或专门时序基础模型进行通用预测。

**使用什么模型**：Time-LLM、TimeGPT、Chronos、Moirai、Time-MoE、Timer、LLM4TS、UniTS、TimesFM、UTSD。

**怎么改进 / 解决了什么问题**：通过大规模预训练获得跨数据集泛化能力，实现零样本/少样本预测；关键改进在于 tokenization、提示工程、混合分布、缩放规律。

**发展方向 / 趋势**：从「为每个数据集训练专用模型」转向「一个模型通用多领域」；2024-2025 爆发式增长。

**代表性论文**：
- 2026 ICML 2026 | It's TIME: Towards the Next Generation of Time Series Forecasting Benchmarks | [paper](https://arxiv.org/abs/2602.12147)
- 2026 ICML 2026 | MemCast: Memory-Driven Time Series Forecasting with Experience-Conditioned Reasoning | [paper](https://arxiv.org/abs/2602.03164)
- 2026 ICLR 2026 | Semantic-Enhanced Time-Series Forecasting via Large Language Models | [paper](https://openreview.net/forum?id=GZ9uSxY3Yn)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 KDD 2026 | From Tokenizer Bias to Backbone Capability: A Controlled Study of LLMs for Time Series Forecasting | [paper](https://arxiv.org/abs/2504.08818)
- 2026 KDD 2026 | LoFT-LLM: Low-Frequency Time-series Forecasting with Large Language Models | [paper](https://arxiv.org/abs/2512.20002)
- 2026 KDD 2026 | TSCOMP: Beyond Holistic Models: Systematic Component-level Benchmarking of Deep Multivariate Time-Series Forecasting | [paper](https://arxiv.org/abs/2605.26562)
- 2026 KDD 2026 | TimeDistill: Efficient Long-Term Time Series Forecasting with MLP via Cross-Architecture Distillation | [paper](https://arxiv.org/abs/2502.15016)

**年份热度**：2021: 14, 2022: 14, 2023: 29, 2024: 113, 2025: 201, 2026: 114

## 10. 检索增强 / 外部记忆

**匹配论文数**：1232

**主要怎么做（研究思路）**：在推理或训练时检索相似历史序列/外部知识，增强预测。

**使用什么模型**：RAFT、TS-RAG、SARAF、PFRP、MemCast、TimeRAG、Retrieval Augmented Time Series Forecasting。

**怎么改进 / 解决了什么问题**：利用海量历史数据中的相似模式，提升零样本、非平稳和少样本场景；改进包括语义/时序混合检索、动态记忆更新。

**发展方向 / 趋势**：与 LLM 和基础模型天然契合，正成为提升泛化的重要方向。

**代表性论文**：
- 2026 ICML 2026 | CombinationTS: A Modular Framework for Understanding Time-Series Forecasting Models | [paper](https://arxiv.org/abs/2605.01231)
- 2026 ICML 2026 | DAG: A Dual Correlation Network for Time Series Forecasting with Exogenous Variables | [paper](https://arxiv.org/pdf/2509.14933)
- 2026 ICML 2026 | It's TIME: Towards the Next Generation of Time Series Forecasting Benchmarks | [paper](https://arxiv.org/abs/2602.12147)
- 2026 ICML 2026 | MemCast: Memory-Driven Time Series Forecasting with Experience-Conditioned Reasoning | [paper](https://arxiv.org/abs/2602.03164)
- 2026 ICLR 2026 | GTR: Enhancing Multivariate Time Series Forecasting with Global Temporal Retrieval | [paper](https://arxiv.org/abs/2602.10847)
- 2026 AAAI 2026 | EMAformer: Enhancing Transformer through Embedding Armor for Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08396)
- 2026 AAAI 2026 | PFRP: Predicting the Future by Retrieving the Past | [paper](https://arxiv.org/abs/2511.05859)
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)

**年份热度**：2021: 101, 2022: 147, 2023: 198, 2024: 289, 2025: 328, 2026: 169

## 11. 扩散 / 生成 / 概率模型

**匹配论文数**：410

**主要怎么做（研究思路）**：通过生成模型或概率分布建模，输出完整预测分布而非单点。

**使用什么模型**：TimeDiff、DPM、DSPD、CSDI、N-BEATS 概率版、DeepAR、NHiTS、TACTiS。

**怎么改进 / 解决了什么问题**：支持不确定性量化和风险决策；改进包括扩散加速、条件生成、多步一致性、分布校准。

**发展方向 / 趋势**：与基础模型结合，成为高风险管理场景（金融、能源）的关键技术。

**代表性论文**：
- 2026 ICML 2026 | CombinationTS: A Modular Framework for Understanding Time-Series Forecasting Models | [paper](https://arxiv.org/abs/2605.01231)
- 2026 ICML 2026 | MemCast: Memory-Driven Time Series Forecasting with Experience-Conditioned Reasoning | [paper](https://arxiv.org/abs/2602.03164)
- 2026 ICML 2026 | PPM: Parametric Prior Mapping Framework for Non-stationary Probabilistic Time Series Forecasting | [paper](https://arxiv.org/abs/2605.23402)
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 ICLR 2026 | DoFlow: Flow-based Generative Models for Interventional and Counterfactual Forecasting on Time Series | [paper](https://openreview.net/forum?id=4IPIhOgVqz)
- 2026 IJCAI 2026 | EVENTTSF: Event-Aware Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2508.13434)
- 2026 IJCAI 2026 | From Values to Tokens: An LLM-Driven Framework for Context-Aware Time Series Forecasting via Symbolic Discretization | [paper](https://arxiv.org/abs/2508.09191)
- 2026 PAKDD 2026 | Bridging Statistical Seasonality and Diffusion-Based Deep Learning for Multivariate Time Series Forecasting | [paper](https://doi.org/10.1007/978-981-92-1947-6_4)

**年份热度**：2021: 32, 2022: 46, 2023: 61, 2024: 87, 2025: 107, 2026: 77

## 12. 不确定性 / 置信区间 / 共形预测

**匹配论文数**：286

**主要怎么做（研究思路）**：在点预测之外给出可靠区间或概率分布，并校准不确定性。

**使用什么模型**：ConformalTS、EnbPI、NGBoost、MQRNN、ACI、QRNN、CQR。

**怎么改进 / 解决了什么问题**：解决深度学习预测过度自信问题；改进包括自适应分位数、共形预测、分布偏移下的区间修正。

**发展方向 / 趋势**：随着大模型应用，预测不确定性越来越受重视。

**代表性论文**：
- 2026 ICML 2026 | PPM: Parametric Prior Mapping Framework for Non-stationary Probabilistic Time Series Forecasting | [paper](https://arxiv.org/abs/2605.23402)
- 2026 ICLR 2026 | Flow-based Conformal Prediction for Multi-dimensional Time Series | [paper](https://openreview.net/forum?id=Uv3efQiPBZ)
- 2026 ICLR 2026 | ResCP: Reservoir Conformal Prediction for Time Series Forecasting | [paper](https://openreview.net/forum?id=WGqibe5H3W)
- 2026 AAAI 2026 | interPDN: Time Series Forecasting via Direct Per-Step Probability Distribution Modeling | [paper](https://arxiv.org/abs/2511.23260)
- 2026 KDD 2026 | LoFT-LLM: Low-Frequency Time-series Forecasting with Large Language Models | [paper](https://arxiv.org/abs/2512.20002)
- 2026 KDD 2026 | Under-Cali: Online Irregular Multivariate Time Series Forecasting via Uncertainty-Driven Dual-Expert Calibration | [paper](https://arxiv.org/abs/2605.28603)
- 2026 IJCAI 2026 | EVENTTSF: Event-Aware Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2508.13434)
- 2025 ICML 2025 | K² VAE: A Koopman-Kalman Enhanced Variational AutoEncoder for Probabilistic Time Series Forecasting | [paper](https://arxiv.org/abs/2505.23017)

**年份热度**：2021: 23, 2022: 24, 2023: 38, 2024: 47, 2025: 88, 2026: 66

## 13. 非平稳 / 分布偏移 / 在线适应

**匹配论文数**：636

**主要怎么做（研究思路）**：针对真实数据分布随时间变化的问题，设计动态适应机制。

**使用什么模型**：Non-stationary Transformer、DLinear + RevIN、OCB、PPM、PULSE、ADAPT、Domain Adaptation 系列。

**怎么改进 / 解决了什么问题**：RevIN 归一化、自适应参数更新、阶段演化、在线学习、源域/目标域迁移。

**发展方向 / 趋势**：从「训练-测试同分布」假设走向持续学习与动态适应。

**代表性论文**：
- 2026 ICML 2026 | MemCast: Memory-Driven Time Series Forecasting with Experience-Conditioned Reasoning | [paper](https://arxiv.org/abs/2602.03164)
- 2026 ICML 2026 | PPM: Parametric Prior Mapping Framework for Non-stationary Probabilistic Time Series Forecasting | [paper](https://arxiv.org/abs/2605.23402)
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 ICLR 2026 | Delta-XAI: A Unified Framework for Explaining Prediction Changes in Online Time Series Monitoring | [paper](https://openreview.net/forum?id=ZHW5pp5nE5)
- 2026 ICLR 2026 | Online time series prediction using feature adjustment | [paper](https://openreview.net/forum?id=s4U2FWEMTU)
- 2026 ICLR 2026 | Tackling Time-Series Forecasting Generalization via Mitigating Concept Drift | [paper](https://openreview.net/forum?id=emkvZ7NanK)
- 2026 AAAI 2026 | ReCast: Reliability-aware Codebook Assisted Lightweight Time Series Forecasting | [paper](https://arxiv.org/pdf/2511.11991)
- 2026 KDD 2026 | SARAF: Stationarity-Aware Retrieval-Augmented Time Series Forecasting | [paper](https://arxiv.org/abs/2606.04135)

**年份热度**：2021: 48, 2022: 74, 2023: 90, 2024: 135, 2025: 171, 2026: 118

## 14. 因果 / 可解释 / XAI

**匹配论文数**：319

**主要怎么做（研究思路）**：揭示模型为何做出预测，并在预测中引入因果/反事实推理。

**使用什么模型**：Causal-TSF、Delta-XAI、CausalFS、SHAP/LIME 应用、TimeSHAP、CausalTime。

**怎么改进 / 解决了什么问题**：减少虚假相关、提高可信度；改进包括因果干预、结构因果模型、反事实样本生成。

**发展方向 / 趋势**：在高风险领域（医疗、金融）需求日益增长。

**代表性论文**：
- 2026 ICML 2026 | CombinationTS: A Modular Framework for Understanding Time-Series Forecasting Models | [paper](https://arxiv.org/abs/2605.01231)
- 2026 ICLR 2026 | Delta-XAI: A Unified Framework for Explaining Prediction Changes in Online Time Series Monitoring | [paper](https://openreview.net/forum?id=ZHW5pp5nE5)
- 2026 ICLR 2026 | DoFlow: Flow-based Generative Models for Interventional and Counterfactual Forecasting on Time Series | [paper](https://openreview.net/forum?id=4IPIhOgVqz)
- 2026 AAAI 2026 | PFRP: Predicting the Future by Retrieving the Past | [paper](https://arxiv.org/abs/2511.05859)
- 2026 KDD 2026 | STM3: Mixture of Multiscale Mamba for Long-Term Spatio-Temporal Time-Series Prediction | [paper](https://arxiv.org/abs/2508.12247)
- 2026 PAKDD 2026 | Channel Dependence, Limited Lookback Windows, and the Simplicity of Datasets: How Biased is Time Series Forecasting? | [paper](https://arxiv.org/pdf/2502.09683)
- 2026 AISTATS 2026 | Time Series Forecasting with Hahn Kolmogorov-Arnold Networks | [paper](https://arxiv.org/abs/2601.18837)
- 2025 ICML 2025 | Exploring Representations and Interventions in Time Series Foundation Models | [paper](https://arxiv.org/abs/2409.12915)

**年份热度**：2021: 22, 2022: 26, 2023: 48, 2024: 57, 2025: 93, 2026: 73

## 15. KAN / 神经算子 / 函数空间

**匹配论文数**：48

**主要怎么做（研究思路）**：用 KAN、神经算子或谱算子在函数/算子层面建模时序动态。

**使用什么模型**：TimeKAN、KAN4TS、Sonnet、FNO 变体、DeepONet。

**怎么改进 / 解决了什么问题**：提供可解释的非线性组合与连续函数逼近能力；仍处探索阶段。

**发展方向 / 趋势**：2024-2025 新兴，尚待大规模验证。

**代表性论文**：
- 2026 AAAI 2026 | Sonnet: Spectral Operator Neural Network for Multivariable Time Series Forecasting | [paper](https://arxiv.org/abs/2505.15312)
- 2026 WWW 2026 | Time-TK: A Multi-Offset Temporal Interaction Framework Combining Transformer and Kolmogorov-Arnold Networks for Time Series Forecasting | [paper](https://arxiv.org/abs/2602.11190)
- 2026 PAKDD 2026 | DDCG: Dual-granularity Dual-domain Collaborative Graph Neural Networks for Time Series Forecasting | [paper](https://researchr.org/publication/pakdd-2026-1)
- 2026 AISTATS 2026 | Time Series Forecasting with Hahn Kolmogorov-Arnold Networks | [paper](https://arxiv.org/abs/2601.18837)
- 2025 ICLR 2025 | TimeKAN: KAN-based Frequency Decomposition Learning Architecture for Long-term Time Series Forecasting | [paper](https://openreview.net/pdf?id=wTLc79YNbh)
- 2025 Proceedings of the AAAI Conference on Artificial Intelligence 2025 | Affirm: Interactive Mamba with Adaptive Fourier Filters for Long-term Time Series Forecasting | [paper](https://ojs.aaai.org/index.php/AAAI/article/download/35463/37618)
- 2025 PAKDD 2025 | SplineFormer: Improving Time Series Forecasting with Kolmogorov-Arnold Networks and Enhanced ProbSparse Self-Attention | [paper](https://researchr.org/publication/ZengYQGC25)
- 2026 arXiv 2026 | Autocorrelation Reintroduces Spectral Bias in KANs for Time Series Forecasting | [paper](https://arxiv.org/abs/2604.23518)

**年份热度**：2021: 2, 2022: 1, 2023: 1, 2024: 13, 2025: 22, 2026: 9

## 16. 数据增强 / 合成 / 自动机器学习

**匹配论文数**：367

**主要怎么做（研究思路）**：通过生成或增强数据，改善小样本、低质量或稀缺数据预测。

**使用什么模型**：TimeGAN、GT-GAN、TimePFN、SigAug、Auto-Sktime、TSMix。

**怎么改进 / 解决了什么问题**：提升样本多样性、缓解过拟合；改进包括条件生成、保持时序结构、自动增强策略。

**发展方向 / 趋势**：与基础模型训练数据构建紧密相关。

**代表性论文**：
- 2026 ICML 2026 | It's TIME: Towards the Next Generation of Time Series Forecasting Benchmarks | [paper](https://arxiv.org/abs/2602.12147)
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 AAAI 2026 | PFRP: Predicting the Future by Retrieving the Past | [paper](https://arxiv.org/abs/2511.05859)
- 2026 KDD 2026 | SARAF: Stationarity-Aware Retrieval-Augmented Time Series Forecasting | [paper](https://arxiv.org/abs/2606.04135)
- 2026 KDD 2026 | TSCOMP: Beyond Holistic Models: Systematic Component-level Benchmarking of Deep Multivariate Time-Series Forecasting | [paper](https://arxiv.org/abs/2605.26562)
- 2026 KDD 2026 | TimeDistill: Efficient Long-Term Time Series Forecasting with MLP via Cross-Architecture Distillation | [paper](https://arxiv.org/abs/2502.15016)
- 2026 WWW 2026 | QuiZSF: A Retrieval-Augmented Framework for Zero-Shot Time Series Forecasting | [paper](https://arxiv.org/abs/2508.06915)
- 2026 IJCAI 2026 | EVENTTSF: Event-Aware Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2508.13434)

**年份热度**：2021: 20, 2022: 46, 2023: 50, 2024: 73, 2025: 99, 2026: 79

## 17. 基准 / 评测 / 工具库

**匹配论文数**：1047

**主要怎么做（研究思路）**：建立统一评测标准、数据集、评测框架和开源库。

**使用什么模型**：Time-Series-Library (TSlib)、TFB、Chronos、Moirai、Monash Forecasting Repository、CombinationTS、TIME。

**怎么改进 / 解决了什么问题**：规范实验流程、统一数据切分、公平比较；推动领域从模型堆砌转向组件级归因。

**发展方向 / 趋势**：基础模型时代，评测基准的重要性进一步提升。

**代表性论文**：
- 2026 ICML 2026 | CombinationTS: A Modular Framework for Understanding Time-Series Forecasting Models | [paper](https://arxiv.org/abs/2605.01231)
- 2026 ICML 2026 | It's TIME: Towards the Next Generation of Time Series Forecasting Benchmarks | [paper](https://arxiv.org/abs/2602.12147)
- 2026 ICML 2026 | PULSE: Generative Phase Evolution for Non-Stationary Time Series Forecasting | [paper](https://arxiv.org/abs/2605.16793)
- 2026 ICLR 2026 | MixLinear: Extreme Low-Resource Multivariate Time Series Forecasting with 0.1K Parameters | [paper](https://arxiv.org/abs/2410.02081)
- 2026 AAAI 2026 | EMAformer: Enhancing Transformer through Embedding Armor for Time Series Forecasting | [paper](https://arxiv.org/abs/2511.08396)
- 2026 AAAI 2026 | T3Time: Tri-Modal Time Series Forecasting via Adaptive Multi-Head Alignment and Residual Fusion | [paper](https://arxiv.org/abs/2508.04251)
- 2026 KDD 2026 | STM3: Mixture of Multiscale Mamba for Long-Term Spatio-Temporal Time-Series Prediction | [paper](https://arxiv.org/abs/2508.12247)
- 2026 KDD 2026 | TSCOMP: Beyond Holistic Models: Systematic Component-level Benchmarking of Deep Multivariate Time-Series Forecasting | [paper](https://arxiv.org/abs/2605.26562)

**年份热度**：2021: 63, 2022: 83, 2023: 126, 2024: 207, 2025: 336, 2026: 232

---

# 综合发展趋势

1. **模型复杂度**正在经历「复杂 Transformer → 极简线性/MLP → 结构必要性的反思」的循环，催生组件级归因（CombinationTS）和模块化框架。
2. **多变量关系建模**从「全通道共享」走向「通道独立 + 选择性交互」，再到基于图/注意力/变量token的动态关系学习。
3. **长序列与效率**推动 State Space / Mamba、线性模型、频域方法和稀疏注意力的快速发展。
4. **预训练与基础模型**（Chronos、Moirai、Time-MoE、Timer）和 **大语言模型重编程**（Time-LLM）正重塑时序预测范式，向统一、零样本、跨领域泛化演进。
5. **可信预测**：不确定性量化、共形预测、因果推断、可解释性在高风险应用（金融、医疗、能源）中愈发重要。
6. **数据与评测**：高质量公开基准、大规模预训练数据集和公平评测体系成为基础模型时代的核心基础设施。

> 注：路线划分基于关键词自动匹配，存在一定误差；代表性论文按 CCF 等级与年份优先展示。