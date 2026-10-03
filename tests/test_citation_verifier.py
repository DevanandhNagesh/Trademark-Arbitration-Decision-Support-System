"""tests/test_citation_verifier.py

Unit tests for agents/citation_verifier.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.citation_verifier import verify_citations
from agents.landmark_retrieval_agent import LandmarkMatch


def test_verify_citations_empty_inputs():
    """Empty or None inputs should return an empty dict without failing."""
    assert verify_citations(None, None, None) == {}
    assert verify_citations([], {}, []) == {}


def test_verify_citations_known_registry_cases():
    """Citations present in LANDMARK_CASES in config.py should verify as True."""
    statutory_provisions = [
        {
            "statute": "Section 29 of Trade Marks Act 1999",
            "judicial_interpretation": "Parle Products v JP Co AIR 1972 SC 1359 — deceptive similarity test.",
        },
        {
            "statute": "Section 8 of Arbitration Act 1996",
            "judicial_interpretation": "Booz Allen & Hamilton Inc. (2011) 5 SCC 532 held rights in rem non-arbitrable.",
        },
    ]
    adversarial_analysis = {
        "law_for_claimant": [
            {
                "statute": "Section 30",
                "case_interpretation": "Vidya Drolia (2021) 2 SCC 1 established fourfold test.",
            }
        ]
    }

    results = verify_citations(
        statutory_provisions=statutory_provisions,
        adversarial_analysis=adversarial_analysis,
        landmark_matches=[],
    )

    assert "AIR 1972 SC 1359" in results
    assert results["AIR 1972 SC 1359"] is True

    assert "(2011) 5 SCC 532" in results
    assert results["(2011) 5 SCC 532"] is True

    assert "(2021) 2 SCC 1" in results
    assert results["(2021) 2 SCC 1"] is True


def test_verify_citations_from_retrieved_landmark_matches():
    """Citations present in retrieved LandmarkMatch objects should verify as True."""
    custom_lm = LandmarkMatch(
        case_key="custom_case",
        case_name="Custom Brand v. Other Corp",
        citation="(2023) 14 SCC 500",
        year=2023,
        court="Supreme Court of India",
        principle="Specific licensing rule",
        relevant_text="...",
        similarity_score=0.92,
        category="arbitrability",
    )

    statutory_provisions = [
        {
            "statute": "Section 135 Trade Marks Act 1999",
            "judicial_interpretation": "In Custom Brand (2023) 14 SCC 500, permanent injunction was granted.",
        }
    ]

    results = verify_citations(
        statutory_provisions=statutory_provisions,
        adversarial_analysis={},
        landmark_matches=[custom_lm],
    )

    assert "(2023) 14 SCC 500" in results
    assert results["(2023) 14 SCC 500"] is True


def test_verify_citations_flags_hallucinations_as_false():
    """Unverified / hallucinated citations should verify as False."""
    statutory_provisions = [
        {
            "statute": "Section 29 Trade Marks Act 1999",
            "judicial_interpretation": "Fictional Case (2026) 99 SCC 1234 on deceptive similarity.",
        }
    ]
    adversarial_analysis = {
        "law_against_claimant": [
            {
                "statute": "Section 30",
                "case_interpretation": "Imaginary Corp AIR 2030 SC 8888 held defense applies.",
            }
        ],
        "options_if_law_against": [
            {
                "option_title": "Fair Use",
                "case_support": "Fake Judgment 2029 SCC OnLine Del 99999",
            }
        ],
    }

    results = verify_citations(
        statutory_provisions=statutory_provisions,
        adversarial_analysis=adversarial_analysis,
        landmark_matches=[],
    )

    assert "(2026) 99 SCC 1234" in results
    assert results["(2026) 99 SCC 1234"] is False

    assert "AIR 2030 SC 8888" in results
    assert results["AIR 2030 SC 8888"] is False

    assert "2029 SCC OnLine Del 99999" in results
    assert results["2029 SCC OnLine Del 99999"] is False
