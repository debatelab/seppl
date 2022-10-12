"""DAMetric Class that contains metrics of DA2Item and can update itself"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
import dataclasses
from itertools import chain, combinations
from lib2to3.pgen2.pgen import generate_grammar
import logging
from typing import Iterable, List, Dict, Any, Optional, Type, Union

from deepa2 import DeepA2Item, DeepA2Parser, DeepA2Layouter, ArgdownStatement, DA2_ANGLES_MAP
from deepa2.parsers import Argument
import deepa2.metrics.metric_handler as metrics
from nltk.inference.prover9 import Prover9
import nltk.sem.logic

from seppl.backend.inference import AbstractInferencePipeline


# TODO: write tests for this metrics class!

# """
# The main idea is to define different *phases* and to make the logic
# dependent on the phase of the project. The *phase* of the project
# in turn is a function of (a) available components (da2item) and
# (b) their evaluation (metrics) in the current state of analysis.
# """

RECONSTRUCTION_PHASES = [
    "0_BASE_STAGE",
    "1_EXEGETIC_STAGE",
    "2_FORMALIZATION_STAGE",
    "3_FINAL_STAGE",
]

class Util:
    """simple utilities class"""

    @staticmethod
    def powerset(iterable) -> Iterable:
        "powerset([1,2,3]) → () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        my_list = list(iterable)
        return chain.from_iterable(combinations(my_list, r) for r in range(len(my_list)+1))

    @staticmethod
    def available_cues(da2item: DeepA2Item) -> List[str]:
        """return list of available cues (angle ids) in da2item"""
        cues = []
        if da2item.gist:
            cues.append("g")
        if da2item.context:
            cues.append("x")
        if da2item.source_paraphrase:
            cues.append("h")
        return cues

    @staticmethod
    def expand_and_format_da2item(da2item: DeepA2Item, argdown: Argument) -> DeepA2Item:
        """adds premises and conclusions, and layouts da2item"""
        da2item_tmp = deepcopy(da2item)
        # add premises, conclusions, and intermediary conclusions to temp da2item
        if argdown:
            premises = [s for s in argdown.statements if not s.is_conclusion]
            conclusion = [argdown.statements[-1]]
            interm_conclusions = [s for s in argdown.statements[:-1] if s.is_conclusion]

            da2item_tmp.premises=[
                ArgdownStatement(text=p.text,ref_reco=p.label)
                for p in premises
            ]
            da2item_tmp.intermediary_conclusions=[
                ArgdownStatement(text=p.text,ref_reco=p.label)
                for p in interm_conclusions
            ]
            da2item_tmp.conclusion=[
                ArgdownStatement(text=p.text,ref_reco=p.label)
                for p in conclusion
            ]

        # layout temporary da2item
        layouter=DeepA2Layouter()
        formatted_da2item = layouter.format(da2item_tmp)
        return formatted_da2item


class Metric(ABC):
    """abstract base class of individual metric"""

    #inference pipeline
    _inference: AbstractInferencePipeline
    # cache, especially for default_reconstruction
    _cache: Dict[str,Any]
    # da2item to be evaluated
    da2item: DeepA2Item = None
    # current score of metric
    score: Optional[Union[int, float]] = None

    def __init__(self,
        inference: AbstractInferencePipeline,
        cache: Dict[str, Any],
        da2item: DeepA2Item = None,
    ):
        self._inference = inference
        self._cache = cache
        self.da2item = da2item
        if da2item:
            self.score = self.calculate()

    @abstractmethod
    def critical_angles(self) -> List[str]:
        """list of angles watched by metric"""

    @property
    def satisficed(self) -> bool:
        """is metric satisficed?"""
        return bool(self.score)

    @abstractmethod
    def calculate(self) -> Union[int, float]:
        """calculates metric"""

    def update_cache(self,
        da2item: DeepA2Item,  # pylint: disable=unused-argument
        cached_items_updated: List[str]
    ) -> List[str]:
        """
        update any cached items
        returns extended list of updated items
        """
        return cached_items_updated

    def update_score(self, da2item: DeepA2Item = None) -> None:
        """update da2item and, if required, re-calculate score"""
        recalculate = False
        if da2item:
            if not self.da2item:
                recalculate = True
            elif any(
                getattr(da2item, angle) != getattr(self.da2item, angle)
                for angle in self.critical_angles()
            ):
                recalculate = True

        self.da2item = da2item
        if recalculate:
            self.score = self.calculate()

    @property
    def formatted_da2item(self) -> Dict[str,Optional[str]]:
        """return formatted da2item"""
        parsed_argdown: Argument = None
        if "parsed_argdown" in self._cache:
            if self._cache["parsed_argdown"]:
                parsed_argdown = self._cache["parsed_argdown"]
        return Util.expand_and_format_da2item(self.da2item, parsed_argdown)


