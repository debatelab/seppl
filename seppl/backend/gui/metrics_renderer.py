"""module for rendering da2items in streamlit"""

from __future__ import annotations
from typing import Dict

import streamlit as st

from seppl.backend.state_of_analysis import StateOfAnalysis


class MetricsStRenderer:
    """renders metrics data"""

    def __init__(self):
        pass


    def render(self, sofa: StateOfAnalysis, metrics_data: Dict):
        """renders da2 item"""

        metrics_expander = st.expander(
            label="Detailed evaluation of current analysis",
            expanded=False,
        )
        with metrics_expander:

            if metrics_data is None:
                st.write("No metrics data to display")
                return

            icon = lambda x: ("---" if x is None else ("✅" if x else "❌"))

            tab_da2item, tab_level0, tab_level1, tab_level2 = st.tabs(
                ["Contribution", "Base metrics (level 0)", "Exegetic metrics (level 1)", "Logical metrics(level 2)"]
            )

            # available components in reconstruction
            with tab_da2item:
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("Argument supplied")
                    check = icon(bool(sofa.da2item.argdown_reconstruction))
                    st.write(f"{check}&ensp;argument reconstruction")
                    st.caption("Informal analysis and cues supplied")
                    check = icon(bool(sofa.da2item.conclusion))
                    st.write(f"{check}&ensp;conclusion")
                    check = icon(bool(sofa.da2item.gist))
                    st.write(f"{check}&ensp;gist (argument's key point)")
                    check = icon(bool(sofa.da2item.source_paraphrase))
                    st.write(f"{check}&ensp;paraphrase of source text")
                    check = icon(bool(sofa.da2item.context))
                    st.write(f"{check}&ensp;context information")
                with col2:
                    st.caption("Source text annotations supplied")
                    check = icon(bool(sofa.da2item.reasons))
                    st.write(f"{check}&ensp;reason statements")
                    check = icon(bool(sofa.da2item.conjectures))
                    st.write(f"{check}&ensp;conjecture statements")
                    st.caption("Formal analysis supplied")
                    check = icon(bool(sofa.da2item.premises_formalized))
                    st.write(f"{check}&ensp;formalization of premises")
                    check = icon(bool(sofa.da2item.intermediary_conclusions_formalized))
                    st.write(f"{check}&ensp;formalization of intermediary conclusions")
                    check = icon(bool(sofa.da2item.conclusion_formalized))
                    st.write(f"{check}&ensp;formalization of final conclusion")
                    check = icon(bool(sofa.da2item.plchd_substitutions))
                    st.write(f"{check}&ensp;substitutions for placeholders")


            # base metrics
            with tab_level0:
                st.caption("Basic quality criteria")
                check = icon(metrics_data.get("ValidArgdownScore"))
                st.write(f"{check}&ensp;valid argdown syntax")
                check = icon(metrics_data.get("PCStructureScore"))
                st.write(f"{check}&ensp;premise-conclusion structure")
                check = icon(metrics_data.get("NoRedundancyScore"))
                st.write(f"{check}&ensp;no redundant statements in argument reconstruction")
                check = icon(metrics_data.get("ConclMatchesRecoScore"))
                st.write(f"{check}&ensp;argument's final statement matches separetely-provided conclusion")
                check = icon(metrics_data.get("RecoCohSourceScore"))
                st.write(f"{check}&ensp;argument reconstruction minimally coheres with source text")

            # exegtic metrics
            with tab_level1:
                st.caption("Interpretative quality criteria")
                check = icon(metrics_data.get("ReasonsAlignedScore"))
                st.write(f"{check}&ensp;reason statements aligned with argument reconstruction (i.e., refer to premises)")
                check = icon(metrics_data.get("ConjecturesAlignedScore"))
                st.write(f"{check}&ensp;conjecture statements aligned with argument reconstruction (i.e., refer to conclusions)")
                check = icon(metrics_data.get("ReasConjCohRecoScore"))
                st.write(f"{check}&ensp;argument reconstruction minimally coheres with reasons and/or conjectures")

            # logical metrics
            with tab_level2:
                st.caption("Logical quality criteria")
                check = icon(metrics_data.get("ConsistentUsageScore"))
                st.write(f"{check}&ensp;premises (and interm. conclusions) used in sub-inferences")
                check = icon(metrics_data.get("CompleteFormalization"))
                st.write(f"{check}&ensp;complete formalization of argument")
                check = icon(metrics_data.get("WellFormedFormScore"))
                st.write(f"{check}&ensp;syntactically correct logical formulas")
                check = icon(metrics_data.get("WellFormedKeysScore"))
                st.write(f"{check}&ensp;well-formed placeholder substitions")
                check = icon(metrics_data.get("FormCohRecoScore"))
                st.write(f"{check}&ensp;formalization semantically coheres with argument reconstruction")
                check = icon(metrics_data.get("GlobalDeductiveValidityScore"))
                st.write(f"{check}&ensp;global deductive validity (final conclusion follows from premisses)")
                check = icon(metrics_data.get("LocalDeductiveValidityScore"))
                st.write(f"{check}&ensp;local deductive validity (each sub-inference is valid)")
