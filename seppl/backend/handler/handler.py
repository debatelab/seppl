"""Handlers"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict
from dataclasses import dataclass

from deepa2 import DeepA2Item, DeepA2Parser
import deepa2.metrics.metric_handler as metrics
from seppl.backend.inference import AbstractInferencePipeline
import seppl.backend.project as pjt
from seppl.backend.userinput import ArgdownInput, CueInput, QuoteInput, UserInput
from seppl.backend.inputoption import ChoiceOption, InputOption, TextOption


@dataclass
class Request:
    """dataclass representing data passed on to handlers"""
    query: UserInput
    state_of_analysis: pjt.StateOfAnalysis
    global_step: int

@dataclass
class DA2Metric:
    """
    dataclass representing metrics object that evaluates da2item
    """
    # argdown
    valid_argdown: int = None
    pc_structure: int = None
    consistent_usage: int = None
    no_petitio: int = None
    no_redundancy: int = None
    # formalizations
    valid_formalizations: float = None
    global_deductive_validity: int = None
    local_deductive_validity: float = None  # inference step-wise


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
    returning a new state of analysis and a list of options for next user input.
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

    def evaluate_da2item(self, da2item: DeepA2Item = None) -> DA2Metric:
        """
        calculates metrics for comprehensive argumentative analysis
        represented by da2item
        """
        metric = DA2Metric()
        # argdown
        parsed_argdown = DeepA2Parser.parse_argdown(da2item.argdown_reconstruction)
        metric.valid_argdown = metrics.ArgdownHandler.valid_argdown(parsed_argdown)
        metric.pc_structure = metrics.ArgdownHandler.pc_structure(parsed_argdown)
        metric.consistent_usage = metrics.ArgdownHandler.consistent_usage(parsed_argdown)
        metric.no_petitio = metrics.ArgdownHandler.no_petitio(parsed_argdown)
        metric.no_redundancy = metrics.ArgdownHandler.no_redundancy(parsed_argdown)
        # TODO
        # calculate more metrics
        return metric

    @abstractmethod
    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if self._next_handler:
            return self._next_handler.handle(request)

        return None

