"""module for rendering projects and its components in streamlit"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, Callable, Optional
import streamlit as st

from seppl.backend.project import Project
from seppl.backend.userinput import UserInput, INPUT_TYPES
from seppl.backend.inputoption import (
    ChoiceOption,
    InputOption,
    TextOption,
    QuoteOption,
)


class _InputOptionStRenderer(ABC):
    """
    abstract class
    renders input option in streamlit
    """

    _input: Any = None
    _input_option: InputOption = None
    _submit: Callable = None # reference to project renderer's submit method

    def __init__(self,
        submit: Callable = None,
        input_option: InputOption = None,
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
        return user_input

    @abstractmethod
    def render(self):
        """renders the input option as streamlit gui"""


class _ChoiceOptionStRenderer(_InputOptionStRenderer):
    """renders a ChoiceOption"""

    _input_option: ChoiceOption = None

    def render(self):
        """renders the choice option as streamlit gui"""
        st.write(f"## ChoiceOption for: {self._input_option.da2_field}")
        st.write("### Context")
        for context_item in self._input_option.context:
            st.markdown(context_item)
        st.write(f"Q: {self._input_option.question}")
        if self._input_option.inference_rater:
            st.write("Display InferenceRater")
        for answer_label, answer in self._input_option.answers.items():
                st.button(
                    answer_label,
                    on_click = self._submit,
                    kwargs = dict(query=self.query(answer))
                )


class _TextOptionStRenderer(_InputOptionStRenderer):
    """renders a TextOption"""

    _input_option: TextOption = None

    def render(self):
        """renders the text option as streamlit gui"""
        st.write(f"## TextOption for: {self._input_option.da2_field}")
        if self._input_option.context:
            st.write("### Context\n")
            for context_item in self._input_option.context:
                st.write(context_item)
        st.write(f"Q: {self._input_option.question}")

        text_input = st.text_area(
            label="Enter or modify text below",
            height=200,
            value=self._input_option.initial_text)

        if self._input_option.inference_rater:
            st.write("Display InferenceRater")

        st.button(
            "Submit",
            on_click = self._submit,
            kwargs = dict(query=self.query(text_input))
        )
    

class _QuoteOptionStRenderer(_InputOptionStRenderer):
    """renders a QuoteOption"""

    _input_option: QuoteOption = None

    def render(self):
        """renders the quote option as streamlit gui"""
        st.write(f"## QuoteOption for: {self._input_option.da2_field}")
        if self._input_option.context:
            st.write("### Context")
            for context_item in self._input_option.context:
                st.write(context_item)

        annotation = st.text_area(
            label=self._input_option.question,
            height=200,
            value=self._input_option.initial_annotation
        )

        # TODO: check: if self._input_option.is_annotation(annotation):


        if self._input_option.inference_rater:
            st.write("Display InferenceRater")

        st.button(
            "Submit",
            on_click = self._submit,
            kwargs = dict(query=self.query(annotation))
        )
    



class ProjectStRenderer:
    """renders project in streamlit"""

    def __init__(self, project: Project):
        self._project: Project = project
        self._query: Optional[UserInput] = None

    def submit(self, query):
        """update"""
        self._project.update(query)

    def option_gui_factory(self, option: InputOption) -> _InputOptionStRenderer:
        """creates gui for option"""
        logging.debug(option)
        option_gui = None
        if isinstance(option, ChoiceOption):
            option_gui = _ChoiceOptionStRenderer(
                submit=self.submit,
                input_option=option
            )
        elif isinstance(option, TextOption):
            option_gui = _TextOptionStRenderer(
                submit=self.submit,
                input_option=option
            )
        elif isinstance(option, QuoteOption):
            option_gui = _QuoteOptionStRenderer(
                submit=self.submit,
                input_option=option
            )
        return option_gui


    def render(self):
        """renders the project as streamlit gui"""
        st.write(f"RENDERING THE PROJECT ({self._project.project_id})")
        st.write(f"source_text: {self._project.state_of_analysis.da2item.source_text}")
        st.write(f"step: {self._project.state_of_analysis.global_step}")
        st.write(f"resumes from: {self._project.state_of_analysis.resumes_from_step}")
        if self._project.state_of_analysis.metrics:
            metric_data = [
                {"name": key, "score": value}
                for key, value 
                in self._project.state_of_analysis.metrics.all_scores().items()
            ]
            st.table(data=metric_data)
        st.write(f"phase: {self._project.state_of_analysis.metrics.reconstruction_phase}")
        
        if self._project.state_of_analysis.global_step>0:
            st.write(f"feedback: {self._project.state_of_analysis.feedback}")
        st.write("argdown:")
        st.code(
            self._project.state_of_analysis.da2item.argdown_reconstruction,
            language=None
        )

        # setup options
        input_options = self._project.state_of_analysis.input_options
        visible_option = self._project.state_of_analysis.visible_option
        option_gui = self.option_gui_factory(
            input_options[visible_option]
        )

        # render options
        option_gui.render()
        if len(input_options)>1:
            st.button("Toggle Option", on_click = self._project.toggle_visible_option)
