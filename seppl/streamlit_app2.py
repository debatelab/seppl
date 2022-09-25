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
_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"

# TODO: load from database
_SOURCE_TEXT = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely. Animals are sentient beings that
have emotions and social connections. Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""

def main():
    """main script"""

    # initialize inference pipeline
    inference = inference_factory(
        pipeline_id = _PIPELINE,
        textgen_server_url = _TEXTEGEN_SERVER_URL,
        loss_server_url = _LOSS_SERVER_URL,
    )

    # initialize reconstruction project
    if "project" not in st.session_state:
        # TODO
        # replace dummy initialization
        option = ChoiceOption(
            context = ["(1) P --- (2) C", "(1) Q --- (2) C"],
            question = "Which reco is better A or B?",
            da2_field = "argdown_reconstruction",
            answers = {
                "reco 1": "(1) P ---(2) C",
                "reco 2": "(1) Q ---(2) C",
            }
        )
        st.session_state["project"] = Project(
            inference = inference,
            input_options = [option],
            source_text = _SOURCE_TEXT,
        )

    # visualize state of project
    gui = ProjectStRenderer(st.session_state.project)
    gui.render()


if __name__ == '__main__':
    main()
