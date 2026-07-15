---
name: rebuttal-writing
description: >
  Use this Skill to write structured academic peer-review rebuttals: point-by-point
  responses, tone calibration, LaTeX templates, and cover letters for re-submission.
  Also read references/rebuttal-strategy.md for concern triage (misunderstanding /
  fixable / fundamental), rebuttal-experiment scheduling, and score-raising strategy.
tags:
  - universal
  - rebuttal-writing
  - peer-review
  - academic-writing
  - latex
  - revision
version: "1.0.0"
authors:
  - name: awesome-rosetta-skills contributors
    github: "@awesome-rosetta-skills"
license: "MIT"
platforms:
  - claude-code
  - codex
  - gemini-cli
  - cursor
dependencies:
  python:
    - re>=3.11
    - pathlib>=3.11
last_updated: "2026-03-17"
---

**本整合包契约：**产物写 `research_run/<课题slug>/stage7_rebuttal/`；脱离
`research-pipeline` 单独调用时，退当前工作目录。按场景分三种模式：

1. **会议 rebuttal**（不可改稿、短周期、字数受限）→ `stage7_rebuttal/rebuttal.md`，
   用 Section 4/5 的分诊与策略；rebuttal 实验按 `references/rebuttal-strategy.md` 排期。
2. **期刊 major revision / 重投**（可改稿）→ `stage7_rebuttal/response_letter.md`
   （本文件的 LaTeX 模板 + cover letter 节）+ 修改稿 change log/latexdiff
   （`stage7_rebuttal/manuscript_diff/`）；在 `state.md` 记录 resubmission 截止日期。
3. **被拒转投**：逐条消化审稿意见（不可反驳的按 major revision 处理修改稿）→
   回阶段 6 重跑自审 → 出临时决策卡定新 venue → 按新 venue 格式重排后再投。

# Rebuttal Writing

> **TL;DR** — Structured academic peer-review response writing. Covers point-by-point
> rebuttal structure, tone calibration for hostile/constructive/minor comments,
> a complete LaTeX rebuttal template, Python parsers for review text, polite phrase
> banks for each scenario, and cover letter structure for re-submission.

---

## 1. Overview

### What Problem Does This Skill Solve?

Responding to peer review is one of the most strategically demanding parts of academic
publishing. A poorly structured rebuttal — even for strong science — can lead to rejection
at the revision stage. This Skill provides:

- **Point-by-point structure** that editors and reviewers expect
- **Tone calibration** templates covering hostile, constructive, and minor comments
- A **complete LaTeX rebuttal document** ready to compile
- **Python utilities** to parse raw review text and scaffold response sections
- **Phrase banks** for agree, disagree-but-address, clarification-only, and
  experiment-added scenarios
- A **response-length calibration guide** and **re-submission cover letter** template

### Applicable Scenarios

| Scenario | Recommended Entry Point |
|---|---|
| Major revision from a top journal | Full LaTeX template + `parse_review_text()` |
| Hostile reviewer comment | `tone_phrases["disagree"]` + length guide |
| Minor revision / clarification only | `tone_phrases["clarification"]` scaffold |
| New experiment requested by reviewer | `tone_phrases["experiment_added"]` |
| Preparing cover letter for re-submission | Cover letter template in Section 6 |
| Deciding whether to appeal a rejection | Decision checklist in Section 5 |

### Key Principles

1. **Address every comment** — even those you disagree with. Silence signals evasion.
2. **Be respectful but direct** — excessive hedging weakens your scientific position.
3. **Quote the reviewer** before responding — removes ambiguity and helps editors follow.
4. **Show the change** — paste the revised text (LaTeX diff or plain) directly in the response.
5. **Number responses hierarchically** — `R1.C3` means Reviewer 1, Comment 3.

---

## 2. Environment Setup

No special packages are required beyond the Python standard library. The LaTeX template
requires a standard TeX distribution (TeX Live, MiKTeX, or MacTeX).

