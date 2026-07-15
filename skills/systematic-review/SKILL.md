---
name: systematic-review
description: >
  Use this Skill when conducting a systematic literature review following PRISMA 2020:
  PICO framework, database search strategy, title/abstract screening, full-text
  eligibility, data extraction, and GRADE evidence grading.
tags:
  - universal
  - systematic-review
  - PRISMA
  - evidence-synthesis
  - meta-research
version: "1.0.0"
authors:
  - name: awesome-rosetta-skills contributors
    github: "@xjtulyc"
license: "MIT"
platforms:
  - claude-code
  - codex
  - gemini-cli
  - cursor
dependencies:
  python:
    - pybtex>=0.24
    - pandas>=1.5
    - matplotlib>=3.6
    - requests>=2.28
last_updated: "2026-03-17"
status: stable
---

# Systematic Literature Review (PRISMA 2020)

> **TL;DR** — Conduct a rigorous systematic review using the PRISMA 2020 framework:
> build PICO-based search queries, search multiple databases via API, deduplicate
> records, run two-stage screening, extract data into a structured DataFrame, apply
> GRADE evidence grading, and generate the PRISMA flow diagram automatically.

---

## When to Use This Skill

Use this Skill whenever you need to:

- Summarize evidence on a clinical, policy, or scientific question following PRISMA 2020
- Build reproducible, documented search strategies across PubMed, Embase, Cochrane, or Scopus
- Track the screening process and record reasons for exclusion at each stage
- Extract structured data from included studies into a machine-readable format
- Grade the certainty of evidence using the GRADE framework
- Generate the mandatory PRISMA flow diagram for journal submission

| Task | When to apply |
|---|---|
| Database search | Need comprehensive evidence retrieval |
| Deduplication | After merging records from ≥2 databases |
| Title/abstract screening | First-pass filter on thousands of records |
| Full-text eligibility | Detailed inclusion/exclusion assessment |
| Data extraction | Populate the evidence table |
| GRADE grading | Communicate certainty to clinicians or policymakers |

---

## Background & Key Concepts

### PRISMA 2020

PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) 2020
defines a four-stage flowchart:

1. **Identification** — Records retrieved from databases + other sources
2. **Screening** — Records after deduplication; title/abstract screened; reasons for exclusion
3. **Eligibility** — Full-text assessed; reasons for exclusion recorded
4. **Included** — Studies included in the review (and meta-analysis if applicable)

### PICO Framework

| Element | Definition | Example |
|---|---|---|
| **P**opulation | Who are the subjects? | Adults with type-2 diabetes |
| **I**ntervention | What is being tested? | SGLT2 inhibitor |
| **C**omparator | What is the control? | Placebo or standard care |
| **O**utcome | What is measured? | HbA1c reduction at 24 weeks |

### GRADE Evidence Certainty

| Level | Meaning | Typical study type |
|---|---|---|
| High | True effect is close to estimate | Well-conducted RCTs |
| Moderate | Moderate confidence; true effect likely similar | RCTs with limitations |
| Low | Limited confidence | Observational studies |
| Very Low | Very uncertain | Case series, expert opinion |

GRADE certainty starts at "High" for RCTs and can be downgraded for risk of bias,
inconsistency, indirectness, imprecision, and publication bias.

---

## Environment Setup

```bash
# Create and activate a dedicated conda environment
conda create -n sysrev python=3.11 -y
conda activate sysrev

# Install required packages
pip install pybtex pandas matplotlib requests

# Verify installation
python -c "import pandas, matplotlib, requests; print('Setup OK')"
```

For PubMed API access, register for an NCBI API key to raise the rate limit from
3 to 10 requests per second:

```bash
# Register at: https://www.ncbi.nlm.nih.gov/account/
# Then set the environment variable:
export NCBI_API_KEY="<paste-your-key>"

# Verify
python -c "import os; print(os.getenv('NCBI_API_KEY', 'NOT SET'))"
```

---

## Core Workflow

### Step 1 — Build Search Strategy and Query Databases

The following code implements a PubMed search using the NCBI E-utilities API.
It constructs a PICO-based Boolean query and retrieves PubMed IDs (PMIDs) along
with article metadata.

