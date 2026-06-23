"""
Standalone test: crops TIBETAN_LEGACY_FONT spans from page index 1 of the
Medicine Buddha sample and saves them as PNGs under tests/output/page2_crops/.
"""
import sys
import os

sys.path.insert(0, "src")

import fitz
from format_detect import classify_document
from crop_tibetan import crop_tibetan_spans_for_page

PDF_PATH = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"
OUTPUT_DIR = "tests/output/page2_crops_merged"
PAGE_INDEX = 1

result = classify_document(PDF_PATH)

page_info = result["pages"][PAGE_INDEX]
classified_spans = page_info["spans"]

doc = fitz.open(PDF_PATH)
page = doc[PAGE_INDEX]

# --- Diagnostic: y-coordinate distribution of TIBETAN_LEGACY_FONT spans ---
tibetan_spans = [s for s in classified_spans if s.get("classification") == "TIBETAN_LEGACY_FONT"]
print(f"Total TIBETAN_LEGACY_FONT spans: {len(tibetan_spans)}")
print(f"\n{'idx':>4}  {'y0':>7}  {'y1':>7}  {'height':>7}  text")
print("-" * 60)
for i, s in enumerate(tibetan_spans):
    b = s["bbox"]
    print(f"{i:>4}  {b[1]:>7.2f}  {b[3]:>7.2f}  {b[3]-b[1]:>7.2f}  {s['text'][:20]!r}")

unique_y0 = sorted({round(s["bbox"][1]) for s in tibetan_spans})
print(f"\nUnique y0 values (rounded to nearest int): {unique_y0}")
print(f"Distinct y0 count: {len(unique_y0)}")
print()
# --- End diagnostic ---

crops = crop_tibetan_spans_for_page(page, classified_spans, OUTPUT_DIR)

print(f"Crops produced: {len(crops)}")
for c in crops:
    print(f"  line_id={c['line_id']}  bbox={c['bbox']}  -> {os.path.basename(c['image_path'])}")
