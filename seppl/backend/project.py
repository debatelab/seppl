"""Main project class"""

from __future__ import annotations
from copy import deepcopy
import logging
from typing import Optional, List, Any, Dict

from seppl.backend.state_of_analysis import StateOfAnalysis
from seppl.backend.inference import AbstractInferencePipeline
from seppl.backend.project_store import AbstractProjectStore
from seppl.backend.userinput import UserInput
import seppl.backend.handler
from seppl.backend.handler import (
    Request,
    AbstractUserInputHandler)



class Project:
    """representation of a reconstruction project"""

    inference: AbstractInferencePipeline
    project_id: str  # unique identifier of this project
    global_step: int  # global counter of sofas in project history
    project_store: AbstractProjectStore
    state_of_analysis: StateOfAnalysis # current sofa

    def __init__(
        self,
        inference: AbstractInferencePipeline,
        project_store: AbstractProjectStore,
        project_id: str,
    ):
        self.inference = inference
        self.project_id = project_id
        self.project_store = project_store
        self.project_store.set_project(self.project_id)
        self.state_of_analysis = self.project_store.get_last_sofa()        
        self.global_step = self.project_store.get_length()-1


        # setup chain of responsibility for handling user queries
        self.handlers: List[AbstractUserInputHandler] = [
            # PHASE ZERO
            seppl.backend.handler.PhaseZeroHandlerNoCues(inference=self.inference),
            seppl.backend.handler.PhaseZeroHandlerNoArgd(inference=self.inference),
            seppl.backend.handler.PhaseZeroHandlerIllfArgd(inference=self.inference),
            seppl.backend.handler.PhaseZeroHandlerRedund(inference=self.inference),
            seppl.backend.handler.PhaseZeroHandlerMismatchCA(inference=self.inference),
            seppl.backend.handler.PhaseZeroHandlerCatchAll(inference=self.inference),
            # PHASE ONE
            seppl.backend.handler.PhaseOneHandlerNoRJ(inference=self.inference),
            seppl.backend.handler.PhaseOneHandlerRNotAlgn(inference=self.inference),
            seppl.backend.handler.PhaseOneHandlerJNotAlgn(inference=self.inference),
            seppl.backend.handler.PhaseOneHandlerCatchAll(inference=self.inference),
            # PHASE TWO
            seppl.backend.handler.PhaseTwoHandlerNoConsUsg(inference=self.inference),
            seppl.backend.handler.PhaseTwoHandlerNoCompleteForm(inference=self.inference),
            seppl.backend.handler.PhaseTwoHandlerIllfForm(inference=self.inference),
            seppl.backend.handler.PhaseTwoHandlerCatchAll(inference=self.inference),
            #PHASE THREE
            seppl.backend.handler.PhaseThreeHandlerCatchAll(inference=self.inference),
        ]
        for i in range(1,len(self.handlers)):
            self.handlers[i-1].set_next(
                self.handlers[i]
            )


    def toggle_visible_option(self):
        """increments index of visible option in state of analysis"""
        n_options = len(self.state_of_analysis.input_options)
        i_vis = self.state_of_analysis.visible_option
        i_vis = (i_vis + 1) % n_options
        self.state_of_analysis.visible_option = i_vis


    def update(self, query: UserInput):
        """update the project given user input query"""
        logging.debug(
            "%s: updating project with query %s",
            self.__class__.__name__,
            (query._raw_input,query.da2_field)
        )
        self.global_step += 1
        request = Request(
            query = query,
            state_of_analysis = self.state_of_analysis,
            global_step = self.global_step,
        )
        new_sofa = self.handlers[0].handle(request)
        # write new sofa to store
        self.project_store.store_sofa(new_sofa)
        # write metrics to store
        self.project_store.store_metrics(new_sofa)
        # update state of analysis
        self.state_of_analysis = new_sofa
