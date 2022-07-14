"""Main project class"""

from __future__ import annotations
from typing import Optional, List, Any, Dict

from deepa2 import DeepA2Item
from seppl.backend.inference import AbstractInferencePipeline
from seppl.backend.userinput import UserInput
from seppl.backend.inputoption import InputOption
#import seppl.backend.handler as hdl
from seppl.backend.handler import (
    Request,
    AbstractHandler,
    ArgdownHandler,
    CueHandler,
    QuoteHandler
)


class StateOfAnalysis:
    """represent a current state of logical analysis"""
    _input_options: List[InputOption]
    global_step: int
    resumes_from: int
    visible_option: int
    da2item: DeepA2Item
    metrics: Dict[str, Any]
    feedback: str

    """state of the current analysis"""
    def __init__(self,
        text = "Some text",
        input_options: Optional[List[InputOption]] = None,
        global_step: int = 0,
    ):
        self.text = text
        self.project = text
        self.global_step = global_step
        self.visible_option = 0
        self.feedback = "That was excellent!"
        self._input_options = input_options
        self.da2item = DeepA2Item()

    @property
    def input_options(self) -> List[InputOption]:
        """input_options for next step"""
        return self._input_options


class Project:
    """representation of a reconstruction project"""

    step: int = 0
    inference: AbstractInferencePipeline = None

    def __init__(self, inference: AbstractInferencePipeline, **kwargs):
        self.current_step: int = 0
        self.max_steps: int = 10
        self.inference = inference
        self.state_of_analysis: StateOfAnalysis = StateOfAnalysis(**kwargs)

        # setup chain of responsibility for handling user queries
        self.handlers: List[AbstractHandler] = [
            ArgdownHandler(inference=self.inference),
            CueHandler(inference=self.inference),
            QuoteHandler(inference=self.inference),
        ]
        for i in range(1,len(self.handlers)):
            self.handlers[i-1].set_next(
                self.handlers[i-1]
            )

    def toggle_visible_option(self):
        """inceremnts index of visible option in state of analysis"""
        n_options = len(self.state_of_analysis.input_options)
        i_vis = self.state_of_analysis.visible_option
        i_vis = (i_vis + 1) % n_options
        self.state_of_analysis.visible_option = i_vis


    def update(self, query: Optional[UserInput]):
        """update the project given user input query"""
        self.step += 1
        request = Request(
            query = query,
            state_of_analysis = self.state_of_analysis,
        )
        new_sofa = self.handlers[0].handle(request)
        # update state of analysis
        self.state_of_analysis = new_sofa

