"""
crop_tibetan.py

Crops Tibetan-script regions as images, using the format-appropriate method:
- TIBETAN_LEGACY_FONT: use known span bounding boxes directly
- PECHA_IMAGE pages: requires band_detect.py's ink-density profiling first
- TIBETAN_UNICODE: NOT handled here — extracted as text directly in
  extract_text_layers.py, since cropping a reliable Unicode span as an
  image would discard a layer that's already safe to trust as text.
"""

import fitz

def crop_span_as_image(page: fitz.Page, bbox: tuple, output_path: str, dpi: int = 300):
    """Renders the page at given dpi and crops to bbox, saving as PNG."""
    scale = dpi / 72  # PDF points are 72 dpi by default
    matrix = fitz.Matrix(scale, scale)
    clip = fitz.Rect(bbox)
    pix = page.get_pixmap(matrix=matrix, clip=clip)
    pix.save(output_path)

def merge_spans_into_lines(classified_spans: list, y_tolerance: float = 6.5) -> list:
    """Groups TIBETAN_LEGACY_FONT spans that share approximately the same
    vertical position into single merged bounding boxes, each representing
    one visual Tibetan line.

    Two spans are considered to be on the same visual line if the difference
    between their bbox top-y values (bbox[1]) is within y_tolerance PDF
    points. This handles minor vertical jitter in how the PDF stores spans
    within a single typeset line.

    Comparison is made against the running minimum y0 of the current group
    (i.e. the topmost span seen so far in the group), not just the initial
    span's y0. This correctly handles cumulative within-line drift where
    successive spans step slightly lower than the group's first span.

    Returns a list of merged bboxes — one per visual line — where each merged
    bbox is a tuple (x0, y0, x1, y1) spanning from the leftmost to rightmost
    extent of all spans on that line. The returned list is sorted top-to-bottom
    by y0.

    Only operates on spans with classification == "TIBETAN_LEGACY_FONT".
    Spans of other classifications are ignored.
    """
    import unicodedata

    def _has_visible_content(text: str) -> bool:
        """True if text contains at least one character that is not a Unicode
        separator (Zs/Zl/Zp) or control/format/surrogate (Cc/Cf/Cs).
        This is more robust than str.strip() == '' because some non-whitespace
        codepoints (e.g. U+00AD SOFT HYPHEN) produce blank glyphs but are
        not stripped by Python's str.strip()."""
        return any(
            not unicodedata.category(ch).startswith(("Z", "C"))
            for ch in text
        )

    # FIX A: skip spans whose text has no visible content — pure whitespace,
    # soft hyphens, format characters, and other codepoints that produce
    # blank glyphs in legacy fonts and must never produce a crop.
    tibetan_spans = [
        s for s in classified_spans
        if s.get("classification") == "TIBETAN_LEGACY_FONT"
        and _has_visible_content(s.get("text") or "")
    ]
    # Sort by top-y so we can sweep through once
    tibetan_spans.sort(key=lambda s: s["bbox"][1])

    lines = []            # each entry: [x0, y0, x1, y1] (mutable during merging)
    group_min_y0 = []     # running minimum y0 for each group
    group_span_counts = []  # number of spans merged into each group (for FIX B)
    for span in tibetan_spans:
        bx0, by0, bx1, by1 = span["bbox"]
        # Compare against the running-min y0 of the current group so that
        # cumulative within-line drift doesn't cause a false split.
        if lines and abs(by0 - group_min_y0[-1]) <= y_tolerance:
            # Extend the current line's bbox horizontally and vertically
            lines[-1][0] = min(lines[-1][0], bx0)
            lines[-1][2] = max(lines[-1][2], bx1)
            lines[-1][3] = max(lines[-1][3], by1)
            group_min_y0[-1] = min(group_min_y0[-1], by0)
            group_span_counts[-1] += 1
        else:
            lines.append([bx0, by0, bx1, by1])
            group_min_y0.append(by0)
            group_span_counts.append(1)

    # FIX B: absorb or discard isolated single-span groups that are layout
    # artifacts rather than real Tibetan lines.
    #
    # Legacy font spans encode Tibetan glyphs as Latin characters, so we
    # cannot use Tibetan Unicode codepoints to identify punctuation.
    # Instead, we use the vertical geometry of each group relative to its
    # neighbours — a strategy that is font-encoding-agnostic:
    #
    #   Leading orphan (i == 0): a single-span group sitting just above the
    #   first real line.  We discard it if the gap from this group's bottom
    #   (y1) to the next group's top (y0) is <= LEADING_DISCARD_GAP.
    #   (Observed gap for the stray glyph at y≈89: 0.48 pts.)
    #
    #   Trailing dangle (i > 0): a single-span group sitting just below the
    #   line it belongs to (terminal punctuation that fell outside the
    #   y_tolerance window).  We absorb it into the preceding group if the
    #   gap from the preceding group's bottom (y1) to this group's top (y0)
    #   is <= TRAILING_ABSORB_GAP.
    #   (Observed gap for the stray Shad/comma at y≈157: 16.2 pts; real
    #   inter-line bottom-to-top gap is ~42 pts — comfortably above 25.)
    LEADING_DISCARD_GAP = 5.0   # pts between orphan.y1 and next_group.y0
    TRAILING_ABSORB_GAP = 25.0  # pts between prev_group.y1 and dangle.y0

    merged = list(lines)  # shallow copy — we replace elements, not mutate them
    to_remove = set()
    for i in range(len(merged)):
        if group_span_counts[i] != 1:
            continue  # only consider single-span groups as artifact candidates
        if i == 0 and len(merged) > 1:
            # Leading orphan: discard if immediately above the next group
            gap_to_next = merged[1][1] - merged[0][3]  # next.y0 - this.y1
            if gap_to_next <= LEADING_DISCARD_GAP:
                to_remove.add(0)
        elif i > 0:
            # Trailing dangle: absorb into preceding group if close below it
            gap_to_prev = merged[i][1] - merged[i - 1][3]  # this.y0 - prev.y1
            if gap_to_prev <= TRAILING_ABSORB_GAP:
                prev = merged[i - 1]
                merged[i - 1] = (
                    prev[0],
                    prev[1],
                    max(prev[2], merged[i][2]),
                    prev[3],
                )
                to_remove.add(i)

    return [tuple(b) for i, b in enumerate(merged) if i not in to_remove]


def crop_tibetan_spans_for_page(page: fitz.Page, classified_spans: list, output_dir: str,
                                y_tolerance: float = 6.5) -> list:
    """Given spans classified as TIBETAN_LEGACY_FONT (or pecha-Tibetan via a
    separate band-detection path, not span-based), crop each as an image.
    Deliberately filters OUT TIBETAN_UNICODE spans — those are never
    cropped. Merges per-span bboxes into whole-line bboxes first.
    Returns list of {line_id, image_path, bbox}."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    results = []
    merged_lines = merge_spans_into_lines(classified_spans, y_tolerance=y_tolerance)
    for line_id, bbox in enumerate(merged_lines):
        filename = f"line_{line_id:04d}_{int(bbox[0])}_{int(bbox[1])}.png"
        output_path = os.path.join(output_dir, filename)
        crop_span_as_image(page, bbox, output_path)
        results.append({
            "line_id": line_id,
            "image_path": output_path,
            "bbox": bbox,
        })
    return results