```python
import os
import time
import requests
import pandas as pd
from typing import List, Optional

# export NCBI_API_KEY="<paste-your-key>"
NCBI_API_KEY: Optional[str] = os.getenv("NCBI_API_KEY")
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def build_pico_query(
    population: List[str],
    intervention: List[str],
    comparator: Optional[List[str]] = None,
    outcome: Optional[List[str]] = None,
    study_filters: Optional[List[str]] = None,
) -> str:
    """
    Build a PubMed Boolean search string from PICO components.

    Each list element within a PICO component is joined with OR;
    the components are joined with AND.

    Args:
        population:     MeSH terms / free-text for the target population.
        intervention:   MeSH terms / free-text for the intervention.
        comparator:     MeSH terms / free-text for the comparator (optional).
        outcome:        MeSH terms / free-text for the outcome (optional).
        study_filters:  Filters such as 'Randomized Controlled Trial[pt]'.

    Returns:
        PubMed query string suitable for the esearch endpoint.

    Example:
        >>> q = build_pico_query(
        ...     population=["type 2 diabetes[MeSH]", "T2DM"],
        ...     intervention=["SGLT2 inhibitor[MeSH]", "empagliflozin", "dapagliflozin"],
        ...     outcome=["HbA1c", "glycated hemoglobin"],
        ...     study_filters=["Randomized Controlled Trial[pt]"],
        ... )
    """
    def join_component(terms: List[str]) -> str:
        return "(" + " OR ".join(terms) + ")"

    parts = [join_component(population), join_component(intervention)]
    if comparator:
        parts.append(join_component(comparator))
    if outcome:
        parts.append(join_component(outcome))
    if study_filters:
        parts.append(join_component(study_filters))

    return " AND ".join(parts)


def search_pubmed(
    query: str,
    max_results: int = 500,
    date_range: Optional[tuple] = None,
) -> List[str]:
    """
    Search PubMed via E-utilities and return a list of PMIDs.

    Args:
        query:       Boolean PubMed query string.
        max_results: Maximum number of PMIDs to retrieve.
        date_range:  Optional (min_date, max_date) tuple, format 'YYYY/MM/DD'.

    Returns:
        List of PMID strings.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "usehistory": "y",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    if date_range:
        params["mindate"], params["maxdate"] = date_range
        params["datetype"] = "pdat"

    resp = requests.get(f"{NCBI_BASE}/esearch.fcgi", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    pmids = data["esearchresult"]["idlist"]
    total = int(data["esearchresult"]["count"])
    print(f"PubMed: {total} total hits; retrieved {len(pmids)} PMIDs.")
    return pmids


def fetch_pubmed_summaries(pmids: List[str], batch_size: int = 100) -> pd.DataFrame:
    """
    Fetch article metadata for a list of PMIDs using eSummary.

    Args:
        pmids:      List of PMID strings.
        batch_size: Number of IDs per API request (max 200 recommended).

    Returns:
        DataFrame with columns: pmid, title, authors, journal, year, abstract_flag.
    """
    records = []
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i : i + batch_size]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "json",
        }
        if NCBI_API_KEY:
            params["api_key"] = NCBI_API_KEY

        resp = requests.get(f"{NCBI_BASE}/esummary.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        result = resp.json().get("result", {})

        for pmid in batch:
            art = result.get(pmid, {})
            authors = "; ".join(
                a.get("name", "") for a in art.get("authors", [])
            )
            records.append({
                "pmid": pmid,
                "title": art.get("title", ""),
                "authors": authors,
                "journal": art.get("fulljournalname", ""),
                "year": art.get("pubdate", "")[:4],
                "source": "PubMed",
                "screen_status": "pending",
            })
        time.sleep(0.15)  # respect rate limit

    return pd.DataFrame(records)


# ── Usage example ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    query = build_pico_query(
        population=["type 2 diabetes[MeSH]", "T2DM"],
        intervention=["SGLT2 inhibitor[MeSH]", "empagliflozin", "dapagliflozin"],
        outcome=["HbA1c", "glycated hemoglobin"],
        study_filters=["Randomized Controlled Trial[pt]"],
    )
    print("Query:", query)
    pmids = search_pubmed(query, max_results=200)
    df_pubmed = fetch_pubmed_summaries(pmids)
    df_pubmed.to_csv("pubmed_results.csv", index=False)
    print(df_pubmed.head())
```

