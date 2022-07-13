"""Types of UserInput"""

from __future__ import annotations
from abc import ABC, abstractmethod

class UserInput(ABC):
    """abstract base class"""

class ArgdownInput(UserInput):
    """argdown input by user"""

class CueInput(UserInput):
    """cue input by user (gist, context, etc.)"""

class QuoteInput(UserInput):
    """quote input by user (reason, conjecture)"""
