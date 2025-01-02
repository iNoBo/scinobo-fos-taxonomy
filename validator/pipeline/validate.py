"""
This script uses the scientific descriptions of the FoS along with the web descriptions to validate the FoS.
In essence we are going to perform two validations. One with the old taxonomy and one with the new taxonomy.
We are going to provide the scientific and web descriptions of a parent FoS and the scientific and web descriptions of the children FoS.
We are going to ask an LLM whether the children FoS are related to the parent and whether are indeed a subcategory of the parent FoS.
The LLM should provide a structured output with the following format:
{
    "related": boolean,
    "related_explanation": string,
    "subcategory": boolean,
    "subcategory_explanation": "string"
}
The results will be ingested to langfuse for further annotation. 
We have already created our prompt in langfuse and we can retrieve it by providing the name and version.
Otherwise we can create a prompt here using langfuse. Example below:
langfuse.create_prompt(
    name="event-planner",
    prompt=
    "Plan an event titled {{Event Name}}. The event will be about: {{Event Description}}. "
    "The event will be held in {{Location}} on {{Date}}. "
    "Consider the following factors: audience, budget, venue, catering options, and entertainment. "
    "Provide a detailed plan including potential vendors and logistics.",
    config={
        "model":"gpt-3.5-turbo-1106",
        "temperature": 0,
    },
    labels=["production"]
);
Furtermore, for this module to work you need to have a langfuse instance running and the following environment variables set:
"LANGFUSE_HOST": "the host of the langfuse instance",
"LANGFUSE_PUBLIC_KEY": "the public key of the langfuse instance",
"LANGFUSE_SECRET_KEY": "the secret key of the langfuse instance",
"HAYSTACK_CONTENT_TRACING_ENABLED": "true"
"""

import json
import os
import argparse

from haystack import Pipeline
from haystack import component
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator
from tqdm import tqdm
from config import (
    FOS_TAXONOMY_PATH,
    OLLAMA_HOST,
    OLLAMA_PORT,
    DATA_PATH,
    set_langfuse
)
# for overriding the OllamaGenerator
from typing import Any, Dict, List, Optional, Union, Callable
from haystack.dataclasses import StreamingChunk


