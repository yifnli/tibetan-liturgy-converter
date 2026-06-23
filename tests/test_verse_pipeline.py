# tests/test_verse_pipeline.py
#
# Tests for src/verse_pipeline.py — per-verse-unit orchestrator.
# Tests are added cumulatively: Function 1 tests added first,
# Function 2 tests added only after Function 1 passes.

import sys
import pytest
import fitz

sys.path.insert(0, "src")

from src.format_detect import classify_document
from src.layout_segment import segment_page_spans
from src.verse_pipeline import _extract_legacy_verse, process_verse_unit

_RD_PDF = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"

_EXPECTED_8_KEYS = frozenset({
    "tibetan_unicode", "tibetan_image_paths",
    "wylie", "french", "english",
    "mandarin_homophonic", "mandarin_semantic", "ambiguous_cjk",
})


# ── Session-scoped fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def mb_verse_pipeline_data():
    """Returns (vu0_spans, fitz_doc) for Medicine Buddha page 1 verse-unit 0."""
    doc = classify_document(_MB_PDF)
    assert doc["format"] == "LEGACY_FONT_TEXT"
    spans = doc["pages"][1]["spans"]
    verses = segment_page_spans(spans, page_index=1)
    vu0 = verses[0]
    pdf_doc = fitz.open(_MB_PDF)
    yield vu0, pdf_doc
    pdf_doc.close()


# ── Tests 1–7: _extract_legacy_verse ─────────────────────────────────────

def test_legacy_verse_produces_one_image_for_mb_vu0(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert len(result["tibetan_image_paths"]) == 1


def test_legacy_verse_image_file_exists_on_disk(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert len(result["tibetan_image_paths"]) == 1
    import os
    assert os.path.isfile(result["tibetan_image_paths"][0])


def test_legacy_verse_wylie_ground_truth(mb_verse_pipeline_data, tmp_path):
    # Ground-truth from live extraction (explore_next_stage.py).
    # Do NOT adjust this value if the test fails — diagnose instead.
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert "DOR JE CHANG CHEN TE LO NA RO DANG" in result["wylie"]


def test_legacy_verse_tibetan_unicode_is_none(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert result["tibetan_unicode"] is None


def test_legacy_verse_mandarin_fields_are_none(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert result["mandarin_homophonic"] is None
    assert result["mandarin_semantic"] is None


def test_legacy_verse_ambiguous_cjk_is_empty_list(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert result["ambiguous_cjk"] == []


def test_legacy_verse_all_8_keys_present(mb_verse_pipeline_data, tmp_path):
    vu0, pdf_doc = mb_verse_pipeline_data
    result = _extract_legacy_verse(vu0["spans"], pdf_doc, vu0["page_index"], tmp_path)
    assert set(result.keys()) == _EXPECTED_8_KEYS


# ── Session-scoped fixtures for process_verse_unit ───────────────────────

@pytest.fixture(scope="session")
def rd_process_data():
    """Returns (verse_unit_0, doc_format, fitz_doc) for Rigpe Dorje page 2."""
    doc = classify_document(_RD_PDF)
    assert doc["format"] == "UNICODE_TEXT"
    spans = doc["pages"][2]["spans"]
    verses = segment_page_spans(spans, page_index=2)
    pdf_doc = fitz.open(_RD_PDF)
    yield verses[0], doc["format"], pdf_doc
    pdf_doc.close()


@pytest.fixture(scope="session")
def mb_process_data():
    """Returns (verse_unit_0, doc_format, fitz_doc) for Medicine Buddha page 1."""
    doc = classify_document(_MB_PDF)
    assert doc["format"] == "LEGACY_FONT_TEXT"
    spans = doc["pages"][1]["spans"]
    verses = segment_page_spans(spans, page_index=1)
    pdf_doc = fitz.open(_MB_PDF)
    yield verses[0], doc["format"], pdf_doc
    pdf_doc.close()


# ── Tests 8–17: process_verse_unit ───────────────────────────────────────

def test_process_rd_tibetan_unicode_starts_with_expected(rd_process_data, tmp_path):
    vu0, doc_format, pdf_doc = rd_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert result["tibetan_unicode"] is not None
    assert result["tibetan_unicode"].startswith("༈ རྡོ་རྗེ་འཆང་ཆེན་")


def test_process_rd_tibetan_image_paths_is_empty(rd_process_data, tmp_path):
    # Contract: UNICODE_TEXT path always returns tibetan_image_paths == [].
    vu0, doc_format, pdf_doc = rd_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert result["tibetan_image_paths"] == []


def test_process_rd_wylie_contains_expected(rd_process_data, tmp_path):
    vu0, doc_format, pdf_doc = rd_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert "DOR JE CHANG CHEN" in result["wylie"]


def test_process_rd_all_8_keys_present(rd_process_data, tmp_path):
    vu0, doc_format, pdf_doc = rd_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert set(result.keys()) == _EXPECTED_8_KEYS


def test_process_mb_tibetan_unicode_is_none(mb_process_data, tmp_path):
    # Contract: LEGACY_FONT_TEXT path always returns tibetan_unicode == None.
    vu0, doc_format, pdf_doc = mb_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert result["tibetan_unicode"] is None


def test_process_mb_one_image_path_produced(mb_process_data, tmp_path):
    vu0, doc_format, pdf_doc = mb_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert len(result["tibetan_image_paths"]) == 1


def test_process_mb_image_path_exists_on_disk(mb_process_data, tmp_path):
    vu0, doc_format, pdf_doc = mb_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    import os
    assert os.path.isfile(result["tibetan_image_paths"][0])


def test_process_mb_all_8_keys_present(mb_process_data, tmp_path):
    vu0, doc_format, pdf_doc = mb_process_data
    result = process_verse_unit(vu0, doc_format, pdf_doc, tmp_path)
    assert set(result.keys()) == _EXPECTED_8_KEYS


def test_process_both_paths_image_paths_is_list(rd_process_data, mb_process_data, tmp_path):
    # Adjustment 2: tibetan_image_paths is always a list on both paths.
    vu_rd, fmt_rd, pdf_rd = rd_process_data
    vu_mb, fmt_mb, pdf_mb = mb_process_data
    res_rd = process_verse_unit(vu_rd, fmt_rd, pdf_rd, tmp_path)
    res_mb = process_verse_unit(vu_mb, fmt_mb, pdf_mb, tmp_path)
    assert isinstance(res_rd["tibetan_image_paths"], list)
    assert isinstance(res_mb["tibetan_image_paths"], list)


def test_process_both_paths_ambiguous_cjk_is_list(rd_process_data, mb_process_data, tmp_path):
    vu_rd, fmt_rd, pdf_rd = rd_process_data
    vu_mb, fmt_mb, pdf_mb = mb_process_data
    res_rd = process_verse_unit(vu_rd, fmt_rd, pdf_rd, tmp_path)
    res_mb = process_verse_unit(vu_mb, fmt_mb, pdf_mb, tmp_path)
    assert isinstance(res_rd["ambiguous_cjk"], list)
    assert isinstance(res_mb["ambiguous_cjk"], list)


def test_process_unknown_format_raises_value_error(rd_process_data, tmp_path):
    vu0, _, pdf_doc = rd_process_data
    with pytest.raises(ValueError, match="Unrecognised doc_format"):
        process_verse_unit(vu0, "PECHA_IMAGE", pdf_doc, tmp_path)
