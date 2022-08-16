"""Handlers"""

from __future__ import annotations
from typing import Optional, Any, List

from deepa2 import DeepA2Item
import seppl.backend.project as pjt
from seppl.backend.handler import Request, AbstractUserInputHandler
from seppl.backend.userinput import FormalizationInput



class FormalizationHandler(AbstractUserInputHandler):
    """handles quote (reasons, conjectures) input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, FormalizationInput):
            new_sofa = pjt.StateOfAnalysis()
            # TODO
            return new_sofa

        return super().handle(request)
