"""Dispute type classifier — TF-IDF + Linear SVM, zero LLM calls.

Predicts one of six dispute categories from free-text ``dispute_description``:
    passing_off | assignment | licensing | brand_similarity |
    infringement | trademark

Intended to be trained offline and loaded at runtime by the arbitrability
pipeline.  Wire-in point: replace the regex heuristic in gemini_agents.py
with ``DisputeClassifier.predict(description)`` after validation.

Standalone usage
----------------
Train from a JSON/CSV file and print a full evaluation report::

    python agents/dispute_classifier.py \\
        --data path/to/training_data.json \\
        --save models/dispute_classifier.joblib \\
        [--test-size 0.25] [--random-seed 42]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Project-level imports (resolve from repo root regardless of cwd)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_config import logger  # noqa: E402  (after sys.path patch)

# ---------------------------------------------------------------------------
# sklearn imports (soft-required; raise a clear error if missing)
# ---------------------------------------------------------------------------
try:
    import joblib
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.svm import LinearSVC
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "scikit-learn and joblib are required for DisputeClassifier.\n"
        "Install with:  pip install scikit-learn joblib"
    ) from exc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Canonical label set (5 categories) — keep in sync with the frontend / config
#: wherever dispute_type is used.
#:
#:   infringement    — Trademark Infringement (unauthorised use of a registered mark)
#:   brand_similarity — Brand Similarity / trade-dress confusion without a contract
#:   passing_off     — Passing Off (misrepresentation of goods/services)
#:   assignment      — Assignment Dispute (contested transfer of trademark ownership)
#:   licensing       — Licence / Distribution Dispute (breach of a trademark licence)
DISPUTE_LABELS: List[str] = [
    "infringement",
    "brand_similarity",
    "passing_off",
    "assignment",
    "licensing",
]

#: Normalise human-readable variants from existing scenario JSONs to canonical labels.
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
    # Single-word / underscored variants (already canonical or close)
    "passing_off": "passing_off",
    "brand_similarity": "brand_similarity",
    "assignment": "assignment",
    "licensing": "licensing",
    "infringement": "infringement",
}

#: How many top TF-IDF features to log per class (for the paper method section).
_TOP_FEATURES_PER_CLASS: int = 10


# ---------------------------------------------------------------------------
# Label normalisation helper
# ---------------------------------------------------------------------------

def normalise_label(raw: str) -> str:
    """Normalise a raw dispute_type string to a canonical DISPUTE_LABELS value.

    Applies lower-casing, whitespace collapsing, and alias resolution.
    Returns the raw (lowercased, underscored) value unchanged if no alias
    matches — this lets the classifier learn from novel labels without
    crashing.
    """
    cleaned = raw.strip().lower()
    # Try direct alias lookup first
    if cleaned in _LABEL_ALIASES:
        return _LABEL_ALIASES[cleaned]
    # Underscore variant
    underscored = cleaned.replace(" ", "_")
    if underscored in _LABEL_ALIASES:
        return _LABEL_ALIASES[underscored]
    if underscored in DISPUTE_LABELS:
        return underscored
    return underscored  # Unknown — pass through


# ---------------------------------------------------------------------------
# DisputeClassifier
# ---------------------------------------------------------------------------

class DisputeClassifier:
    """TF-IDF + LinearSVC classifier for trademark dispute categorisation.

    The internal pipeline is::

        TfidfVectorizer(ngram_range=(1,2), min_df=2, stop_words='english')
            -> CalibratedClassifierCV(LinearSVC())   # gives probability scores

    Parameters
    ----------
    top_features_per_class:
        Number of top discriminative TF-IDF features to log per class after
        fitting.  Set to 0 to skip (useful in unit tests).
    """

    def __init__(self, top_features_per_class: int = _TOP_FEATURES_PER_CLASS) -> None:
        self._top_features_per_class = top_features_per_class
        self._pipeline: Optional[Pipeline] = None
        self._classes_: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train(self, training_data: List[Dict]) -> None:
        """Fit the classifier on labelled examples.

        Parameters
        ----------
        training_data:
            List of dicts with keys ``dispute_description`` (str) and
            ``dispute_type`` (str).  Labels are normalised via
            :func:`normalise_label` before fitting.

        Raises
        ------
        ValueError
            If fewer than 2 distinct classes are present after filtering.
        """
        if not training_data:
            raise ValueError("training_data must be a non-empty list.")

        texts: List[str] = []
        labels: List[str] = []
        skipped = 0

        for idx, item in enumerate(training_data):
            desc = (item.get("dispute_description") or "").strip()
            raw_label = (item.get("dispute_type") or "").strip()
            label = normalise_label(raw_label)

            if not desc:
                logger.warning("Skipping item %d — empty dispute_description.", idx)
                skipped += 1
                continue
            if not label:
                logger.warning("Skipping item %d — empty dispute_type.", idx)
                skipped += 1
                continue
            if label not in DISPUTE_LABELS:
                logger.warning(
                    "Item %d has unknown label %r (normalised from %r) — "
                    "keeping it but it is not in DISPUTE_LABELS %s.",
                    idx, label, raw_label, DISPUTE_LABELS,
                )
            texts.append(desc)
            labels.append(label)

        if skipped:
            logger.info("Skipped %d items due to missing fields.", skipped)

        unique_classes = list(set(labels))
        if len(unique_classes) < 2:
            raise ValueError(
                f"Need at least 2 distinct classes, got {len(unique_classes)}: "
                f"{unique_classes}"
            )

        logger.info(
            "Training DisputeClassifier on %d examples across %d classes: %s",
            len(texts), len(unique_classes), sorted(unique_classes),
        )

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            stop_words="english",
            sublinear_tf=True,      # log(1 + tf) — helps with long descriptions
            max_features=50_000,
        )
        # CalibratedClassifierCV wraps LinearSVC to expose predict_proba
        svm = CalibratedClassifierCV(LinearSVC(max_iter=5000, C=1.0), cv=3)

        self._pipeline = Pipeline([
            ("tfidf", vectorizer),
            ("clf", svm),
        ])
        self._pipeline.fit(texts, labels)
        self._classes_ = self._pipeline.named_steps["clf"].classes_

        # ---- Interpretability logging ----------------------------------------
        fitted_vocab = self._pipeline.named_steps["tfidf"].vocabulary_
        logger.info(
            "TF-IDF vocabulary size after fitting: %d tokens.", len(fitted_vocab)
        )
        self._log_top_features()

    def predict(self, description: str) -> Tuple[str, float]:
        """Predict the dispute category for a free-text description.

        Parameters
        ----------
        description:
            Raw ``dispute_description`` text.

        Returns
        -------
        Tuple[str, float]
            ``(predicted_label, confidence_score)`` where confidence is the
            maximum class probability from the calibrated SVM (0–1).

        Raises
        ------
        RuntimeError
            If the classifier has not been trained or loaded yet.
        """
        self._require_fitted()
        if not description or not description.strip():
            logger.warning(
                "predict() called with empty description; defaulting to 'infringement'."
            )
            return ("infringement", 0.0)

        proba = self._pipeline.predict_proba([description.strip()])[0]
        best_idx = int(np.argmax(proba))
        predicted_label: str = self._classes_[best_idx]
        confidence: float = float(proba[best_idx])

        logger.debug(
            "Prediction: label=%r  confidence=%.4f  description_preview=%r",
            predicted_label, confidence, description[:80],
        )
        return (predicted_label, confidence)

    def predict_batch(self, descriptions: List[str]) -> List[Tuple[str, float]]:
        """Vectorised prediction for a list of descriptions.

        Parameters
        ----------
        descriptions:
            List of raw dispute_description strings.

        Returns
        -------
        List[Tuple[str, float]]
            One ``(label, confidence)`` tuple per input.
        """
        self._require_fitted()
        clean = [d.strip() for d in descriptions]
        probas = self._pipeline.predict_proba(clean)
        results: List[Tuple[str, float]] = []
        for proba in probas:
            best_idx = int(np.argmax(proba))
            results.append((self._classes_[best_idx], float(proba[best_idx])))
        return results

    def save(self, path: str) -> None:
        """Persist the fitted pipeline to *path* using joblib.

        Parameters
        ----------
        path:
            Destination file path (e.g. ``models/dispute_classifier.joblib``).

        Raises
        ------
        RuntimeError
            If the classifier has not been trained yet.
        """
        self._require_fitted()
        save_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(save_dir, exist_ok=True)
        payload = {
            "pipeline": self._pipeline,
            "classes_": self._classes_,
            "top_features_per_class": self._top_features_per_class,
        }
        joblib.dump(payload, path, compress=3)
        logger.info("DisputeClassifier saved to %s", path)

    def load(self, path: str) -> "DisputeClassifier":
        """Load a persisted classifier from *path*.

        Returns ``self`` so callers can chain::

            clf = DisputeClassifier().load("models/dispute_classifier.joblib")

        Parameters
        ----------
        path:
            Path to the ``.joblib`` file produced by :meth:`save`.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
        payload = joblib.load(path)
        self._pipeline = payload["pipeline"]
        self._classes_ = payload["classes_"]
        self._top_features_per_class = payload.get(
            "top_features_per_class", _TOP_FEATURES_PER_CLASS
        )
        vocab_size = len(self._pipeline.named_steps["tfidf"].vocabulary_)
        logger.info(
            "DisputeClassifier loaded from %s  (vocab=%d, classes=%s)",
            path, vocab_size, list(self._classes_),
        )
        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_fitted(self) -> None:
        if self._pipeline is None or self._classes_ is None:
            raise RuntimeError(
                "DisputeClassifier is not trained/loaded yet. "
                "Call train() or load() first."
            )

    def _log_top_features(self) -> None:
        """Log the top TF-IDF feature names per class (for the paper method section)."""
        if self._top_features_per_class <= 0:
            return

        vectorizer: TfidfVectorizer = self._pipeline.named_steps["tfidf"]
        clf_cv: CalibratedClassifierCV = self._pipeline.named_steps["clf"]
        feature_names: np.ndarray = np.array(vectorizer.get_feature_names_out())

        # Access the underlying LinearSVC estimator from each calibrated fold,
        # then average coef_ matrices across folds for a stable ranking.
        base_estimators = [
            est.estimator for est in clf_cv.calibrated_classifiers_
        ]
        coef_stack = np.array([est.coef_ for est in base_estimators])
        mean_coef = coef_stack.mean(axis=0)  # shape: (n_classes, n_features)

        for class_idx, class_name in enumerate(clf_cv.classes_):
            if mean_coef.shape[0] == 1:
                # Binary OvR collapses to 1 row — skip multi-class logging
                break
            top_indices = (
                np.argsort(mean_coef[class_idx])
                [-self._top_features_per_class:][::-1]
            )
            top_terms = feature_names[top_indices].tolist()
            logger.info(
                "Top %d TF-IDF features for class %r: %s",
                self._top_features_per_class, class_name, top_terms,
            )