### Step 2 — Deduplicate and Screen Records

After merging results from multiple databases, remove duplicates by title similarity
and track screening decisions in a structured DataFrame.

```python
import hashlib
import re
import pandas as pd
from typing import Dict


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy matching."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def deduplicate_records(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge records from multiple databases and deduplicate by normalized title.

    Args:
        dfs: Dictionary mapping source name -> DataFrame with at least 'title' column.

    Returns:
        Deduplicated DataFrame with a 'duplicate_removed' flag column and
        PRISMA stage counts printed to stdout.
    """
    combined = pd.concat(list(dfs.values()), ignore_index=True)
    total_retrieved = len(combined)
    print(f"PRISMA Stage 1 — Identification: {total_retrieved} records retrieved")

    # Generate a hash key from the normalized title
    combined["title_norm"] = combined["title"].fillna("").apply(normalize_title)
    combined["title_hash"] = combined["title_norm"].apply(
        lambda t: hashlib.md5(t.encode()).hexdigest()
    )

    # Keep first occurrence of each title hash
    combined["duplicate_removed"] = combined.duplicated(subset="title_hash", keep="first")
    n_duplicates = combined["duplicate_removed"].sum()
    n_after_dedup = total_retrieved - n_duplicates
    print(f"PRISMA Stage 2a — Deduplication: {n_duplicates} duplicates removed; "
          f"{n_after_dedup} records remain")

    combined["screen_status"] = "pending"
    combined["exclude_reason"] = ""
    return combined.reset_index(drop=True)


def apply_title_abstract_screen(
    df: pd.DataFrame,
    include_keywords: list,
    exclude_keywords: list,
) -> pd.DataFrame:
    """
    Automated title/abstract screening by keyword matching.

    In real practice, two independent reviewers screen manually and resolve
    disagreements. This function demonstrates automated pre-screening for
    efficiency in large retrieval sets.

    Args:
        df:                Combined, deduplicated records DataFrame.
        include_keywords:  Records MUST match at least one of these.
        exclude_keywords:  Records are excluded if they match any of these.

    Returns:
        DataFrame with 'screen_status' updated to 'include', 'exclude', or 'unclear'.
    """
    df = df.copy()
    search_text = (df["title"].fillna("") + " " + df.get("abstract", pd.Series([""] * len(df)))).str.lower()

    has_include = search_text.apply(
        lambda t: any(kw.lower() in t for kw in include_keywords)
    )
    has_exclude = search_text.apply(
        lambda t: any(kw.lower() in t for kw in exclude_keywords)
    )

    df.loc[df["duplicate_removed"], "screen_status"] = "duplicate"
    df.loc[~df["duplicate_removed"] & ~has_include, "screen_status"] = "exclude"
    df.loc[~df["duplicate_removed"] & ~has_include, "exclude_reason"] = "no relevant keywords"
    df.loc[~df["duplicate_removed"] & has_exclude, "screen_status"] = "exclude"
    df.loc[~df["duplicate_removed"] & has_exclude, "exclude_reason"] = "exclusion keyword match"
    df.loc[~df["duplicate_removed"] & has_include & ~has_exclude, "screen_status"] = "include"

    counts = df["screen_status"].value_counts()
    print(f"PRISMA Stage 2b — Title/Abstract Screen:\n{counts.to_string()}")
    return df


# ── Screening tracker ─────────────────────────────────────────────────────────
def create_screening_tracker(df: pd.DataFrame, output_path: str = "screening_tracker.csv") -> None:
    """Save the screening DataFrame with all PRISMA stage metadata."""
    cols = ["pmid", "title", "authors", "year", "journal", "source",
            "duplicate_removed", "screen_status", "exclude_reason"]
    available = [c for c in cols if c in df.columns]
    df[available].to_csv(output_path, index=False)
    print(f"Screening tracker saved to {output_path}")
```

