# 2021–2026 时序预测论文类型总结

基于《TS_Forecasting_2021_2026_Comprehensive_Report.md》共 **3447** 篇论文的标题、摘要与创新点进行自动分类。

## 一、年份分布

| 年份 | 数量 |
|------|------|
| 2026 | 420 |
| 2025 | 893 |
| 2024 | 760 |
| 2023 | 592 |
| 2022 | 429 |
| 2021 | 353 |

## 二、模型/方法范式

| 类型 | 数量 | 占比 |
|------|------|------|
| Transformer / Attention | 1044 | 13.9% |
| Graph Neural Network | 971 | 12.9% |
| Benchmark / Survey / Library | 830 | 11.0% |
| MLP / Linear | 666 | 8.8% |
| State Space / Mamba / RNN | 647 | 8.6% |
| Random Forest / Boosting / Classical ML | 522 | 6.9% |
| Large Language / Foundation Model | 499 | 6.6% |
| Other / Unclear | 482 | 6.4% |
| Frequency / Wavelet / Spectral | 372 | 4.9% |
| Conformal / Uncertainty Quantification | 350 | 4.6% |
| Reinforcement / Online / Continual | 335 | 4.4% |
| Causal / Interpretable / XAI | 281 | 3.7% |
| Diffusion / Generative | 209 | 2.8% |
| Anomaly / Imputation / General TS | 126 | 1.7% |
| Kernel / Gaussian Process | 117 | 1.6% |
| Retrieval-Augmented | 51 | 0.7% |
| KAN / Kolmogorov-Arnold | 32 | 0.4% |

> 注：单篇论文可能同时命中多种模型标签，因此总数（7534）会大于论文总数。

### 模型-年份交叉 Top 类型

| 模型类型 | 2026 | 2025 | 2024 | 2023 | 2022 | 2021 |
|---|---|---|---|---|---|---|
| Transformer / Attention | 152 | 339 | 266 | 166 | 83 | 38 |
| Graph Neural Network | 155 | 263 | 222 | 158 | 106 | 67 |
| Benchmark / Survey / Library | 208 | 278 | 159 | 91 | 57 | 37 |
| MLP / Linear | 96 | 176 | 156 | 105 | 75 | 58 |
| State Space / Mamba / RNN | 52 | 149 | 154 | 116 | 96 | 80 |
| Random Forest / Boosting / Classical ML | 33 | 110 | 99 | 93 | 100 | 87 |
| Large Language / Foundation Model | 115 | 230 | 111 | 33 | 7 | 3 |
| Other / Unclear | 21 | 57 | 93 | 110 | 97 | 104 |

## 三、任务/问题类型

| 任务类型 | 数量 | 占比 |
|----------|------|------|
| General Forecasting | 1096 | 22.3% |
| Multivariate Forecasting | 755 | 15.3% |
| Short-term / Nowcasting | 711 | 14.4% |
| Long-term Forecasting | 667 | 13.6% |
| Irregular / Event / Sparse TS | 412 | 8.4% |
| Zero-shot / Transfer / Few-shot | 369 | 7.5% |
| Probabilistic / Interval Forecasting | 337 | 6.8% |
| Spatio-temporal Forecasting | 231 | 4.7% |
| Univariate Forecasting | 168 | 3.4% |
| Imputation | 109 | 2.2% |
| Anomaly Detection | 66 | 1.3% |

## 四、应用领域

| 领域 | 数量 | 占比 |
|------|------|------|
| General / Not Specified | 1570 | 33.7% |
| Energy / Electricity | 908 | 19.5% |
| Finance / Stock / Crypto | 570 | 12.2% |
| Climate / Weather / Environment | 466 | 10.0% |
| Traffic / Transport | 390 | 8.4% |
| Health / Medical / ECG | 297 | 6.4% |
| Industrial / IoT / Sensor | 283 | 6.1% |
| Retail / Sales / Demand | 160 | 3.4% |
| Web / User Behavior | 17 | 0.4% |

## 五、等级 × 年份分布

| CCF 等级 | 2026 | 2025 | 2024 | 2023 | 2022 | 2021 |
|----------|------|------|------|------|------|------|
| A | 44 | 85 | 47 | 10 | 12 | 10 |
| B | 5 | 7 | 1 | 0 | 0 | 1 |
| C | 12 | 33 | 0 | 0 | 7 | 2 |
| Workshop | 0 | 0 | 1 | 0 | 0 | 0 |
| Preprint | 351 | 537 | 369 | 231 | 81 | 0 |
| Other | 8 | 231 | 342 | 351 | 329 | 340 |

## 六、主要趋势概括

1. **模型范式**：Transformer 与注意力机制仍是主流，但近年来 MLP/Linear、State Space/Mamba、KAN、LLM/FM 和扩散/生成模型快速增长。
2. **任务焦点**：长期预测（Long-term Forecasting）与多元预测占主导，零样本/迁移/基础模型方向从 2024 年开始显著升温。
3. **应用领域**：能源/电力、交通、金融和气候/环境是最常被研究的四大应用方向。
4. **新兴方向**：结合大语言模型、检索增强、不确定性量化、因果推断、在线/持续学习和可解释性的交叉研究增多。

---

> 注：本总结基于标题与摘要关键词的自动匹配，可能存在少量误判；多标签论文会被同时计入多个类别。