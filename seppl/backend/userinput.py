"""Types of UserInput"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Union, List, Optional, Tuple
from deepa2 import (
    DeepA2Item,
    ArgdownStatement,
    QuotedStatement,
    Formalization,
    DeepA2Parser
)

import bs4

from seppl.backend.inputoption import QuoteOption



class UserInput(ABC):
    """abstract base class"""

    def __init__(
        self,
        raw_input: str,
        da2_field: str,
    ):
        self._raw_input: str = raw_input
        self.da2_field: str = da2_field

    def cast(self) -> Any:
        """casts raw input as component of da2item"""
        return self._raw_input

    def update_da2item(self, da2_item: DeepA2Item = None) -> Any:
        """updates the da2item (no copy!) given the current raw input"""
        setattr(da2_item, self.da2_field, self.cast())

    def stripped_input(self) -> str:
        """strips input from html tags and trailing space"""
        stripped_input = self._raw_input.strip()
        soup = bs4.BeautifulSoup(stripped_input, features="html.parser")
        return soup.get_text()

class ArgdownInput(UserInput):
    """argdown input by user"""

    def cast(self) -> str:
        # minimal preprocessing
        argdown_text = self.stripped_input()
        return argdown_text


class CueInput(UserInput):
    """cue input by user (gist, context, etc.)"""

    def cast(self) -> Union[str, List[ArgdownStatement]]:
        if self.da2_field == "conclusion":
            return [ArgdownStatement(text=self.stripped_input())]
        else:
            # minimal preprocessing
            return self.stripped_input()



class QuoteInput(UserInput):
    """quote input by user (reasons, conjectures)"""

    def cast(self) -> List[QuotedStatement]:
        quoted_statements = QuoteOption.annotation_as_quotes(
            self.stripped_input()
        )

        return quoted_statements


class FormalizationInput(UserInput):
    """formalization input by user (premises formalized,
    conclusion formalized, intermediary conclusions formalized)"""

    def cast(self) -> List[Formalization]:
        formalizations = DeepA2Parser.parse_formalization(
            self.stripped_input()
        )
        return formalizations

class KeysInput(UserInput):
    """keys input by user (placeholder substitutions)"""

    def cast(self) -> Optional[List[Tuple[str, str]]]:
        keys = DeepA2Parser.parse_keys(
            self.stripped_input()
        )
        return keys



INPUT_TYPES = {
    """maps DeepA2Item fields to user_input classes"""

    "title": CueInput,
    "gist": CueInput,
    "source_paraphrase": CueInput,
    "context": CueInput,
    "conclusion": CueInput,

    "argdown_reconstruction": ArgdownInput,

    "reasons": QuoteInput,
    "conjectures": QuoteInput,

    "premises_formalized": FormalizationInput,
    "intermediary_conclusions_formalized": FormalizationInput,
    "conclusion_formalized": FormalizationInput,

    "plchd_substitutions": KeysInput,
}
