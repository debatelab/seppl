"""inference tools and pipelines"""

from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
import logging
import json
import re
from typing import Optional, Dict, List, Tuple, Any, Union

from deepa2 import DeepA2Item
import requests  # type: ignore

from seppl.backend.state_of_analysis import StateOfAnalysis
from seppl.backend.inputoption import ChoiceOption
from seppl.backend.inference import AbstractInferencePipeline

# DUMMY DATA
_SOURCE_TEXT = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely. Animals are sentient beings that
have emotions and social connections. Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""


class AbstractProjectStore(ABC):
    """Interface for Project Stores"""

    _inference: AbstractInferencePipeline
    _user_id: Optional[str] = None
    _project_id: Optional[str] = None

    def __init__(self,
        inference: AbstractInferencePipeline,
        user_id: str = None,
        project_id: str = None,
    ):
        self._inference = inference
        self._user_id = user_id
        self._project_id = project_id

    @abstractmethod
    def get_sofa(self, idx: int) -> StateOfAnalysis:
        """get_sofa in current project at step idx"""

    def get_last_sofa(self) -> StateOfAnalysis:
        """get last sofa in current project """
        return self.get_sofa(-1)

    @abstractmethod
    def get_length(self) -> int:
        """get number of sofas in current project """

    @abstractmethod
    def store_sofa(self, sofa: StateOfAnalysis):
        """stores sofa in current project"""

    @abstractmethod
    def list_projects(self) -> List[str]:
        """list all projects of current user"""

    def set_user(self, user_id: str) -> None:
        """sets user with id user_id as current user"""
        self._user_id = user_id

    def set_project(self, project_id: str) -> None:
        """sets project_id"""
        self._project_id = project_id



class DummyLocalProjectStore(AbstractProjectStore):
    """local dummy store for testing"""

    _user_id: str
    _project_id: str
    _sofa_list: List[StateOfAnalysis]

    def __init__(self,
        inference: AbstractInferencePipeline,
        user_id: str = None,
        project_id: str = None,
    ):
        super().__init__(
            inference=inference,
            user_id=user_id,
            project_id=project_id
        )

        dummy_option = ChoiceOption(
            context = ["(1) P --- (2) C", "(1) Q --- (2) C"],
            question = "Which reco is better A or B?",
            da2_field = "argdown_reconstruction",
            answers = {
                "reco 1": "(1) P ---(2) C",
                "reco 2": "(1) Q ---(2) C",
            }
        )

        if self._project_id is None:
            self._project_id = "dummy_project"

        dummy_sofa = StateOfAnalysis(
            project_id = self._project_id,
            inference = self._inference,
            da2item = DeepA2Item(source_text=_SOURCE_TEXT),
            input_options = [dummy_option],
        )

        self._sofa_list = [
            dummy_sofa,
        ]



    def get_sofa(self, idx: int) -> StateOfAnalysis:
        """get_sofa in current project at step idx"""
        return self._sofa_list[idx]

    def get_last_sofa(self) -> StateOfAnalysis:
        """get last sofa in current project """
        return self.get_sofa(-1)

    def get_length(self) -> int:
        """get number of sofas in current project """
        return len(self._sofa_list)

    def store_sofa(self, sofa: StateOfAnalysis):
        """stores sofa in current project"""
        logging.info("DummyLocalProjectStore: Saving sofa %s in store. New size of store: %s.", sofa, self.get_length())
        self._sofa_list.append(deepcopy(sofa))

    def list_projects(self) -> List[str]:
        """list all projects of current user"""

    def get_project(self) -> str:
        """return id of current project project_id """

