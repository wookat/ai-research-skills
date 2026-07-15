# Attribution

本包整合了以下开源项目的 skill 原件（均为 MIT License，版权归各原作者）：

| 本包位置 | 来源 | License |
|---|---|---|
| skills/paper-search, skills/idea-spark, skills/scoop-check；skills/paper2poster, paper2video, paper2reel, paper2blog, paper2assets | [microsoft/ResearchStudio](https://github.com/microsoft/ResearchStudio) (ResearchStudio-Idea / ResearchStudio-Reel) | MIT © 2026 |
| skills/reproduce, skills/compare, skills/debug, skills/experiment-design, skills/latex-setup, skills/research-publishing, skills/paper-verification, skills/launch, skills/dataset-curation；skills/reviewer-simulation/references/reviewer-defense.md | [fcakyon/phd-skills](https://github.com/fcakyon/phd-skills) | MIT © 2026 Fatih Cagatay Akyon |
| skills/paper-writing（主体及 references/，ccfa-structure.md 除外） | [Master-cai/Research-Paper-Writing-Skills](https://github.com/Master-cai/Research-Paper-Writing-Skills)（改编自彭思达老师的写作指南） | MIT © 2026 Master-cai |
| skills/rebuttal-writing/SKILL.md, skills/data-visualization, skills/latex-workflow, skills/statistical-testing, skills/systematic-review, skills/meta-analysis, skills/time-series-analysis | [xjtulyc/awesome-rosetta-skills](https://github.com/xjtulyc/awesome-rosetta-skills) (00-universal/rebuttal-writing) | MIT © 2026 |
| skills/idea-critic/references/novelty_gate.md, roles.md | [ngtiendong/academic-research-agent-skill](https://github.com/ngtiendong/academic-research-agent-skill) | MIT © 2026 |
| skills/patent-pipeline, invention-structuring, prior-art-search, patent-novelty-check, claims-drafting, specification-writing, patent-review, jurisdiction-format, paper-poster-html, paper-slides, paper-talk, render-html, mermaid-diagram, grant-proposal, proof-checker, formula-derivation, ablation-planner, analyze-results, slides-polish, paper-illustration, figure-description, embodiment-description, result-to-claim, paper-claim-audit, research-review, proof-writer, research-wiki, paper-compile, overleaf-sync, auto-review-loop, auto-review-loop-llm, auto-paper-improvement-loop, run-experiment, monitor-experiment, experiment-queue, dse-loop, shared-references/, tools/ | [wanshuiyin/Auto-claude-code-research-in-sleep (ARIS)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（原件收录） | MIT © 2026 wanshuiyin |
| skills/cross-model-review, kill-argument, night-loop, citation-audit | 自研提炼，机制与实证结论源自 [wanshuiyin/Auto-claude-code-research-in-sleep (ARIS)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | MIT © 2026 wanshuiyin（方法论出处） |
| skills/research-pipeline, idea-mining, literature-gap-mining, idea-critic（主体）, experiment-loop, reviewer-simulation（主体）, thesis-convert, arxiv-radar, deai-polish, rebuttal-writing/references/rebuttal-strategy.md, paper-writing/references/ccfa-structure.md, domains/ | 本包原创（提炼整合自上述项目的方法论） | MIT |

对原件的修改限于：frontmatter 触发消歧与 YAML 修复、路径引用改为包内/环境无关定位
（去除 CLAUDE_PROJECT_DIR 硬依赖）、为缺少降级分支的外部 MCP 评审步骤补充 fallback 说明、
为 scoop-check 补充报告落盘契约。方法内容未改动；未收录的 ARIS 引用见
`skills/shared-references/pack-mapping.md` 的替换表。
