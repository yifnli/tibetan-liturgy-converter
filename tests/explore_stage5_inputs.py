"""Step 3 live data for Stage 5 planning."""
import sys, pprint, copy
sys.path.insert(0, ".")
sys.path.insert(0, "src")
import fitz
from format_detect import classify_document
from layout_segment import segment_page_spans
from verse_pipeline import process_verse_unit
from translation_resolve import resolve_translation_layers

_RD_PDF = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"

import tempfile
tmpdir = tempfile.mkdtemp()

rd_doc = classify_document(_RD_PDF)
rd_pdf = fitz.open(_RD_PDF)
rd_p2  = segment_page_spans(rd_doc["pages"][2]["spans"], page_index=2)

mb_doc = classify_document(_MB_PDF)
mb_pdf = fitz.open(_MB_PDF)
mb_p1  = segment_page_spans(mb_doc["pages"][1]["spans"], page_index=1)

case1_result = process_verse_unit(rd_p2[0], rd_doc["format"], rd_pdf, tmpdir)
case2_result = {**case1_result, "mandarin_homophonic": None, "mandarin_semantic": None}
case3_result = process_verse_unit(mb_p1[0], mb_doc["format"], mb_pdf, tmpdir)

_REQ = {"english", "french", "mandarin_semantic"}
_VU_RD = rd_p2[0]
_VU_MB = mb_p1[0]

for label, result, vu in [
    ("CASE 1 — RD all layers",           case1_result, _VU_RD),
    ("CASE 2 — RD mandarin_* forced None", case2_result, _VU_RD),
    ("CASE 3 — MB LEGACY_FONT_TEXT",      case3_result, _VU_MB),
]:
    print("=" * 70)
    print(f"Stage 4 output for: {label}")
    print("=" * 70)
    stage4_out = resolve_translation_layers(result, vu, _REQ)
    pprint.pprint(stage4_out)
    print()
    print(f"  Stage 5 inputs:")
    print(f"    wylie               = {result['wylie']!r}")
    print(f"    mandarin_homophonic = {result['mandarin_homophonic']!r}")
    need_gap = result["mandarin_homophonic"] is None
    print(f"    needs homophonic gap record: {need_gap}")
    print()
