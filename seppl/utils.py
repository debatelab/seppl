"""utils"""

from typing import Callable, List, Dict, Any

import streamlit as st

from deepa2 import DeepA2Item


ASK_STHG_ELSE = "ASK_STHG_ELSE"


class InputOption:
    """Base input option"""

    target_field: str  # field in da2item this input option targets
    sofa: Callable  # parent sofa object
    user_input = None # input eventually provided by user

    def __init__(self, sofa, text = "Some text"):
        self.text = text
        self.sofa = sofa

    def _on_click(self, user_input = None):
        self.user_input = user_input
        self.sofa.update()

    def render(self, on_click: Callable):
        """render"""
        st.write(self.text)

        answer1 = st.button("1", on_click = self._on_click, kwargs = dict(user_input="1"))
        answer2 = st.button("2", on_click = self._on_click, kwargs = dict(user_input="2"))
        st.write("Or:")
        st.button(
            "Ask me something else, please.",
            on_click = on_click,
            kwargs = dict(user_input=ASK_STHG_ELSE)
        )
        if answer1:
            return "1"
        elif answer2:
            return "2"
        else:
            return None





class StateOfAnalysis:
    """represent a current state of logical analysis"""
    _input_options: List[InputOption]
    global_step: int
    resumes_from: int
    visible_option: int
    da2item: DeepA2Item
    metrics: Dict[str, Any]
    feedback: str

    """state of the current analysis"""
    def __init__(self, text = "Some text"):
        self.text = text
        self.project = text
        self.global_step = 0
        self.visible_option = 0
        self.feedback = "That was excellent!"
        self._input_options = [
            InputOption(self, "Please specify the conclusion:"),
            InputOption(self, "Please specify the reasons:")
        ]
        self.da2item = DeepA2Item()

    @classmethod
    def load_from_firestore(cls):
        """loads sofa from firestore"""

    def update(self):
        """central update method, called if user has provided input"""
        # fetch user input from currently visible InputOption widget
        user_input = self.get_visible_input_option().user_input
        if user_input:
            if user_input==ASK_STHG_ELSE:
                self.increment_visible_input_option()
            else:
                if self.da2item.argdown_reconstruction:
                    self.da2item.argdown_reconstruction += user_input
                else:
                    self.da2item.argdown_reconstruction = user_input
                self.text += user_input
                self.global_step += 1

    def increment_visible_input_option(self):
        """increments visible input option"""
        self.visible_option += 1
        self.visible_option = self.visible_option % len(self._input_options)

    def get_visible_input_option(self) -> InputOption:
        """returns visible input option"""
        return self._input_options[self.visible_option]

    def render_visible_option(self):
        """renders visible input option"""
        input_option = self.get_visible_input_option()
        input_option.render(on_click = self.update)

    def render(self):
        """render"""
        st.write(self.text)

    def key_metrics(self) -> List[Dict[str,int]]:
        """key metrics"""
        return [
            {"name": "Completeness", "abs": 70, "delta": 2},
            {"name": "Coherence", "abs": 12, "delta": -9},
            {"name": "Validity", "abs": 86, "delta": 14},
        ]

    def render_feedback(self):
        """renders feedback"""
        st.info(self.feedback)

    def render_annotated_text(self):
        """render annot text"""
        st.write("annotated text from sofa")

    def render_inference_graph(self):
        """render inference_graph"""
        st.write("inference_graph from sofa")

    def render_argdown(self):
        """render argdown"""
        st.write(self.da2item.argdown_reconstruction)

    def render_formalization(self):
        """render formalization"""
        st.write("formalization from sofa")

    def render_source_text(self):
        """render source_text"""
        st.write("source_text from sofa")

    def render_gist(self):
        """render gist"""
        st.write("title from sofa")
        st.write("gist from sofa")
        st.write("paraphrase from sofa")
