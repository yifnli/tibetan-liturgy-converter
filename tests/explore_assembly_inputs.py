"""Step 3: build full assembly input for two verse-units."""
import sys, pprint, copy, tempfile
sys.path.insert(0, ".")
sys.path.insert(0, "src")

import fitz
from format_detect import classify_document
from layout_segment import segment_page_spans
from verse_pipeline import process_verse_unit
from translation_resolve import resolve_translation_layers
from homophonic_resolve import resolve_homophonic_layers

_RD_PDF = "samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf"
_MB_PDF = "samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf"

# SYNTHETIC_TABLE — copied verbatim from tests/test_homophonic_resolve.py
SYNTHETIC_TABLE = {
    "DOR JE":     {"zh": "多杰",   "source": "test"},
    "CHANG CHEN": {"zh": "羌千",   "source": "test"},
    "TI LO":      {"zh": "帝洛",   "source": "test"},
    "NA RO DANG": {"zh": "那诺倘", "source": "test"},
    "MAR PA":     {"zh": "玛巴",   "source": "test"},
    "MI LA":      {"zh": "⽶拉",   "source": "test"},
    "CHÖ JE":     {"zh": "却戒",   "source": "test"},
    "GAM PO PA":  {"zh": "冈波巴", "source": "test"},
}

REQUESTED_TRANSLATION  = {"english", "french", "mandarin_semantic"}
REQUESTED_HOMOPHONIC   = {"wylie", "mandarin_homophonic"}
tmpdir = tempfile.mkdtemp()

def run_full_pipeline(pdf_path, page_idx, verse_idx, label):
    doc = classify_document(pdf_path)
    pdf_doc = fitz.open(pdf_path)
    page_spans = doc["pages"][page_idx]["spans"]
    verses = segment_page_spans(page_spans, page_index=page_idx)
    vu = verses[verse_idx]

    verse_result = process_verse_unit(vu, doc["format"], pdf_doc, tmpdir)

    t_out  = resolve_translation_layers(verse_result, vu, REQUESTED_TRANSLATION)
    h_out  = resolve_homophonic_layers(
        verse_result, vu, REQUESTED_HOMOPHONIC, SYNTHETIC_TABLE, {}
    )

    # Build the combined assembly input
    assembly_input = {
        # Tibetan layers from verse_pipeline
        "tibetan_unicode":     verse_result["tibetan_unicode"],
        "tibetan_image_paths": verse_result["tibetan_image_paths"],
        # Resolved text layers
        "layers": {**t_out["layers"], **h_out["layers"]},
        # Combined gap list from both resolve stages
        "gaps":   t_out["gaps"] + h_out["gaps"],
        # Provenance
        "verse_ref": {"page_index": vu["page_index"], "verse_index": vu["verse_index"]},
        "doc_format": doc["format"],
    }

    print("=" * 70)
    print(f"ASSEMBLY INPUT: {label}")
    print("=" * 70)
    pprint.pprint(assembly_input)
    print()
    print(f"  tibetan_unicode present:     {assembly_input['tibetan_unicode'] is not None}")
    print(f"  tibetan_image_paths count:   {len(assembly_input['tibetan_image_paths'])}")
    print(f"  layers keys:                 {sorted(assembly_input['layers'].keys())}")
    print(f"  gaps count:                  {len(assembly_input['gaps'])}")
    for g in assembly_input["gaps"]:
        print(f"    gap: layer={g['layer']:22s} status={g['status']}")
    print()
    pdf_doc.close()

run_full_pipeline(_RD_PDF, 2, 0, "Rigpe Dorje page 2 verse 0 (UNICODE_TEXT, all layers)")
run_full_pipeline(_MB_PDF, 1, 0, "Medicine Buddha page 1 verse 0 (LEGACY_FONT_TEXT)")
