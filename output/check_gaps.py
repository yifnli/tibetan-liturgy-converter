"""Step 4 verification — check gap counts after seeding mantra table."""
import sys
sys.path.insert(0, ".")

from src.run_pipeline import run

summary = run(
    pdf_path="samples/rigpe-dorje-treasury-of-blessings/treasury-of-blessing-Tib-Fr-Eng-Ch.pdf",
    out_docx="output/rd_with_tables.docx",
    requested_layers={"wylie", "mandarin_homophonic"},
    layer_order=["wylie", "mandarin_homophonic"],
)

novel     = [g for g in summary["gaps"] if g["status"] == "novel_needs_review"]
no_src    = [g for g in summary["gaps"] if g["status"] == "no_source_available"]
assembled = [g for g in summary["gaps"] if g["status"] == "needs_generation"]

print(f"Total gaps:           {len(summary['gaps'])}")
print(f"novel_needs_review:   {len(novel)}")
print(f"no_source_available:  {len(no_src)}")
print(f"needs_generation:     {len(assembled)}")

if novel:
    print("\nFirst 5 novel gaps:")
    for g in novel[:5]:
        print(f"  verse_ref={g['verse_ref']}  unresolved={g.get('unresolved_tokens')}")
