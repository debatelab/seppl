"""Handlers"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass

from deepa2 import DeepA2Item
import seppl.backend.project as pjt
from seppl.backend.userinput import ArgdownInput, CueInput, QuoteInput, UserInput
from seppl.backend.inputoption import InputOption


@dataclass
class Request:
    """dataclass representing data passed on to handlers"""
    query: UserInput
    state_of_analysis: pjt.StateOfAnalysis

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


class AbstractHandler(Handler):
    """
    The default chaining behavior can be implemented inside a base handler
    class.
    Every Handler handles a `request` with keys "query", "state_of_analysis",
    returning a new state of analysis and a list of options for next user input.
    """

    _next_handler: Handler = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        # Returning a handler from here will let us link handlers in a
        # convenient way like this:
        # monkey.set_next(squirrel).set_next(dog)
        return handler

    @abstractmethod
    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if self._next_handler:
            return self._next_handler.handle(request)

        return None



class ArgdownHandler(AbstractHandler):
    """handles argdown input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, ArgdownInput):
            old_sofa = request.state_of_analysis
            input_options = []
            new_sofa = pjt.StateOfAnalysis(
                text = old_sofa.text+" *and more*",
                input_options = input_options,
            )
            # TODO
            return new_sofa

        return super().handle(request)


class CueHandler(AbstractHandler):
    """handles cue (gist, paraphrase, etc.) input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, CueInput):
            new_sofa = pjt.StateOfAnalysis()
            # TODO
            return new_sofa

        return super().handle(request)


class QuoteHandler(AbstractHandler):
    """handles quote (reasons, conjectures) input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, QuoteInput):
            new_sofa = pjt.StateOfAnalysis()
            # TODO
            return new_sofa

        return super().handle(request)