class GlobalCompletenessScore(Metric):
    """scores ratio of essential da2 fields that are not None"""

    _ignored_fields: str = "stghxe"

    def calculate(self):
        if not self.da2item:
            return 0
        count_not_none = 0
        count_all = 0
        for field in dataclasses.fields(DA2_ANGLES_MAP):
            if field.name not in self._ignored_fields:
                count_all += 1
                if getattr(self.da2item, getattr(DA2_ANGLES_MAP, field.name)):
                    count_not_none += 1

        score = count_not_none / count_all
        return score

    @property
    def satisficed(self) -> bool:
        """are there any essential da2 fields provided?"""    
        return bool(self.score)

    def critical_angles(self) -> List[str]:
        return [
            getattr(DA2_ANGLES_MAP,field.name)
            for field in dataclasses.fields(DA2_ANGLES_MAP)
            if field.name not in self._ignored_fields
        ]


class ArgdownMetric(Metric):
    """metric that requires parsed argdown"""

    def update_cache(self,
        da2item: DeepA2Item,
        cached_items_updated: List[str]
    ) -> List[str]:
        """update cache with newly provided da2item"""
        cached_items = cached_items_updated
        reparse = False
        if ("parsed_argdown" not in cached_items):
            if not "parsed_argdown" in self._cache or not self.da2item:
                reparse = True
            elif self.da2item.argdown_reconstruction != da2item.argdown_reconstruction:
                reparse = True
        if reparse:
            if da2item.argdown_reconstruction is None:
                self._cache["parsed_argdown"] = None
            else:
                self._cache["parsed_argdown"] = DeepA2Parser.parse_argdown(
                    da2item.argdown_reconstruction
                )
            cached_items = cached_items + ["parsed_argdown"]

        return cached_items

    def critical_angles(self) -> List[str]:
        return ["argdown_reconstruction"]


class ValidArgdownScore(ArgdownMetric):
    """scores whether argdown is valid (returns 1 or 0)"""

    def calculate(self):
        score = metrics.ArgdownHandler.valid_argdown(self._cache["parsed_argdown"])
        return score

class PCStructureScore(ArgdownMetric):
    """scores whether argdown has premise-conclusion structure (returns 1 or 0)"""

    def calculate(self):
        score = metrics.ArgdownHandler.pc_structure(self._cache["parsed_argdown"])
        return score

class ConsistentUsageScore(ArgdownMetric):
    """scores whether premises and intermediary conclusions are used consistently (returns 1 or 0)"""

    def calculate(self):
        score = metrics.ArgdownHandler.consistent_usage(self._cache["parsed_argdown"])
        return score

class NoPetitioScore(ArgdownMetric):
    """scores whether argument is not a petitio (returns 1 or 0)"""

    def calculate(self):
        score = metrics.ArgdownHandler.no_petitio(self._cache["parsed_argdown"])
        return score

class NoRedundancyScore(ArgdownMetric):
    """scores whether argument is not redundant (returns 1 or 0)"""

    def calculate(self):
        score = metrics.ArgdownHandler.no_redundancy(self._cache["parsed_argdown"])
        return score

class ArgumentSizeScore(ArgdownMetric):
    """scores size of argdown, if valid"""

    def calculate(self):
        if not self.da2item.argdown_reconstruction:
            return None
        parsed_argdown: Argument = self._cache["parsed_argdown"]
        if not parsed_argdown:
            return None
        n_statements = len(parsed_argdown.statements)
        score = 1.0 - (0.9 ** n_statements)
        return score

    @property
    def satisficed(self) -> bool:
        """are there any statements in parsed argdown?"""    
        return bool(self.score)


