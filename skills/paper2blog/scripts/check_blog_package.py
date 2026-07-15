#!/usr/bin/env python3
"""Quality gate for bilingual paper2blog DOCX deliverables.

The gate reads the DOCX package directly. It checks cross-language consistency,
embedded media, font declarations, TODO markers, and approximate pagination
risks such as large blank areas before images and one-word final lines.

Word pagination is renderer-dependent, so layout findings are reported as
actionable risks, not as a pixel-perfect substitute for opening the document.
They still point at the exact paragraph/image that needs review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    fitz = None

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
EMU_PER_PT = 12700
TWIPS_PER_PT = 20
SCHEMA_VERSION = "paper2blog_qa.v1"


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    location: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Block:
    kind: str
    text: str = ""
    style: str = ""
    image_width_pt: float | None = None
    image_height_pt: float | None = None
    index: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add(findings: list[Finding], severity: str, code: str, message: str, *, location: str | None = None, **data: Any) -> None:
    findings.append(Finding(severity=severity, code=code, message=message, location=location, data=data))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xml_text(el: ET.Element) -> str:
    parts = []
    for node in el.iter():
        if local_name(node.tag) == "t" and node.text:
            parts.append(node.text)
        elif local_name(node.tag) in {"tab", "br"}:
            parts.append(" ")
    return "".join(parts).strip()


def attr(el: ET.Element | None, name: str) -> str | None:
    if el is None:
        return None
    return el.attrib.get(f"{{{NS['w']}}}{name}")


def read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None


def drawing_extents_pt(paragraph: ET.Element) -> list[tuple[float, float]]:
    out = []
    for extent in paragraph.findall(".//wp:extent", NS):
        try:
            cx = float(extent.attrib.get("cx", "0")) / EMU_PER_PT
            cy = float(extent.attrib.get("cy", "0")) / EMU_PER_PT
        except ValueError:
            continue
        if cx > 0 and cy > 0:
            out.append((cx, cy))
    return out


def paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("w:pPr/w:pStyle", NS)
    return attr(style, "val") if style is not None else ""


def section_content_box_pt(document_root: ET.Element) -> tuple[float, float]:
    sect = document_root.find(".//w:sectPr", NS)
    if sect is None:
        return 468.0, 648.0
    pg_sz = sect.find("w:pgSz", NS)
    pg_mar = sect.find("w:pgMar", NS)
    try:
        width = float(attr(pg_sz, "w") or 12240) / TWIPS_PER_PT
        height = float(attr(pg_sz, "h") or 15840) / TWIPS_PER_PT
        left = float(attr(pg_mar, "left") or 1440) / TWIPS_PER_PT
        right = float(attr(pg_mar, "right") or 1440) / TWIPS_PER_PT
        top = float(attr(pg_mar, "top") or 1440) / TWIPS_PER_PT
        bottom = float(attr(pg_mar, "bottom") or 1440) / TWIPS_PER_PT
    except (TypeError, ValueError):
        return 468.0, 648.0
    return max(72.0, width - left - right), max(72.0, height - top - bottom)


def collect_blocks(document_root: ET.Element) -> list[Block]:
    body = document_root.find("w:body", NS)
    if body is None:
        return []
    blocks: list[Block] = []
    index = 0
    for child in body:
        lname = local_name(child.tag)
        if lname == "p":
            text = xml_text(child)
            style = paragraph_style(child)
            extents = drawing_extents_pt(child)
            if extents:
                for width, height in extents:
                    index += 1
                    blocks.append(Block(kind="image", text=text, style=style, image_width_pt=width, image_height_pt=height, index=index))
            elif text:
                index += 1
                blocks.append(Block(kind="paragraph", text=text, style=style, index=index))
        elif lname == "tbl":
            index += 1
            blocks.append(Block(kind="table", text=xml_text(child), index=index))
    return blocks


def list_media(zf: zipfile.ZipFile) -> list[str]:
    return sorted(n for n in zf.namelist() if n.startswith("word/media/") and not n.endswith("/"))


def media_hashes(zf: zipfile.ZipFile, media: list[str]) -> list[str]:
    hashes = []
    for name in media:
        try:
            hashes.append(hashlib.sha256(zf.read(name)).hexdigest())
        except KeyError:
            continue
    return hashes


def style_fonts(zf: zipfile.ZipFile) -> dict[str, set[str]]:
    root = read_xml(zf, "word/styles.xml")
    found = {"ascii": set(), "eastAsia": set(), "hAnsi": set()}
    if root is None:
        return found
    for rfonts in root.findall(".//w:rFonts", NS):
        for key in found:
            value = attr(rfonts, key)
            if value:
                found[key].add(value)
    return found


def char_units(ch: str) -> float:
    if ch.isspace():
        return 0.34
    code = ord(ch)
    if 0x4E00 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF or 0xAC00 <= code <= 0xD7AF:
        return 1.0
    if ch in "il.,:;|'!":
        return 0.28
    if ch in "MW@#%&":
        return 0.85
    return 0.55


def wrap_lines(text: str, content_width_pt: float, font_pt: float) -> list[str]:
    max_units = max(content_width_pt / max(font_pt, 1.0), 1.0)
    lines: list[str] = []
    for para in re.split(r"\n+", text):
        current = ""
        units = 0.0
        for token in re.findall(r"\S+\s*|\s+", para):
            token_units = sum(char_units(ch) for ch in token)
            if current and units + token_units > max_units:
                lines.append(current.rstrip())
                current = token
                units = token_units
            else:
                current += token
                units += token_units
        if current.strip():
            lines.append(current.rstrip())
    return lines or [text]


def estimate_block_height(block: Block, content_width_pt: float) -> float:
    if block.kind == "image":
        return float(block.image_height_pt or 0) + 10.0
    if block.kind == "table":
        rows = max(1, len(re.findall(r"\n", block.text)) + 2)
        return min(260.0, rows * 20.0 + 18.0)
    style = block.style.lower()
    if "title" in style:
        font_pt = 22.0
        line_height = 28.0
    elif "heading1" in style or "heading 1" in style:
        font_pt = 16.0
        line_height = 22.0
    elif "heading" in style:
        font_pt = 13.0
        line_height = 18.0
    elif "caption" in style:
        font_pt = 9.5
        line_height = 12.0
    else:
        font_pt = 11.0
        line_height = 14.0
    lines = wrap_lines(block.text, content_width_pt, font_pt)
    return max(line_height, len(lines) * line_height) + 6.0


def orphan_tail(text: str, content_width_pt: float, lang: str) -> tuple[str, int] | None:
    if len(text.strip()) < 70:
        return None
    lines = wrap_lines(text, content_width_pt, 11.0)
    if len(lines) < 2:
        return None
    tail = lines[-1].strip()
    if not tail:
        return None
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9._%+-]*", tail)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", tail)
    if lang == "en" and len(words) == 1 and len(tail) <= 18:
        return tail, len(lines)
    if lang == "zh" and len(cjk_chars) <= 4 and len(tail) <= 12:
        return tail, len(lines)
    if len(words) == 1 and len(cjk_chars) <= 2 and len(tail) <= 14:
        return tail, len(lines)
    return None


def extract_numbers(text: str) -> list[str]:
    pattern = re.compile(r"(?<![A-Za-z0-9_.])[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|×|x|X|B|M|K|k|million|billion)?")
    out = []
    for m in pattern.finditer(text):
        value = re.sub(r"\s+", "", m.group(0)).replace(",", "")
        if len(value) == 4 and value.isdigit() and 1900 <= int(value) <= 2100:
            continue
        out.append(value)
    return out


def normalize_number(value: str) -> str:
    return value.strip().replace("×", "x").replace("X", "x").replace("million", "M").replace("billion", "B")


def common_terms(text: str) -> set[str]:
    terms = set(re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}(?:-[A-Za-z0-9]+)?\b", text))
    stop = {"The", "This", "That", "Figure", "Table", "Section", "We", "Our", "Code", "Paper"}
    return {t for t in terms if t not in stop}


def load_outline(path: Path | None, findings: list[Finding] | None = None, label: str = "outline") -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if findings is not None:
            add(findings, "warning", "outline_missing", "Outline JSON was requested but not found.", location=str(path), outline=label)
    except json.JSONDecodeError as exc:
        if findings is not None:
            add(findings, "warning", "outline_invalid_json", f"Outline JSON could not be parsed: {exc}", location=str(path), outline=label)
    except Exception as exc:
        if findings is not None:
            add(findings, "warning", "outline_read_failed", f"Outline JSON could not be read: {exc}", location=str(path), outline=label)
    return None


def outline_figures(outline: dict[str, Any] | None) -> list[str]:
    if not isinstance(outline, dict):
        return []
    figs = []
    for block in outline.get("blocks", []):
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("path"):
            figs.append(str(block["path"]))
    return figs


def which(name: str) -> str | None:
    return shutil.which(name)


def find_libreoffice() -> str | None:
    return which("libreoffice") or which("soffice")


def natural_key(path: Path) -> list[Any]:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", path.stem)]


def load_rendered_pages_dir(pages_dir: Path, lang: str, findings: list[Finding], *, required: bool) -> dict[str, Any]:
    if not pages_dir.is_dir():
        severity = "error" if required else "warning"
        add(findings, severity, "docx_preview_pages_dir_missing", "Rendered DOCX page directory is missing.", location=str(pages_dir), lang=lang)
        return {"checked": False, "pages": []}
    pages = sorted([p for p in pages_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}], key=natural_key)
    if not pages:
        severity = "error" if required else "warning"
        add(findings, severity, "docx_preview_pages_empty", "Rendered DOCX page directory contains no page images.", location=str(pages_dir), lang=lang)
        return {"checked": False, "pages": []}
    page_items = []
    for index, path in enumerate(pages, start=1):
        item: dict[str, Any] = {"index": index, "path": str(path)}
        if Image is not None:
            try:
                with Image.open(path) as im:
                    item["width"], item["height"] = im.size
            except Exception:
                pass
        page_items.append(item)
    return {"checked": True, "pages_dir": str(pages_dir), "pages": page_items}


def render_docx_preview(docx_path: Path, preview_root: Path, lang: str, findings: list[Finding], *, required: bool) -> dict[str, Any]:
    """Render DOCX to page PNGs so layout gates inspect the actual artifact."""
    if not docx_path.is_file():
        if required:
            add(findings, "error", "docx_preview_source_missing", "Cannot render DOCX preview because the DOCX is missing.", location=str(docx_path), lang=lang)
        return {"checked": False, "pages": []}
    libreoffice = find_libreoffice()
    if not libreoffice:
        severity = "error" if required else "warning"
        add(findings, severity, "libreoffice_missing", "LibreOffice/soffice is required for DOCX layout preview rendering.", lang=lang)
        return {"checked": False, "pages": []}
    if fitz is None:
        severity = "error" if required else "warning"
        add(findings, severity, "pymupdf_missing", "PyMuPDF is required to rasterize DOCX preview PDFs.", lang=lang)
        return {"checked": False, "pages": []}

    pdf_dir = preview_root / "pdf"
    pages_dir = preview_root / f"{lang}_pages"
    expected_pdf_path = pdf_dir / f"{docx_path.stem}.pdf"
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf_path.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile_dir:
        cmd = [
            libreoffice,
            f"-env:UserInstallation=file://{profile_dir}",
            "--headless", "--norestore", "--nolockcheck", "--nodefault", "--nofirststartwizard", "--nologo",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", str(pdf_dir),
            str(docx_path),
        ]
        started_at = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            severity = "error" if required else "warning"
            add(findings, severity, "docx_preview_render_timeout", "LibreOffice timed out while exporting DOCX preview PDF.", location=str(docx_path), lang=lang)
            return {"checked": False, "pages": []}
    if proc.returncode != 0:
        severity = "error" if required else "warning"
        add(
            findings,
            severity,
            "docx_preview_render_failed",
            "LibreOffice failed while exporting DOCX preview PDF.",
            location=str(docx_path),
            lang=lang,
            stdout=proc.stdout[-1000:],
            stderr=proc.stderr[-1000:],
        )
        return {"checked": False, "pages": []}

    pdf_path = expected_pdf_path
    if not pdf_path.exists():
        candidates = sorted(
            [p for p in pdf_dir.glob("*.pdf") if p.stat().st_mtime >= started_at - 1],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        pdf_path = candidates[0] if candidates else pdf_path
    if not pdf_path.exists():
        severity = "error" if required else "warning"
        add(
            findings,
            severity,
            "docx_preview_pdf_missing",
            "LibreOffice did not produce a DOCX preview PDF.",
            location=str(docx_path),
            lang=lang,
            stdout=proc.stdout[-1000:],
            stderr=proc.stderr[-1000:],
        )
        return {"checked": False, "pages": []}

    pages: list[dict[str, Any]] = []
    try:
        doc = fitz.open(str(pdf_path))
        matrix = fitz.Matrix(1.6, 1.6)
        for page_index, page in enumerate(doc, start=1):
            out_path = pages_dir / f"page_{page_index:03d}.png"
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(out_path))
            pages.append({"index": page_index, "path": str(out_path), "width": pix.width, "height": pix.height})
        doc.close()
    except Exception as exc:
        severity = "error" if required else "warning"
        add(findings, severity, "docx_preview_raster_failed", f"Could not rasterize DOCX preview PDF: {exc}", location=str(pdf_path), lang=lang)
        return {"checked": False, "pdf": str(pdf_path), "pages": []}

    if not pages:
        severity = "error" if required else "warning"
        add(findings, severity, "docx_preview_no_pages", "DOCX preview produced no pages.", location=str(pdf_path), lang=lang)
    return {"checked": bool(pages), "pdf": str(pdf_path), "pages": pages}


def page_foreground_metrics(image_path: Path) -> dict[str, Any] | None:
    if Image is None or np is None:
        return None
    with Image.open(image_path) as im:
        arr = np.asarray(im.convert("RGB")).astype(np.int16)
    height, width = arr.shape[:2]
    border = max(4, min(width, height) // 35)
    samples = np.concatenate(
        [
            arr[:border, :, :].reshape(-1, 3),
            arr[-border:, :, :].reshape(-1, 3),
            arr[:, :border, :].reshape(-1, 3),
            arr[:, -border:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    bg = np.median(samples, axis=0)
    diff = np.max(np.abs(arr - bg), axis=2)
    dark_ink = np.max(arr, axis=2) < 242
    mask = (diff > 16) | dark_ink
    rim = max(2, min(width, height) // 180)
    mask[:rim, :] = False
    mask[-rim:, :] = False
    mask[:, :rim] = False
    mask[:, -rim:] = False

    foreground = int(mask.sum())
    total = int(mask.size)
    if foreground == 0:
        return {
            "foreground_ratio": 0.0,
            "content_bbox": None,
            "content_bbox_area_ratio": 0.0,
            "bottom_blank_ratio": 1.0,
            "right_blank_ratio": 1.0,
        }
    ys, xs = np.where(mask)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return {
        "foreground_ratio": round(foreground / max(total, 1), 5),
        "content_bbox": [round(x0 / width, 4), round(y0 / height, 4), round((x1 - x0 + 1) / width, 4), round((y1 - y0 + 1) / height, 4)],
        "content_bbox_area_ratio": round(((x1 - x0 + 1) * (y1 - y0 + 1)) / max(total, 1), 5),
        "bottom_blank_ratio": round(max(0, height - y1 - 1) / height, 5),
        "right_blank_ratio": round(max(0, width - x1 - 1) / width, 5),
    }


def check_docx_preview_layout(preview: dict[str, Any], lang: str, findings: list[Finding], *, required: bool) -> dict[str, Any]:
    pages = preview.get("pages") or []
    if not pages:
        if required:
            add(findings, "error", "docx_preview_required", "DOCX rendered-page preview is required for strict blog QA.", lang=lang)
        return {"checked": False, "pages": []}
    if Image is None or np is None:
        severity = "error" if required else "warning"
        add(findings, severity, "docx_preview_pixel_dependencies_missing", "Pillow and NumPy are required for rendered DOCX page pixel checks.", lang=lang)
        return {"checked": False, "pages": pages}

    details: list[dict[str, Any]] = []
    total_pages = len(pages)
    for item in pages:
        page_index = int(item.get("index") or len(details) + 1)
        path = Path(str(item.get("path")))
        try:
            metrics = page_foreground_metrics(path)
        except Exception as exc:
            add(findings, "error" if required else "warning", "docx_preview_page_read_failed", f"Could not inspect rendered DOCX page: {exc}", location=str(path), lang=lang, page=page_index)
            continue
        if metrics is None:
            continue
        fg = float(metrics["foreground_ratio"])
        bbox_area = float(metrics["content_bbox_area_ratio"])
        bottom_blank = float(metrics["bottom_blank_ratio"])
        if fg < 0.004 or bbox_area < 0.035:
            add(
                findings,
                "error",
                "docx_preview_page_near_blank",
                "Rendered DOCX page is nearly blank.",
                location=str(path),
                lang=lang,
                page=page_index,
                **metrics,
            )
        elif fg < 0.012 or bbox_area < 0.12:
            add(
                findings,
                "warning",
                "docx_preview_page_sparse",
                "Rendered DOCX page content occupies too little area.",
                location=str(path),
                lang=lang,
                page=page_index,
                **metrics,
            )
        if page_index < total_pages and bottom_blank > 0.34 and bbox_area < 0.62:
            add(
                findings,
                "error",
                "docx_preview_large_bottom_blank",
                "A non-final DOCX page leaves a large blank area at the bottom.",
                location=str(path),
                lang=lang,
                page=page_index,
                **metrics,
            )
        elif page_index == total_pages and total_pages > 1 and bottom_blank > 0.72:
            add(
                findings,
                "warning",
                "docx_preview_final_page_sparse",
                "Final DOCX page is very sparse; consider rebalancing images/text if the article looks unfinished.",
                location=str(path),
                lang=lang,
                page=page_index,
                **metrics,
            )
        details.append({**item, "foreground": metrics})
    return {"checked": True, "pages": details}


def analyze_docx(path: Path, lang: str, outline: dict[str, Any] | None, findings: list[Finding]) -> dict[str, Any]:
    if not path.is_file():
        add(findings, "error", "docx_missing", "DOCX file is missing.", location=str(path), lang=lang)
        return {"exists": False}
    try:
        with zipfile.ZipFile(path) as zf:
            root = read_xml(zf, "word/document.xml")
            if root is None:
                add(findings, "error", "docx_document_xml_missing", "DOCX has no word/document.xml.", location=str(path), lang=lang)
                return {"exists": True, "valid": False}
            content_width_pt, content_height_pt = section_content_box_pt(root)
            blocks = collect_blocks(root)
            text = "\n".join(block.text for block in blocks if block.text)
            media = list_media(zf)
            media_sha256 = media_hashes(zf, media)
            fonts = style_fonts(zf)

            if len(text.strip()) < 800:
                add(findings, "warning", "docx_short_text", "Document text is unusually short for a finished blog article.", location=str(path), lang=lang, chars=len(text.strip()))
            if not media:
                add(findings, "warning", "docx_no_embedded_images", "DOCX has no embedded images.", location=str(path), lang=lang)
            if re.search(r"\b(TODO|TBD|XXX|FIXME|to be confirmed)\b|待确认|待补充|占位", text, re.I):
                add(findings, "error", "docx_placeholder_text", "Document contains TODO/placeholder text.", location=str(path), lang=lang)

            expected_latin = "Arial"
            expected_east_asia = "Microsoft YaHei"
            if expected_latin not in fonts["ascii"] and expected_latin not in fonts["hAnsi"]:
                add(findings, "warning", "docx_latin_font_not_declared", "Expected Latin font is not declared in DOCX styles.", location=str(path), lang=lang, expected=expected_latin, found=sorted(fonts["ascii"] | fonts["hAnsi"]))
            if expected_east_asia not in fonts["eastAsia"]:
                add(findings, "warning", "docx_cjk_font_not_declared", "Expected CJK fallback font is not declared in DOCX styles.", location=str(path), lang=lang, expected=expected_east_asia, found=sorted(fonts["eastAsia"]))

            page_used = 0.0
            page_no = 1
            layout_risks = []
            for block in blocks:
                height = estimate_block_height(block, content_width_pt)
                remaining = content_height_pt - page_used
                if block.kind == "image":
                    image_width_ratio = float(block.image_width_pt or 0) / max(content_width_pt, 1.0)
                    image_height_ratio = float(block.image_height_pt or 0) / max(content_height_pt, 1.0)
                    image_area_ratio = image_width_ratio * image_height_ratio
                    if image_width_ratio < 0.66 and image_height_ratio < 0.30 and image_area_ratio < 0.13:
                        add(
                            findings,
                            "warning",
                            "docx_image_underfilled",
                            "Embedded image is small relative to the content area; consider enlarging it if readability and page balance allow.",
                            location=f"{path.name}: image block {block.index}",
                            lang=lang,
                            image_width_ratio=round(image_width_ratio, 3),
                            image_height_ratio=round(image_height_ratio, 3),
                            image_area_ratio=round(image_area_ratio, 3),
                        )
                if block.kind == "image" and height > remaining and remaining / content_height_pt > 0.22:
                    shrink_to_fit = remaining / max(height, 1.0)
                    if shrink_to_fit >= 0.78:
                        severity = "error" if remaining / content_height_pt > 0.32 and shrink_to_fit >= 0.84 else "warning"
                        risk = {
                            "type": "large_blank_before_image",
                            "page": page_no,
                            "block_index": block.index,
                            "remaining_pt": round(remaining, 1),
                            "image_height_pt": round(height, 1),
                            "suggested_scale": round(shrink_to_fit, 2),
                        }
                        layout_risks.append(risk)
                        add(
                            findings,
                            severity,
                            "docx_large_blank_before_image",
                            "An image likely moves to the next page while a moderate shrink could fit it on the current page.",
                            location=f"{path.name}: block {block.index}",
                            lang=lang,
                            **risk,
                        )
                if page_used + height > content_height_pt:
                    page_no += 1
                    page_used = 0.0
                page_used += min(height, content_height_pt)
                if page_used > content_height_pt:
                    page_no += 1
                    page_used = 0.0

                if block.kind == "paragraph" and "caption" not in block.style.lower() and "heading" not in block.style.lower():
                    tail = orphan_tail(block.text, content_width_pt, lang)
                    if tail:
                        tail_text, line_count = tail
                        add(
                            findings,
                            "warning",
                            "docx_orphan_tail_risk",
                            "A paragraph likely ends with a very short final line; rephrase slightly if confirmed in preview.",
                            location=f"{path.name}: paragraph block {block.index}",
                            lang=lang,
                            tail=tail_text,
                            estimated_lines=line_count,
                            text_preview=re.sub(r"\s+", " ", block.text)[:180],
                        )

            outline_figs = outline_figures(outline)
            if outline_figs and len(outline_figs) != len(media):
                add(findings, "warning", "outline_docx_image_count_mismatch", "Outline figure count differs from embedded DOCX media count.", location=str(path), lang=lang, outline_figures=len(outline_figs), embedded_media=len(media))

            return {
                "exists": True,
                "valid": True,
                "path": str(path),
                "lang": lang,
                "char_count": len(text),
                "paragraph_blocks": sum(1 for b in blocks if b.kind == "paragraph"),
                "image_blocks": sum(1 for b in blocks if b.kind == "image"),
                "table_blocks": sum(1 for b in blocks if b.kind == "table"),
                "media_count": len(media),
                "media": media,
                "media_sha256": media_sha256,
                "numbers": [normalize_number(n) for n in extract_numbers(text)],
                "terms": sorted(common_terms(text)),
                "outline_figures": outline_figs,
                "layout_risks": layout_risks,
                "fonts": {k: sorted(v) for k, v in fonts.items()},
                "content_box_pt": [round(content_width_pt, 1), round(content_height_pt, 1)],
            }
    except zipfile.BadZipFile:
        add(findings, "error", "docx_invalid_zip", "DOCX is not a readable zip archive.", location=str(path), lang=lang)
        return {"exists": True, "valid": False}


def compare_docs(zh: dict[str, Any], en: dict[str, Any], findings: list[Finding]) -> None:
    if not zh.get("valid") or not en.get("valid"):
        return
    if zh.get("media_count") != en.get("media_count"):
        add(findings, "error", "bilingual_image_count_mismatch", "Chinese and English DOCX files embed different numbers of images.", zh_media=zh.get("media_count"), en_media=en.get("media_count"))
    elif zh.get("media_sha256") and en.get("media_sha256") and zh.get("media_sha256") != en.get("media_sha256"):
        add(findings, "warning", "bilingual_media_hash_diff", "Chinese and English DOCX files embed different image bytes; verify the figure set/order is intentionally identical.", zh_media=zh.get("media"), en_media=en.get("media"))

    zh_outline = zh.get("outline_figures") or []
    en_outline = en.get("outline_figures") or []
    if zh_outline and en_outline and zh_outline != en_outline:
        add(findings, "error", "bilingual_outline_figure_order_mismatch", "Chinese and English outlines use different figure paths/order.", zh_figures=zh_outline, en_figures=en_outline)

    zh_nums = set(zh.get("numbers") or [])
    en_nums = set(en.get("numbers") or [])
    only_zh = sorted(zh_nums - en_nums)
    only_en = sorted(en_nums - zh_nums)
    if only_zh or only_en:
        add(
            findings,
            "warning",
            "bilingual_number_set_diff",
            "Numeric claims differ between Chinese and English versions; verify each difference is intentional.",
            only_zh=only_zh[:30],
            only_en=only_en[:30],
            zh_extra_count=len(only_zh),
            en_extra_count=len(only_en),
        )

    zh_terms = set(zh.get("terms") or [])
    en_terms = set(en.get("terms") or [])
    missing_from_en = sorted(t for t in zh_terms - en_terms if not re.match(r"^[A-Z][a-z]+$", t))
    if missing_from_en:
        add(findings, "warning", "bilingual_term_diff", "Some technical-looking terms appear only in the Chinese version.", terms=missing_from_en[:30], count=len(missing_from_en))


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel_to(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def maybe_write_manifest(outdir: Path, *, zh_path: Path, en_path: Path, report_path: Path, passed: bool) -> None:
    if looks_like_stage_dir(outdir) and not looks_like_v2_bundle(outdir):
        return
    manifest = {
        "schema_version": "paper2blog.v1",
        "layout": "v2-assets",
        "created_at": utc_now(),
        "files": {
            "blog_zh": rel_to(zh_path, outdir),
            "blog_en": rel_to(en_path, outdir),
            "assets_dir": "assets",
            "figures_dir": "assets/figures",
            "meta_dir": "assets/meta",
            "qa_report": rel_to(report_path, outdir),
        },
        "qa": {
            "check": "check_blog_package",
            "passed": passed,
            "report": rel_to(report_path, outdir),
        },
    }
    write_report(outdir / "manifest.json", manifest)


def looks_like_stage_dir(outdir: Path) -> bool:
    return (outdir / "final").is_dir() or (outdir / "intermedia").is_dir()


def looks_like_v2_bundle(outdir: Path) -> bool:
    if (outdir / "assets").is_dir():
        return True
    manifest = outdir / "manifest.json"
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get("layout") == "v2-assets"


def default_docx_path(outdir: Path, filename: str) -> Path:
    """Support v2 bundle-root files plus legacy flat/stage outputs."""
    direct = outdir / filename
    staged = outdir / "final" / filename
    if looks_like_v2_bundle(outdir):
        return direct
    if looks_like_stage_dir(outdir):
        return staged
    if direct.exists():
        return direct
    return staged if staged.exists() else direct


def default_preview_root(outdir: Path) -> Path:
    if looks_like_v2_bundle(outdir):
        return outdir / "assets" / "meta" / "previews" / "blog_qa_preview"
    if looks_like_stage_dir(outdir):
        return outdir / "intermedia" / "previews" / "blog_qa_preview"
    return outdir / "blog_qa_preview"


def default_report_path(outdir: Path) -> Path:
    if looks_like_v2_bundle(outdir):
        return outdir / "assets" / "meta" / "reports" / "blog_qa_report.json"
    if looks_like_stage_dir(outdir):
        return outdir / "intermedia" / "reports" / "blog_qa_report.json"
    return outdir / "blog_qa_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic QA gates for bilingual paper2blog DOCX outputs.")
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--zh", type=Path, default=None, help="Chinese DOCX path; default <outdir>/blog_zh.docx for v2 bundles.")
    parser.add_argument("--en", type=Path, default=None, help="English DOCX path; default <outdir>/blog_en.docx for v2 bundles.")
    parser.add_argument("--outline-zh", type=Path, default=None)
    parser.add_argument("--outline-en", type=Path, default=None)
    parser.add_argument("--preview-dir", type=Path, default=None, help="Directory for rendered DOCX PDF/PNG layout previews.")
    parser.add_argument("--zh-preview-dir", type=Path, default=None, help="Pre-rendered Chinese DOCX page PNG/JPG directory.")
    parser.add_argument("--en-preview-dir", type=Path, default=None, help="Pre-rendered English DOCX page PNG/JPG directory.")
    parser.add_argument("--no-preview", action="store_true", help="Skip LibreOffice/PDF rendered-page layout preview checks.")
    parser.add_argument("--require-preview", action="store_true", help="Fail if both DOCX files cannot be rendered and inspected as page previews.")
    parser.add_argument("--strict", action="store_true", help="Final-package hard gate: require rendered previews and fail on warnings.")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    outdir = args.outdir.resolve()
    zh_path = (args.zh or default_docx_path(outdir, "blog_zh.docx")).resolve()
    en_path = (args.en or default_docx_path(outdir, "blog_en.docx")).resolve()
    findings: list[Finding] = []

    zh_outline = load_outline(args.outline_zh.resolve() if args.outline_zh else None, findings, "zh")
    en_outline = load_outline(args.outline_en.resolve() if args.outline_en else None, findings, "en")
    zh = analyze_docx(zh_path, "zh", zh_outline, findings)
    en = analyze_docx(en_path, "en", en_outline, findings)
    compare_docs(zh, en, findings)
    require_preview = args.require_preview or args.strict
    preview_report: dict[str, Any] = {"checked": False}
    if args.no_preview:
        if require_preview:
            add(findings, "error", "docx_preview_disabled", "Strict blog QA requires rendered DOCX preview checks; remove --no-preview.")
    else:
        preview_root = (args.preview_dir or default_preview_root(outdir)).resolve()
        preview_root.mkdir(parents=True, exist_ok=True)
        if args.zh_preview_dir:
            zh_preview = load_rendered_pages_dir(args.zh_preview_dir.resolve(), "zh", findings, required=require_preview)
        else:
            zh_preview = render_docx_preview(zh_path, preview_root, "zh", findings, required=require_preview)
        if args.en_preview_dir:
            en_preview = load_rendered_pages_dir(args.en_preview_dir.resolve(), "en", findings, required=require_preview)
        else:
            en_preview = render_docx_preview(en_path, preview_root, "en", findings, required=require_preview)
        zh_layout = check_docx_preview_layout(zh_preview, "zh", findings, required=require_preview)
        en_layout = check_docx_preview_layout(en_preview, "en", findings, required=require_preview)
        preview_report = {
            "checked": bool(zh_layout.get("checked") and en_layout.get("checked")),
            "dir": str(preview_root),
            "zh": {**zh_preview, "layout": zh_layout},
            "en": {**en_preview, "layout": en_layout},
        }

    counts = {
        "error": sum(1 for f in findings if f.severity == "error"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "info": sum(1 for f in findings if f.severity == "info"),
    }
    fail_on_warning = args.fail_on_warning or args.strict
    passed = counts["error"] == 0 and (counts["warning"] == 0 or not fail_on_warning)
    report = {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "outdir": str(outdir),
        "options": {
            "strict": args.strict,
            "fail_on_warning": fail_on_warning,
            "require_preview": require_preview,
            "no_preview": args.no_preview,
            "zh_preview_dir": str(args.zh_preview_dir.resolve()) if args.zh_preview_dir else None,
            "en_preview_dir": str(args.en_preview_dir.resolve()) if args.en_preview_dir else None,
        },
        "passed": passed,
        "counts": counts,
        "documents": {"zh": zh, "en": en},
        "preview": preview_report,
        "findings": [f.__dict__ for f in findings],
    }
    report_path = args.out or default_report_path(outdir)
    write_report(report_path, report)
    maybe_write_manifest(outdir, zh_path=zh_path, en_path=en_path, report_path=report_path, passed=passed)

    status = "PASS" if passed else "FAIL"
    print(f"[check_blog_package] {status}: {counts['error']} error(s), {counts['warning']} warning(s)")
    print(f"[check_blog_package] report: {report_path}")
    if not passed:
        for finding in findings[:20]:
            loc = f" ({finding.location})" if finding.location else ""
            print(f"  - {finding.severity.upper()} {finding.code}{loc}: {finding.message}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
