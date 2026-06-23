"""
layout_segment.py

Stage 1: Layout segmentation.

Takes the classified spans for a single page (as produced by
format_detect.classify_document) and groups them into verse-unit dicts.
Each verse-unit dict contains all the spans belonging to one discrete
verse of the liturgical text, keyed by verse_index within the page.

The segmentation anchor for each verse unit is the block of Tibetan-script
spans at the top of that unit:

  UNICODE_TEXT pages (Rigpe Dorje):
    TIBETAN_UNICODE spans with 17–19 pt font size. The page title uses
    sz=20 and is excluded by this filter.

  LEGACY_FONT_TEXT pages (Medicine Buddha):
    TIBETAN_LEGACY_FONT spans with size > 18 pt. The stray noise span
    at sz=15.8 and the absorbed shad/comma spans (sz=12) are excluded
    by this filter.

Spans that appear above the first anchor (page headers, section titles,
attribution lines, etc.) are silently dropped. Spans in HelveticaNeue
font (page number footers) are pre-filtered before any assignment.

The y-clustering algorithm is identical to the one in crop_tibetan.py:
a rolling-minimum sweep with y_tolerance=6.5 pt.
"""

import bisect

# ── Size filters for Tibetan anchor detection ──────────────────────────────

# UNICODE_TEXT: MonlamUniOuChan2 verse Tibetan is sz=18; title is sz=20.
_TIBETAN_UNICODE_VERSE_SIZE_MIN = 17.0
_TIBETAN_UNICODE_VERSE_SIZE_MAX = 19.0

# LEGACY_FONT_TEXT: Dedris verse Tibetan is sz≈20.9; noise spans are ≤15.8.
_TIBETAN_LEGACY_VERSE_MIN_SIZE = 18.0

# Fonts that mark footer/header noise — excluded before any span assignment.
_FOOTER_FONTS = frozenset({"HelveticaNeue"})

# Default y-tolerance (pt) — matches crop_tibetan.merge_spans_into_lines.
_Y_TOLERANCE_DEFAULT = 6.5


# ── Function 1 ─────────────────────────────────────────────────────────────

def _find_tibetan_anchor_spans(classified_spans: list) -> list:
    """Return the spans that serve as verse-unit anchors.

    For UNICODE_TEXT pages: TIBETAN_UNICODE spans with
      ``_TIBETAN_UNICODE_VERSE_SIZE_MIN <= size <= _TIBETAN_UNICODE_VERSE_SIZE_MAX``
      (17–19 pt).  The page title uses sz=20 and is intentionally excluded.

    For LEGACY_FONT_TEXT pages: TIBETAN_LEGACY_FONT spans with
      ``size > _TIBETAN_LEGACY_VERSE_MIN_SIZE`` (> 18 pt).  The stray
      noise/shad spans at sz≤15.8 and sz=12 are excluded.

    Both filters are applied unconditionally to the same span list; a span
    can only satisfy one because it carries exactly one classification.
    """
    result = []
    for span in classified_spans:
        cls = span.get("classification", "")
        size = span.get("size", 0)
        if cls == "TIBETAN_UNICODE":
            if _TIBETAN_UNICODE_VERSE_SIZE_MIN <= size <= _TIBETAN_UNICODE_VERSE_SIZE_MAX:
                result.append(span)
        elif cls == "TIBETAN_LEGACY_FONT":
            if size > _TIBETAN_LEGACY_VERSE_MIN_SIZE:
                result.append(span)
    return result


# ── Function 2 ─────────────────────────────────────────────────────────────

def _cluster_anchor_y0s(
    anchor_spans: list,
    y_tolerance: float = _Y_TOLERANCE_DEFAULT,
) -> list:
    """Cluster anchor spans by vertical position into visual Tibetan lines.

    Uses the same rolling-minimum algorithm as
    ``crop_tibetan.merge_spans_into_lines``: spans are sorted by bbox y0,
    then a new cluster is started whenever the current span's y0 differs
    from the running minimum y0 of the current group by more than
    y_tolerance.

    Returns a sorted (ascending) list of cluster min-y0 floats, one value
    per visual Tibetan line found.
    """
    if not anchor_spans:
        return []

    # Sort ascending by top-y — identical to crop_tibetan's sweep order.
    sorted_spans = sorted(anchor_spans, key=lambda s: s["bbox"][1])

    cluster_min_y0s: list[float] = []   # one entry per cluster (the running min y0)
    group_min_y0: list[float] = []      # single-element list; mirrors crop_tibetan pattern

    for span in sorted_spans:
        by0 = span["bbox"][1]
        if group_min_y0 and abs(by0 - group_min_y0[-1]) <= y_tolerance:
            # Same cluster — update running minimum y0 for this group.
            group_min_y0[-1] = min(group_min_y0[-1], by0)
            # Also update the stored cluster min (in case by0 < previous min).
            cluster_min_y0s[-1] = group_min_y0[-1]
        else:
            # New cluster — record it and start fresh group tracking.
            group_min_y0.clear()
            group_min_y0.append(by0)
            cluster_min_y0s.append(by0)

    return cluster_min_y0s  # already in ascending order (swept top-to-bottom)


# ── Function 3 ─────────────────────────────────────────────────────────────

def segment_page_spans(
    classified_spans: list,
    page_index: int,
    y_tolerance: float = _Y_TOLERANCE_DEFAULT,
) -> list:
    """Group classified spans for one page into verse-unit dicts.

    Algorithm:
      1. Pre-filter: remove any span whose font is in ``_FOOTER_FONTS``
         (HelveticaNeue page-number footers/headers).
      2. Find Tibetan anchor spans via ``_find_tibetan_anchor_spans``.
      3. Cluster anchor y0 values via ``_cluster_anchor_y0s``.
      4. For each remaining span, assign it to the verse unit whose cluster
         min-y0 is the *largest value ≤ span.y0* (bisect_right lookup).
         Spans whose y0 precedes the first cluster (page header content)
         produce an index of -1 and are silently dropped.
      5. Return one dict per non-empty cluster, in top-to-bottom order.

    Returns a list of dicts:
      {
        "verse_index": int,   # 0-based within this page
        "page_index":  int,   # the page_index argument
        "spans":       list,  # classified span dicts belonging to this unit
      }
    """
    # Step 1 — remove footer/header noise fonts before any processing.
    content_spans = [
        s for s in classified_spans
        if s.get("font", "") not in _FOOTER_FONTS
    ]

    # Steps 2–3 — find anchors and cluster them.
    anchors = _find_tibetan_anchor_spans(content_spans)
    cluster_y0s = _cluster_anchor_y0s(anchors, y_tolerance)

    if not cluster_y0s:
        return []

    # Step 4 — assign each span to the most-recent anchor cluster.
    buckets: list[list] = [[] for _ in cluster_y0s]
    for span in content_spans:
        span_y0 = span["bbox"][1]
        idx = bisect.bisect_right(cluster_y0s, span_y0) - 1
        if idx >= 0:
            buckets[idx].append(span)
        # idx == -1  →  span is above the first anchor (header) → silently drop

    # Step 5 — build result dicts, skipping empty buckets.
    result = []
    for i, spans in enumerate(buckets):
        if spans:
            result.append({
                "verse_index": i,
                "page_index":  page_index,
                "spans":       spans,
            })
    return result
