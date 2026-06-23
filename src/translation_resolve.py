"""
translation_resolve.py

Stage 4 — Translation resolution.

Receives the 8-key verse-result dict produced by verse_pipeline.process_verse_unit
and a set of user-requested translation layers.  For each requested layer,
checks whether a value already exists in the source; if so, carries it
forward unchanged; if not, emits a gap record for human-reviewed generation.

Scope and deliberate non-scope
-------------------------------
"Present" means the layer's value in the 8-key dict is not None.
Empty strings, whitespace-only strings, and extraction artefacts (e.g. the
Medicine Buddha source's French field, which may contain mis-classified text
such as 'G reat Vajradhara, …' due to ambiguous bold-style role assignment)
are treated as present by this module.  Content-quality validation is
Stage 3's responsibility.  Stage 4 never attempts artefact detection or
heuristic filtering of extracted strings — doing so here would create a
hidden dependency on Stage 3 internals and make Stage 4 logic fragile.

This module does NOT call any LLM.  It only routes:
  - Present layers  → value passes through into the returned dict
  - Absent layers   → a structured gap record is added to the gaps list

The assembly stage (Stage 6) treats every gap record as a placeholder.
A human-review step (external to this module) consumes the gaps list,
fills in generated translations, then calls apply_translation() (Stage 6
input builder) to merge them back before final assembly.
"""

_VALID_TRANSLATION_LAYERS = frozenset({"english", "french", "mandarin_semantic"})
_SOURCE_PRIORITY = ["english", "french", "mandarin_semantic"]


# ── Function 1 ─────────────────────────────────────────────────────────────

def _resolve_source(verse_result: dict) -> str | None:
    """Return the key of the first non-None semantic layer, in priority order.

    Priority: english → french → mandarin_semantic.
    Returns None if all three are absent (None).

    This value is used as the ``source`` field in gap records: it identifies
    which existing layer a human (or downstream generation step) should
    derive the missing translation from.
    """
    for key in _SOURCE_PRIORITY:
        if verse_result.get(key) is not None:
            return key
    return None


# ── Function 2 ─────────────────────────────────────────────────────────────

def _make_gap_record(layer: str, source: str | None, verse_unit: dict) -> dict:
    """Construct one gap record for a requested layer that is absent.

    Parameters
    ----------
    layer:
        The name of the absent requested layer (e.g. ``"mandarin_semantic"``).
    source:
        The key of the best available source layer from which a translation
        can be derived (as returned by ``_resolve_source``), or ``None`` if
        no source layer is available at all.
    verse_unit:
        The verse-unit dict from layout_segment.segment_page_spans.  Must
        contain ``"page_index"`` (int) and ``"verse_index"`` (int).

    Returns
    -------
    dict with exactly four keys:
      layer      — the absent layer name
      source     — source layer key, or None
      verse_ref  — {"page_index": int, "verse_index": int}
      status     — "needs_generation" if source is not None,
                   "no_source_available" if source is None
    """
    return {
        "layer":     layer,
        "source":    source,
        "verse_ref": {
            "page_index":  verse_unit["page_index"],
            "verse_index": verse_unit["verse_index"],
        },
        "status": "needs_generation" if source is not None else "no_source_available",
    }


# ── Function 3 ─────────────────────────────────────────────────────────────

def resolve_translation_layers(
    verse_result: dict,
    verse_unit: dict,
    requested_layers: set,
) -> dict:
    """Route each requested translation layer to either a value or a gap record.

    Parameters
    ----------
    verse_result:
        The 8-key dict returned by verse_pipeline.process_verse_unit.
    verse_unit:
        The verse-unit dict from layout_segment.segment_page_spans (provides
        page_index and verse_index for gap records).
    requested_layers:
        A set of layer names the user wants in the output.  Valid values:
        "english", "french", "mandarin_semantic".  An empty set is valid
        and returns {layers: {}, gaps: []}.

    Returns
    -------
    dict with two keys:
      "layers" — dict mapping each requested layer name to its value
                 (the extracted string if present, or None if absent)
      "gaps"   — list of gap records (one per absent requested layer)

    Raises
    ------
    ValueError if any element of requested_layers is not a valid layer name.

    Notes
    -----
    The input dicts are never mutated.  The returned dict is a fresh object.
    """
    unknown = requested_layers - _VALID_TRANSLATION_LAYERS
    if unknown:
        raise ValueError(
            f"Invalid layer name(s) in requested_layers: {unknown!r}. "
            f"Valid values: {sorted(_VALID_TRANSLATION_LAYERS)}"
        )

    source = _resolve_source(verse_result)
    layers = {}
    gaps = []

    for layer in requested_layers:
        value = verse_result.get(layer)
        layers[layer] = value
        if value is None:
            gaps.append(_make_gap_record(layer, source, verse_unit))

    return {"layers": layers, "gaps": gaps}
