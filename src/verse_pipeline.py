"""
verse_pipeline.py

Per-verse-unit orchestrator (Stage 2 + Stage 3 combined).

Takes a verse-unit dict produced by layout_segment.segment_page_spans and
returns a standardised 8-key extraction dict.  The correct acquisition path
is selected by the document-level format string (read from the ``"format"``
key returned by format_detect.classify_document):

  UNICODE_TEXT     — Tibetan already present as real Unicode text; delegate
                     entirely to extract_text_layers_for_verse_unit().
  LEGACY_FONT_TEXT — Tibetan is stored as glyph-mapped legacy-font spans;
                     crop each visual Tibetan line as a PNG image, then
                     extract Roman-script layers separately.

Output dict contract (both format paths, always 8 keys):
  {
    "tibetan_unicode":     str | None,   # None for LEGACY_FONT_TEXT
    "tibetan_image_paths": list[str],    # []   for UNICODE_TEXT
    "wylie":               str | None,
    "french":              str | None,
    "english":             str | None,
    "mandarin_homophonic": str | None,
    "mandarin_semantic":   str | None,
    "ambiguous_cjk":       list,
  }

Neither ``tibetan_unicode`` nor ``tibetan_image_paths`` is ever absent.
"""

import fitz
from pathlib import Path

from src.crop_tibetan import crop_span_as_image, merge_spans_into_lines
from src.extract_text_layers import extract_roman_text, extract_text_layers_for_verse_unit


# ── Function 1 ─────────────────────────────────────────────────────────────

def _extract_legacy_verse(
    spans: list,
    pdf_doc: fitz.Document,
    page_index: int,
    out_dir,
) -> dict:
    """Extract all layers from a LEGACY_FONT_TEXT verse-unit.

    Tibetan acquisition (Stage 2):
      - Merge TIBETAN_LEGACY_FONT spans into one merged bbox per visual line
        using merge_spans_into_lines().
      - Render each line as a PNG using crop_span_as_image(), writing the
        files into out_dir.

    Roman-layer extraction (Stage 3):
      - Call extract_roman_text() on the full span list to obtain wylie,
        french, and english.  TIBETAN_LEGACY_FONT spans are ignored by that
        function automatically.

    Returns the 8-key extraction dict.  ``tibetan_unicode`` is always None
    and ``mandarin_homophonic`` / ``mandarin_semantic`` are always None for
    this format (Medicine Buddha-style documents carry no CJK layers).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    page = pdf_doc[page_index]
    line_bboxes = merge_spans_into_lines(spans)

    image_paths = []
    for line_idx, bbox in enumerate(line_bboxes):
        # NOTE: naming convention here is line{idx:03d}.png (e.g. line000.png).
        # crop_tibetan_spans_for_page uses a different convention
        # (line_{id:04d}_{x}_{y}.png).  Do not refactor to call that function
        # without also updating anything that reads these paths.
        path = str(out_dir / f"line{line_idx:03d}.png")
        crop_span_as_image(page, tuple(bbox), path)
        image_paths.append(path)

    roman = extract_roman_text(spans)

    return {
        "tibetan_unicode":     None,
        "tibetan_image_paths": image_paths,
        "wylie":               roman["wylie"],
        "french":              roman["french"],
        "english":             roman["english"],
        "mandarin_homophonic": None,
        "mandarin_semantic":   None,
        "ambiguous_cjk":       [],
    }


# ── Function 2 ─────────────────────────────────────────────────────────────

def process_verse_unit(
    verse_unit: dict,
    doc_format: str,
    pdf_doc: fitz.Document,
    out_dir,
) -> dict:
    """Process one verse-unit dict into a complete 8-key extraction dict.

    Parameters
    ----------
    verse_unit:
        A dict as returned by segment_page_spans: keys ``page_index``,
        ``verse_index``, ``spans``.
    doc_format:
        The document-level format string from classify_document()["format"].
        Must be ``"UNICODE_TEXT"`` or ``"LEGACY_FONT_TEXT"``.
    pdf_doc:
        Open fitz.Document for the source PDF.  Required for pixel-level
        Tibetan crop rendering on the LEGACY_FONT_TEXT path; ignored on the
        UNICODE_TEXT path.
    out_dir:
        Directory (str or Path) where PNG crop files will be written.  Only
        used on the LEGACY_FONT_TEXT path.

    Returns
    -------
    dict with exactly these 8 keys (both keys always present regardless of
    format path):
      tibetan_unicode     — str | None   (None for LEGACY_FONT_TEXT)
      tibetan_image_paths — list[str]    ([] for UNICODE_TEXT)
      wylie               — str | None
      french              — str | None
      english             — str | None
      mandarin_homophonic — str | None
      mandarin_semantic   — str | None
      ambiguous_cjk       — list

    Raises
    ------
    ValueError if doc_format is not a recognised value.
    """
    spans = verse_unit["spans"]

    if doc_format == "UNICODE_TEXT":
        result = extract_text_layers_for_verse_unit(spans)
        # extract_text_layers_for_verse_unit returns 7 keys; add the 8th.
        return {**result, "tibetan_image_paths": []}

    elif doc_format == "LEGACY_FONT_TEXT":
        return _extract_legacy_verse(
            spans,
            pdf_doc,
            verse_unit["page_index"],
            out_dir,
        )

    else:
        raise ValueError(
            f"Unrecognised doc_format: {doc_format!r}. "
            "Expected 'UNICODE_TEXT' or 'LEGACY_FONT_TEXT'."
        )
