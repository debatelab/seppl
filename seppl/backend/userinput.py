"""Types of UserInput"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from deepa2 import DeepA2Item



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

    @abstractmethod
    def update_da2item(self, da2_item: DeepA2Item = None) -> Any:
        """updates the da2item (no copy!) given the raw input"""

class ArgdownInput(UserInput):
    """argdown input by user"""

    def cast(self) -> str:
        # minimal preprocessing
        argdown_text = self._raw_input.strip()
        return argdown_text


class CueInput(UserInput):
    """cue input by user (gist, context, etc.)"""

class QuoteInput(UserInput):
    """quote input by user (reason, conjecture)"""

class FormalizationInput(UserInput):
    """formalization input by user (premises formalized,
    conclusion formalized, intermediary conclusions formalized)"""

class KeysInput(UserInput):
    """keys input by user (placeholder substitutions)"""



INPUT_TYPES = {
    """maps DeepA2Item fields to user_input classes"""

    "title": CueInput,
    "gist": CueInput,
    "source_paraphrase": CueInput,
    "context": CueInput,

    "argdown_reconstruction": ArgdownInput,

    "reasons": QuoteInput,
    "conjectures": QuoteInput,

    "premises_formalized": FormalizationInput,
    "intermediary_conclusions_formalized": FormalizationInput,
    "conclusion_formalized": FormalizationInput,

    "plchd_substitutions": KeysInput,
}
