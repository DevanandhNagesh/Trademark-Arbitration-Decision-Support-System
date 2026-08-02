"""Smoke test for _detect_dispute_type_hybrid across all 5 dispute categories."""
import sys
sys.path.insert(0, ".")

from agents.landmark_retrieval_agent import (
    _detect_dispute_type,
    _detect_dispute_type_hybrid,
)

CASES = [
    {
        "desc":     "Bikaji Foods is the registered owner of BIKAJI. Bikano Snacks started selling"
                    " snacks under a deceptively similar mark without authorisation.",
        "label":    "Trademark Infringement",
        "expected": "infringement",
    },
    {
        "desc":     "BluePeak Roasters licensed the trademark BLUEPEAK under a Trademark License"
                    " Agreement. The joint venture failed to pay royalties and sub-licensed without"
                    " permission.",
        "label":    "License Dispute",
        "expected": "licensing",
    },
    {
        "desc":     "The Coca-Cola Company acquired MAAZA under a Trademark Assignment Agreement."
                    " Bisleri later exported beverages under the same mark claiming the deed was"
                    " territorially limited.",
        "label":    "Assignment Dispute",
        "expected": "assignment",
    },
    {
        "desc":     "Haldiram Snacks has goodwill in the mark HALDIRAMS. Hariram Snacks is"
                    " misrepresenting its bhujia products as those of Haldiram causing consumer"
                    " confusion.",
        "label":    "Passing Off",
        "expected": "passing_off",
    },
    {
        "desc":     "Starbucks owns the circular green mermaid logo. Sardarbuksh has opened coffee"
                    " outlets with a nearly identical green circular logo causing trade dress"
                    " confusion.",
        "label":    "Brand Similarity",
        "expected": "brand_similarity",
    },
    # Vague input — SVM confidence should be low, so dropdown label wins
    {
        "desc":     "They copied my brand.",
        "label":    "Trademark Infringement",
        "expected": "infringement",
    },
    # No dropdown label supplied — hybrid falls back to keyword heuristic
    {
        "desc":     "The distribution agreement expired and the licensee refused to stop using the"
                    " APEX mark.",
        "label":    "",
        "expected": "licensing",
    },
]

print(f"{'Label':<28}  {'Keyword':<18}  {'Hybrid':<18}  {'Expected':<18}  Result")
print("-" * 112)

all_pass = True
for c in CASES:
    kw  = _detect_dispute_type(c["desc"])
    hyb = _detect_dispute_type_hybrid(c["desc"], c["label"])
    ok  = hyb == c["expected"]
    all_pass = all_pass and ok
    status = "PASS" if ok else "FAIL <--"
    lbl = c["label"] if c["label"] else "(no label)"
    print(f"{lbl:<28}  {kw:<18}  {hyb:<18}  {c['expected']:<18}  {status}")

print()
print("All tests PASSED." if all_pass else "Some tests FAILED — check FAIL rows above.")
