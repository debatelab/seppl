"""inference tools and pipelines"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from streamlit_server_state import server_state, server_state_lock

from deepa2 import GenerativeMode

class AbstractInferencePipeline(ABC):
    """Interface vor Inference Pipelines"""

    def generate_with_chain(
        self,
        inputs: Dict[str,str] = None,
        chain: List[str] = None,
        **kwargs
    ) -> Dict[str,str]:
        """
        generates output by iterating over modes in chain
        uses internal _generate()
        """
        #cast modes
        chain: List[GenerativeMode] = [GenerativeMode.from_keys(mode) for mode in chain]
        # TODO check that chain is valid
        #start with input
        data = inputs.copy()
        # iterate over chain
        for mode in chain:
            outputs = self._generate(inputs=data, mode=mode, **kwargs)
            data.update({mode.target:outputs})
        return data

    def generate(self, inputs: Dict[str,str] = None, mode: str = None, **kwargs) -> str:
        """
        generates output
        uses internal _generate()
        """
        mode = GenerativeMode.from_keys(mode)
        # TODO check that input is complete
        return self._generate(inputs=inputs, mode=mode, **kwargs)

    def construct_prompt(self, inputs: Dict[str,str] = None, mode: GenerativeMode = None) -> str:
        """construct_prompt"""
        prompt = f"{mode.target}:"
        for from_key in mode.from_keys:
            prompt += f" {from_key}: {inputs[from_key]}"
        return prompt

    @abstractmethod
    def _generate(self, inputs: Dict[str,str] = None, mode: GenerativeMode = None, **kwargs) -> str:
        """generates output"""

    @abstractmethod
    def loss(self, inputs: Dict[str,str] = None, mode: str = None) -> float:
        """calculates loss"""


class BigModelPipeline(AbstractInferencePipeline):
    """Inference with local model (server state) using BigModelInference"""

    def __init__(
        self,
        model_path: str = None,
        revision: str = None,
        auth_token: str = None,
    ):
        """load and initialize tokenizer and model as server states"""
        self.device: int = -1
        if torch.cuda.is_available():
            self.device = 0
            logging.info("GPUs: %s", torch.cuda.device_count())
            logging.info(
                "GPU 0 can access GPU 1: %s",
                torch.cuda.can_device_access_peer(self.device, 1)
            )
            logging.info(
                "Capability of GPU %s: %s",
                self.device,
                torch.cuda.get_device_capability(device=self.device)
            )

        # load tokenizer
        with server_state_lock["tokenizer"]: # lock for thread-safety
            if "tokenizer" not in server_state:
                tokenizer: AutoTokenizer = None
                # TODO load tokenizer
                # tokenizer = AutoTokenizer.from_pretrained(
                #     model_path,
                #     use_auth_token=auth_token,
                # )
                server_state.tokenizer = tokenizer
        # load model
        with server_state_lock["model"]: # lock for thread-safety
            if "model" not in server_state:
                model: AutoModelForSeq2SeqLM = None
                # TODO load model
                # model = AutoModelForSeq2SeqLM.from_pretrained(
                #     model_path,
                #     revision=revision,
                #     use_auth_token=auth_token,
                #     device_map="auto" if device>-1 else None, ## offloads to cpu if gpu not big enough
                # )
                server_state.model = model
            # initialize server state

    def _generate(self, inputs: Dict[str,str] = None, mode: GenerativeMode = None, **kwargs) -> str:
        """generate text given input text."""
        # construct input text
        input_text = self.construct_prompt(inputs=inputs, mode=mode)

        # tokenize
        with server_state_lock["tokenizer"]: # lock for thread-safety
            if "tokenizer" in server_state:
                input_ids = server_state.tokenizer(input_text, return_tensors="pt")
            else:
                raise ValueError("No tokenizer in server_state while trying to tokenize prompt.")
        # send to device
        input_ids = input_ids.to(self.device)

        # generate
        with server_state_lock["model"]: # lock for thread-safety
            if "model" in server_state:
                outputs = server_state.model.generate(input_ids["input_ids"], **kwargs)
            else:
                raise ValueError("No model in server_state while trying to generate.")

        # decode
        with server_state_lock["tokenizer"]: # lock for thread-safety
            if "tokenizer" in server_state:
                generated_text = server_state.tokenizer.decode(outputs[0].tolist(), skip_special_tokens=True)
            else:
                raise ValueError("No tokenizer in server_state while trying to decode output.")

        return [{"generated_text": generated_text}]


    def loss(self, inputs: Dict[str,str] = None, mode: str = None) -> float:
        """calculate loss given input text and target text."""
        # construct input and target texts
        mode: GenerativeMode = GenerativeMode.from_keys(mode)
        input_text = self.construct_prompt(inputs=inputs, mode=mode)
        target_text = inputs[mode.target]

        # tokenize
        with server_state_lock["tokenizer"]: # lock for thread-safety
            if "tokenizer" in server_state:
                inputs = server_state.tokenizer(input_text, return_tensors="pt")
                labels = server_state.tokenizer(target_text, return_tensors="pt")
            else:
                raise ValueError("No tokenizer in server_state while trying to tokenize input and target.")

        with server_state_lock["model"]: # lock for thread-safety
            if "model" in server_state:
                # move to device depending on device_map
                inputs = inputs.to(server_state.model.hf_device_map["decoder"])
                labels = labels.to(server_state.model.hf_device_map["encoder.final_layer_norm"])

                # forward pass
                with torch.no_grad():
                    outputs = server_state.model(**inputs, labels=labels['input_ids'])
            else:
                raise ValueError("No model in server_state while trying to calculate loss.")

        return float(outputs['loss'])


_INFERENCE_PIPELINES = {
    "BigModelPipeline": BigModelPipeline
}

def inference_factory(pipeline_id: str, **kwargs) -> AbstractInferencePipeline:
    """factory method for constructing inference pipeline"""
    inference = _INFERENCE_PIPELINES[pipeline_id](**kwargs)
    return inference