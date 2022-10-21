# %% 

from google.cloud import firestore
import uuid
import unidecode
import os
import datetime
import secrets
import string
import pandas as pd

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
        "sofa_counter": 0,
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
    "david-lanius",
]
# %%

# create a-team users
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
# pd.DataFrame({"username": usernames, "password": passwords}).to_csv("kit_ars1_ws2223.csv", index=False)


# %%

kit_ars1_ws2223 = pd.read_csv("kit_ars1_ws2223.csv")
kit_ars1_ws2223

# %%

for _, row in kit_ars1_ws2223.iterrows():
    try:
        print(f"name: {row['username']}")
        # create_user(
        #     user_id=row["username"],
        #     password=row["password"],
        #     organization="kit-ars1-ws2223",
        # )
    except Exception as e:
        print(e)

# %%
# # create 2nd df with user info, only this one will be updated
# kit_ars1_ws2223_with_email = pd.read_csv("kit_ars1_ws2223.csv")
# if not "email" in kit_ars1_ws2223_with_email.columns:
#     kit_ars1_ws2223_with_email["email"] = ""
# if not "name" in kit_ars1_ws2223_with_email.columns:
#     kit_ars1_ws2223_with_email["name"] = ""
# if not "send_account_info" in kit_ars1_ws2223_with_email.columns:
#     kit_ars1_ws2223_with_email["send_account_info"] = False
#     # this field stores whether the account info needs to be send to the user
#     # it is used to filter the list when preparing and sending the serial email
# 
# kit_ars1_ws2223_with_email.to_csv("kit_ars1_ws2223_with_email.csv", index=False)

# %%
# update emails #

kit_ars1_ws2223_with_email = pd.read_csv("kit_ars1_ws2223_with_email.csv")

user_input = input("Has account-info been sent to all previously assigned SEPPL accounts (y/n)?")
if user_input == "y":
    kit_ars1_ws2223_with_email["send_account_info"] = False


## read ILIAS user list
ilias_ars1_ws2223 = pd.read_csv(
    "/Users/ggbetz/Documents/Philosophie/Lehre/WS2223/ars/2022_10_19_15-111666185064_member_export_2487257.csv"
)

ilias_ars1_ws2223["name"] = ilias_ars1_ws2223["Vorname"] + " " + ilias_ars1_ws2223["Nachname"]
ilias_ars1_ws2223["email"] = ilias_ars1_ws2223["E-Mail"]
ilias_ars1_ws2223.head()

## identify ilias students that have not been assigned to SEPPL-account
ilias_ars1_ws2223["has_account"] = ilias_ars1_ws2223["email"].isin(kit_ars1_ws2223_with_email["email"])
print("User without SEPPL account:")
new_users = ilias_ars1_ws2223[~ilias_ars1_ws2223["has_account"]][["name", "email"]]
print(new_users.head())

# free seppl accounts
free_seppl_accounts = kit_ars1_ws2223_with_email[
    kit_ars1_ws2223_with_email["email"].isna()
]
assert len(new_users) <= len(free_seppl_accounts)

newly_assigned_seppl_accounts = free_seppl_accounts[: len(new_users)].copy(deep=True)
newly_assigned_seppl_accounts["email"] = new_users["email"]
newly_assigned_seppl_accounts["name"] = new_users["name"].apply(unidecode.unidecode)
newly_assigned_seppl_accounts["send_account_info"] = True

# reassemble seppl accounts

kit_ars1_ws2223_with_email_updated = pd.concat([
    kit_ars1_ws2223_with_email[~kit_ars1_ws2223_with_email["email"].isna()],
    newly_assigned_seppl_accounts,
    free_seppl_accounts[len(new_users):],
])

# checks
assert(
    kit_ars1_ws2223_with_email_updated[["username","password"]].equals(
        kit_ars1_ws2223_with_email[["username","password"]]
    )
)
previously_assigned = kit_ars1_ws2223_with_email[~kit_ars1_ws2223_with_email["email"].isna()]
if len(previously_assigned) > 0:
    assert(
        previously_assigned.equals(
            kit_ars1_ws2223_with_email_updated[:len(previously_assigned)]
        )
    )

# write file
# kit_ars1_ws2223_with_email_updated.to_csv("kit_ars1_ws2223_with_email.csv", index=False)

# %%


# %%