class ConclMatchesRecoScore(ArgdownMetric):
    """
    scores whether conclusion matches argdown, i.e.:
    if the `conclusion` is non-empty, it is identical with the 
    final conclusion of the `argdown_reconstruction`
    """

    def calculate(self):
        if not self.da2item.conclusion:
            return None
        score = 0
        if self._cache["parsed_argdown"]:
            score = int(
                self._cache["parsed_argdown"].statements[-1].text.strip().lower() == 
                self.da2item.conclusion[0].text.strip().lower()
            )
        return score

    def critical_angles(self) -> List[str]:
        return super().critical_angles() + ["conclusion"]



class RecoCohSourceScore(ArgdownMetric):
    """
    scores 1 if `argdown_reconstruction` minimally coheres
    with a `source_text`, i.e. iff
    1. loss(`A`,`S`) < loss(`A'`,`S`) for some model-generated reconstruction `A'` OR
    2. loss(`A`,`S+C+CUE`) < loss(`A`,`S`) for some user-provided cues,
        i.e. `gist`, `context`, `source_paraphrase`, and a user-provided `conclusion`.
    """

    def calculate(self):
        if not self._inference or self.da2item.argdown_reconstruction is None:
            return None
        if not self.da2item.source_text or not self._cache["parsed_argdown"]:
            return 0
        # check condition 1
        ## copy da2item and replace argdown with default reconstruction 
        default_inputs = deepcopy(dataclasses.asdict(self.da2item))
        default_inputs.update(
            {
                "argdown_reconstruction": self._cache["default_reconstruction"]
            }
        )
        default_loss = self._inference.loss(inputs=default_inputs, mode="s => a")
        inputs = dataclasses.asdict(self.da2item)
        current_loss = self._inference.loss(inputs=inputs, mode="s => a")
        if  current_loss <= default_loss:
            return 1
        # check condition 2
        if not self.da2item.conclusion:
            return 0
        cues = Util.available_cues(da2item=self.da2item)
        input_angles = [["s", "c"]+list(ss) for ss in list(Util.powerset(cues))]
        modes = [f"{' + '.join(l)} => a" for l in input_angles]
        coheres = any(
            (self._inference.loss(inputs=inputs, mode=mode) <=
            self._inference.loss(inputs=inputs, mode="s => a"))
            for mode in modes
        )
        return int(coheres)

    def update_cache(self,
        da2item: DeepA2Item,
        cached_items_updated: List[str]
    ) -> List[str]:
        """create default reconstruction, if not available (or source text has changed)"""
        # call super method
        cached_items = super().update_cache(
            da2item=da2item,
            cached_items_updated=cached_items_updated
        )
        # in addition create default reconstruction if necessary
        if (
            not "default_reconstruction" in self._cache or
            self.da2item.source_text != da2item.source_text
        ):
            self._cache["default_reconstruction"] = "default reconstruction"
            if self._inference:
                output, _ = self._inference.generate(
                    dataclasses.asdict(da2item),
                    mode="s => a"
                )
                if output:
                    generated_argdown = output[0].get(
                        "generated_text",
                        "default reconstruction"
                    )
                    generated_argdown = self._inference.postprocess_argdown(generated_argdown)
                    self._cache["default_reconstruction"] = generated_argdown

            cached_items = cached_items + ["default_reconstruction"]

        return cached_items

    def critical_angles(self) -> List[str]:
        c_angles = [
            "conclusion",
            "gist",
            "context",
            "source_paraphrase",
        ]
        c_angles = c_angles + super().critical_angles()
        return c_angles





class SomeReasonsScore(Metric):
    """scores whether da2item cointains some `reasons` (returns number of reasons)"""

    def calculate(self):
        if not self.da2item.reasons:
            return 0
        score = len(self.da2item.reasons)
        score = 1.0 - (0.9**score)
        return score

    def critical_angles(self) -> List[str]:
        return ["reasons"]

    @property
    def satisficed(self) -> bool:
        """are there any reasons?"""    
        return bool(self.score)

class SomeConjecturesScore(Metric):
    """scores whether da2item contains some `conjectures` (returns 1 or 0)"""

    def calculate(self):
        if not self.da2item.conjectures:
            return 0
        score = len(self.da2item.conjectures)
        score = 1.0 - (0.9**score)
        return score

    def critical_angles(self) -> List[str]:
        return ["conjectures"]

    @property
    def satisficed(self) -> bool:
        """are there any conjectures?"""    
        return bool(self.score)


