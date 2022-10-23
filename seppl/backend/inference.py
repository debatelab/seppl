"""inference tools and pipelines"""

from __future__ import annotations
from abc import ABC, abstractmethod
import functools
import logging
import json
import re
from typing import Optional, Dict, List, Tuple, Any, Union

from deepa2 import GenerativeMode
from deepa2.parsers import ArgdownParser
import requests  # type: ignore

class InferenceRater:
    """object for rating inference results (generation)"""

    def __init__(
        self,
        inputs: Dict[str,str] = None,
        mode: GenerativeMode = None,
        generated_text: str = None,
        **kwargs
    ):
        self.inputs = inputs
        self.mode = mode
        self.generated_text = generated_text
        self.parameters = kwargs        

    def rate_and_submit(self, rating: Any):
        """receive and submit user inference rating"""
        # TODO: implement
        raise NotImplementedError


class AbstractInferencePipeline(ABC):
    """Interface vor Inference Pipelines"""

    def generate_with_chain(
        self,
        inputs: Dict[str,str],
        chain: List[str],
        **kwargs
    ) -> Dict[str,str]:
        """
        generates output by iterating over modes in chain
        uses internal _generate()
        """        
        #cast modes
        chain_gm: List[GenerativeMode] = [GenerativeMode.from_keys(mode) for mode in chain]
        # TODO check that chain is valid
        #start with input
        data = inputs.copy()
        # iterate over chain
        for mode in chain_gm:
            outputs = self._generate(inputs=data, mode=mode, **kwargs)
            if "generated_text" in outputs[0]:
                generated_text = outputs[0]["generated_text"]
                data.update({mode.target:generated_text})
            else:
                logging.warning("generation failed in chain %s at step %s", chain_gm, mode)
                return {"error": f"generation failed in step {mode}"}
        return data

    def generate(
        self,
        inputs: Dict[str,str],
        mode: Union[str, GenerativeMode],
        **kwargs
    ) -> Tuple[List[Dict[str,str]], Optional[InferenceRater]]:
        """
        generates output
        uses internal _generate()
        returns:
        - [{"generated_text": ...}, {"generated_text": ...}, ...]
        - InferenceRater object to elicit quality rating by user
        """
        if not isinstance(mode, GenerativeMode):
            mode = GenerativeMode.from_keys(mode)
        # TODO check that input is complete
        inference_rater = None
        outputs = self._generate(inputs=inputs, mode=mode, **kwargs)
        if "generated_text" in outputs[0]:
            inference_rater = InferenceRater(
                inputs=inputs,
                mode=mode,
                generated_text=outputs[0]["generated_text"],
                **kwargs
            )
        return outputs, inference_rater

    def construct_prompt(self, inputs: Dict[str,str], mode: GenerativeMode) -> str:
        """construct_prompt"""
        prompt = f"{mode.target}:"
        for input_key in mode.input:
            prompt += f" {input_key}: {inputs[input_key]}"
        return prompt

    def preprocess_inputs(self, inputs: Dict[str,str]) -> Dict[str,str]:
        """preprocess inputs by removing line breaks"""
        inputs = {
            key: (value.replace("\n", " ") if value is not None else value)
            for key, value in inputs.items() 
        }
        return inputs

    @staticmethod
    def postprocess_argdown(argdown_reconstrcution:str) -> str:
        """
        postprocesses argdown reconstruction:
        * inserts line breaks
        """

        def newlines_between_propositions(propositions: str) -> str:
            """inserts line breaks between propositions"""
            formatted_propositions = ""
            # match labels
            regex = r" \(([0-9]*)\) "
            matches = re.finditer(regex, propositions, re.MULTILINE)
            pointer = 0
            # iterate over matched labels
            for match in matches:
                formatted_propositions += propositions[pointer:match.start()]
                formatted_propositions += "\n" # add new line
                formatted_propositions += propositions[match.start()+1:match.end()]
                pointer = match.end()
            formatted_propositions += propositions[pointer:]
            return formatted_propositions

        # find all inferences
        matches = re.finditer(
            ArgdownParser.INFERENCE_PATTERN_REGEX,
            argdown_reconstrcution,
            re.MULTILINE
        )

        pointer = 0
        formatted_argdown = ""
        # iterate over inferences
        for match in matches:
            formatted_argdown += newlines_between_propositions(
                argdown_reconstrcution[pointer : match.start()]
            )
            # add new line before inference
            formatted_argdown += "\n"
            # add inference (except beginning and trailing whitespace char)
            formatted_argdown += argdown_reconstrcution[match.start()+1 : match.end()-1]
            # add new line after inference
            formatted_argdown += "\n"
            pointer = match.end()
        formatted_argdown += newlines_between_propositions(
            argdown_reconstrcution[pointer:]
        )
        return formatted_argdown


    @abstractmethod
    def _generate(self, inputs: Dict[str,str], mode: GenerativeMode, **kwargs) -> List[Dict[str,str]]:
        """generates output"""

    @abstractmethod
    def loss(self, inputs: Dict[str,str], mode: str) -> Optional[float]:
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


    def _generate(self, inputs: Dict[str,str], mode: GenerativeMode, **kwargs) -> List[Dict[str,str]]:
        """generates output"""
        # preprocess inputs
        inputs = self.preprocess_inputs(inputs)
        # construct input text
        input_text = self.construct_prompt(inputs=inputs, mode=mode)
        # pack payload
        payload = {
            "input": input_text,
            "parameters": kwargs,
        }
        data = json.dumps(payload)
        result_json = self._query_server(
            server_url=self.textgen_server_url,
            data=data,
        )
        if not result_json:
            return [{"error": "generation failed, no result"}]
        return [result_json]

    def loss(self, inputs: Dict[str,str], mode: str) -> Optional[float]:
        """calculate loss"""
        # preprocess inputs
        inputs = self.preprocess_inputs(inputs)
        # construct input and target texts
        logging.info("Calculating loss for plain mode: %s", mode)
        mode_gm: GenerativeMode = GenerativeMode.from_keys(mode)
        logging.info(f"Parsed mode: input={mode_gm.input} and target={mode_gm.target}.")
        input_text = self.construct_prompt(inputs=inputs, mode=mode_gm)
        target_text = inputs[mode_gm.target]

        # pack payload
        payload = {
            "input": input_text,
            "target": target_text,
            "parameters": {},
        }
        data = json.dumps(payload)
        result_json = self._query_server(
            server_url=self.loss_server_url,
            data=data,
        )
        if not result_json:
            return None
        if not "loss" in result_json:
            return None

        return float(result_json["loss"])


    @functools.lru_cache(maxsize=128)
    def _query_server(self, server_url: str, data: str) -> Dict[Any, Any]:
        """query server"""
        # send http request
        logging.info("Sending http request: %s", data)
        response = requests.request(
            "POST",
            server_url,
            headers=self.headers,
            data=data,
            timeout=self.timeout,
        )
        # decode and unpack response
        content = response.content.decode("utf-8")
        logging.info("Received response: %s", content)
        try:
            # as json
            result_json = json.loads(content)
        except Exception:
            result_json = {"error": content}

        return result_json


_INFERENCE_PIPELINES = {
    "DA2MosecPipeline": DA2MosecPipeline
}

def inference_factory(pipeline_id: str, **kwargs) -> AbstractInferencePipeline:
    """factory method for constructing inference pipeline"""
    inference = _INFERENCE_PIPELINES[pipeline_id](**kwargs)
    return inference