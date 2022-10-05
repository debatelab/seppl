"""tests the da2metric module"""

from ast import arg
import pytest

from deepa2 import (
    DeepA2Item,
)
from seppl.backend.da2metric import SofaEvaluator



@pytest.fixture(name="da2_items")
def fixture_da2_items():
    """da2 items"""
    da2_items = [
        DeepA2Item(
            source_text="Peter is lonely. So he calls his sister.",
            argdown_reconstruction="(1) Peter is lonely. "
            "-- with modus ponens from (1) -- "
            "(2) So he calls his sister.",
        ),
    ]
    return da2_items

def test_sofaeval_1(da2_items):
    """test first argument"""
    sofaeval = SofaEvaluator(inference=None)
    sofaeval.update(da2_items[0])
    print(sofaeval.all_scores)
    assert sofaeval.individual_score("ValidArgdownScore")

