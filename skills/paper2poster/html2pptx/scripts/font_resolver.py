"""Auto-detect font-family names from an HTML poster and ensure each is
locally installed. Missing fonts are downloaded from Google Fonts when
possible. Idempotent — re-runs skip already-installed families.

Resolves the "PPT renders with wrong fallback because user's machine
doesn't have the font" class of bug, without requiring the user to
maintain a font install manifest.

Usage as module:
    from font_resolver import ensure_fonts_for_html
    installed, missing = ensure_fonts_for_html(Path('poster.html'))

Usage as CLI:
    python -m scripts.font_resolver path/to/poster.html
"""
from __future__ import annotations
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# Generic / system / fallback names that don't resolve to a real font file
CSS_GENERIC = {
    "sans-serif", "serif", "monospace", "cursive", "fantasy",
    "system-ui", "ui-monospace", "ui-sans-serif", "ui-serif", "ui-rounded",
    "math", "emoji", "fangsong", "-apple-system", "BlinkMacSystemFont",
}
# Family names whose absence we don't try to fix via Google Fonts because
# they're OS-shipped (Helvetica, Arial, Times etc.). Their fontconfig
# fallback chain handles them.
NEVER_DOWNLOAD = {
    "Helvetica", "Helvetica Neue", "Arial", "Times", "Times New Roman",
    "Courier", "Courier New", "Verdana", "Tahoma", "Georgia", "Calibri",
    "Cambria", "Segoe UI", "Menlo", "Monaco", "Consolas", "SF Mono",
    "SFMono-Regular", "SF Pro Display", "SF Pro Text", "Apple Color Emoji",
    "Aptos", "Trebuchet MS",
}

FONT_DIR = Path.home() / ".local/share/fonts"
GOOGLE_FONTS_CSS = "https://fonts.googleapis.com/css2"
# UA without WOFF2 support → Google serves plain TTF with .ttf URL.
# Note: stricter UAs like "Mozilla/4.0 (compatible; MSIE 6.0)" cause Google
# to serve extensionless URLs (https://...gstatic.com/l/font?kit=...) that
# our regex won't catch. Plain "Mozilla/4.0" gets clean .ttf URLs.
LEGACY_UA = "Mozilla/4.0"
HTTP_TIMEOUT = 20


