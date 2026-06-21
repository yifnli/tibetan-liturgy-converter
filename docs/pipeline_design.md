# Pipeline Design

## Goal
Convert traditional Tibetan Buddhist liturgical texts (sadhanas) — in varying
source formats — into multi-layer reference documents (docx) containing
Tibetan script plus a user-selected combination of translation and
transliteration layers (see "Output schema" below).

## Core safety constraint
**Tibetan script is never transcribed into Unicode text by an LLM or OCR
unless it is already present in the source as genuine Unicode text.** Where
Tibetan exists only as a scanned image or as Latin characters mapped to a
legacy display font, it is always preserved as a cropped image, never
re-derived through vision-transcription or font-decoding guesswork. Where
Tibetan already exists as real Unicode text in the source (see
UNICODE_TEXT below), it is extracted directly as text — there is no
transcription risk to guard against in that case, since the accurate
Unicode already exists; cropping it as an image as well would be a needless
downgrade of a layer that's already reliable. Roman-script layers
(Wylie, English, French) are extracted as text when a reliable text layer
exists, or vision-transcribed only when no text layer exists at all (true
scanned pecha pages). This rule holds regardless of source format.

## Output schema (user-configurable)
The target document is no longer a fixed five-layer structure. Per
verse-unit, the user selects which layers to include at generation time:

- **Tibetan script** — always included, non-optional.
- **Translation layer(s)** — zero or more of: English, French, Mandarin
  (semantic translation, meaning-based — e.g. rendering "Vajradhara" as
  ⾦刚总持, not as a phonetic approximation of the Tibetan sound).
- **Homophonic transliteration layer(s)** — zero or more of: Wylie/English
  phonetic (Romanized rendering of the Tibetan pronunciation, e.g. "DOR JE
  CHANG"), Mandarin homophonic (Chinese characters chosen to approximate
  the Tibetan sound, e.g. "多杰 羌千" for the same phrase — sound-based, not
  meaning-based).

These two Mandarin layers are distinct outputs with different generation
logic and must not be conflated: semantic Chinese translation can be
derived from the English/French meaning (similar to how French may be
generated from English when no existing French is present), whereas
Mandarin homophonic transliteration is generated from the Wylie phonetic
using the lookup-table approach described below. A source document may
contain both side by side (see "Reference structure" below); the user's
language selection determines which of the two (or both, or neither) the
tool produces in its output, independent of which the source happens to
already provide.

The assembly stage takes the user's layer selection as a configuration
input and reflows only the selected layers per verse-unit, in a fixed
display order (Tibetan first, then translations, then transliterations,
or per a user-configurable order if that proves useful later).

## Input format categories (detected at Stage 0)
1. **PECHA_IMAGE** — long/narrow pages, no extractable text layer at all
   (scanned or vector-only from old DTP software). Requires ink-density
   band-detection to locate and crop each Tibetan line.
2. **UNICODE_TEXT** — standard page layout, Tibetan present as real Unicode
   text in a known Tibetan font (e.g. Jomolhari, Microsoft Himalaya, Noto
   Sans Tibetan). Confirmed in practice via the Rigpe Dorje Centre sample
   ("Treasury of Blessings" / "Tashi Chok Gyin Lab Gter Dzöd"), which
   renders genuine Tibetan Unicode throughout. This is the most reliable
   case: Tibetan is extracted directly as text, with no cropping needed,
   since the safety constraint is already satisfied by the source format
   itself.
3. **LEGACY_FONT_TEXT** — standard page layout, but Tibetan-position text is
   actually Latin characters styled with a non-Unicode glyph-mapped font
   (visually Tibetan, textually meaningless if extracted naively). Common in
   older Word/QuarkXPress-produced sadhanas. Confirmed in practice via the
   Medicine Buddha sample. Tibetan-position spans are cropped as images
   using their known bounding boxes (no band-detection needed, since
   position metadata already exists); Roman-script and CJK layers are
   extracted as real text directly.

