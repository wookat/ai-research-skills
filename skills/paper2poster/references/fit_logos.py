#!/usr/bin/env python3
"""fit_logos.py — pack the header's institution logos (+ optional QR tiles) so they
FILL their zone as much as the shapes allow, then BAKE the arrangement into poster.html.

The logo zone is a SHAPE-PACKING problem (mixed-AR marks in a fixed box), distinct from
a content section: mixed rectangles leave gaps, so ~100% is unreachable. We GREEDILY
search row arrangements and keep the one with the highest *real-pixel* fill (opaque,
non-transparent coverage — a sparse wordmark counts less, so the packer grows it more).

Two halves:
  - pure geometry (Mark, measure_mark, best_arrangement) — unit-testable, no browser.
  - bake(poster_path): open the rendered poster headless, measure each logo zone at the
    TRUE canvas scale (viewport = 5760x3456 so the #poster-stage transform is identity),
    pack, and rewrite the zone's markup into rows (+ a distinct QR row). Disk-to-disk:
    the self-contained poster.html never passes through a tool-call's output.

Run after content substitution / the fill loop and BEFORE render_poster.py:
    python references/fit_logos.py --poster <outdir>/poster.html

Design (per user): real opaque-pixel fill; logos reorderable; QR a distinct row; no
upper size cap (grow until the pseudo-section, inset by `pad`, would overflow).
"""
from __future__ import annotations
import argparse, json, sys, urllib.parse
from dataclasses import dataclass
from itertools import product
from pathlib import Path


@dataclass(frozen=True)
class Mark:
    kind: str        # "logo" | "qr"
    ar: float        # bbox aspect ratio w/h (post-autotrim)
    opaque: float    # real opaque-pixel fraction of the bbox (0..1); qr ~ solid → ~1.0
    label: str = ""  # qr caption ("Paper"/"Code"); blank for logos


