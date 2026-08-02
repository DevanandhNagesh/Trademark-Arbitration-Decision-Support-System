"""prepare_training_data.py — Build a labelled training dataset for DisputeClassifier.

Sources
-------
1. All ``tests/test_cases/scenario_*.json`` files (19 formal scenarios).
2. An optional directory of informal fact-pattern text files (``--extra-dir``).
3. An optional hand-crafted supplemental JSON file (``--supplement``).

Output
------
A single JSON file (default: ``data/training/dispute_training_data.json``) that
is a JSON array of::

    [
        {
            "dispute_description": "<free-text>",
            "dispute_type": "<canonical_label>",
            "source": "<filename>"
        },
        ...
    ]

Category adequacy check
-----------------------
After building the dataset the script checks every category in
``DISPUTE_LABELS`` and **flags** any that has fewer than 5 examples —
these are insufficient for reliable SVM training.  The check is also
printed as a summary table.

Usage examples
--------------
# Prepare using only the built-in scenarios:
    python scripts/prepare_training_data.py

# Also include informal .txt fact-patterns in a directory:
    python scripts/prepare_training_data.py --extra-dir data/raw/fact_patterns

# Write output to a custom path:
    python scripts/prepare_training_data.py --output data/my_training.json

# Add a hand-crafted supplemental file:
    python scripts/prepare_training_data.py --supplement data/extra_labels.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Resolve project root so we can import project modules when run directly
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from logging_config import logger  # noqa: E402

# ---------------------------------------------------------------------------
# Canonical labels and aliases (mirrors dispute_classifier.py)
# ---------------------------------------------------------------------------

DISPUTE_LABELS: List[str] = [
    "infringement",
    "brand_similarity",
    "passing_off",
    "assignment",
    "licensing",
]

#: Minimum examples per class for reliable SVM training
MIN_EXAMPLES_PER_CLASS: int = 5

_LABEL_ALIASES: Dict[str, str] = {
    # Multi-word scenario JSON values
    "trademark infringement": "infringement",
    "brand similarity": "brand_similarity",
    "passing off": "passing_off",
    "assignment dispute": "assignment",
    "trademark assignment": "assignment",
    "license dispute": "licensing",
    "licence dispute": "licensing",
    "licensing dispute": "licensing",
    # Single-word / underscored (already canonical)
    "passing_off": "passing_off",
    "brand_similarity": "brand_similarity",
    "assignment": "assignment",
    "licensing": "licensing",
    "infringement": "infringement",
}


def normalise_label(raw: str) -> str:
    """Map a raw dispute_type string to a canonical DISPUTE_LABELS entry."""
    cleaned = raw.strip().lower()
    if cleaned in _LABEL_ALIASES:
        return _LABEL_ALIASES[cleaned]
    underscored = cleaned.replace(" ", "_")
    if underscored in _LABEL_ALIASES:
        return _LABEL_ALIASES[underscored]
    if underscored in DISPUTE_LABELS:
        return underscored
    # Unknown label — return as-is (will trigger a warning downstream)
    return underscored


# ---------------------------------------------------------------------------
# Source 1: formal scenario JSON files
# ---------------------------------------------------------------------------

def load_scenario_jsons(scenarios_dir: str) -> List[Dict]:
    """Parse all scenario_*.json files and extract (description, label) pairs.

    Parameters
    ----------
    scenarios_dir:
        Path to the directory containing scenario_1.json … scenario_N.json.

    Returns
    -------
    List of training dicts with keys dispute_description, dispute_type, source.
    """
    records: List[Dict] = []
    if not os.path.isdir(scenarios_dir):
        logger.warning("Scenarios directory not found: %s — skipping.", scenarios_dir)
        return records

    json_files = sorted(
        f for f in os.listdir(scenarios_dir)
        if f.startswith("scenario_") and f.endswith(".json")
    )
    logger.info(
        "Found %d scenario JSON files in %s.", len(json_files), scenarios_dir
    )

    for fname in json_files:
        fpath = os.path.join(scenarios_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not parse %s: %s — skipping.", fname, exc)
            continue

        description = (data.get("dispute_description") or "").strip()
        raw_label = (data.get("dispute_type") or "").strip()

        if not description:
            logger.warning("%s has no dispute_description — skipping.", fname)
            continue
        if not raw_label:
            logger.warning("%s has no dispute_type — skipping.", fname)
            continue

        normalised = normalise_label(raw_label)
        if normalised not in DISPUTE_LABELS:
            logger.warning(
                "%s has unrecognised dispute_type %r (normalised: %r) — "
                "including but flagging.",
                fname, raw_label, normalised,
            )

        records.append({
            "dispute_description": description,
            "dispute_type": normalised,
            "source": fname,
            "_raw_label": raw_label,  # kept for audit; stripped before output
        })

    return records


# ---------------------------------------------------------------------------
# Source 2: informal fact-pattern text files (optional)
# ---------------------------------------------------------------------------

def load_extra_txt_patterns(extra_dir: str) -> List[Dict]:
    """Load informal fact-pattern .txt files from *extra_dir*.

    File naming convention::

        <label>_<anything>.txt

    e.g. ``passing_off_01.txt``, ``licensing_franchise_case.txt``.

    The first segment (before the first underscore that is followed by a
    non-label character) is used as the label.  If the filename prefix does not
    match a canonical label the user is warned and the file is still included
    so manual review can correct it.

    Parameters
    ----------
    extra_dir:
        Directory to scan for ``*.txt`` files.

    Returns
    -------
    List of training dicts.
    """
    records: List[Dict] = []
    if not extra_dir:
        return records
    if not os.path.isdir(extra_dir):
        logger.warning("Extra directory not found: %s — skipping.", extra_dir)
        return records

    txt_files = sorted(f for f in os.listdir(extra_dir) if f.endswith(".txt"))
    logger.info(
        "Found %d .txt fact-pattern files in %s.", len(txt_files), extra_dir
    )

    for fname in txt_files:
        fpath = os.path.join(extra_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as fh:
                text = fh.read().strip()
        except OSError as exc:
            logger.warning("Could not read %s: %s — skipping.", fname, exc)
            continue

        if not text:
            logger.warning("%s is empty — skipping.", fname)
            continue

        # Infer label from filename prefix
        stem = os.path.splitext(fname)[0]
        raw_label = stem.split("_")[0]
        label = normalise_label(raw_label)
        if label not in DISPUTE_LABELS:
            logger.warning(
                "Could not infer a canonical label from filename %r "
                "(derived: %r).  Please rename to start with one of %s.",
                fname, label, DISPUTE_LABELS,
            )

        records.append({
            "dispute_description": text,
            "dispute_type": label,
            "source": fname,
            "_raw_label": raw_label,
        })

    return records


# ---------------------------------------------------------------------------
# Source 3: supplemental hand-crafted JSON (optional)
# ---------------------------------------------------------------------------

def load_supplement_json(supplement_path: str) -> List[Dict]:
    """Load additional labelled examples from a JSON file.

    The file should be a JSON array of objects with at minimum the keys
    ``dispute_description`` and ``dispute_type``.

    Parameters
    ----------
    supplement_path:
        Path to a supplemental JSON file.
    """
    records: List[Dict] = []
    if not supplement_path:
        return records
    if not os.path.isfile(supplement_path):
        logger.warning("Supplement file not found: %s — skipping.", supplement_path)
        return records

    with open(supplement_path, encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict):
        data = data.get("items", data.get("data", list(data.values())[0]))

    for idx, item in enumerate(data):
        desc = (item.get("dispute_description") or "").strip()
        raw_label = (item.get("dispute_type") or "").strip()
        if not desc or not raw_label:
            logger.warning(
                "Supplement item %d missing description or label — skipping.", idx
            )
            continue
        label = normalise_label(raw_label)
        records.append({
            "dispute_description": desc,
            "dispute_type": label,
            "source": os.path.basename(supplement_path),
            "_raw_label": raw_label,
        })

    logger.info("Loaded %d examples from supplement %s.", len(records), supplement_path)
    return records


# ---------------------------------------------------------------------------
# Adequacy check
# ---------------------------------------------------------------------------

def check_class_adequacy(
    records: List[Dict],
    min_examples: int = MIN_EXAMPLES_PER_CLASS,
) -> Dict[str, int]:
    """Check whether each DISPUTE_LABEL has enough training examples.

    Prints a formatted summary table and returns a dict mapping each label to
    its count.  Labels with fewer than *min_examples* are flagged with a
    WARNING log entry.

    Parameters
    ----------
    records:
        Finalised training records (each must have a ``dispute_type`` key).
    min_examples:
        Minimum count threshold for a class to be considered training-ready.

    Returns
    -------
    dict mapping label → count (includes 0 for absent labels).
    """
    counts: Counter = Counter(r["dispute_type"] for r in records)

    # Report on all canonical labels + any extra labels present
    all_labels = sorted(set(DISPUTE_LABELS) | set(counts.keys()))
    label_counts = {label: counts.get(label, 0) for label in all_labels}

    print("\n" + "=" * 60)
    print("TRAINING DATA — CLASS ADEQUACY REPORT")
    print(f"Minimum required examples per class: {min_examples}")
    print("=" * 60)
    print(f"{'Label':<22} {'Count':>6}  {'Status'}")
    print("-" * 60)

    has_warnings = False
    for label in all_labels:
        count = label_counts[label]
        if label not in DISPUTE_LABELS:
            status = "[!] UNKNOWN LABEL"
            has_warnings = True
        elif count < min_examples:
            status = f"[!] INSUFFICIENT (need {min_examples - count} more)"
            has_warnings = True
        else:
            status = "[OK]"
        print(f"  {label:<20} {count:>6}  {status}")

    print("-" * 60)
    print(f"  {'TOTAL':<20} {sum(label_counts.values()):>6}")
    print("=" * 60)

    if has_warnings:
        logger.warning(
            "One or more classes have insufficient training data.  "
            "Consider augmenting with more examples or merging rare classes "
            "before training the SVM."
        )
        print(
            "\n[!] WARNING: Categories flagged above have fewer than "
            f"{min_examples} examples and may cause unreliable classification.\n"
            "   Options:\n"
            "   - Add more examples via --supplement or --extra-dir\n"
            "   - Merge rare classes (e.g. 'assignment' + 'trademark' -> 'other')\n"
            "   - Use cross-validation only (no held-out test split)\n"
        )
    else:
        print("\n[OK] All classes meet the minimum training data requirement.\n")

    return label_counts


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(records: List[Dict]) -> List[Dict]:
    """Remove duplicate records by (dispute_description, dispute_type) pair.

    Keeps the first occurrence.  Logs the number of duplicates removed.
    """
    seen = set()
    unique: List[Dict] = []
    duplicates = 0
    for rec in records:
        key = (rec["dispute_description"].strip().lower(), rec["dispute_type"])
        if key in seen:
            duplicates += 1
            logger.debug(
                "Duplicate removed (source=%s, label=%s).",
                rec.get("source"), rec.get("dispute_type"),
            )
        else:
            seen.add(key)
            unique.append(rec)
    if duplicates:
        logger.info("Removed %d duplicate records.", duplicates)
    return unique


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare {dispute_description, dispute_type} training data from "
            "scenario JSON files and optional extra sources."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scenarios-dir",
        default=os.path.join(_REPO_ROOT, "tests", "test_cases"),
        metavar="DIR",
        help="Directory containing scenario_*.json files.",
    )
    parser.add_argument(
        "--extra-dir",
        default=None,
        metavar="DIR",
        help=(
            "Optional directory of informal fact-pattern .txt files. "
            "Filename must start with the canonical label prefix, e.g. "
            "'passing_off_01.txt'."
        ),
    )
    parser.add_argument(
        "--supplement",
        default=None,
        metavar="PATH",
        help=(
            "Optional hand-crafted supplemental JSON file (array of "
            "{dispute_description, dispute_type} objects)."
        ),
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(_REPO_ROOT, "data", "training", "dispute_training_data.json"),
        metavar="PATH",
        help="Output path for the prepared training JSON.",
    )
    parser.add_argument(
        "--min-examples",
        type=int,
        default=MIN_EXAMPLES_PER_CLASS,
        metavar="INT",
        help="Minimum examples per class to flag as training-ready.",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Skip deduplication of identical descriptions.",
    )
    args = parser.parse_args(argv)

    # ---- Collect all records -----------------------------------------------
    records: List[Dict] = []

    scenario_records = load_scenario_jsons(args.scenarios_dir)
    records.extend(scenario_records)
    logger.info("Loaded %d records from scenario JSONs.", len(scenario_records))

    if args.extra_dir:
        extra_records = load_extra_txt_patterns(args.extra_dir)
        records.extend(extra_records)
        logger.info("Loaded %d records from extra .txt files.", len(extra_records))

    if args.supplement:
        supplement_records = load_supplement_json(args.supplement)
        records.extend(supplement_records)

    if not records:
        raise SystemExit(
            "ERROR: No training records collected. "
            "Check --scenarios-dir and ensure scenario JSON files exist."
        )

    # ---- Deduplicate -------------------------------------------------------
    if not args.no_dedup:
        records = deduplicate(records)

    # ---- Clean internal audit fields before writing ------------------------
    output_records = [
        {
            "dispute_description": r["dispute_description"],
            "dispute_type": r["dispute_type"],
            "source": r.get("source", "unknown"),
        }
        for r in records
    ]

    # ---- Adequacy check ----------------------------------------------------
    check_class_adequacy(output_records, min_examples=args.min_examples)

    # ---- Write output -------------------------------------------------------
    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(output_records, fh, indent=2, ensure_ascii=False)

    logger.info(
        "Wrote %d training records to %s", len(output_records), args.output
    )
    print(f"\nOutput written to: {args.output}")
    print(f"Total records    : {len(output_records)}")
    print(
        "\nNext step — train the classifier:\n"
        f"  python agents/dispute_classifier.py "
        f"--data {args.output} "
        f"--save models/dispute_classifier.joblib\n"
    )


if __name__ == "__main__":
    main()