class ReasonsAlignedScore(ArgdownMetric):
    """scores extent to which reasons are aligned with reco, i.e.
    whether they reference premises"""

    def calculate(self):
        if not self.da2item.reasons or not self.da2item.argdown_reconstruction:
            return None
        if not self._cache["parsed_argdown"]:
            return 0
        parsed_argdown: Argument = self._cache["parsed_argdown"]
        count_aligned = 0
        for reason in self.da2item.reasons:
            if reason.ref_reco > 0 and reason.ref_reco <= len(parsed_argdown.statements):
                referenced_statement = next(
                    s for s in parsed_argdown.statements
                    if (s.label == reason.ref_reco)
                )
                if referenced_statement:
                    if not referenced_statement.is_conclusion:
                        count_aligned += 1

        score = count_aligned / len(self.da2item.reasons)
        return score        

    def critical_angles(self) -> List[str]:
        return super().critical_angles() + ["reasons"]

    @property
    def satisficed(self) -> bool:
        """are all reasons aligned?"""    
        return bool(round(self.score,5) >= 1) if self.score is not None else False



class ConjecturesAlignedScore(ArgdownMetric):
    """scores extent to which conjectures are aligned with reco, i.e.
    whether they reference a final or intermediary conclusion"""

    def calculate(self):
        if not self.da2item.conjectures or not self.da2item.argdown_reconstruction:
            return None
        if not self._cache["parsed_argdown"]:
            return 0
        parsed_argdown: Argument = self._cache["parsed_argdown"]
        count_aligned = 0
        for conjecture in self.da2item.conjectures:
            if conjecture.ref_reco > 0 and conjecture.ref_reco <= len(parsed_argdown.statements):
                referenced_statement = next(
                    s for s in parsed_argdown.statements
                    if s.label == conjecture.ref_reco
                )
                if referenced_statement:
                    if referenced_statement.is_conclusion:
                        count_aligned += 1

        score = count_aligned / len(self.da2item.conjectures)
        return score

    def critical_angles(self) -> List[str]:
        return super().critical_angles() + ["conjectures"]

    @property
    def satisficed(self) -> bool:
        """are all conjectures aligned?"""
        return bool(round(self.score,5) >= 1) if self.score is not None else False


class ReasConjCohRecoScore(Metric):
    """
    scores 1 if some `reasons` `R` and `conjectures` `J` 
    cohere with the `argdown_reconstruction` `A` and given `CUE`s, i.e. if
    - loss(`A`,`S+R+J+CUE'`) <= loss(`A`,`S+CUE'`) 
      for some subset `CUE'` of all `CUE`s.
    """

    def calculate(self):    
        if not self._inference:
            return None
        if (
            (not self.da2item.reasons and not self.da2item.conjectures) or
            not self.da2item.argdown_reconstruction
        ):
            return None

        inputs = self.formatted_da2item
        loss = lambda mode: self._inference.loss(inputs=inputs, mode=mode)
        cues = Util.available_cues(da2item=self.da2item)
        input_angles_base = [["s"]+list(ss) for ss in list(Util.powerset(cues))]
        input_angles_rj = [ss+["r","j"] for ss in input_angles_base]
        modes = lambda input_angles: [f"{' + '.join(l)} => a" for l in input_angles]
        coheres = any(
            loss(mode_rj) <= loss(mode_base)
            for mode_rj, mode_base
            in zip(modes(input_angles_rj),modes(input_angles_base))
        )
        return int(coheres)

    def critical_angles(self) -> List[str]:
        c_angles = [
            "argdown_reconstruction",
            "reasons",
            "conjectures",
            "gist",
            "context",
            "source_paraphrase",
        ]
        return c_angles










