"""inference tools and pipelines"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Optional, Dict, List, Any

from deepa2 import DeepA2Item
from google.cloud import firestore
import uuid

from seppl.backend.handler import CUE_FIELDS
from seppl.backend.inference import AbstractInferencePipeline
from seppl.backend.inputoption import ChoiceOption, OptionFactory
from seppl.backend.state_of_analysis import StateOfAnalysis

# DUMMY DATA
_SOURCE_TEXT = "It is cruel and unethical to kill animals for food "
"when vegetarian options are available, especially because raising animals "
"in confinement for slaughter is cruel, and many animals in the United "
"States are not slaughtered humanely. Animals are sentient beings that "
"have emotions and social connections. Scientific studies show that cattle, "
"pigs, chickens, and all warm-blooded animals can experience stress, pain, "
"and fear."


class AbstractProjectStore(ABC):
    """Interface for Project Stores"""

    _inference: AbstractInferencePipeline
    _user_id: str
    _project_id: Optional[str] = None

    def __init__(self,
        inference: AbstractInferencePipeline,
        user_id: str,
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
    def store_metrics(self, sofa: StateOfAnalysis):
        """stores sofa's metric in current project"""

    @abstractmethod
    def get_metrics(self, sofa_id: str) -> Dict[str, Any]:
        """get metrics for sofa with id sofa_id"""

    @abstractmethod
    def list_projects(self) -> List[str]:
        """list all projects of current user"""

    @abstractmethod
    def get_project(self) -> str:
        """return id of current project project_id """

    @abstractmethod
    def get_title(self) -> str:
        """title of current project"""

    @abstractmethod
    def get_description(self) -> str:
        """description of current project"""


    def set_user(self, user_id: str) -> None:
        """sets user with id user_id as current user"""
        raise NotImplementedError

    def get_user_metrics(self) -> Dict[str, Any]:
        """get aggregate metrics for current user"""
        raise NotImplementedError

    def set_project(self, project_id: str) -> None:
        """sets project_id"""
        self._project_id = project_id



