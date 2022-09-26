"""Phase Two Handlers"""

from __future__ import annotations
import logging
from typing import List, Tuple

import deepa2
from deepa2.parsers import DeepA2Parser, DeepA2Layouter


from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    CUE_FIELDS,
    FORM_FIELDS,
)
from seppl.backend.inference import InferenceRater
from seppl.backend.inputoption import (
    InputOption,
    QuoteOption,
    TextOption,
    OptionFactory,
)



class PhaseTwoHandler(AbstractUserInputHandler):
    """handles requests during reconstruction phase one"""

    def is_responsible(self, request: Request) -> bool:
        """checks if project is in reconstruction phase 2"""
        metrics = request.metrics
        logging.info("PhaseTwoHandler: phase = %s", metrics.reconstruction_phase)
        return metrics.reconstruction_phase == 2

    def get_feedback(self, request: Request) -> str:
        """general user feedback concerning sofa as a whole"""
        # TODO: implement!
        return "Default Feedback Phase Two."

    def _generate_formalization(self, request: Request, field: str) -> Tuple[str, InferenceRater]:
        """generates formalization for given field, uses all available formalizations"""
        if field not in FORM_FIELDS:
            logging.warning("PhaseTwoHandler: cannot generate formalization for field %s", field)
            return None, None
        # propositions to be formalized
        props_field = field[:-len("_formalized")]
        props = request.metrics.from_cache(props_field)
        if not props:
            logging.info("PhaseTwoHandler: nothing to formalize for field %s", field)
            return None, None
        avail_formalizations = [
            ff for ff in FORM_FIELDS+["plchd_substitutions"]
            if request.new_da2item[ff] and ff != field
        ]
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        mode = deepa2.GenerativeMode(
            name = "not_used",
            target = field,
            input = [props_field]+avail_formalizations,
        )
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode=mode,
        )
        if "generated_text" in outputs[0]:
            formalization = outputs[0]["generated_text"]
            logging.info("PhaseTwoHandler: generated formalization (%s) = %s", field, formalization)
        else:
            logging.warning("Generation failed for mode %s", mode)
            return None, None

        return formalization, inference_rater



class PhaseTwoHandlerNoConsUsg(PhaseTwoHandler):
    """handles phase two requests if premises and intermediary conclusions
    are not consistently used in the argument's inferences (substep 1)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if the argdown reconstruction doesn't consistently
        use props (ConsistentUsageScore)"""
        metrics = request.metrics
        no_consistent_usg = not bool(metrics.individual_score("ConsistentUsageScore"))
        return PhaseTwoHandler.is_responsible(self, request) and no_consistent_usg

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += """ But premises and intermediary conclusions are not
        "consistently used in the argument's inference."""
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates text input option for argdown"""
        options = OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        return options


class PhaseTwoHandlerNoCompleteForm(PhaseTwoHandler):
    """handles phase two requests if there is no complete formalization (substep 2+3)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if formalizations is complete"""
        da2item = request.new_da2item
        metrics = request.metrics
        no_forms = not any(getattr(da2item,ff) for ff in FORM_FIELDS)
        logging.info("PhaseTwoHandler: no formalizations = %s", no_forms)
        no_compl_form = not bool(metrics.individual_score("CompleteFormalization"))
        logging.info("PhaseTwoHandler: no complete formalization = %s", no_compl_form)
        return PhaseTwoHandler.is_responsible(self, request) and (no_forms or no_compl_form)


    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        feedback += """ But the formalization of the argument is incomplete."""
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """
        creates text input options for formalizations
        pre-initialized with SEPPL-generated formalizations
        """
        options = []
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        for field in FORM_FIELDS:
            if formatted_da2item[field]:
                initial_text = formatted_da2item[field]
                inference_rater = None
            else:
                # if no formalization exists, generate one
                initial_text, inference_rater = self._generate_formalization(request, field)
            # create and append text option 
            options.append(
                TextOption(
                    initial_text=initial_text,
                    inference_rater=inference_rater,
                    da2_field=field,
                    question=f"Please add or revise {field}.",
                )
            )
        # TextOption for argdown reconstruction 
        options += OptionFactory.create_text_options(
            da2_fields=["argdown_reconstruction"],
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        logging.info(" PhaseTwoHandlerNoForm created input_options: %s", options)
        return options



class PhaseTwoHandlerIllfForm(PhaseTwoHandler):
    """handles phase two requests if some formalization is not well formed (substep 4)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if argdown reconstruction and conjectures are provided and don't match (WellFormedFormScore)"""
        da2item = request.new_da2item
        metrics = request.metrics
        mismatch = (
            da2item.argdown_reconstruction and
            da2item.conjectures and
            not bool(metrics.individual_score("ConjecturesAlignedScore"))
        )
        return PhaseTwoHandler.is_responsible(self, request) and mismatch

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


class PhaseTwoHandlerCatchAll(PhaseTwoHandler):
    """handles any phase two requests (serves as catch all)"""

    def is_responsible(self, request: Request) -> bool:  # pylint: disable=useless-parent-delegation
        """just checks for phase two"""
        return PhaseTwoHandler.is_responsible(self, request)

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request)
        metrics = request.metrics
        if not metrics.individual_score("WellFormedKeysScore"):
            feedback += " The keys don't match your formalization."
        if not metrics.individual_score("FormCohRecoScore"):
            feedback += """ Given your keys, the formalization doesn't cohere with
            your argument reconstruction."""
        if not metrics.individual_score("GlobalDeductiveValidityScore"):
            feedback += """ Given your formalization, the argument is not globally
            deductively valid."""
        if not metrics.individual_score("GlobalDeductiveValidityScore"):
            feedback += """ Given your formalization, some individual sub-argument
            is not deductively valid."""
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
