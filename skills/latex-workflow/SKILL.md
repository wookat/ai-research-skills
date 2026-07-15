---
name: latex-workflow
description: >
  Write, compile, and submit LaTeX papers: IMRaD structure, key packages,
  bibliography management, arXiv preparation, and common error fixes.
tags:
  - latex
  - academic-writing
  - bibliography
  - arxiv
  - research-workflow
  - manuscript
version: "1.0.0"
authors:
  - name: "awesome-rosetta-skills contributors"
    github: "@awesome-rosetta-skills"
license: "MIT"
platforms:
  - claude-code
  - codex
  - gemini-cli
  - cursor
dependencies:
  python:
    - pylatexenc>=2.10
last_updated: "2026-03-17"
---

# LaTeX Workflow

A complete guide for writing research papers in LaTeX: document structure,
essential packages, bibliography management, figure inclusion, table formatting,
arXiv submission, and a rebuttal letter template.

---

## Prerequisites

```bash
# Install TeX Live (Linux/macOS)
# Ubuntu / Debian
sudo apt-get install texlive-full latexmk biber

# macOS via Homebrew
brew install --cask mactex
brew install latexmk

# Windows: install MiKTeX from https://miktex.org
# Then install latexmk via MiKTeX console

# Verify installation
latexmk --version
pdflatex --version
biber --version
```

---

## Minimal Working Example — Full Paper Structure

