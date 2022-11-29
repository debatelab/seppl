# %% 
import os
from io import StringIO
import json
import random
from typing import List

from deepa2 import DeepA2Item
from google.cloud import firestore
import pandas as pd
import requests  # type: ignore

from seppl.backend.project_store import FirestoreProjectStore
from seppl.backend.inference import inference_factory


_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"


_SOURCES = dict(
    owner = 'debatelab',
    repo = 'pros-and-cons',
    path = 'procon.org/procon-org_20221011.jsonl',
)

N_SPLITS = 8 # total number of splits into which source data is divided
SPLIT_IDX = 5 # index of this split / this week!
N_NEW_PROJECTS = 5 # number of new projects to create

# %%

os.chdir("..")

# initialze database
db = firestore.Client.from_service_account_json("seppl-deepa2-firebase-key.json")

# initialize inference pipeline
inference = inference_factory(
    pipeline_id = _PIPELINE,
    textgen_server_url = _TEXTEGEN_SERVER_URL,
    loss_server_url = _LOSS_SERVER_URL,
)


# %%

def get_users(organization: str) -> List[str]:
    """get users from organization"""
    users = []
    for user in db.collection("users").stream():
        if user.to_dict()["organization"] == organization:
            users.append(user.id)
    return users

# %%

# test
# get_users("a-team")

# %%
# get githubtoken

with open('github_tokens.json') as f:
    d = json.load(f)
    GITHUB_TOKEN = d.get("token")

# %%
# get data from github

# send a request
r = requests.get(
    'https://api.github.com/repos/{owner}/{repo}/contents/{path}'.format(
        owner=_SOURCES["owner"],
        repo=_SOURCES["repo"],
        path=_SOURCES["path"]
    ),
    headers={
        'accept': 'application/vnd.github.v3.raw',
        'authorization': 'token {}'.format(GITHUB_TOKEN)
            }
    )

# convert string to StringIO object
string_io_obj = StringIO(r.text)

data = []
for line in string_io_obj:
    data.append(json.loads(line))

len(data)

# %%

# flatten data (one da2 item per line)

data_flat = []
for item in data:
    for reason in item["reasons"]:
        data_flat.append({
            "source_text": reason,
            "title": item["title"],
            "description": item["description"],
        })
# shuffle data
random.seed(42)
random.shuffle(data_flat)

len(data_flat)


# %%
# split data

from_idx = int(SPLIT_IDX / N_SPLITS * len(data_flat))
to_idx = int((SPLIT_IDX+1) / N_SPLITS * len(data_flat))
split = data_flat[from_idx:to_idx]
# %%
split[SPLIT_IDX]

# %%

# load user from course list

kit_ars1_ws2223_with_email = pd.read_csv("kit_ars1_ws2223_with_email.csv")
kit_ars1_ws2223_with_email["username"].to_list()

# %%
import unidecode

#userlist = get_users("a-team")
userlist = kit_ars1_ws2223_with_email["username"].to_list()
course_id = "kit-ars1-ws2223"

for user_id in userlist:
    print(user_id)
    project_store = FirestoreProjectStore(
        user_id=user_id,
        inference=inference,
    )
    sample = random.sample(split, N_NEW_PROJECTS)
    for e, data_item in enumerate(sample):      
        da2item = DeepA2Item(source_text=data_item["source_text"])
        title = data_item["title"]
        description = data_item["description"]
        project_id = unidecode.unidecode(title[:30]).replace(" ", "_")
        project_id = ''.join(c for c in project_id if c.isalnum())
        project_id = f"Week{(SPLIT_IDX+1)}-{e}-{project_id}"
        project_store.create_new_project(
            project_id=project_id,
            da2item=DeepA2Item(source_text=da2item.source_text),
            title=title,
            description=description,
            course_id=course_id,
        )



# %%
