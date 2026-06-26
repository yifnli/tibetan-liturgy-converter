# tests/test_run_pipeline.py
#
# Tests for src/run_pipeline.py — loader and integration smoke tests.

import sys

sys.path.insert(0, "src")

from src.run_pipeline import _load_table


# ── Tests: _load_table ────────────────────────────────────────────────────

def test_load_table_mantra_returns_keyed_dict():
    # The seeded mantra table must be loaded and keyed by the "wylie" field.
    table = _load_table("mantra_syllables_zh.json")
    assert "DOR JE" in table
    assert table["DOR JE"] == {"zh": "多杰", "source": "rigpe-dorje-treasury-of-blessings"}


def test_load_table_missing_file_returns_empty_dict():
    # A nonexistent filename must return {} without raising.
    result = _load_table("nonexistent_file_that_does_not_exist.json")
    assert result == {}