# ---------------------------------------------------------------------------
# Evaluation helpers (used by __main__ and external callers)
# ---------------------------------------------------------------------------

def evaluate(
    clf: DisputeClassifier,
    test_texts: List[str],
    test_labels: List[str],
) -> Dict:
    """Run predictions on test set and return evaluation artefacts.

    Parameters
    ----------
    clf:
        A fitted :class:`DisputeClassifier`.
    test_texts:
        Raw description strings.
    test_labels:
        Ground-truth labels (already normalised).

    Returns
    -------
    dict
        Keys: ``report`` (str), ``matrix`` (list[list[int]]),
        ``classes`` (list[str]).
    """
    predictions = [clf.predict(t)[0] for t in test_texts]
    present_classes = sorted(set(test_labels) | set(predictions))

    report = classification_report(
        test_labels, predictions,
        labels=present_classes,
        zero_division=0,
    )
    matrix = confusion_matrix(
        test_labels, predictions, labels=present_classes
    ).tolist()
    return {
        "report": report,
        "matrix": matrix,
        "classes": present_classes,
    }


def _pretty_confusion_matrix(matrix: List[List[int]], classes: List[str]) -> str:
    """Render a confusion matrix as an aligned text table."""
    col_width = max(len(c) for c in classes) + 2
    header = " " * col_width + "".join(c.center(col_width) for c in classes)
    rows = [header, "-" * len(header)]
    for label, row in zip(classes, matrix):
        cells = "".join(str(v).center(col_width) for v in row)
        rows.append(label.ljust(col_width) + cells)
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Data loading helper (JSON or CSV)
# ---------------------------------------------------------------------------

