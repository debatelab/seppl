"""streamlit_app.py"""

from google.cloud import firestore
import streamlit as st



def main():
    """main script"""

    # INIT Firestore

    # Authenticate to Firestore with the JSON account key.
    db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")

    user_list = list(db.collection("users").list_documents())
    st.write(f"Users: {user_list}")

    first_user = user_list[0].get()
    st.write(f"First user {first_user.id}: {first_user.to_dict()}")


    # Create a reference to the Google post.
    doc_ref = db.collection("users").document("marcantonio-galuppi")

    # Then get the data at that reference.
    doc = doc_ref.get()


    # Let's see what we got!
    st.write("The id is: ", doc.id)
    st.write("The contents are: ", doc.to_dict())

    doc_ref = db.collection("users").document("non-existent-user")
    doc = doc_ref.get()
    st.write(f"User {doc.id} exists: ", doc.exists)



if __name__ == '__main__':
    main()
