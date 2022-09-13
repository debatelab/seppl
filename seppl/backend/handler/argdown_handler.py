"""Handlers"""

from __future__ import annotations
from copy import deepcopy
from typing import Optional, Any, List

from deepa2 import DeepA2Item
import seppl.backend.project as pjt
from seppl.backend.handler import Request, AbstractUserInputHandler
from seppl.backend.userinput import ArgdownInput
from seppl.backend.inputoption import ChoiceOption, InputOption, TextOption



class ArgdownHandler(AbstractUserInputHandler):
    """handles argdown input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, ArgdownInput):
            old_sofa = request.state_of_analysis
            argdown_input = request.query
            # revise comprehensive argumentative analysis (da2item) 
            new_da2item = deepcopy(old_sofa.da2item)
            new_da2item.argdown_reconstruction = argdown_input.cast()
            # evaluate revised analysis
            metrics = old_sofa.metrics
            metrics.update(new_da2item)

            # TODO: replace dummy option
            input_options: List[InputOption] = [
                ChoiceOption(
                    context = ["(1) P --- (2) C", f"(1) Q --- ({old_sofa.global_step}) C"],
                    question = "Which reco is better A or B?",
                    input_type = "ARGDOWN_INPUT",
                    answers = {
                        "reco 1": "(1) P ---(2) C",
                        "reco 2": f"(1) Q --- ({old_sofa.global_step}) C",
                    }
                ),
                TextOption(
                    context = [],
                    question = "Can you improve the follow reco, or provide a better alternative?",
                    input_type = "ARGDOWN_INPUT",
                    initial_text = f"({old_sofa.global_step}) B (2) B->C --- (3) C"
                ),
            ]
            # TODO construct new sofa in meaningful way
            new_sofa = old_sofa.create_revision(
                global_step = request.global_step,
                input_options = input_options,
                user_input = argdown_input,
                feedback = "Not bad",
                da2item = new_da2item,
                metrics = metrics,
            )
            
            return new_sofa

        return super().handle(request)

