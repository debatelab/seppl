"""Main project class"""

from __future__ import annotations
from copy import deepcopy
import logging
from typing import Optional, List, Any, Dict

import streamlit as st

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
    sofa_counter: int  # global counter of sofas in project history
    project_store: AbstractProjectStore
    state_of_analysis: StateOfAnalysis # current sofa
    metrics_data: Dict[str, Any] = {}# metrics data for current sofa
    metrics_delta: Dict[str, Any] = {} # metrics changes for current sofa
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[str] = None

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
        self.sofa_counter = self.project_store.get_length()
        self.title = self.project_store.get_title()
        self.description = self.project_store.get_description()
        self.course_id = self.project_store.get_course_id()

        # load last sofa
        self.load_sofa()

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


    def load_sofa(self, global_step: Optional[int] = None):
        """load sofa from store
        loads last sofa if global_step is None
        """
        if global_step is not None:
            try:
                self.state_of_analysis = self.project_store.get_sofa(global_step)
            except ValueError as e:
                st.error(
                    f"Could not load state of analysis with global_step {global_step}: {e}"
                )
                return
        else:
            self.state_of_analysis = self.project_store.get_last_sofa()
        self.sofa_counter = self.project_store.get_length()
        self.metrics_data = self.project_store.get_metrics(
            self.state_of_analysis.sofa_id
        )
        # get last sofa and correspondings metrics to calculate metrics delta
        prev_metrics_data = self.project_store.get_metrics(
            self.project_store.get_sofa(
                self.state_of_analysis.resumes_from_step
            ).sofa_id
        )
        self.metrics_delta = {
            k: self.metrics_data[k] - prev_metrics_data[k]
            for k, v in self.metrics_data.items()
            if k in prev_metrics_data and isinstance(v, (int, float))
        }


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
        request = Request(
            query = query,
            state_of_analysis = self.state_of_analysis,
            global_step = self.sofa_counter,
        )
        new_sofa = self.handlers[0].handle(request)

        # check if sofa has changed at all
        if not new_sofa.da2item == self.state_of_analysis.da2item:
            # write new sofa to store
            self.project_store.store_sofa(new_sofa)
            # write metrics to store
            self.project_store.store_metrics(new_sofa)
            # update state of analysis
            self.state_of_analysis = new_sofa
            # get new metrics data from store
            new_metrics_data = self.project_store.get_metrics(
                new_sofa.sofa_id
            )
            # calculate metrics delta
            self.metrics_delta = {
                k: new_metrics_data[k]-self.metrics_data[k]
                for k,v in new_metrics_data.items()
                if k in self.metrics_data and isinstance(v, (int, float))
            }                
            # update metrics data
            self.metrics_data = new_metrics_data
            # update counter
            self.sofa_counter = self.project_store.get_length()
