"""
Diagnostic for Stage 1 (layout segmentation).
Shows vertical span distribution for:
  - Rigpe Dorje page 2 (UNICODE_TEXT)
  - Medicine Buddha pages 1 and 2 (LEGACY_FONT_TEXT)
"""
import sys
sys.path.insert(0, "src")
import fitz
from format_detect import classify_span

SEPARATOR = "=" * 70

def dump_page(pdf_path, page_idx, label):
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    print(f"\n{SEPARATOR}")
    print(f"{label}  (page index {page_idx}, {page.rect.width:.0f}x{page.rect.height:.0f} pt)")
    print(SEPARATOR)
    spans = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                spans.append({
                    "text": span.get("text") or "",
                    "font": span.get("font", ""),
                    "size": round(span.get("size", 0), 2),
                    "bbox": tuple(round(v, 2) for v in span["bbox"]),
                    "classification": classify_span(span),
                })
    doc.close()

    # Print each span with y0, classification, and abbreviated text
    for i, s in enumerate(spans):
        cls = s["classification"]
        y0 = s["bbox"][1]
        txt = repr(s["text"])[:55]
        print(f"  [{i:3d}] y0={y0:7.2f}  cls={cls[:12]:12s}  "
              f"font={s['font'][:26]:26s}  sz={s['size']:4.1f}  {txt}")

    # Show unique y0 positions for TIBETAN_UNICODE and TIBETAN_LEGACY_FONT
    tibetan_y = sorted({round(s["bbox"][1], 1)
                        for s in spans
                        if s["classification"] in ("TIBETAN_UNICODE",
                                                    "TIBETAN_LEGACY_FONT")})
    print(f"\n  Tibetan-script y0 positions: {tibetan_y}")

    # Show unique y0 positions for ROMAN_TEXT (ignoring noise)
    roman_y = sorted({round(s["bbox"][1], 1)
                      for s in spans
                      if s["classification"] == "ROMAN_TEXT"
                      and s["font"] not in ("Georgia", "HelveticaNeue")
                      and s["size"] <= 13})
    print(f"  Roman-text y0 positions (non-noise, <=13pt): {roman_y}")

    return spans

# ── Rigpe Dorje: page 2 ──────────────────────────────────────────────────
rd_spans = dump_page(
    "samples/rigpe-dorje-treasury-of-blessings/"
    "treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
    2, "RIGPE DORJE — UNICODE_TEXT")

# ── Medicine Buddha: page 1 ──────────────────────────────────────────────
mb1_spans = dump_page(
    "samples/medicine-buddha-sample/"
    "Medicine-Buddha-Tib-Fr-Eng-WORD.pdf",
    1, "MEDICINE BUDDHA — LEGACY_FONT_TEXT, page index 1")

# ── Medicine Buddha: page 2 ──────────────────────────────────────────────
mb2_spans = dump_page(
    "samples/medicine-buddha-sample/"
    "Medicine-Buddha-Tib-Fr-Eng-WORD.pdf",
    2, "MEDICINE BUDDHA — LEGACY_FONT_TEXT, page index 2")
