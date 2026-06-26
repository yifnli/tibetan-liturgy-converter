# scripts/mb_novel_tokens.py
# Diagnostic: surface all novel_needs_review unresolved tokens from the
# Medicine Buddha sadhana run, sorted by frequency.
import sys
sys.path.insert(0, ".")

from src.run_pipeline import run
from collections import Counter

summary = run(
    pdf_path="samples/medicine-buddha-sample/Medicine-Buddha-Tib-Fr-Eng-WORD.pdf",
    out_docx="output/mb_with_tables.docx",
    requested_layers={"wylie", "mandarin_homophonic"},
    layer_order=["wylie", "mandarin_homophonic"],
    debug=True,
)

novel_gaps = [g for g in summary["gaps"] if g["status"] == "novel_needs_review"]
print(f"Total novel gaps: {len(novel_gaps)}")

# Collect all unresolved tokens across all gaps
all_tokens = []
for g in novel_gaps:
    all_tokens.extend(g.get("unresolved_tokens", []))

counter = Counter(all_tokens)
print(f"\nUnique unresolved tokens: {len(counter)}")
print("\nAll unresolved tokens (sorted by frequency):")
for token, count in counter.most_common():
    print(f"  {count:3d}x  {token!r}")
