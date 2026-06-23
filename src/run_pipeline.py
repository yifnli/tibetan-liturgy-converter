"""
run_pipeline.py

CLI entry point and programmatic API for the end-to-end Tibetan liturgy
conversion pipeline (Stages 0–6).

Programmatic usage
------------------
    from src.run_pipeline import run

    summary = run(
        pdf_path  = "samples/.../source.pdf",
        out_docx  = "output/result.docx",
        requested_layers = {"english", "french", "wylie"},
    )
    # summary keys: verse_count, gap_count, gaps, out_docx

CLI usage
---------
    python src/run_pipeline.py <pdf_path> <out_docx> [<layers>]

    <layers> — optional comma-separated subset of:
                   english,french,mandarin_semantic,wylie,mandarin_homophonic
               Defaults to all five when omitted.

Notes
-----
- No new pipeline logic lives here; this module only wires the six stages.
- Lookup tables are loaded from data/mantra_syllables_zh.json and
  data/liturgical_terms_zh.json if they exist; empty dicts are used when
  the files are absent, so the pipeline runs without populated tables.
- PNG crops (LEGACY_FONT_TEXT path) are written to a temporary directory
  that is cleaned up after doc.save() completes.
- The fitz document is opened separately from classify_document (which
  opens and closes its own internal handle) because process_verse_unit
  needs a live fitz.Document for pixel-level crop rendering.
"""

import json
import os
import shutil
import sys
import tempfile

import fitz

from src.format_detect import classify_document
from src.layout_segment import segment_page_spans
from src.verse_pipeline import process_verse_unit
from src.translation_resolve import resolve_translation_layers
from src.homophonic_resolve import resolve_homophonic_layers
from src.assembly import build_document

# Partition of requested layers by which resolver handles each.
_TRANSLATION_LAYERS = frozenset({"english", "french", "mandarin_semantic"})
_HOMOPHONIC_LAYERS  = frozenset({"wylie", "mandarin_homophonic"})
_ALL_LAYERS         = _TRANSLATION_LAYERS | _HOMOPHONIC_LAYERS

