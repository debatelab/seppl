"""Main project class"""

from __future__ import annotations
from copy import deepcopy
import dataclasses
from typing import Optional, List, Any, Dict

from deepa2 import DeepA2Item
from seppl.backend.inference import AbstractInferencePipeline
from seppl.backend.userinput import UserInput
from seppl.backend.inputoption import InputOption
#import seppl.backend.handler as hdl
from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    ArgdownHandler,
    CueHandler,
    QuoteHandler,
    FormalizationHandler,
)
from seppl.backend.da2metric import DA2Metric


class StateOfAnalysis:
    """
    represent a current state of logical analysis

    _user_input: UserInput the user has provided at previous step and
            that was used to construct this state of analysis
    _input_options: List[InputOption] available to-be-shown for next
            user input 
    global_step: int global step of this sofa in project history
    resumes_from_step: int global step of earlier sofa where this sofa
            resumes from (resumes_from_step < global_step)
    visible_option: int index of option that is currently shown to user
    da2item: DeepA2Item comprehensive argumentative analysis
    metrics: Dict[str, Any] metrics corresponding to and evaluating
            da2item
    feedback: Optional[str] to be shown, refers to quality of previous
            user input (_user_input)
    """
    _user_input: UserInput
    _input_options: List[InputOption]
    global_step: int
    resumes_from_step: int
    visible_option: int
    da2item: DeepA2Item
    metrics: DA2Metric # TODO: implement SofaEvaluation!
    feedback: Optional[str]

    """state of the current analysis"""
    def __init__(self,
        project_id = "project-id",
        global_step: int = 0,
        resumes_from_step: int = 0,
        input_options: Optional[List[InputOption]] = None,
    ):
        self.project_id = project_id
        self.global_step = global_step
        self.resumes_from_step = resumes_from_step
        self.visible_option = 0
        self.feedback = "That was excellent!"
        self._input_options = input_options
        self.da2item = DeepA2Item()
        self.metrics = DA2Metric()

    @property
    def input_options(self) -> List[InputOption]:
        """input_options for next step"""
        return self._input_options

    @input_options.setter
    def input_options(self, input_options: List[InputOption]) -> None:
        """sets input options"""
        self._input_options = input_options

    @property
    def user_input(self) -> UserInput:
        """user_input from last step"""
        return self._user_input

    @user_input.setter
    def user_input(self, user_input: UserInput) -> None:
        """sets user input"""
        self._user_input = user_input

    def create_revision(self,
        global_step: int = None,
        user_input: UserInput = None,
        input_options: List[InputOption] = None,
        feedback: str = None,
        metrics: DA2Metric = None,
        da2item: DeepA2Item = None,
        **kwargs,
    ) -> StateOfAnalysis:
        """
        creates a revised copy as next sofa
        """
        revision: StateOfAnalysis = deepcopy(self)
        revision.visible_option = 0
        revision.global_step = global_step
        revision.resumes_from_step = self.global_step
        revision.user_input = user_input
        revision.input_options = input_options
        revision.feedback = feedback
        revision.metrics = metrics
        revision.da2item = da2item
        return revision

class Project:
    """representation of a reconstruction project"""

    inference: AbstractInferencePipeline = None
    project_id: str  # unique identifier of this project
    global_step: int  # global counter of sofas in project history

    def __init__(self, inference: AbstractInferencePipeline, **kwargs):
        self.inference = inference
        self.project_id = "PROJECT-ID"
        self.state_of_analysis: StateOfAnalysis = StateOfAnalysis(
            project_id = self.project_id,
            **kwargs
        )
        self.global_step = 0

        # setup chain of responsibility for handling user queries
        self.handlers: List[AbstractUserInputHandler] = [
            ArgdownHandler(inference=self.inference),
            CueHandler(inference=self.inference),
            QuoteHandler(inference=self.inference),
            FormalizationHandler(inference=self.inference),
        ]
        for i in range(1,len(self.handlers)):
            self.handlers[i-1].set_next(
                self.handlers[i-1]
            )

    def toggle_visible_option(self):
        """increments index of visible option in state of analysis"""
        n_options = len(self.state_of_analysis.input_options)
        i_vis = self.state_of_analysis.visible_option
        i_vis = (i_vis + 1) % n_options
        self.state_of_analysis.visible_option = i_vis


    def update(self, query: Optional[UserInput]):
        """update the project given user input query"""
        self.global_step += 1
        request = Request(
            query = query,
            state_of_analysis = self.state_of_analysis,
            global_step = self.global_step,
        )
        new_sofa = self.handlers[0].handle(request)
        # TODO: add old sofa to history before updating
        # update state of analysis
        self.state_of_analysis = new_sofa
