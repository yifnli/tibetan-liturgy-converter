# tests/test_translation_resolve.py
#
# Tests for src/translation_resolve.py — Stage 4 translation resolution.
# Tests added cumulatively, one function at a time.

import sys
import pytest

sys.path.insert(0, "src")

from src.translation_resolve import (
    _resolve_source,
    _make_gap_record,
    resolve_translation_layers,
)

# ── Shared fixtures built from live data (explore_stage4_inputs.py output) ──
#
# String values copied verbatim — do not retype from memory.

# Case 1: Rigpe Dorje page 2 verse 0 — all translation layers present
_CASE1 = {
    "tibetan_unicode":     "༈ རྡོ་རྗེ་འཆང་ཆེན་ཏཻ་ལོ་ནཱ་རོ་དང༌། །མར་པ་མི་ལ་ཆོས་རྗེ་སྒམ་པོ་པ། །",
    "tibetan_image_paths": [],
    "wylie":               "DOR JE CHANG CHEN TI LO NA RO DANG  MAR PA MI LA CHÖ JE GAM PO PA",
    "french":              "Grand Vajradhara, Tilopa, Naropa, Marpa, Milarépa, Seigneur-du-Dharma Gampopa,",
    "english":             "Great Vajradhara, Tilopa, Naropa, Marpa, Milarepa, Lord of Dharma Gampopa,",
    "mandarin_homophonic": "多杰 羌千 帝洛 那诺倘 玛巴 ⽶拉 却戒 冈波巴",
    "mandarin_semantic":   "⾦刚总持帝洛那洛巴，马巴密勒法王冈波巴，",
    "ambiguous_cjk":       [],
}

# Case 2: Same verse, mandarin_homophonic and mandarin_semantic forced to None
_CASE2 = {**_CASE1, "mandarin_homophonic": None, "mandarin_semantic": None}

# Case 3: Medicine Buddha page 1 verse 0 — LEGACY_FONT_TEXT, no CJK
# french value is a real extraction artefact — left as-is per Stage 4 scope
_CASE3 = {
    "tibetan_unicode":     None,
    "tibetan_image_paths": ["line000.png"],  # path normalised for test portability
    "wylie":               "DOR JE CHANG CHEN TE LO NA RO DANG",
    "french":              "G reat Vajradhara, Tilopa, Naropa,",
    "english":             "Grand Vajradhara, Tilopa, Naropa",
    "mandarin_homophonic": None,
    "mandarin_semantic":   None,
    "ambiguous_cjk":       [],
}

# Synthetic cases
_ALL_NONE = {
    "tibetan_unicode": None, "tibetan_image_paths": [],
    "wylie": None, "french": None, "english": None,
    "mandarin_homophonic": None, "mandarin_semantic": None, "ambiguous_cjk": [],
}
_ENGLISH_NONE_FRENCH_PRESENT = {**_ALL_NONE, "french": "some French text"}


# ── Tests 1–5: _resolve_source ────────────────────────────────────────────

def test_resolve_source_case1_all_present_returns_english():
    # When all three are present, english wins (highest priority).
    assert _resolve_source(_CASE1) == "english"


def test_resolve_source_case2_english_french_present_mandarin_semantic_none():
    # english and french present, mandarin_semantic None → still "english".
    assert _resolve_source(_CASE2) == "english"


def test_resolve_source_case3_mb_english_present():
    # english is present (even though french has an artefact value, both are
    # non-None); english wins by priority order.
    assert _resolve_source(_CASE3) == "english"


def test_resolve_source_english_none_french_present_returns_french():
    assert _resolve_source(_ENGLISH_NONE_FRENCH_PRESENT) == "french"


def test_resolve_source_all_three_none_returns_none():
    assert _resolve_source(_ALL_NONE) is None


# ── Tests 6–10: _make_gap_record ──────────────────────────────────────────

_VERSE_UNIT_RD = {"page_index": 2, "verse_index": 0, "spans": []}
_VERSE_UNIT_MB = {"page_index": 1, "verse_index": 0, "spans": []}


