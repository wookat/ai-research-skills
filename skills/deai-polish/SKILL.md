---
name: deai-polish
description: Remove AI-flavored writing patterns from academic text (papers and theses) and reduce AIGC-detector risk while preserving technical content - sentence rhythm variation, filler-phrase removal, template-structure breaking, and Chinese academic style normalization. Use when the user asks to de-AI, humanize, polish AI-generated academic text, or prepare a thesis for AIGC detection checks.
---

# De-AI Polish（去 AI 味润色）

目标不是"骗过检测器"，而是消除 AI 文风的真实缺陷——这些缺陷同时也是审稿人和答辩委员会反感的点。技术内容一字不错地保留。

## AI 文风特征清单（逐段核对并修复）

1. **节奏单一**：连续长句、句长方差小 → 长短句交替；关键结论用短句
2. **空洞连接词堆砌**：Moreover/Furthermore/Additionally 开头连发；中文"此外/同时/值得注意的是" → 删掉一半，用内容逻辑自然衔接
3. **模板化段落结构**：每段"总起-三点展开-小结"完全对称 → 打破对称，信息密度决定段落形状
4. **对冲滥用**：may/might/could/potentially 密度过高 → 有证据的判断就直说
5. **列表化倾向**：能写成段落的硬拆成 bullet → 论文正文以段落叙述为主
6. **万能形容词**：novel/comprehensive/significant/robust 无信息量堆叠 → 换成具体事实
7. **中文翻译腔**：欧化长定语、"进行了…的操作"、"基于…的方式" → 重写为地道学术中文
8. **首尾公式化**："In this paper, we..." 开头、"In conclusion..." 结尾的呆板变体 → 用具体问题/结果开场

## 流程

1. 逐节扫描，按上表标记问题句（输出 diff 风格：原句 → 改句 + 命中的特征编号）
2. 修改后自检：技术主张、数字、引用完全未变（用 claim-evidence map 核对）
3. 全文通读一遍句长分布与段落形状；重点打磨 abstract、每章首末段（检测与人读的焦点）

## 红线

- 不改变任何技术内容、数据、引用；只动表达。
- 不使用同义词替换器式的机械扰动（降低可读性且无效）。
- 学位论文按学校 AIGC 检测规定如实处理；本 skill 提升的是文本质量，不提供规避造假背书。
