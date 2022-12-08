"""SEPPL streamlit app"""

import logging
from re import S
from typing import Optional

import streamlit as st

from seppl.backend.project import Project
from seppl.backend.gui import ProjectStRenderer, SidebarRenderer
from seppl.backend.inference import AbstractInferencePipeline, inference_factory
from seppl.backend.project_store import AbstractProjectStore, FirestoreProjectStore
import seppl.backend.session_state_keys as stsk

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    filename='seppl.log',
)


# TODO: load this from config.yaml
_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"


def check_authentification() -> bool:
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if "password" in st.session_state and "username" in st.session_state:
            if st.session_state.password and st.session_state.username:
                st.session_state["password_correct"] = FirestoreProjectStore.authenticate_user(
                    user_id=st.session_state.username,
                    password=st.session_state.password,
                )

        if "password_correct" in st.session_state:
            if st.session_state.password_correct:
                st.session_state["user_id"] = st.session_state.username
                del st.session_state.password

        # elif (
        #     st.session_state["password"] == st.secrets["password"] 
        #     and st.session_state["user_id"] == "marcantonio-galuppi"
        # ):
        #     st.session_state["password_correct"] = True
        #     del st.session_state["password"]  # don't store password
        # else:
        #     st.session_state["password_correct"] = False

    def display_login(incorrect_password: bool = False):
        """Displays a login screen."""
        _, col, _ = st.columns([1,2,1])
        with col:
            st.text_input(
                "Username",
                key="username",
                on_change=password_entered,
            )
            if st.session_state["username"]:
                st.text_input(
                    "Password",
                    type="password",
                    key="password",
                    on_change=password_entered,
                )
            if incorrect_password:
                st.error("😕 Password incorrect")
            #if st.button("Login"):
            #    password_entered()

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        display_login()
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        display_login(incorrect_password=True)
        return False
    else:
        # Password correct.
        return True


def load_project() -> None:
    """initialize reconstruction project"""
    if stsk.PROJECT_ID in st.session_state:
        inference = st.session_state["inference"]
        project_store: AbstractProjectStore = st.session_state["project_store"]
        project_id = st.session_state[stsk.PROJECT_ID]
        if project_id:
            st.session_state["project"] = Project(
                inference = inference,
                project_store = project_store,
                project_id = project_id,
            )
        else:
            st.session_state["project"] = None

def main():
    """main script"""

    st.set_page_config(
        page_title="seppl (AI argument analysis tutor)",
        page_icon="🤹",
        layout="wide",
    )

    if check_authentification():

        # user id (TODO: set in authentification method)
        user_id = st.session_state.user_id

        # initialize inference pipeline
        if not "inference" in st.session_state:
            st.session_state["inference"] = inference_factory(
                pipeline_id = _PIPELINE,
                textgen_server_url = _TEXTEGEN_SERVER_URL,
                loss_server_url = _LOSS_SERVER_URL,
            )
        inference = st.session_state["inference"]

        # initialize project_store
        if not "project_store" in st.session_state:
            st.session_state["project_store"] = FirestoreProjectStore(
                inference=inference,
                user_id=user_id,
            )
        project_store: AbstractProjectStore = st.session_state["project_store"]

        # initialize project_list
        if not "project_list" in st.session_state:
            st.session_state["project_list"] = project_store.list_projects()

        # get reference to project if already initialized
        project = None
        if "project" in st.session_state:
            project = st.session_state.project

        # initialize and render sidebar
        sidebar_gui = SidebarRenderer(
            user_id=user_id,
            project_list = st.session_state["project_list"],
            project_loader = load_project,
        )
        sidebar_gui.render(
            project = project,
            agg_metrics = project_store.get_user_metrics()
        )

        # visualize state of project in main gui
        main_gui = ProjectStRenderer(project)
        main_gui.render()


if __name__ == '__main__':
    main()
