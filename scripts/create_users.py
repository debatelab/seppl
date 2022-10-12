# %% 

from google.cloud import firestore
import uuid
import os
import datetime
import secrets
import string

# %%
os.chdir("..")
db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")

# %%

def create_user(
    user_id: str,
    password: str,
    organization: str = "default_oraganization",
):

    if not (user_id and password):
        raise ValueError("user_id and password must not be empty")

    # Check if user already exists
    user_ref = db.collection("users").document(user_id)
    if user_ref.get().exists:
        raise ValueError(f"user {user_id} already exists")

    # Create user
    user_ref.set({
        "password": password,
        "organization": organization,
        "created": datetime.datetime.now().isoformat(),
    })


# %%

alphabet = string.ascii_letters + string.digits

# %%

password = ''.join(secrets.choice(alphabet) for i in range(9)) 
create_user(
    user_id="test_user1",
    password=password,
    organization="a-team",
)




# %%

ateam = [
    "clara.schuler",
    "hannah.mueller",
    "katharina.wolf",
    "dilara.akyildiz",
    "richard.lohse",
    "christian.seidel",
    "georg.brun",
    "basti.cacean",
]
# %%

for user_id in ateam:
    password = ''.join(secrets.choice(alphabet) for i in range(9))
    try:
        create_user(
            user_id=user_id,
            password=password,
            organization="a-team",
        )
    except Exception as e:
        print(e)
# %%

from faker import Faker
import unidecode
import pandas as pd
fake = Faker("it_IT")

# ARS I 22/23

# usernames = []
# passwords = []
# 
# for _ in range (200):
#     name = unidecode.unidecode(fake.name())
#     name = name.replace(".", "")
#     name = name.replace(" ", "-").lower()
#     usernames.append(name)
#     password = ''.join(secrets.choice(alphabet) for i in range(9))
#     passwords.append(password)
# 
# pd.DataFrame({"usernames": usernames, "passwords": passwords}).to_csv("kit_ars1_ws2223.csv", index=False)


# %%

kit_ars1_ws2223 = pd.read_csv("kit_ars1_ws2223.csv")
kit_ars1_ws2223


# %%
