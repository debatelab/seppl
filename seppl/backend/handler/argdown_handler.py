"""Handlers"""

from __future__ import annotations
from typing import Optional, Any, List

from deepa2 import DeepA2Item
import seppl.backend.project as pjt
from seppl.backend.handler import Request, AbstractHandler
from seppl.backend.userinput import ArgdownInput
from seppl.backend.inputoption import ChoiceOption, InputOption, TextOption



class ArgdownHandler(AbstractHandler):
    """handles argdown input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, ArgdownInput):
            old_sofa = request.state_of_analysis
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
            new_sofa = pjt.StateOfAnalysis(
                text = old_sofa.text+" *and* "+request.query.cast(),
                global_step = old_sofa.global_step + 1,
                input_options = input_options,
            )
            
            return new_sofa

        return super().handle(request)

