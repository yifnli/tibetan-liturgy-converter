"""
extract_text_layers.py

Extracts all text layers from a verse-unit's spans:
TIBETAN_UNICODE (as real Unicode text), ROMAN_TEXT (split into
Wylie / French / English by font style), and CJK_TEXT (split into
Mandarin homophonic transliteration / Mandarin semantic translation
by font size).

Layer assignment logic
----------------------
TIBETAN_UNICODE
  Extracted as-is; only PDF layout artefacts (embedded tabs, trailing
  newlines) are removed.  The Tibetan characters themselves are never
  modified.

ROMAN_TEXT
  Distributed by font style after skipping noise spans:
    Bold   → Wylie phonetic transliteration
    Italic → French semantic translation
    Upright (neither Bold nor Italic) → English semantic translation
  Noise spans that are always skipped:
    - Georgia font       (section/title headings)
    - HelveticaNeue font (page footer)
    - Any Roman span with size > 13 pt (spacer spans in the Tibetan font
      MonlamUniOuChan2, drop-cap titles, etc.)
  Embedded tab characters (PDF half-line separators in Wylie) are
  normalised to a double-space gap.

CJK_TEXT
  Distributed by font size — the sole reliable discriminator, because
  both Mandarin layers use the same font (STSongti-SC-Regular):
    size >= 15 pt  → mandarin_homophonic (syllable-level sound rendering)
    size <  13 pt  → mandarin_semantic   (meaning-based translation)
    13 <= size < 15 (±1 pt ambiguous band around the 14 pt threshold)
                   → vertical-proximity fallback, then ambiguous_cjk
  Homophonic spans (individual syllable groups) are joined with a space.
  Semantic spans (continuous Chinese sentences) are joined without space.
"""


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# ROMAN_TEXT spans from these fonts are layout noise and must be skipped.
_ROMAN_NOISE_FONTS = frozenset({"Georgia", "HelveticaNeue"})

# Any ROMAN_TEXT span larger than this (pt) is a title, header, or spacer
# rendered in a Tibetan font — not a content layer.
_ROMAN_MAX_SIZE_PT = 13.0

# Font-size threshold separating the two Mandarin CJK roles (pt).
_CJK_HOMOPHONIC_MIN_SIZE = 14.0

# Half-width of the ambiguous band around the threshold (pt).
# Spans in [threshold − band, threshold + band) get proximity fallback.
_CJK_AMBIGUOUS_BAND_PT = 1.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_roman_noise(span: dict) -> bool:
    """True if this ROMAN_TEXT span is layout noise (title, footer, spacer)."""
    return (
        span.get("font", "") in _ROMAN_NOISE_FONTS
        or span.get("size", 0) > _ROMAN_MAX_SIZE_PT
    )


def _normalize_roman_text(text: str) -> str:
    """Normalise PDF layout artefacts in a Roman text span.

    Steps:
      1. Replace newlines with a space (newline = PDF line-break in stream).
      2. Split on tab characters (tab = half-line column separator in Wylie).
      3. Strip each part and discard empty parts.
      4. Re-join with a double-space, preserving the half-line boundary as a
         visible gap in Wylie text.

    Result is an empty string if the span contained only tabs/newlines/spaces.
    """
    parts = text.replace("\n", " ").split("\t")
    parts = [p.strip() for p in parts]
    parts = [p for p in parts if p]
    return "  ".join(parts)


def _is_bold_font(font: str) -> bool:
    return "Bold" in font


def _is_italic_font(font: str) -> bool:
    return "Italic" in font


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------

def extract_tibetan_unicode_text(spans: list) -> str | None:
    """Extract Tibetan Unicode text from all TIBETAN_UNICODE spans.

    Strips surrounding whitespace and PDF layout artefacts (tabs, trailing
    newlines) from each span's text, then joins the results with a single
    space.  Returns None if no TIBETAN_UNICODE spans are present or all
    produce empty strings after stripping.

    The Tibetan characters themselves are never modified.
    """
    texts = []
    for span in spans:
        if span.get("classification") != "TIBETAN_UNICODE":
            continue
        text = (span.get("text") or "").replace("\t", "").replace("\n", "").strip()
        if text:
            texts.append(text)
    return " ".join(texts) if texts else None


def extract_roman_text(spans: list) -> dict:
    """Extract all Roman-script layers from a verse unit's spans.

    Filters to ROMAN_TEXT spans, skips noise spans (Georgia, HelveticaNeue,
    any span > 13 pt), normalises embedded tabs to double-space, then
    distributes the remaining content by font style:

      Bold   → Wylie phonetic transliteration
      Italic → French semantic translation
      Upright → English semantic translation

    Returns a dict with keys ``wylie``, ``french``, ``english``.  Each
    value is the normalised, joined text for that layer, or None if no
    spans of that type are present.
    """
    wylie_parts: list[str] = []
    french_parts: list[str] = []
    english_parts: list[str] = []

    for span in spans:
        if span.get("classification") != "ROMAN_TEXT":
            continue
        if _is_roman_noise(span):
            continue
        text = _normalize_roman_text(span.get("text") or "")
        if not text:
            continue
        font = span.get("font", "")
        if _is_bold_font(font):
            wylie_parts.append(text)
        elif _is_italic_font(font):
            french_parts.append(text)
        else:
            english_parts.append(text)

    return {
        "wylie":   " ".join(wylie_parts)   if wylie_parts   else None,
        "french":  " ".join(french_parts)  if french_parts  else None,
        "english": " ".join(english_parts) if english_parts else None,
    }