class DummyLocalProjectStore(AbstractProjectStore):
    """local dummy store for testing"""

    _user_id: str
    _project_id: str
    _sofa_list: List[Dict[str,Any]]
    _metrics_list: List[Dict[str,Any]]

    def __init__(self,
        inference: AbstractInferencePipeline,
        user_id: str,
        project_id: str = None,
    ):
        super().__init__(
            inference=inference,
            user_id=user_id,
            project_id=project_id
        )

        input_options = OptionFactory.create_text_options(
            da2_fields=list(CUE_FIELDS),
            pre_initialized=False,
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

        input_options += [dummy_option]

        if self._project_id is None:
            self._project_id = "dummy_project"

        dummy_sofa = StateOfAnalysis(
            sofa_id = "12345678-1234-5678-1234-567812345678",
            project_id = self._project_id,
            inference = self._inference,
            da2item = DeepA2Item(source_text=_SOURCE_TEXT),
            input_options = input_options,
        )

        data = dummy_sofa.as_dict()

        self._sofa_list = [
            data,
        ]

        self._metrics_list = []


    def get_sofa(self, idx: int) -> StateOfAnalysis:
        """get_sofa in current project at step idx"""
        data = self._sofa_list[idx]
        logging.debug("DummyLocalProjectStore: Fetching sofa data with id %s from store.", data.get("sofa_id"))
        sofa = StateOfAnalysis.from_dict(data, self._inference)
        logging.debug("DummyLocalProjectStore: Returning sofa %s at idx %s from store.", sofa.sofa_id, idx)
        return sofa

    def get_last_sofa(self) -> StateOfAnalysis:
        """get last sofa in current project """
        return self.get_sofa(-1)

    def get_length(self) -> int:
        """get number of sofas in current project """
        return len(self._sofa_list)

    def store_sofa(self, sofa: StateOfAnalysis):
        """stores sofa in current project"""
        data = sofa.as_dict()
        logging.info("DummyLocalProjectStore: Saving sofa %s in store. New size of store: %s.", data, self.get_length())
        self._sofa_list.append(data)

    def list_projects(self) -> List[str]:
        """list all projects of current user"""
        return [self._project_id]

    def get_project(self) -> str:
        """return id of current project project_id """
        return self._project_id

    def get_title(self) -> str:
        """title of current project"""
        return "dummy project title"

    def get_description(self) -> str:
        """description of current project"""
        return "dummy project description"

    def store_metrics(self, sofa: StateOfAnalysis):
        """stores sofa's metrics"""
        assert self._project_id == sofa.project_id
        if sofa.sofa_id in [m["sofa_id"] for m in self._metrics_list]:
            logging.warning("DummyLocalProjectStore: Sofa %s already has metrics in store. Storing duplicate metric!", sofa.sofa_id)
        metrics = sofa.metrics
        data = metrics.as_dict()
        data["sofa_id"] = sofa.sofa_id
        data["project_id"] = sofa.project_id
        data["user_id"] = self._user_id
        data["global_step"] = sofa.global_step
        self._metrics_list.append(data)
        logging.info("DummyLocalProjectStore: Saving metrics %s in store. New size of metric collection: %s.", data, len(self._metrics_list))

    def get_metrics(self, sofa_id: str):
        """gets sofa's metrics from current project and user"""
        for m in self._metrics_list:
            if (
                m["sofa_id"] == sofa_id
                and m["project_id"] == self._project_id
                and m["user_id"] == self._user_id
            ):
                return m
        return None




class FirestoreProjectStore(AbstractProjectStore):
    """firestore store"""

    _user_id: str
    _project_id: str
    db: firestore.Client

    def __init__(self,
        inference: AbstractInferencePipeline,
        user_id: str,
        project_id: str = None,
    ):
        super().__init__(
            inference=inference,
            user_id=user_id,
            project_id=project_id
        )

        # Authenticate to Firestore with the JSON account key.
        self.db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")

        # Check whether user exists
        doc_ref = self.db.collection("users").document(self._user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("User with id %s does not exist in firestore." % self._user_id)

        # Sets project
        if project_id:
            self.set_project(project_id)


    def set_project(self, project_id: str) -> None:
        """sets project_id"""
        # check if project exists
        if project_id is not None:
            doc_ref = self.db.collection(f"users/{self._user_id}/projects").document(project_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise ValueError("Project with id %s of user %s does not exist in firestore." % project_id, self._user_id)

        self._project_id = project_id

    def create_new_project(self,
        project_id: str,
        da2item: DeepA2Item,
        title: str = None,
        description: str = None,
    ) -> None:
        """creates new project for current user, set current project accordingly"""
        # check if project exists
        project_ref = self.db.collection(f"users/{self._user_id}/projects").document(project_id)
        doc = project_ref.get()
        if doc.exists:
            raise ValueError("Cannot create new project. Project with id %s of user %s exists in firestore." % project_id, self._user_id)

        # assemble data for new project
        source_text = da2item.source_text
        input_options = OptionFactory.create_text_options(
            da2_fields=list(CUE_FIELDS),
            pre_initialized=False,
        )
        sofa = StateOfAnalysis(
            sofa_id = str(uuid.uuid4()),
            project_id = project_id,
            inference = self._inference,
            da2item = da2item,
            input_options = input_options,
        )
        #sofa_data = sofa.as_dict()
        ## don't store source text in sofa(s), but in project once
        #sofa_data["da2item"] = {
        #    k:v for k,v in sofa_data["da2item"].items()
        #    if k != "source_text"
        #}

        data = {
            "title": title,
            "description": description,
            "project_id": project_id,
            "user_id": self._user_id,
            "source_text": source_text,
            "sofa_counter": 0,
        }

        # Create new project document
        project_ref.set(data)

        # Create first sofa in subcollection for sofas
        self.set_project(project_id)
        self.store_sofa(sofa)
        #sofa_ref = project_ref.collection("sofa_list").document(sofa.sofa_id)
        #sofa_ref.set(sofa_data)

    @property
    def source_text(self) -> str:
        """source text of current project"""
        doc_ref = self.db.collection(f"users/{self._user_id}/projects").document(self._project_id)
        doc = doc_ref.get()
        return doc.get("source_text")

    def get_sofa(self, idx: int) -> StateOfAnalysis:
        """get_sofa in current project at step idx"""

        sofa_list = self.db.collection(f"users/{self._user_id}/projects/{self._project_id}/sofa_list")
        sofas = sofa_list.where(u'global_step', u'==', idx).stream()
        sofa = next(sofas, None)
        if sofa:
            data = sofa.to_dict()
            data["da2item"]["source_text"] = self.source_text
            logging.debug("FirestoreProjectStore: Fetching sofa data with id %s from store.", data.get("sofa_id"))
            sofa = StateOfAnalysis.from_dict(data, self._inference)
            logging.debug("FirestoreProjectStore: Returning sofa %s at idx %s from store.", sofa.sofa_id, idx)
            return sofa
        raise ValueError("FirestoreProjectStore: No sofa at idx %s in store." % idx)

    def get_last_sofa(self) -> StateOfAnalysis:
        """get last sofa in current project """
        sofa_list = self.db.collection(f"users/{self._user_id}/projects/{self._project_id}/sofa_list")
        query = sofa_list.order_by(
            u'global_step', direction=firestore.Query.DESCENDING).limit(1)
        last_sofa = next(query.stream(), None)
        if last_sofa:
            data = last_sofa.to_dict()
            data["da2item"]["source_text"] = self.source_text
            logging.debug("FirestoreProjectStore: Fetching sofa data with id %s from store.", data.get("sofa_id"))
            sofa = StateOfAnalysis.from_dict(data, self._inference)
            logging.debug("FirestoreProjectStore: Returning sofa %s from store.", sofa.sofa_id)
            return sofa
        raise ValueError("FirestoreProjectStore: Couldn't access last sofa in project %s in store." % self._project_id)

    def get_length(self) -> int:
        """get number of sofas in current project 
        """
        # get sofa counter
        project_ref = self.db.collection(f"users/{self._user_id}/projects").document(self._project_id)
        counter = project_ref.get().to_dict().get("sofa_counter")
        return counter

    def store_sofa(self, sofa: StateOfAnalysis):
        """stores sofa in current project"""
        sofa_list = self.db.collection(f"users/{self._user_id}/projects/{self._project_id}/sofa_list")
        sofa_ref = sofa_list.document(sofa.sofa_id)
        data = sofa.as_dict()
        # don't store source text in sofa(s), but in project once
        data["da2item"] = {
            k:v for k,v in data["da2item"].items()
            if k != "source_text"
        }
        logging.info("FirestoreProjectStore: Saving sofa %s in store.", data)
        sofa_ref.set(data)
        # increment sofa counter
        project_ref = self.db.collection(f"users/{self._user_id}/projects").document(self._project_id)
        project_ref.update({"sofa_counter": firestore.Increment(1)})

    def list_projects(self) -> List[str]:
        """list all projects of current user"""
        projects_collection = self.db.collection(f"users/{self._user_id}/projects")
        projects: List[str] = []
        for doc in projects_collection.stream():
            logging.info("FirestoreProjectStore: Found project %s in store.", doc.id)
            projects.append(doc.id)
        return projects

    def get_project(self) -> str:
        """return id of current project project_id """
        return self._project_id

    def get_title(self) -> str:
        """title of current project"""
        pj_coll = self.db.collection(f"users/{self._user_id}/projects")
        pj_ref = pj_coll.document(self._project_id)
        pj_doc = pj_ref.get()        
        return pj_doc.get("title")

    def get_description(self) -> str:
        """description of current project"""
        pj_coll = self.db.collection(f"users/{self._user_id}/projects")
        pj_ref = pj_coll.document(self._project_id)
        pj_doc = pj_ref.get()        
        return pj_doc.get("description")
        
    def store_metrics(self, sofa: StateOfAnalysis):
        """stores sofa's metrics"""
        # sanity checks
        assert self._project_id == sofa.project_id
        # prepare data
        metrics = sofa.metrics
        data = metrics.as_dict()
        data["sofa_id"] = sofa.sofa_id
        data["timestamp"] = sofa.timestamp
        data["project_id"] = sofa.project_id
        data["user_id"] = self._user_id
        data["global_step"] = sofa.global_step
        # store data
        metrics_id = "mx_" + sofa.sofa_id
        metrics_ref = self.db.collection(f"metrics").document(metrics_id)
        if metrics_ref.get().exists:
            raise ValueError("FirestoreProjectStore: Cannot store metrics. Metrics with id %s already exist in firestore." % metrics_id)
        metrics_ref.set(data)
        logging.debug("FirestoreProjectStore: Saving metrics %s in store.", data)

    def get_metrics(self, sofa_id: str):
        """gets sofa's metrics"""
        metrics_id = "mx_" + sofa_id
        metrics_ref = self.db.collection("metrics").document(metrics_id)
        metrics_doc = metrics_ref.get()
        if not metrics_doc.exists:
            logging.warning("FirestoreProjectStore: No metrics with id %s in store. Returning empty dict.", metrics_id)
            return {}
        metrics_data = metrics_doc.to_dict()
        return metrics_data

    def get_user_metrics(self) -> Dict[str, Any]:
        """get aggregate metrics for current user"""
        metrics_user = self.db.collection("metrics").where(u'user_id', u'==', self._user_id).stream()
        count_mx = 0
        for mx in metrics_user:
            count_mx += 1
        return {"count_metrics": count_mx}

