"""Diagnostic: compute per-verse span counts using the segmentation algorithm,
before segment_page_spans is implemented, so we can write tests with ground truth."""
import sys, bisect
sys.path.insert(0, "src")
from format_detect import classify_document
from layout_segment import _find_tibetan_anchor_spans, _cluster_anchor_y0s

_FOOTER_FONTS = frozenset({"HelveticaNeue"})

def count_verse_spans(pdf_path, page_idx, label):
    doc = classify_document(pdf_path)
    spans = doc["pages"][page_idx]["spans"]
    content = [s for s in spans if s.get("font", "") not in _FOOTER_FONTS]
    anchors = _find_tibetan_anchor_spans(content)
    clusters = _cluster_anchor_y0s(anchors)
    buckets = [[] for _ in clusters]
    for span in content:
        y0 = span["bbox"][1]
        idx = bisect.bisect_right(clusters, y0) - 1
        if idx >= 0:
            buckets[idx].append(span)
    print(f"\n{label}")
    print(f"  Total clusters: {len(clusters)}")
    total = 0
    for i, (y, bucket) in enumerate(zip(clusters, buckets)):
        print(f"  verse {i}: cluster_y0={y:.2f}  span_count={len(bucket)}")
        total += len(bucket)
    skipped = sum(1 for s in content
                  if bisect.bisect_right(clusters, s["bbox"][1]) - 1 < 0)
    print(f"  Spans assigned: {total}  Header-dropped: {skipped}  Pre-filtered(footer): {len(spans)-len(content)}")

count_verse_spans(
    "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
    2, "RIGPE DORJE page 2")

count_verse_spans(
    "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf",
    1, "MEDICINE BUDDHA page 1")
