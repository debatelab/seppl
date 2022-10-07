"""option renderer"""


from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, Callable, Optional

from deepa2 import DA2_ANGLES_MAP
import streamlit as st
from streamlit_ace import st_ace

from seppl.backend.userinput import UserInput, INPUT_TYPES
from seppl.backend.inputoption import (
    ChoiceOption,
    InputOption,
    TextOption,
    QuoteOption,
)


class InputOptionStRenderer(ABC):
    """
    abstract class
    renders input option in streamlit
    """

    _input: Any = None
    _input_option: InputOption
    _submit: Optional[Callable] # reference to project renderer's submit method

    def __init__(self,
        submit: Callable,
        input_option: InputOption,
    ):
        self._submit = submit
        self._input_option = input_option

    #@property
    #def input(self):
    #    """returns currently selcted / provided input"""
    #    return self._input

    def query(self, raw_input: str) -> UserInput:
        """constructs and returns user_input to-be passed to submit function"""
        user_input = INPUT_TYPES[self._input_option.da2_field](
            raw_input,
            self._input_option.da2_field,
        )
        logging.info(
            "%s: created query %s",
            self.__class__.__name__,
            (raw_input, self._input_option.da2_field)
        )
        return user_input

    @abstractmethod
    def render(self):
        """renders the input option as streamlit gui"""

    @staticmethod
    def option_gui_factory(option: InputOption, submit: Callable) -> InputOptionStRenderer:
        """creates gui for option"""
        logging.debug(option)
        option_gui: InputOptionStRenderer
        if isinstance(option, ChoiceOption):
            option_gui = ChoiceOptionStRenderer(
                submit=submit,
                input_option=option
            )
        elif isinstance(option, TextOption):
            option_gui = TextOptionStRenderer(
                submit=submit,
                input_option=option
            )
        elif isinstance(option, QuoteOption):
            option_gui = QuoteOptionStRenderer(
                submit=submit,
                input_option=option
            )
        else:
            raise ValueError(f"Cannot render unknown option type: {type(option)}")
        return option_gui


class ChoiceOptionStRenderer(InputOptionStRenderer):
    """renders a ChoiceOption"""

    _input_option: ChoiceOption

    def render(self):
        """renders the choice option as streamlit gui"""
        #st.write(f"## ChoiceOption for: {self._input_option.da2_field}")
        #st.write("### Context")
        for context_item in self._input_option.context:
            st.markdown(context_item)
        st.write(f"*{self._input_option.question}*")
        if self._input_option.inference_rater:
            st.caption("[Display InferenceRater]")
        for answer_label, answer in self._input_option.answers.items():
                st.button(
                    answer_label,
                    on_click = self._submit,
                    #kwargs = dict(query=self.query(answer))
                    kwargs = dict(
                        query_factory = self.query,
                        raw_input = answer,
                    )
                )


