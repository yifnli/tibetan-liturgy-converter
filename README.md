# tibetan-liturgy-converter

A Python pipeline for converting Tibetan Buddhist liturgical texts (sādhanas, prayer books) into multi-layer reference documents. Given a source PDF — whether it uses Unicode Tibetan, legacy glyph-mapped fonts, or scanned images — the pipeline extracts or crops the Tibetan, identifies translation and transliteration layers, resolves gaps via lookup tables, and assembles a `.docx` output with the user's chosen combination of layers.

## What it does

Each verse-unit in the output document contains the layers you select, in a fixed display order:

1. Tibetan script (Unicode text or inline image, depending on source format)
2. Wylie phonetic transliteration
3. French semantic translation
4. English semantic translation
5. Mandarin homophonic transliteration
6. Mandarin semantic translation

Layers present in the source are extracted directly. Layers absent from the source produce a placeholder note in the output (`[NEEDS GENERATION]`, `[NOVEL — HUMAN REVIEW REQUIRED]`, or `[NO SOURCE AVAILABLE]`) so gaps are always visible rather than silently omitted.

## Supported source formats

| Format | Tibetan extraction | Text layers |
|---|---|---|
| `UNICODE_TEXT` | Unicode passthrough | Full extraction |
| `LEGACY_FONT_TEXT` | Cropped as PNG images | Roman + CJK extraction |

## Sample PDFs

Two reference samples are included under `samples/`:

- **Rigpe Dorje Treasury of Blessings** (`UNICODE_TEXT`) — Śākyamuni practice, trilingual (Tibetan / French / English / Mandarin), published by Rigpe Dorje Centre, Montréal
- **Medicine Buddha Sādhana** (`LEGACY_FONT_TEXT`) — Menla practice, quadrilingual (Tibetan / French / English / Wylie phonetic), legacy font format

## Installation

```bash
git clone https://github.com/yifnli/tibetan-liturgy-converter
cd tibetan-liturgy-converter
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Requires Python 3.10+. Key dependencies: `pymupdf`, `python-docx`.

## Usage

```python
from src.run_pipeline import run

summary = run(
    pdf_path="samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
    out_docx="output/treasury_of_blessings.docx",
    requested_layers={"wylie", "french", "english", "mandarin_homophonic", "mandarin_semantic"},
)

print(f"Verses: {summary['verse_count']}, Gaps: {summary['gap_count']}")
```

Output layer selection is a Python `set` — include only the layers you want. Tibetan is always included regardless of selection.

## Lookup tables

Mandarin homophonic transliteration uses a two-layer lookup table:

- `data/mantra_syllables_zh.json` — established mantra syllable mappings (layer 1)
- `data/liturgical_terms_zh.json` — common liturgical terms (layer 2)

Each entry carries a `source` field citing the specific published text the mapping comes from. Entries without a traceable source are not added. The tables are currently seeded with 8 entries from the Kagyü lineage prayer; Medicine Buddha entries are in progress using the *Kagyu Monlam Book* (噶舉大祈願法會課誦本, 17th Karmapa Ogyen Trinley Dorje, 2020) as the reference.

## Running tests

```bash
python -m pytest        # not bare pytest — required by IT policy
```

142 tests across 9 modules. All tests use real span data extracted from the sample PDFs rather than hand-constructed fixtures.

## Project structure

```
src/
  format_detect.py        # classify PDF spans by script type
  crop_tibetan.py         # crop legacy-font Tibetan spans as PNG
  extract_text_layers.py  # extract 7-layer dict from verse-unit spans
  layout_segment.py       # segment page spans into verse-unit dicts
  verse_pipeline.py       # route verse-units to UNICODE or LEGACY path
  translation_resolve.py  # pass-through or gap-record for translation layers
  homophonic_resolve.py   # longest-match Wylie lookup + novel flagging
  assembly.py             # build python-docx Document from verse results
  run_pipeline.py         # end-to-end entry point
data/
  mantra_syllables_zh.json
  liturgical_terms_zh.json
samples/
output/                   # generated .docx files (not tracked)
```

## Design principles

**Human in the loop at every doctrinally sensitive step.** The pipeline never silently auto-generates Mandarin phonetic mappings for unestablished syllables. Novel tokens produce a flagged placeholder; a human authors the correct mapping and adds it to the lookup table with a source citation.

**Real data, not assumed shapes.** Every test fixture is extracted from an actual sample PDF. No hand-constructed span dicts or synthetic page layouts.

**Format-agnostic output contract.** Both source formats produce the same 8-key dict per verse-unit, so all downstream stages are format-blind.

## Status

| Stage | Module | Tests |
|---|---|---|
| Format detection | `format_detect.py` | ✅ |
| Tibetan cropping | `crop_tibetan.py` | ✅ |
| Text layer extraction | `extract_text_layers.py` | ✅ |
| Layout segmentation | `layout_segment.py` | ✅ |
| Verse routing | `verse_pipeline.py` | ✅ |
| Translation resolution | `translation_resolve.py` | ✅ |
| Homophonic resolution | `homophonic_resolve.py` | ✅ |
| Assembly | `assembly.py` | ✅ |
| Lookup table population | `data/*.json` | 🔄 in progress |
