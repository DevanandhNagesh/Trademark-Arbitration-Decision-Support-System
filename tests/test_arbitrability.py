import json
import glob
import os
import pytest
import sys

# Ensure project root is in system path so agents can be imported correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.arbitrability_agent import check_arbitrability

# Find all JSON test cases
test_case_dir = os.path.join(os.path.dirname(__file__), "test_cases")
json_files = glob.glob(os.path.join(test_case_dir, "scenario_*.json"))

@pytest.mark.parametrize("filepath", json_files)
def test_scenario_arbitrability(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        dispute_data = json.load(f)

    # Check that expected_arbitrable is defined
    assert "expected_arbitrable" in dispute_data, f"Missing expected_arbitrable field in {os.path.basename(filepath)}"
    
    expected = dispute_data["expected_arbitrable"]
    
    # Run through the check_arbitrability function
    result = check_arbitrability(dispute_data)
    
    # Assert result matches expectation
    assert result.is_arbitrable == expected, (
        f"Mismatch in {os.path.basename(filepath)}: "
        f"expected is_arbitrable to be {expected}, but got {result.is_arbitrable}. "
        f"Reasoning: {result.reason}"
    )
