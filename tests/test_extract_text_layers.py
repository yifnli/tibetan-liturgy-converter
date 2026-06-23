# tests/test_extract_text_layers.py
#
# 32 tests for src/extract_text_layers.py.
# Fixtures are loaded once per session from page index 2 of the Rigpe Dorje
# sample PDF and sliced into verse-unit spans by y-coordinate range.
# Expected text values were derived from live span data extracted from that
# page (see tests/explore_page2_spans.py and tests/explore_page2_full_text.py).

import sys
import pytest

sys.path.insert(0, "src")

import fitz  # PyMuPDF
from src.format_detect import classify_span
from src.extract_text_layers import (
    _build_reference_bboxes,
    extract_tibetan_unicode_text,
    extract_roman_text,
    split_cjk_lines_by_role,
    extract_text_layers_for_verse_unit,
)

# ---------------------------------------------------------------------------
# Session-scoped fixtures: loaded once from the Rigpe Dorje PDF
# ---------------------------------------------------------------------------

_PDF_PATH = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_PAGE_IDX = 2  # zero-based (third physical page)


@pytest.fixture(scope="session")
def page2_spans():
    """All classified spans from page index 2 of the Rigpe Dorje PDF."""
    doc = fitz.open(_PDF_PATH)
    page = doc[_PAGE_IDX]
    spans = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                spans.append({
                    "text": span.get("text") or "",
                    "font": span.get("font", ""),
                    "size": round(span.get("size", 0), 2),
                    "bbox": tuple(round(v, 2) for v in span["bbox"]),
                    "classification": classify_span(span),
                })
    doc.close()
    return spans


@pytest.fixture(scope="session")
def verse1_spans(page2_spans):
    """Verse unit 1 — first verse of the prayer (y0 250–395)."""
    return [s for s in page2_spans if 250 <= s["bbox"][1] <= 395]


@pytest.fixture(scope="session")
def verse2_spans(page2_spans):
    """Verse unit 2 — second verse (y0 400–545)."""
    return [s for s in page2_spans if 400 <= s["bbox"][1] <= 545]


@pytest.fixture(scope="session")
def verse3_spans(page2_spans):
    """Verse unit 3 — third verse (y0 550–700)."""
    return [s for s in page2_spans if 550 <= s["bbox"][1] <= 700]


# ---------------------------------------------------------------------------
# Tests 1–8: extract_tibetan_unicode_text
# ---------------------------------------------------------------------------

def test_tibetan_unicode_verse1_starts_with_prefix(verse1_spans):
    result = extract_tibetan_unicode_text(verse1_spans)
    assert result is not None
    assert result.startswith("༈")


def test_tibetan_unicode_verse1_joins_two_spans(verse1_spans):
    # Verse 1 Tibetan is stored as two separate spans (two half-lines);
    # both must be present in the joined result.
    result = extract_tibetan_unicode_text(verse1_spans)
    assert "རྡོ་རྗེ་འཆང་ཆེན" in result
    assert "མར་པ་མི་ལ་ཆོས་རྗེ" in result


def test_tibetan_unicode_verse2_content(verse2_spans):
    result = extract_tibetan_unicode_text(verse2_spans)
    assert result is not None
    assert "ཀརྨ་པ" in result
    assert "འཛིན་རྣམས" in result


def test_tibetan_unicode_verse3_single_span(verse3_spans):
    # Verse 3 Tibetan is stored as a single span containing both half-lines.
    result = extract_tibetan_unicode_text(verse3_spans)
    assert result is not None
    assert "འབྲི་སྟག་ཚལ་གསུམ" in result


def test_tibetan_unicode_empty_list_returns_none():
    assert extract_tibetan_unicode_text([]) is None


def test_tibetan_unicode_no_tibetan_spans_returns_none():
    spans = [
        {
            "text": "Hello", "font": "TimesNewRomanPSMT",
            "size": 11.0, "bbox": (0, 0, 100, 20),
            "classification": "ROMAN_TEXT",
        }
    ]
    assert extract_tibetan_unicode_text(spans) is None


def test_tibetan_unicode_strips_tabs_and_newlines():
    span = {
        "text": "རྡོ་རྗེ།\t\t\n",
        "font": "MonlamUniOuChan2", "size": 18.0,
        "bbox": (0, 0, 200, 25), "classification": "TIBETAN_UNICODE",
    }
    result = extract_tibetan_unicode_text([span])
    assert result == "རྡོ་རྗེ།"


def test_tibetan_unicode_ignores_roman_spans():
    spans = [
        {
            "text": "Hello", "font": "TimesNewRomanPSMT",
            "size": 11.0, "bbox": (0, 0, 100, 20),
            "classification": "ROMAN_TEXT",
        },
        {
            "text": "རྡོ་རྗེ།",
            "font": "MonlamUniOuChan2", "size": 18.0,
            "bbox": (0, 25, 200, 45), "classification": "TIBETAN_UNICODE",
        },
    ]
    result = extract_tibetan_unicode_text(spans)
    assert result == "རྡོ་རྗེ།"


