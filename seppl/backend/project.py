"""Main project class"""

from __future__ import annotations
from typing import Optional, List, Any, Dict

from deepa2 import DeepA2Item
from seppl.backend.userinput import UserInput
from seppl.backend.inputoption import InputOption
import seppl.backend.handler as hdl


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
    ):
        self.text = text
        self.project = text
        self.global_step = 0
        self.visible_option = 0
        self.feedback = "That was excellent!"
        self._input_options = input_options
        self.da2item = DeepA2Item()


class Project:
    """representation of a reconstruction project"""

    step: int = 0

    def __init__(self):
        self.current_step: int = 0
        self.max_steps: int = 10
        self.state_of_analysis: StateOfAnalysis = StateOfAnalysis()

        # setup chain of responsibility for handling user queries
        self.handlers: List[hdl.AbstractHandler] = [
            hdl.ArgdownHandler(),
            hdl.CueHandler(),
            hdl.QuoteHandler(),
        ]
        for i in range(1,len(self.handlers)):
            self.handlers[i-1].set_next(
                self.handlers[i-1]
            )

    def update(self, query: Optional[UserInput]):
        """update the project given user input query"""
        self.step += 1
        request = hdl.Request(
            query = query,
            state_of_analysis = self.state_of_analysis,
        )
        new_sofa = self.handlers[0].handle(request)
        # update state of analysis
        self.state_of_analysis = new_sofa

