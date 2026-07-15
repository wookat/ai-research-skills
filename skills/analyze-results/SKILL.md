---
name: analyze-results
description: Analyze ML experiment results, compute statistics, generate comparison tables and insights. Use when user says "analyze results" or needs to interpret experimental data. Do not use for run-vs-run alignment and tracking (use compare).
argument-hint: "[results-path-or-description]"
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit
---

# Analyze Experiment Results

Analyze: $ARGUMENTS

## Workflow

### Step 1: Locate Results
Find all relevant JSON/CSV result files:
- Check `figures/`, `results/`, or project-specific output directories
- Parse JSON results into structured data

### Step 2: Build Comparison Table
Organize results by:
- **Independent variables**: model type, hyperparameters, data config
- **Dependent variables**: primary metric (e.g., perplexity, accuracy, loss), secondary metrics
- **Delta vs baseline**: always compute relative improvement

### Step 3: Statistical Analysis
- If multiple seeds: report mean +/- std, check reproducibility
- If sweeping a parameter: identify trends (monotonic, U-shaped, plateau)
- Flag outliers or suspicious results

### Step 4: Generate Insights
For each finding, structure as:
1. **Observation**: what the data shows (with numbers)
2. **Interpretation**: why this might be happening
3. **Implication**: what this means for the research question
4. **Next step**: what experiment would test the interpretation

### Step 5: Update Documentation
If findings are significant:
- Propose updates to project notes or experiment reports
- Draft a concise finding statement (1-2 sentences)

## Output Format
Always include:
1. Raw data table
2. Key findings (numbered, concise)
3. Suggested next experiments (if any)

## 统计纪律（本整合包硬规则）

任何"A 优于 B"的结论必须遵守 `skills/statistical-testing/SKILL.md` 的小样本
规则：n=3 种子只报 mean ± std / 极差，不报 p 值；≥5 种子的配对比较才做显著性
检验（默认 Wilcoxon signed-rank 或 Welch）；多个比较记入 comparison ledger
并做 Holm / BH-FDR 校正。分析产出的每一条对比结论都要注明种子数与检验方式
（或注明"未做检验，仅描述统计"）。
