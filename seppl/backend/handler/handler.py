"""Handlers"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
import logging
from typing import Optional, Any, List
from dataclasses import dataclass

from deepa2 import DeepA2Item, DA2_ANGLES_MAP

from seppl.backend.inference import AbstractInferencePipeline
import seppl.backend.project as pjt
from seppl.backend.state_of_analysis import StateOfAnalysis
from seppl.backend.userinput import UserInput
from seppl.backend.da2metric import SofaEvaluator
from seppl.backend.inputoption import InputOption

CUE_FIELDS = (
    DA2_ANGLES_MAP.c,
    DA2_ANGLES_MAP.g,
    DA2_ANGLES_MAP.x,
    DA2_ANGLES_MAP.h,
)

FORM_FIELDS = (
    DA2_ANGLES_MAP.fp,
    DA2_ANGLES_MAP.fi,
    DA2_ANGLES_MAP.fc,
)


@dataclass
class Request:
    """dataclass representing data passed on to handlers"""
    query: UserInput
    state_of_analysis: StateOfAnalysis
    global_step: int
    _metrics: Optional[SofaEvaluator] = None # will be created by first handler
    new_da2item: DeepA2Item = None  # will be set by first handler

    @property
    def metrics(self) -> SofaEvaluator:
        """metrics of current state of analysis"""
        if self._metrics is None:
            raise ValueError("Fatal Error: SOFA metrics accessed before calculated")
        return self._metrics

    @metrics.setter
    def metrics(self, metrics: SofaEvaluator) -> None:
        """sets input options"""
        self._metrics = metrics

    def has_metrics(self) -> bool:
        """returns True if metrics are calculated and set"""
        return self._metrics is not None


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

    _next_handler: Optional[Handler] = None
    _inference: AbstractInferencePipeline

    def __init__(self, inference: AbstractInferencePipeline):
        self._inference = inference

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        # Returning a handler from here will let us link handlers in a
        # convenient way like this:
        # monkey.set_next(squirrel).set_next(dog)
        return handler

    @abstractmethod
    def is_responsible(self, request: Request) -> bool:
        """checks if this haadler is responsible for the given request"""

    @abstractmethod
    def get_feedback(
        self,
        request: Request,
    ) -> str:
        """creates user feedback to be displayed"""

    @abstractmethod
    def get_input_options(
        self,
        request: Request,
    ) -> List[InputOption]:
        """creates input options for next user-input"""

    def handle(self, request: Request) -> StateOfAnalysis:
        """defines the global strategy for processing user input"""
        logging.info("currently handling request: %s", type(self))

        old_sofa = request.state_of_analysis
        user_input: UserInput = request.query

        # revise comprehensive argumentative analysis (da2item)
        if not request.new_da2item:
            new_da2item = deepcopy(old_sofa.da2item)
            user_input.update_da2item(new_da2item)
            request.new_da2item = new_da2item
            logging.info("  updated da2item: %s", new_da2item)

        # return old sofa if no change
        if old_sofa.da2item == request.new_da2item:
            logging.info("  no change in da2item, returning old sofa")
            return old_sofa

        # evaluate revised analysis and update metrics
        if not request.has_metrics():
            metrics = deepcopy(old_sofa.metrics)
            metrics.update(new_da2item)
            request.metrics = metrics
            logging.info("  updated metrics: %s", metrics.all_scores())

        if self.is_responsible(request):
            logging.info("  responsible for request: %s", request)
            logging.info("  metrics in request: %s", request.metrics.all_scores())

            # create feedback
            feedback = self.get_feedback(request)
#            feedback = self.get_feedback(
#                old_sofa = old_sofa,
#                new_da2item = new_da2item,
#                metrics = metrics,
#                user_input = user_input,
#            )

            # create input options
            input_options = self.get_input_options(request)

            # create new state of analysis (sofa)
            new_sofa = old_sofa.create_revision(
                global_step = request.global_step,
                da2item = request.new_da2item,
                metrics = request.metrics,
                user_input = user_input,
                input_options = input_options,
                feedback = feedback,
            )

            return new_sofa

        elif self._next_handler:
            logging.info("  passing on to next handler: %s", type(self._next_handler))
            return self._next_handler.handle(request)

        raise Exception("No handler responsible for request: %s", request)
