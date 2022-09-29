"""SEPPL streamlit app"""

import logging

import streamlit as st

from seppl.backend.project import Project
from seppl.backend.gui.gui import ProjectStRenderer
from seppl.backend.inference import inference_factory
from seppl.backend.project_store import DummyLocalProjectStore

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

# TODO: load this from config.yaml
_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"

# TODO: load from database

def main():
    """main script"""

    # initialize reconstruction project
    if "project" not in st.session_state:
        # initialize inference pipeline
        inference = inference_factory(
            pipeline_id = _PIPELINE,
            textgen_server_url = _TEXTEGEN_SERVER_URL,
            loss_server_url = _LOSS_SERVER_URL,
        )
        project_store = DummyLocalProjectStore(
            inference=inference,
            project_id="test_project",
            user_id="test_user",
        )
        st.session_state["project"] = Project(
            inference = inference,
            project_store = project_store,
            project_id = "test_project",
        )

    # visualize state of project
    gui = ProjectStRenderer(st.session_state.project)
    gui.render()


if __name__ == '__main__':
    main()