```latex
% main.tex  —  IMRaD structure with common packages
\documentclass[11pt, a4paper]{article}

% ── Encoding & language ───────────────────────────────────────────────────
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}

% ── Math ──────────────────────────────────────────────────────────────────
\usepackage{amsmath, amssymb, amsthm}
\usepackage{mathtools}          % fixes and extensions to amsmath

% ── Graphics & figures ───────────────────────────────────────────────────
\usepackage{graphicx}           % \includegraphics
\usepackage{float}              % [H] placement option
\usepackage{caption}            % caption formatting
\usepackage{subcaption}         % subfigures
\graphicspath{{figures/}}       % default figure directory

% ── Tables ────────────────────────────────────────────────────────────────
\usepackage{booktabs}           % \toprule, \midrule, \bottomrule
\usepackage{tabularx}           % auto-width columns
\usepackage{multirow}           % multi-row cells
\usepackage{siunitx}            % aligned numeric columns via S

% ── Layout ────────────────────────────────────────────────────────────────
\usepackage[margin=2.5cm]{geometry}
\usepackage{setspace}
\usepackage{parskip}            % no indent, space between paragraphs
\usepackage{microtype}          % better typography (microtypography)
\usepackage{lineno}             % line numbers for review
% \linenumbers                  % uncomment for submission

% ── Hyperlinks ────────────────────────────────────────────────────────────
\usepackage[
  colorlinks = true,
  linkcolor  = blue!70!black,
  citecolor  = blue!70!black,
  urlcolor   = blue!70!black,
  pdftitle   = {Your Paper Title},
  pdfauthor  = {Author Name},
]{hyperref}
\usepackage{cleveref}           % \cref{fig:results} → "Figure 1"

% ── Bibliography (biblatex + biber) ──────────────────────────────────────
\usepackage[
  backend    = biber,
  style      = nature,          % or: authoryear, apa, ieee, vancouver
  sorting    = none,
  maxcitenames = 2,
  doi        = true,
  url        = false,
]{biblatex}
\addbibresource{references.bib}

% ── Algorithms ────────────────────────────────────────────────────────────
\usepackage[ruled, vlined, linesnumbered]{algorithm2e}

% ── Code listings ────────────────────────────────────────────────────────
\usepackage{listings}
\lstset{
  basicstyle   = \small\ttfamily,
  breaklines   = true,
  frame        = single,
  numbers      = left,
  numberstyle  = \tiny,
  language     = Python,
}

% ── Custom commands ───────────────────────────────────────────────────────
\newcommand{\eg}{\textit{e.g.,}\xspace}
\newcommand{\ie}{\textit{i.e.,}\xspace}
\newcommand{\etal}{\textit{et al.}\xspace}
\newcommand{\TODO}[1]{\textbf{\textcolor{red}{[TODO: #1]}}}

% ─────────────────────────────────────────────────────────────────────────
\title{Your Paper Title: A Study of Something Important}
\author{
  First Author\textsuperscript{1}\thanks{Corresponding author:
    \href{mailto:first@university.edu}{first@university.edu}} \and
  Second Author\textsuperscript{1,2} \and
  Third Author\textsuperscript{2}
}
\date{
  \textsuperscript{1}Department of Something, University One, City, Country \\
  \textsuperscript{2}Institute of Things, University Two, City, Country \\[6pt]
  \today
}

% ─────────────────────────────────────────────────────────────────────────
\begin{document}
\maketitle

\begin{abstract}
  \noindent
  \textbf{Background:} One to two sentences stating the research problem.
  \textbf{Methods:} Brief description of design and main methods.
  \textbf{Results:} Key quantitative findings ($n = 120$; $p < 0.001$).
  \textbf{Conclusion:} One sentence on the main implication.
\end{abstract}

\noindent\textbf{Keywords:} keyword one; keyword two; keyword three; keyword four

\tableofcontents   % remove for journal submissions

% ── 1. Introduction ───────────────────────────────────────────────────────
\section{Introduction}
\label{sec:intro}

Background and motivation \cite{Smith2023}.
The specific gap in knowledge addressed by this work.
Our main contributions are: (i) ...; (ii) ...; (iii) ...

% ── 2. Methods ────────────────────────────────────────────────────────────
\section{Methods}
\label{sec:methods}

\subsection{Study Design}
Describe the experimental design (see \cref{sec:intro}).

\subsection{Statistical Analysis}
All tests were two-tailed with $\alpha = 0.05$.
Multiple comparisons were corrected using the Benjamini--Hochberg procedure~\cite{Benjamini1995}.

% ── 3. Results ────────────────────────────────────────────────────────────
\section{Results}
\label{sec:results}

\subsection{Primary Outcome}
As shown in \cref{fig:main}, the treatment group showed a significant improvement
($t(58) = 3.24$, $p = 0.002$, Cohen's $d = 0.83$, 95\% CI [0.31, 1.35]).

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.8\linewidth]{figure1_main.pdf}
  \caption{
    \textbf{Primary outcome by treatment arm.}
    Violin plots show the full distribution; diamonds indicate group medians.
    Whiskers extend to 1.5$\times$IQR. $n = 30$ per group.
    $^{***}p < 0.001$ (Mann--Whitney U test).
  }
  \label{fig:main}
\end{figure}

\subsection{Summary Statistics}
\Cref{tab:demographics} summarises participant characteristics at baseline.

\begin{table}[htbp]
  \centering
  \caption{Baseline characteristics of participants (mean $\pm$ SD unless stated).}
  \label{tab:demographics}
  \begin{tabular}{lSSS}
    \toprule
    Characteristic &
      {Control ($n=60$)} &
      {Intervention ($n=60$)} &
      {$p$-value} \\
    \midrule
    Age (years)         & 34.2 \pm 8.1  & 33.8 \pm 7.6  & 0.79 \\
    Sex (female, \%)    & 55             & 52             & 0.72 \\
    BMI (kg/m²)         & 24.1 \pm 3.2  & 24.5 \pm 3.1  & 0.48 \\
    Baseline score      & 48.3 \pm 10.2 & 47.9 \pm 9.8  & 0.83 \\
    \bottomrule
  \end{tabular}
\end{table}

% ── 4. Discussion ─────────────────────────────────────────────────────────
\section{Discussion}
\label{sec:discussion}

Summary of main findings in context of prior work.
Strengths and limitations.
Future directions.

% ── 5. Conclusion ─────────────────────────────────────────────────────────
\section{Conclusion}
\label{sec:conclusion}

One paragraph restating the main contribution and its implications.

% ── Acknowledgements ─────────────────────────────────────────────────────
\section*{Acknowledgements}
This work was supported by Grant XYZ-1234 from Funding Agency.
The authors thank ... for helpful discussions.

% ── Author contributions (CRediT) ────────────────────────────────────────
\section*{Author Contributions}
\textbf{FA}: conceptualisation, methodology, writing—original draft.
\textbf{SA}: data curation, formal analysis.
\textbf{TA}: supervision, writing—review and editing.

% ── Data availability ─────────────────────────────────────────────────────
\section*{Data Availability}
Data and analysis code are available at \url{https://github.com/username/repo}.

% ── References ────────────────────────────────────────────────────────────
\printbibliography

% ── Supplementary (optional) ─────────────────────────────────────────────
\appendix
\section{Supplementary Methods}
\label{sec:supp}

Additional methodological details.

\end{document}
```

---

## Makefile for Compilation

