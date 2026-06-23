"""One-shot diagnostic: dumps all span data from page index 2 of the Rigpe Dorje PDF."""
import fitz, sys
sys.path.insert(0, "src")
from format_detect import classify_span

doc = fitz.open("samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf")
page = doc[2]
print(f"Page 2 dimensions: {page.rect}")
spans = []
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
            spans.append(s)

print(f"Total spans: {len(spans)}\n")
for i, s in enumerate(spans):
    print(
        f"[{i:3d}] cls={s['classification'][:12]:12s}  "
        f"font={s['font'][:32]:32s}  sz={s['size']:5.1f}  "
        f"y0={s['bbox'][1]:7.2f}  "
        f"text={repr(s['text'])[:70]}"
    )