class FormalizationMetric(Metric):
    """metric that requires parsed formalization"""

    def update_cache(self,
        da2item: DeepA2Item,
        cached_items_updated: List[str]
    ) -> List[str]:
        cached_items = cached_items_updated
        citems_to_update = [
            "parsed_p_formalizations",
            "parsed_ic_formalizations",
            "parsed_c_formalizations",
        ]
        corresponding_angles = [
            "premises_formalized",
            "intermediary_conclusions_formalized",
            "conclusion_formalized",
        ]
        for citem_key, angle in zip(citems_to_update, corresponding_angles):
            reparse = False
            if citem_key not in cached_items:
                if not citem_key in self._cache or not self.da2item:
                    reparse = True
                elif getattr(self.da2item,angle) != getattr(da2item, angle):
                    reparse = True
            if reparse:
                self._cache[citem_key] = DeepA2Parser.parse_as_folf(
                    getattr(da2item,angle)
                )
                cached_items = cached_items + [citem_key]

        return cached_items

    def critical_angles(self) -> List[str]:
        return [
            "premises_formalized",
            "intermediary_conclusions_formalized",
            "conclusion_formalized"
        ]



class CompleteFormalization(ArgdownMetric):
    """scores extent to which formalization is complete, i.e.
    every statement in argdown is formalized and correctly referenced
    and keys are provided"""


    def calculate(self):
        if not self._cache["parsed_argdown"]:
            return None
        parsed_argdown: Argument = self._cache["parsed_argdown"]
        premises = [s for s in parsed_argdown.statements if not s.is_conclusion]
        conclusion = [parsed_argdown.statements[-1]]
        interm_conclusions = [s for s in parsed_argdown.statements[:-1] if s.is_conclusion]
        # first, check whether some formalizations are entirely missing
        if (
            not self.da2item.premises_formalized or
            not self.da2item.conclusion_formalized or
            (not self.da2item.intermediary_conclusions_formalized and interm_conclusions) or
            not self.da2item.plchd_substitutions
        ):
            return 0
        # second, check whether there is a one-one-match between statements and formalizations
        count_aligned = 0
        for premise in premises:
            # is premise formalized exactly once?
            formalizations = [
                f for f in self.da2item.premises_formalized
                if f.ref_reco == premise.label
            ]
            if len(formalizations)==1:
                count_aligned += 1

        for interm_conclusion in interm_conclusions:
            # is interm_conclusion formalized exactly once?
            formalizations = [
                f for f in self.da2item.intermediary_conclusions_formalized
                if f.ref_reco == interm_conclusion.label
            ]
            if len(formalizations)==1:
                count_aligned += 1

        # is conclusion formalized exactly once?
        if conclusion[0]:
            formalizations = [
                f for f in self.da2item.conclusion_formalized
                if f.ref_reco == conclusion[0].label
            ]
            if len(formalizations)==1:
                count_aligned += 1

        # third, check whether there are any formalizations with non-existing references
        all_labels = [s.label for s in parsed_argdown.statements]
        all_formalizations = (
            self.da2item.premises_formalized +
            self.da2item.conclusion_formalized
        )
        if self.da2item.intermediary_conclusions_formalized:
            all_formalizations += self.da2item.intermediary_conclusions_formalized
        count_non_existing = len(
            [
                f for f in all_formalizations
                if f.ref_reco not in all_labels
            ]
        )
        if count_aligned >= count_non_existing:
            count_aligned -= count_non_existing
        else:
            count_aligned = 0

        score = count_aligned / len(parsed_argdown.statements)
        return score

    def critical_angles(self) -> List[str]:
        return super().critical_angles() + [
            "premises_formalized",
            "conclusion_formalized",
            "intermediary_conclusions_formalized",
            "plchd_substitutions",
        ]

    @property
    def satisficed(self) -> bool:
        """is every statement formalized exactly once?"""
        return bool(round(self.score,5) >= 1) if self.score is not None else False



class WellFormedKeysScore(Metric):
    """scores whether keys match formalizations (returns 1 or 0)"""

    def calculate(self):
        if not self.da2item.plchd_substitutions:
            return None
        # gather all formalizations
        formalizations = []
        if self.da2item.premises_formalized:
            formalizations += self.da2item.premises_formalized
        if self.da2item.intermediary_conclusions_formalized:
            formalizations += self.da2item.intermediary_conclusions_formalized
        if self.da2item.conclusion_formalized:
            formalizations += self.da2item.conclusion_formalized
        # check whether all keys occur in at least one formalization
        for key, _ in self.da2item.plchd_substitutions:
            if not any(
                key in f.form
                for f in formalizations
            ):
                return 0
        return 1

    def critical_angles(self) -> List[str]:
        return [
            "premises_formalized",
            "conclusion_formalized",
            "intermediary_conclusions_formalized",
            "plchd_substitutions",
        ]