# override the current OllamaGenerator to account for structured outputs
# since haystack does not currently support this
@component
class StructuredOllamaGenerator(OllamaGenerator):
    def __init__(self,
            model: str = "orca-mini",
            url: str = "http://localhost:11434",
            generation_kwargs: Optional[Dict[str, Any]] = None,
            system_prompt: Optional[str] = None,
            template: Optional[str] = None,
            raw: bool = False,
            timeout: int = 120,
            keep_alive: Optional[Union[float, str]] = None,
            streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
            format: Optional[Dict[str, Any]] = None
        ):
        super(StructuredOllamaGenerator, self).__init__(
            model=model,
            url=url,
            generation_kwargs=generation_kwargs,
            system_prompt=system_prompt,
            template=template,
            raw=raw,
            timeout=timeout,
            keep_alive=keep_alive,
            streaming_callback=streaming_callback
        )
        self.format = format
    
    @component.output_types(replies=List[str], meta=List[Dict[str, Any]])
    def run(
        self,
        prompt: str,
        generation_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Runs an Ollama Model on the given prompt.

        :param prompt:
            The prompt to generate a response for.
        :param generation_kwargs:
            Optional arguments to pass to the Ollama generation endpoint, such as temperature,
            top_p, and others. See the available arguments in
            [Ollama docs](https://github.com/jmorganca/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values).
        :returns: A dictionary with the following keys:
            - `replies`: The responses from the model
            - `meta`: The metadata collected during the run
        """
        generation_kwargs = {**self.generation_kwargs, **(generation_kwargs or {})}

        stream = self.streaming_callback is not None

        response = self._client.generate(
            model=self.model, 
            prompt=prompt, 
            stream=stream, 
            keep_alive=self.keep_alive, 
            options=generation_kwargs,
            format=self.format
        )

        if stream:
            chunks: List[StreamingChunk] = self._handle_streaming_response(response)
            return self._convert_to_streaming_response(chunks)

        return self._convert_to_response(response)
 
    
def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ipath-science",
        type=str,
        help="Path of the saved collection that contains the scientific descriptions",
    )
    parser.add_argument(
        "--ipath-web",
        type=str,
        help="Path of the saved collection that contains the web descriptions",
    )
    parser.add_argument(
        "--prompt-version", # if you want to use the production prompt, leave it None
        type=int,
        default=None
    )
    parser.add_argument(
        "--prompt-name",
        type=str,
        default=None
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None
    )
    parser.add_argument(
        "--level",
        type=str,
        nargs="+",
        help="Levels to search in the taxonomy",
    )
    parser.add_argument(
        "--ipath-science-extra",
        type=str,
        help="Path of the saved collection that contains the scientific descriptions. This is used for loading descriptions of other levels.",
        default=None
    )
    parser.add_argument(
        "--ipath-web-extra",
        type=str,
        help="Path of the saved collection that contains the web descriptions. This is used for loading descriptions of other levels.",
        default=None
    )
    parser.add_argument(
        "--tags",
        type=str,
        nargs="+",
        help="Tags that you want to use in the langfuse logging",
        default=["taxonomy-validation"]
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the validation from the last saved state in Langfuse",
        default=False
    )
    args = parser.parse_args()
    return args
    ##############################################
    

def load_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    return data


def log_results(langfuse, llm_res, **kwargs):
    # log the results into langfuse
    # compile the prompt and use it as the input to llm
    input_prompt = kwargs["prompt_template"].compile(
        parent_fos_name=kwargs["parent"],
        parent_fos_scientific=kwargs["parent_scientific"],
        parent_fos_web=kwargs["parent_web"],
        child_fos_name=kwargs["child"],
        child_fos_scientific=kwargs["child_scientific"],
        child_fos_web=kwargs["child_web"]
    )
    trace = langfuse.trace(
        input={
            "input_prompt": input_prompt
        },
        name=f"validate-fos-{kwargs['parent']}-{kwargs['child']}-{kwargs['version']}",
        metadata={
            "taxonomy_version": kwargs["version"],
            "parent": kwargs["parent"],
            "child": kwargs["child"],
            "parent_scientific": kwargs["parent_scientific"],
            "parent_web": kwargs["parent_web"],
            "child_scientific": kwargs["child_scientific"],
            "child_web": kwargs["child_web"]
        },
        session_id=f"taxonomy-validation-{kwargs['version']}",
        user_id=f"taxonomy-validation-{kwargs['version']}",
        version=kwargs["version"],
        tags=kwargs["tags"]
    )
    generation = trace.generation(
        name=f"validate-fos-{kwargs['parent']}-{kwargs['child']}",
        model=llm_res['llm']['meta'][0]['model'],
        input={
            "input_prompt": input_prompt
        },
        output=json.loads(llm_res['llm']['replies'][0]),
        metadata={
            "related": str(json.loads(llm_res['llm']['replies'][0])['related']).lower(), # filtering is based on string values
            "subcategory": str(json.loads(llm_res['llm']['replies'][0])['subcategory']).lower()
        },
        prompt=kwargs["prompt_template"], # link the prompt to the generation
        version=kwargs["version"]
    )
    generation.end()


def transform_dict(sci_dict, web_dict):
    new_dict = {}
    for key, value in sci_dict.items():
        if "publications" not in value or isinstance(value["publications"], list):
            continue
        if value["publications"]["3-shot-label"] not in web_dict:
            continue
        name = value["publications"]["3-shot-label"]
        new_dict[key] = {
            **web_dict[name],
            "name": name
        }
    return new_dict


def get_descriptions(sci_col, web_col, fos):
    scientific, web = sci_col[fos]['description'], web_col[fos]['reply']
    if scientific is None and web is None:
        return None, None
    if scientific is None:
        scientific = "The scientific description is not available. Please refer to the web description."
    else:
        scientific = scientific.split("Summary:")[1].rstrip().lstrip()
    if web is None:
        web = "The web description is not available. Please refer to the scientific description."
    else:
        web = web.split("Answer:")[1].rstrip().lstrip()
    return scientific, web

     
def main():
    # parse arguments
    args = parse_args()
    ipath_science = args.ipath_science
    ipath_web = args.ipath_web
    prompt_version = args.prompt_version
    prompt_name = args.prompt_name
    model_name = args.model_name
    levels = args.level
    tags = args.tags
    resume = args.resume
    # these paths contain the descriptions of the other levels (l3, l4).
    # the file for the l5 descriptions only has the l5 descriptions :p
    # as a result we must load the l4 descriptions as well to perform the validation.
    ipath_science_extra = args.ipath_science_extra
    ipath_web_extra = args.ipath_web_extra
    # assert that the provided levels are two
    assert len(levels) == 2, "The validation module works only with two levels, parent and child"
    # sort the levels, in order to have the parent first
    levels = sorted(levels) # this will work even if they are strings, since the names are level_# where # is an integer.
    # load the collections
    science_collection = load_json(ipath_science)
    web_collection = load_json(ipath_web)
    taxonomy = load_json(FOS_TAXONOMY_PATH)
    if ipath_science_extra is not None and ipath_web_extra is not None:    
        science_collection_extra = load_json(ipath_science_extra)
        web_collection_extra = load_json(ipath_web_extra)
        science_collection = {**science_collection, **science_collection_extra}        
        # convert the web_collection to a similar format as the science_collection -- having l5_ids as keys
        web_collection = {**transform_dict(science_collection, web_collection), **web_collection_extra}
    # get the version of the taxonomy and use it as experiment version in langfuse
    version = FOS_TAXONOMY_PATH.split("/")[1].split("_")[-1].split(".json")[0]
    # re-format the taxonomy for validation
    validation_data = {}
    for item in tqdm(taxonomy, desc="Parsing taxonomy"):
        # since the levels are sorted and only two, we can use the first level as the parent and the second level as the child
        parent, child = item[levels[0]], item[levels[1]]
        if parent == "N/A":
            continue
        if parent in validation_data:
            if child == "N/A":
                continue
            validation_data[parent].add(child)
        else:
            if child == "N/A":
                validation_data[parent] = set()
                continue
            validation_data[parent] = set([child])
    # init langfuse
    langfuse = set_langfuse()
    prompt_template = langfuse.get_prompt(name=prompt_name, version=prompt_version)
    # filter out the validation data based on the resume flag
    if resume:
        # this returns the latest traces based on the tags
        latest_traces = langfuse.fetch_traces(
            limit=50, 
            page=1, 
            user_id=f"taxonomy-validation-{version}",
            tags=tags[0]).data
        if not latest_traces:
            print("No traces found. Continuing with the validation.")
        else:
            parent = latest_traces[0].metadata["parent"]
            # find all the other children of the parent
            processed_children = [item.metadata["child"] for item in latest_traces if item.metadata["parent"] == parent]
            # get the ids of the processed children
            if "level_5" in levels[1]:
                processed_children = [
                    item[levels[1]] for item in taxonomy 
                    if item[levels[0]] == parent and item[f'{"_".join(levels[1].split("_")[:2])}_name'] in processed_children
                ]
            else:
                processed_children = [item[levels[1]] for item in taxonomy if item[levels[0]] == parent and item[levels[1]] in processed_children]
            children = validation_data[parent]
            # the keys in validation_data are always in the same order, find the idx of the parent
            idx = list(validation_data.keys()).index(parent)
            validation_data = {k: v for i, (k, v) in enumerate(validation_data.items()) if i >= idx}
            # remove the processed children
            validation_data[parent] = children - set(processed_children)
    # initialize the components
    llm = StructuredOllamaGenerator(
        model=model_name, 
        url=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}", 
        generation_kwargs={
            "num_ctx": 8192, 
            "temperature": 0.0
        },
        format= {
            "type": "object",
            "properties": {
                "related_explanation": {
                    "type": "string"
                },
                "related": {
                    "type": "boolean"
                },
                "subcategory_explanation": {
                    "type": "string"
                },
                "subcategory": {
                    "type": "boolean"
                },
            },
            "required": [
                "related_explanation",
                "related",
                "subcategory_explanation",
                "subcategory",
            ]
        }
    )
    # get the prompt from langfuse
    prompt_builder = PromptBuilder(template=prompt_template.prompt)
    # create the pipeline
    pipe = Pipeline()
    pipe.add_component(instance=llm, name="llm")
    pipe.add_component(instance=prompt_builder, name="prompt_builder")
    pipe.connect("prompt_builder", "llm")
    pipe.draw(os.path.join(DATA_PATH, "haystack-pipelines", f"taxonomy-validation-pipeline_{levels[0]}_{levels[1]}.png"))
    # validate
    for parent in tqdm(validation_data, desc="Validating FoS"):
        ##############################################
        # for parent
        children = validation_data[parent]
        if parent not in science_collection or parent not in web_collection:
            continue
        if not children:
            continue
        parent_scientific, parent_web = get_descriptions(science_collection, web_collection, parent)
        if parent_scientific is None and parent_web is None:
            continue
        ##############################################
        for child in children:
            if child not in science_collection or child not in web_collection:
                continue
            child_scientific, child_web = get_descriptions(science_collection, web_collection, child)
            if child_scientific is None and child_web is None:
                continue
            if "name" in web_collection[child]:
                child = web_collection[child]["name"]
            ##############################################
            # run the pipeline
            res = pipe.run(
                {
                    "prompt_builder": {
                        "parent_fos_name": parent,
                        "parent_fos_scientific": parent_scientific,
                        "parent_fos_web": parent_web,
                        "child_fos_name": child,
                        "child_fos_scientific": child_scientific,
                        "child_fos_web": child_web
                    }
                }
            )
            # log the results into langfuse
            log_results(
                langfuse=langfuse,
                llm_res=res,
                parent=parent,
                child=child,
                parent_scientific=parent_scientific,
                parent_web=parent_web,
                child_scientific=child_scientific,
                child_web=child_web,
                version=version,
                prompt_template=prompt_template,
                tags=tags
            )
            ##############################################


if __name__ == "__main__":
    main()