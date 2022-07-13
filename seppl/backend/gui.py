"""MixIns for rendering projects and its components in streamlit"""

from __future__ import annotations
from typing import Optional
import streamlit as st

from seppl.backend.project import Project
from seppl.backend.userinput import ArgdownInput, UserInput

class ProjectStRenderer:
    """renders project in streamlit"""

    def __init__(self, project: Project):
        self._project: Project = project
        self._query: Optional[UserInput] = None

    def submit(self):
        """update"""
        self._project.update(self._query)

    def render(self):
        """renders the project as treamlit gui"""
        st.write("RENDERING THE PROJECT")
        st.write(f"step: {self._project.step}")
        st.write(f"text: {self._project.state_of_analysis.text}")

        # TODO
        # placeholder for testing
        self._query = ArgdownInput()

        st.button("Submit", on_click = self.submit)