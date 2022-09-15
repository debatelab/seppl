"""Types of UserInput"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Any, Dict

from deepa2 import DeepA2Item

from seppl.backend.inference import InferenceRater


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
    da2_field: str = None
    inference_rater: InferenceRater = None

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
    

class OptionFactory():
    """factory class for creating InputOption objects"""

    @staticmethod
    def create_text_options(
        da2_fields: List[str] = None,
        da2_item: DeepA2Item = None,
        pre_initialized: bool = False,
    ) -> List[InputOption]:
        """
        TextOption Factory
        creates a list of TextOptions, possibly
        pre-initialized with da2item values
        """
        input_options = []
        for da2_field in da2_fields:
            if pre_initialized and da2_item:
                initial_text = getattr(da2_item, da2_field)
            else:
                initial_text = ""
            if initial_text:
                question_text = f"Please revise the {da2_field}."
            else:
                question_text = f"Please enter a {da2_field}."
            input_options.append(
                TextOption(
                    question=question_text,
                    da2_field=da2_field,
                    initial_text=initial_text,
                )
            )
        return input_options