```makefile
# Makefile — LaTeX build automation
# Usage:
#   make          Build PDF
#   make clean    Remove auxiliary files
#   make arxiv    Prepare arXiv submission tarball
#   make watch    Auto-rebuild on file change

MAIN     := main
LATEX    := pdflatex
BIBER    := biber
LATEXMK  := latexmk

.PHONY: all pdf clean cleanall arxiv watch

all: pdf

# ── Standard build with latexmk ───────────────────────────────────────────
pdf:
	$(LATEXMK) -pdf -bibtex -interaction=nonstopmode -file-line-error $(MAIN).tex

# ── Manual multi-pass build (fallback) ────────────────────────────────────
manual:
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(BIBER) $(MAIN)
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(LATEX) -interaction=nonstopmode $(MAIN).tex

# ── Auto-rebuild on change ─────────────────────────────────────────────────
watch:
	$(LATEXMK) -pdf -pvc -bibtex $(MAIN).tex

# ── Clean auxiliary files ─────────────────────────────────────────────────
clean:
	$(LATEXMK) -c
	rm -f *.bbl *.bcf *.run.xml

# ── Remove everything including PDF ──────────────────────────────────────
cleanall:
	$(LATEXMK) -CA
	rm -f *.bbl *.bcf *.run.xml

# ── arXiv submission tarball ──────────────────────────────────────────────
# Flattens all includes, strips comments, bundles figures
arxiv: pdf
	mkdir -p arxiv_submission
	# Copy source files
	cp $(MAIN).tex arxiv_submission/
	cp references.bib arxiv_submission/ 2>/dev/null || true
	cp $(MAIN).bbl arxiv_submission/ 2>/dev/null || true
	# Copy figures (PDF and EPS preferred by arXiv)
	cp -r figures/ arxiv_submission/ 2>/dev/null || true
	# Strip LaTeX comments from source
	python3 -c "
import re, sys
with open('arxiv_submission/$(MAIN).tex') as f:
    src = f.read()
# Remove comment lines but preserve escaped percent signs
src = re.sub(r'(?<!\\\\)%.*', '', src)
with open('arxiv_submission/$(MAIN).tex', 'w') as f:
    f.write(src)
print('Comments stripped.')
"
	tar -czf arxiv_submission.tar.gz -C arxiv_submission .
	@echo "arXiv tarball: arxiv_submission.tar.gz"
```

---

## Bibliography — BibTeX Format

```bibtex
% references.bib

@article{Smith2023,
  author    = {Smith, Jane and Doe, John},
  title     = {A Study of Something Important},
  journal   = {Nature Methods},
  year      = {2023},
  volume    = {20},
  number    = {4},
  pages     = {500--510},
  doi       = {10.1038/s41592-023-01234-5},
}

@article{Benjamini1995,
  author    = {Benjamini, Yoav and Hochberg, Yosef},
  title     = {Controlling the False Discovery Rate: A Practical and Powerful
               Approach to Multiple Testing},
  journal   = {Journal of the Royal Statistical Society: Series B},
  year      = {1995},
  volume    = {57},
  number    = {1},
  pages     = {289--300},
  doi       = {10.1111/j.2517-6161.1995.tb02031.x},
}

@book{Bishop2006,
  author    = {Bishop, Christopher M.},
  title     = {Pattern Recognition and Machine Learning},
  publisher = {Springer},
  year      = {2006},
  address   = {New York},
  isbn      = {978-0-387-31073-2},
}

@inproceedings{Vaswani2017,
  author    = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and
               Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N. and
               Kaiser, {\L}ukasz and Polosukhin, Illia},
  title     = {Attention Is All You Need},
  booktitle = {Advances in Neural Information Processing Systems},
  year      = {2017},
  volume    = {30},
  pages     = {5998--6008},
}

@misc{OpenAI2024,
  author    = {{OpenAI}},
  title     = {GPT-4 Technical Report},
  year      = {2024},
  eprint    = {2303.08774},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
}
```

---

## Zotero → BibTeX Export

