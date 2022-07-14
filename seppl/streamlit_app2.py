"""SEPPL streamlit app"""

import logging

import streamlit as st

from seppl.backend import Project
from seppl.backend.gui.gui import ProjectStRenderer
from seppl.backend.inputoption import ChoiceOption
from seppl.backend.inference import inference_factory

logging.basicConfig(
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

# TODO: load this from config.yaml
_PIPELINE = "BigModelPipeline"
_MODEL_PATH = "debatelab/argument-analyst"
_MODEL_REVISION = "main"


def main():
    """main script"""

    # initialize inference pipeline
    inference = inference_factory(
        pipeline_id = _PIPELINE,
        model_path = _MODEL_PATH,
        revision = _MODEL_REVISION,
        auth_token=st.secrets["api_token"]
    )

    # initialize reconstruction project
    if "project" not in st.session_state:
        # TODO
        # replace dummy initialization
        option = ChoiceOption(
            context = ["(1) P --- (2) C", "(1) Q --- (2) C"],
            question = "Which reco is better A or B?",
            input_type = "ARGDOWN_INPUT",
            answers = {
                "reco 1": "(1) P ---(2) C",
                "reco 2": "(1) Q ---(2) C",
            }
        )
        st.session_state["project"] = Project(
            inference = inference,
            input_options = [option],
        )

    # visualize state of project
    gui = ProjectStRenderer(st.session_state.project)
    gui.render()


if __name__ == '__main__':
    main()
