# Pipeline Design

## Goal
Convert traditional Tibetan Buddhist liturgical texts (sadhanas) — in varying
source formats — into multi-layer reference documents (docx) containing, per
verse-unit: Tibetan script (image), Wylie phonetic transliteration (text),
existing English translation (text), French translation (existing or
generated from English), and Mandarin homophonic transliteration of the
Tibetan phonetics (text, not a translation).

## Core safety constraint
**Tibetan script is never transcribed into Unicode text by an LLM or OCR.**
It is always preserved as a cropped image from the source. Roman-script
layers (Wylie, English, French) are extracted as text when a reliable text
layer exists, or vision-transcribed only when no text layer exists at all
(true scanned pecha pages). This rule holds regardless of source format.

## Input format categories (detected at Stage 0)
1. **PECHA_IMAGE** — long/narrow pages, no extractable text layer at all
   (scanned or vector-only from old DTP software). Requires ink-density
   band-detection to locate and crop each Tibetan line.
2. **UNICODE_TEXT** — standard page layout, Tibetan present as real Unicode
   text in a known Tibetan font. Rare in practice but the easiest case.
3. **LEGACY_FONT_TEXT** — standard page layout, but Tibetan-position text is
   actually Latin characters styled with a non-Unicode glyph-mapped font
   (visually Tibetan, textually meaningless if extracted naively). Common in
   older Word/QuarkXPress-produced sadhanas. Tibetan-position spans are
   cropped as images using their known bounding boxes (no band-detection
   needed, since position metadata already exists); Roman-script layers
   (Wylie/English/French) are extracted as real text directly.

## Pipeline stages
0. **Format detection** — classify document/page into one of the three
   categories above; this determines how every later stage behaves.
1. **Layout segmentation** — locate verse-unit boundaries; for PECHA_IMAGE,
   run ink-density band detection; for the other two, use embedded span
   position metadata.
2. **Tibetan cropping** — crop Tibetan-script regions as images per the
   method appropriate to the detected format.
3. **Roman-layer extraction/transcription** — extract Wylie/English/French
   as text directly when a real text layer exists; vision-transcribe only
   when it doesn't.
4. **French resolution** — check for an existing, independently-authored
   French translation first (some source documents have this); only
   generate French from English when no existing French is present.
5. **Mandarin homophonic transliteration** — lookup-table-first (layer 1:
   established mantra syllables; layer 2: common liturgical terms outside
   mantras), falling back to a flagged "novel — needs human review" output
   for anything not in the tables. Never silently auto-generates a mapping
   for unestablished syllables.
6. **Assembly** — reflow all layers into the target docx format.

## Human-in-the-loop checkpoints
- **100% review**: all mantra syllables, all "novel" Mandarin
  transliteration outputs (no established convention to fall back on).
- **Spot-check / flagged-only review**: non-mantra Roman-script
  transcription (when vision-transcribed from images), French translation
  quality.
- Review happens via Copilot Chat-assisted prompts the pipeline generates,
  not unattended API calls — this keeps a deliberate human decision point at
  every step that touches doctrinal or phonetic accuracy.

## Mandarin transliteration lookup table
Two-layer structure stored in `data/mantra_syllables_zh.json` (layer 1) and
`data/liturgical_terms_zh.json` (layer 2). Each entry should carry a
`source` field documenting where the mapping came from (a specific
published Chinese sadhana, a glossary, a lineage center's convention) —
there is no single canonical master list, so traceability per entry matters
more than completeness. `data/glossary_sources.md` tracks reference sources
used.

## Resumability
Per-verse-unit state tracked in a manifest (`segmented` → `roman_extracted`
→ `french_resolved` → `mandarin_transliterated` → `reviewed` → `assembled`),
persisted as JSON so interrupted runs on long documents don't require
restarting from scratch.