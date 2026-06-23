#!/usr/bin/env python
"""
test_integration.py

End-to-end integration script for the Tibetan liturgy conversion pipeline.

NOT a pytest file — run as a standalone script:
    python tests/test_integration.py

Runs the full pipeline against both sample PDFs, writes .docx output to
output/, prints a human-readable summary, then verifies both files open
without error by re-opening them with python-docx and reporting paragraph
counts.

No assertions are made.  The intent is to confirm correct wiring and to
produce real .docx files for manual layout inspection.
"""

import os
import sys

# Allow `from src.xxx import ...` from the project root.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from src.run_pipeline import run, _ALL_LAYERS

# ── Paths ───────────────────────────────────────────────────────────────────

SAMPLES = {
    "rigpe_dorje": {
        "label":   "Rigpe Dorje — Treasury of Blessings (UNICODE_TEXT)",
        "pdf":     os.path.join(_ROOT, "samples", "rigpe-dorje-treasury-of-blessings",
                                "treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"),
        "out_docx": os.path.join(_ROOT, "output", "treasury_of_blessings.docx"),
    },
    "medicine_buddha": {
        "label":   "Medicine Buddha (LEGACY_FONT_TEXT)",
        "pdf":     os.path.join(_ROOT, "samples", "medicine-buddha-sample",
                                "Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"),
        "out_docx": os.path.join(_ROOT, "output", "medicine_buddha.docx"),
    },
}

OUTPUT_DIR = os.path.join(_ROOT, "output")


def _hr():
    print("-" * 70)


def run_one(key: str, info: dict) -> dict | None:
    """Run the pipeline for one PDF. Returns the summary dict or None on error."""
    _hr()
    print(f"▶  {info['label']}")
    print(f"   PDF  : {info['pdf']}")
    print(f"   DOCX : {info['out_docx']}")

    if not os.path.exists(info["pdf"]):
        print(f"   ✗  PDF not found — skipping.")
        return None

    try:
        summary = run(
            pdf_path=info["pdf"],
            out_docx=info["out_docx"],
            requested_layers=set(_ALL_LAYERS),
        )
    except Exception as exc:
        print(f"    ERROR: Pipeline raised {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return None

    print(f"    Verse count : {summary['verse_count']}")
    print(f"    Gap count   : {summary['gap_count']}")

    if summary["gaps"]:
        print("    Gaps:")
        for g in summary["gaps"]:
            vr = g.get("verse_ref", {})
            print(
                f"      p{vr.get('page_index', '?')}v{vr.get('verse_index', '?')}"
                f"  [{g.get('layer')}]  {g.get('status')}  <- {g.get('source')}"
            )
    else:
        print("    Gaps: none")

    return summary


def verify_docx(label: str, path: str) -> None:
    """Open the written .docx with python-docx and report paragraph count."""
    from docx import Document as open_docx
    try:
        doc = open_docx(path)
        para_count = len(doc.paragraphs)
        print(f"    OK: {label} -- {para_count} paragraphs")
    except Exception as exc:
        print(f"    FAIL: {label} -- {exc}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = {}
    for key, info in SAMPLES.items():
        results[key] = run_one(key, info)

    _hr()
    print("VERIFICATION — re-opening .docx files with python-docx:")
    for key, info in SAMPLES.items():
        if results[key] is not None and os.path.exists(info["out_docx"]):
            verify_docx(info["label"], info["out_docx"])
        else:
            print(f"    --  {info['label']} -- skipped (no output)")

    _hr()
    print("SUMMARY")
    for key, info in SAMPLES.items():
        s = results[key]
        if s:
            print(
                f"  {info['label'][:50]:<50}  "
                f"verses={s['verse_count']:4d}  gaps={s['gap_count']:4d}  "
                f"-> {os.path.basename(info['out_docx'])}"
            )
        else:
            print(f"  {info['label'][:50]:<50}  FAILED or SKIPPED")
    _hr()


if __name__ == "__main__":
    main()
