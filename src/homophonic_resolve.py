"""
homophonic_resolve.py

Stage 5 — Homophonic transliteration resolution.

Receives the 8-key verse-result dict from verse_pipeline.process_verse_unit
and a set of user-requested homophonic layers.  For each requested layer,
checks whether a value already exists; if so, carries it forward unchanged;
if not, either assembles it from the Wylie string via lookup-table scan, or
emits a gap record.

Valid requested_layers values: "wylie", "mandarin_homophonic".

Output shape is identical to resolve_translation_layers:
  {"layers": dict, "gaps": list[dict]}

Gap record shape:
  {
    "layer":     str,
    "source":    str | None,
    "verse_ref": {"page_index": int, "verse_index": int},
    "status":    "needs_generation" | "no_source_available" | "novel_needs_review",
    # only present when status == "novel_needs_review":
    "unresolved_tokens": list[str],
  }

For all other statuses the dict has four keys (identical to Stage 4).

Three valid status values (Stage 4 + Stage 5 combined):
  "needs_generation"    — a source text exists; an LLM or translator can derive the layer
  "no_source_available" — no source text exists to derive from
  "novel_needs_review"  — lookup found unrecognised Wylie syllables; a qualified
                          human must author the phonetic mapping from scratch

Scope and deliberate non-scope
-------------------------------
"Wylie" layer: always passes through as-is (None or the extracted string).
There is no Wylie generation path — if wylie is None and mandarin_homophonic
is also None, the gap record for mandarin_homophonic carries source=None,
status="no_source_available" (nothing to look up).

Lookup tables are passed as parameters (dict[str, dict]) — no file I/O
occurs in this module.  The JSON files in data/ are loaded by the caller.
Each table entry must have at least {"zh": str, "source": str}.

Lookup algorithm: longest-match left-to-right scan.  Table keys are
space-separated multi-syllable Wylie phrases (e.g. "DOR JE", "GAM PO PA").
Layer 1 (mantra_table) is tried first; layer 2 (liturgical_table) is tried
if no layer-1 match is found at that position.  A position with no match in
either table produces a ("TOKEN", "novel") tuple, which triggers a
"novel_needs_review" gap record rather than a silent assembly.

PyMuPDF tab-normalisation produces double-space separators inside Wylie
strings.  _tokenize_wylie() normalises these to single spaces before
splitting, so no empty tokens appear in the token list.
"""

_VALID_HOMOPHONIC_LAYERS = frozenset({"wylie", "mandarin_homophonic"})

_VALID_STATUSES = frozenset({
    "needs_generation",
    "no_source_available",
    "novel_needs_review",
})


# ── Internal gap-record builder ────────────────────────────────────────────

def _make_gap_record(
    layer: str,
    source: str | None,
    verse_unit: dict,
    status: str,
) -> dict:
    """Build a gap record with an explicitly supplied status.

    Status must be one of the three valid values defined in the module
    docstring.  This function is internal; callers are responsible for
    supplying the correct status value.

    Output shape is identical to translation_resolve._make_gap_record
    (same four keys: layer, source, verse_ref, status).
    """
    return {
        "layer":     layer,
        "source":    source,
        "verse_ref": {
            "page_index":  verse_unit["page_index"],
            "verse_index": verse_unit["verse_index"],
        },
        "status": status,
    }


# ── Function 1 ─────────────────────────────────────────────────────────────

def _tokenize_wylie(wylie: str) -> list[str]:
    """Normalise and tokenize a Wylie transliteration string.

    PyMuPDF replaces tab characters with a double-space during text
    extraction.  This appears inside Wylie strings as a double-space
    separator between phrases (e.g. between the two hemistichs of a verse
    line).  Normalising double-space to single space before splitting
    ensures no empty token is produced in the middle of the token list.

    Returns a list of non-empty token strings.  Casing is not altered —
    Wylie strings extracted from source PDFs are already uppercase.
    """
    normalized = wylie.replace("  ", " ")
    return [t for t in normalized.split(" ") if t]


# ── Function 2 ─────────────────────────────────────────────────────────────

def _lookup_wylie_tokens(
    tokens: list[str],
    table: dict,
) -> list[tuple[str, str]]:
    """Longest-match left-to-right scan of tokens against a single table.

    At each position the longest key whose token sequence matches the
    remaining tokens is chosen first (greedy longest-match).  A position
    with no match consumes one token and yields ``(token, "novel")``.

    Parameters
    ----------
    tokens:
        List of Wylie tokens from ``_tokenize_wylie``.
    table:
        Lookup dict mapping space-separated Wylie phrases to entry dicts.
        Each entry must have at least ``{"zh": str, "source": str}``.

    Returns
    -------
    List of ``(zh_or_token, status)`` tuples where status is ``"found"``
    for matched entries or ``"novel"`` for unmatched single tokens.
    """
    if not tokens:
        return []

    # Pre-sort: entries with the most tokens first to guarantee longest-match.
    sorted_entries = sorted(
        table.items(),
        key=lambda item: len(item[0].split()),
        reverse=True,
    )

    results = []
    i = 0
    while i < len(tokens):
        matched = False
        for key, entry in sorted_entries:
            key_tokens = key.split()
            n = len(key_tokens)
            if tokens[i:i + n] == key_tokens:
                results.append((entry["zh"], "found"))
                i += n
                matched = True
                break
        if not matched:
            results.append((tokens[i], "novel"))
            i += 1

    return results


