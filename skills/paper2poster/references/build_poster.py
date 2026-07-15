#!/usr/bin/env python3
"""
build_poster.py — REFERENCE SKELETON for INDIRECT poster generation.

WHY THIS EXISTS
  poster.html is ~100 KB. Emitting it inline with the Write tool is ~30-40k tokens
  in a single reply, which overflows the per-turn output cap
  (CLAUDE_CODE_MAX_OUTPUT_TOKENS, default 32000) and ABORTS the run — and the
  measured-fill loop would re-pay that every round. This pattern keeps the bulk
  TEMPLATE on disk: you shell-`cp` the template to poster.html, then this script
  reads it and you only emit the small paper-specific content (the SUBS values).
  The template never passes through your (model) output channel.

HOW TO USE  (copy this file next to the poster, fill SUBS, run it)
  1. cp <skill>/assets/<chosen_template>.html <outdir>/poster.html
  2. Edit SUBS below with THIS paper's content. See
     references/template_substitution.md for what every placeholder means and the
     lean-render policy (which optional sections / Additional text to withhold).
  3. python build_poster.py            # rewrites ./poster.html in place
     python build_poster.py other.html # or target a different file

PATHS ARE RELATIVE ON PURPOSE — never hardcode an absolute path here. Figure / logo
/ qr values are paths relative to the poster, e.g. "assets/figures/page1_figure1.png",
"assets/logos/mit.png", "assets/qr/paper.png".
"""
import re
import sys
from pathlib import Path


def drop_section(doc: str, sec: str) -> str:
    """Remove the whole `<div class="section ..." data-section="sec">...</div>` block.
    Depth-aware: section divs contain nested divs, so a naive regex would stop at the
    first inner </div>; here we balance <div>/</div> to find the real close."""
    m = re.search(rf'<div\b[^>]*\bdata-section="{re.escape(sec)}"', doc)
    if not m:
        return doc  # section already absent — nothing to drop
    start = doc.rfind("<div", 0, m.end())
    i, depth = start, 0
    while i < len(doc):
        o, c = doc.find("<div", i), doc.find("</div>", i)
        if c == -1:
            return doc  # malformed; leave as-is
        if o != -1 and o < c:
            depth += 1
            i = o + 4
        else:
            depth -= 1
            i = c + len("</div>")
            if depth == 0:
                while i < len(doc) and doc[i] in " \t\r\n":
                    i += 1
                return doc[:start] + doc[i:]
    return doc


target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("poster.html")
html = target.read_text(encoding="utf-8")   # <-- big template read from disk, NOT emitted by you

# --- 1. fill EACH placeholder with this paper's content (this dict is all you emit) ---
#     Section bodies get the Necessary content + at least one content_patterns.md widget.
SUBS = {
    # titlebar / metadata
    "{{TITLE}}":         "...",
    "{{AUTHORS}}":       "...",
    "{{AUTHOR_LEGEND}}": "...",   # e.g. '<sup>1</sup> MIT &nbsp;&nbsp; <sup>2</sup> NUS'
    "{{VENUE}}":         "...",
    "{{VENUE_NAME}}":    "...",
    "{{VENUE_YEAR}}":    "...",
    "{{VENUE_TAG}}":     "...",   # e.g. 'POSTER'
    "{{VENUE_LINK}}":    "...",   # a real URL or '' — never fabricate
    "{{CONTACT}}":       "...",
    # ONE logo slot per institute logo in assets/logos/ (headers expose LOGO_1..6). Fill
    # every slot you have a logo for; leave the rest "". If there are MORE institute logos
    # than slots, that's fine — fit_logos.py AUTO-COMPLETES the header with every logo file
    # on disk, so no institute is dropped even if you under-fill here.
    "{{LOGO_1}}": "...", "{{LOGO_2}}": "...", "{{LOGO_3}}": "...",
    "{{LOGO_4}}": "...", "{{LOGO_5}}": "...", "{{LOGO_6}}": "...",
    # QR slots: take the make_qr manifest `path` verbatim (slot 0 -> QR_PAPER, slot 1 ->
    # QR_CODE). A one-link paper has ONE slot -> leave QR_CODE "". Do NOT write captions:
    # fit_logos.py stamps each tile's Paper/Code/Project label from the manifest.
    "{{QR_PAPER}}": "...", "{{QR_CODE}}": "...",
    # core sections (Necessary only at the lean render)
    "{{PROBLEM}}":              "...",
    "{{MOTIVATION_1}}": "...", "{{MOTIVATION_2}}": "...",
    "{{METHOD_1}}": "...", "{{METHOD_2}}": "...", "{{METHOD_3}}": "...",
    "{{METHOD_FIGURE}}":       "...",   # 'assets/figures/<page>_figure<n>.png'
    "{{METHOD_CAPTION}}":      "...",
    "{{KEY_RESULT_CONCLUSION}}": "...",
    "{{BASELINE}}": "...", "{{BASELINE_NUM}}": "...",
    "{{OURS}}": "...", "{{OURS_NUM}}": "...",
    "{{HERO_VAL}}": "...", "{{HERO_LABEL}}": "...", "{{HERO_NOTE}}": "...",
    "{{HEADLINE_DELTA}}":      "...",
    "{{STAT_2_VAL}}": "...", "{{STAT_2_LBL}}": "...",
    "{{STAT_3_VAL}}": "...", "{{STAT_3_LBL}}": "...",
    "{{STAT_4_VAL}}": "...", "{{STAT_4_LBL}}": "...",
    "{{TAKEAWAY}}":            "...",
    "{{TEASER_FIGURE}}": "...", "{{TEASER_CAPTION}}": "...",
    # OPTIONAL sections — uncomment ONLY for the ones you keep (and drop them from
    # DROP_SECTIONS below). Default lean render withholds all three.
    # "{{CONTRIBUTION_1}}": "...", "{{CONTRIBUTION_2}}": "...", "{{CONTRIBUTION_3}}": "...",
    # "{{DATASET_1}}": "...", "{{DATASET_2}}": "...",
    # "{{ABLATION_1}}": "...", "{{ABLATION_2}}": "...", "{{ABLATION_CONCLUSION}}": "...",
}

# --- 2. lean render: remove the optional <section> blocks you are NOT keeping.
#        Removing a whole block also removes its {{...}} placeholders. Keep the
#        PLAYLIST in sync (drop the section id) so its Listen button doesn't dangle. ---
DROP_SECTIONS = ["contribution", "dataset-benchmark", "ablation-study"]  # trim to keep some
for sec in DROP_SECTIONS:
    html = drop_section(html, sec)
    html = re.sub(rf'"{re.escape(sec)}"\s*,?\s*', "", html)   # best-effort PLAYLIST id removal

# --- 3. substitute ---
missing = [k for k in SUBS if k not in html]
if missing:
    sys.exit(f"placeholder(s) not in template (typo, or the section was dropped?): {missing}")
for token, value in SUBS.items():
    html = html.replace(token, value)

# --- 4. sanity: no {{...}} may survive (fill it or drop its section) ---
leftover = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", html)))
if leftover:
    sys.exit(f"unreplaced placeholders remain: {leftover}")

target.write_text(html, encoding="utf-8")
print(f"wrote {target} ({len(html)} bytes)")