# ---------------------------------------------------------------------------
# Tests 9–22: extract_roman_text
# ---------------------------------------------------------------------------

def test_roman_text_returns_all_three_keys(verse1_spans):
    result = extract_roman_text(verse1_spans)
    assert set(result.keys()) == {"wylie", "french", "english"}


def test_roman_text_verse1_wylie_content(verse1_spans):
    result = extract_roman_text(verse1_spans)
    assert result["wylie"] is not None
    assert "DOR JE CHANG CHEN" in result["wylie"]
    assert "MAR PA MI LA" in result["wylie"]


def test_roman_text_verse1_wylie_double_space_separator(verse1_spans):
    # The tab separating the two Wylie half-lines must be normalised to
    # a double-space gap, not a single space or a tab character.
    result = extract_roman_text(verse1_spans)
    assert "  " in result["wylie"]
    assert "\t" not in result["wylie"]


def test_roman_text_verse1_french_content(verse1_spans):
    result = extract_roman_text(verse1_spans)
    assert result["french"] is not None
    assert "Grand Vajradhara" in result["french"]
    assert "Milarépa" in result["french"]


def test_roman_text_verse1_english_content(verse1_spans):
    result = extract_roman_text(verse1_spans)
    assert result["english"] is not None
    assert "Great Vajradhara" in result["english"]
    assert "Milarepa" in result["english"]


def test_roman_text_verse2_french_single_span(verse2_spans):
    # Verse 2 French is stored as a single long span (no tab splitting).
    result = extract_roman_text(verse2_spans)
    assert result["french"] is not None
    assert "Omniscient Karmapa" in result["french"]
    assert "Trois Temps" in result["french"]


def test_roman_text_verse2_english_two_spans_joined(verse2_spans):
    result = extract_roman_text(verse2_spans)
    assert result["english"] is not None
    assert "three times" in result["english"]
    assert "Lineage holders" in result["english"]


def test_roman_text_verse3_wylie_content(verse3_spans):
    result = extract_roman_text(verse3_spans)
    assert result["wylie"] is not None
    assert "DRI TAK TSAL" in result["wylie"]
    assert "ZAB LAM CHAK" in result["wylie"]


def test_roman_text_georgia_font_excluded():
    # Georgia = section title; must never appear as wylie/french/english.
    spans = [
        {
            "text": "SECTION TITLE", "font": "Georgia",
            "size": 15.0, "bbox": (0, 0, 200, 25),
            "classification": "ROMAN_TEXT",
        },
        {
            "text": "real english", "font": "TimesNewRomanPSMT",
            "size": 11.0, "bbox": (0, 30, 200, 50),
            "classification": "ROMAN_TEXT",
        },
    ]
    result = extract_roman_text(spans)
    assert result["english"] == "real english"
    assert result["wylie"] is None
    assert result["french"] is None


def test_roman_text_helveticaneue_excluded():
    # HelveticaNeue = page footer; must produce all-None output.
    spans = [
        {
            "text": "Rigpe Dorje Centre - 1", "font": "HelveticaNeue",
            "size": 10.0, "bbox": (0, 756, 612, 770),
            "classification": "ROMAN_TEXT",
        }
    ]
    result = extract_roman_text(spans)
    assert result["wylie"] is None
    assert result["french"] is None
    assert result["english"] is None


def test_roman_text_large_size_excluded():
    # Any Roman span > 13 pt is excluded (spacer in Tibetan font, drop-cap, etc.).
    spans = [
        {
            "text": "LARGE TITLE", "font": "TimesNewRomanPS-BoldMT",
            "size": 14.0, "bbox": (0, 0, 200, 25),
            "classification": "ROMAN_TEXT",
        },
        {
            "text": "real wylie", "font": "TimesNewRomanPS-BoldMT",
            "size": 12.0, "bbox": (0, 30, 200, 50),
            "classification": "ROMAN_TEXT",
        },
    ]
    result = extract_roman_text(spans)
    assert result["wylie"] == "real wylie"


def test_roman_text_wylie_none_when_no_bold():
    spans = [
        {
            "text": "english text", "font": "TimesNewRomanPSMT",
            "size": 11.0, "bbox": (0, 0, 200, 20),
            "classification": "ROMAN_TEXT",
        }
    ]
    result = extract_roman_text(spans)
    assert result["wylie"] is None
    assert result["english"] == "english text"


def test_roman_text_french_none_when_no_italic():
    spans = [
        {
            "text": "wylie text", "font": "TimesNewRomanPS-BoldMT",
            "size": 12.0, "bbox": (0, 0, 200, 20),
            "classification": "ROMAN_TEXT",
        }
    ]
    result = extract_roman_text(spans)
    assert result["french"] is None
    assert result["wylie"] == "wylie text"