# ── Function 3 ─────────────────────────────────────────────────────────────

def _apply_both_tables(
    tokens: list[str],
    mantra_table: dict,
    liturgical_table: dict,
) -> list[tuple[str, str]]:
    """Longest-match scan using layer 1 then layer 2 per position.

    For each token position:
      1. Try longest match in mantra_table (layer 1).
      2. If no match, try longest match in liturgical_table (layer 2).
      3. If still no match, emit ``(token, "novel")`` and advance by 1.

    A match in layer 1 is never re-tried against layer 2.

    Parameters and return value are the same as ``_lookup_wylie_tokens``.
    """
    if not tokens:
        return []

    sorted_mantra = sorted(
        mantra_table.items(),
        key=lambda item: len(item[0].split()),
        reverse=True,
    )
    sorted_liturgical = sorted(
        liturgical_table.items(),
        key=lambda item: len(item[0].split()),
        reverse=True,
    )

    results = []
    i = 0
    while i < len(tokens):
        matched = False

        # Layer 1: mantra table
        for key, entry in sorted_mantra:
            key_tokens = key.split()
            n = len(key_tokens)
            if tokens[i:i + n] == key_tokens:
                results.append((entry["zh"], "found"))
                i += n
                matched = True
                break

        if not matched:
            # Layer 2: liturgical table
            for key, entry in sorted_liturgical:
                key_tokens = key.split()
                n = len(key_tokens)
                if tokens[i:i + n] == key_tokens:
                    results.append((entry["zh"], "found"))
                    i += n
                    matched = True
                    break

        if not matched:
            results.append((tokens[i], "novel"))
            i += 1

    return results


# ── Function 4 ─────────────────────────────────────────────────────────────

def resolve_homophonic_layers(
    verse_result: dict,
    verse_unit: dict,
    requested_layers: set,
    mantra_table: dict,
    liturgical_table: dict,
) -> dict:
    """Route each requested homophonic layer to a value or a gap record.

    Parameters
    ----------
    verse_result:
        The 8-key dict returned by verse_pipeline.process_verse_unit.
    verse_unit:
        The verse-unit dict from layout_segment.segment_page_spans
        (provides page_index and verse_index for gap records).
    requested_layers:
        Set of layer names to resolve.  Valid values: ``"wylie"``,
        ``"mandarin_homophonic"``.  An empty set is valid.
    mantra_table:
        Layer-1 lookup table (mantra syllables).
    liturgical_table:
        Layer-2 lookup table (non-mantra liturgical terms).

    Returns
    -------
    dict with two keys:
      ``"layers"`` — dict mapping each requested layer to its value
                     (str if resolved, None if absent)
      ``"gaps"``   — list of gap records for absent/unresolvable layers

    Notes on wylie handling:
      Wylie always passes through as-is (None or str).  No gap record is
      produced for an absent wylie — there is no Wylie generation path.
      If wylie is None and mandarin_homophonic is also None, the
      mandarin_homophonic gap record carries source=None,
      status="no_source_available".

    Raises
    ------
    ValueError if any element of requested_layers is not a valid layer name.
    """
    unknown = requested_layers - _VALID_HOMOPHONIC_LAYERS
    if unknown:
        raise ValueError(
            f"Invalid layer name(s) in requested_layers: {unknown!r}. "
            f"Valid values: {sorted(_VALID_HOMOPHONIC_LAYERS)}"
        )

    layers = {}
    gaps = []

    for layer in requested_layers:

        if layer == "wylie":
            # Pass through as-is; no generation path exists for Wylie.
            layers["wylie"] = verse_result.get("wylie")

        elif layer == "mandarin_homophonic":
            value = verse_result.get("mandarin_homophonic")

            if value is not None:
                # Already present in the source — pass through unchanged.
                layers["mandarin_homophonic"] = value

            else:
                wylie = verse_result.get("wylie")

                if wylie is None:
                    # No Wylie string to look up — nothing we can do.
                    layers["mandarin_homophonic"] = None
                    gaps.append(_make_gap_record(
                        "mandarin_homophonic", None, verse_unit,
                        "no_source_available",
                    ))

                else:
                    tokens = _tokenize_wylie(wylie)
                    matches = _apply_both_tables(tokens, mantra_table, liturgical_table)
                    novel = [t for t, status in matches if status == "novel"]

                    if novel:
                        # Unrecognised syllables — human must author mapping.
                        layers["mandarin_homophonic"] = None
                        gap = _make_gap_record(
                            "mandarin_homophonic", "wylie", verse_unit,
                            "novel_needs_review",
                        )
                        gap["unresolved_tokens"] = novel
                        gaps.append(gap)
                    else:
                        # All tokens resolved — assemble and return.
                        layers["mandarin_homophonic"] = " ".join(
                            zh for zh, _ in matches
                        )

    return {"layers": layers, "gaps": gaps}
