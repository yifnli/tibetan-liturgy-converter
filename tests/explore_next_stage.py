"""Live pipeline probe — Step 3 data extraction for planning next module."""
import sys, pprint
sys.path.insert(0, "src")
from format_detect import classify_document
from layout_segment import segment_page_spans
from extract_text_layers import extract_text_layers_for_verse_unit
from crop_tibetan import merge_spans_into_lines

_RD_PDF = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"

print("=" * 70)
print("RIGPE DORJE — page 2, verse-unit 0")
print("=" * 70)
rd_doc = classify_document(_RD_PDF)
rd_p2_spans = rd_doc["pages"][2]["spans"]
rd_verses = segment_page_spans(rd_p2_spans, page_index=2)
vu0 = rd_verses[0]
result = extract_text_layers_for_verse_unit(vu0["spans"])
pprint.pprint(result)

print()
print("=" * 70)
print("MEDICINE BUDDHA — page index 0, verse-unit 0 spans")
print("=" * 70)
mb_doc = classify_document(_MB_PDF)
mb_p0_spans = mb_doc["pages"][0]["spans"]
mb_verses_p0 = segment_page_spans(mb_p0_spans, page_index=0)
print(f"  Total verse units on page 0: {len(mb_verses_p0)}")
if mb_verses_p0:
    vu0_mb = mb_verses_p0[0]
    print(f"  Verse-unit 0 span count: {len(vu0_mb['spans'])}")
    for s in vu0_mb["spans"]:
        print(f"    cls={s['classification']:24s}  font={s.get('font','')[:30]:30s}  "
              f"sz={s.get('size',0):5.1f}  y0={s['bbox'][1]:.2f}  "
              f"text={repr(s['text'][:40])}")
    tib_spans = [s for s in vu0_mb["spans"] if s["classification"] == "TIBETAN_LEGACY_FONT"]
    print(f"\n  TIBETAN_LEGACY_FONT spans in verse-unit 0: {len(tib_spans)}")
    lines = merge_spans_into_lines(vu0_mb["spans"])
    print(f"  merge_spans_into_lines would produce: {len(lines)} line bbox(s)")
    for i, (x0, y0, x1, y1) in enumerate(lines):
        print(f"    line {i}: y0={y0:.2f}  bbox=({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
else:
    print("  (no verse units found on page 0)")

print()
print("=" * 70)
print("MEDICINE BUDDHA — page index 1, verse-unit 0 (the known-good page)")
print("=" * 70)
mb_p1_spans = mb_doc["pages"][1]["spans"]
mb_verses_p1 = segment_page_spans(mb_p1_spans, page_index=1)
vu0_mb1 = mb_verses_p1[0]
print(f"  Total verse units on page 1: {len(mb_verses_p1)}")
print(f"  Verse-unit 0 span count: {len(vu0_mb1['spans'])}")
tib_spans_p1 = [s for s in vu0_mb1["spans"] if s["classification"] == "TIBETAN_LEGACY_FONT"]
print(f"  TIBETAN_LEGACY_FONT spans: {len(tib_spans_p1)}")
lines_p1 = merge_spans_into_lines(vu0_mb1["spans"])
print(f"  merge_spans_into_lines output: {len(lines_p1)} line(s)")
for i, (x0, y0, x1, y1) in enumerate(lines_p1):
    print(f"    line {i}: y0={y0:.2f}")
