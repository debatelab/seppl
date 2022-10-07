"""Types of UserInput"""

from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, asdict
import logging
import re
import textwrap
from typing import List, Any, Dict, Optional

from deepa2 import DeepA2Item, DeepA2Layouter, QuotedStatement

from seppl.backend.inference import InferenceRater


@dataclass
class InputOption():
    """
    abstract base class
    contains alternative contexts
    contains a question / task-formulation
    contains id(str) of intended input_type to-be returned
    """
    da2_field: str
    context: Optional[List[Any]] = None
    question: Optional[str] = None
    inference_rater: Optional[InferenceRater] = None

    def as_dict(self) -> Dict[str, Any]:
        """returns a dict representation of this input option"""
        data = asdict(self)
        data["inference_rater"] = None
        data["class"] = self.__class__.__name__
        return data

    @staticmethod
    def wrap_argdown(argdown: str) -> str:
        """wraps argdown text, preserving linebreaks"""
        # split lines
        argdown_lines = argdown.split("\n")
        # wrap each line
        argdown_lines = [
            "  \n".join(textwrap.wrap(line, width=60))
            for line in argdown_lines
        ]
        # join lines
        argdown = "\n".join(argdown_lines)
        return argdown

@dataclass
class ChoiceOption(InputOption):
    """
    represents a multiple choice option
    contains answer options
        keys: answer_labels
        values: answers
    """
    answers: Optional[Dict[str, str]] = None 

@dataclass
class TextOption(InputOption):
    """
    represents an input option for free-text
    contains an initial_text
    """
    initial_text: Optional[str] = None
    
@dataclass
class QuoteOption(InputOption):
    """
    represents a quote option for annotating
    a given source text
    """
    source_text: Optional[str] = None
    initial_annotation: Optional[str] = None
    initial_quotes: Optional[List[QuotedStatement]] = None
    
    _REGEX_QUOTE = r"\[([^\[]+)\]\(([^ ]*)( \"(.+)\")?\)"

    def __post_init__(self):
        if self.source_text is None:
            raise ValueError(f"QuoteOption ({self}): source_text is None but must be given")
        if self.initial_annotation:
            if not self.is_annotation(self.initial_annotation):
                self.initial_annotation = None
                logging.warning("QuoteOption: ignoring faulty initial_annotation")
        # construct initial annotation from initial quotes
        if self.initial_quotes and not self.initial_annotation:
            self.initial_annotation = QuoteOption.quotes_as_annotation(
                self.source_text, self.initial_quotes
            )
        # if no initial annotation, display pure source text
        if not self.initial_annotation:
            self.initial_annotation = self.source_text

    def is_annotation(
        self,
        annotation: str
    ) -> bool:
        """checks whether annotation is valid annotation of source_text"""
        if self.source_text is None:
            return False
        # retrieve source text by stripping annotation
        retrieved_text = ""
        matches = re.finditer(self._REGEX_QUOTE, annotation, re.MULTILINE)
        pointer = 0 # pointer to current position in source_text
        for match in matches:
            if not match.group(1) in self.source_text:
                return False
            retrieved_text += annotation[pointer:match.start()]
            retrieved_text += match.group(1)
            pointer = match.end()
            #pointer = self.source_text.index(match.group(1), pointer) + len(match.group(1))
        retrieved_text += annotation[pointer:]
        print(retrieved_text)
        return retrieved_text == self.source_text

    @staticmethod
    def quotes_as_annotation(
        source_text: str,
        quotes: List[QuotedStatement]
    ) -> str:
        """formats quotes as annotation"""
        pointer = 0 # pointer to current position in source_text
        annotation = ""
        # gradually build annotation
        for quote in quotes:
            if quote:
                if quote.text in source_text[pointer:]:
                    start_idx = source_text.index(quote.text, pointer)
                    annotation += source_text[pointer:start_idx]
                    annotation += f"[{quote.text}]({quote.ref_reco})"
                    pointer = start_idx+len(quote.text)
                else:
                    logging.warning("QuoteOption: ignoring faulty quote %s", quote.text)
            else:
                logging.warning("QuoteOption: ignoring empty quote.")
        annotation += source_text[pointer:]
        return annotation

    @staticmethod
    def annotation_as_quotes(
        annotation: str
    ) -> List[QuotedStatement]:
        """returns quotes from annotation"""
        quotes = []
        matches = re.finditer(QuoteOption._REGEX_QUOTE, annotation, re.MULTILINE)
        for match in matches:
            ref_reco = -1
            if match.group(2):
                try:
                    ref_reco = int(match.group(2))
                except ValueError:
                    pass
            quotes.append(
                QuotedStatement(
                    text=match.group(1),
                    ref_reco=ref_reco,
                )
            )
        return quotes

class OptionFactory():
    """factory class for creating InputOption objects"""

    @staticmethod
    def from_dict(data: Dict[str,Any]) -> InputOption:
        """creates InputOption from dict"""
        option_class = data.pop("class")
        if option_class == "ChoiceOption":
            return ChoiceOption(**data)
        if option_class == "TextOption":
            return TextOption(**data)
        if option_class == "QuoteOption":
            return QuoteOption(**data)
        raise ValueError(f"OptionFactory: unknown class {data['class']}")

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
        formatted_da2item = DeepA2Layouter().format(da2_item) if da2_item else None
        # re-format conclusion, which is used as cues (text only)
        if formatted_da2item and da2_item:
            formatted_da2item["conclusion"] = da2_item.conclusion[0].text
        input_options: List[InputOption] = []
        if da2_fields:
            for da2_field in da2_fields:
                if pre_initialized and formatted_da2item:
                    initial_text = formatted_da2item.get(da2_field, "")
                else:
                    initial_text = ""
                if initial_text:
                    question_text = f"Please revise the *{da2_field}*."
                else:
                    question_text = f"Please enter a *{da2_field}*."
                input_options.append(
                    TextOption(
                        question=question_text,
                        da2_field=da2_field,
                        initial_text=initial_text,
                    )
                )
        return input_options

    @staticmethod
    def create_quote_options(
        da2_fields: List[str] = None,
        da2_item: DeepA2Item = None,
        pre_initialized: bool = False,
    ) -> List[InputOption]:
        """
        QuoteOption Factory
        creates a list of QuoteOptions, possibly
        pre-initialized with da2item values
        """
        if not da2_item:
            logging.warning("OptionFactory: no da2_item given, cannot prodiuce quote options.")
            return []
        input_options: List[InputOption] = []
        if da2_fields:
            for da2_field in da2_fields:
                if pre_initialized and da2_item:
                    quotes = getattr(da2_item, da2_field, None)
                else:
                    quotes = None
                if quotes:
                    question_text = f"Please revise the {da2_field}."
                else:
                    question_text = f"Please mark the {da2_field}."
                input_options.append(
                    QuoteOption(
                        question=question_text,
                        da2_field=da2_field,
                        source_text=da2_item.source_text,
                        initial_quotes=quotes,
                    )
                )
        return input_options        