class FormCohRecoScore(ArgdownMetric):
    """
    scores extent to which formalizations coeher with reco: 
    Formalizations `fp`, `fc`, `fi` plus keys `k` do *cohere*
    with an `argdown_reconstruction` that contains statements 
    `p`, `c`, and `i` (extracted from parsed `a`) iff
    1. loss(`fc`, `c+fp+k`) <= loss(`fc`, `fp`) AND
    2. loss(`fp`, `p+fc+fi+k`) <= loss(`fp`, `fc+fi`) AND
    (3. loss(`c`, `fc+fp+k`) <= loss(`c`, `fp+k`) AND)
    4. loss(`p`, `fp+fc+fi+k`) <= loss(`p`, `fc+fi+k`).
    """

    def calculate(self):
        if not self._inference:
            return None
        if (
            not self.da2item.plchd_substitutions or
            not self.da2item.conclusion_formalized or
            not self.da2item.premises_formalized or
            not self._cache["parsed_argdown"]
        ):
            return None

        parsed_argdown: Argument = self._cache["parsed_argdown"]
        has_interm_concl = any(s.is_conclusion for s in parsed_argdown.statements[:-1])

        inputs = self.formatted_da2item
        loss = lambda mode: self._inference.loss(inputs=inputs, mode=mode)
        # use fi only of interm.concl.formalized exist
        fi = "+fi" if self.da2item.intermediary_conclusions_formalized else ""
        coheres = int(
            (loss("c+k => fc") <= loss("c => fc")) and
            (loss("p+k => fp") <= loss("p => fp")) and
            (loss("i+k => fi") <= loss("i => fi") if (fi and has_interm_concl) else True) and
            (loss(f"fp+k => p") <= loss(f"fc+k => p")) and
            (loss(f"fi+k => i") <= loss(f"fc+k => i") if (fi and has_interm_concl) else True)
        ) 
        return coheres


    def critical_angles(self) -> List[str]:
        c_angles = [
            "premises_formalized",
            "conclusion_formalized",
            "intermediary_conclusions_formalized",
            "plchd_substitutions",
        ]
        c_angles = c_angles + super().critical_angles()
        return c_angles


class WellFormedFormScore(FormalizationMetric):
    """scores whether formalizations are well-formed (returns 1 or 0)"""

    def calculate(self):
        if self.da2item.premises_formalized:
            if None in self._cache["parsed_p_formalizations"]:
                return 0
        elif self.da2item.conclusion_formalized:
            if None in self._cache["parsed_c_formalizations"]:
                return 0
        elif self.da2item.intermediary_conclusions_formalized:
            if None in self._cache["parsed_ic_formalizations"]:
                return 0
        else:
            return None
        return 1


class GlobalDeductiveValidityScore(FormalizationMetric):
    """scores whether the inference from premises to conclusion is valid"""

    def calculate(self):
        premise_formulae = self._cache["parsed_p_formalizations"]
        conclusion_formulae = self._cache["parsed_c_formalizations"]
        if (
            not premise_formulae or
            not conclusion_formulae
        ):
            return None
        score = Prover9().prove(conclusion_formulae[0], premise_formulae)
        return int(score)


