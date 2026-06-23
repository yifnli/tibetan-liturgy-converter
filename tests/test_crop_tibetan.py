# tests/test_crop_tibetan.py
#
# Pytest coverage for src/crop_tibetan.py.
#
# Run with:  python -m pytest tests/test_crop_tibetan.py -v
#
# Notes on naming conventions
# ---------------------------
# crop_tibetan_spans_for_page() writes:
#   line_{id:04d}_{x}_{y}.png   (e.g. line_0000_56_89.png)
# That differs from the naming used inside verse_pipeline._extract_legacy_verse,
# which calls merge_spans_into_lines + crop_span_as_image directly and writes:
#   line{idx:03d}.png            (e.g. line000.png)
# The tests here validate the actual behaviour of crop_tibetan_spans_for_page.
#
# PIL/Pillow is not installed in this project's venv.  PNG validity is
# verified by checking the 8-byte PNG file signature instead.

import os
import sys

import fitz
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.format_detect import classify_document
from src.crop_tibetan import crop_tibetan_spans_for_page

# ── PDF paths ──────────────────────────────────────────────────────────────

_MB_PDF = os.path.join(
    os.path.dirname(__file__), "..",
    "samples", "medicine-buddha-sample",
    "Medicine-Buddha-Tib-Fr-Eng-WORD.pdf",
)
_RD_PDF = os.path.join(
    os.path.dirname(__file__), "..",
    "samples", "rigpe-dorje-treasury-of-blessings",
    "treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
)

# Page 1 of Medicine Buddha is the first content page and has exactly 9
# TIBETAN_LEGACY_FONT lines.  Page 0 is a cover/title with only 1 line.
_MB_CONTENT_PAGE = 1

# Page 2 of Rigpe Dorje is a known content page (UNICODE_TEXT only).
_RD_CONTENT_PAGE = 2

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# ── Module-scoped PDF fixtures (load each PDF once for the whole test session) ──

@pytest.fixture(scope="module")
def mb_classified():
    return classify_document(_MB_PDF)


@pytest.fixture(scope="module")
def rd_classified():
    return classify_document(_RD_PDF)


# ── Test 1: correct number of crops produced ──────────────────────────────

def test_crop_produces_9_crops_on_mb_page1(mb_classified, tmp_path):
    """MB page 1 (first content page) should yield exactly 9 PNG crops,
    one per merged TIBETAN_LEGACY_FONT visual line."""
    doc = fitz.open(_MB_PDF)
    page = doc[_MB_CONTENT_PAGE]
    spans = mb_classified["pages"][_MB_CONTENT_PAGE]["spans"]

    results = crop_tibetan_spans_for_page(page, spans, str(tmp_path))
    doc.close()

    assert len(results) == 9, (
        f"Expected 9 crops from MB page {_MB_CONTENT_PAGE}, got {len(results)}"
    )
    for r in results:
        assert os.path.exists(r["image_path"]), (
            f"Crop file does not exist: {r['image_path']}"
        )


# ── Test 2: each output file is a valid PNG ───────────────────────────────

def test_crop_files_are_valid_pngs(mb_classified, tmp_path):
    """Every file written by crop_tibetan_spans_for_page must start with the
    PNG 8-byte file signature (Pillow is not available; check bytes directly)."""
    doc = fitz.open(_MB_PDF)
    page = doc[_MB_CONTENT_PAGE]
    spans = mb_classified["pages"][_MB_CONTENT_PAGE]["spans"]

    results = crop_tibetan_spans_for_page(page, spans, str(tmp_path))
    doc.close()

    for r in results:
        with open(r["image_path"], "rb") as fh:
            header = fh.read(8)
        assert header == _PNG_SIGNATURE, (
            f"{r['image_path']} does not start with PNG signature"
        )


# ── Test 3: filename naming convention ────────────────────────────────────

def test_crop_filenames_follow_naming_convention(mb_classified, tmp_path):
    """crop_tibetan_spans_for_page writes line_{id:04d}_{x}_{y}.png.
    Filenames are checked against this pattern; zero-padded 4-digit id
    must match the result index."""
    doc = fitz.open(_MB_PDF)
    page = doc[_MB_CONTENT_PAGE]
    spans = mb_classified["pages"][_MB_CONTENT_PAGE]["spans"]

    results = crop_tibetan_spans_for_page(page, spans, str(tmp_path))
    doc.close()

    for i, r in enumerate(results):
        name = os.path.basename(r["image_path"])
        assert name.startswith(f"line_{i:04d}_"), (
            f"Crop {i}: expected filename to start with 'line_{i:04d}_', got {name!r}"
        )
        assert name.endswith(".png"), (
            f"Crop {i}: expected .png extension, got {name!r}"
        )
        assert r["line_id"] == i, (
            f"result[{i}]['line_id'] should be {i}, got {r['line_id']}"
        )


# ── Test 4: zero crops for a UNICODE_TEXT page ────────────────────────────

def test_no_crops_for_unicode_text_page(rd_classified, tmp_path):
    """A UNICODE_TEXT page (Rigpe Dorje) contains TIBETAN_UNICODE spans, not
    TIBETAN_LEGACY_FONT spans.  crop_tibetan_spans_for_page must return an
    empty list and write no files."""
    doc = fitz.open(_RD_PDF)
    page = doc[_RD_CONTENT_PAGE]
    spans = rd_classified["pages"][_RD_CONTENT_PAGE]["spans"]

    results = crop_tibetan_spans_for_page(page, spans, str(tmp_path))
    doc.close()

    assert results == [], (
        f"Expected 0 crops for UNICODE_TEXT page, got {len(results)}"
    )
    # tmp_path should have no PNG files written
    pngs = [f for f in os.listdir(tmp_path) if f.endswith(".png")]
    assert pngs == [], f"Unexpected PNG files in tmp_path: {pngs}"
