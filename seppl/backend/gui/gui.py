"""module for rendering projects and its components in streamlit"""

from __future__ import annotations
import logging
from typing import Any, Callable, Optional, Dict, List
import streamlit as st
from seppl.backend.gui.sofa_renderer import SofaStRenderer

from seppl.backend.gui.option_renderer import InputOptionStRenderer

from seppl.backend.project import Project
from seppl.backend.userinput import UserInput
import seppl.backend.session_state_keys as stsk



class SidebarRenderer:
    """renders the sidebar"""

    def __init__(
        self,
        user_id: str,
        project_list: List[str],
        project_loader: Callable,
    ):
        self.user_id = user_id
        self.project_list = project_list
        self.project_loader = project_loader

    def load_sofa(self, project: Project):
        """call project.load_sofa()"""
        if stsk.GLOBAL_STEP in st.session_state:
            project.load_sofa(st.session_state[stsk.GLOBAL_STEP])

    def render(
        self,
        project: Optional[Project] = None,
        agg_metrics: Optional[Dict] = None,
    ):
        """renders the sidebar"""
        first_line = f"{self.user_id}"
        if agg_metrics:
            candies = agg_metrics["count_metrics"]
            first_line += f" | {candies} 🍬"
        st.sidebar.write(first_line)

        # select project
        st.sidebar.selectbox(
            label="Project",
            options=[""]+self.project_list,
            key=stsk.PROJECT_ID,
            on_change=self.project_loader,
        )

        if project:
            # display project info
            if project.title:
                st.sidebar.subheader(project.title)
            if project.description:
                st.sidebar.caption(project.description)

            # select sofa
            st.sidebar.selectbox(
                label="Reconstruction step",
                options=list(reversed(range(project.sofa_counter))),
                index=project.sofa_counter-project.state_of_analysis.global_step-1,
                key=stsk.GLOBAL_STEP,
                on_change=self.load_sofa,
                kwargs=dict(project=project),
            )

            # display sofa info
            st.sidebar.caption(f"Resumes from step: {project.state_of_analysis.resumes_from_step}.")

            # sofa metrics
            mxd = project.metrics_data
            mxdelta = project.metrics_delta
            if mxd:
                level_str = int(mxd.get('reconstruction_phase',0)) * "🏅"
                if not level_str:
                    level_str = "**0**"
                st.sidebar.write(f"Reconstruction level: {level_str}")
                format_mx = lambda x: f"{(100*x):.0f}"
                col1, col2, col3 = st.sidebar.columns(3)
                col1.metric(
                    "complete",
                    format_mx(mxd.get("completeness")),
                    format_mx(mxdelta.get("completeness")) if mxdelta else None,
                )
                col2.metric(
                    "correct",
                    format_mx(mxd.get("correctness")),
                    format_mx(mxdelta.get("correctness")) if mxdelta else None,
                )
                col3.metric(
                    "comprehensive",
                    format_mx(mxd.get("depth")),
                    format_mx(mxdelta.get("depth")) if mxdelta else None,
                )


class ProjectStRenderer:
    """renders project in streamlit"""

    def __init__(self, project: Project):
        self._project: Project = project
        self._query: Optional[UserInput] = None

#    def submit(self, query):
#        """update"""
#        self._project.update(query)

    def submit(self, query_factory: Callable, raw_input: str):
        """update"""
        self._project.update(query_factory(raw_input))


    def render(self):
        """renders the project as streamlit gui"""
        # don't render if no project
        if self._project is None:
            st.warning("You're using SEPPL, an e-tutor based on neural language technologies, "
            "capable of creating original texts. The output of SEPPL is not fully "
            "predictabe and may contain suprising, even offending speech. Please "
            "use SEPPL responsibly.", icon="🤹")
            return None

        # render da2item
        SofaStRenderer().render(
            self._project.state_of_analysis,
            self._project.metrics_data
        )


        # metrics and feedback
        if self._project.state_of_analysis.global_step>0:
            st.info(self._project.state_of_analysis.feedback, icon="👉")

        if self._project.metrics_data:
            st.json(self._project.metrics_data, expanded=False)
            st.json(
                {
                    key: value for key, value in
                    self._project.metrics_data.items()
                    if key in ["reconstruction_phase", "completeness", "correctness", "depth"]
                },
                expanded=False,
            )
        

        # options
        # setup options
        input_options = self._project.state_of_analysis.input_options
        visible_option = self._project.state_of_analysis.visible_option
        option_gui = InputOptionStRenderer.option_gui_factory(
            input_options[visible_option],
            self.submit
        )
        # render options
        option_gui.render()
        if len(input_options)>1:
            st.button("Ask me something different", on_click = self._project.toggle_visible_option)

        # debugging: full da2 item
        st.json(self._project.state_of_analysis.as_dict(), expanded=False)

        # debugging: sofa info
        st.caption(f"showing {self._project.state_of_analysis.sofa_id} at {self._project.state_of_analysis.global_step}")
    