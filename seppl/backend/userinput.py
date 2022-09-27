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

    @abstractmethod
    def cast(self) -> Any:
        """casts raw input as component of da2item"""

    def update_da2item(self, da2_item: DeepA2Item = None) -> Any:
        """updates the da2item (no copy!) given the current raw input"""
        setattr(da2_item, self.da2_field, self.cast())

class ArgdownInput(UserInput):
    """argdown input by user"""

    def cast(self) -> str:
        # minimal preprocessing
        argdown_text = self._raw_input.strip()
        return argdown_text


class CueInput(UserInput):
    """cue input by user (gist, context, etc.)"""

    def cast(self) -> Union[str, List[ArgdownStatement]]:
        if self.da2_field == "conclusion":
            return [ArgdownStatement(text=self._raw_input.strip())]
        else:
            # minimal preprocessing
            return self._raw_input.strip()



class QuoteInput(UserInput):
    """quote input by user (reasons, conjectures)"""

    def cast(self) -> List[QuotedStatement]:
        quoted_statements = QuoteOption.annotation_as_quotes(
            self._raw_input.strip()
        )

        return quoted_statements


class FormalizationInput(UserInput):
    """formalization input by user (premises formalized,
    conclusion formalized, intermediary conclusions formalized)"""

    def cast(self) -> List[Formalization]:
        formalizations = DeepA2Parser.parse_formalization(
            self._raw_input.strip()
        )
        return formalizations

class KeysInput(UserInput):
    """keys input by user (placeholder substitutions)"""

    def cast(self) -> Optional[List[Tuple[str, str]]]:
        keys = DeepA2Parser.parse_keys(
            self._raw_input.strip()
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