```bash
# Install a TeX distribution if needed (Linux/macOS example)
sudo apt-get install texlive-latex-extra texlive-fonts-recommended

# Install optional helper for diff highlighting
pip install latexdiff  # provides Python wrapper; or use system latexdiff

# Verify Python utilities
python - <<'EOF'
import re, pathlib, textwrap
print("Standard library OK — no additional packages needed")
EOF
```

---

## 3. LaTeX Rebuttal Template

Save this as `rebuttal.tex` and compile with `pdflatex rebuttal.tex`.

```latex
% ==============================================================
%  Academic Peer Review Rebuttal Template
%  Usage: fill in the macros below, then populate each \response
%  block. Compile twice for correct cross-references.
% ==============================================================
\documentclass[11pt, a4paper]{article}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\geometry{margin=2.5cm}
\usepackage{xcolor}
\usepackage{mdframed}
\usepackage{parskip}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage{lmodern}

% ---- Colour scheme ----
\definecolor{reviewercolor}{RGB}{0, 70, 127}
\definecolor{changecolor}{RGB}{0, 110, 51}
\definecolor{boxbg}{RGB}{240, 245, 255}

% ---- Environments ----
\newmdenv[
  backgroundcolor=boxbg,
  linecolor=reviewercolor,
  linewidth=1pt,
  innerleftmargin=10pt,
  innerrightmargin=10pt,
  innertopmargin=8pt,
  innerbottommargin=8pt,
  skipabove=8pt,
  skipbelow=4pt,
]{reviewerbox}

\newcommand{\reviewercomment}[2]{%
  \begin{reviewerbox}
    \textbf{\textcolor{reviewercolor}{#1:}} #2
  \end{reviewerbox}%
}

\newcommand{\response}[1]{%
  \textbf{Response:} #1
  \vspace{4pt}
}

\newcommand{\changemade}[1]{%
  \textit{\textcolor{changecolor}{\textbf{Change made:} #1}}
  \vspace{8pt}
}

% ---- Paper metadata — fill these in ----
\newcommand{\mstitle}{TITLE OF YOUR MANUSCRIPT}
\newcommand{\msjournal}{TARGET JOURNAL NAME}
\newcommand{\msid}{MANUSCRIPT-ID-XXXX}
\newcommand{\msdecision}{Major Revision}

% ==============================================================
\begin{document}

\begin{center}
  {\LARGE \textbf{Response to Reviewers}}\\[6pt]
  {\large \mstitle}\\[4pt]
  {\normalsize Submitted to \textit{\msjournal} \quad|\quad Manuscript ID: \msid}\\[4pt]
  {\normalsize Decision: \msdecision \quad|\quad \today}
\end{center}

\hrule
\vspace{12pt}

% ---- Opening statement ----
\noindent
We thank the Editor and the reviewers for their careful reading of our manuscript and
for their constructive comments. We have revised the manuscript thoroughly in response
to all points raised. Below we address each comment in turn.
Reviewer comments are reproduced verbatim in shaded boxes.
Our responses appear immediately below each comment.
All changes to the manuscript are highlighted in \textcolor{changecolor}{green}
in the tracked-changes PDF.

\vspace{12pt}
\hrule
\vspace{12pt}

% ==============================================================
\section*{Response to Reviewer 1}

% --- Comment 1 ---
\reviewercomment{Reviewer 1, Comment 1}{%
  The manuscript lacks a direct comparison with [BASELINE METHOD]. Without this
  comparison, the claimed improvements cannot be assessed.
}

\response{%
  We thank the reviewer for this important point. We agree that a direct comparison
  with [BASELINE METHOD] strengthens the evaluation. We have added this comparison
  in Table~2 of the revised manuscript. [BASELINE METHOD] achieves
  \textbf{XX.X\%} on [METRIC], while our method achieves \textbf{YY.Y\%},
  a statistically significant improvement ($p < 0.05$, paired $t$-test).
}

\changemade{%
  Table~2 now includes [BASELINE METHOD] as a new row. Section~4.2 (paragraph~3)
  was expanded to discuss these results. The experimental setup for [BASELINE METHOD]
  is described in Appendix~A.
}

% --- Comment 2 ---
\reviewercomment{Reviewer 1, Comment 2}{%
  The motivation in the introduction is weak. It is unclear why this problem matters
  for practitioners.
}

\response{%
  We appreciate this feedback. We have substantially revised the introduction (Section~1,
  paragraphs 1--3) to articulate the practical significance more clearly. Specifically,
  we now open with a concrete motivating example drawn from [DOMAIN] and explicitly
  connect our contribution to two pressing real-world challenges: [CHALLENGE~1] and
  [CHALLENGE~2].
}

\changemade{%
  Introduction revised: paragraphs 1--3 rewritten. A motivating example (Figure~1)
  was added. Word count of introduction increased by approximately 180 words.
}

% ==============================================================
\section*{Response to Reviewer 2}

% --- Comment 1 ---
\reviewercomment{Reviewer 2, Comment 1}{%
  I find the statistical analysis in Section~3 unconvincing. A simple $t$-test is
  insufficient for comparing multiple methods; corrections for multiple comparisons
  are required.
}

\response{%
  The reviewer raises a valid methodological concern. We have replaced the uncorrected
  $t$-tests with a one-way ANOVA followed by Tukey's HSD post-hoc test, which
  appropriately controls the family-wise error rate across the [N] pairwise comparisons
  in Table~3. The revised analysis does not change our main conclusions, but does
  slightly narrow several confidence intervals.
}

\changemade{%
  Section~3.4 revised. Table~3 now reports Tukey-adjusted $p$-values and 95\%~CI.
  The Methods section (Section~2.5) was updated to describe the revised statistical
  procedure.
}

% --- Comment 2 ---
\reviewercomment{Reviewer 2, Comment 2}{%
  Minor: Several references are formatted inconsistently (mix of et~al. and full
  author lists). Please standardise to journal style.
}

\response{%
  We apologise for the inconsistency. All references have been reformatted to conform
  strictly to \textit{\msjournal} author guidelines (APA 7th edition). We used
  Zotero with the \textit{\msjournal} CSL style to ensure consistency.
}

\changemade{%
  All references in the reference list standardised. No substantive content changed.
}

% ==============================================================
\section*{Response to Associate Editor}

\reviewercomment{Associate Editor}{%
  Please ensure that the data availability statement is updated to reflect the
  repository hosting your code and data.
}

\response{%
  Thank you for this reminder. We have updated the Data Availability Statement
  (end of manuscript, before References) to include the permanent DOI of our
  code and data repository:
  \url{https://doi.org/10.XXXX/zenodo.XXXXXXX}.
  The repository was made publicly available on [DATE].
}

\changemade{%
  Data Availability Statement updated with repository DOI and access date.
}

\vspace{12pt}
\hrule
\vspace{12pt}
\noindent
We hope that the revised manuscript and this response letter adequately address all
the concerns raised. We remain available to provide any additional information or
clarification the Editor or reviewers may require.

\vspace{12pt}
\noindent
\textit{Sincerely,}\\
The Authors

\end{document}
```

