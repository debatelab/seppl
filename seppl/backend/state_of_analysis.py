"""Main project class"""

from __future__ import annotations
from copy import deepcopy
from typing import Optional, List, Any, Dict

from deepa2 import DeepA2Item
from seppl.backend.inference import AbstractInferencePipeline
from seppl.backend.userinput import UserInput
from seppl.backend.inputoption import InputOption
from seppl.backend.da2metric import SofaMetrics


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
    metrics: SofaMetrics
    feedback: Optional[str]

    """state of the current analysis"""
    def __init__(self,
        project_id: str,
        inference: AbstractInferencePipeline,
        source_text: str = None,
        global_step: int = 0,
        resumes_from_step: int = 0,
        input_options: List[InputOption] = None,
        feedback: str = None,
        da2item: DeepA2Item = None,
        metrics: SofaMetrics = None,
    ):
        self.project_id = project_id
        self.global_step = global_step
        self.resumes_from_step = resumes_from_step
        self.visible_option = 0
        self.feedback = feedback
        if input_options is None:
            self._input_options = []
        else:
            self._input_options = input_options
        if da2item is None:
            self.da2item = DeepA2Item(source_text = source_text)
        else:
            self.da2item = da2item
        if metrics is None:
            self.metrics = SofaMetrics(inference = inference)
        else:
            self.metrics = metrics

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
        global_step: int,
        user_input: UserInput,
        input_options: List[InputOption],
        metrics: SofaMetrics,
        da2item: DeepA2Item,
        feedback: str = None,
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
