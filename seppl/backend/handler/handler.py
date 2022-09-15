"""Handlers"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional, Any, List, Dict
from dataclasses import dataclass

from deepa2 import DeepA2Item

from seppl.backend.inference import AbstractInferencePipeline
import seppl.backend.project as pjt
from seppl.backend.userinput import UserInput


@dataclass
class Request:
    """dataclass representing data passed on to handlers"""
    query: UserInput
    state_of_analysis: pjt.StateOfAnalysis
    global_step: int


class Handler(ABC):
    """
    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a request.
    """

    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        """set next handler in chain"""

    @abstractmethod
    def handle(self, request: Request) -> Any:
        """handle request"""


class AbstractUserInputHandler(Handler):
    """
    The default chaining behavior can be implemented inside a base handler
    class.
    Every Handler handles a `request` with keys "query", "state_of_analysis",
    returning a new state of analysis, included a list of options for next user input.
    """

    _next_handler: Handler = None
    _inference: AbstractInferencePipeline = None
    
    def __init__(self, inference: AbstractInferencePipeline = None):
        self._inference = inference

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        # Returning a handler from here will let us link handlers in a
        # convenient way like this:
        # monkey.set_next(squirrel).set_next(dog)
        return handler

    @abstractmethod
    def is_responsible(self, request: Request) -> bool:
        """checks if this hnadler is responsible for the given request"""

    @abstractmethod
    def get_feedback(
        self,
        old_sofa: pjt.StateOfAnalysis = None,
        new_da2item: DeepA2Item = None,
        metrics: pjt.SofaEvaluation = None,
        user_input: UserInput = None,
    ) -> str:
        """creates user feedback to be displayed"""

    @abstractmethod
    def get_input_options(
        self,
        old_sofa: pjt.StateOfAnalysis = None,
        new_da2item: DeepA2Item = None,
        metrics: pjt.SofaEvaluation = None,
        user_input: UserInput = None,
    ) -> str:
        """creates input options for next user-input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        """defines the global strategy for processing user input"""
        if self.is_responsible(request):
            old_sofa = request.state_of_analysis

            # revise comprehensive argumentative analysis (da2item)
            user_input: UserInput = request.query
            new_da2item = deepcopy(old_sofa.da2item)
            user_input.update_da2item(new_da2item)

            # evaluate revised analysis and update metrics
            metrics = deepcopy(old_sofa.metrics)
            metrics.update(new_da2item)

            # create feedback
            feedback = self.get_feedback(
                old_sofa = old_sofa,
                new_da2item = new_da2item,
                metrics = metrics,
                user_input = user_input,
            )

            # create input options
            input_options = self.get_input_options(
                old_sofa = old_sofa,
                new_da2item = new_da2item,
                metrics = metrics,
                user_input = user_input,
            )

            # create new state of analysis (sofa)
            new_sofa = old_sofa.create_revision(
                global_step = request.global_step,
                input_options = input_options,
                user_input = user_input,
                feedback = feedback,
                da2item = new_da2item,
                metrics = metrics,
            )

            return new_sofa

        elif self._next_handler:
            return self._next_handler.handle(request)

        return None