---

## 4. Python Utilities for Review Parsing

### 4.1 Parse Review Text into Structured Comments

```python
import re
from pathlib import Path
from typing import List, Dict, Optional
import textwrap


def parse_review_text(
    raw_text: str,
    reviewer_pattern: str = r"(?i)(reviewer\s*\d+|associate\s+editor|editor)",
    comment_pattern: str = r"(?i)(comment\s*[\d]+|point\s*[\d]+|\d+[\.\)])",
) -> Dict[str, List[str]]:
    """
    Parse raw review text into a structured dict of reviewer -> list of comments.

    The parser is heuristic: it splits on reviewer headers and then on numbered
    comment markers. Works for most journal review formats.

    Args:
        raw_text:        Full text pasted from the review system.
        reviewer_pattern: Regex that identifies a new reviewer section header.
        comment_pattern:  Regex that identifies a new comment within a section.

    Returns:
        Dict mapping reviewer label (str) to list of comment strings.

    Example:
        >>> text = "Reviewer 1\\n1. The introduction is unclear.\\n2. Table 2 needs..."
        >>> parse_review_text(text)
        {'Reviewer 1': ['The introduction is unclear.', 'Table 2 needs...']}
    """
    # Split text into reviewer sections
    sections: Dict[str, str] = {}
    current_label = "General"
    current_lines = []

    for line in raw_text.splitlines():
        if re.match(reviewer_pattern, line.strip()):
            if current_lines:
                sections[current_label] = "\n".join(current_lines)
            current_label = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_label] = "\n".join(current_lines)

    # Within each section, split on comment markers
    result: Dict[str, List[str]] = {}
    for label, body in sections.items():
        comments = re.split(comment_pattern, body)
        cleaned = [c.strip() for c in comments if c.strip() and not re.match(comment_pattern, c.strip())]
        result[label] = cleaned

    return result


def scaffold_rebuttal(
    parsed_reviews: Dict[str, List[str]],
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a plain-text rebuttal scaffold from parsed review comments.

    Each comment block is pre-filled with placeholders that the author
    replaces with their actual response and change description.

    Args:
        parsed_reviews: Output of parse_review_text().
        output_path:    If provided, write scaffold to this file (UTF-8).

    Returns:
        Scaffold string with one block per reviewer comment.
    """
    lines = [
        "=" * 70,
        "REBUTTAL SCAFFOLD — fill in each [RESPONSE] and [CHANGE MADE] block",
        "=" * 70,
        "",
    ]

    for reviewer, comments in parsed_reviews.items():
        lines.append(f"\n{'=' * 70}")
        lines.append(f"RESPONSE TO: {reviewer}")
        lines.append("=" * 70)

        for i, comment in enumerate(comments, start=1):
            wrapped = textwrap.fill(comment, width=68, initial_indent="  ", subsequent_indent="  ")
            lines.append(f"\n--- Comment {i} ---")
            lines.append("REVIEWER SAID:")
            lines.append(wrapped)
            lines.append("")
            lines.append("RESPONSE:")
            lines.append("  [YOUR RESPONSE HERE — address the concern directly;")
            lines.append("   cite manuscript line numbers; include revised text if short]")
            lines.append("")
            lines.append("CHANGE MADE:")
            lines.append("  [DESCRIBE EXACTLY WHAT WAS CHANGED: section, lines, added/removed]")
            lines.append("-" * 70)

    scaffold = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(scaffold, encoding="utf-8")
        print(f"Scaffold written to {output_path}")

    return scaffold


def count_comments(parsed_reviews: Dict[str, List[str]]) -> None:
    """Print a summary of comment counts per reviewer."""
    total = 0
    print("Review summary:")
    for reviewer, comments in parsed_reviews.items():
        n = len(comments)
        total += n
        print(f"  {reviewer}: {n} comment(s)")
    print(f"Total comments to address: {total}")
```

