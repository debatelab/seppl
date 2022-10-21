"""Types of UserInput"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Union, List, Optional, Tuple
from deepa2 import (
    DeepA2Item,
    ArgdownStatement,
    QuotedStatement,
    Formalization,
    DeepA2Parser
)

import bs4

from seppl.backend.inputoption import QuoteOption, ReasonsConjecturesOption



class UserInput(ABC):
    """abstract base class"""

    def __init__(
        self,
        raw_input: Any,
        da2_field: str,
    ):
        self._raw_input: Any = raw_input
        self.da2_field: str = da2_field

    def cast(self) -> Any:
        """casts raw input as component of da2item"""
        return self._raw_input

    def update_da2item(self, da2_item: DeepA2Item = None) -> Any:
        """updates the da2item (no copy!) given the current raw input"""
        setattr(da2_item, self.da2_field, self.cast())

    def stripped_input(self) -> Any:
        """strips text input from html tags and trailing space"""
        if isinstance(self._raw_input, str):
            stripped_input = self._raw_input.strip()
            soup = bs4.BeautifulSoup(stripped_input, features="html.parser")
            return soup.get_text()
        return self._raw_input

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



class ReasonsConjecturesInput(UserInput):
    """input by user for complete annotation of source_text 
    (reasons and conjectures)"""

    _raw_input: Dict[str, List[Dict[str,Any]]]

    def cast(self) -> Tuple[List[QuotedStatement],List[QuotedStatement]]:
        """casts raw input as components of da2item"""
        reasons = ReasonsConjecturesOption.dicts_as_quotes(
            self._raw_input.get("reasons",[])
        )       
        conjectures = ReasonsConjecturesOption.dicts_as_quotes(
            self._raw_input.get("conjectures",[])
        )
        return reasons, conjectures

    def update_da2item(self, da2_item: DeepA2Item = None) -> Any:
        """updates the da2item (no copy!) given the current raw input"""
        reasons, conjectures = self.cast()
        if da2_item:
            da2_item.reasons = reasons
            da2_item.conjectures = conjectures
        else:
            logging.warning("ReasonsConjecturesInput: no da2_item given")




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
        # drop None values
        if formalizations:
            formalizations = [f for f in formalizations if f is not None]
        if not formalizations:
            formalizations = None
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
    "reasons_conjectures": ReasonsConjecturesInput,

    "premises_formalized": FormalizationInput,
    "intermediary_conclusions_formalized": FormalizationInput,
    "conclusion_formalized": FormalizationInput,

    "plchd_substitutions": KeysInput,
}
