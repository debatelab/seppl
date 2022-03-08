"""streamlit_app.py"""

from google.cloud import firestore
import streamlit as st

from seppl.utils import StateOfAnalysis


def check_authentification():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
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


def main():
    """main script"""
    if check_authentification():

        # INIT Firestore

        # Authenticate to Firestore with the JSON account key.
        db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")

        # Create a reference to the Google post.
        doc_ref = db.collection("users").document("users")

        # Then get the data at that reference.
        doc = doc_ref.get()


        st.set_page_config(
            page_title="Seppl",
            page_icon="🤹",
            layout="wide",
        )
        # Sidebar
        st.sidebar.write("User key: X | 5 ⭐")

        selected_project = st.sidebar.selectbox(
            "Select a reconstruction project to work on:",
            ("", "Descartes", "NEW PROJECT")
        )


        if selected_project:

            # reload / initialize sofa
            if "sofa" not in st.session_state:
                st.session_state["sofa"] = StateOfAnalysis(selected_project)
            elif st.session_state["sofa"].project != selected_project:
                st.session_state["sofa"] = StateOfAnalysis(selected_project)

            sofa: StateOfAnalysis = st.session_state["sofa"]


            # Sidebar

            st.sidebar.subheader(sofa.project)

            st.sidebar.selectbox(
                "Currently shown global step:",
                list(range(1,sofa.global_step+1)),
                index=sofa.global_step-1
            )

            key_metrics = sofa.key_metrics()
            for metric, metr_col in zip(key_metrics, st.sidebar.columns(len(key_metrics))):
                metr_col.metric(metric["name"], metric["abs"], metric["delta"])


            # Main panel

            st.write(f"selected_project: {selected_project}")
            st.write(f"{sofa.project}: {sofa.text} {sofa.global_step} {sofa.visible_option}")


            # Let's see what we got!
            st.write("The id is: ", doc.id)
            st.write("The contents are: ", doc.to_dict())


            with st.expander("Source text, title and gist", expanded = True):
                col_source_text, col_gist = st.columns(2)
                with col_source_text:
                    sofa.render_source_text()
                with col_gist:
                    sofa.render_gist()


            with st.expander("Reasons and conjectures", expanded = True):
                col_annot_text, col_inf_graph = st.columns(2)
                with col_annot_text:
                    sofa.render_annotated_text()
                with col_inf_graph:
                    sofa.render_inference_graph()


            with st.expander("Logical reconstruction", expanded = True):
                col_argdown, col_formaliz = st.columns(2)
                with col_argdown:
                    sofa.render_argdown()
                with col_formaliz:
                    sofa.render_formalization()

            sofa.render_feedback()

            sofa.render_visible_option()


if __name__ == '__main__':
    main()
