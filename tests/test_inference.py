"""tests the inference module"""

import pytest

from deepa2 import (
    DeepA2Item,
    QuotedStatement,
)
from seppl.backend.inference import AbstractInferencePipeline


@pytest.fixture(name="postprocessing_examples")
def fixture_postprocessing_examples():
    """postprocessing_examples"""
    postprocessing_examples = [
        (
            "(1) premise 1 -- my inference -- (2) conclusion 2 "
            "(3) another premise ---- (4) conclusion",
            "(1) premise 1\n-- my inference --\n(2) conclusion 2\n"
            "(3) another premise\n----\n(4) conclusion",
        ),
    ]
    return postprocessing_examples



def test_pp_argdown(postprocessing_examples):
    """test postprocessing of argdown"""
    for raw, pp in postprocessing_examples:
        pp_gen = AbstractInferencePipeline.postprocess_argdown(raw)
        print(pp_gen)
        assert pp_gen == pp