### Step 3 — Data Extraction, GRADE Grading, and PRISMA Flow Diagram

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from typing import Literal


# ── Data extraction template ──────────────────────────────────────────────────
EXTRACTION_COLUMNS = [
    "study_id", "author", "year", "country", "design", "n_total",
    "n_intervention", "n_control", "population_description",
    "intervention_description", "comparator_description",
    "primary_outcome", "effect_size", "ci_lower", "ci_upper",
    "p_value", "follow_up_weeks", "risk_of_bias", "grade_certainty",
    "notes",
]


def create_extraction_template(output_path: str = "data_extraction.csv") -> pd.DataFrame:
    """Return an empty DataFrame ready for manual data extraction."""
    df = pd.DataFrame(columns=EXTRACTION_COLUMNS)
    df.to_csv(output_path, index=False)
    print(f"Data extraction template saved to {output_path}")
    return df


def grade_evidence(
    study_design: Literal["RCT", "cohort", "case-control", "cross-sectional", "case-series"],
    risk_of_bias: Literal["low", "some concerns", "high"],
    inconsistency: bool = False,
    indirectness: bool = False,
    imprecision: bool = False,
    publication_bias: bool = False,
) -> str:
    """
    Apply GRADE evidence grading rules.

    Starting certainty: High for RCTs, Low for observational studies.
    Downgrade one level for each serious concern.

    Args:
        study_design:      Study design type.
        risk_of_bias:      Overall risk of bias assessment.
        inconsistency:     True if I² > 50% or unexplained heterogeneity.
        indirectness:      True if PICO differs importantly from review question.
        imprecision:       True if confidence intervals are wide or n is small.
        publication_bias:  True if funnel plot asymmetry or selective reporting.

    Returns:
        GRADE certainty label: 'High', 'Moderate', 'Low', or 'Very Low'.
    """
    LEVELS = ["Very Low", "Low", "Moderate", "High"]
    start = 3 if study_design == "RCT" else 1  # High vs Low

    downgrades = 0
    if risk_of_bias in ("some concerns",):
        downgrades += 1
    elif risk_of_bias == "high":
        downgrades += 2
    if inconsistency:
        downgrades += 1
    if indirectness:
        downgrades += 1
    if imprecision:
        downgrades += 1
    if publication_bias:
        downgrades += 1

    final_idx = max(0, start - downgrades)
    return LEVELS[final_idx]


def plot_prisma_flowchart(
    n_identified: int,
    n_duplicates: int,
    n_title_excluded: int,
    n_fulltext_assessed: int,
    n_fulltext_excluded: int,
    n_included: int,
    output_path: str = "prisma_flowchart.png",
) -> None:
    """
    Generate a PRISMA 2020 flow diagram using matplotlib.

    Args:
        n_identified:        Total records identified across all databases.
        n_duplicates:        Duplicate records removed.
        n_title_excluded:    Records excluded at title/abstract screen.
        n_fulltext_assessed: Records assessed for full-text eligibility.
        n_fulltext_excluded: Full-text articles excluded with reasons.
        n_included:          Studies included in the review.
        output_path:         File path to save the PNG diagram.
    """
    n_screened = n_identified - n_duplicates

    fig, ax = plt.subplots(figsize=(10, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")
    ax.set_facecolor("white")

    def box(x, y, w, h, text, color="#D6E4F0"):
        rect = mpatches.FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor="#2C5F8A", linewidth=1.5,
        )
        ax.add_patch(rect)
        ax.text(x, y, text, ha="center", va="center", fontsize=9,
                wrap=True, multialignment="center")

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#2C5F8A", lw=1.5))

    # Identification
    box(5, 13, 6, 1.0,
        f"Records identified from databases\n(n = {n_identified})")
    # Deduplication
    box(5, 11.2, 6, 1.0,
        f"Records after duplicates removed\n(n = {n_screened})\nDuplicates removed: {n_duplicates}")
    arrow(5, 12.5, 5, 11.7)

    # Screening
    box(5, 9.3, 6, 1.0,
        f"Records screened\n(n = {n_screened})")
    box(8.5, 9.3, 2.5, 1.0,
        f"Excluded\n(n = {n_title_excluded})",
        color="#FAD7A0")
    arrow(5, 10.7, 5, 9.8)
    ax.annotate("", xy=(7.2, 9.3), xytext=(6.2, 9.3),  # sideways
                arrowprops=dict(arrowstyle="->", color="#2C5F8A", lw=1.5))

    # Eligibility
    box(5, 7.3, 6, 1.0,
        f"Full-text articles assessed\n(n = {n_fulltext_assessed})")
    box(8.5, 7.3, 2.5, 1.0,
        f"Excluded\n(n = {n_fulltext_excluded})",
        color="#FAD7A0")
    arrow(5, 8.8, 5, 7.8)
    ax.annotate("", xy=(7.2, 7.3), xytext=(6.2, 7.3),
                arrowprops=dict(arrowstyle="->", color="#2C5F8A", lw=1.5))

    # Included
    box(5, 5.3, 6, 1.0,
        f"Studies included in review\n(n = {n_included})",
        color="#D5F5E3")
    arrow(5, 6.8, 5, 5.8)

    ax.set_title("PRISMA 2020 Flow Diagram", fontsize=13, fontweight="bold", pad=10)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"PRISMA flowchart saved to {output_path}")