### 4.2 Tone Calibration Phrase Bank

```python
TONE_PHRASES = {
    "agree": {
        "opening": [
            "We thank the reviewer for this insightful observation.",
            "We fully agree with the reviewer's assessment.",
            "This is an excellent point that we had underweighted.",
            "The reviewer correctly identifies a weakness in our original analysis.",
        ],
        "transition": [
            "In response, we have revised [SECTION] to address this directly.",
            "We have therefore added [CONTENT] as suggested.",
            "The manuscript has been updated accordingly (see [SECTION]).",
        ],
        "closing": [
            "We believe this change substantially strengthens the paper.",
            "The revised manuscript addresses this concern in full.",
        ],
    },
    "disagree": {
        "opening": [
            "We respectfully disagree with the reviewer's interpretation for the following reasons.",
            "While we appreciate this concern, we believe the current approach is appropriate because:",
            "We understand the reviewer's concern; however, the evidence supports our original conclusion.",
            "With respect, we maintain our original position and provide the following justification.",
        ],
        "support": [
            "First, [EVIDENCE/CITATION] directly supports our claim.",
            "The reviewer's suggested alternative has been considered; it is not applicable here because [REASON].",
            "We note that [RELATED WORK] uses the same approach under similar conditions.",
        ],
        "bridge": [
            "To address the reviewer's underlying concern, we have added [CLARIFICATION] to [SECTION].",
            "Although we retain our original conclusion, we have strengthened the discussion of limitations in [SECTION].",
        ],
    },
    "clarification": {
        "opening": [
            "We thank the reviewer for pointing out this ambiguity.",
            "This comment reveals that our original text was insufficiently clear.",
            "We apologize for the unclear presentation; the intended meaning is as follows.",
        ],
        "explanation": [
            "To clarify: [CLEAR RESTATEMENT OF THE ORIGINAL POINT].",
            "Our intent was [INTENT]; we have rewritten this passage to make it unambiguous.",
        ],
        "closing": [
            "The revised text reads: '[NEW SENTENCE(S)]'.",
            "[SECTION] has been rewritten to make this explicit.",
        ],
    },
    "experiment_added": {
        "opening": [
            "We thank the reviewer for this suggestion. We have conducted the requested analysis.",
            "The reviewer's request is well-motivated. We have added this experiment.",
            "This is a valuable suggestion. New results are presented in [SECTION/TABLE/FIGURE].",
        ],
        "result": [
            "The new experiment shows [RESULT], which [SUPPORTS / IS CONSISTENT WITH / QUALIFIES] our main conclusion.",
            "Results for [NEW EXPERIMENT] are reported in [TABLE/FIGURE]. [BRIEF INTERPRETATION].",
        ],
        "closing": [
            "This additional evidence further supports the robustness of our approach.",
            "We are grateful for this suggestion, which has strengthened the manuscript.",
        ],
    },
    "minor": {
        "opening": [
            "Thank you for catching this.",
            "We apologize for this oversight.",
            "Corrected, thank you.",
        ],
        "closing": [
            "This has been fixed in the revised manuscript.",
            "The error has been corrected throughout.",
        ],
    },
}


def get_phrases(scenario: str, role: str = "opening") -> List[str]:
    """
    Retrieve phrase options for a given rebuttal scenario and rhetorical role.

    Args:
        scenario: One of 'agree', 'disagree', 'clarification',
                  'experiment_added', 'minor'.
        role:     Rhetorical role within the response:
                  'opening', 'transition', 'closing', 'support',
                  'bridge', 'explanation', 'result'.

    Returns:
        List of phrase strings to choose from.

    Example:
        >>> get_phrases("disagree", "opening")
        ['We respectfully disagree...', ...]
    """
    scenario_bank = TONE_PHRASES.get(scenario, {})
    phrases = scenario_bank.get(role, [])
    if not phrases:
        available = list(scenario_bank.keys())
        raise KeyError(
            f"Role '{role}' not found for scenario '{scenario}'. "
            f"Available roles: {available}"
        )
    return phrases


def compose_response(
    scenario: str,
    reviewer_quote: str,
    response_body: str,
    change_description: str,
) -> str:
    """
    Compose a formatted rebuttal response block for a single comment.

    Args:
        scenario:           Tone scenario: 'agree', 'disagree', 'clarification',
                            'experiment_added', or 'minor'.
        reviewer_quote:     Verbatim reviewer comment text.
        response_body:      Core of your response (your own words, specific to this paper).
        change_description: What was changed in the manuscript.

    Returns:
        Formatted plain-text response block.
    """
    opening = get_phrases(scenario, "opening")[0]
    closing_options = TONE_PHRASES.get(scenario, {}).get("closing", [])
    closing = closing_options[0] if closing_options else ""

    block = (
        f"REVIEWER SAID:\n"
        f"  {reviewer_quote.strip()}\n\n"
        f"RESPONSE:\n"
        f"  {opening} {response_body.strip()}"
        + (f" {closing}" if closing else "")
        + f"\n\nCHANGE MADE:\n"
        f"  {change_description.strip()}\n"
    )
    return block
```

