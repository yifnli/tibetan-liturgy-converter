# tests/test_homophonic_resolve.py
#
# Tests for src/homophonic_resolve.py — Stage 5 homophonic resolution.
# Tests added cumulatively, one function at a time.

import sys
import pytest

sys.path.insert(0, "src")

from src.homophonic_resolve import (
    _tokenize_wylie,
    _lookup_wylie_tokens,
    _apply_both_tables,
    resolve_homophonic_layers,
)

# ── Shared live-data constants (exact strings from explore_stage5_inputs.py) ──

# Case 1 wylie (Rigpe Dorje) — contains double-space between hemistichs
_WYLIE_RD = "DOR JE CHANG CHEN TI LO NA RO DANG  MAR PA MI LA CHÖ JE GAM PO PA"

# Case 3 wylie (Medicine Buddha) — no double-space
_WYLIE_MB = "DOR JE CHANG CHEN TE LO NA RO DANG"

# Expected assembled Mandarin homophonic (live data, do not reconstruct)
_HOMOPHONIC_RD = "多杰 羌千 帝洛 那诺倘 玛巴 ⽶拉 却戒 冈波巴"

# Synthetic lookup table — covers all 18 tokens of _WYLIE_RD exactly
# Chinese characters copied verbatim from live data / user spec.
SYNTHETIC_TABLE = {
    "DOR JE":     {"zh": "多杰",   "source": "test"},
    "CHANG CHEN": {"zh": "羌千",   "source": "test"},
    "TI LO":      {"zh": "帝洛",   "source": "test"},
    "NA RO DANG": {"zh": "那诺倘", "source": "test"},
    "MAR PA":     {"zh": "玛巴",   "source": "test"},
    "MI LA":      {"zh": "⽶拉",   "source": "test"},
    "CHÖ JE":     {"zh": "却戒",   "source": "test"},
    "GAM PO PA":  {"zh": "冈波巴", "source": "test"},
}


# ── Tests 1–4: _tokenize_wylie ────────────────────────────────────────────

def test_tokenize_wylie_rd_produces_18_tokens_no_empty():
    # Ground truth: RD wylie has a double-space that must collapse to one space.
    tokens = _tokenize_wylie(_WYLIE_RD)
    assert tokens == [
        "DOR", "JE", "CHANG", "CHEN", "TI", "LO", "NA", "RO", "DANG",
        "MAR", "PA", "MI", "LA", "CHÖ", "JE", "GAM", "PO", "PA",
    ]
    assert len(tokens) == 18
    assert "" not in tokens


def test_tokenize_wylie_mb_produces_9_tokens():
    # MB wylie has no double-space; must produce 9 clean tokens.
    tokens = _tokenize_wylie(_WYLIE_MB)
    assert tokens == ["DOR", "JE", "CHANG", "CHEN", "TE", "LO", "NA", "RO", "DANG"]
    assert len(tokens) == 9


def test_tokenize_wylie_empty_string_returns_empty_list():
    assert _tokenize_wylie("") == []


def test_tokenize_wylie_whitespace_only_returns_empty_list():
    assert _tokenize_wylie("   ") == []


# ── Tests 5–8: _lookup_wylie_tokens ──────────────────────────────────────────

def test_lookup_wylie_tokens_full_rd_verse_all_found():
    # All 18 tokens from the RD Wylie string must resolve to 8 "found" tuples
    # whose zh values match the live mandarin_homophonic exactly.
    tokens = _tokenize_wylie(_WYLIE_RD)
    result = _lookup_wylie_tokens(tokens, SYNTHETIC_TABLE)
    assert len(result) == 8
    assert all(status == "found" for _, status in result)
    assembled = " ".join(zh for zh, _ in result)
    assert assembled == _HOMOPHONIC_RD


def test_lookup_wylie_tokens_novel_token_not_in_table():
    # A token absent from the table must produce (token, "novel").
    result = _lookup_wylie_tokens(["UNKNOWN"], SYNTHETIC_TABLE)
    assert result == [("UNKNOWN", "novel")]