def detect_pdf_fonts(pdf_path: Path) -> list[str]:
    """Run `pdffonts` and return unique font family names (with subset
    prefixes like 'AAAAAA+' stripped, and style suffixes like '-Bold'
    normalized off). Used to reverse-engineer what fonts a reference PDF
    actually rendered with — so our HTML→PPT pipeline can match those
    fonts (and thus the PDFs text wrap), rather than the designer-intent
    fonts the CSS asks for."""
    try:
        out = subprocess.run(["pdffonts", str(pdf_path)],
                             capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if out.returncode != 0:
        return []
    families: list[str] = []
    seen: set[str] = set()
    # pdffonts output: skip 2-line header, then one font per line.
    # Format: name, type, encoding, emb, sub, uni, object ID
    for line in out.stdout.splitlines()[2:]:
        if not line.strip() or line.startswith("---"):
            continue
        # The font name is the first whitespace-separated token. May contain
        # a "+" subset prefix like "AAAAAA+Arimo-Bold".
        name = line.split()[0]
        if "+" in name:
            name = name.split("+", 1)[1]
        # Strip common style suffixes — we want the base family name
        for suf in ("-Bold", "-BoldItalic", "-BoldOblique",
                    "-Italic", "-Oblique", "-Regular", "-Light",
                    "-Medium", "-Semibold", "-SemiBold", "-Heavy", "-Black",
                    "-It", "-BoldIt"):
            if name.endswith(suf):
                name = name[: -len(suf)]
                break
        # Skip camelCase splitting — fontconfig handles "DejaVuSansMono",
        # "DejaVu Sans Mono", and similar variants equivalently. Naive
        # split inserts spaces in family names like "DejaVu" → "Deja Vu"
        # which doesnt match how the font self-registers.
        if name and name not in seen:
            seen.add(name)
            families.append(name)
    return families


def build_pdf_alias_map(html_families: list[str],
                        pdf_families: list[str]) -> dict[str, str]:
    """For each HTML font family, pick the most appropriate PDF-rendered
    font as its alias target. Heuristic:
      - mono → mono (matches any PDF font with 'Mono' in the name)
      - serif keywords → first PDF font that looks serif
      - everything else → first PDF font that looks sans
    Empty dict when PDF has no fonts at all (caller falls back to default
    alias behavior)."""
    if not pdf_families:
        return {}

    def is_mono(name: str) -> bool:
        n = name.lower()
        return ("mono" in n) or ("typewriter" in n) or ("courier" in n)

    def is_serif(name: str) -> bool:
        n = name.lower()
        return ("serif" in n) or ("times" in n) or ("tinos" in n) \
               or ("cambria" in n) or ("georgia" in n)

    pdf_mono = next((f for f in pdf_families if is_mono(f)), None)
    pdf_serif = next((f for f in pdf_families if is_serif(f)), None)
    pdf_sans = next((f for f in pdf_families
                     if not is_mono(f) and not is_serif(f)), None)
    if pdf_sans is None and pdf_families:
        pdf_sans = pdf_families[0]  # last-ditch fallback

    aliases: dict[str, str] = {}
    MONO_HINTS = {"mono", "ui-monospace", "sfmono-regular", "sf mono",
                  "menlo", "monaco", "consolas", "courier"}
    SERIF_HINTS = {"serif", "ui-serif", "source serif", "times", "georgia",
                   "cambria", "garamond", "playfair", "merriweather"}
    for fam in html_families:
        # Skip OS-shipped cross-platform fonts (NEVER_DOWNLOAD). Linux's
        # fontconfig falls back consistently for these (e.g. Times New
        # Roman → Liberation Serif) for BOTH browser-side PDF rendering
        # AND soffice's PPT-render, so screenshot diffs stay aligned
        # WITHOUT us aliasing the typeface in the .pptx XML. Aliasing
        # would corrupt the typeface= attribute that PowerPoint on Mac/
        # Win uses to look up the real font on the target platform —
        # i.e. user picks POSTER_FONT=Times New Roman expecting the
        # actual TNR on their Mac, gets LiberationSerif baked into the
        # XML, fails. Same applies to the math-font CSS line
        # `font-family: 'Cambria Math', 'Times New Roman', serif` —
        # listing TNR there used to leak the alias into FONT_ALIASES
        # and corrupt the body text typeface (bug observed 2026-06-11).
        if fam in NEVER_DOWNLOAD:
            continue
        low = fam.lower()
        if any(h in low for h in MONO_HINTS):
            target = pdf_mono or pdf_sans
        elif any(h in low for h in SERIF_HINTS):
            target = pdf_serif or pdf_sans
        else:
            target = pdf_sans
        if target and target != fam:
            aliases[fam] = target
    return aliases


def extract_font_families(html_path: Path) -> list[str]:
    """Pull all font-family declarations from CSS in the HTML, return
    UNIQUE non-generic family names in first-occurrence order."""
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    families: list[str] = []
    seen: set[str] = set()
    # Match `font-family: ...;` declarations
    for decl in re.findall(r"font-family\s*:\s*([^;}\n]+)", text, re.IGNORECASE):
        for raw in decl.split(","):
            name = raw.strip().strip('"').strip("'").strip()
            if not name:
                continue
            # Skip CSS var()/calc() expressions and their leaked tokens
            # (e.g. trailing ")" after `var(--font-mono, ui-monospace, monospace)`)
            if name.startswith("var(") or name.startswith("calc("):
                continue
            if "(" in name or ")" in name:
                # Inside a var() — strip parens, then re-check
                name = name.replace(")", "").replace("(", "").strip()
                if not name:
                    continue
            if name in CSS_GENERIC or name.lower() in {g.lower() for g in CSS_GENERIC}:
                continue
            if name not in seen:
                seen.add(name)
                families.append(name)
    return families


def is_installed(family: str) -> bool:
    """fc-match returns the family name if installed; checks (case-insensitive)
    whether the requested family is the actual resolution (not a fallback)."""
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{family}", family],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    matched = out.stdout.strip().lower()
    return matched == family.lower() or matched.startswith(family.lower() + ",")


def download_from_google_fonts(family: str, dest_dir: Path) -> int:
    """Try to fetch this family from Google Fonts. Returns count of TTFs
    saved. 0 if the family isn't on Google Fonts."""
    # Request regular + 500 + 700 + italics if available; GF will silently
    # drop weights it doesn't have.
    params = {
        "family": f"{family}:ital,wght@0,400;0,500;0,600;0,700;1,400;1,700",
        "display": "swap",
    }
    url = GOOGLE_FONTS_CSS + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": LEGACY_UA})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            if r.status != 200:
                return 0
            css = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return 0
    ttf_urls = re.findall(r"url\((https://[^)]+?\.ttf)\)", css)
    if not ttf_urls:
        return 0  # font exists on Google but no TTF (unlikely w/ legacy UA)
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", family)
    for i, font_url in enumerate(ttf_urls):
        fname = dest_dir / f"{slug}__{i:02d}.ttf"
        if fname.exists() and fname.stat().st_size > 1024:
            saved += 1
            continue
        try:
            with urllib.request.urlopen(font_url, timeout=HTTP_TIMEOUT) as f:
                fname.write_bytes(f.read())
            saved += 1
        except Exception:
            pass
    return saved


def ensure_font_installed_simple(family: str,
                                  font_dir: Path = FONT_DIR) -> bool:
    """Check if `family` is installed. If not and it's not in NEVER_DOWNLOAD
    nor a CSS generic, try Google Fonts download. Returns True if available
    after this call."""
    if not family or family in CSS_GENERIC:
        return True
    if is_installed(family):
        return True
    if family in NEVER_DOWNLOAD or family.lower() in {n.lower() for n in NEVER_DOWNLOAD}:
        return False
    n = download_from_google_fonts(family, font_dir)
    if n > 0:
        subprocess.run(["fc-cache", "-f", str(font_dir)],
                       capture_output=True, timeout=30)
        return is_installed(family)
    return False


RUNTIME_ALIAS_CONF = Path.home() / ".config/fontconfig/conf.d/00-html2pptx-runtime.conf"


def write_runtime_aliases(aliases: dict[str, str]) -> None:
    """Write a fontconfig `<match>` conf that FORCES family X to be served
    as family Y, even if X is installed. Used by --reference-pdf mode so
    the browser's wrap measurement uses the PDFs actual font (Arimo), not
    the CSS-requested font (Inter) — even when Inter is locally installed.

    Idempotent: overwrites previous runtime conf. Pair with
    clear_runtime_aliases() in a finally block so the alias is per-run."""
    RUNTIME_ALIAS_CONF.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '<?xml version="1.0"?>',
        '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">',
        '<fontconfig>',
        '  <!-- generated by html2pptx auto_correct_loop --reference-pdf; safe to delete -->',
    ]
    for src, dst in aliases.items():
        lines.extend([
            '  <match target="pattern">',
            f'    <test name="family" qual="any"><string>{src}</string></test>',
            f'    <edit name="family" mode="prepend_first" binding="strong"><string>{dst}</string></edit>',
            '  </match>',
        ])
    lines.append('</fontconfig>')
    RUNTIME_ALIAS_CONF.write_text("\n".join(lines))
    subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=30)