## Reference structure: the Rigpe Dorje Centre sample
This document (Treasury of Blessings, Rigpe Dorje Centre) is the most
comprehensive available sample and serves as the model for desired *output*
structure, not as a new source-format category — it is itself a
UNICODE_TEXT source. Per verse-unit it carries, in this order: Tibetan
script, Wylie phonetic, then a French semantic translation, an English
semantic translation, a Mandarin homophonic-phonetic line (e.g. "多杰 羌千
帝洛 那诺倘" for "DOR JE CHANG CHEN TI LO NA RO DANG" — sound-matching, not
meaning-based), and a Mandarin semantic-translation line (e.g. "⾦刚总持帝
洛那洛巴" — meaning-based, using the actual translated term). This document
therefore exercises every layer in the configurable output schema at once,
and is the primary fixture for validating full-schema output. Its colophon
(page 20) notes the Chinese translation is drawn from the Larung Gar
liturgical collection, compiled/translated by Khenpo Sodargye — a named,
citable, high-authority source worth treating as a primary candidate for
seeding both Mandarin lookup tables (see below), if that corpus is
accessible.

## Pipeline stages
0. **Format detection** — classify document/page into one of the three
   input categories above; this determines how every later stage behaves.
1. **Layout segmentation** — locate verse-unit boundaries; for PECHA_IMAGE,
   run ink-density band detection; for the other two, use embedded span
   position metadata.
2. **Tibetan acquisition** — for PECHA_IMAGE and LEGACY_FONT_TEXT, crop
   Tibetan-script regions as images per the method appropriate to the
   detected format; for UNICODE_TEXT, extract as Unicode text directly.
3. **Roman/CJK-layer extraction or transcription** — extract Wylie/
   English/French/Mandarin (both semantic and homophonic lines, where
   present) as text directly when a real text layer exists; vision-
   transcribe only when it doesn't.
4. **Translation resolution** — for each user-selected translation layer
   (English/French/Mandarin-semantic), check for an existing,
   independently-authored translation in the source first; only generate
   a translation when none is present for that language. Generation is
   derived from whichever existing semantic layer is most authoritative
   for that source (typically English), not re-derived from Tibetan.
5. **Homophonic transliteration resolution** — for each user-selected
   homophonic layer (Wylie/English-phonetic, Mandarin-homophonic): extract
   if present in the source; generate if not. Mandarin homophonic
   generation is lookup-table-first (layer 1: established mantra syllables;
   layer 2: common liturgical terms outside mantras), falling back to a
   flagged "novel — needs human review" output for anything not in the
   tables. Never silently auto-generates a mapping for unestablished
   syllables.
6. **Assembly** — reflow the user-selected layers into the target docx
   format, Tibetan always first.

## Human-in-the-loop checkpoints
- **100% review**: all mantra syllables, all "novel" Mandarin
  transliteration outputs (no established convention to fall back on).
- **Spot-check / flagged-only review**: non-mantra Roman-script
  transcription (when vision-transcribed from images), generated
  translation quality (French/English/Chinese-semantic, whichever is
  generated rather than extracted).
- Review happens via Copilot Chat-assisted prompts the pipeline generates,
  not unattended API calls — this keeps a deliberate human decision point at
  every step that touches doctrinal or phonetic accuracy.

## Mandarin transliteration lookup table
Two-layer structure stored in `data/mantra_syllables_zh.json` (layer 1) and
`data/liturgical_terms_zh.json` (layer 2). Each entry should carry a
`source` field documenting where the mapping came from (a specific
published Chinese sadhana, a glossary, a lineage center's convention) —
there is no single canonical master list, so traceability per entry matters
more than completeness. Candidate primary source: Khenpo Sodargye /
Larung Gar liturgical Chinese translations, per the Rigpe Dorje Centre
sample's colophon, if that corpus is accessible. `data/glossary_sources.md`
tracks reference sources used. Note this table is strictly for the
homophonic layer; it must not be used to populate or validate the separate
Mandarin semantic-translation layer, which follows ordinary translation
logic instead.

## Resumability
Per-verse-unit state tracked in a manifest (`segmented` → `layers_extracted`
→ `translations_resolved` → `transliterations_resolved` → `reviewed` →
`assembled`), persisted as JSON so interrupted runs on long documents don't
require restarting from scratch.