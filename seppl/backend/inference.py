"""inference tools and pipelines"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import json
from typing import Optional, Dict, List

from deepa2 import GenerativeMode
import requests

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
        for input_key in mode.input:
            prompt += f" {input_key}: {inputs[input_key]}"
        return prompt

    @abstractmethod
    def _generate(self, inputs: Dict[str,str] = None, mode: GenerativeMode = None, **kwargs) -> str:
        """generates output"""

    @abstractmethod
    def loss(self, inputs: Dict[str,str] = None, mode: str = None) -> float:
        """calculates loss"""


class DA2MosecPipeline(AbstractInferencePipeline):  # pylint: disable=too-few-public-methods
    """
    Simple Pipeline for using DA2Mosec da2 inference server.
    """

    textgen_server_url: str
    loss_server_url: str
    headers: dict
    timeout: int

    def __init__(
        self,
        textgen_server_url: str,
        loss_server_url: str,
        timeout: int = 120,
    ):
        """initialize the pipeline"""
        self.textgen_server_url = textgen_server_url
        self.loss_server_url = loss_server_url
        self.headers = {}
        self.timeout = timeout


    def _generate(self, inputs: Dict[str,str] = None, mode: GenerativeMode = None, **kwargs) -> str:
        """generates output"""
        # construct input text
        input_text = self.construct_prompt(inputs=inputs, mode=mode)
        # pack payload
        payload = {
            "input": input_text,
            "parameters": kwargs,
        }
        data = json.dumps(payload)
        # send http request
        logging.debug("Sending http request: %s", data)
        response = requests.request(
            "POST",
            self.textgen_server_url,
            headers=self.headers,
            data=data,
            timeout=self.timeout,
        )
        # decode and unpack response
        content = response.content.decode("utf-8")
        logging.debug("Received response: %s", content)
        try:
            # as json
            result_json = json.loads(content)
        except Exception:
            result_json = {"error": content}

        return [result_json]

    def loss(self, inputs: Dict[str,str] = None, mode: str = None) -> Optional[float]:
        """calculate loss"""
        # construct input and target texts
        mode: GenerativeMode = GenerativeMode.from_keys(mode)
        input_text = self.construct_prompt(inputs=inputs, mode=mode)
        target_text = inputs[mode.target]
        # pack payload
        payload = {
            "input": input_text,
            "target": target_text,
            "parameters": {},
        }
        data = json.dumps(payload)
        # send http request
        logging.debug("Sending http request: %s", data)
        response = requests.request(
            "POST",
            self.loss_server_url,
            headers=self.headers,
            data=data,
            timeout=self.timeout,
        )
        # decode and unpack response
        content = response.content.decode("utf-8")
        logging.debug("Received response: %s", content)
        try:
            # as json
            result_json = json.loads(content)
        except Exception:
            result_json = {"error": content}

        return float(result_json.get("loss"))



_INFERENCE_PIPELINES = {
    "DA2MosecPipeline": DA2MosecPipeline
}

def inference_factory(pipeline_id: str, **kwargs) -> AbstractInferencePipeline:
    """factory method for constructing inference pipeline"""
    inference = _INFERENCE_PIPELINES[pipeline_id](**kwargs)
    return inference