---

## 5. Decision Checklists

### 5.1 Major Revision Checklist

Before submitting a major revision, verify each item:

```
MAJOR REVISION CHECKLIST
========================
[ ] Every reviewer comment is addressed — no comment skipped silently
[ ] Each response block has three parts: (1) response, (2) change made, (3) new text
[ ] New experiments / analyses are complete and reproducible
[ ] Abstract updated if conclusions changed
[ ] Introduction revised if scope or motivation changed
[ ] Methods section updated if procedures changed
[ ] Statistical analyses re-run if requested; corrected p-values reported
[ ] All figures re-generated at print resolution (300 dpi minimum)
[ ] Supplementary material cross-referenced from main text
[ ] Word/page count checked against journal limits
[ ] Reference list checked: new citations added, formatting standardized
[ ] Tracked-changes PDF generated for editor convenience
[ ] Rebuttal letter spell-checked and proofread
[ ] Cover letter written (see Section 6 below)
[ ] All co-authors have reviewed and approved the revision
```

### 5.2 Reject and Resubmit Decision Guide

```python
def assess_resubmission(
    decision: str,
    reviewer_scores: Optional[List[str]] = None,
    editor_tone: str = "neutral",
) -> dict:
    """
    Heuristic assessment of whether to appeal, revise and resubmit to same
    journal, or submit elsewhere.

    Args:
        decision:        'reject', 'major_revision', 'minor_revision', 'accept'.
        reviewer_scores: Optional list of reviewer sentiment strings:
                         'positive', 'mixed', 'negative'.
        editor_tone:     'encouraging', 'neutral', or 'discouraging'.

    Returns:
        Dict with keys: recommendation, rationale, priority_actions.
    """
    if decision == "accept":
        return {
            "recommendation": "Accept and finalize",
            "rationale": "Paper accepted; only copy-edits remain.",
            "priority_actions": ["Address copy-edit queries", "Sign license agreement"],
        }

    if decision == "minor_revision":
        return {
            "recommendation": "Revise and resubmit to same journal",
            "rationale": "Minor revisions are typically low-risk; address all points carefully.",
            "priority_actions": [
                "Address every minor comment — do not skip any",
                "Turn around within 3–4 weeks",
                "Write a brief but complete cover letter",
            ],
        }

    if decision == "major_revision":
        return {
            "recommendation": "Revise and resubmit to same journal",
            "rationale": "Major revision is an invitation to revise; most are eventually accepted.",
            "priority_actions": [
                "Prioritize the most substantive comments first",
                "Run requested new experiments promptly",
                "Aim for resubmission within the deadline (usually 2–3 months)",
                "Request a deadline extension if necessary — editors usually grant it",
            ],
        }

    # Reject case: weigh editor tone and reviewer sentiment
    if reviewer_scores is None:
        reviewer_scores = ["negative"]

    positive_count = reviewer_scores.count("positive")
    negative_count = reviewer_scores.count("negative")

    if editor_tone == "encouraging" and positive_count >= 1:
        recommendation = "Appeal the rejection with a strong rebuttal"
        rationale = "At least one reviewer was positive and the editor tone suggests openness."
    elif editor_tone == "discouraging" or negative_count >= len(reviewer_scores) - 1:
        recommendation = "Submit to a different journal"
        rationale = "Majority of reviewers negative and/or editor discouraging; appeal unlikely to succeed."
    else:
        recommendation = "Revise substantially and submit to a different (possibly lower-tier) journal"
        rationale = "Mixed signals; a thorough revision may succeed elsewhere."

    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "priority_actions": [
            "Carefully read the editor's decision letter for explicit guidance",
            "Address all comments in the revision regardless of destination",
            "Consider whether the paper's scope fits the new target journal",
        ],
    }
```

