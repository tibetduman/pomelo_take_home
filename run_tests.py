"""Unit tests for Pomelo HackerRank question."""

import os
import glob
import pytest
from solution import summarize

test_case_files = glob.glob('test_cases/*.json')


@pytest.mark.parametrize('json_filename', test_case_files)
def test_json_inputs(json_filename):
    """Creates a unit test for each file in the test_cases directory."""
    with open(json_filename, 'r', encoding="utf-8") as file:
        input_json_str = file.read()
    try:
        actual = summarize(input_json_str)
    except ValueError as e:
        actual = 'Error: ' + str(e)

    filename, _ = os.path.splitext(json_filename)
    with open(filename + '.txt', 'r', encoding="utf-8") as file:
        output_str = file.read()
    expected = output_str.rstrip('\n')

    assert actual == expected
