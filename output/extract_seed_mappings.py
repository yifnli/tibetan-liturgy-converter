"""Temporary extraction script — Step 2 seed mapping discovery."""
import sys
sys.path.insert(0, ".")

from src.run_pipeline import run
from src.homophonic_resolve import _tokenize_wylie

summary = run(
    pdf_path="samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
    out_docx="output/rd_debug.docx",
    requested_layers={"wylie", "mandarin_homophonic"},
    layer_order=["wylie", "mandarin_homophonic"],
    debug=True,
)

print(f"verse_count : {summary['verse_count']}")
print(f"gap_count   : {summary['gap_count']}")
print()

# ── Print all raw verse-result pairs first ──────────────────────────────────
print("=" * 70)
print("RAW VERSE RESULTS (wylie + mandarin_homophonic where both present)")
print("=" * 70)
for i, vr in enumerate(summary["verse_results"]):
    homo  = vr.get("mandarin_homophonic")
    wylie = vr.get("wylie")
    if homo is None or wylie is None:
        continue
    print(f"\n[verse {i}]")
    print(f"  wylie : {wylie!r}")
    print(f"  homo  : {homo!r}")

# ── Attempt one-to-one token-level alignment ─────────────────────────────────
print()
print("=" * 70)
print("ONE-TO-ONE ALIGNMENT ATTEMPT (mismatches printed as MISMATCH)")
print("=" * 70)

mappings: dict[str, str] = {}
for i, vr in enumerate(summary["verse_results"]):
    homo  = vr.get("mandarin_homophonic")
    wylie = vr.get("wylie")
    if homo is None or wylie is None:
        continue

    tokens    = _tokenize_wylie(wylie)
    zh_groups = homo.split(" ")

    if len(tokens) != len(zh_groups):
        print(
            f"MISMATCH [verse {i}]:"
            f"\n  tokens ({len(tokens)}) : {tokens}"
            f"\n  zh     ({len(zh_groups)}) : {zh_groups}"
        )
        continue

    for token, zh in zip(tokens, zh_groups):
        if token not in mappings:
            mappings[token] = zh
        elif mappings[token] != zh:
            print(f"CONFLICT: {token!r} maps to both {mappings[token]!r} and {zh!r}")

print(f"\nUnique single-token mappings found: {len(mappings)}")
for wylie_tok, zh in sorted(mappings.items()):
    print(f"  {wylie_tok!r}: {zh!r}")
