# tests/test_layout_segment.py
#
# Tests for src/layout_segment.py — Stage 1 layout segmentation.
# Tests are added cumulatively: tests for function N are only added
# after function N-1 is verified passing.

import sys
import pytest

sys.path.insert(0, "src")

from src.format_detect import classify_document
from src.layout_segment import (
    _find_tibetan_anchor_spans,
    _cluster_anchor_y0s,
    segment_page_spans,
)

_RD_PDF  = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF  = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"


# ── Session-scoped fixtures loaded from the actual PDFs ───────────────────

@pytest.fixture(scope="session")
def rd_page2_spans():
    """Classified spans from Rigpe Dorje page index 2 via classify_document."""
    doc = classify_document(_RD_PDF)
    return doc["pages"][2]["spans"]


@pytest.fixture(scope="session")
def mb_page1_spans():
    """Classified spans from Medicine Buddha page index 1 via classify_document."""
    doc = classify_document(_MB_PDF)
    return doc["pages"][1]["spans"]


# ── Tests 1–6: _find_tibetan_anchor_spans ─────────────────────────────────

def test_anchor_excludes_tibetan_unicode_title_size():
    # Title Tibetan (sz=20) must NOT be an anchor.
    spans = [
        {"classification": "TIBETAN_UNICODE", "size": 20.0,
         "bbox": (0, 74, 300, 94), "text": "གསོལ་འདེབས།", "font": "MonlamUniOuChan2"},
    ]
    assert _find_tibetan_anchor_spans(spans) == []


def test_anchor_includes_tibetan_unicode_verse_size():
    # Content Tibetan (sz=18) IS an anchor.
    spans = [
        {"classification": "TIBETAN_UNICODE", "size": 18.0,
         "bbox": (0, 261, 400, 285), "text": "༈ རྡོ་རྗེ།", "font": "MonlamUniOuChan2"},
    ]
    anchors = _find_tibetan_anchor_spans(spans)
    assert len(anchors) == 1
    assert anchors[0]["size"] == 18.0


def test_anchor_excludes_tibetan_legacy_stray_size():
    # Stray TIBETAN_LEGACY_FONT noise (sz=15.8) must NOT be an anchor.
    spans = [
        {"classification": "TIBETAN_LEGACY_FONT", "size": 15.8,
         "bbox": (72, 89, 77, 112), "text": " ", "font": "Dedris-vowa"},
    ]
    assert _find_tibetan_anchor_spans(spans) == []


def test_anchor_includes_tibetan_legacy_verse_size():
    # Verse TIBETAN_LEGACY_FONT (sz=20.9) IS an anchor.
    spans = [
        {"classification": "TIBETAN_LEGACY_FONT", "size": 20.9,
         "bbox": (72, 112, 244, 141), "text": "!,  ,", "font": "Dedris-vowa"},
    ]
    anchors = _find_tibetan_anchor_spans(spans)
    assert len(anchors) == 1
    assert anchors[0]["size"] == 20.9


def test_anchor_ignores_roman_text_regardless_of_size():
    # No ROMAN_TEXT span should ever be an anchor regardless of size.
    spans = [
        {"classification": "ROMAN_TEXT", "size": 18.0,
         "bbox": (0, 261, 300, 280), "text": "\t", "font": "MonlamUniOuChan2"},
        {"classification": "ROMAN_TEXT", "size": 12.0,
         "bbox": (0, 291, 400, 305), "text": "DOR JE CHANG", "font": "TimesNewRomanPS-BoldMT"},
    ]
    assert _find_tibetan_anchor_spans(spans) == []


def test_anchor_empty_input_returns_empty():
    assert _find_tibetan_anchor_spans([]) == []


# ── Tests 7–12: _cluster_anchor_y0s ──────────────────────────────────────

def test_cluster_empty_input_returns_empty():
    assert _cluster_anchor_y0s([]) == []


def test_cluster_single_span_returns_one_value():
    spans = [
        {"classification": "TIBETAN_UNICODE", "size": 18.0,
         "bbox": (0, 261, 400, 285), "text": "x", "font": "MonlamUniOuChan2"},
    ]
    anchors = _find_tibetan_anchor_spans(spans)
    clusters = _cluster_anchor_y0s(anchors)
    assert len(clusters) == 1
    assert abs(clusters[0] - 261.0) < 1.0


def test_cluster_rd_page2_produces_three_clusters(rd_page2_spans):
    # Rigpe Dorje page 2: 3 verse units → 3 cluster min-y0 values.
    anchors = _find_tibetan_anchor_spans(rd_page2_spans)
    clusters = _cluster_anchor_y0s(anchors)
    assert len(clusters) == 3