# ── End-to-end demo ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simulate PRISMA stage counts
    plot_prisma_flowchart(
        n_identified=1842,
        n_duplicates=324,
        n_title_excluded=1287,
        n_fulltext_assessed=231,
        n_fulltext_excluded=198,
        n_included=33,
        output_path="prisma_flowchart.png",
    )

    # Create extraction template
    tmpl = create_extraction_template("data_extraction.csv")

    # Example GRADE assessment
    certainty = grade_evidence(
        study_design="RCT",
        risk_of_bias="some concerns",
        inconsistency=True,
        imprecision=False,
    )
    print(f"GRADE certainty: {certainty}")  # -> Moderate
```

---

## Advanced Usage

### Multi-Database Search Strategy

For a comprehensive systematic review, search at least three databases. Below are
representative query translations for the same PICO question across platforms:

| Database | Query syntax | Access method |
|---|---|---|
| PubMed | MeSH terms + Boolean | E-utilities REST API (see Step 1) |
| Embase | Emtree terms + `.de.` tags | Institutional Elsevier API |
| Cochrane | MeSH + free-text | Cochrane REST API or manual export |
| Scopus | TITLE-ABS-KEY() | Elsevier Scopus API |

**Sample Scopus query (same PICO):**

```
TITLE-ABS-KEY(
  ("type 2 diabetes" OR "T2DM")
  AND ("SGLT2 inhibitor" OR "empagliflozin" OR "dapagliflozin")
  AND ("HbA1c" OR "glycated hemoglobin")
  AND ("randomized controlled trial" OR "RCT")
)
AND PUBYEAR > 2010
AND DOCTYPE(ar)
```

### Risk of Bias Assessment

For RCTs, use the Cochrane RoB 2.0 tool. Assess five domains:

1. Randomization process
2. Deviations from intended intervention
3. Missing outcome data
4. Measurement of the outcome
5. Selection of the reported result

Store judgements in the extraction DataFrame under `risk_of_bias` column
(`'low'`, `'some concerns'`, or `'high'`).

### GRADE Evidence Profile Table

After extracting data and grading certainty, summarize findings in a GRADE
evidence profile table. Columns: Outcome, No. studies, No. participants,
Relative effect (95% CI), Absolute effect, Certainty, Importance.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `requests.HTTPError: 429` | PubMed rate limit exceeded | Set NCBI_API_KEY; add `time.sleep(0.15)` between requests |
| `KeyError: 'esearchresult'` | Empty query or API outage | Validate query string; retry with exponential back-off |
| Very high deduplication rate | Overly broad query | Tighten MeSH terms; add study-type filter |
| Very low retrieval | Overly narrow query | Broaden with OR synonyms; add free-text variants |
| matplotlib box overlap | Too many PRISMA stages shown | Adjust `figsize` and y-coordinates in `plot_prisma_flowchart` |
| Inconsistent GRADE ratings | Subjective domain judgments | Use the official GRADEpro GDT web tool for consensus grading |

---

## External Resources

- PRISMA 2020 statement: <https://www.prisma-statement.org/prisma-2020>
- NCBI E-utilities guide: <https://www.ncbi.nlm.nih.gov/books/NBK25499/>
- Cochrane Handbook (Chapter 6 — searching): <https://training.cochrane.org/handbook>
- GRADE handbook: <https://gdt.gradepro.org/app/handbook/handbook.html>
- Covidence systematic review software: <https://www.covidence.org>
- rayyan.ai (free screening tool): <https://www.rayyan.ai>

---

## Examples

### Example 1 — Full PubMed Search + Deduplication Pipeline

```python
# Assumes NCBI_API_KEY is set in environment
query = build_pico_query(
    population=["heart failure[MeSH]", "cardiac failure"],
    intervention=["sacubitril[MeSH]", "valsartan", "LCZ696"],
    outcome=["mortality", "hospitalization", "ejection fraction"],
    study_filters=["Randomized Controlled Trial[pt]", "Clinical Trial[pt]"],
)