```bash
# 1. In Zotero: File → Export Library → BibTeX (.bib)
# 2. Or use Better BibTeX plugin (recommended):
#    - Install: https://retorque.re/zotero-better-bibtex/
#    - Right-click collection → Export Collection → Better BibTeX
#    - Check "Keep updated" for auto-sync

# 3. Clean up common Zotero artefacts with bibtexparser (Python)
pip install bibtexparser

python3 << 'EOF'
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bparser import BibTexParser

with open("exported_zotero.bib") as f:
    parser = BibTexParser(common_strings=True)
    db = bibtexparser.load(f, parser=parser)

# Remove Zotero-specific fields
fields_to_remove = {"file", "abstract", "keywords", "mendeley-tags", "note"}
for entry in db.entries:
    for field in fields_to_remove:
        entry.pop(field, None)

writer = BibTexWriter()
writer.indent = "  "
with open("references.bib", "w") as f:
    f.write(writer.write(db))

print(f"Exported {len(db.entries)} entries to references.bib")
EOF
```

---

## arXiv Submission Preparation

```bash
# Step 1: Build final PDF and verify it looks correct
latexmk -pdf main.tex

# Step 2: Check for undefined references / citations
grep -i "warning" main.log | grep -i "undefined"

# Step 3: Flatten \input / \include (arXiv requires single .tex or explicit includes)
# Use latexpand (part of texlive-extra-utils)
latexpand main.tex > main_flat.tex

# Step 4: Strip comments (arXiv processes the source; hidden comments can leak)
python3 -c "
import re
with open('main_flat.tex') as f:
    src = f.read()
# Remove comments but keep \% (escaped percent signs)
src = re.sub(r'(?<!\\\\)%[^\n]*', '', src)
with open('main_flat.tex', 'w') as f:
    f.write(src)
print('Done.')
"

# Step 5: Ensure all figures are included and named without spaces
# PDF figures preferred; EPS and PNG also accepted

# Step 6: Bundle
mkdir arxiv_pkg
cp main_flat.tex arxiv_pkg/ms.tex
cp main.bbl       arxiv_pkg/   # pre-compiled bibliography (biber → .bbl)
cp -r figures/    arxiv_pkg/
tar -czf arxiv_submission.tar.gz -C arxiv_pkg .

# Step 7: Test-compile the tarball in a clean directory
mkdir test_compile && cd test_compile
tar -xzf ../arxiv_submission.tar.gz
pdflatex ms.tex
pdflatex ms.tex
ls -lh ms.pdf
```

---

## Common LaTeX Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `! Undefined control sequence` | Missing package or typo | Check `\usepackage` and spelling |
| `! Missing $ inserted` | Math symbol outside math mode | Wrap in `$...$` or `\(...\)` |
| `Overfull \hbox` | Text exceeds margin | Add `\-` hyphenation hints or use `\sloppy` locally |
| `Citation 'X' on page Y undefined` | Missing .bib entry or not compiled with biber | Run biber, then pdflatex twice |
| `File 'X.sty' not found` | Package not installed | `sudo tlmgr install <package>` |
| `Float too large for page` | Figure height > \textheight | Use `\includegraphics[height=0.9\textheight]` |
| `\begin{X} ended by \end{Y}` | Mismatched environments | Check all `\begin`/`\end` pairs |
| `Package babel Error: Unknown option 'X'` | Wrong language code | Use `english` not `en` |
| `pdfTeX warning: … PDF inclusion: …` | Mixed PDF versions in figures | Regenerate figures with consistent pdflatex version |

---

## Rebuttal Letter Template