def test_cluster_rd_page2_values_match_known_anchors(rd_page2_spans):
    # Cluster min-y0 values must match the known verse-anchor y positions.
    anchors = _find_tibetan_anchor_spans(rd_page2_spans)
    clusters = _cluster_anchor_y0s(anchors)
    expected = [261.32, 412.39, 563.37]
    for got, exp in zip(clusters, expected):
        assert abs(got - exp) < 0.5, f"cluster {got} differs from expected {exp}"


def test_cluster_mb_page1_produces_nine_clusters(mb_page1_spans):
    # Medicine Buddha page 1: 9 visual Tibetan lines → 9 cluster values.
    # This count independently validates crop_tibetan.py's 9-crop result.
    anchors = _find_tibetan_anchor_spans(mb_page1_spans)
    clusters = _cluster_anchor_y0s(anchors)
    assert len(clusters) == 9


def test_cluster_mb_page1_values_match_crop_y_positions(mb_page1_spans):
    # Cluster min-y0 values must match the y0 positions of the 9 PNG crops
    # confirmed by crop_tibetan.py (ground truth from visual inspection).
    anchors = _find_tibetan_anchor_spans(mb_page1_spans)
    clusters = _cluster_anchor_y0s(anchors)
    expected = [112.23, 183.75, 255.03, 326.31, 397.59, 468.87, 540.15, 611.19, 682.47]
    for got, exp in zip(clusters, expected):
        assert abs(got - exp) < 0.5, f"cluster {got} differs from expected {exp}"


# ── Tests 13–23: segment_page_spans ─────────────────────────────────

def test_segment_rd_page2_three_verse_units(rd_page2_spans):
    result = segment_page_spans(rd_page2_spans, page_index=2)
    assert len(result) == 3


def test_segment_rd_page2_span_counts(rd_page2_spans):
    # Ground-truth span counts: 35, 31, 32 (sum=98; 10 header + 1 footer dropped).
    result = segment_page_spans(rd_page2_spans, page_index=2)
    counts = [len(vu["spans"]) for vu in result]
    assert counts == [35, 31, 32]


def test_segment_rd_page2_verse_index_sequential(rd_page2_spans):
    result = segment_page_spans(rd_page2_spans, page_index=2)
    assert [vu["verse_index"] for vu in result] == [0, 1, 2]


def test_segment_rd_page2_page_index_preserved(rd_page2_spans):
    result = segment_page_spans(rd_page2_spans, page_index=2)
    assert all(vu["page_index"] == 2 for vu in result)


def test_segment_rd_footer_span_not_in_any_verse(rd_page2_spans):
    # The HelveticaNeue footer span must not appear in any verse unit.
    result = segment_page_spans(rd_page2_spans, page_index=2)
    all_spans = [s for vu in result for s in vu["spans"]]
    footer_fonts = {s["font"] for s in all_spans}
    assert "HelveticaNeue" not in footer_fonts


def test_segment_rd_header_spans_not_in_any_verse(rd_page2_spans):
    # Georgia spans (section titles at y<261) must not appear in any verse unit.
    result = segment_page_spans(rd_page2_spans, page_index=2)
    all_spans = [s for vu in result for s in vu["spans"]]
    georgia_spans = [s for s in all_spans if s["font"] == "Georgia"]
    assert georgia_spans == []


def test_segment_rd_output_keys(rd_page2_spans):
    result = segment_page_spans(rd_page2_spans, page_index=2)
    for vu in result:
        assert set(vu.keys()) == {"verse_index", "page_index", "spans"}


def test_segment_mb_page1_nine_verse_units(mb_page1_spans):
    result = segment_page_spans(mb_page1_spans, page_index=1)
    assert len(result) == 9


def test_segment_mb_page1_span_counts(mb_page1_spans):
    # Ground-truth span counts derived from live data (explore_segment_counts.py).
    result = segment_page_spans(mb_page1_spans, page_index=1)
    counts = [len(vu["spans"]) for vu in result]
    assert counts == [24, 17, 17, 19, 17, 12, 21, 16, 15]


def test_segment_mb_page1_each_verse_has_tibetan_legacy_anchor(mb_page1_spans):
    result = segment_page_spans(mb_page1_spans, page_index=1)
    for vu in result:
        tib_spans = [s for s in vu["spans"]
                     if s["classification"] == "TIBETAN_LEGACY_FONT"]
        assert tib_spans, (
            f"verse {vu['verse_index']} has no TIBETAN_LEGACY_FONT spans"
        )


def test_segment_empty_spans_returns_empty():
    assert segment_page_spans([], page_index=0) == []