# Relative to this file's location (src/../data)
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def _load_table(filename: str) -> dict:
    """Load a JSON lookup table from data/. Return empty dict if absent."""
    path = os.path.join(_DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def run(
    pdf_path: str,
    out_docx: str,
    requested_layers: set[str],
    layer_order: list[str] | None = None,
    debug: bool = False,
) -> dict:
    """Run the complete pipeline for one PDF and write a .docx file.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF.
    out_docx:
        Destination path for the output .docx.  The parent directory must
        already exist.
    requested_layers:
        Which text layers to include.  Any subset of
        {"english", "french", "mandarin_semantic", "wylie",
         "mandarin_homophonic"}.
    layer_order:
        Display order for text layers (Tibetan is always first regardless).
        Defaults to the _DEFAULT_LAYER_ORDER in assembly.py:
        ["wylie", "french", "english", "mandarin_homophonic",
         "mandarin_semantic"].
    debug:
        When True, the returned dict includes a ``"verse_results"`` key
        containing the list of raw 8-key dicts from process_verse_unit
        (one per verse-unit, in processing order).  Useful for inspecting
        intermediate extraction output without modifying the pipeline.
        Has no effect on .docx output.

    Returns
    -------
    dict:
        "verse_count"   — int  — number of verse-units processed
        "gap_count"     — int  — total gap records across all verses
        "gaps"          — list — all gap dicts (layer, source, status, verse_ref)
        "out_docx"      — str  — path written (echoes the argument)
        "verse_results" — list — (only when debug=True) raw process_verse_unit
                                  output, one dict per verse-unit
    """
    mantra_table    = _load_table("mantra_syllables_zh.json")
    liturgical_table = _load_table("liturgical_terms_zh.json")

    trans_requested = requested_layers & _TRANSLATION_LAYERS
    homo_requested  = requested_layers & _HOMOPHONIC_LAYERS

    tmp_dir = tempfile.mkdtemp(prefix="tibetan_crops_")
    try:
        # ── Stage 0: format detection (classify_document opens its own fitz handle) ──
        classified = classify_document(pdf_path)
        doc_format = classified["format"]
        pages      = classified["pages"]

        # Separate fitz.Document for pixel-level Tibetan crop rendering (LEGACY path).
        fitz_doc = fitz.open(pdf_path)

        assembly_inputs: list[dict] = []
        all_gaps: list[dict]        = []
        raw_verse_results: list[dict] = []  # populated only when debug=True

        for page_index, page in enumerate(pages):
            page_spans = page["spans"]

            # ── Stage 1: layout segmentation ────────────────────────────────
            verse_units = segment_page_spans(page_spans, page_index)

            for verse_unit in verse_units:
                # ── Stages 2+3: Tibetan acquisition + layer extraction ───────
                verse_result = process_verse_unit(
                    verse_unit, doc_format, fitz_doc, tmp_dir
                )
                if debug:
                    raw_verse_results.append(verse_result)

                # ── Stage 4: translation resolution ─────────────────────────
                trans_out = resolve_translation_layers(
                    verse_result, verse_unit, trans_requested
                )

                # ── Stage 5: homophonic resolution ───────────────────────────
                homo_out = resolve_homophonic_layers(
                    verse_result, verse_unit, homo_requested,
                    mantra_table, liturgical_table,
                )

                # Merge resolved layers from both resolvers.
                merged_layers: dict = {}
                merged_layers.update(trans_out["layers"])
                merged_layers.update(homo_out["layers"])
                verse_gaps = trans_out["gaps"] + homo_out["gaps"]
                all_gaps.extend(verse_gaps)

                assembly_inputs.append({
                    "tibetan_unicode":     verse_result.get("tibetan_unicode"),
                    "tibetan_image_paths": verse_result.get("tibetan_image_paths", []),
                    "layers":  merged_layers,
                    "gaps":    verse_gaps,
                    "verse_ref": {
                        "page_index":  verse_unit["page_index"],
                        "verse_index": verse_unit["verse_index"],
                    },
                    "doc_format": doc_format,
                })

        fitz_doc.close()

        # ── Stage 6: assembly → write .docx ─────────────────────────────────
        # Images are embedded into the Document object at add_picture() call
        # time, so tmp_dir may be cleaned up safely after save().
        doc = build_document(assembly_inputs, layer_order)
        doc.save(out_docx)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    summary = {
        "verse_count": len(assembly_inputs),
        "gap_count":   len(all_gaps),
        "gaps":        all_gaps,
        "out_docx":    out_docx,
    }
    if debug:
        summary["verse_results"] = raw_verse_results
    return summary


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python src/run_pipeline.py <pdf_path> <out_docx> [<layers>]\n"
            "  <layers>: comma-separated from:\n"
            "    english,french,mandarin_semantic,wylie,mandarin_homophonic\n"
            "  Default: all five layers.",
            file=sys.stderr,
        )
        sys.exit(1)

    _pdf  = sys.argv[1]
    _docx = sys.argv[2]
    _layers = (
        set(sys.argv[3].split(","))
        if len(sys.argv) > 3
        else set(_ALL_LAYERS)
    )

    _summary = run(_pdf, _docx, _layers)
    print(f"Verses processed : {_summary['verse_count']}")
    print(f"Gaps recorded    : {_summary['gap_count']}")
    print(f"Output written   : {_summary['out_docx']}")
    if _summary["gaps"]:
        print("Gaps:")
        for _g in _summary["gaps"]:
            _vr = _g.get("verse_ref", {})
            print(
                f"  p{_vr.get('page_index', '?')}v{_vr.get('verse_index', '?')}"
                f"  [{_g.get('layer')}]  {_g.get('status')}  ← {_g.get('source')}"
            )