```latex
% rebuttal.tex — Peer review response letter
\documentclass[11pt]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{mdframed}
\usepackage{enumitem}
\usepackage{parskip}

% Reviewer comment box
\newmdenv[
  backgroundcolor = blue!5,
  linecolor       = blue!30,
  linewidth       = 0.5pt,
  leftmargin      = 0pt,
  rightmargin     = 0pt,
  innertopmargin  = 6pt,
  innerbottommargin = 6pt,
  innerleftmargin = 8pt,
  innerrightmargin = 8pt,
]{reviewbox}

% Commands
\newcommand{\reviewer}[2]{%
  \subsection*{Reviewer #1, Comment #2}
}
\newcommand{\revcomment}[1]{%
  \begin{reviewbox}
  \textit{#1}
  \end{reviewbox}
  \vspace{4pt}
}
\newcommand{\response}[1]{%
  \textbf{Response:} #1
  \vspace{8pt}
}
\newcommand{\change}[1]{%
  \par\noindent\textcolor{teal}{\textbf{Manuscript change:} #1}
  \vspace{6pt}
}

% ─────────────────────────────────────────────────────────────────────────
\begin{document}

\begin{center}
  {\Large\bfseries Response to Reviewers}\\[6pt]
  Manuscript ID: JOURNALNAME-2024-01234\\
  Title: Your Paper Title\\[4pt]
  \today
\end{center}

\bigskip

We sincerely thank the Editor and all three reviewers for their constructive
feedback. We have addressed all concerns and believe the manuscript is
substantially improved. Changes in the revised manuscript are highlighted
in \textcolor{teal}{teal}.

\hrule
\bigskip

\section*{Reviewer 1}

\reviewer{1}{1}
\revcomment{%
  The sample size justification is unclear. How was the effect size of 0.5
  determined for the power calculation?
}
\response{%
  We agree that the justification was insufficiently detailed. The effect size
  was derived from a pilot study ($n = 20$) conducted by our group (now cited
  as Smith et al., 2022). We have added a paragraph in \S2.3 (Methods) with the
  full calculation: assuming Cohen's $d = 0.50$, $\alpha = 0.05$, and 80\%
  power, a minimum of 64 participants per arm is required. Our enrolled sample
  ($n = 70$ per arm) provides $>85$\% power.
}
\change{%
  Revised \S2.3, lines 112--119. Added citation to Smith et al. (2022).
  Updated supplementary Table S1 with full power curve.
}

\reviewer{1}{2}
\revcomment{%
  Figure 3 is difficult to read in greyscale. Please ensure figures are
  accessible to colourblind readers.
}
\response{%
  Thank you for raising this important point. We have replaced the red/green
  colour scheme with the Okabe--Ito palette, which is safe for all common
  forms of colour-vision deficiency. We have also added pattern fills to bars
  to ensure legibility in greyscale.
}
\change{%
  Figures 3, 4, and 5 updated with new colour palette. Legend updated
  accordingly.
}

\hrule
\bigskip

\section*{Reviewer 2}

\reviewer{2}{1}
\revcomment{%
  The Discussion overstates the clinical implications. Please temper the
  language regarding translation to practice.
}
\response{%
  We appreciate this important caution. We have revised the Discussion
  (\S4.3) to clearly delineate the current evidence base from speculative
  clinical translation. Phrases such as "will improve clinical outcomes"
  have been replaced with "may inform future clinical trials".
}
\change{%
  Revised \S4.3, lines 287--301.
}

\hrule
\bigskip

\noindent We hope the revised manuscript now meets the standards of the journal.
We are grateful to the reviewers for their thorough reading and constructive
suggestions.

\bigskip
\noindent Sincerely,

\bigskip
\noindent First Author (on behalf of all co-authors)\\
\href{mailto:first@university.edu}{first@university.edu}

\end{document}
```

---

## Key Package Reference

| Package | Purpose | Key Commands |
|---|---|---|
| `amsmath` | Math environments | `equation`, `align`, `gather` |
| `amssymb` | Math symbols | `\mathbb`, `\mathcal` |
| `booktabs` | Publication tables | `\toprule`, `\midrule`, `\bottomrule` |
| `graphicx` | Include figures | `\includegraphics[width=...]{file}` |
| `hyperref` | Clickable links | `\href`, `\url`, PDF metadata |
| `cleveref` | Smart cross-refs | `\cref{fig:x}` → "Figure 1" |
| `biblatex` | Bibliography | `\cite`, `\printbibliography` |
| `algorithm2e` | Pseudocode | `\begin{algorithm2e}` |
| `siunitx` | Units & numbers | `\SI{3.14}{\kilo\gram}`, `S` column |
| `microtype` | Better typography | (loads automatically) |
| `geometry` | Page margins | `\usepackage[margin=2cm]{geometry}` |
| `lineno` | Review line numbers | `\linenumbers` |
| `xcolor` | Colored text | `\textcolor{red}{text}` |
| `subcaption` | Subfigures | `\begin{subfigure}` |

---

## Journal-Specific Tips

```bash
# Download journal class files (example: NeurIPS)
wget https://neurips.cc/Conferences/2024/PaperInformation/StyleFiles -O neurips.zip
unzip neurips.zip

# Most journals provide a .cls or .sty template:
# - IEEE: IEEEtran.cls
# - ACM: acmart.cls
# - Springer: llncs.cls (LNCS), svjour3.cls (journals)
# - Elsevier: elsarticle.cls
# - ACS: achemso.cls

# Install a class file globally (if not in your project directory)
kpsewhich -var-value TEXMFHOME
# e.g. ~/texmf
mkdir -p ~/texmf/tex/latex/local
cp yourjournal.cls ~/texmf/tex/latex/local/
texhash ~/texmf
```
