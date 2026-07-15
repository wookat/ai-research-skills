#!/usr/bin/env python3
"""Post-process a .pptx to embed TrueType fonts so the file is self-contained.

OOXML's font embedding model bundles the font binaries inside the .pptx ZIP
under ``ppt/fonts/*.fntdata`` and references them from three XML manifests:

  - ``[Content_Types].xml``         declares the ``application/x-fontdata``
                                     MIME type for each font part
  - ``ppt/_rels/presentation.xml.rels``  adds Relationship entries linking
                                          each font to the presentation
  - ``ppt/presentation.xml``        adds an ``<p:embeddedFontLst>`` block
                                     mapping each typeface+weight to its
                                     relationship id

Without all three, PowerPoint silently ignores the binary and the text
renders with a metric-substitute on machines that don't have the font
installed. With all three, the .pptx ships its own fonts — viewers and
editors see + type with the original glyphs even on a fresh Windows box.

We embed exactly the four Inter weights the paper2poster templates use
(Regular/SemiBold/Bold/ExtraBold) because those are the weights the
@font-face block in the HTML loads. Reviewers can edit the text in
PowerPoint using any of those four; new text inherits the embedded face.

Usage:
    python -m scripts.font_embedder <pptx> --typeface Inter \\
        --regular path/to/Inter-Regular.ttf \\
        --bold path/to/Inter-Bold.ttf \\
        [--italic .ttf] [--bold-italic .ttf]

Library API:
    from font_embedder import embed_fonts
    embed_fonts(pptx_path, [(typeface, {'regular': ttf, 'bold': ttf, ...})])

This is a SOFT path: if a font file is missing or unreadable, we warn and
skip that weight, leaving the rest intact. The .pptx is rewritten in
place atomically (write to .tmp + rename) so a mid-run crash never leaves
a corrupt .pptx behind.
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import struct
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

# OOXML namespaces — pinned here so the regex/string edits below don't drift.
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
FONT_REL_TYPE = ("http://schemas.openxmlformats.org/"
                 "officeDocument/2006/relationships/font")
FONT_CONTENT_TYPE = "application/x-fontdata"
# Per ECMA-376 §17.8.1 / MS-OI29500 §15.2.13, embedded OBFUSCATED fonts
# must declare this content type — NOT application/x-fontdata. Office
# uses the content type to decide whether to apply the inverse XOR
# transform when reading the font part. If we write obfuscated bytes
# under application/x-fontdata, Office reads them as raw TTF, gets a
# corrupted-looking header, and either rejects the file or silently
# falls back to a system font.
OBFUSCATED_FONT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.obfuscatedFont"

# Weight tag → child element name in <p:embeddedFont>.
_WEIGHT_TO_TAG = {
    "regular":     "regular",
    "bold":        "bold",
    "italic":      "italic",
    "bold-italic": "boldItalic",
    "boldItalic":  "boldItalic",
}


def _patch_heavy_face_to_bold(ttf_bytes: bytes,
                              weight_hint: str | None = None) -> bytes:
    """If the TTF is a heavy face (usWeightClass >= 600) that lies about
    its bold-ness in its internal flags, flip the bold bits so PowerPoint
    (and other consumers that look at fsSelection / macStyle to decide
    "is this a bold variant?") will treat the embedded glyphs as bold.

    Inter ships SemiBold/ExtraBold as standalone families with subfamily
    "Regular" and bold bits OFF — that's correct under the OS's standalone-
    family registration model, but PowerPoint then sees an embedded face
    whose typeface NAME matches our run's typeface but whose bold bit is
    0, and substitutes a non-embedded "regular" Inter from the system
    instead of using the embedded glyphs. End result: heavy weights render
    as regular.

    This patch flips three things on heavy variants only:
      - OS/2.fsSelection bit 5 (BOLD)
      - OS/2.fsSelection bit 6 (REGULAR) → off
      - head.macStyle bit 0 (bold)
      - name table subfamily (nameID 2) → 'Bold' / 'SemiBold' / 'ExtraBold'

    Soft path: if fontTools is missing or the font is unparseable, returns
    the bytes unchanged.
    """
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return ttf_bytes
    try:
        f = TTFont(io.BytesIO(ttf_bytes))
        os2 = f["OS/2"]
        head = f["head"]
        weight_class = int(os2.usWeightClass)
        # Only touch faces that are heavier than Regular but advertise
        # themselves as non-bold. Skip the actual Bold (700) face: it
        # already has the flags set correctly.
        if weight_class < 600:
            return ttf_bytes
        bold_already = bool(os2.fsSelection & 0x20) and bool(head.macStyle & 0x01)
        if bold_already:
            return ttf_bytes
        # Set BOLD (bit 5), clear REGULAR (bit 6).
        os2.fsSelection = (os2.fsSelection | 0x20) & ~0x40
        head.macStyle = head.macStyle | 0x01
        # Rewrite subfamily name (nameID 2) so the face advertises itself
        # as a bold-style variant. Prefer the weight hint we got from the
        # caller; fall back to a class-derived label.
        new_subfamily = (weight_hint or "").strip().lower()
        if new_subfamily in ("regular", "", "bold", None):
            new_subfamily = (
                "SemiBold" if weight_class < 700
                else "ExtraBold" if weight_class >= 800
                else "Bold"
            )
        else:
            # 'bold-italic' → 'Bold Italic', 'italic' stays as-is, etc.
            new_subfamily = new_subfamily.replace("-", " ").title()
        for rec in list(f["name"].names):
            if rec.nameID == 2:
                try:
                    rec.string = new_subfamily.encode(
                        "utf-16-be" if rec.platformID == 3 else "ascii")
                except UnicodeEncodeError:
                    rec.string = new_subfamily.encode("utf-16-be")
        out = io.BytesIO()
        f.save(out)
        return out.getvalue()
    except Exception as e:
        _eprint(f"[font_embedder] heavy-face patch skipped: {e}")
        return ttf_bytes


def _eprint(*a) -> None:
    print(*a, file=sys.stderr)


def _font_guid_str() -> str:
    """Generate a fresh GUID in the OOXML embedded-font canonical form:
    '{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}' (uppercase, brace-wrapped)."""
    return "{" + str(uuid.uuid4()).upper() + "}"


def _obfuscate_first_32(data: bytes, guid_str: str) -> bytes:
    """Apply OOXML §17.8.1 first-32-byte obfuscation to a font binary.

    Algorithm (matches docx4j's ObfuscatedFontPart.deObfuscate, which
    interoperates with Microsoft Office in production):
      1. Strip `{` and `}` from the relationship GUID.
      2. Remove `-` separators → 32 hex chars.
      3. Parse in STRING ORDER (NOT .NET mixed-endian — a previous
         attempt with .NET-endian was rejected by both Mac AND Windows
         PowerPoint as 'corrupted'). 16 bytes of key.
      4. XOR bytes 0..15 of the font data with `key[15 - i]`
         (i.e., the key is applied in REVERSE).
      5. XOR bytes 16..31 with the same reversed key again.

    Why the previous string-order attempt (commit fb587b4 rolled back)
    was ALSO rejected by Mac PowerPoint: the algorithm was correct, but
    the Content Type was wrong. The embedded part was tagged as
    `application/x-fontdata` (raw-font content type); when the OOXML
    runtime sees that content type it doesn't apply de-obfuscation, so
    the XORed first-32-bytes look like a corrupted TTF header. The fix
    is to also tag obfuscated parts as
    `application/vnd.openxmlformats-officedocument.obfuscatedFont` — see
    OBFUSCATED_FONT_CONTENT_TYPE below. With BOTH the algorithm AND
    the content type right, Office reads the part, applies the
    inverse XOR (using the GUID from the relationship Id), and gets a
    valid TTF.
    """
    if len(data) < 32:
        return data
    hex_chars = guid_str.strip("{}").replace("-", "")
    if len(hex_chars) != 32:
        raise ValueError(f"bad GUID for obfuscation: {guid_str!r}")
    key = bytes.fromhex(hex_chars)             # 16 bytes, STRING ORDER
    out = bytearray(data)
    for i in range(16):
        out[i] ^= key[15 - i]                  # bytes 0..15 XOR reversed key
        out[i + 16] ^= key[15 - i]             # bytes 16..31 XOR reversed key again
    return bytes(out)


def _build_eot_uncompressed(ttf_bytes: bytes,
                            family_override: str | None = None,
                            style_override: str | None = None) -> bytes:
    """Wrap raw TTF bytes in an EOT (Embedded OpenType) v2.2 container,
    flags=0 (no compression). Returns the EOT bytes ready to be written
    as a `.fntdata` part inside a .pptx.

    `family_override` / `style_override`: if set, override the family/style
    names from the TTF `name` table. Matches Office's reference behavior
    where all 4 weight slots are encoded with family="Inter" + style of
    {"Regular","Bold","Italic","Bold Italic"} even when the underlying
    TTF file is "Inter-ExtraBold.ttf" (internal name "Inter ExtraBold").
    PowerPoint resolves runs by the `<p:embeddedFont>` typeface attribute,
    which references the EOT's family field — they MUST match.

    Why this exists: Microsoft Office produces .pptx files where each
    `ppt/fonts/font*.fntdata` part is an EOT-wrapped font — NOT raw TTF
    and NOT XOR-obfuscated TTF. Reverse-engineered from a Word/PowerPoint
    -authored reference (debug/reference.pptx, prior session). Office's
    own EOTs use MicroType Express (MTX) compression for the font_data
    payload, but MTX is Microsoft-patented and not freely implementable.
    Per W3C EOT spec §4.2, MTX is OPTIONAL — flags=0 means the payload
    is raw uncompressed TTF, which our PoC encoder produces and which
    we hope PowerPoint accepts. Needs hands-on Mac + Windows testing
    per release because Office's parser tolerance is opaque.

    EOT v2.2 header layout (per W3C EOT spec, all little-endian):
      ULONG  EOTSize            — total file size (header + font_data)
      ULONG  FontDataSize       — uncompressed font_data size = len(ttf_bytes)
      ULONG  Version            — 0x00020002 (v2.2)
      ULONG  Flags              — 0 (no compression, no subset, no XOR)
      BYTE   FontPANOSE[10]     — from TTF OS/2 panose table
      BYTE   Charset            — 0 (ANSI)
      BYTE   Italic             — 0x00 or 0xFF (per Office reference)
      ULONG  Weight             — from OS/2 usWeightClass (e.g. 400)
      USHORT fsType             — from OS/2 fsType
      USHORT MagicNumber        — 0x504C
      ULONG  UnicodeRange1..4   — from OS/2
      ULONG  CodePageRange1..2  — from OS/2
      ULONG  CheckSumAdjustment — from head table
      ULONG  Reserved1..4       — 0
      USHORT Padding1           — 0
      USHORT FamilyNameSize     — bytes (UTF-16LE chars × 2)
      BYTE   FamilyName[…]      — UTF-16LE, NULL-terminated
      USHORT Padding2 + StyleName block
      USHORT Padding3 + VersionName block
      USHORT Padding4 + FullName block
      USHORT Padding5 + RootString block (empty)
      ULONG  RootStringCheckSum — 0
      ULONG  EUDCCodePage       — 0
      USHORT Padding6 + Signature block (empty)
      ULONG  EUDCFlags          — 0
      ULONG  EUDCFontSize       — 0
      [no EUDCFontData]
      BYTE   FontData[FontDataSize] — raw TTF bytes
    """
    # fontTools is heavy; import lazily so the embedder module still
    # imports cleanly when EOT-wrap mode isn't being used.
    from fontTools.ttLib import TTFont

    font = TTFont(io.BytesIO(ttf_bytes))
    os2 = font["OS/2"]
    p = os2.panose
    panose = bytes([p.bFamilyType, p.bSerifStyle, p.bWeight, p.bProportion,
                    p.bContrast, p.bStrokeVariation, p.bArmStyle, p.bLetterForm,
                    p.bMidline, p.bXHeight])
    weight = int(os2.usWeightClass)
    fs_type = int(os2.fsType)
    is_italic = bool(int(os2.fsSelection) & 0x01)
    italic_byte = 0xFF if is_italic else 0  # 255 for italic, per Office reference
    charset = 0

    unicode_range = [int(getattr(os2, f"ulUnicodeRange{i}", 0)) for i in (1, 2, 3, 4)]
    code_page_range = [int(getattr(os2, "ulCodePageRange1", 0)),
                       int(getattr(os2, "ulCodePageRange2", 0))]
    check_sum_adjustment = int(font["head"].checkSumAdjustment) & 0xFFFFFFFF

    def name_str(name_id: int) -> str:
        # Prefer English Windows (3, 1, 0x409); fall back to any.
        for record in font["name"].names:
            if record.nameID == name_id and \
               (record.platformID, record.platEncID, record.langID) == (3, 1, 0x409):
                return record.toUnicode()
        for record in font["name"].names:
            if record.nameID == name_id:
                try:
                    return record.toUnicode()
                except Exception:
                    continue
        return ""

    def utf16le(s: str, trailing_null: bool = False) -> bytes:
        if trailing_null:
            s = s + "\x00"
        return s.encode("utf-16-le")

    # Per Office reference: family/style/version have trailing NULL,
    # full_name doesn't. Use overrides (typeface name from the
    # <p:embeddedFont> declaration + weight-slot label) when provided so
    # the EOT family/style match the names PowerPoint looks up at render
    # time. Without overrides, an Inter-ExtraBold.ttf would land in the
    # bold slot with internal family "Inter ExtraBold" — mismatching
    # the <p:font typeface="Inter"> declaration and possibly causing
    # PowerPoint to ignore the embed.
    family_text = family_override if family_override is not None else name_str(1)
    style_text = style_override if style_override is not None else name_str(2)
    full_text = name_str(4) if family_override is None \
        else (f"{family_text} {style_text}" if style_text else family_text)
    family_b = utf16le(family_text, trailing_null=True)
    style_b = utf16le(style_text, trailing_null=True)
    version_b = utf16le(name_str(5), trailing_null=True)
    full_b = utf16le(full_text, trailing_null=False)
    root_string_b = b""

    parts: list[bytes] = []
    parts.append(struct.pack("<L", 0))                # EOTSize (back-patched)
    parts.append(struct.pack("<L", len(ttf_bytes)))   # FontDataSize
    parts.append(struct.pack("<L", 0x00020002))       # Version
    parts.append(struct.pack("<L", 0x00000000))       # Flags (uncompressed)
    parts.append(panose)
    parts.append(bytes([charset]))
    parts.append(bytes([italic_byte]))
    parts.append(struct.pack("<L", weight))
    parts.append(struct.pack("<H", fs_type))
    parts.append(struct.pack("<H", 0x504C))           # MagicNumber
    for u in unicode_range:
        parts.append(struct.pack("<L", u))
    for c in code_page_range:
        parts.append(struct.pack("<L", c))
    parts.append(struct.pack("<L", check_sum_adjustment))
    for _ in range(4):
        parts.append(struct.pack("<L", 0))            # Reserved1..4

    parts.append(struct.pack("<H", 0))                # Padding1
    parts.append(struct.pack("<H", len(family_b)))
    parts.append(family_b)
    parts.append(struct.pack("<H", 0))                # Padding2
    parts.append(struct.pack("<H", len(style_b)))
    parts.append(style_b)
    parts.append(struct.pack("<H", 0))                # Padding3
    parts.append(struct.pack("<H", len(version_b)))
    parts.append(version_b)
    parts.append(struct.pack("<H", 0))                # Padding4
    parts.append(struct.pack("<H", len(full_b)))
    parts.append(full_b)

    # v > 0x00010000 → RootString block (empty)
    parts.append(struct.pack("<H", 0))                # Padding5
    parts.append(struct.pack("<H", len(root_string_b)))
    parts.append(root_string_b)

    # v > 0x00020001 → v2.2 extras
    parts.append(struct.pack("<L", 0))                # RootStringCheckSum
    parts.append(struct.pack("<L", 0))                # EUDCCodePage
    parts.append(struct.pack("<H", 0))                # Padding6
    parts.append(struct.pack("<H", 0))                # SignatureSize
    parts.append(struct.pack("<L", 0))                # EUDCFlags
    parts.append(struct.pack("<L", 0))                # EUDCFontSize

    parts.append(ttf_bytes)

    out = b"".join(parts)
    # Back-patch EOTSize at offset 0
    return struct.pack("<L", len(out)) + out[4:]


def _next_rid(rels_xml: str) -> int:
    """Highest existing rId number in the relationships XML, +1."""
    ids = re.findall(r'Id="rId(\d+)"', rels_xml)
    return (max(int(i) for i in ids) + 1) if ids else 1


def _content_types_add(content_types_xml: str,
                       parts: list[tuple[str, str]]) -> str:
    """Add <Override> per font part if missing.

    `parts` is a list of (part_path, content_type) tuples. Obfuscated
    fonts use OBFUSCATED_FONT_CONTENT_TYPE; raw fonts use FONT_CONTENT_TYPE.
    """
    out = content_types_xml
    for part, ctype in parts:
        if f'PartName="/{part}"' in out:
            continue
        override = (f'<Override PartName="/{part}" '
                    f'ContentType="{ctype}"/>')
        # Insert before </Types>.
        out = out.replace("</Types>", override + "</Types>")
    return out


def _rels_add_fonts(rels_xml: str, font_parts: list[tuple[str, str]]) -> str:
    """Add Relationship entries for each (rid, target_path) pair. Returns
    the updated XML. Assumes rels_xml has a </Relationships> close tag."""
    out = rels_xml
    for rid, target in font_parts:
        if f'Id="{rid}"' in out:
            continue
        # target is relative to /ppt/ (e.g. "fonts/font1.fntdata").
        entry = (f'<Relationship Id="{rid}" '
                 f'Type="{FONT_REL_TYPE}" Target="{target}"/>')
        out = out.replace("</Relationships>", entry + "</Relationships>")
    return out


def _build_embedded_font_lst(faces: list[dict]) -> str:
    """Build the <p:embeddedFontLst> block from a list of dicts with
    {typeface: str, weights: {'regular': rid, 'bold': rid, ...}}."""
    lines = ['<p:embeddedFontLst>']
    for face in faces:
        typeface = face["typeface"]
        lines.append(f'<p:embeddedFont>')
        lines.append(f'<p:font typeface="{typeface}" charset="0"/>')
        for weight, rid in face["weights"].items():
            tag = _WEIGHT_TO_TAG.get(weight)
            if not tag:
                continue
            lines.append(f'<p:{tag} r:id="{rid}"/>')
        lines.append('</p:embeddedFont>')
    lines.append('</p:embeddedFontLst>')
    return "".join(lines)


def _inject_font_lst(presentation_xml: str, font_lst_xml: str) -> str:
    """Insert the <p:embeddedFontLst> block in schema-valid position.

    Per the OOXML PresentationML schema, the element sits between
    <p:notesSz> (always present) and <p:defaultTextStyle>. We anchor on
    <p:defaultTextStyle> because it's stable across python-pptx outputs.

    If the document already has an <p:embeddedFontLst>, we REPLACE it —
    re-running the embedder must be idempotent. Otherwise we insert
    before <p:defaultTextStyle>."""
    # Replace existing block, if any.
    existing = re.search(r"<p:embeddedFontLst>.*?</p:embeddedFontLst>",
                         presentation_xml, re.DOTALL)
    if existing:
        return (presentation_xml[:existing.start()]
                + font_lst_xml
                + presentation_xml[existing.end():])
    # Insert before <p:defaultTextStyle> (always present in python-pptx out).
    anchor = "<p:defaultTextStyle>"
    if anchor not in presentation_xml:
        # Fallback: insert before </p:presentation>.
        anchor = "</p:presentation>"
    return presentation_xml.replace(anchor, font_lst_xml + anchor, 1)


def embed_fonts(pptx_path: Path,
                fonts: list[tuple[str, dict[str, Path]]],
                obfuscate: bool = False,
                eot_wrap: bool = False) -> dict:
    """Embed fonts into an existing .pptx.

    Args:
      pptx_path: path to the .pptx (modified in place).
      fonts: list of (typeface, {weight: ttf_path}) tuples.
             weight is one of: 'regular', 'bold', 'italic', 'bold-italic'.
             A typeface may declare any subset of the four weights.
      obfuscate: when True, apply OOXML §17.8.1 first-32-bytes XOR
             obfuscation with a .NET-endian GUID-derived key. DEFAULT
             FALSE — the .NET-endian implementation we tried (2026-06)
             produces files that Mac AND Windows PowerPoint reject as
             'corrupted'. Algorithm or rId format is still wrong despite
             matching documented MS behavior; needs more reverse-
             engineering against an Office-authored sample .pptx.
             With obfuscation off, Windows PowerPoint falls back to
             Calibri when Inter isn't system-installed — known
             trade-off; cross-platform openable beats Windows font
             fidelity until we get the algorithm right.

    Returns: {'embedded': int, 'skipped': int, 'bytes_added': int}.
    """
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.exists():
        raise FileNotFoundError(pptx_path)

    # ── 1. Read existing .pptx into memory + open a tmp output zip ──
    with zipfile.ZipFile(pptx_path, "r") as zin:
        members = {info.filename: zin.read(info.filename) for info in zin.infolist()}

    rels_xml = members["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    presentation_xml = members["ppt/presentation.xml"].decode("utf-8")
    content_types_xml = members["[Content_Types].xml"].decode("utf-8")

    # ── 2. Walk the fonts list, assign rIds + part paths, queue binaries ──
    faces_out = []
    new_parts = []   # for [Content_Types].xml Override entries
    new_rels = []    # for ppt/_rels/presentation.xml.rels Relationship entries
    new_binaries: dict[str, bytes] = {}   # zip path → file bytes
    embedded = 0
    skipped = 0
    bytes_added = 0
    counter = 0  # font part index

    for typeface, weight_map in fonts:
        face_entry = {"typeface": typeface, "weights": {}}
        for weight, ttf in weight_map.items():
            ttf = Path(ttf)
            if not ttf.exists():
                _eprint(f"[font_embedder] missing {ttf} ({typeface} {weight}); "
                        f"skipping this weight")
                skipped += 1
                continue
            counter += 1
            part = f"ppt/fonts/font{counter}.fntdata"
            target = f"fonts/font{counter}.fntdata"  # relative to ppt/
            # When obfuscation is ON, the rId IS the GUID (wrapped in {})
            # and the same GUID seeds the first-32-byte XOR key. Without
            # obfuscation we use a sequential numeric rId and keep raw
            # font bytes — this is what python-pptx output looks like
            # by default and what LibreOffice / older Office versions
            # accept unconditionally.
            if obfuscate:
                rid = _font_guid_str()
            else:
                rid = f"rId{_next_rid(rels_xml) + len(new_rels)}"
            blob = ttf.read_bytes()
            blob = _patch_heavy_face_to_bold(blob, weight_hint=weight)
            if eot_wrap:
                # Wrap the (possibly bold-patched) TTF in an EOT v2.2
                # uncompressed container. This is what Office produces —
                # see _build_eot_uncompressed() docstring. EOT framing
                # is orthogonal to XOR obfuscation; the two are mutually
                # exclusive in our embedder (CLI asserts at most one).
                # Pass typeface + weight-slot label so EOT family/style
                # match the <p:font typeface="..."> declaration.
                style_label = {
                    "regular": "Regular",
                    "bold": "Bold",
                    "italic": "Italic",
                    "bold-italic": "Bold Italic",
                    "bold_italic": "Bold Italic",
                }.get(weight, "Regular")
                blob = _build_eot_uncompressed(blob,
                                               family_override=typeface,
                                               style_override=style_label)
            elif obfuscate:
                # XOR the first 32 bytes with the docx4j-style key.
                blob = _obfuscate_first_32(blob, rid)
            new_binaries[part] = blob
            new_parts.append((part,
                              OBFUSCATED_FONT_CONTENT_TYPE if obfuscate
                              else FONT_CONTENT_TYPE))
            new_rels.append((rid, target))
            face_entry["weights"][weight] = rid
            embedded += 1
            bytes_added += len(blob)
        if face_entry["weights"]:
            faces_out.append(face_entry)

    if not faces_out:
        _eprint(f"[font_embedder] no usable fonts in {pptx_path}; "
                f"nothing to embed.")
        return {"embedded": 0, "skipped": skipped, "bytes_added": 0}

    # ── 3. Patch the three XML manifests ──
    content_types_xml = _content_types_add(content_types_xml, new_parts)
    rels_xml = _rels_add_fonts(rels_xml, new_rels)
    font_lst = _build_embedded_font_lst(faces_out)
    presentation_xml = _inject_font_lst(presentation_xml, font_lst)

    members["[Content_Types].xml"] = content_types_xml.encode("utf-8")
    members["ppt/_rels/presentation.xml.rels"] = rels_xml.encode("utf-8")
    members["ppt/presentation.xml"] = presentation_xml.encode("utf-8")
    members.update({k: v for k, v in new_binaries.items()})

    # ── 4. Rewrite the .pptx atomically (write to tmp, rename in place) ──
    tmp = pptx_path.with_suffix(pptx_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in members.items():
            zout.writestr(name, data)
    shutil.move(str(tmp), str(pptx_path))

    _eprint(f"[font_embedder] {pptx_path.name}: embedded {embedded} weight(s) "
            f"across {len(faces_out)} typeface(s), "
            f"+{bytes_added // 1024} KB")
    return {"embedded": embedded, "skipped": skipped, "bytes_added": bytes_added}


def _parse_font_spec(spec: str) -> tuple[str, dict[str, Path]]:
    """Parse a comma-separated --font value into (family, weight_map).

    Format: 'family=NAME,regular=PATH[,bold=PATH][,italic=PATH][,bold-italic=PATH]'

    Accepts `bold_italic` as an alias for `bold-italic` (both Python-friendly
    and shell-friendly). Whitespace around keys/values is trimmed.

    Raises ValueError on malformed input.
    """
    fields: dict[str, str] = {}
    for part in spec.split(","):
        if "=" not in part:
            raise ValueError(f"--font spec missing '=' in segment {part!r}")
        k, _, v = part.partition("=")
        fields[k.strip()] = v.strip()
    family = fields.pop("family", None) or fields.pop("typeface", None)
    if not family:
        raise ValueError(f"--font spec missing family=NAME: {spec!r}")
    weight_keys = {"regular", "bold", "italic", "bold-italic", "bold_italic"}
    weights: dict[str, Path] = {}
    for k, v in fields.items():
        k_norm = k.replace("_", "-")
        if k_norm not in weight_keys:
            raise ValueError(f"--font spec unknown key {k!r} in: {spec!r}")
        if not v:
            raise ValueError(f"--font spec empty value for {k!r} in: {spec!r}")
        weights[k_norm] = Path(v)
    if not weights:
        raise ValueError(f"--font spec needs at least one weight key: {spec!r}")
    return family, weights


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("pptx", type=Path, help="target .pptx (modified in place)")
    ap.add_argument(
        "--font", action="append", default=[],
        help="font family spec: 'family=NAME,regular=PATH[,bold=PATH]"
             "[,italic=PATH][,bold-italic=PATH]'. Repeatable for multi-family "
             "embedding (e.g. embed Inter + Inter SemiBold + Inter ExtraBold "
             "as separate typefaces so PPTX renders SemiBold/ExtraBold as "
             "themselves instead of falling back to Bold — OOXML's classic "
             "embedded-font spec only has 4 slots per family).",
    )
    # Backward-compat: original single-family CLI. If --font is given, these
    # are ignored.
    ap.add_argument("--typeface",
                    help="(legacy single-family form) CSS font-family name; "
                         "use --font for multi-family embedding")
    ap.add_argument("--regular", type=Path, help="(legacy) .ttf for weight 400")
    ap.add_argument("--bold", type=Path, help="(legacy) .ttf for weight 700")
    ap.add_argument("--italic", type=Path, help="(legacy) .ttf for italic 400")
    ap.add_argument("--bold-italic", type=Path, dest="bold_italic",
                    help="(legacy) .ttf for italic 700")
    ap.add_argument("--obfuscate-fonts", action=argparse.BooleanOptionalAction,
                    default=False,
                    help="Apply OOXML §17.8.1 font obfuscation (first-32-byte XOR "
                         "with .NET-endian GUID-derived key). DEFAULT OFF — the "
                         ".NET-endian obfuscation we tried (2026-06) is rejected "
                         "by both Mac and Windows PowerPoint as 'corrupted'. "
                         "Algorithm or rId format is still wrong despite matching "
                         "the documented MS behavior; needs more reverse-engineering "
                         "against an Office-authored sample .pptx. Pass "
                         "--obfuscate-fonts to re-enable when the algorithm is "
                         "fixed. With it off, embedded fonts ride along but "
                         "Windows PowerPoint silently falls back to Calibri.")
    ap.add_argument("--eot-wrap", action=argparse.BooleanOptionalAction,
                    default=False,
                    help="Wrap each embedded TTF in an EOT v2.2 uncompressed "
                         "container before writing as .fntdata. EXPERIMENTAL — "
                         "Office's own .pptx files use EOT format (verified by "
                         "reverse-engineering Word/PowerPoint-authored reference "
                         "fonts at debug/reference.pptx, 2026-06). Office uses "
                         "MicroType Express compression which is patented; our "
                         "encoder produces uncompressed EOT (flags=0) which the "
                         "W3C spec permits. Needs hands-on Mac + Windows testing "
                         "per release. Mutually exclusive with --obfuscate-fonts "
                         "(EOT framing replaces XOR obfuscation).")
    a = ap.parse_args()

    fonts: list[tuple[str, dict[str, Path]]] = []

    # New CLI: --font (repeatable).
    for spec in a.font:
        try:
            family, weights = _parse_font_spec(spec)
        except ValueError as e:
            _eprint(f"ERROR: {e}")
            return 2
        fonts.append((family, weights))

    # Legacy CLI: --typeface + weight flags. Ignored when --font was used.
    if not fonts and a.typeface:
        weight_map: dict[str, Path] = {}
        if a.regular: weight_map["regular"] = a.regular
        if a.bold: weight_map["bold"] = a.bold
        if a.italic: weight_map["italic"] = a.italic
        if a.bold_italic: weight_map["bold-italic"] = a.bold_italic
        if not weight_map:
            _eprint("ERROR: --typeface requires at least one of --regular / "
                    "--bold / --italic / --bold-italic")
            return 2
        fonts.append((a.typeface, weight_map))

    if not fonts:
        _eprint("ERROR: pass --font 'family=NAME,regular=PATH,...' "
                "(repeatable for multi-family) or the legacy --typeface NAME "
                "+ --regular/--bold/--italic/--bold-italic")
        return 2

    if a.obfuscate_fonts and a.eot_wrap:
        _eprint("[font_embedder] ERROR: --obfuscate-fonts and --eot-wrap are "
                "mutually exclusive (EOT framing replaces XOR obfuscation).")
        return 1
    result = embed_fonts(a.pptx, fonts, obfuscate=a.obfuscate_fonts,
                         eot_wrap=a.eot_wrap)
    return 0 if result["embedded"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
