"""Handlers"""

from __future__ import annotations
import logging
from typing import List

import deepa2
from deepa2.parsers import Argument, DeepA2Parser, DeepA2Layouter
from seppl.backend.da2metric import ConclMatchesRecoScore, NoRedundancyScore, RecoCohSourceScore, ValidArgdownScore


from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    CUE_FIELDS,
)
from seppl.backend.handler.phase_three_handler import DA2KEY
from seppl.backend.inputoption import (
    InputOption,
    ChoiceOption,
    TextOption,
    OptionFactory,
)


class PhaseZeroHandler(AbstractUserInputHandler):
    """handles requests during reconstruction phase zero"""

    def is_responsible(self, request: Request) -> bool:
        """checks if project is in reconstruction phase 0"""
        metrics = request.metrics
        logging.info("PhaseZeroHandler: phase = %s", metrics.reconstruction_phase)
        return metrics.reconstruction_phase == 0

    def get_feedback(self, request: Request) -> str:
        """general user feedback concerning sofa as a whole"""
        da2item = request.new_da2item
        if not any(getattr(da2item,cue) for cue in list(CUE_FIELDS)+[DA2KEY.a]):
            return ""
        cues_qualifier = ""
        metrics = request.state_of_analysis.metrics
        if (
            metrics.individual_score(ConclMatchesRecoScore) 
            and metrics.individual_score(RecoCohSourceScore)
        ):
            cues_qualifier = "adequate "
        feedback = f"Good. We have an {cues_qualifier}informal analysis"

        if da2item.argdown_reconstruction:
            arg_qualifier = ""
            if (
                metrics.individual_score(ValidArgdownScore)
                and metrics.individual_score(NoRedundancyScore)
            ):
                arg_qualifier = "well-formed "
            else:
                arg_qualifier = "preliminary (though deficient) "
            feedback += f" and a {arg_qualifier}argument reconstruction."
        else:
            feedback += "."
        return feedback


