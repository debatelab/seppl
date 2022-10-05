"""tests the annotations"""

import pytest

from deepa2 import (
    DeepA2Item,
    QuotedStatement,
)
from seppl.backend.inputoption import QuoteOption


@pytest.fixture(name="sources")
def fixture_sources():
    """sources"""
    sources = [
        "Peter is lonely. So he calls his sister. "
        "But Pele is \\]lonely. And he calls his sister.",
    ]
    return sources


@pytest.fixture(name="annotations")
def fixture_annotations():
    """annotations"""
    annotations = [
        "Peter [is lonely. So he](3) calls his sister. "
        "But Pele [is \\]lonely. And](1) he calls his sister.",
    ]
    return annotations

@pytest.fixture(name="quoteslist")
def fixture_quoteslist():
    """quoteslist"""
    quoteslist = [
        [
            QuotedStatement(
                text="is lonely. So he",
                ref_reco=3
            ),
            QuotedStatement(
                text="is \\]lonely. And",
                ref_reco=1
            ),
        ],
    ]
    return quoteslist


def test_annotations_1(annotations,quoteslist):
    """test annotations"""
    for annotation, quotes in zip(annotations, quoteslist):
        assert QuoteOption.annotation_as_quotes(annotation) == quotes


def test_annotations_2(annotations,quoteslist,sources):
    """test annotations"""
    for annotation, quotes, source_text in zip(annotations, quoteslist, sources):
        assert QuoteOption.annotation_as_quotes(annotation) == quotes

        assert QuoteOption.quotes_as_annotation(source_text,quotes) == annotation

def test_annotations_3():
    """test annotations check"""
    source = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely. Animals are sentient beings that
have emotions and social connections. Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""
    annotation1 = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because [raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely](2). [Animals are sentient beings that
have emotions and social connections.[(1) Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""
    annotation2 = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because [raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely](2). [Animals are sentient beings that
have emotions and social connections.](1) Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""
    qoption = QuoteOption(da2_field="reasons", source_text=source)
    assert not qoption.is_annotation(annotation1)
    assert qoption.is_annotation(annotation2)
