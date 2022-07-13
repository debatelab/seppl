"""SEPPL streamlit app"""

import streamlit as st

from seppl.backend.project import Project
from seppl.backend.gui import ProjectStRenderer

def main():
    """main script"""

    # initialize reconstruction project
    if "project" not in st.session_state:
        st.session_state["project"] = Project()

    # visualize state of project
    gui = ProjectStRenderer(st.session_state.project)
    gui.render()


if __name__ == '__main__':
    main()
