"""Phase One Handlers"""

from __future__ import annotations
import logging
from typing import List

import deepa2
from deepa2.parsers import DeepA2Parser, DeepA2Layouter


from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    CUE_FIELDS,
)
from seppl.backend.inputoption import (
    InputOption,
    QuoteOption,
    TextOption,
    OptionFactory,
)



class PhaseOneHandler(AbstractUserInputHandler):
    """handles requests during reconstruction phase one"""

    def is_responsible(self, request: Request) -> bool:
        """checks if project is in reconstruction phase 0"""
        metrics = request.metrics
        logging.info("PhaseOneHandler: phase = %s", metrics.reconstruction_phase)
        return metrics.reconstruction_phase == 1

    def get_feedback(self, request: Request) -> str:
        """general user feedback concerning sofa as a whole"""
        # TODO: implement!
        return "Default Feedback Phase One."


class PhaseOneHandlerNoRJ(PhaseOneHandler):
    """handles phase zero requests if there are no reasons or conjectures (substep 1)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if there are no reasons or conjectures"""
        da2item = request.new_da2item
        no_rc = not any(getattr(da2item,cue) for cue in ["reasons", "conjectures"])
        logging.info("PhaseOneHandler: no reasons or conjectures = %s", no_rc)
        return PhaseOneHandler.is_responsible(self, request) and no_rc

    def get_input_options(self, request: Request) -> List[InputOption]:
        """
        creates quote input options for reasons and conjectures
        pre-initialized with SEPPL-generated quotes
        """
        options = []
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        for field, angle in zip(["reasons","conjectures"],["r","j"]):
            outputs, inference_rater = self._inference.generate(
                inputs=formatted_da2item,
                mode=f"s+a => {angle}",
            )
            if "generated_text" in outputs[0]:
                logging.info("PhaseOneHandler: generated quotes (%s) = %s", field, outputs[0]["generated_text"])
                quotes = DeepA2Parser.parse_quotes(
                    outputs[0]["generated_text"]
                )
            else:
                logging.warning("Generation failed for mode s+a => %s", angle)

            options.append(
                QuoteOption(
                    source_text=request.new_da2item.source_text,
                    initial_quotes=quotes,
                    inference_rater=inference_rater,
                    da2_field=field,
                    question=f"Please add or revise {field}.",
                )
            )
        logging.info(" PhaseOneHandlerNoRJ created input_options: %s", options)
        return options


class PhaseOneHandlerRNotAlgn(PhaseOneHandler):
    """handles phase one requests if reasons are not aligned with argdown reconstruction (substep 2)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if argdown reconstruction and reasons are provided and don'tr match (ReasonsAlignedScore)"""
        da2item = request.new_da2item
        metrics = request.metrics
        mismatch = (
            da2item.argdown_reconstruction and
            da2item.reasons and
            not bool(metrics.individual_score("ReasonsAlignedScore"))
        )
        return PhaseOneHandler.is_responsible(self, request) and mismatch

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += " But the reason statements identified don't refer to premises in your argument reconstruction."
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        options = []
        da2item = request.new_da2item
        options.append(
            QuoteOption(
                source_text=da2item.source_text,
                initial_quotes=da2item.reasons,
                da2_field="reasons",
                question="Please add or revise reasons given you argument reconstruction.",
            )
        )
        # Manually revise current reconstruction?
        options += OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options


class PhaseOneHandlerJNotAlgn(PhaseOneHandler):
    """handles phase one requests if conjectures are not aligned with argdown reconstruction (substep 2)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if argdown reconstruction and conjectures are provided and don't match (ConjecturesAlignedScore)"""
        da2item = request.new_da2item
        metrics = request.metrics
        mismatch = (
            da2item.argdown_reconstruction and
            da2item.conjectures and
            not bool(metrics.individual_score("ConjecturesAlignedScore"))
        )
        return PhaseOneHandler.is_responsible(self, request) and mismatch

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += " But the conjecture statements identified don't refer to premises in your argument reconstruction."
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        options = []
        da2item = request.new_da2item
        options.append(
            QuoteOption(
                source_text=da2item.source_text,
                initial_quotes=da2item.conjectures,
                da2_field="conjectures",
                question="Please add or revise conjectures given you argument reconstruction.",
            )
        )
        # Manually revise current reconstruction?
        options += OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options


class PhaseOneHandlerCatchAll(PhaseOneHandler):
    """handles any phase one requests (serves as catch all)"""

    def is_responsible(self, request: Request) -> bool:  # pylint: disable=useless-parent-delegation
        """just checks for phase one"""
        return PhaseOneHandler.is_responsible(self, request)

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += " Revise and expand so that your reasons and conjectures better cohere with the rest of the analysis (esp. argument reconstruction)."
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        # Generate alternative reconstruction, given CUEs
        alternative_reco = None
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        available_cues = [c for c in CUE_FIELDS if getattr(request.new_da2item,c)]
        available_quotes = [
            q for q in ["reasons", "conjectures"]
            if getattr(request.new_da2item,q)
        ]
        mode = deepa2.GenerativeMode(
            name=None,
            target="argdown_reconstruction",
            input=["source_text"] + available_quotes + available_cues,
        )
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode=mode,
        )
        if "generated_text" in outputs[0]:
            alternative_reco = outputs[0]["generated_text"]
            alternative_reco = self._inference.postprocess_argdown(alternative_reco)
        else:
            logging.warning("Generation failed for mode %s", mode)
        # Assemble options:
        options = []
        if alternative_reco:
            options += [TextOption(
                context=["Based on your hints, SEPPL has come up with "
                "an alternative reconstruction. Feel free to adapt it."],
                initial_text=alternative_reco,
                da2_field="argdown_reconstruction",
                inference_rater=inference_rater,
            )]
        # Manually revise current quotes?
        options += OptionFactory.create_quote_options(
            da2_fields=["reasons", "conjectures"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        # Manually revise current cues or reconstruction?
        options += OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"]+CUE_FIELDS,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options