def clear_runtime_aliases() -> None:
    """Remove the runtime alias conf written by write_runtime_aliases."""
    if RUNTIME_ALIAS_CONF.exists():
        RUNTIME_ALIAS_CONF.unlink()
        subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=30)


def ensure_fonts_for_html(html_path: Path,
                           font_dir: Path = FONT_DIR) -> tuple[list[str], list[str]]:
    """Walk the HTML's font-family declarations and download from Google
    Fonts any that aren't already installed. Returns
    (newly_installed, still_missing) family-name lists."""
    families = extract_font_families(html_path)
    newly_installed: list[str] = []
    still_missing: list[str] = []
    refresh_needed = False
    for fam in families:
        if is_installed(fam):
            continue
        if fam in NEVER_DOWNLOAD or fam.lower() in {n.lower() for n in NEVER_DOWNLOAD}:
            still_missing.append(fam)
            continue
        n = download_from_google_fonts(fam, font_dir)
        if n > 0:
            newly_installed.append(fam)
            refresh_needed = True
        else:
            still_missing.append(fam)
    if refresh_needed:
        subprocess.run(["fc-cache", "-f", str(font_dir)],
                       capture_output=True, timeout=30)
    return newly_installed, still_missing


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <poster.html>", file=sys.stderr)
        sys.exit(2)
    html = Path(sys.argv[1])
    if not html.exists():
        print(f"file not found: {html}", file=sys.stderr)
        sys.exit(1)

    families = extract_font_families(html)
    print(f"[fonts] HTML references {len(families)} non-generic families:",
          file=sys.stderr)
    for fam in families:
        installed = is_installed(fam)
        status = "installed" if installed else "MISSING"
        print(f"  {status:9s}  {fam}", file=sys.stderr)

    installed_now, still_missing = ensure_fonts_for_html(html)
    if installed_now:
        print(f"[fonts] downloaded from Google Fonts: {installed_now}",
              file=sys.stderr)
    if still_missing:
        print(f"[fonts] still missing (not on Google Fonts / "
              f"OS-shipped): {still_missing}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