def test_roman_text_english_none_when_no_upright():
    spans = [
        {
            "text": "wylie text", "font": "TimesNewRomanPS-BoldMT",
            "size": 12.0, "bbox": (0, 0, 200, 20),
            "classification": "ROMAN_TEXT",
        },
        {
            "text": "french text", "font": "TimesNewRomanPS-ItalicMT",
            "size": 11.0, "bbox": (0, 25, 200, 45),
            "classification": "ROMAN_TEXT",
        },
    ]
    result = extract_roman_text(spans)
    assert result["english"] is None


# ---------------------------------------------------------------------------
# Tests 23–30: split_cjk_lines_by_role
# ---------------------------------------------------------------------------

def test_cjk_sz16_assigned_to_homophonic(verse1_spans):
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse1_spans)
    result = split_cjk_lines_by_role(verse1_spans, wylie_bbox, other_bboxes)
    assert result["mandarin_homophonic"] is not None
    assert "多杰" in result["mandarin_homophonic"]


def test_cjk_sz12_assigned_to_semantic(verse1_spans):
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse1_spans)
    result = split_cjk_lines_by_role(verse1_spans, wylie_bbox, other_bboxes)
    assert result["mandarin_semantic"] is not None
    assert "⾦刚总持" in result["mandarin_semantic"]


def test_cjk_verse1_homophonic_syllables_space_joined(verse1_spans):
    # Homophonic syllable groups must be joined with a single space,
    # matching the visual spacing in the source PDF.
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse1_spans)
    result = split_cjk_lines_by_role(verse1_spans, wylie_bbox, other_bboxes)
    expected = "多杰 羌千 帝洛 那诺倘 玛巴 ⽶拉 却戒 冈波巴"
    assert result["mandarin_homophonic"] == expected


def test_cjk_verse1_semantic_sentences_no_space_joined(verse1_spans):
    # Semantic Chinese sentences span both half-lines; they must be joined
    # without an extra space (Chinese prose does not use inter-sentence spaces).
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse1_spans)
    result = split_cjk_lines_by_role(verse1_spans, wylie_bbox, other_bboxes)
    expected = "⾦刚总持帝洛那洛巴，马巴密勒法王冈波巴，"
    assert result["mandarin_semantic"] == expected


def test_cjk_verse2_both_layers_present(verse2_spans):
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse2_spans)
    result = split_cjk_lines_by_role(verse2_spans, wylie_bbox, other_bboxes)
    assert result["mandarin_homophonic"] is not None
    assert result["mandarin_semantic"] is not None
    assert result["mandarin_homophonic"] != result["mandarin_semantic"]


def test_cjk_ambiguous_empty_for_verse1(verse1_spans):
    # All verse-1 CJK spans are clearly 16 pt or 12 pt; none fall in the
    # ±1 pt ambiguous band around the 14 pt threshold.
    wylie_bbox, other_bboxes = _build_reference_bboxes(verse1_spans)
    result = split_cjk_lines_by_role(verse1_spans, wylie_bbox, other_bboxes)
    assert result["ambiguous"] == []


def test_cjk_homophonic_none_when_no_sz16():
    # Only 12 pt spans present → homophonic must be None.
    spans = [
        {
            "text": "语义翻译", "font": "STSongti-SC-Regular",
            "size": 12.0, "bbox": (0, 0, 100, 20),
            "classification": "CJK_TEXT",
        }
    ]
    result = split_cjk_lines_by_role(spans, None, [])
    assert result["mandarin_homophonic"] is None
    assert result["mandarin_semantic"] == "语义翻译"


def test_cjk_semantic_none_when_no_sz12():
    # Only 16 pt spans present → semantic must be None.
    spans = [
        {
            "text": "音译词", "font": "STSongti-SC-Regular",
            "size": 16.0, "bbox": (0, 0, 100, 20),
            "classification": "CJK_TEXT",
        }
    ]
    result = split_cjk_lines_by_role(spans, None, [])
    assert result["mandarin_homophonic"] == "音译词"
    assert result["mandarin_semantic"] is None


# ---------------------------------------------------------------------------
# Tests 31–32: extract_text_layers_for_verse_unit
# ---------------------------------------------------------------------------

def test_full_extract_verse1_all_seven_keys_present(verse1_spans):
    result = extract_text_layers_for_verse_unit(verse1_spans)
    expected_keys = {
        "tibetan_unicode", "wylie", "french", "english",
        "mandarin_homophonic", "mandarin_semantic", "ambiguous_cjk",
    }
    assert set(result.keys()) == expected_keys


def test_full_extract_verse1_all_layers_non_none_and_ambiguous_empty(verse1_spans):
    result = extract_text_layers_for_verse_unit(verse1_spans)
    assert result["tibetan_unicode"] is not None
    assert result["wylie"] is not None
    assert result["french"] is not None
    assert result["english"] is not None
    assert result["mandarin_homophonic"] is not None
    assert result["mandarin_semantic"] is not None
    assert result["ambiguous_cjk"] == []
