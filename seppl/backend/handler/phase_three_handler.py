"""Phase Three Handlers"""

from __future__ import annotations
from dataclasses import asdict
import logging
from typing import List

import deepa2
from deepa2.parsers import Argument

from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    CUE_FIELDS,
    FORM_FIELDS,
)
from seppl.backend.inputoption import (
    InputOption,
    OptionFactory,
    ReasonsConjecturesOption,
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
        return "Excellent! 👍 This is a very good reconstruction. You're invited to further improve it. 😉"


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
        initial_reasons = [asdict(r) for r in request.new_da2item.reasons] if request.new_da2item.reasons else []
        initial_conjectures = [asdict(j) for j in request.new_da2item.conjectures] if request.new_da2item.conjectures else []
        premise_labels, conclusion_labels = self.get_premise_conclusion_labels(request)
        options.append(
            ReasonsConjecturesOption(
                source_text=request.new_da2item.source_text,
                initial_reasons=initial_reasons,
                initial_conjectures=initial_conjectures,
                premise_labels=premise_labels,
                conclusion_labels=conclusion_labels,
                question=f"Please add or revise annotations of reasons or conjectures.",
            )
        )


        # options for missing items
        missing = [
            field for field in CUE_FIELDS 
            if not getattr(request.new_da2item, field)
        ]
        options += OptionFactory.create_text_options(
            da2_fields=missing,
            da2_item=request.new_da2item,
            pre_initialized=False,
        )

        # don't ask to formalize intermediary conclusions if they don't exist
        form_fields = list(FORM_FIELDS)+[DA2KEY.k]
        parsed_argdown : Argument = request.metrics.from_cache("parsed_argdown")
        if parsed_argdown:
            if not any(s.is_conclusion for s in parsed_argdown.statements[:-1]):
                form_fields.remove(DA2KEY.fi)
        else:
            logging.error("PhaseThreeHandlerNoCompleteForm: no parsed argdown")

        # remaining items
        rest = [
            field for field in CUE_FIELDS
            if field not in missing
        ] + form_fields
        options += OptionFactory.create_text_options(
            da2_fields=rest,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        return options
