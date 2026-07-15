#!/usr/bin/env python3
"""compose_poster.py — assemble a self-contained poster TEMPLATE from 3 axes.

The poster source is decoupled into three orthogonal axes under <skill>/assets/:

    layouts/<layout>.html   STRUCTURE  — column grid + .section cards + base CSS,
                            with a {{HEADER}} hook in <body> and a {{STYLE_CSS}}
                            hook in <head>.
    styles/<style>.css      VISUAL     — :root theme vars + .section / .section
                            ::before / .section h2 treatment (solid|framed|simple).
    headers/<header>.html   TITLEBAR   — the header partial: its own <style> +
                            the <header class="titlebar" data-section="title"> HTML
                            (v1..v4).

compose(layout, style, header, outpath) reads the layout, injects the style CSS at
{{STYLE_CSS}} and the header HTML at {{HEADER}}, and writes ONE self-contained
poster.html — structurally identical to the old monolithic poster_<layout>_<style>
.html, so check_poster.py / render_poster.py and the staged-fill loop work unchanged.

WHY COMPOSE (not ship runtime CSS): the rendered poster.html must stay
self-contained (inline CSS, local fonts, MathJax) AND the full ~100 KB HTML must
never pass through a tool-call's output channel (token-cap abort). So we decouple
the SOURCE on disk and compose at build time — this script reads the pieces and
writes the file; the model only ever emits the small per-paper SUBS later
(see references/build_poster.py).

CONTENT placeholders ({{TITLE}}, {{LOGO_1}}, {{VENUE_LOGO}}, {{PROBLEM}}, …) are
INTENTIONALLY left intact for the downstream build_poster.py SUBS fill — compose
only resolves the two STRUCTURAL hooks ({{STYLE_CSS}}, {{HEADER}}).

Usage:
    python compose_poster.py --layout full --style solid --header v3 --out poster.html
    # then fill content with build_poster.py (cp <chosen pieces> already done here)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# references/ lives directly under the skill root; assets/ is its sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_theme  # noqa: E402  (sibling module; the COLOR axis injector)

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ASSETS = SKILL_DIR / "assets"

# The structural hooks compose resolves. Everything else ({{TITLE}} …) is a
# CONTENT placeholder and must SURVIVE compose for the later SUBS fill.
STRUCT_HOOKS = ("{{STYLE_CSS}}", "{{HEADER}}", "{{SCAN_SECTION}}", "{{MATH_HEAD}}")

# Math-typesetting engine axis (ONE place to switch the default). "katex" renders
# thinner glyphs matching the posterskill look; "mathjax" is the classic MathJax
# tex-svg. Both are bundled offline (assets/{katex,mathjax}/) and intercepted by
# the renderer + html2pptx, and the html2pptx math pass is engine-agnostic, so
# flipping this default (or passing --math / POSTER_MATH) needs no other change.
MATH_ENGINE_DEFAULT = "katex"
MATH_ENGINES = ("katex", "mathjax")


def _options(directory: Path, suffix: str) -> list[str]:
    """Sorted stems of the choosable pieces in a directory (for error messages)."""
    if not directory.is_dir():
        return []
    return sorted(p.name[: -len(suffix)] for p in directory.glob(f"*{suffix}"))


def _rand_pick_list(opts: list[str], seed: str) -> str:
    """Deterministically pick one of an explicit ``opts`` list keyed by ``seed`` (SHA-256)."""
    if not opts:
        sys.exit(f"_rand_pick_list: empty option list for seed {seed!r}")
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    return opts[h % len(opts)]


def _rand_pick(directory: Path, suffix: str, seed: str, exclude: tuple = ()) -> str:
    """Deterministically pick one option from ``directory`` keyed by ``seed`` (SHA-256).
    Reproducible — a wave of posters seeded by their output paths gets a stable SPREAD
    across the options, with no flaky model 'pick random' step. ``exclude`` drops names."""
    opts = [o for o in _options(directory, suffix) if o not in exclude]
    if not opts:
        sys.exit(f"_rand_pick: no options in {directory} (excluding {exclude})")
    return _rand_pick_list(opts, seed)


# Scan-to-Read variant groups. The build passes --scan single|dual based ONLY on whether a
# code QR exists (single = paper-only, dual = paper+code); compose then picks a concrete
# variant WITHIN the group, keyed by the output path — a reproducible spread that still
# guarantees a 2-QR layout never lands on a 1-QR paper. "directory" works in either group.
SCAN_GROUPS = {
    "single": ["hero", "contact", "directory", "banner"],
    "dual": ["twin", "chips", "directory"],
}

# Variants that render exactly ONE QR tile (paper only). "directory" and the whole
# "dual" group render two, so they are NOT here. Used by the QR-count guard below.
SCAN_SINGLE_ONLY = {"hero", "contact", "banner"}


def _count_qrs(outpath: Path) -> int:
    """Count QR images that exist on disk for this poster, read from
    <outdir>/assets/meta/metadata.json (written by paper2assets make_qr.py).
    Returns 0 on ANY failure so the caller safely falls back to the passed --scan."""
    try:
        base = outpath.resolve().parent
        data = json.loads((base / "assets" / "meta" / "metadata.json")
                          .read_text(encoding="utf-8"))
        n = 0
        for q in (data.get("qr") or []):
            p = q.get("path") or ""
            if p and (base / p).exists():
                n += 1
        return n
    except Exception:
        return 0


def compose(layout: str, style: str, header: str, outpath, *,
            scan: str = "aside", theme: str = "random",
            orientation: str = "landscape", math: str | None = None,
            assets: Path = DEFAULT_ASSETS) -> Path:
    """Read the layout, inject styles/<style>.css at {{STYLE_CSS}} (+ landscape:
    headers/<header>.html at {{HEADER}} and scan/<scan>.html at {{SCAN_SECTION}}),
    write a self-contained poster template to ``outpath``, then apply the COLOR
    axis: resolve ``theme`` (``random`` = deterministic pick keyed by outpath) and
    rewrite the :root accent vars in place. Returns the output Path.

    ``orientation`` = ``landscape`` (default) reads assets/layouts/ and composes
    all four axes. ``portrait`` reads assets/layouts_portrait/ and composes the
    STYLE axis only — portrait keeps its titlebar inline and has no Scan-to-Read
    section, so it resolves neither header nor scan. Exits non-zero on any error."""
    is_portrait = orientation == "portrait"
    layouts = assets / ("layouts_portrait" if is_portrait else "layouts")
    styles = assets / "styles"
    headers = assets / ("headers_portrait" if is_portrait else "headers")
    scans = assets / "scan"
    math_dir = assets / "math"
    # Math engine: --math wins, then POSTER_MATH env, then the module default.
    # Applies to BOTH orientations ({{MATH_HEAD}} lives in every template).
    engine = (math or os.environ.get("POSTER_MATH") or MATH_ENGINE_DEFAULT).strip().lower()
    if engine not in MATH_ENGINES:
        sys.exit(f"compose: unknown --math '{engine}'; "
                 f"choose from {', '.join(MATH_ENGINES)}")
    # Resolve "random" deterministically from the output path (stable, reproducible
    # spread across a wave — no flaky model pick).
    if style == "random":
        style = _rand_pick(styles, ".css", str(outpath) + "|style")
    if layout == "random":
        # methoddriven is OPT-IN (only when the user explicitly asks for a
        # method-driven poster) — never let --layout random select it.
        layout = _rand_pick(layouts, ".html", str(outpath) + "|layout",
                            exclude=("methoddriven", "methoddriven4"))
    if header == "random":
        header = _rand_pick(headers, ".html", str(outpath) + "|header")
    if not is_portrait:
        # 3col carries NO QR (the wide-column scan-to-read is suppressed, and v5 would add a
        # titlebar QR), so a 3col poster never uses the v5 header — re-pick from v1-v4.
        if layout == "3col" and header == "v5":
            header = _rand_pick(headers, ".html", str(outpath) + "|header3col", exclude=("v5",))
        # scan: a GROUP keyword (single|dual) picks a variant WITHIN that group; "random"
        # picks any installed variant; an explicit name is used as-is. All keyed by outpath.
        # Belt-and-suspenders QR-count guard: a single-QR context (the "single" group OR an
        # explicit hero/contact/banner) chosen for a paper whose metadata carries >=2 QR
        # files silently drops the second QR (observed on paper 2607: scan-hero showed only
        # the paper QR, not the project QR). Force the dual group so both codes render.
        # Fully guarded via _count_qrs (returns 0 on any error) so it never breaks compose.
        if (scan == "single" or scan in SCAN_SINGLE_ONLY) and _count_qrs(Path(outpath)) >= 2:
            print(f"[compose] metadata has >=2 QRs but --scan={scan} is single-QR "
                  f"-> upgrading to the dual group so both codes render", file=sys.stderr)
            scan = "dual"
        if scan in SCAN_GROUPS:
            avail = [s for s in SCAN_GROUPS[scan] if (scans / f"{s}.html").exists()]
            scan = _rand_pick_list(avail or SCAN_GROUPS[scan], str(outpath) + "|scan")
        elif scan == "random":
            scan = _rand_pick(scans, ".html", str(outpath) + "|scan")
    # color: resolve the theme up front (deterministic per outpath) so the echo
    # reports the REAL color; the swap itself happens after the file is written.
    theme = apply_theme.resolve_theme(theme, str(outpath) + "|theme")
    lp = layouts / f"{layout}.html"
    sp = styles / f"{style}.css"
    hp = headers / f"{header}.html"
    mp = math_dir / f"{engine}.html"
    # Echo the RESOLVED axes (after random/group/3col-v5 resolution) so the caller can
    # branch on the real layout. main()'s summary below echoes the raw CLI args.
    tail = (f"scan={scan} " if not is_portrait else "")
    print(f"compose: orientation={orientation} layout={layout} style={style} "
          f"header={header} {tail}math={engine} theme={theme}", flush=True)

    checks = [(lp, "layout", _options(layouts, ".html")),
              (sp, "style", _options(styles, ".css")),
              (hp, "header", _options(headers, ".html")),
              (mp, "math", _options(math_dir, ".html"))]
    if not is_portrait:
        scp = scans / f"{scan}.html"
        checks += [(scp, "scan", _options(scans, ".html"))]
    for path, kind, opts in checks:
        if not path.exists():
            sys.exit(f"compose: {kind} '{path.stem}' not found at {path}\n"
                     f"  available {kind}s: {', '.join(opts) or '(none)'}")

    html = lp.read_text(encoding="utf-8")
    pieces = {"{{STYLE_CSS}}": (sp.read_text(encoding="utf-8"), sp.name),
              "{{HEADER}}": (hp.read_text(encoding="utf-8"), hp.name),
              "{{MATH_HEAD}}": (mp.read_text(encoding="utf-8"), mp.name)}
    if not is_portrait:
        pieces["{{SCAN_SECTION}}"] = (scp.read_text(encoding="utf-8"), scp.name)

    # A style/header piece must never itself carry a STRUCTURAL hook (would recurse
    # / leave a dangling hook). Content placeholders inside the header are fine.
    for hook, (value, src) in pieces.items():
        for other in STRUCT_HOOKS:
            if other in value:
                sys.exit(f"compose: piece {src} unexpectedly contains {other}")

    # Inject each structural hook EXACTLY once.
    for hook, (value, src) in pieces.items():
        n = html.count(hook)
        if n != 1:
            sys.exit(f"compose: layout {lp.name} must contain exactly one {hook}, "
                     f"found {n}")
        html = html.replace(hook, value, 1)

    # Figure-fill floor for the client-side fit() script, kept in sync with the
    # POSTER_FIG_MIN_RATIO gate (default 0.90). Plain replace-all (NOT a structural
    # hook) so templates without the token are a no-op.
    html = html.replace("{{FIG_MIN_RATIO}}",
                        os.environ.get("POSTER_FIG_MIN_RATIO", "0.90"))

    # No structural hook may survive; content {{...}} placeholders are expected to.
    leftover_struct = [h for h in STRUCT_HOOKS if h in html]
    if leftover_struct:
        sys.exit(f"compose: structural hook(s) still present after inject: "
                 f"{leftover_struct}")

    out = Path(outpath)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    # COLOR axis: rewrite the :root accent vars to the resolved theme in place.
    themed, _ = apply_theme.recolor(out.read_text(encoding="utf-8"),
                                    apply_theme.THEMES[theme])
    out.write_text(themed, encoding="utf-8")
    return out


def _self_containment_warnings(html: str) -> list[str]:
    """Best-effort: flag external CSS that would break the self-contained invariant.
    External <link rel=stylesheet> or @import is a hard violation; the MathJax CDN
    <script src> AND the KaTeX CDN css/js are the allowed externals (both mirrored
    offline by the skill + intercepted by the renderer), so they are NOT flagged."""
    warns = []
    # Strip the KaTeX CDN stylesheet link before the generic check — it is an
    # allowed, offline-mirrored external (assets/katex/), like the MathJax script.
    scrubbed = re.sub(
        r'<link\b[^>]*href\s*=\s*["\']?[^"\'>]*katex[^"\'>]*\.css[^>]*>', '', html, flags=re.I)
    if re.search(r'<link\b[^>]*\brel\s*=\s*["\']?stylesheet', scrubbed, re.I):
        warns.append("external stylesheet <link rel=stylesheet> present")
    if re.search(r'@import\b', html):
        warns.append("CSS @import present")
    return warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="compose_poster",
        description="Compose a self-contained poster template from "
                    "layout × style × header.",
    )
    ap.add_argument("--layout", required=True,
                    help="structure: full | half | 3col | random")
    ap.add_argument("--style", default="solid",
                    help="visual style: solid | framed | simple (default solid)")
    ap.add_argument("--header", default="random",
                    help="titlebar variant (default random): landscape v1-v5, "
                         "portrait pv1-pv5")
    ap.add_argument("--scan", default="aside",
                    help="Scan-to-Read variant: single | dual (group keyword — "
                         "recommended; compose picks within the group) | random | "
                         "aside | hero | contact | directory | banner | twin | chips "
                         "(default aside)")
    ap.add_argument("--out", default="poster.html",
                    help="output path (default ./poster.html)")
    ap.add_argument("--theme", default="random",
                    help="COLOR axis: random (default; deterministic per output "
                         "path) | " + " | ".join(sorted(apply_theme.THEMES)))
    ap.add_argument("--orientation", default="landscape",
                    choices=("landscape", "portrait"),
                    help="landscape (default; 4 axes) | portrait (layouts_portrait/, "
                         "STYLE + COLOR only — inline titlebar, no scan)")
    ap.add_argument("--math", default=None, choices=MATH_ENGINES,
                    help=f"math engine (default {MATH_ENGINE_DEFAULT}; also "
                         f"POSTER_MATH env): katex (thin, posterskill-like) | mathjax")
    ap.add_argument("--assets", default=None,
                    help="override the assets/ dir (default: the skill's assets/)")
    a = ap.parse_args(argv)

    assets = Path(a.assets).resolve() if a.assets else DEFAULT_ASSETS
    out = compose(a.layout, a.style, a.header, a.out, scan=a.scan, theme=a.theme,
                  orientation=a.orientation, math=a.math, assets=assets)

    txt = out.read_text(encoding="utf-8")
    leftover = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", txt)))
    _eng = (a.math or os.environ.get("POSTER_MATH") or MATH_ENGINE_DEFAULT)
    print(f"composed {a.layout}+{a.style}+{a.header}+scan:{a.scan}+math:{_eng} -> {out} "
          f"({out.stat().st_size} bytes)")
    if leftover:
        print(f"  content placeholders awaiting SUBS fill: {', '.join(leftover)}")
    for w in _self_containment_warnings(txt):
        print(f"  WARN: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
