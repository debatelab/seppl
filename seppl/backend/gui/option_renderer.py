"""option renderer"""


from __future__ import annotations
from abc import ABC, abstractmethod
import copy
from dataclasses import asdict
import logging
from typing import Any, Callable, Optional, List, Dict

from deepa2 import DA2_ANGLES_MAP, DeepA2Parser, QuotedStatement
import streamlit as st
from streamlit_ace import st_ace
from streamlit_text_label import Selection, label_select

from seppl.backend.userinput import UserInput, INPUT_TYPES
from seppl.backend.inputoption import (
    ChoiceOption,
    InputOption,
    TextOption,
    QuoteOption,
    ReasonsConjecturesOption,
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

    def query(self, raw_input: Any) -> UserInput:
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
        elif isinstance(option, ReasonsConjecturesOption):
            option_gui = ReasonsConjecturesOptionStRenderer(
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


class ReasonsConjecturesOptionStRenderer(InputOptionStRenderer):
    """renders a ReasonsConjecturesOption"""

    _input_option: ReasonsConjecturesOption

    def ready(self, rj_input: Dict[str, List[Dict[str, Any]]]) -> bool:
        return bool(rj_input)

    def _non_overlapping_selections(self, selected: List[Selection]) -> bool:
        """checks if selections don't overlap"""
        selected = sorted(selected, key=lambda s: s.start)
        for i in range(len(selected) - 1):
            if selected[i].end > selected[i + 1].start:
                return False
        return True

    def question(self) -> str:
        """postprocesses and formats question"""
        return (f"{self._input_option.question} (N.B.: Click 'update' before submitting.)")

    def initial_selection(self) -> List[Selection]:
        """constructs initial selection from initial reasons and conjectures"""
        body = self._input_option.source_text
        if not body:
            return []
        labels = self.get_labels()
        selected = []
        if self._input_option.initial_reasons:
            for quote in self._input_option.initial_reasons:
                reason = QuotedStatement(**quote)
                if reason.text not in body:
                    continue;
                label = f"P{reason.ref_reco}"
                if not label in labels:
                    label = "Generic Premise"
                if reason.starts_at >= 0:
                    start = reason.starts_at
                else:
                    start = body.find(reason.text)
                selected.append(
                    Selection(
                        start=start,
                        end=start+len(reason.text),
                        text=reason.text,
                        labels=[label]
                    )
                )
        if self._input_option.initial_conjectures:
            for quote in self._input_option.initial_conjectures:
                conjecture = QuotedStatement(**quote)
                if conjecture.text not in body:
                    continue;
                label = f"C{conjecture.ref_reco}"
                if not label in labels:
                    label = "Generic Conclusion"
                if conjecture.starts_at >= 0:
                    start = conjecture.starts_at
                else:
                    start = body.find(conjecture.text)
                selected.append(
                    Selection(
                        start=start,
                        end=start+len(conjecture.text),
                        text=conjecture.text,
                        labels=[label]
                    )
                )

        return selected

    def get_labels(self) -> List[str]:
        """constructs labels"""
        labels = ["Generic Premise"]
        if self._input_option.premise_labels:
            labels += [f"P{i}" for i in self._input_option.premise_labels]
        labels += ["Generic Conclusion"]
        if self._input_option.conclusion_labels:
            labels += [f"C{i}" for i in self._input_option.conclusion_labels]        
        return labels

    def postprocess_input(self, selected: List[Selection]) -> Dict[str, List[Dict[str, Any]]]:
        """constructs reasons and conjectures from input selection"""
        # check if selections are not overlapping
        if not self._non_overlapping_selections(selected):
            return({})
        selected = copy.deepcopy(selected)
        selected_reasons = [
            s for s in selected 
            if s.labels[0][0] == "P" or "Generic Premise" in s.labels
        ]
        selected_reasons = sorted(selected_reasons, key=lambda s: s.start)
        reason_statements: List[Dict[str, Any]] = []
        for selection in selected_reasons:
            reason_statements.append(
                asdict(QuotedStatement(
                    ref_reco = -1 if selection.labels[0] == "Generic Premise" else int(selection.labels[-1][1:]),
                    starts_at = selection.start,
                    text = selection.text,
                ))
            )

        selected_conjectures = [
            s for s in selected 
            if s.labels[0][0] == "C" or "Generic Conclusion" in s.labels
        ]
        selected_conjectures = sorted(selected_conjectures, key=lambda s: s.start)
        conjecture_statements: List[Dict[str, Any]] = []
        for selection in selected_conjectures:
            conjecture_statements.append(
                asdict(QuotedStatement(
                    ref_reco = -1 if selection.labels[0] == "Generic Conclusion" else int(selection.labels[-1][1:]),
                    starts_at = selection.start,
                    text = selection.text,
                ))
            )

        return {
            "reasons": reason_statements,
            "conjectures": conjecture_statements,
        }


    def render(self):
        """renders reasons and conjectures annotations as streamlit gui"""

        # context
        if self._input_option.context:
            for context_item in self._input_option.context:
                st.write(context_item)        

        # question
        st.write(f"*{self.question()}*")
        selected = label_select(
            body=self._input_option.source_text,
            labels=self.get_labels(),
            selections=self.initial_selection(),
        )

        # postprocess_input
        rj_input = self.postprocess_input(selected)

        # inference rater
        if self._input_option.inference_rater:
            st.caption("[Display InferenceRater]")

        # warning of overlapping selections
        if not self.ready(rj_input):
            st.warning("Overlapping selections are not allowed.")

        # submit
        st.button(
            "Submit",
            on_click = self._submit,
            kwargs = dict(
                query_factory = self.query,
                raw_input = rj_input,
            ),
            disabled=not self.ready(rj_input)
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

    def ready(self, text_input: str) -> bool:
        """checks if text_input is ready for submission"""
        # check formalization
        if self._input_option.da2_field in [
            DA2_ANGLES_MAP.fp,
            DA2_ANGLES_MAP.fi,
            DA2_ANGLES_MAP.fc,
        ]:
            parsed = DeepA2Parser.parse_formalization(text_input)
            if parsed is None:
                return False
            elif None in parsed:
                return False
        # check plcd substitutions
        if self._input_option.da2_field in [
            DA2_ANGLES_MAP.k,
        ]:
            parsed = DeepA2Parser.parse_keys(text_input)
            if parsed is None:
                return False
            elif None in parsed:
                return False
        return True

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
            "refer to statement (i) in argument. Chars `u-z` are _reserved "
            "for variables_. Example with two formulas, referring to (1) "
            "and (4):  \n"
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
                value=self._input_option.initial_text if self._input_option.initial_text else "",
                placeholder="Example 1:  \n"
                "(1) some premise  \n"
                "----  \n"
                "(2) a conclusion \n"
                "Example 2:  \n"
                "(1) some premise  \n"
                "(2) another premise  \n"
                "-- with some-inference-scheme from (1) (2) --  \n"
                "(3) an intermediary conclusion \n"
                "(4) a third premise  \n"
                "-- with some-inference-scheme from (3) (4) --  \n"
                "(5) final conclusion  \n",
                language='markdown',
                theme='dawn',
                font_size=16,
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
            ),
            disabled=not self.ready(text_input)
        )
    

class QuoteOptionStRenderer(InputOptionStRenderer):
    """renders a QuoteOption"""

    _input_option: QuoteOption

    def ready(self, annotation: str) -> bool:
        """checks if annotation is ready for submission"""
        logging.info("QuoteOption checking: %s", annotation)
        ready = (
            self._input_option.is_annotation(annotation)
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
    
