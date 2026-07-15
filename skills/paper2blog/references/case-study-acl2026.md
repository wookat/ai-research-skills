# Case Study: ACL 2026 Data Organization Article

This case is a reusable pattern distilled from a successful draft, not a template to copy word for word.

## Source Situation

- Paper: `Demystifying Data Organization for Enhanced LLM Training`
- Desired output: Chinese `.docx` for public-account editors.
- Existing example: previous DELT public-account article with PDF input and DOCX output.
- Useful supporting materials: paper PDF, LaTeX source, poster summary, README, paper figures.

## What Worked

- The article opened with an intuitive contrast: people usually care about what data to train on, but this paper asks in what order data should appear.
- It used a simple learning/course-schedule analogy to explain data organization.
- It connected this paper to the earlier DELT/Data Efficacy framing without making the new paper sound like a minor appendix.
- It made the four guidances the main public-facing structure:
  - Boundary Sharpening
  - Cyclic Scheduling
  - Curriculum Continuity
  - Local Diversity
- Each guidance had a short explanation plus a figure that showed evidence or mechanism.
- The result section used a compact table instead of forcing readers through all benchmark columns.
- The ending framed the contribution as a Data-centric AI optimization dimension: not only what the model learns, but in what order it learns.

## Reusable Outline

1. Title: conference/venue plus reader-facing thesis.
2. Subtitle: institution or method descriptor.
3. Lead:
   - common assumption,
   - why the overlooked dimension matters now,
   - paper's main question.
4. Overview figure.
5. Paper and code links.
6. Problem framing.
7. Named principles or method components.
8. Evidence figures interleaved with explanation.
9. Compact result table.
10. Scaling or robustness result if the paper has one.
11. Summary with significance and boundary.

## Example Moves

Opening move:

`训练大语言模型时，我们通常首先关心“用什么数据”。但当训练语料已经经过清洗和筛选后，还有一个常常被忽视的问题：这些样本应该以什么顺序呈现给模型？`

Analogy move:

`如果把训练过程类比为上课，那么数据选择决定了教材内容，而数据组织则决定了课程表。`

Contribution move:

`这篇论文的价值不只在于提出两种排序方法，更在于系统总结了可迁移的数据组织指南。`

Closing move:

`如果说数据选择是在回答“模型应该学什么”，那么数据组织进一步回答的是“模型应该按什么顺序学”。`

## Avoid Overfitting to This Case

- Not every paper has four principles. Use the paper's natural structure.
- Not every paper needs seven figures. Use only visuals that help the editor and reader.
- Do not force the course-schedule analogy onto unrelated papers.
- Do not always create a result table; use it when there are compact, trustworthy numbers.