class LocalDeductiveValidityScore(FormalizationMetric, ArgdownMetric):
    """scores number of locally valid inference steps"""

    def _get_parsed_formula(self, label: int) -> Optional[nltk.sem.logic.Expression]:
        """collect parsed formula corresponding
        to the statement with label in argdown"""
        premise_formulae = self._cache["parsed_p_formalizations"]
        i_conclusion_formulae = self._cache["parsed_ic_formalizations"]
        conclusion_formulae = self._cache["parsed_c_formalizations"]
        # search premises
        if self.da2item.premises_formalized and premise_formulae:
            for idx, formalization in enumerate(self.da2item.premises_formalized):
                if formalization.ref_reco == label and idx < len(premise_formulae):
                    return premise_formulae[idx]
        # search intermediary conclusions
        if self.da2item.intermediary_conclusions_formalized and i_conclusion_formulae:
            for idx, formalization in enumerate(self.da2item.intermediary_conclusions_formalized):
                if formalization.ref_reco == label and idx < len(i_conclusion_formulae):
                    return i_conclusion_formulae[idx]
        # search conclusion
        if self.da2item.conclusion_formalized and conclusion_formulae:
            if self.da2item.conclusion_formalized[0]:
                if self.da2item.conclusion_formalized[0].ref_reco == label:
                    return conclusion_formulae[0]

        return None


    def calculate(self):
        if not self._cache["parsed_argdown"]:
            return None
        parsed_argdown: Argument = self._cache["parsed_argdown"]
        count_locally_valid = 0
        for statement in parsed_argdown.statements:
            if statement.is_conclusion and statement.uses:
                conclusion_formula = self._get_parsed_formula(statement.label)
                if conclusion_formula is None:
                    return None
                if conclusion_formula:
                    premise_formulae = []
                    for label in statement.uses:
                        premise_formula = self._get_parsed_formula(label)
                        if premise_formula is None:
                            return None
                        premise_formulae.append(premise_formula)
                    if premise_formulae and None not in premise_formulae:
                        if Prover9().prove(conclusion_formula, premise_formulae):
                            count_locally_valid += 1

        count_inference_steps = len([
            s for s in parsed_argdown.statements 
            if s.is_conclusion
        ])
        score = count_locally_valid / count_inference_steps

        return score

    @property
    def satisficed(self) -> bool:
        """are all inference steps deductively valid?"""
        return bool(round(self.score,5) >= 1) if self.score is not None else False

    def critical_angles(self) -> List[str]:
        c_angles = (
            ArgdownMetric.critical_angles(self) +
            FormalizationMetric.critical_angles(self)
        )
        return c_angles

    def update_cache(self,
        da2item: DeepA2Item,
        cached_items_updated: List[str]
    ) -> List[str]:
        cached_items = cached_items_updated
        cached_items = FormalizationMetric.update_cache(self, da2item, cached_items)
        cached_items = ArgdownMetric.update_cache(self, da2item, cached_items)
        return cached_items