def _load_data(path: str) -> List[Dict]:
    """Load training data from a JSON array or CSV file.

    JSON can be a bare array ``[...]`` or a wrapper dict with an
    ``"items"`` / ``"data"`` key.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data = data.get("items", data.get("data", list(data.values())[0]))
        return data
    elif ext == ".csv":
        import csv
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return list(reader)
    else:
        raise ValueError(
            f"Unsupported file extension {ext!r}. Use .json or .csv."
        )


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate the DisputeClassifier.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data", "-d",
        required=True,
        metavar="PATH",
        help=(
            "Path to training data (.json array or .csv with headers "
            "'dispute_description' and 'dispute_type')."
        ),
    )
    parser.add_argument(
        "--save", "-s",
        default=None,
        metavar="PATH",
        help="If given, save the trained model to this .joblib path.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.20,
        metavar="FLOAT",
        help="Fraction of data held out for evaluation (0–1).",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        metavar="INT",
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--top-features",
        type=int,
        default=_TOP_FEATURES_PER_CLASS,
        metavar="INT",
        help="Number of top TF-IDF features to log per class.",
    )
    args = parser.parse_args(argv)

    # ---- Load data ---------------------------------------------------------
    logger.info("Loading data from %s …", args.data)
    all_data = _load_data(args.data)
    logger.info("Loaded %d records.", len(all_data))

    texts = [
        (item.get("dispute_description") or "").strip() for item in all_data
    ]
    labels = [
        normalise_label((item.get("dispute_type") or "").strip())
        for item in all_data
    ]

    # Filter blank entries
    pairs = [(t, l) for t, l in zip(texts, labels) if t and l]
    if len(pairs) < len(all_data):
        logger.warning(
            "Dropped %d records with missing description or label.",
            len(all_data) - len(pairs),
        )
    texts, labels = zip(*pairs) if pairs else ([], [])
    texts, labels = list(texts), list(labels)

    if len(set(labels)) < 2:
        raise SystemExit(
            f"ERROR: Need at least 2 distinct dispute_type labels, "
            f"found only: {set(labels)}"
        )

    # ---- Train / test split ------------------------------------------------
    _MIN_SPLIT_SIZE = 10
    if args.test_size > 0 and len(texts) >= _MIN_SPLIT_SIZE:
        # Only stratify if every class has enough examples for the split
        label_counts = {l: labels.count(l) for l in set(labels)}
        can_stratify = all(
            c >= max(2, int(1 / args.test_size))
            for c in label_counts.values()
        )
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels,
            test_size=args.test_size,
            random_state=args.random_seed,
            stratify=labels if can_stratify else None,
        )
        if not can_stratify:
            logger.warning(
                "Stratified split skipped — some classes have too few examples."
            )
    else:
        logger.warning(
            "Dataset too small for a held-out split (%d examples); "
            "evaluating on training data.",
            len(texts),
        )
        X_train, X_test, y_train, y_test = texts, texts, labels, labels

    # ---- Fit ---------------------------------------------------------------
    clf = DisputeClassifier(top_features_per_class=args.top_features)
    train_records = [
        {"dispute_description": t, "dispute_type": l}
        for t, l in zip(X_train, y_train)
    ]
    clf.train(train_records)

    # ---- Evaluate ----------------------------------------------------------
    print("\n" + "=" * 70)
    print("DISPUTE CLASSIFIER — EVALUATION REPORT")
    print("=" * 70)
    print(f"Train size : {len(X_train)}")
    print(f"Test  size : {len(X_test)}")
    print(f"Classes    : {sorted(set(y_train))}")
    print("-" * 70)

    results = evaluate(clf, X_test, y_test)

    print("\n-- Classification Report ------------------------------------------------")
    print(results["report"])

    print("-- Confusion Matrix -----------------------------------------------")
    print(_pretty_confusion_matrix(results["matrix"], results["classes"]))
    print("=" * 70 + "\n")

    # ---- Persist -----------------------------------------------------------
    if args.save:
        clf.save(args.save)
        print(f"Model saved -> {args.save}")


if __name__ == "__main__":
    main()