def test_lookup_wylie_tokens_longest_match_wins_over_shorter():
    # If table has both "DOR" and "DOR JE", the 2-token key must win.
    overlap_table = {
        "DOR":    {"zh": "short_match", "source": "test"},
        "DOR JE": {"zh": "long_match",  "source": "test"},
    }
    result = _lookup_wylie_tokens(["DOR", "JE", "EXTRA"], overlap_table)
    assert result[0] == ("long_match", "found")
    assert result[1] == ("EXTRA", "novel")


def test_lookup_wylie_tokens_empty_tokens_returns_empty():
    assert _lookup_wylie_tokens([], SYNTHETIC_TABLE) == []


# ── Tests 9–13: _apply_both_tables ────────────────────────────────────────────

_MANTRA_ONLY  = {"DOR JE":    {"zh": "多杰",            "source": "test"}}
_LITUR_ONLY   = {"GAM PO PA": {"zh": "冈波巴",          "source": "test"}}
_MANTRA_CLASH = {"DOR JE":    {"zh": "mantra_version",  "source": "test"}}
_LITUR_CLASH  = {"DOR JE":    {"zh": "liturgical_ver",  "source": "test"}}


def test_apply_both_token_in_mantra_only():
    result = _apply_both_tables(["DOR", "JE"], _MANTRA_ONLY, {})
    assert result == [("多杰", "found")]


def test_apply_both_token_in_liturgical_only():
    result = _apply_both_tables(["GAM", "PO", "PA"], {}, _LITUR_ONLY)
    assert result == [("冈波巴", "found")]


def test_apply_both_mantra_wins_over_liturgical_for_same_key():
    # Same key in both tables: layer 1 (mantra) must win.
    result = _apply_both_tables(["DOR", "JE"], _MANTRA_CLASH, _LITUR_CLASH)
    assert result == [("mantra_version", "found")]


def test_apply_both_token_in_neither_table_is_novel():
    result = _apply_both_tables(["UNKNOWN"], {}, {})
    assert result == [("UNKNOWN", "novel")]


def test_apply_both_empty_tables_all_tokens_novel():
    result = _apply_both_tables(["DOR", "JE", "CHANG"], {}, {})
    assert all(status == "novel" for _, status in result)
    assert len(result) == 3


# ── Tests 14–23: resolve_homophonic_layers ─────────────────────────────────

# Verse-unit dicts supplying page_index / verse_index for gap records
_VU_RD = {"page_index": 2, "verse_index": 0, "spans": []}
_VU_MB = {"page_index": 1, "verse_index": 0, "spans": []}

# 8-key verse-result dicts (copied from live pipeline output)
_CASE1 = {
    "tibetan_unicode":     "༈ རྡོ་རྗེ་འཅང་ཅེན་ཏཀྵ་ལོ་ནཱ་རོ་དང༌། །མར་པ་མི་ལ་ཅོས་རྗེ་སགམ་པོ་པ། །",
    "tibetan_image_paths": [],
    "wylie":               _WYLIE_RD,
    "french":              "Grand Vajradhara, Tilopa, Naropa, Marpa, Milarépa, Seigneur-du-Dharma Gampopa,",
    "english":             "Great Vajradhara, Tilopa, Naropa, Marpa, Milarepa, Lord of Dharma Gampopa,",
    "mandarin_homophonic": _HOMOPHONIC_RD,
    "mandarin_semantic":   "⾦刚总持帝洛那洛巴，马巴密勒法王冈波巴，",
    "ambiguous_cjk":       [],
}
# Case 2: same but both mandarin fields forced to None
_CASE2 = {**_CASE1, "mandarin_homophonic": None, "mandarin_semantic": None}
# Case 3: MB — wylie present, mandarin_homophonic absent
_CASE3 = {
    "tibetan_unicode":     None,
    "tibetan_image_paths": ["line000.png"],
    "wylie":               _WYLIE_MB,
    "french":              "G reat Vajradhara, Tilopa, Naropa,",
    "english":             "Grand Vajradhara, Tilopa, Naropa",
    "mandarin_homophonic": None,
    "mandarin_semantic":   None,
    "ambiguous_cjk":       [],
}