---

## 6. Cover Letter Template for Re-Submission

```python
COVER_LETTER_TEMPLATE = """\
{date}

Dear {editor_name},

Re: Revised Manuscript — "{title}"
Manuscript ID: {manuscript_id}
Journal: {journal}

We are pleased to resubmit the revised version of our manuscript, "{title}", for
reconsideration in {journal}. We thank the Editor and the {n_reviewers} reviewer(s)
for their thorough and constructive evaluation of our work.

In response to the comments received, we have made the following key changes to
the manuscript:

{key_changes_bullet_list}

A point-by-point response to all reviewer and editor comments is included as a
separate document ("rebuttal_letter.pdf"). All changes in the revised manuscript
are highlighted for the reviewers' convenience in the tracked-changes PDF
("manuscript_tracked.pdf").

We believe that the revised manuscript is substantially stronger as a result of the
review process and that it now fully meets the standards of {journal}. We remain
available to provide any additional information or to conduct further revisions
as needed.

Thank you for your continued consideration of our work.

Sincerely,

{corresponding_author}
{affiliation}
{email}
{orcid}
"""


def generate_cover_letter(
    title: str,
    journal: str,
    manuscript_id: str,
    editor_name: str,
    corresponding_author: str,
    affiliation: str,
    email: str,
    orcid: str,
    key_changes: List[str],
    n_reviewers: int = 2,
    date: str = "2026-03-17",
) -> str:
    """
    Generate a formatted cover letter for manuscript re-submission.

    Args:
        title:                Manuscript title.
        journal:              Target journal name.
        manuscript_id:        Journal-assigned manuscript ID.
        editor_name:          Handling editor's name (e.g. 'Prof. J. Smith').
        corresponding_author: Full name of the corresponding author.
        affiliation:          Institution and department.
        email:                Corresponding author email.
        orcid:                Corresponding author ORCID.
        key_changes:          List of bullet-point strings describing major changes.
        n_reviewers:          Number of reviewers.
        date:                 Submission date string.

    Returns:
        Formatted cover letter string.
    """
    bullet_list = "\n".join(f"  • {change}" for change in key_changes)

    return COVER_LETTER_TEMPLATE.format(
        date=date,
        editor_name=editor_name,
        title=title,
        manuscript_id=manuscript_id,
        journal=journal,
        n_reviewers=n_reviewers,
        key_changes_bullet_list=bullet_list,
        corresponding_author=corresponding_author,
        affiliation=affiliation,
        email=email,
        orcid=orcid,
    )
```

