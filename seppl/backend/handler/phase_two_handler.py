"""Phase Two Handlers"""

from __future__ import annotations
import logging
import textwrap
from typing import List, Tuple, Optional

import deepa2
from deepa2.parsers import Argument, DeepA2Layouter


from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler,
    FORM_FIELDS,
)
from seppl.backend.inference import InferenceRater
from seppl.backend.inputoption import (
    InputOption,
    ChoiceOption,
    TextOption,
    OptionFactory,
)
from seppl.backend.da2metric import Util

DA2KEY = deepa2.DA2_ANGLES_MAP

class PhaseTwoHandler(AbstractUserInputHandler):
    """handles requests during reconstruction phase one"""

    def is_responsible(self, request: Request) -> bool:
        """checks if project is in reconstruction phase 2"""
        metrics = request.metrics
        logging.info("PhaseTwoHandler: phase = %s", metrics.reconstruction_phase)
        return metrics.reconstruction_phase == 2

    def get_feedback(self, request: Request) -> str:
        """general user feedback concerning sofa as a whole"""
        qual_exe = ""
        if request.new_da2item.conjectures and request.new_da2item.reasons:
            qual_exe = "strongly "        
        feedback = (
            f"Very good. We have a basic reconstruction that is"
            f" {qual_exe}tied to the source text. But the logical analysis needs "
            f"to be improved."
        )
        return feedback

    def _generate_formalization(self, request: Request, field: str) -> Tuple[Optional[str], Optional[InferenceRater]]:
        """generates formalization for given field, uses all available formalizations"""
        if field not in FORM_FIELDS:
            logging.warning("PhaseTwoHandler: cannot generate formalization for field %s", field)
            return None, None
        # get parsed argument
        parsed_argdown : Argument = request.metrics.from_cache("parsed_argdown")
        if not parsed_argdown:
            return None, None
        # append premises and conclusion to da2item and format
        formatted_da2item = Util.expand_and_format_da2item(request.new_da2item, parsed_argdown)
        # key of propositions to be formalized
        if field == DA2KEY.fp:
            props_field = DA2KEY.p
        elif field == DA2KEY.fc:
            props_field = DA2KEY.c
        elif field == DA2KEY.fi:
            props_field = DA2KEY.i
        else:
            logging.warning("PhaseTwoHandler: cannot match formalization "
            "field %s to proposition", field)
            return None, None
        # available formalizations to be used as inputs
        avail_formalizations = [
            ff for ff in list(FORM_FIELDS)+[DA2KEY.k]
            if formatted_da2item[ff] and ff != field
        ]
        mode = deepa2.GenerativeMode(
            name = "name_is_not_used",
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
        feedback += (" Premises and intermediary conclusions are not "
        "consistently used in the argument's inference steps. (Note that "
        "inference information should be provided in the format "
        "'-- with inference-rule from (1) (2) --'.)")
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """creates options for argdown"""
        # generate alternative reconstruction with LLM
        alternative_reco = None
        # format argdown
        formatted_da2item = DeepA2Layouter().format(request.new_da2item)
        # declare current argdown as erroneaous reconstruction
        formatted_da2item[DA2KEY.e] = formatted_da2item[DA2KEY.e]
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode="s+e => a",
        )
        if "generated_text" in outputs[0]:
            alternative_reco = outputs[0]["generated_text"]
            alternative_reco = self._inference.postprocess_argdown(alternative_reco)
        else:
            logging.warning("PhaseTwoHandlerNoConsUsg: Generation failed for mode s+e=>a")
        # Assemble options
        options: List[InputOption] = []
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
        options = OptionFactory.create_text_options(
            da2_fields=[DA2KEY.a],
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
        feedback += " The formalization of the argument is incomplete."
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        """
        creates text input options for formalizations
        pre-initialized with SEPPL-generated formalizations
        """
        parsed_argdown : Argument = request.metrics.from_cache("parsed_argdown")
        if not parsed_argdown:
            logging.error("PhaseTwoHandlerNoCompleteForm: no parsed argdown")
            return []
        # expand and format da2item
        formatted_da2item = Util.expand_and_format_da2item(request.new_da2item, parsed_argdown)
        # don't ask to formalize intermediary conclusions if they don't exist
        form_fields = list(FORM_FIELDS)
        if not any(s.is_conclusion for s in parsed_argdown.statements[:-1]):
            form_fields.remove(DA2KEY.fi)
        # sort form_fields according to whether field is filled (empty first)
        form_fields.sort(key=lambda x: bool(formatted_da2item[x]))
        # create pre-initialized text options for formalizations
        options: List[InputOption] = []
        for field in form_fields:
            if formatted_da2item[field]:
                initial_text = formatted_da2item[field]
                inference_rater = None
                context = None
            else:
                # if no formalization exists, generate one
                initial_text, inference_rater = self._generate_formalization(request, field)
                context = ["SEPPL suggests the following formalization."]
            # create and append text option
            options.append(
                TextOption(
                    initial_text=initial_text,
                    inference_rater=inference_rater,
                    da2_field=field,
                    context=context,
                    question=f"Please add or revise {InputOption.da2_field_name(field)}.",
                )
            )
        # Further options
        option_fields = []
        # Option to add/revise keys, if some formalization has already been provided
        if any(getattr(request.new_da2item,ff) for ff in FORM_FIELDS):
            option_fields.append(DA2KEY.k)
        # argdown reconstruction
        option_fields.append(DA2KEY.a)
        # Create further TextOptions
        further_options: List[InputOption] = OptionFactory.create_text_options(
            da2_fields=option_fields,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )
        # if all formalizations have been provided, ask for keys first
        if all(bool(formatted_da2item[x]) for x in form_fields):
            options = further_options + options
        else:
            options = options + further_options

        logging.info(" PhaseTwoHandlerNoForm created input_options: %s", options)
        return options



class PhaseTwoHandlerIllfForm(PhaseTwoHandler):
    """handles phase two requests if some formalization is not well formed (substep 4)"""

    def is_responsible(self, request: Request) -> bool:
        """checks if formalizations is well formed (WellFormedFormScore / WellFormedKeysScore)"""
        da2item = request.new_da2item
        metrics = request.metrics
        illf = (
            da2item.argdown_reconstruction and
            bool(metrics.individual_score("CompleteFormalization")) and
            (
                not bool(metrics.individual_score("WellFormedFormScore")) or
                not bool(metrics.individual_score("WellFormedKeysScore"))
            )
        )
        return PhaseTwoHandler.is_responsible(self, request) and illf

    def get_feedback(self, request: Request) -> str:
        metrics = request.metrics
        feedback = super().get_feedback(request)
        if not metrics.individual_score("WellFormedFormScore"):
            feedback += " Some formalizations are not well formed."
        if not metrics.individual_score("WellFormedKeysScore"):
            feedback += " Some keys don't match the formalizations."
        feedback = feedback.strip()
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        parsed_argdown : Argument = request.metrics.from_cache("parsed_argdown")
        if not parsed_argdown:
            logging.error("PhaseTwoHandlerNoIllForm: no parsed argdown")
            return []
        # don't ask to formalize intermediary conclusions if they don't exist
        cache_fields = [
            "parsed_p_formalizations",
            "parsed_ic_formalizations",
            "parsed_c_formalizations",
        ]
        form_fields = list(FORM_FIELDS)
        if not any(s.is_conclusion for s in parsed_argdown.statements[:-1]):
            form_fields.remove(DA2KEY.fi)
            cache_fields.remove("parsed_ic_formalizations")
        # ignore all fields with well-formed formalizations
        for cuef, formf in zip(cache_fields, form_fields):
            if request.metrics.from_cache(cuef):
                form_fields.remove(formf)
                cache_fields.remove(cuef)

        # create pre-initialized text options for remaining (i.e. ill-formed) formalizations
        da2_fields = form_fields
        # plus, if ill-formed, for keys
        if not request.metrics.individual_score("WellFormedKeysScore"):
            da2_fields += [DA2KEY.k]

        # create options
        options = OptionFactory.create_text_options(
            da2_fields=da2_fields,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        logging.debug(" PhaseTwoHandlerIllfForm created input_options: %s", options)
        return options


class PhaseTwoHandlerCatchAll(PhaseTwoHandler):
    """handles any phase two requests (serves as catch all)"""

    def is_responsible(self, request: Request) -> bool:  # pylint: disable=useless-parent-delegation
        """just checks for phase two"""
        return PhaseTwoHandler.is_responsible(self, request)

    def get_feedback(self, request: Request) -> str:
        feedback = super().get_feedback(request) + " SEPPL judges: "
        metrics = request.metrics
        if not metrics.individual_score("FormCohRecoScore"):
            feedback += (" Given your keys, the formalization doesn't cohere with "
            "your argument reconstruction.")
        if not metrics.individual_score("GlobalDeductiveValidityScore"):
            feedback += (" Given your formalization, the argument is not globally "
            "deductively valid.")
        if not metrics.individual_score("LocalDeductiveValidityScore"):
            feedback += (" Given your formalization, some individual sub-argument "
            "is not deductively valid.")
        return feedback

    def get_input_options(self, request: Request) -> List[InputOption]:
        parsed_argdown : Argument = request.metrics.from_cache("parsed_argdown")
        if not parsed_argdown:
            logging.error("PhaseTwoHandlerNoCompleteForm: no parsed argdown")
            return []
        # Generate alternative reconstruction, given premises and conclusion of current argument
        alternative_reco = None
        formatted_da2item = Util.expand_and_format_da2item(
            request.new_da2item,
            parsed_argdown,
        )
        mode = deepa2.GenerativeMode(
            name = "name_is_not_used",
            target = DA2KEY.a,
            input = [DA2KEY.p, DA2KEY.c],
        )
        outputs, inference_rater = self._inference.generate(
            inputs=formatted_da2item,
            mode=mode,
        )
        if "generated_text" in outputs[0]:
            alternative_reco = outputs[0]["generated_text"]
            alternative_reco = self._inference.postprocess_argdown(alternative_reco)
            logging.debug("PhaseTwoHandler: generated alternative_reco = %s", alternative_reco)
        else:
            logging.warning("Generation failed for mode %s", mode)

        # Assemble options
        da2_fields  = [DA2KEY.a]
        da2_fields += list(FORM_FIELDS)
        da2_fields += [DA2KEY.k]
        # ignore intermediary conclusions if they don't exist
        if not any(s.is_conclusion for s in parsed_argdown.statements[:-1]):
            da2_fields.remove(DA2KEY.fi)

        options: List[InputOption] = []

        if alternative_reco:
            display_reco = InputOption.wrap_argdown(alternative_reco)
            options += [ChoiceOption(
                context=[
                    "SEPPL has come up with its own reconstruction:",
                    f"``` \n{display_reco} \n```"
                ],
                question="Do you want to adopt this reconstruction and further improve it?",
                answers={"Yes": alternative_reco},
                da2_field=DA2KEY.a,
                inference_rater=inference_rater,
            )]

        options += OptionFactory.create_text_options(
            da2_fields=da2_fields,
            da2_item=request.new_da2item,
            pre_initialized=True,
        )

        return options
