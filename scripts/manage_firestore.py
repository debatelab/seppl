# %% 
from deepa2 import DeepA2Item

from seppl.backend.project_store import FirestoreProjectStore
from seppl.backend.inference import inference_factory

# DUMMY DATA
_SOURCE_TEXT = """It is cruel and unethical to kill animals for food
when vegetarian options are available, especially because raising animals
in confinement for slaughter is cruel, and many animals in the United
States are not slaughtered humanely. Animals are sentient beings that
have emotions and social connections. Scientific studies show that cattle,
pigs, chickens, and all warm-blooded animals can experience stress, pain,
and fear."""


_PIPELINE = "DA2MosecPipeline"
_TEXTEGEN_SERVER_URL = "http://kriton.philosophie.kit.edu:8002/inference"
_LOSS_SERVER_URL = "http://kriton.philosophie.kit.edu:8001/inference"

# %%

da2item = DeepA2Item(source_text=_SOURCE_TEXT)
# %%

# initialize inference pipeline
inference = inference_factory(
    pipeline_id = _PIPELINE,
    textgen_server_url = _TEXTEGEN_SERVER_URL,
    loss_server_url = _LOSS_SERVER_URL,
)

# %%
import os
print(os.getcwd())
os.chdir("..")
print(os.getcwd())

# %%

project_store = FirestoreProjectStore(
    user_id="marcantonio-galuppi",
    inference=inference,
)
# %%

project_store.create_new_project(
    project_id="test_project1",
    da2item=da2item,
    title="Title 1",
    description="Description 1",
)

# %%
