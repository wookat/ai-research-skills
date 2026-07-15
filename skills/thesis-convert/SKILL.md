---
name: thesis-convert
description: Convert one or more published/submitted conference papers into a master's thesis - restructuring from paper format to thesis chapters, expanding background and related work, unifying notation, and complying with the university LaTeX template and Chinese academic writing norms. Use when the user asks to turn papers into a thesis, write thesis chapters, or prepare 学位论文.
---

# Thesis Convert（论文→硕士学位论文）

把 1-3 篇会议论文扩展重组为一本硕士学位论文。会议论文是"压缩格式"，学位论文要求**完整叙事 + 教学式展开**。

## Step 0 — 骨架规划

- 确认学校 LaTeX 模板（无则向人类要，这是少数必须提问的事项）与页数/格式规范
- 单篇论文 → 经典五章结构；多篇 → 每篇一个核心章 + 统一的绪论/基础/总结章
- 写章节大纲 + 每章与源论文素材的映射表，出决策卡供人审定

## 典型结构（单篇扩展）

1. **绪论**：研究背景与意义（比论文 intro 扩展 3-5 倍：领域大背景→细分方向→本文问题）、
   国内外研究现状（把 related work 扩成系统综述，按脉络分小节）、主要贡献、论文组织
2. **相关理论与技术基础**：会议论文里假定读者已知的预备知识（问题形式化、
   经典方法原理），教学式展开——这是学位论文特有的章，答辩委员会重点检查
3. **方法章**（论文 method 扩展）：动机充分展开、每个设计决策给理由、
   补充论文因篇幅砍掉的推导与细节、被证伪的尝试可作为设计过程叙述（hypothesis_tree.md 是好素材）
4. **实验章**：全部实验含论文附录内容、补充实现细节、失败案例分析扩展
5. **总结与展望**：贡献总结 + 诚实的局限 + 具体可行的未来方向

## 转换规则

- **符号统一**：多篇论文合并时建全局符号表，冲突符号全书统一
- **叙事升维**：绪论必须给出贯穿全书的研究主线，多篇工作要讲成递进关系而非并列
- **中文规范**：学术中文行文（避免翻译腔），术语首次出现"中文（English）"，
  图表题注中文，参考文献按学校要求格式（GB/T 7714 常见）
- **自我引用**：源论文在文献综述中正常引用并声明"本章工作已发表于……"（按学校规范）
- **扩展禁区**：不得为凑页数注水；扩展 = 补足推导/背景/分析，不是复读

## 查重与 AIGC 检测注意

- 与已发表论文的重复率按学校规定处理（通常本人已发表工作可豁免但需声明）
- 全文完成后通读消除模板化 AI 文风：句式多样化、删空洞连接词、每章开头结尾避免公式化套话

## 输出

`thesis/` 目录：学校模板 LaTeX 工程、按章分文件、全局符号表、图表资产、参考文献库。

## 纪律

- 学位论文的第一读者是答辩委员会：预备知识宁多勿少，逻辑链宁细勿跳。
- 所有实验数字与源论文一致；不一致处（如补跑）显式说明。
