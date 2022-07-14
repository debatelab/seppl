"""Types of UserInput"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from deepa2 import DeepA2Item

class UserInput(ABC):
    """abstract base class"""

    def __init__(self, raw_input: str):
        self._raw_input: str = raw_input

    @abstractmethod
    def cast(self) -> Any:
        """casts raw input as component of da2item"""


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

