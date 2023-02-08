# %% 
import os
import json
import random
import re
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
    path = 'debaters_handbook/edition_19',
)

N_SPLITS = 6 # total number of splits into which source data is divided
SPLIT_IDX = 4 # index of this split / this week!
N_NEW_PROJECTS = 5 # number of new projects to create
STARTS_AT_WEEK = 9 # week at which to start the projects with split idx 0


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
# get githubtoken

with open('github_tokens.json') as f:
    d = json.load(f)
    GITHUB_TOKEN = d.get("token")

# %%
# get list with all argdown files from github

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

ad_files = [
    item.get("path") 
    for item in json.loads(r.text)
    if item.get("name").endswith(".argdown")
]
ad_files.sort()
print(f"{len(ad_files)} argdown files found.")
print(ad_files[:3])
# %%
# load data for split

# argdown files in this split
split_size = len(ad_files) // N_SPLITS
split_ad_files = ad_files[split_size * SPLIT_IDX : split_size * (SPLIT_IDX+1)] 

print(f"{len(split_ad_files)} argdown files in this split.")

data = []

for ad_file in split_ad_files:

    r = requests.get(
        'https://api.github.com/repos/{owner}/{repo}/contents/{path}'.format(
            owner=_SOURCES["owner"],
            repo=_SOURCES["repo"],
            path=ad_file
        ),
        headers={
            'accept': 'application/vnd.github.v3.raw',
            'authorization': 'token {}'.format(GITHUB_TOKEN)
                }
        )

    argdown_lines = r.text.splitlines()

    # remove empty lines at the beginning
    while argdown_lines[0].strip() == "":
        argdown_lines = argdown_lines[1:]

    thesis_pattern = r'\[(.+)\]: (.+) \{context: "(.+)"\}'
    pro_pattern = r'\s*\+\s+\[.+\]:\s+(.+)'
    con_pattern = r'\s*\-\s+\[.+\]:\s+(.+)'

    match = re.search(thesis_pattern, argdown_lines[0])
    if match is not None:
        title = match.group(1)
        thesis = match.group(2).strip()
        context = match.group(3)

    for line in argdown_lines[1:]:
        match = re.search(pro_pattern, line)
        if match is not None:
            reason = match.group(1)
            if reason:
                data.append({
                    "title": title,
                    "source_text": thesis+" "+reason,
                    "description": context,
                })
        else:
            match = re.search(con_pattern, line)
            if match is not None:
                reason = match.group(1)
                if reason:
                    data.append({
                        "title": title,
                        "source_text": "It is not the case that "+thesis[:1].lower()+thesis[1:]+" "+reason,
                        "description": context,
                    })
print(f"Loaded: {len(data)} data items for this split.")
# %%
split = data 
split[:2]

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
        project_id = f"Week{(SPLIT_IDX+STARTS_AT_WEEK)}-{e+1}-{project_id}"
        project_store.create_new_project(
            project_id=project_id,
            da2item=DeepA2Item(source_text=da2item.source_text),
            title=title,
            description=description,
            course_id=course_id,
        )



# %%
print("Done.")
# %%
