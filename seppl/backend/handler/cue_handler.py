"""Handlers"""

from __future__ import annotations
from typing import Optional, Any, List

from deepa2 import DeepA2Item
import seppl.backend.project as pjt
from seppl.backend.handler import Request, AbstractHandler
from seppl.backend.userinput import CueInput



class CueHandler(AbstractHandler):
    """handles cue (gist, paraphrase, etc.) input"""

    def handle(self, request: Request) -> Optional[pjt.StateOfAnalysis]:
        if isinstance(request.query, CueInput):
            new_sofa = pjt.StateOfAnalysis()
            # TODO
            return new_sofa

        return super().handle(request)
