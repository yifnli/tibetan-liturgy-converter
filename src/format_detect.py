"""
format_detect.py

Classifies spans within a PDF page into one of:
- TIBETAN_UNICODE: text span uses a known Unicode Tibetan font and the
  extracted text actually decodes to Tibetan Unicode codepoints
- TIBETAN_LEGACY_FONT: span's font is not a known Unicode Tibetan font,
  but text content looks like Tibetan-position content (heuristic: dense
  with non-alphanumeric symbols atypical of normal Latin prose) — visually
  Tibetan, textually meaningless if extracted naively
- ROMAN_TEXT: ordinary Latin-script text (English, French, Wylie phonetic)
- CJK_TEXT: Chinese-character text — NOTE this is intentionally a single
  classification at this stage; distinguishing semantic-translation lines
  from homophonic-transliteration lines is NOT a font/script-level
  decision and happens later, in extract_text_layers.py, using positional
  and content heuristics (see that module's docstring)

Page-level geometry (PECHA_IMAGE vs standard) is still checked first and
gates which of the above span-level classifications are even possible:
PECHA_IMAGE pages have no extractable text layer at all, so no span-level
classification applies; the whole Tibetan region must be band-detected and
cropped as an image instead.

Uses PyMuPDF (fitz) to inspect page geometry and per-span font metadata.
"""

import fitz  # PyMuPDF
import re

KNOWN_UNICODE_TIBETAN_FONTS = {
    "Jomolhari", "Microsoft Himalaya", "Noto Sans Tibetan",
    "Tibetan Machine Uni", "Qomolangma-Uchen", "MonlamUniOuChan2",
}

PECHA_ASPECT_RATIO_THRESHOLD = 3.0  # width:height ratio above this suggests pecha format

# Unicode block range for Tibetan script: U+0F00 to U+0FFF
TIBETAN_UNICODE_RANGE = (0x0F00, 0x0FFF)

# Unicode blocks covering common CJK ranges:
# CJK Unified Ideographs, Extension A, CJK Symbols and Punctuation
# (The Symbols block covers brackets like \u3008 \u3009 used as quotation marks
# in Chinese liturgical texts — must be included to avoid density-heuristic
# false positives on those characters.)
CJK_UNICODE_RANGES = [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x3000, 0x303F)]


def classify_page_geometry(page: fitz.Page) -> str:
    """Returns 'pecha' if page dimensions suggest traditional pecha format,
    else 'standard'."""
    width = page.rect.width
    height = page.rect.height
    aspect_ratio = width / height
    if aspect_ratio > PECHA_ASPECT_RATIO_THRESHOLD:
        return "pecha"
    return "standard"


def _contains_codepoints_in_range(text: str, range_tuple: tuple) -> bool:
    """Returns True if any character in text falls within the given
    (start, end) Unicode codepoint range."""
    start, end = range_tuple
    return any(start <= ord(char) <= end for char in text)


def is_tibetan_unicode(text: str) -> bool:
    """True if text contains genuine Tibetan Unicode codepoints —
    this is the actual ground-truth check, independent of font name,
    since a correctly-encoded span should decode to this range
    regardless of which specific Unicode Tibetan font renders it."""
    return _contains_codepoints_in_range(text, TIBETAN_UNICODE_RANGE)


def is_cjk_text(text: str) -> bool:
    """True if text contains CJK ideographs. Does not distinguish
    Chinese/Japanese/Korean and does not distinguish semantic-translation
    from homophonic-transliteration Chinese — that distinction is made
    later by extract_text_layers.py using context, not script detection,
    since both kinds of Chinese line use the exact same character set."""
    return any(_contains_codepoints_in_range(text, r) for r in CJK_UNICODE_RANGES)

LEGACY_FONT_SYMBOL_DENSITY_THRESHOLD = 0.15  # tune against real samples below
LEGACY_FONT_SYMBOL_PATTERN = re.compile(r"[^A-Za-z0-9\s]")

def classify_span(span: dict) -> str:
    """Given a PyMuPDF span dict (from page.get_text('dict')), returns one
    of TIBETAN_UNICODE / TIBETAN_LEGACY_FONT / ROMAN_TEXT / CJK_TEXT.

    Decision order matters: check actual Tibetan Unicode codepoints FIRST
    (ground truth, font-independent), THEN CJK, THEN fall back to the
    legacy-font heuristic only for spans that are neither.
    """
    text = span.get("text") or ""
    font = span.get("font", "")

    if is_tibetan_unicode(text):
        return "TIBETAN_UNICODE"
    if is_cjk_text(text):
        return "CJK_TEXT"

    if text.strip():
        symbol_chars = LEGACY_FONT_SYMBOL_PATTERN.findall(text)
        density = len(symbol_chars) / len(text)
    else:
        density = 0.0

    if font not in KNOWN_UNICODE_TIBETAN_FONTS and density > LEGACY_FONT_SYMBOL_DENSITY_THRESHOLD:
        return "TIBETAN_LEGACY_FONT"

    return "ROMAN_TEXT"

def classify_document(pdf_path: str) -> dict:
    """Top-level entry point: returns a per-page, per-span classification
    structure for the whole document. Each page's result also records the
    page-geometry classification (pecha/standard) since downstream stages
    branch on that independently of span-level results."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        geometry = classify_page_geometry(page)
        spans = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    spans.append({
                        "text": span.get("text") or "",
                        "font": span.get("font", ""),
                        "bbox": span.get("bbox"),
                        "classification": classify_span(span),
                    })
        pages.append({"geometry": geometry, "spans": spans})
    return {"pages": pages}