class TextOptionStRenderer(InputOptionStRenderer):
    """renders a TextOption"""

    _input_option: TextOption

    _LIST_FIELDS = [
        DA2_ANGLES_MAP.fp,
        DA2_ANGLES_MAP.fi,
        DA2_ANGLES_MAP.fc,
        DA2_ANGLES_MAP.k,
    ]

    def question(self) -> str:
        """postprocesses and formats question"""
        if self._input_option.da2_field == DA2_ANGLES_MAP.a:
            argdown_link = " (See also [argdown.org](https://argdown.org/syntax/#premise-conclusion-structures))"
        else:
            argdown_link = ""
        return (f"{self._input_option.question}"+argdown_link)


    def initial_text(self) -> Optional[str]:
        """postprocesses and formats initial_text"""
        initial_text = self._input_option.initial_text
        if initial_text is None:
            return initial_text
        if self._input_option.da2_field in self._LIST_FIELDS:
            initial_text = TextOption.split_da2_list(initial_text)        
        return initial_text

    def postprocess_input(self, text_input: str) -> str:
        """postprocesses input"""
        if self._input_option.da2_field in self._LIST_FIELDS:
            text_input = TextOption.join_da2_list(text_input)
        return text_input

    def help_text(self) -> Optional[str]:
        """creates help_text"""
        if self._input_option.da2_field in [
            DA2_ANGLES_MAP.fp,
            DA2_ANGLES_MAP.fi,
            DA2_ANGLES_MAP.fc,
        ]:
            return ("One formula per line. Use the syntax `(ref: (i))` to "
            "refer to statement (i) in argument. Example with two formulas, "
            "referring to (1) and (4):  \n"
            "> p (ref: (1))  \n"
            "> p -> q (ref: (4))  \n"
            "**Logical syntax:**  \n"
            "* `p`, `q`, `r`, ...: propositional variables  \n"
            "* `p -> q`: implication  \n"
            "* `p & q`: conjunction  \n"
            "* `p v q`: disjunction  \n"
            "* `not p`: negation  \n"
            "* `F`, `G` , ... : unary predicates  \n"
            "* `R`, `S`, ... : relations  \n"
            "* `a`, `b`, ... : names, aka object constants  \n"
            "* `x`, `y`, ... : variables \n"
            "* `F x` ,`R x a`  : predication  \n"
            "* `(x): ...`: universal quantification  \n"
            "* `(Ex): ...`: existential quantification")
        elif self._input_option.da2_field == DA2_ANGLES_MAP.k:
            return ("One key:value-pair per line. Use the syntax `placeholder : substitution` to "
            "indicate that `placeholder` stands for `substitution`. Example:  \n"
            "> p : it is raining  \n"
            "> q : the hay is getting wet  \n")
        return None

    def render(self):
        """renders the text option as streamlit gui"""

        # context
        if self._input_option.context:
            for context_item in self._input_option.context:
                st.write(context_item)
        

        if self._input_option.da2_field == DA2_ANGLES_MAP.a:
            # question
            st.write(f"*{self.question()}*")
            # text input
            text_input = st_ace(
                value=self._input_option.initial_text,
                language='markdown',
                theme='dawn',
                font_size=14,
                wrap=True,
                show_gutter=False,
                show_print_margin=False,
            )
        else:
            # text input
            text_input = st.text_area(
                label=self.question(),
                height=150,
                value=self.initial_text(),
                help=self.help_text(),
            )

        # postprocess_input
        text_input = self.postprocess_input(text_input)

        # inference rater
        if self._input_option.inference_rater:
            st.caption("[Display InferenceRater]")

        # submit
        st.button(
            "Submit",
            on_click = self._submit,
            #kwargs = dict(query=self.query(text_input))
            kwargs = dict(
                query_factory = self.query,
                raw_input = text_input,
            )
        )
    

class QuoteOptionStRenderer(InputOptionStRenderer):
    """renders a QuoteOption"""

    _input_option: QuoteOption

    def ready(self, annotation: str) -> bool:
        """checks if annotation is ready for submission"""
        logging.info("QuoteOption checking: %s", annotation)
        ready = (
            self._input_option.is_annotation(annotation)
            and annotation != self._input_option.initial_annotation
        )
        logging.info("QuoteOption ready: %s", ready)
        return ready

    def render(self):
        """renders the quote option as streamlit gui"""
        #st.write(f"## QuoteOption for: {self._input_option.da2_field}")
        if self._input_option.context:
            #st.write("### Context")
            for context_item in self._input_option.context:
                st.write(context_item)

        annotation = st.text_area(
            label=self._input_option.question,
            help="Format: `[annotated text](1)`.  \nAnnotations stripped of markup must match source text.",
            height=200,
            value=self._input_option.initial_annotation,
        )


        if self._input_option.inference_rater:
            st.caption("[Display InferenceRater]")

        st.button(
            "Submit",
            on_click = self._submit,
            #kwargs = dict(query=self.query(annotation))
            kwargs = dict(
                query_factory = self.query,
                raw_input = annotation,
            ),
            disabled=not self.ready(annotation)
        )
    