pmids = search_pubmed(query, max_results=300, date_range=("2010/01/01", "2026/01/01"))
df_pubmed = fetch_pubmed_summaries(pmids)

# Simulate adding a second source (e.g., manual Embase export)
df_embase = pd.read_csv("embase_export.csv")  # must have 'title', 'authors', 'year' cols
df_embase["source"] = "Embase"
df_embase["screen_status"] = "pending"

combined = deduplicate_records({"PubMed": df_pubmed, "Embase": df_embase})

screened = apply_title_abstract_screen(
    combined,
    include_keywords=["heart failure", "sacubitril", "LCZ696"],
    exclude_keywords=["animal study", "in vitro", "pediatric"],
)
create_screening_tracker(screened, "hf_screening_tracker.csv")
```

### Example 2 — Batch GRADE Assessment for Multiple Outcomes

```python
outcomes = [
    {"name": "All-cause mortality", "design": "RCT", "rob": "low",
     "inconsistency": False, "indirectness": False, "imprecision": False, "pub_bias": False},
    {"name": "HF hospitalization",  "design": "RCT", "rob": "some concerns",
     "inconsistency": True,  "indirectness": False, "imprecision": False, "pub_bias": False},
    {"name": "eGFR change",         "design": "cohort", "rob": "low",
     "inconsistency": False, "indirectness": True,  "imprecision": True,  "pub_bias": False},
]

grade_rows = []
for o in outcomes:
    certainty = grade_evidence(
        study_design=o["design"],
        risk_of_bias=o["rob"],
        inconsistency=o["inconsistency"],
        indirectness=o["indirectness"],
        imprecision=o["imprecision"],
        publication_bias=o["pub_bias"],
    )
    grade_rows.append({"outcome": o["name"], "certainty": certainty})

grade_df = pd.DataFrame(grade_rows)
print(grade_df.to_string(index=False))
```

### Example 3 — Generate PRISMA Diagram from Screening Tracker

```python
df = pd.read_csv("hf_screening_tracker.csv")

n_identified   = len(df)
n_duplicates   = df["duplicate_removed"].sum()
n_screened     = n_identified - n_duplicates
n_ta_excluded  = (df["screen_status"] == "exclude").sum()
n_ft_assessed  = (df["screen_status"] == "include").sum()  # pending full-text
n_ft_excluded  = int(n_ft_assessed * 0.7)                  # placeholder
n_included     = n_ft_assessed - n_ft_excluded

plot_prisma_flowchart(
    n_identified=n_identified,
    n_duplicates=int(n_duplicates),
    n_title_excluded=int(n_ta_excluded),
    n_fulltext_assessed=int(n_ft_assessed),
    n_fulltext_excluded=n_ft_excluded,
    n_included=n_included,
    output_path="prisma_hf_review.png",
)
```

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-03-17 | Initial release — PubMed search, deduplication, screening, GRADE, PRISMA flowchart |
