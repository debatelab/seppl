"""SEPPL streamlit app"""

import logging

import streamlit as st

from seppl.backend.project import Project
from seppl.backend.gui.gui import ProjectStRenderer
from seppl.backend.inference import AbstractInferencePipeline, inference_factory
from seppl.backend.project_store import AbstractProjectStore, FirestoreProjectStore

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

# TODO: load this from config.yaml
_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"


def check_authentification() -> bool:
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            st.session_state["user_id"] = "marcantonio-galuppi"
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True


def load_project(
    inference: AbstractInferencePipeline,
    project_store: AbstractProjectStore,
) -> None:
    """initialize reconstruction project"""
    if st.session_state.project_id:
        st.session_state["project"] = Project(
            inference = inference,
            project_store = project_store,
            project_id = st.session_state.project_id,
        )


def main():
    """main script"""

    if check_authentification():

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

        # select project
        st.selectbox(
            label="Select project",
            options=[""]+st.session_state["project_list"],
            key="project_id",
            on_change=load_project,
            kwargs=dict(
                inference=inference,
                project_store=project_store,
            ),
        )

        if "project" in st.session_state:
            # visualize state of project
            gui = ProjectStRenderer(st.session_state.project)
            gui.render()


if __name__ == '__main__':
    main()