---

## 7. Response Length Calibration Guide

| Comment Type | Typical Response Length | Rationale |
|---|---|---|
| Minor typo / formatting | 1–2 sentences | Nothing to argue; just confirm the fix |
| Clarification request | 2–4 sentences | State the clarification + point to revised text |
| Methodological concern (addressed) | 1–2 paragraphs | Explain the fix + quote revised methods |
| Methodological concern (disagreed) | 2–3 paragraphs | Evidence + explanation + concession if any |
| New experiment requested (done) | 2–3 paragraphs + table/figure reference | Present new result + brief interpretation |
| New experiment requested (declined) | 2–3 paragraphs | Justify scope decision diplomatically |
| Fundamental conceptual disagreement | 3–5 paragraphs | Full argument with citations |

**Golden rule**: Match response length to comment severity. Over-responding to minor
comments dilutes the impact of your substantive responses; under-responding to major
concerns signals dismissiveness.

---

## 8. End-to-End Example

```python
# --- Example: parse a real review and scaffold a rebuttal ---

sample_review = """
Reviewer 1

Comment 1
The abstract does not mention the dataset used in the experiments.

Comment 2
The comparison with baseline X is missing from Table 3. This makes it impossible
to assess whether the proposed method is truly competitive.

Comment 3
Minor: "Equation 4" should be "Equation (4)" throughout.

Reviewer 2

Comment 1
The motivation for the choice of hyperparameter lambda is unclear. How was this
value selected and how sensitive are the results to this choice?
"""

# Parse the review
parsed = parse_review_text(sample_review)
count_comments(parsed)

# Build scaffold
scaffold = scaffold_rebuttal(parsed, output_path="rebuttal_scaffold.txt")
print(scaffold[:500])

# Compose an individual response using tone phrases
response_r1c2 = compose_response(
    scenario="experiment_added",
    reviewer_quote=(
        "The comparison with baseline X is missing from Table 3. "
        "This makes it impossible to assess whether the proposed method is truly competitive."
    ),
    response_body=(
        "We have added baseline X to Table 3. Baseline X achieves 78.3% on [METRIC], "
        "while our method achieves 83.1%, a statistically significant improvement "
        "(p=0.02, paired t-test across 5 seeds)."
    ),
    change_description=(
        "Table 3 now includes a row for Baseline X. Section 4.2 (paragraph 2) "
        "was updated to discuss this comparison. Implementation details for "
        "Baseline X are in Appendix B."
    ),
)
print("\nFormatted response for R1.C2:")
print(response_r1c2)

# Generate cover letter
letter = generate_cover_letter(
    title="Efficient Graph Neural Networks for Node Classification",
    journal="IEEE Transactions on Neural Networks and Learning Systems",
    manuscript_id="TNNLS-2026-001234",
    editor_name="Prof. J. Editor",
    corresponding_author="Dr. A. Researcher",
    affiliation="Department of Computer Science, University of Example",
    email="a.researcher@university.edu",
    orcid="0000-0002-1234-5678",
    key_changes=[
        "Added comparison with Baseline X in Table 3 (Reviewer 1, Comment 2)",
        "Clarified hyperparameter selection via grid search (Reviewer 2, Comment 1)",
        "Updated abstract to include dataset names (Reviewer 1, Comment 1)",
        "Corrected equation numbering throughout (Reviewer 1, Comment 3)",
    ],
    n_reviewers=2,
)
Path("cover_letter.txt").write_text(letter, encoding="utf-8")
print("\nCover letter saved to cover_letter.txt")
```

