"""module for rendering da2items in streamlit"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import re
from typing import Tuple, Dict, List, Any, Optional

from deepa2 import DeepA2Item, QuotedStatement
from deepa2.parsers import DeepA2Parser, Argument
import graphviz
import seaborn as sns
from spacy import displacy
import streamlit as st
import textwrap

from seppl.backend.state_of_analysis import StateOfAnalysis

class AbstractDA2ItemRenderer(ABC):
    """abstract base class for rendering subcomponents of da2items"""

    sofa: StateOfAnalysis

    def __init__(self, sofa: StateOfAnalysis):
        self.sofa = sofa

    def get_parsed_argdown(self) -> Argument:
        argument = self.sofa.metrics.from_cache("parsed_argdown")
        if argument is None:
            argument = DeepA2Parser.parse_argdown(
                self.sofa.da2item.argdown_reconstruction
            )
        return argument


    @abstractmethod
    def render(self):
        """render da2item subcomponent"""

class FormalizationRenderer(AbstractDA2ItemRenderer):
    """renders argument formalizations"""

    metrics_data: Optional[Dict] = None

    def __init__(self, sofa: StateOfAnalysis, metrics_data: Dict = None):
        super().__init__(sofa)
        self.metrics_data = metrics_data

    def get_formalization_list(self) -> str:
        """format formalization as markdown"""
        # format premises and conclusion and store in seprate lists
        premise_list = []
        if self.sofa.da2item.premises_formalized:
            for fp in self.sofa.da2item.premises_formalized:
                premise_list.append(
                    {
                        "text": f"(P{fp.ref_reco}) `{fp.form}`",
                        "ref_reco": fp.ref_reco
                    }
                )

        interm_concl_list = []
        if self.sofa.da2item.intermediary_conclusions_formalized:
            for fi in self.sofa.da2item.intermediary_conclusions_formalized:
                interm_concl_list.append(
                    {
                        "text": f"(C{fi.ref_reco}) `{fi.form}`",
                        "ref_reco": fi.ref_reco
                    }
                )
        conclusion_list = []
        if self.sofa.da2item.conclusion_formalized:
            for fc in self.sofa.da2item.conclusion_formalized:
                conclusion_list.append(
                    {
                        "text": f"(C{fc.ref_reco}) `{fc.form}`",
                        "ref_reco": fc.ref_reco
                    }
                )
        # merge and sort by ref_reco
        formalization_list = premise_list + interm_concl_list + conclusion_list
        formalization_list.sort(key=lambda x: x["ref_reco"])

        formalizations_str = "  \n".join([f["text"] for f in formalization_list])
        return formalizations_str


    def render(self):
        """render formalization"""
        if not (
            self.sofa.da2item.premises_formalized
            or self.sofa.da2item.intermediary_conclusions_formalized
            or self.sofa.da2item.conclusion_formalized
        ):
            st.write("No formalizations to display.")
            return

        # formalizations
        st.write(self.get_formalization_list())

        # placeholders
        if self.sofa.da2item.plchd_substitutions:
            st.caption("Placeholders:")
            plcds_str = [
                f"`{plcd}`: {sub}"
                for plcd, sub
                in self.sofa.da2item.plchd_substitutions
            ]
            st.write("  \n".join(plcds_str))

        # evaluation
        if self.metrics_data:
            global_val = "❌"
            local_val = "❌"

            if self.metrics_data.get("GlobalDeductiveValidityScore"):
                global_val = "✅"
            if self.metrics_data.get("LocalDeductiveValidityScore"):
                local_val = "✅"
            st.caption("Deductive validity:")
            st.write(f"{global_val} global inference  \n{local_val} local sub-inferences")

class ArgumentGraphRenderer(AbstractDA2ItemRenderer):
    """renders the recos as graphviz graph"""

    PREMISE_TEMPLATE = """<
    <TABLE BORDER="0" COLOR="#444444" CELLPADDING="10" CELLSPACING="2">
    <TR><TD BORDER="0" BGCOLOR="{bgcolor}" STYLE="rounded"><FONT FACE="sans serif" POINT-SIZE="12"><B>({label})</B> {text}</FONT></TD></TR>
    </TABLE>
    >"""

    CONCLUSION_TEMPLATE = """<
    <TABLE BORDER="0" COLOR="#444444" CELLPADDING="10" CELLSPACING="2">
    <TR><TD BORDER="1" BGCOLOR="white" CELLPADDING="4"><FONT FACE="sans serif" POINT-SIZE="10">{inference}</FONT></TD></TR>
    <TR><TD BORDER="0" BGCOLOR="{bgcolor}" STYLE="rounded"><FONT FACE="sans serif" POINT-SIZE="12"><B>({label})</B> {text}</FONT></TD></TR>
    </TABLE>
    >"""

    argument: Argument
    graphviz_graph: graphviz.Digraph = None

    def __init__(
        self,
        sofa: StateOfAnalysis,
        colors: Dict,
        metrics_data: Dict,
    ):
        super().__init__(sofa)
        self.colors = colors
        if sofa.da2item.argdown_reconstruction:
            self.argument = self.get_parsed_argdown()
            if metrics_data and self.argument:
                if metrics_data.get("ConsistentUsageScore", False):
                    self.graphviz_graph = self.get_inference_graph()

    def get_inference_graph(self) -> graphviz.Digraph:
        """construct inference graph"""
        if self.argument is None:
            return None
        graph = graphviz.Digraph()
        graph.attr(ratio="compress", size="6,10", orientation="portrait", overlay="compress")
        for item in self.argument.statements:
            # wrap text
            textlines = textwrap.wrap("(X) " + item.text, width=30)
            text = "<BR/>".join(textlines)[4:]
            # create nodes
            graph.attr("node", shape="plaintext")
            if not item.is_conclusion:
                # premise node
                graph.node(
                    "node%d" % item.label,
                    self.PREMISE_TEMPLATE.format(
                        text=text,
                        label=item.label,
                        bgcolor=self.colors.get("P%d" % item.label, "white"),
                    ),
                    tooltip=textwrap.fill(item.text, width=30),
                )
            else:
                # conclusion and inference node
                inference = "with <I>" + ", ".join(item.schemes) + "</I>"
                if item.variants:
                    inference += " (" + (", ".join(item.variants)) + "):"
                inference_lines = textwrap.wrap(inference, width=40)
                inference = "<BR/>".join(inference_lines)
                graph.node(
                    "node%d" % item.label,
                    self.CONCLUSION_TEMPLATE.format(
                        text=text,
                        label=item.label,
                        bgcolor=self.colors.get("C%d" % item.label, "white"),
                        inference=inference,
                    ),
                    tooltip=textwrap.fill(item.text, width=30),
                )
            # add edges
            if item.uses:
                for i in item.uses:
                    graph.edge("node%d" % i, "node%d" % item.label)

        return graph

    def render(self):
        """renders the argument graph"""
        if self.graphviz_graph:
            st.graphviz_chart(self.graphviz_graph, use_container_width=True)
        else:
            st.write("No inference graph to display.")

class SourceTextRenderer(AbstractDA2ItemRenderer):
    """renders the source text including conjectures and reasons"""
    HTML_WRAPPER = """<div style="overflow-x: auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem; margin-bottom: 2.5rem">{}</div>"""

    def __init__(self, sofa: StateOfAnalysis):
        super().__init__(sofa)
        self.displacy_html, self.colors = self.build_displacy_html(sofa.da2item)


    @staticmethod
    def get_ds_entities(
        source_text: str,
        quotes: List[QuotedStatement],
        type:str="reasons"
    ) -> Tuple[List[Dict[str, Any]], Dict]:
        """get entities and colors for displacy"""
        # set up template and color profiles (different for reasons and conjectures)
        if type == "reasons":
            lab_templ = "P%d"
            color_profile = "mako_r"
        elif type == "conjectures":
            lab_templ = "C%d"
            color_profile = "rocket_r"
        else:
            return [], {}

        # determine start and end indices of quotes in source text
        ents: List[Dict[str, Any]] = []
        pointer: int = 0
        for quote in quotes:
            if quote.text in source_text:
                idx_start = source_text.index(quote.text, pointer)
                idx_end = idx_start + len(quote.text)
                pointer = idx_end
                ref_reco = quote.ref_reco if quote.ref_reco else 0
                ents.append(
                    {
                        "start": idx_start,
                        "end": idx_end,
                        "label": lab_templ % ref_reco,
                    }
                )

        # construct colors for reason statements
        palette = sns.color_palette(color_profile, round(3 * len(ents))).as_hex()
        colors = {ent["label"]: palette[i] for i, ent in enumerate(ents)}

        return ents, colors

    def build_displacy_html(self, da2item: DeepA2Item) -> Tuple[str, Dict]:
        """returns displacy html as str and colors (to be reused in graph)"""
        # get and merge entities and colors for displacy
        # TODO: simplify!
        ents: List[Dict[str, Any]] = []
        colors: Dict = {}
        if da2item.conjectures:
            ents, colors = self.get_ds_entities(
                da2item.source_text,
                da2item.conjectures,
                type="conjectures"
            )
            if da2item.reasons:
                ents_r, colors_r = self.get_ds_entities(
                    da2item.source_text,
                    da2item.reasons,
                    type="reasons",
                )
                ents = ents + ents_r
                colors.update(colors_r)
                ents = sorted(ents, key=lambda item: item["start"])
        elif da2item.reasons:
            ents, colors = self.get_ds_entities(
                da2item.source_text,
                da2item.reasons,
                type="reasons"
            )

        options = {"colors": colors}
        ex = [
            {"text": da2item.source_text, "ents": ents, "title": None}
        ]
        displacy_html = displacy.render(
            ex, style="ent", options=options, manual=True
        )

        return displacy_html, colors


    def render(self):
        """renders da2 item, returns colors for reuse in graph"""
        st.write(
            self.HTML_WRAPPER.format(self.displacy_html),
            unsafe_allow_html=True
        )

class ArgdownRenderer(AbstractDA2ItemRenderer):
    """renders the argdown text"""

    argdown_html: Optional[str] = None

    def __init__(
        self,
        sofa: StateOfAnalysis,
        colors: Dict,
        metrics_data: Dict,
    ):
        super().__init__(sofa)
        if self.sofa.da2item.argdown_reconstruction:
            self.argdown_html = self.format_argdown(
                self.sofa.da2item.argdown_reconstruction,
                colors,
            )

    @staticmethod
    def format_argdown(raw_argdown: str, colors: Dict) -> str:
        """format raw argdown (inserting line breaks)"""

        # construct color map for statements in argument
        all_colors = {("color(" + str(i + 1) + ")"): "white" for i in range(50)}
        if colors:
            all_colors.update({("color(" + k[1:] + ")"): v for k, v in colors.items()})

        # formats a statement block (background color for labels)
        def format_statement_block(s):
            r = re.sub(
                "(\([0-9]+\))",
                r'<b><span style="background-color:{color\1}">\1</span></b>',
                s,
            )
            r = r.format(**all_colors)
            r = r.replace("\n", "<br>")
            return r

        # formats inference blocks (bold)
        def format_inference_block(s: str):
            formatted = "<b>" + s + "</b>"
            formatted = formatted.replace("\n", "<br>")
            return formatted

        # split into blocks
        splits = re.split(r"(\s--\s[^-]*\s--\s)", raw_argdown)

        # format, alternating between statement and inference blocks
        argdown: str = ""
        is_inference = False
        for block in splits:
            if is_inference:
                argdown += format_inference_block(block)
            else:
                argdown += format_statement_block(block)
            is_inference = not is_inference

        # embed
        argdown = """<div style="font-family:monospace;font-size:14px">%s<br><br></div>""" % argdown

        return argdown

    def render(self):
        """renders the argdown text"""
        if not self.argdown_html:
            st.write("No argument reconstruction to display.")
        else:
            st.write(self.argdown_html, unsafe_allow_html=True)

class CuesRenderer(AbstractDA2ItemRenderer):
    """renders informal cues (gist etc.)"""

    def render(self):
        """render cues"""
        da2item = self.sofa.da2item
        some_cue = False
        if da2item.gist:
            st.caption("Gist (key point)")
            st.write(da2item.gist)
            some_cue = True
        if da2item.conclusion:
            st.caption("Conclusion")
            st.write(da2item.conclusion[0].text)
            some_cue = True
        if da2item.source_paraphrase:
            st.caption("Source paraphrase")
            st.write(da2item.source_paraphrase)
            some_cue = True
        if da2item.context:
            st.caption("Context")
            st.write(da2item.context)
            some_cue = True
        if not some_cue:
            st.write("No cues to display.")

class SofaStRenderer:
    """renders da2 item"""

    def __init__(self):
        pass

    def render(self, sofa: StateOfAnalysis, metrics_data: Dict):
        """renders da2 item"""

        if sofa is None:
            st.info("No argument reconstruction to display")

        source_renderer = SourceTextRenderer(sofa)
        arg_graph_renderer = ArgumentGraphRenderer(
            sofa = sofa,
            colors = source_renderer.colors,
            metrics_data = metrics_data,
        )
        form_renderer = FormalizationRenderer(
            sofa = sofa,
            metrics_data=metrics_data,
        )
        argdown_renderer = ArgdownRenderer(
            sofa = sofa,
            colors = source_renderer.colors,
            metrics_data = metrics_data,
        )
        cues_renderer = CuesRenderer(sofa)

        
        legal_macro_structures: bool = False
        if metrics_data:
            legal_macro_structures = metrics_data.get("ConsistentUsageScore", False)

        # Show output
        col_source, col_reco = st.columns(2)
        with col_source:
            st.caption('Reasons and conjectures in source text')
            source_renderer.render()

        with col_reco:
            ig_expander = st.expander(
                label="Argument reconstruction (inference graph)",
                expanded=legal_macro_structures,
            )
            with ig_expander:
                arg_graph_renderer.render()

            lgc_expander = st.expander(
                label="Formalization",
                expanded=bool(sofa.da2item.premises_formalized)
            )
            with lgc_expander:
                form_renderer.render()

            ad_expander = st.expander(
                label="Argument reconstruction (argdown snippet)",
                expanded=(not legal_macro_structures),
            )
            with ad_expander:
                argdown_renderer.render()

            cues_expander = st.expander(
                label="Informal analysis and cues",
                expanded=False,
            )
            with cues_expander:
                cues_renderer.render()


