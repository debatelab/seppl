"""Phase Three Handlers"""

from __future__ import annotations
import logging
from typing import List

import deepa2

from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
)
from seppl.backend.inputoption import (
    InputOption,
    OptionFactory,
)

DA2KEY = deepa2.DA2_ANGLES_MAP

class PhaseThreeHandler(AbstractUserInputHandler):
    """handles requests during reconstruction phase three"""

    def is_responsible(self, request: Request) -> bool:
        """checks if project is in reconstruction phase 2"""
        metrics = request.metrics
        logging.info("PhaseThreeHandler: phase = %s", metrics.reconstruction_phase)
        return metrics.reconstruction_phase == 3

    def get_feedback(self, request: Request) -> str:
        """general user feedback concerning sofa as a whole"""
        return "Excellent! Default Feedback Phase Three."


class PhaseThreeHandlerCatchAll(PhaseThreeHandler):
    """handles any phase three requests (serves as catch all)"""

    def is_responsible(self, request: Request) -> bool:  # pylint: disable=useless-parent-delegation
        """just checks for phase two"""
        return PhaseThreeHandler.is_responsible(self, request)

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request) # pylint: disable=useless-super-delegation
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:

        # Assemble options

        options = []

        # argdown
        options += OptionFactory.create_text_options(
            da2_fields=[DA2KEY.a],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        # reasons and conjectures
        options += OptionFactory.create_quote_options(
            da2_fields=[DA2KEY.r, DA2KEY.j],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        return options
