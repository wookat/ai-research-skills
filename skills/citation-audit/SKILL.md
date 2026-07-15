---
name: citation-audit
description: Zero-context verification that every cited bibliography entry is real, correctly attributed, and actually supports the sentence citing it - catching hallucinated references, wrong metadata, and wrong-context citations with per-entry KEEP/FIX/REPLACE/REMOVE verdicts. Use before any submission (paper or thesis) or when the user asks to check citations, verify references, or audit the bibliography.
---

# Citation Audit（引用核查）

幻觉引用和张冠李戴的引用是 AI 辅助写作最危险的输出——审稿人抽查到一条就足以
摧毁全文可信度。投稿前和学位论文送审前**必跑**。

⚠ 本 skill 属 verdict 类评审，必须遵守 `../cross-model-review` 协议：在零上下文
新线程、优先跨模型的条件下逐条核验，只读 `.bib`/`.tex` 本身，禁止在生成这些
引用的同一上下文里自查。无法换线程/换模型时，按 `shared-references/reviewer-adapter.md`
降级，并在报告头部标注 `⚠ same-context audit, hallucinated citations may be missed`。
同时遵守 `shared-references/research-integrity.md` 红线。

## 流程

1. **提取**：解析 `.bib` 与全部 `.tex`，得到每个 cite key 的（元数据，引用处上下文句子）
   对；未被引用的 bib 条目单独列出（建议删除）。
2. **逐条核验（遵守 cross-model-review 协议，零上下文）**，每条查三层：
   - **真实性**：论文是否存在——用 paper-search / Semantic Scholar / DBLP 按标题精确检索；
     核对作者、年份、venue、版本（arXiv v几 vs 正式版）
   - **归属正确**：引用句描述的贡献是否真是这篇论文做的（最常见错误：把后续改进
     工作的结论安到奠基论文头上）
   - **语境支持**：读被引论文摘要（必要时正文），判断它是否支持引用句的具体主张
3. **逐条判定**：
   - `KEEP`：干净，全部引用处恰当
   - `FIX`：元数据需更正（年份/venue/作者拼写），用法没问题
   - `REPLACE`：语境不符——找一篇真正支持该主张的论文替换
   - `REMOVE`：条目是幻觉或无法支持，删除并改写引用句
4. **报告**：`citation_audit.md` —— 汇总计数表 + 逐条 verdict（含证据链接）+
   待执行的 bib/tex 修改清单。修改执行后只复核被改动的条目。

**本整合包契约：**报告写入
`research_run/<课题slug>/stage6_review/citation_audit.md`；脱离
`research-pipeline` 单独调用时，退当前工作目录。

## 纪律

- 检索不到 ≠ 幻觉：先试标题变体、作者+年份组合；确认多路检索都无果才判 REMOVE。
- REPLACE 的新引用必须真读过摘要确认支持，禁止"看标题像就换上"。
- 学位论文按 GB/T 7714（或学校规定格式）同时核查格式一致性。
