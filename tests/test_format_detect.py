# tests/test_format_detect.py
import sys
sys.path.insert(0, "src")
from src.format_detect import classify_document

def test_medicine_buddha_legacy_font_sample():
    result = classify_document("samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf")
    page_2_spans = result["pages"][1]["spans"]
    classifications = {s["classification"] for s in page_2_spans}
    assert "TIBETAN_LEGACY_FONT" in classifications
    assert "ROMAN_TEXT" in classifications

def test_rigpe_dorje_unicode_and_cjk_sample():
    result = classify_document("samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf")
    page_3_spans = result["pages"][2]["spans"]  # 0-indexed, page 3 has the Vajradhara prayer with all layers
    classifications = {s["classification"] for s in page_3_spans}
    assert "TIBETAN_UNICODE" in classifications
    assert "ROMAN_TEXT" in classifications
    assert "CJK_TEXT" in classifications
    # ensure no legacy-font false positive on a page with no legacy font at all
    assert "TIBETAN_LEGACY_FONT" not in classifications