def test_gap_record_has_exactly_four_keys():
    record = _make_gap_record("mandarin_semantic", "english", _VERSE_UNIT_RD)
    assert set(record.keys()) == {"layer", "source", "verse_ref", "status"}


def test_gap_record_verse_ref_matches_verse_unit():
    record = _make_gap_record("mandarin_semantic", "english", _VERSE_UNIT_MB)
    assert record["verse_ref"] == {"page_index": 1, "verse_index": 0}


def test_gap_record_status_needs_generation_when_source_present():
    record = _make_gap_record("french", "english", _VERSE_UNIT_RD)
    assert record["status"] == "needs_generation"


def test_gap_record_status_no_source_available_when_source_none():
    record = _make_gap_record("english", None, _VERSE_UNIT_RD)
    assert record["status"] == "no_source_available"


def test_gap_record_layer_and_source_passed_through_exactly():
    record = _make_gap_record("french", "mandarin_semantic", _VERSE_UNIT_MB)
    assert record["layer"] == "french"
    assert record["source"] == "mandarin_semantic"


# ── Tests 11–18: resolve_translation_layers ─────────────────────────────

def test_resolve_case1_all_requested_no_gaps():
    # Case 1: all three translation layers present → gaps == [], all values non-None.
    result = resolve_translation_layers(
        _CASE1, _VERSE_UNIT_RD, {"english", "french", "mandarin_semantic"}
    )
    assert result["gaps"] == []
    assert result["layers"]["english"] is not None
    assert result["layers"]["french"] is not None
    assert result["layers"]["mandarin_semantic"] is not None


def test_resolve_case2_mandarin_semantic_absent_produces_one_gap():
    # Case 2: mandarin_semantic is None → exactly one gap record.
    result = resolve_translation_layers(
        _CASE2, _VERSE_UNIT_RD, {"english", "french", "mandarin_semantic"}
    )
    assert len(result["gaps"]) == 1
    gap = result["gaps"][0]
    assert gap["layer"] == "mandarin_semantic"
    assert gap["source"] == "english"
    assert gap["status"] == "needs_generation"


def test_resolve_single_layer_requested():
    # Only 'english' requested → only that key in layers, no gaps.
    result = resolve_translation_layers(_CASE1, _VERSE_UNIT_RD, {"english"})
    assert set(result["layers"].keys()) == {"english"}
    assert result["gaps"] == []


def test_resolve_empty_requested_layers():
    result = resolve_translation_layers(_CASE1, _VERSE_UNIT_RD, set())
    assert result["layers"] == {}
    assert result["gaps"] == []


def test_resolve_all_none_both_gaps_have_no_source():
    result = resolve_translation_layers(
        _ALL_NONE, _VERSE_UNIT_RD, {"english", "french"}
    )
    assert len(result["gaps"]) == 2
    for gap in result["gaps"]:
        assert gap["source"] is None
        assert gap["status"] == "no_source_available"


def test_resolve_invalid_layer_raises_value_error():
    with pytest.raises(ValueError, match="Invalid layer name"):
        resolve_translation_layers(_CASE1, _VERSE_UNIT_RD, {"invalid_layer"})


def test_resolve_does_not_mutate_input_verse_result():
    import copy
    original = copy.deepcopy(_CASE2)
    resolve_translation_layers(_CASE2, _VERSE_UNIT_RD, {"english", "french", "mandarin_semantic"})
    assert _CASE2 == original


def test_resolve_case1_layers_values_match_live_data():
    # Values must exactly match the live extraction output from Case 1.
    result = resolve_translation_layers(
        _CASE1, _VERSE_UNIT_RD, {"english", "french", "mandarin_semantic"}
    )
    assert result["layers"]["english"] == (
        "Great Vajradhara, Tilopa, Naropa, Marpa, Milarepa, Lord of Dharma Gampopa,"
    )
    assert result["layers"]["french"] == (
        "Grand Vajradhara, Tilopa, Naropa, Marpa, Milarépa, Seigneur-du-Dharma Gampopa,"
    )
    assert result["layers"]["mandarin_semantic"] == "⾦刚总持帝洛那洛巴，马巴密勒法王冈波巴，"