def test_resolve_homophonic_case1_present_passthrough():
    # mandarin_homophonic already in source → pass-through, no gap.
    result = resolve_homophonic_layers(
        _CASE1, _VU_RD, {"mandarin_homophonic"}, SYNTHETIC_TABLE, {}
    )
    assert result["gaps"] == []
    assert result["layers"]["mandarin_homophonic"] == _HOMOPHONIC_RD


def test_resolve_homophonic_case2_assembles_from_wylie():
    # mandarin_homophonic None but wylie present + all tokens in SYNTHETIC_TABLE
    # → gaps == [], assembled zh must match the live homophonic string exactly.
    result = resolve_homophonic_layers(
        _CASE2, _VU_RD, {"mandarin_homophonic"}, SYNTHETIC_TABLE, {}
    )
    assert result["gaps"] == []
    assert result["layers"]["mandarin_homophonic"] == _HOMOPHONIC_RD


def test_resolve_homophonic_novel_token_produces_novel_gap():
    # wylie containing an unrecognised token → gap with status="novel_needs_review".
    novel_verse = {**_CASE2, "wylie": "DOR JE UNRECOGNISED_SYLLABLE"}
    result = resolve_homophonic_layers(
        novel_verse, _VU_RD, {"mandarin_homophonic"}, SYNTHETIC_TABLE, {}
    )
    assert len(result["gaps"]) == 1
    gap = result["gaps"][0]
    assert gap["layer"] == "mandarin_homophonic"
    assert gap["source"] == "wylie"
    assert gap["status"] == "novel_needs_review"
    assert gap["unresolved_tokens"] == ["UNRECOGNISED_SYLLABLE"]


def test_resolve_homophonic_wylie_none_mandarin_none_no_source_gap():
    # Both wylie and mandarin_homophonic absent → gap with source=None.
    no_wylie = {**_CASE2, "wylie": None}
    result = resolve_homophonic_layers(
        no_wylie, _VU_RD, {"mandarin_homophonic"}, SYNTHETIC_TABLE, {}
    )
    assert len(result["gaps"]) == 1
    gap = result["gaps"][0]
    assert gap["source"] is None
    assert gap["status"] == "no_source_available"


def test_resolve_homophonic_wylie_passthrough_when_none():
    # Requesting "wylie" when wylie is None → layers["wylie"]=None, gaps==[]
    no_wylie = {**_CASE2, "wylie": None}
    result = resolve_homophonic_layers(
        no_wylie, _VU_RD, {"wylie"}, SYNTHETIC_TABLE, {}
    )
    assert result["layers"]["wylie"] is None
    assert result["gaps"] == []


def test_resolve_homophonic_wylie_passthrough_when_present():
    result = resolve_homophonic_layers(
        _CASE1, _VU_RD, {"wylie"}, SYNTHETIC_TABLE, {}
    )
    assert result["layers"]["wylie"] == _WYLIE_RD
    assert result["gaps"] == []


def test_resolve_homophonic_empty_requested_layers():
    result = resolve_homophonic_layers(_CASE1, _VU_RD, set(), SYNTHETIC_TABLE, {})
    assert result == {"layers": {}, "gaps": []}


def test_resolve_homophonic_invalid_layer_raises_value_error():
    with pytest.raises(ValueError, match="Invalid layer name"):
        resolve_homophonic_layers(_CASE1, _VU_RD, {"invalid"}, SYNTHETIC_TABLE, {})


def test_resolve_homophonic_does_not_mutate_input():
    import copy
    original = copy.deepcopy(_CASE2)
    resolve_homophonic_layers(_CASE2, _VU_RD, {"mandarin_homophonic"}, SYNTHETIC_TABLE, {})
    assert _CASE2 == original


def test_resolve_homophonic_gap_verse_ref_correct():
    novel_verse = {**_CASE2, "wylie": "NOVEL_TOKEN"}
    result = resolve_homophonic_layers(
        novel_verse, _VU_MB, {"mandarin_homophonic"}, {}, {}
    )
    assert result["gaps"][0]["verse_ref"] == {"page_index": 1, "verse_index": 0}
    assert result["gaps"][0]["unresolved_tokens"] == ["NOVEL_TOKEN"]
