# html2pptx-skill

Convert a rendered HTML page (especially A0 conference posters) into a native PowerPoint .pptx with **editable text + native shapes** — NOT a PNG-in-slide.

Designed as a [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills) but the scripts work standalone.

In this repo it ships as a **bundled sub-skill of [`paper2poster`](../)**, which runs it automatically as the final step of its pipeline (`poster.html` → editable `poster.pptx`) — so most users never invoke it directly. It is still fully usable on its own for any HTML page.

## What it does

Walks the live DOM via headless Chromium, extracts BLOCK-level text containers as TextBoxes with inline `<strong>`/`<em>` as mixed-style Runs, `<img>` as Picture with `object-fit:contain` respected, decorative `<div>`/`<section>` with bg/border/gradient/box-shadow as Rectangle/RoundedRect with matching fill.

- All CSS colors (including `color-mix`/`oklab`/`color()`) normalized via canvas
- CSS `hyphens: auto` → OOXML soft hyphens via pyphen
- CSS `line-height` absolute Pt for paragraph spacing
- Native OOXML bullets with hanging indent
- Closed-loop PIL-based font shrinking auto-fits overflowing blocks

Targets ~95% visual fidelity when the web fonts are installed on both render and viewer machines.

## Quick start

```bash
pip install -r requirements.txt
playwright install chromium

# Linux (Ubuntu/Debian)
sudo apt install libreoffice-impress

# Install web fonts (Inter, Source Serif 4, JetBrains Mono) — see SKILL.md §3 for full commands
```

One command builds + auto-corrects:

```bash
python -m scripts.auto_correct_loop \
    --html /path/to/poster.html \
    --outdir /path/to/output/ \
    --rounds 3
```

Output: `<name>_round_N.{pptx,pdf,png}` for each of N rounds. Final pptx is typically `round_3.pptx`.

## Files

- **[SKILL.md](SKILL.md)** — canonical skill spec (setup, architecture, quick start, capability table)
- **[GOTCHAS.md](GOTCHAS.md)** — 14 production-tested failure modes with root cause + fix + why
- `scripts/html_to_pptx.py` — DOM extract + PPTX build (accepts `--corrections` for per-block font scale)
- `scripts/auto_correct_loop.py` — canonical entry point: N-round closed loop with PIL-based overflow detection

## Use as Claude Code skill

In this repo it's vendored under `skills/paper2poster/html2pptx/` as a bundled sub-skill of paper2poster (not a git submodule). To use it standalone elsewhere, place it under `.claude/skills/html2pptx` in your project (or symlink to it). Claude Code reads SKILL.md's frontmatter and exposes it as `html2pptx`.

## Use standalone

The scripts work without Claude Code. Just clone, install deps, run the one-liner above.

## Status

Production-tested on A0 (47×33.1") conference posters for ML papers (LPQLD, Attention Is All You Need pipeline figure). Untested on 16:9 deck-style HTML.

See [SKILL.md](SKILL.md) for full capability matrix.

## License

MIT
