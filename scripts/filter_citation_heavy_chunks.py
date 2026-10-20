"""Preprocess chunks to classify and tag citation-heavy survey paragraphs vs substantive content."""

import json
import os
import re
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LANDMARK_CASES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CHUNKS_FILE = os.path.join(BASE_DIR, "data", "chunks", "all_chunks.json")

# Citation regex patterns
CASE_PATTERN = re.compile(
    r'\b[A-Z][a-zA-Z0-9&\s\.\-\']{1,40}\s+(?:v\.|vs\.|versus|v/s|VS\.|V\.)\s+[A-Z][a-zA-Z0-9&\s\.\-\']{1,40}\b',
    re.IGNORECASE
)
AIR_PATTERN = re.compile(r'\bAIR\s*(?:ONLINE)?\s*\d{4}\s*[A-Z\s]*\s*\d+\b', re.IGNORECASE)
SCC_PATTERN = re.compile(r'\(\d{4}\)\s*\d+\s*SCC\s*\d+', re.IGNORECASE)


def classify_chunk(text: str, case_key: str, word_count: int) -> dict:
    # 1. Match all case-citation patterns
    case_matches = CASE_PATTERN.findall(text)
    air_matches = AIR_PATTERN.findall(text)
    scc_matches = SCC_PATTERN.findall(text)

    # 2. Extract self case keywords to avoid matching self-citations
    self_keywords = set()
    if case_key in LANDMARK_CASES:
        name_lower = LANDMARK_CASES[case_key]["name"].lower()
        self_keywords = set(re.findall(r'\b[a-z]{3,}\b', name_lower)) - {
            "vs", "versus", "limited", "pvt", "ltd", "and", "or", "anr", "ors"
        }

    # 3. Count distinct other case names referenced
    distinct_other_cases = set()
    for match in case_matches:
        match_clean = " ".join(match.split()).lower()
        match_words = set(re.findall(r'\b[a-z]{3,}\b', match_clean))
        overlap = match_words.intersection(self_keywords)
        
        # If match has minimal keyword overlap with self name, count it as "other case"
        if len(overlap) < 2:
            distinct_other_cases.add(match_clean)

    num_other_citations = len(distinct_other_cases)

    # 4. Calculate citation density (distinct other-case citations per 500 words)
    if word_count > 0:
        citation_density = num_other_citations / (word_count / 500.0)
    else:
        citation_density = 0.0

    # 5. Flag as citation_survey if density >= 3.0 (i.e. 3+ citations per 500 words)
    chunk_type = "citation_survey" if (citation_density >= 3.0) else "substantive"

    return {
        "pattern_occurrences": len(case_matches) + len(air_matches) + len(scc_matches),
        "distinct_other_citations": num_other_citations,
        "citation_density": round(citation_density, 4),
        "chunk_type": chunk_type,
        "distinct_other_cases": sorted(list(distinct_other_cases))
    }


def annotate_chunks_file(chunks_file_path: str = DEFAULT_CHUNKS_FILE):
    if not os.path.exists(chunks_file_path):
        print(f"Error: Chunks file not found at {chunks_file_path}")
        return

    with open(chunks_file_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Filtering {len(chunks)} chunks from {chunks_file_path}...")

    case_stats = {}
    annotated_chunks = []

    for chunk in chunks:
        case_key = chunk.get("case_key", "unknown")
        word_count = chunk.get("word_count", 0)
        if not word_count:
            word_count = len(chunk["text"].split())

        cls_info = classify_chunk(chunk["text"], case_key, word_count)
        
        # Merge classification info into chunk entry
        chunk_entry = chunk.copy()
        chunk_entry["chunk_type"] = cls_info["chunk_type"]
        chunk_entry["citation_density"] = cls_info["citation_density"]
        chunk_entry["distinct_other_citations"] = cls_info["distinct_other_citations"]
        
        annotated_chunks.append(chunk_entry)

        # Track stats
        if case_key not in case_stats:
            case_stats[case_key] = {"citation_survey": 0, "substantive": 0}
        case_stats[case_key][cls_info["chunk_type"]] += 1

    # Overwrite file with annotated chunks
    with open(chunks_file_path, "w", encoding="utf-8") as f:
        json.dump(annotated_chunks, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("CITATION DENSITY CLASSIFICATION RESULTS")
    print("=" * 60)
    print(f"{'Case Key / ID':<25} | {'Substantive':<12} | {'Citation Survey':<15}")
    print("-" * 60)
    for c_key in sorted(case_stats.keys()):
        stats = case_stats[c_key]
        print(f"{c_key:<25} | {stats['substantive']:<12} | {stats['citation_survey']:<15}")
    print("=" * 60)

    # Specific validate print for target cases
    print("\nValidation of target pathology cases:")
    for target in ["hms_mauritz", "marico_parachute"]:
        if target in case_stats:
            stats = case_stats[target]
            total = stats['substantive'] + stats['citation_survey']
            survey_pct = (stats['citation_survey'] / total * 100) if total > 0 else 0
            print(f"  {target:<16} : {stats['citation_survey']}/{total} chunks flagged as citation_survey ({survey_pct:.1f}%)")


if __name__ == "__main__":
    annotate_chunks_file()