def measure_mark(path, kind="logo", label=""):
    """Read a PNG → Mark(ar, opaque). ar = trimmed-bbox w/h; opaque = non-transparent
    pixel fraction of that bbox. RGB (no alpha) → opaque=1.0. Best-effort; never raises."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGBA")
        bb = im.getbbox()
        if bb:
            im = im.crop(bb)
        w, h = im.size
        if w == 0 or h == 0:
            return Mark(kind, 1.0, 1.0, label)
        opaque_px = sum(im.getchannel("A").histogram()[16:])     # alpha > ~6%
        return Mark(kind, w / float(h), max(0.02, min(1.0, opaque_px / float(w * h))), label)
    except Exception:
        return Mark(kind, 1.0, 1.0, label)


# ----- row (shelf) packing ------------------------------------------------------
def _row_height(row, W):
    s = sum(m.ar for m in row)
    return (W / s) if s > 0 else 0.0


def _eval(rows, W, H):
    hs = [_row_height(r, W) for r in rows]
    total = sum(hs)
    if total <= 0:
        return 0.0, hs, 1.0
    scale = min(1.0, H / total)
    hs = [h * scale for h in hs]
    opaque_area = sum(m.opaque * (h * m.ar) * h for r, h in zip(rows, hs) for m in r)
    return opaque_area / float(W * H), hs, scale


def _logo_partitions(logos, max_rows):
    n = len(logos)
    seen = set()
    for r in range(1, min(max_rows, n) + 1):
        for assign in product(range(r), repeat=n):
            if len(set(assign)) != r:
                continue
            rows = tuple(tuple(sorted(i for i in range(n) if assign[i] == j)) for j in range(r))
            key = frozenset(rows)
            if key in seen:
                continue
            seen.add(key)
            yield [[logos[i] for i in row] for row in rows]


def best_arrangement(logos, qrs, zone_w, zone_h, pad=0.0, max_rows=3, gap_frac=0.14, hgap=27.0):
    """Pick the row partition that MAXIMISES the UNIFORM logo height — every institution
    logo ends up the SAME height (they enlarge *together*, never some big / some small).

    For a partition into r rows, one uniform height h makes each row span width
    h*sum(ar_in_row) PLUS the inter-logo gaps the renderer inserts; the WIDEST row caps h at
    (W - gaps)/row_sum_ar, and the r-tall stack caps it at H/(r*(1+gap)). We maximise h —
    balanced rows fall out, since they minimise the widest-row cap — tie-breaking on real
    opaque-pixel fill. `hgap` is the horizontal gap (px, true-canvas scale) between marks in
    a row, mirrored from _APPLY_JS so a wide wordmark + gap never overflows the zone. QR
    tiles are a DISTINCT trailing row (square, their own height). Returns dict(rows,
    row_heights, fill, h); every logo row carries the SAME height.
    """
    W = max(1.0, zone_w - 2 * pad)
    H = max(1.0, zone_h - 2 * pad)
    qr_h = min(H * 0.45, W / (len(qrs) * 1.2)) if qrs else 0.0     # square QR tiles, one row
    H_logo = max(1.0, H - (qr_h * 1.25 if qrs else 0.0))
    best = None
    for rows in list(_logo_partitions(logos, max_rows)):
        r = len(rows)
        sumars = [sum(m.ar for m in row) for row in rows]
        if max(sumars) <= 0:
            continue
        # height capped by the row needing the most width — its logos AT this height PLUS the
        # (n-1) inter-logo gaps the renderer inserts (else a wide SVG wordmark + gap overflows).
        h_width = min(max(1.0, W - (len(row) - 1) * hgap) / sa
                      for row, sa in zip(rows, sumars) if sa > 0)
        h = min(h_width, H_logo / (r * (1 + gap_frac)))           # the ONE uniform logo height
        fill = sum(m.opaque * (h * m.ar) * h for row in rows for m in row) / float(W * H)
        if best is None or (h, fill) > (best["h"], best["fill"]):
            best = {"rows": rows, "h": h, "fill": fill}
    if best is None:
        best = {"rows": [], "h": 0.0, "fill": 0.0}
    best["row_heights"] = [best["h"]] * len(best["rows"])         # SAME height for every logo row
    if qrs:
        best["rows"] = best["rows"] + [list(qrs)]
        best["row_heights"] = best["row_heights"] + [qr_h]
    return best


# ----- bake into poster.html ----------------------------------------------------
# The header logo container across all landscape headers: v1/v2/v4 use `.logo-grid`,
# v5 uses `.logo-block`, and v3 uses `.strip[data-section="logos"]` (its "equal-height
# strip"). ALL must be listed here or that header's logos never get packed / auto-completed.
_LOGO_SELS = [".titlebar .logo-grid", ".titlebar .logo-block", '.titlebar .strip[data-section="logos"]']

# Read each candidate zone: its box + the institution logo srcs + any QR marks (split
# out). A QR is anything in a .qr-* wrapper OR whose src points at assets/qr/* — the
# latter also catches QR <figure>s a PRIOR bake emitted, so re-baking stays idempotent
# (a baked QR is never mis-counted as an institution logo).
_ZONES_JS = r"""(sels)=>{const out=[];
  sels.forEach(sel=>{document.querySelectorAll(sel).forEach((z,zi)=>{
    const r=z.getBoundingClientRect(); if(r.width<8||r.height<8) return;
    // IDEMPOTENCY: a prior bake collapses the zone to its packed-content height, so a
    // re-bake would then only ever fit ONE row. Remember the ORIGINAL available height on
    // the first bake and reuse it, so re-running fit_logos re-packs against the real header
    // space (e.g. 8 logos -> 2 rows) instead of the shrunken strip.
    // The zone's TRUE available height = the largest we've ever seen. On a re-bake
    // the zone collapses to packed-content height (so trust the cached pre-bake
    // height); when the TEMPLATE grew the zone (e.g. v4 stacked layout), the fresh
    // box is taller than a stale cache -> trust the fresh box. max() is correct both
    // ways and self-heals a stale data-lf-h0 from an older layout.
    const h0=z.getAttribute('data-lf-h0');
    let H = h0 ? Math.max(r.height, +h0) : r.height;
    z.setAttribute('data-lf-h0', String(H));
    const isQR=(im)=>!!im.closest('.qr-tile, .qr-block, .qr') || /assets\/qr\//.test(im.getAttribute('src')||'');
    const imgs=[...z.querySelectorAll('img')].filter(im=>im.getAttribute('src')&&!im.src.includes('{{'));
    const logos=imgs.filter(im=>!isQR(im));
    const qrImgs=imgs.filter(isQR);
    if(!logos.length && !qrImgs.length) return;
    out.push({sel, idx:[...document.querySelectorAll(sel)].indexOf(z), W:r.width, H:H,
      logos:logos.map(im=>({src:im.getAttribute('src'), natW:im.naturalWidth, natH:im.naturalHeight})),
      qrs:qrImgs.map(im=>{const fig=im.closest('figure, .qr-tile, .qr');
        const lb=fig?(fig.querySelector('figcaption, .qr-lbl, .qr-label, span')||{}).textContent:'';
        return {src:im.getAttribute('src'), label:(lb||'').trim()};})});
  });}); return out;}"""

# Move relocated header QR marks into the standalone Scan-to-Read section (Paper + Code
# tiles). Used for v1-v4 headers, which carry NO titlebar QR — the QR always lives here.
# If the section is absent (an older poster rendered with the QR in the header dropped the
# then-empty section), re-create it right after Takeaway so the relocated QR has a home.
_SCAN_JS = r"""(qrs)=>{let sec=document.querySelector('.section[data-section="scan-to-read"]');
  if(!sec){
    const tw=document.querySelector('.section[data-section="takeaway"]')
           || document.querySelector('.col:last-of-type .section:last-child')
           || document.querySelector('.section:last-of-type');
    const host=tw?tw.parentElement:null; if(!host) return false;
    sec=document.createElement('div'); sec.className='section'; sec.setAttribute('data-section','scan-to-read');
    sec.innerHTML='<h2>Scan to Read</h2><div class="scan-qr">'
      +'<div class="tq" data-qr=""><div class="qr-img"></div><span>Paper</span></div>'
      +'<div class="tq" data-qr=""><div class="qr-img"></div><span>Code</span></div></div>';
    if(tw && tw.nextSibling) host.insertBefore(sec, tw.nextSibling); else host.appendChild(sec);
  }
  const tqs=[...sec.querySelectorAll('.tq')];
  const paper=qrs.find(q=>/paper/i.test(q.label)) || qrs[0] || null;
  const code =qrs.find(q=>/code/i.test(q.label)) || (qrs.length>1?qrs[1]:null);
  const fill=(tq,f)=>{if(!tq||!f||!f.src)return; tq.setAttribute('data-qr',f.src);
    const im=tq.querySelector('.qr-img'); if(im) im.style.backgroundImage="url('"+f.src+"')";};
  fill(tqs[0],paper); fill(tqs[1],code); return true;}"""

# After re-homing the QR, verify the Scan-to-Read column still fits. If ANY section in it
# now overflows its box (the section landed in an already-full column and flex-shrank its
# siblings below their content), remove the Scan-to-Read section so the column reflows back
# to its converged height. Returns 'kept' | 'reverted' | 'none' | 'nocol'.
_SCAN_REVERT_IF_OVERFLOW = r"""()=>{const sec=document.querySelector('.section[data-section="scan-to-read"]');
  if(!sec) return 'none';
  const col=sec.closest('.col'); if(!col) return 'nocol';
  const over=[...col.querySelectorAll('.section')].some(s=>s.scrollHeight - s.clientHeight > 8);
  if(over){ sec.remove(); return 'reverted'; }
  return 'kept';}"""

# Rebuild ONE zone's children into packer rows. spec = {rows:[{kind,h,items:[{src,label}]}], fill}.
_APPLY_JS = r"""({sel, idx, spec})=>{const z=document.querySelectorAll(sel)[idx]; if(!z) return;
  z.innerHTML=''; z.style.display='flex'; z.style.flexDirection='column'; z.style.flexWrap='nowrap';
  z.style.justifyContent='center'; z.style.alignItems='center'; z.style.gap='14pt';
  spec.rows.forEach(row=>{const d=document.createElement('div');
    d.style.display='flex'; d.style.flexDirection='row'; d.style.alignItems='center';
    d.style.justifyContent='center'; d.style.gap=(row.kind==='qr'?'26pt':'20pt'); d.style.flexWrap='nowrap';
    row.items.forEach(it=>{
      if(row.kind==='qr'){const fig=document.createElement('figure');fig.style.margin='0';
        fig.style.display='flex';fig.style.flexDirection='column';fig.style.alignItems='center';fig.style.gap='6pt';
        const im=document.createElement('img');im.src=it.src;im.style.height=row.h+'px';im.style.width=row.h+'px';
        im.style.imageRendering='pixelated';fig.appendChild(im);
        if(it.label){const c=document.createElement('figcaption');c.textContent=it.label;
          c.style.fontSize='24pt';c.style.fontWeight='600';c.style.color='var(--tb-fg,#111)';fig.appendChild(c);}
        d.appendChild(fig);
      } else {const im=document.createElement('img');im.src=it.src;im.style.height=row.h+'px';
        im.style.width='auto';im.style.maxWidth='none';im.style.objectFit='contain';d.appendChild(im);}
    });
    z.appendChild(d);});
  z.setAttribute('data-lf-fill', spec.fill);}"""


def _resolve(src, base):
    if src.startswith("file://"):
        return urllib.parse.unquote(src[7:])
    if src.startswith(("http://", "https://", "data:")):
        return None
    return str((base / src).resolve())


def _load_qr_labels(base: Path) -> dict:
    """Read the make_qr manifest from metadata.json → {qr-filename: caption}.

    e.g. {"paper.png": "Project"}. The caption describes what the QR actually
    points to (Paper / Code / Project), decoupled from the slot filename. Empty
    dict when there's no manifest (older bundles) → captions fall back to the
    template defaults, so nothing regresses.
    """
    fp = base / "assets" / "meta" / "metadata.json"
    if not fp.exists():
        return {}
    try:
        meta = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}
    labels: dict = {}
    for e in (meta.get("qr") or []):
        path, lbl = (e.get("path") or ""), (e.get("label") or "")
        if path and lbl:
            labels[path.rsplit("/", 1)[-1]] = lbl     # "assets/qr/paper.png" -> "paper.png"
    return labels


# Final deterministic pass: caption EVERY QR tile from the make_qr manifest, keyed by the
# QR image's filename — so a tile showing qr/paper.png is captioned "Project" when that's
# what the URL is, not the template's hardcoded "Paper". Covers v5 header <figure>s, packed
# logo-zone QR figures, and v1-v4 Scan-to-Read `.tq` tiles (bg-image or <img>). Runs ONLY
# when a manifest exists, so a QR tile whose file is NOT in the manifest is a STALE slot
# (e.g. a pre-dedup code.png the paper no longer has) and is dropped — no bare duplicate.
_STAMP_QR_LABELS_JS = r"""(labels)=>{const norm=s=>((s||'').split('?')[0].split('#')[0].split('/').pop());
  const isqr=s=>/(^|\/)qr\/[^\/]+\.(png|svg|jpg|jpeg)$/i.test(s||'');
  document.querySelectorAll('img').forEach(im=>{
    const src=im.getAttribute('src')||''; if(!isqr(src)) return;
    const fig=im.closest('figure, .qr, .qr-tile, .tq'); if(!fig) return;
    const lb=labels[norm(src)];
    if(lb){const cap=fig.querySelector('figcaption, .qr-label, .qr-lbl, span'); if(cap) cap.textContent=lb;}
    else{ fig.remove(); }                                   // stale slot not in manifest -> drop
  });
  document.querySelectorAll('.tq').forEach(tq=>{
    if(tq.querySelector('img')) return;                     // <img> tiles handled above
    let src=tq.getAttribute('data-qr')||'';
    if(!src){const bg=tq.querySelector('.qr-img');
      const s=(bg&&bg.style)?bg.style.backgroundImage:''; const m=(s||'').match(/url\(['"]?([^'")]+)/); src=m?m[1]:'';}
    const lb=labels[norm(src)];
    if(lb){const sp=tq.querySelector('.qr-lbl, .qr-label, figcaption, span'); if(sp) sp.textContent=lb;}
    else{ tq.remove(); }                                    // empty or stale tile -> drop
  });
  return true;}"""


def bake(poster_path, max_rows=3, pad_frac=0.06):
    """Measure each logo zone at true canvas scale, pack, and rewrite poster.html."""
    from playwright.sync_api import sync_playwright
    poster = Path(poster_path).resolve()
    base = poster.parent
    qr_labels = _load_qr_labels(base)
    # Every institution logo fetched to disk (excluding the venue mark + QR). The model
    # fills only a handful of {{LOGO_N}} slots and drops institutes when there are more
    # than the header's slots — so we AUTO-COMPLETE the header with any of these that the
    # model didn't place, deterministically. Sorted for stable ordering across renders.
    _logo_dir = base / "assets" / "logos"
    disk_logos = sorted(
        (p for p in _logo_dir.glob("*")
         if p.suffix.lower() in (".png", ".svg", ".jpg", ".jpeg") and p.name != "_venue.png"),
        key=lambda p: p.name,
    ) if _logo_dir.is_dir() else []
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=p.chromium.executable_path, args=["--no-sandbox"])
        pg = br.new_page(viewport={"width": 5760, "height": 3456}, device_scale_factor=1)
        pg.emulate_media(media="print")   # match render_poster.py's layout: the header/logo
                                          # zone sizes differently under screen vs print media,
                                          # so measure the SAME layout the final PDF/PNG uses.
        pg.goto(poster.as_uri()); pg.wait_for_timeout(600)
        # Venue inject: if the venue logo file exists on disk but the header isn't showing
        # it (the <img> was left empty, or its onerror="this.remove()" already fired on the
        # empty src), (re)create the venue <img> in the conference chip and point it at the
        # file. Only acts when the chip has no real logo yet — never overrides a good one.
        if (base / "assets" / "logos" / "_venue.png").exists():
            # Insert the venue <img> INTO the conference chip (.chip.conf), never its
            # .venue-mark parent. The vtext-hide CSS keys off `.chip.conf:has(img[src])`,
            # so an <img> placed in the parent leaves the chip "logo-less" and the year
            # text ("NeurIPS 2022") stays visible ALONGSIDE the logo — the duplication the
            # user flagged. Targeting .chip.conf makes the CSS fire and hides the vtext.
            # v5 uses a text-only venue badge (no .chip.conf) — skip it entirely.
            pg.evaluate("""()=>{const chip=document.querySelector('.titlebar .chip.conf');
              if(!chip) return;                                  // v5 text badge has no .chip.conf
              const vm=document.querySelector('.titlebar .venue-mark');
              if(vm){[...vm.children].forEach(c=>{if(c.tagName==='IMG') c.remove();});}  // drop stale parent-level venue img
              let im=chip.querySelector('img');
              if(im){const s=im.getAttribute('src')||''; if(s && !s.includes('{{')) return;}  // logo already shown
              if(!im){im=document.createElement('img'); im.alt=''; chip.insertBefore(im, chip.firstChild);}
              im.removeAttribute('onerror'); im.setAttribute('src','assets/logos/_venue.png');}""")
            pg.wait_for_timeout(150)
        zones = pg.evaluate(_ZONES_JS, _LOGO_SELS)
        is_v5 = pg.evaluate("""()=>!!document.querySelector('.titlebar[data-header="v5"]')""")
        relocate_qrs = []          # header QR pulled out of v1-v4 titlebars -> Scan-to-Read
        baked = []
        logos_completed = False    # inject missing disk logos into the first logo zone only
        for z in zones:
            logos, srcs = [], []
            for lg in z["logos"]:
                s = lg["src"]
                fp = _resolve(s, base)
                # AR from the BROWSER's natural size — correct for SVG wordmarks too, which
                # PIL cannot read: measure_mark would default them to AR 1.0, so the packer
                # would render a wide wordmark at FULL height and it overflows the zone
                # (the #10/#21 "logo stretched big and long" bug). PIL is used only for the
                # opaque-pixel fill weight (best-effort; SVG / unreadable -> 1.0).
                nw, nh = lg.get("natW") or 0, lg.get("natH") or 0
                ar = (nw / nh) if (nw and nh) else 1.0
                opaque = measure_mark(fp).opaque if fp else 1.0
                logos.append(Mark("logo", ar, opaque))
                srcs.append(s)
            # AUTO-COMPLETE: every fetched institute logo on disk MUST appear — the model
            # under-fills the header's slots and silently drops institutes when there are
            # more than it placed (the "8 fetched, only 6 shown" bug). Inject any disk logo
            # not already placed into this (first, header) logo zone, then pack them all.
            if disk_logos and not logos_completed and logos:
                placed = {s.rsplit("/", 1)[-1] for s in srcs}
                for lf in disk_logos:
                    if lf.name in placed:
                        continue
                    m = measure_mark(str(lf))
                    logos.append(Mark("logo", m.ar, m.opaque))
                    srcs.append(f"assets/logos/{lf.name}")
                logos_completed = True
            qr_src = [(q["src"], q["label"]) for q in z["qrs"] if q["src"] and "{{" not in q["src"]]
            if qr_src and not is_v5:
                # v1-v4 carry NO titlebar QR: pull any QR out of the header and re-home it
                # in the standalone Scan-to-Read section; the header then packs logos only.
                relocate_qrs.extend({"src": s, "label": lb} for s, lb in qr_src)
                qr_src = []
            qrs = [Mark("qr", 1.0, 1.0, lb) for _, lb in qr_src]
            pad = min(z["W"], z["H"]) * pad_frac
            b = best_arrangement(logos, qrs, z["W"], z["H"], pad=pad, max_rows=max_rows)
            id2i = {id(m): i for i, m in enumerate(logos)}
            spec_rows = []
            for r, h in zip(b["rows"], b["row_heights"]):
                if r and r[0].kind == "qr":
                    spec_rows.append({"kind": "qr", "h": round(h),
                                      "items": [{"src": qr_src[k][0], "label": qr_src[k][1]} for k in range(len(r))]})
                else:
                    spec_rows.append({"kind": "logo", "h": round(h),
                                      "items": [{"src": srcs[id2i[id(m)]], "label": ""} for m in r]})
            pg.evaluate(_APPLY_JS, {"sel": z["sel"], "idx": z["idx"],
                                    "spec": {"rows": spec_rows, "fill": round(b["fill"] * 100)}})
            baked.append((z["sel"], len(logos), round(b["fill"] * 100)))
        if relocate_qrs:
            pg.evaluate(_SCAN_JS, relocate_qrs)   # re-home v1-v4 header QR into Scan-to-Read
            pg.wait_for_timeout(150)
            # The Scan-to-Read section only belongs here if its column has the room. An
            # ALREADY-CONVERGED poster (the QR used to live in the header, so the fill loop
            # never budgeted a QR section) has none — the new section flex-shrinks its
            # siblings until their content overflows. If that happens, drop the section back
            # out so the column reflows to its converged height; this poster then shows no QR
            # (a future fresh render balances Scan-to-Read in via the fill loop instead).
            verdict = pg.evaluate(_SCAN_REVERT_IF_OVERFLOW)
            baked.append(("scan-to-read", 0, verdict))
        # Final deterministic caption pass: label every QR from the make_qr manifest by the
        # QR file it shows (v5 header figures, packed logo-zone QRs, and Scan-to-Read tiles),
        # so a project-only paper reads "Project" not "Paper", and drop any empty tile.
        if qr_labels:
            pg.evaluate(_STAMP_QR_LABELS_JS, qr_labels)
        html = pg.content()
        poster.write_text(html, encoding="utf-8")
        br.close()
    return baked


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fit_logos")
    ap.add_argument("--poster", help="bake the logo packing into this poster.html (in place)")
    ap.add_argument("--selftest", action="store_true", help="run the pure-geometry self-test")
    a = ap.parse_args(argv)
    if a.poster:
        for sel, n, fill in bake(a.poster):
            print(f"  baked {sel}: {n} logo(s), fill={fill}%")
        print(f"fit_logos: done -> {a.poster}")
        return 0
    ZW, ZH = 1322, 251
    sample = [Mark("logo", 1.0, 0.85), Mark("logo", 2.6, 0.55), Mark("logo", 0.9, 0.9),
              Mark("logo", 3.1, 0.40), Mark("logo", 1.2, 0.80), Mark("logo", 2.0, 0.70)]
    for n in (1, 2, 3, 4, 6):
        b = best_arrangement(sample[:n], [], ZW, ZH, pad=14)
        print(f"  {n} logos: fill={b['fill']*100:5.1f}%  {len(b['rows'])} row(s)  "
              f"h={[round(h) for h in b['row_heights']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
