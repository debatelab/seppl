"""streamlit_app.py"""

from google.cloud import firestore
import streamlit as st



class InputOption:

    def __init__(self, text = "Some text"):
        self.text = text
    
    def render(self):
        st.write(self.text)


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
        page_icon="🐢",
        layout="wide",
    )
    # Sidebar
    st.sidebar.write("User: XY")
    selected_project = st.sidebar.selectbox(
        "Select a reconstruction project to work on:",
        ("", "Descartes", "NEW PROJECT")
    )


    if selected_project:
        st.write(selected_project)


        # Let's see what we got!
        st.write("The id is: ", doc.id)
        st.write("The contents are: ", doc.to_dict())


        with st.expander("Reasons and conjectures", expanded = True):
            col_annot_text, col_inf_graph = st.columns(2)
            with col_annot_text:
                st.write("Here goes the annotated text")
            with col_inf_graph:
                st.write("Here goes the inference graph")


        with st.expander("Logical reconstruction", expanded = True):
            col_argdown, col_formaliz = st.columns(2)
            with col_argdown:
                st.write("Here goes the argdown reco")
            with col_formaliz:
                st.write("Here goes the formalization")

        input_option = InputOption("Please specify the conclusion:")

        input_option.render()



