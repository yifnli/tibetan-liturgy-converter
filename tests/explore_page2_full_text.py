"""Dumps full span text for the truncated spans on page index 2."""
import fitz, sys
sys.path.insert(0, "src")
from format_detect import classify_span

doc = fitz.open("samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf")
page = doc[2]
all_spans = []
for block in page.get_text("dict")["blocks"]:
    if "lines" not in block:
        continue
    for line in block["lines"]:
        for span in line["spans"]:
            s = {
                "text": span.get("text") or "",
                "font": span.get("font", ""),
                "size": round(span.get("size", 0), 2),
                "bbox": tuple(round(v, 2) for v in span["bbox"]),
                "classification": classify_span(span),
            }
            all_spans.append(s)

# Print full text for key spans (no truncation)
key_indices = [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 39, 43,
               45, 48, 49, 50, 51, 52, 70, 74,
               76, 77, 78, 79, 80, 81, 82, 83, 84, 102, 106]
for i in key_indices:
    s = all_spans[i]
    print(f"[{i:3d}] cls={s['classification'][:12]:12s}  "
          f"font={s['font'][:30]:30s}  sz={s['size']:5.1f}  "
          f"y0={s['bbox'][1]:7.2f}")
    print(f"      text={repr(s['text'])}")
    print()