class SofaEvaluator:
    """class to evaluate a da2item with respect to set of metrics"""

    #inference pipeline
    _inference: AbstractInferencePipeline
    # cache, especially for default_reconstruction
    _cache: Dict[str, Any]
    # registry of metrics
    _metrics_registry: Dict[str, Metric]
    # mapping of metrics to reconstruction phases
    _metric_phase: Dict[str, int]
    # mapping of metrics to alternatives that may be satisficed for reconstruction phases
    _alternative_metrics: Dict[str, List[str]]

    def __init__(self,
        inference: AbstractInferencePipeline,
    ):
        self._inference = inference
        self._cache = {}
        self._metrics_registry = {}
        self._metric_phase = {}
        self._alternative_metrics = {}

        self.register_metric(GlobalCompletenessScore)
        self.register_metric(ArgumentSizeScore)

        self.register_metric(ValidArgdownScore,phase=0)
        self.register_metric(PCStructureScore,phase=0)
        self.register_metric(NoPetitioScore,phase=0)
        self.register_metric(NoRedundancyScore,phase=0)
        self.register_metric(ConclMatchesRecoScore,phase=0)
        self.register_metric(RecoCohSourceScore,phase=0)

        self.register_metric(
            SomeReasonsScore,
            phase=1,
            alternatives=[SomeConjecturesScore]
        )
        self.register_metric(
            SomeConjecturesScore,
            phase=1,
            alternatives=[SomeReasonsScore]
        )
        self.register_metric(ReasonsAlignedScore,phase=1)
        self.register_metric(ConjecturesAlignedScore,phase=1)
        self.register_metric(ReasConjCohRecoScore,phase=1)

        self.register_metric(ConsistentUsageScore,phase=2)
        self.register_metric(CompleteFormalization,phase=2)
        self.register_metric(WellFormedKeysScore,phase=2)
        self.register_metric(WellFormedFormScore,phase=2)
        self.register_metric(FormCohRecoScore,phase=2)
        self.register_metric(GlobalDeductiveValidityScore,phase=2)
        self.register_metric(LocalDeductiveValidityScore,phase=2)

        # check whether all alternatives are actually registered
        for alternatives in self._alternative_metrics.values():
            for alt in alternatives:
                if alt not in self._metrics_registry:
                    logging.error("alternative metrics %s not registered", alt)


    def register_metric(
        self,
        metric_class: Type[Metric],
        phase: int = -1,
        alternatives: List[Type[Metric]] = None
    ) -> None:
        """register a metric"""
        # instantiate metric
        metric = metric_class(inference=self._inference, cache=self._cache)
        # register metric
        self._metrics_registry[metric.__class__.__name__] = metric
        self._metric_phase[metric.__class__.__name__] = phase
        if alternatives:
            self._alternative_metrics[metric.__class__.__name__] = []
            for alternative in alternatives:
                self._alternative_metrics[metric.__class__.__name__].append(alternative.__name__)

    def update(self, da2item: DeepA2Item = None) -> None:
        """update cache and metric scores"""
        # update cache
        cached_items_updated: List[str] = []
        for metric in self._metrics_registry.values():
            cached_items_updated = metric.update_cache(da2item, cached_items_updated)

        # update metric scores
        for metric in self._metrics_registry.values():
            metric.update_score(da2item)

    def individual_score(self, metric_name = Union[Metric,str]) -> Optional[Union[float,int]]:
        """get individual score of metric by name"""
        if not isinstance(metric_name, str):
            metric_name = metric_name.__name__
        metric = self._metrics_registry.get(metric_name)
        if metric:
            return metric.score
        else:
            # metric not registered
            return None

    def all_scores(
        self, phases: Optional[List[int]] = None
    ) -> Dict[str,Optional[Union[float,int]]]:
        """get scores of all registered metrics in phases as dict"""
        scores = {
            key: metric.score
            for key, metric 
            in self._metrics_registry.items()
            if (not phases or self._metric_phase[key] in phases)
        }
        return scores

    def from_cache(self, key: str) -> Any:
        """utility: get item from cache"""
        return self._cache.get(key)

    @property
    def reconstruction_phase(self) -> int:
        """return current reconstruction phase"""
        for phase in range(len(RECONSTRUCTION_PHASES)):
            for key, metric in self._metrics_registry.items():
                if self._metric_phase[key] == phase:
                    # is metric satisficed?
                    if not metric.satisficed:
                        # no alternatives?
                        if not key in self._alternative_metrics: 
                            return phase
                        # is no alternative satisficed?
                        if not any(
                            self._metrics_registry[alt].satisficed
                            for alt in self._alternative_metrics[key]
                            if alt in self._metrics_registry
                        ):
                            return phase
        return len(RECONSTRUCTION_PHASES)-1

    @property
    def completeness(self) -> float:
        """
        scores the completenesss of the current 
        comprehensive argumentative analysis (da2item)
        - ratio of non-empty core fields
        """
        gcs = self.individual_score(GlobalCompletenessScore)
        gcs = 0. if gcs is None else gcs
        return gcs

    @property
    def correctness(self) -> float:
        """
        scores the global completes of the current 
        comprehensive argumentative analysis
        - average non-None scores
        """
        all_scores = [
            score for score in 
            self.all_scores(phases=[0,1,2,3]).values()
            if score is not None
        ]
        if not all_scores:
            return 0.
        return sum(all_scores)/len(all_scores)

    @property
    def depth(self) -> float:
        """
        scores the sophistication/depth of the current
        comprehensive argumentative analysis (da2item)
        - number of statements in the argument
        - number of reasons and conjectures
        """
        # quotes
        srs = self.individual_score(SomeReasonsScore)
        srs = 0 if srs is None else srs
        scs = self.individual_score(SomeConjecturesScore)
        scs = 0 if scs is None else scs
        # argument size
        ass = self.individual_score(ArgumentSizeScore)
        ass = 0 if ass is None else ass
        # alignment
        ras = self.individual_score(ReasonsAlignedScore) 
        ras = 0 if ras is None else ras
        cas = self.individual_score(ConjecturesAlignedScore) 
        cas = 0 if cas is None else cas
        # aggregate
        depth_score: float = (
            max(srs,scs)
            + ass
            + max(ras,cas)
        )/3.
        return depth_score

    def as_dict(self) -> Dict[str, Any]:
        """return all scores and aggregate metrics as dict"""
        data = self.all_scores()
        data["completeness"] = self.completeness
        data["correctness"] = self.correctness
        data["depth"] = self.depth
        data["reconstruction_phase"] = self.reconstruction_phase
        # remove None values
        data = {
            key: value for key, value in data.items()
            if value is not None
        }
        return data
    