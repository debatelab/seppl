"""Types of UserInput"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Any, Dict

from seppl.backend.userinput import ArgdownInput


INPUT_TYPES = {
    "ARGDOWN_INPUT": ArgdownInput
}

@dataclass
class InputOption():
    """
    abstract base class
    contains alternative contexts
    contains a question / task-formulation
    contains id(str) of intended input_type to-be returned
    """
    context: List[Any] = None
    question: str = None
    input_type: str = None

@dataclass
class ChoiceOption(InputOption):
    """
    represents a multiple choice option
    contains answer options
        keys: answer_labels
        values: answers
    """
    answers: Dict[str, str] = None 

@dataclass
class TextOption(InputOption):
    """
    represents an input option for free-text
    contains an initial_text
    """
    initial_text: str = None
    