def split_cjk_lines_by_role(
    verse_unit_spans: list,
    wylie_span_bbox: tuple | None,
    other_translation_bboxes: list,
) -> dict:
    """Assign CJK_TEXT spans to Mandarin homophonic or Mandarin semantic.

    Primary discriminator — font size (font-encoding-agnostic; both layers
    share the same font):
      size >= 15 pt  → homophonic (size clearly above 14 pt threshold)
      size <  13 pt  → semantic   (size clearly below 14 pt threshold)
      13 <= size < 15 → ambiguous band: use vertical proximity to the
                        Wylie span vs. the English/French spans as a
                        tiebreaker; unresolvable spans go to 'ambiguous'.

    Homophonic parts (individual syllable groups) are joined with a space.
    Semantic parts (continuous Chinese sentences) are joined without space.

    Returns:
      {
        'mandarin_homophonic': str or None,
        'mandarin_semantic':   str or None,
        'ambiguous':           list of span dicts that could not be
                               confidently assigned (for human review),
      }
    """
    cjk_spans = [s for s in verse_unit_spans if s.get("classification") == "CJK_TEXT"]

    lo = _CJK_HOMOPHONIC_MIN_SIZE - _CJK_AMBIGUOUS_BAND_PT  # 13.0
    hi = _CJK_HOMOPHONIC_MIN_SIZE + _CJK_AMBIGUOUS_BAND_PT  # 15.0

    homophonic_parts: list[str] = []
    semantic_parts: list[str] = []
    ambiguous: list[dict] = []

    for span in cjk_spans:
        text = (span.get("text") or "").strip()
        if not text:
            continue
        size = span.get("size", 0)
        if size >= hi:
            homophonic_parts.append(text)
        elif size < lo:
            semantic_parts.append(text)
        else:
            # Ambiguous band: vertical-proximity fallback.
            assigned = False
            if wylie_span_bbox is not None and other_translation_bboxes:
                span_y = span["bbox"][1]
                dist_wylie = abs(span_y - wylie_span_bbox[1])
                dist_others = min(abs(span_y - b[1]) for b in other_translation_bboxes)
                if dist_wylie < dist_others:
                    homophonic_parts.append(text)
                    assigned = True
                elif dist_others < dist_wylie:
                    semantic_parts.append(text)
                    assigned = True
            if not assigned:
                ambiguous.append(span)

    return {
        "mandarin_homophonic": " ".join(homophonic_parts) if homophonic_parts else None,
        "mandarin_semantic":   "".join(semantic_parts)    if semantic_parts   else None,
        "ambiguous":           ambiguous,
    }


def _build_reference_bboxes(verse_unit_spans: list) -> tuple:
    """Internal helper: extract reference bounding boxes for the CJK
    vertical-proximity fallback.

    Returns (wylie_bbox, other_bboxes) where:
      wylie_bbox   — bbox of the first Bold ROMAN_TEXT span with content,
                     or None if absent.
      other_bboxes — list of bboxes for all non-Bold ROMAN_TEXT spans with
                     content (French + English rows), possibly empty.

    Noise spans are excluded using the same filter as extract_roman_text.
    """
    wylie_bbox: tuple | None = None
    other_bboxes: list[tuple] = []

    for span in verse_unit_spans:
        if span.get("classification") != "ROMAN_TEXT":
            continue
        if _is_roman_noise(span):
            continue
        text = _normalize_roman_text(span.get("text") or "")
        if not text:
            continue
        bbox = span.get("bbox")
        if bbox is None:
            continue
        if _is_bold_font(span.get("font", "")):
            if wylie_bbox is None:
                wylie_bbox = bbox
        else:
            other_bboxes.append(bbox)

    return wylie_bbox, other_bboxes


def extract_text_layers_for_verse_unit(verse_unit_spans: list) -> dict:
    """Top-level entry point: extract all text layers from a verse unit.

    Calls extract_tibetan_unicode_text, extract_roman_text, and
    split_cjk_lines_by_role, then assembles the results into the
    canonical seven-key output dict.

    Returns a dict with exactly these keys:
      tibetan_unicode, wylie, french, english,
      mandarin_homophonic, mandarin_semantic, ambiguous_cjk

    Each text value is a str (normalised, joined) or None if that layer
    is absent in this verse unit.  ambiguous_cjk is always a list
    (empty when all CJK spans were confidently assigned).
    """
    tibetan = extract_tibetan_unicode_text(verse_unit_spans)
    roman = extract_roman_text(verse_unit_spans)
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse_unit_spans)
    cjk = split_cjk_lines_by_role(verse_unit_spans, wylie_bbox, other_bboxes)
    return {
        "tibetan_unicode":     tibetan,
        "wylie":               roman["wylie"],
        "french":              roman["french"],
        "english":             roman["english"],
        "mandarin_homophonic": cjk["mandarin_homophonic"],
        "mandarin_semantic":   cjk["mandarin_semantic"],
        "ambiguous_cjk":       cjk["ambiguous"],
    }