class PhaseZeroHandlerNoCues(PhaseZeroHandler):
    """handles phase zero requests if there are no cues (substep 1)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if there are no cues"""
        da2item = request.new_da2item
        no_cues = not any(getattr(da2item,cue) for cue in CUE_FIELDS)
        logging.info("PhaseZeroHandler: no_cues = %s", no_cues)
        return PhaseZeroHandler.is_responsible(self, request) and no_cues

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates empty text input options for all cues"""
        options = OptionFactory.create_text_options(
            da2_fields=list(CUE_FIELDS),
            pre_initialized=False,
        )
        logging.info(" PhaseZeroHandlerNoCues created input_options: %s", options)
        return options

    def get_feedback(self, request: Request) -> str:
        feedback = (" We have no informal analysis yet. Summarizing "
        "the argument's key point (gist) or stating its central conclusion in"
        " your own words might be a good starting point.")
        feedback = feedback.strip()
        return feedback


class PhaseZeroHandlerNoArgd(PhaseZeroHandler):
    """handles phase zero requests if there is no argdown reconstruction"""

    def is_responsible(self, request: Request) -> bool:
        """checks if there is nor argdown reconstruction"""
        da2item = request.new_da2item
        no_argdown = not bool(da2item.argdown_reconstruction)
        return PhaseZeroHandler.is_responsible(self, request) and no_argdown

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += " But there is no argument reconstruction."
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates empty text input options for argdown
        and further text inputs for all cues"""
        da2_fields = ["argdown_reconstruction"] + list(CUE_FIELDS)
        options = OptionFactory.create_text_options(
            da2_fields=da2_fields,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options


class PhaseZeroHandlerIllfArgd(PhaseZeroHandler):
    """handles phase zero requests if argdown reconstruction is ill-formed"""

    def is_responsible(self, request: Request) -> bool:
        """checks if the argdown reconstruction is well-formed (ValidArgdownScore)"""
        metrics = request.metrics
        illformed = not bool(metrics.individual_score("ValidArgdownScore"))
        return PhaseZeroHandler.is_responsible(self, request) and illformed

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += (" Yet the argument reconstruction is ill-formed "
        "(incorrect argdown syntax). That needs to be corrected.")
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates text input option for argdown"""
        options = OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options



class PhaseZeroHandlerRedund(PhaseZeroHandler):
    """handles phase zero requests if argdown reconstruction is redundant"""

    def is_responsible(self, request: Request) -> bool:
        """checks if the argdown reconstruction is redundant (NoPetitioScore, NoRedundancyScore)"""
        metrics = request.metrics
        redundant = (
            not bool(metrics.individual_score("NoPetitioScore")) or
            not bool(metrics.individual_score("NoRedundancyScore"))
        )
        return PhaseZeroHandler.is_responsible(self, request) and redundant

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += (" More specifically, our argument reconstruction is redundant "
        "(premises and/or conclusions occur more than once).")
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates text input option for argdown"""
        options = OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options



class PhaseZeroHandlerMismatchCA(PhaseZeroHandler):
    """handles phase zero requests if argdown reconstruction doesn't match conclusion"""

    def is_responsible(self, request: Request) -> bool:
        """checks if argdown reconstruction and conclusion are provided and don'tr match (ConclMatchesRecoScore)"""
        da2item = request.new_da2item
        metrics = request.metrics
        mismatch = (
            da2item.argdown_reconstruction and
            da2item.conclusion and
            bool(metrics.individual_score("ValidArgdownScore")) and
            not bool(metrics.individual_score("ConclMatchesRecoScore"))
        )
        return PhaseZeroHandler.is_responsible(self, request) and mismatch

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += (" But the conclusion statement (separately provided "
        " as part of the informal analysis) doesn't match your "
        "argument reconstruction. You might want to change one "
        "or the other.")
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        # get parsed argument and retrieve conclusion
        parsed_argdown: Argument = request.metrics.from_cache("parsed_argdown")
        if not parsed_argdown:
            parsed_argdown = DeepA2Parser.parse_argdown(
                request.new_da2item.argdown_reconstruction
            )
        concl_from_ad = parsed_argdown.statements[-1].text
        # generate alternative reconstruction with LLM
        alternative_reco = None
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode="s+c => a",
        )
        if "generated_text" in outputs[0]:
            alternative_reco = outputs[0]["generated_text"]
            alternative_reco = self._inference.postprocess_argdown(alternative_reco)
        else:
            logging.warning("Generation failed for mode s+c=>a")
        # Assemble options:
        # Take conclusion from argument?
        options: List[InputOption] = [
            ChoiceOption(
                context=[f"Conclusion in argument reconstruction: `{concl_from_ad}`"],
                question="Do you want to use this conclusion as part of the informal analysis?",
                answers={"Yes": concl_from_ad},
                da2_field="conclusion",
            )
        ]
        # Adopt newly generated argument reconstruction?
        if alternative_reco:
            display_reco = InputOption.wrap_argdown(alternative_reco)
            options += [ChoiceOption(
                context=[
                    "SEPPL has come up with its own reconstruction:",
                    f"``` \n{display_reco} \n```"
                ],
                question="Do you want to adopt this reconstruction and further improve it?",
                answers={"Yes": alternative_reco},
                da2_field="argdown_reconstruction",
                inference_rater=inference_rater,
            )]
        # Manually revise current conclusion or reconstruction?
        options += OptionFactory.create_text_options(
            da2_fields=["conclusion", "argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options


class PhaseZeroHandlerCatchAll(PhaseZeroHandler):
    """handles any phase zero requests (serves as catch all)"""

    def is_responsible(self, request: Request) -> bool:  # pylint: disable=useless-parent-delegation
        """just checks for phase zero"""
        return PhaseZeroHandler.is_responsible(self, request)

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += (
            " SEPPL fails to see how your argument reconstruction "
            "is an interpretation OF the source text. You might revise and expand the "
            "reconstruction, or provide additional/better cues (e.g., gist, paraphrase) "
            "that close the gap between the source text and the reconstructed "
            "argument."
        )
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        # Generate alternative reconstruction, given CUEs
        alternative_reco = None
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        available_cues = [c for c in CUE_FIELDS if getattr(request.new_da2item,c)]
        mode = deepa2.GenerativeMode(
            name=None,
            target="argdown_reconstruction",
            input=["source_text"] + available_cues,
        )
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode=mode,
        )
        if "generated_text" in outputs[0]:
            alternative_reco = outputs[0]["generated_text"]
            alternative_reco = self._inference.postprocess_argdown(alternative_reco)
        else:
            logging.warning("Generation failed for mode s+c=>a")
        # Assemble options:
        options: List[InputOption] = []
        if alternative_reco:
            options += [TextOption(
                context=["Based on your hints, SEPPL has come up with "
                "its own reconstruction."],
                question="Feel free to use and adapt it.",
                initial_text=alternative_reco,
                da2_field="argdown_reconstruction",
                inference_rater=inference_rater,
            )]
        # Manually revise current conclusion or reconstruction?
        options += OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"]+list(CUE_FIELDS),
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options
