"""Step 3 live data extraction for Stage 4 planning."""
import sys, pprint, copy
sys.path.insert(0, ".")
sys.path.insert(0, "src")
import fitz
from format_detect import classify_document
from layout_segment import segment_page_spans
from verse_pipeline import process_verse_unit

_RD_PDF = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"

import tempfile, os
tmpdir = tempfile.mkdtemp()

# ── Case 1: Rigpe Dorje page 2 verse 0 — all 6 text layers ──────────────
rd_doc = classify_document(_RD_PDF)
rd_pdf = fitz.open(_RD_PDF)
rd_p2 = segment_page_spans(rd_doc["pages"][2]["spans"], page_index=2)
result_rd = process_verse_unit(rd_p2[0], rd_doc["format"], rd_pdf, tmpdir)
print("=" * 70)
print("CASE 1 — Rigpe Dorje page 2 verse 0 (UNICODE_TEXT, all layers)")
print("=" * 70)
pprint.pprint(result_rd)

# ── Case 2: Same, but CJK layers manually set to None ────────────────────
result_rd_no_cjk = copy.copy(result_rd)
result_rd_no_cjk["mandarin_homophonic"] = None
result_rd_no_cjk["mandarin_semantic"] = None
print()
print("=" * 70)
print("CASE 2 — Same verse, mandarin_homophonic/semantic forced to None")
print("         (simulates missing CJK, would need generation)")
print("=" * 70)
pprint.pprint(result_rd_no_cjk)

# ── Case 3: Medicine Buddha page 1 verse 0 ────────────────────────────────
mb_doc = classify_document(_MB_PDF)
mb_pdf = fitz.open(_MB_PDF)
mb_p1 = segment_page_spans(mb_doc["pages"][1]["spans"], page_index=1)
result_mb = process_verse_unit(mb_p1[0], mb_doc["format"], mb_pdf, tmpdir)
print()
print("=" * 70)
print("CASE 3 — Medicine Buddha page 1 verse 0 (LEGACY_FONT_TEXT)")
print("=" * 70)
pprint.pprint(result_mb)
print()

# Summary of what's present/absent per case
def layer_status(d):
    keys = ["tibetan_unicode", "tibetan_image_paths", "wylie", "french",
            "english", "mandarin_homophonic", "mandarin_semantic", "ambiguous_cjk"]
    return {k: ("PRESENT" if d.get(k) not in (None, [], "") else "ABSENT/EMPTY")
            for k in keys}

print("=" * 70)
print("LAYER STATUS SUMMARY")
print("=" * 70)
for label, d in [("Case 1 (RD all)", result_rd),
                 ("Case 2 (RD no CJK)", result_rd_no_cjk),
                 ("Case 3 (MB LEGACY)", result_mb)]:
    print(f"\n  {label}:")
    for k, v in layer_status(d).items():
        print(f"    {k:30s}  {v}")