---

## 9. Common Pitfalls

| Pitfall | Consequence | Prevention |
|---|---|---|
| Skipping a comment without addressing it | Editor returns immediately for non-compliance | Use `count_comments()` to track coverage |
| Agreeing with every comment unconditionally | Suggests the paper was under-developed | Use `disagree` phrases when scientifically justified |
| Responses longer than the actual paper section | Editor loses track of the actual change | Follow length calibration guide in Section 7 |
| Not showing the revised text | Reviewer must search the manuscript | Always include "The revised text reads: ..." |
| Passive-aggressive phrasing | Inflames reviewer and editor | Run tone check: avoid "obviously", "clearly", "as stated" |
| Cover letter that restates every change | Redundant; editor has the rebuttal letter | Keep cover letter to key changes only (4–6 bullets) |

---

## 10. References and Further Reading

- Cals & Kotz (2013), "Effective writing and publishing scientific papers": <https://doi.org/10.1136/jech-2012-202276>
- Noble (2017), "Ten simple rules for writing a response to reviewers": <https://doi.org/10.1371/journal.pcbi.1005730>
- Annesley (2011), "Responding to reviewer comments": <https://doi.org/10.1373/clinchem.2011.170738>
- LaTeX `latexdiff` tool: <https://ctan.org/pkg/latexdiff>
- Overleaf rebuttal templates: <https://www.overleaf.com/gallery/tagged/response-to-reviewers>

---

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-03-17 | Initial release — LaTeX template, Python parser, tone phrase bank, cover letter generator |
