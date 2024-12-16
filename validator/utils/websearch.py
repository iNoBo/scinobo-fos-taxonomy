"""

This util script loads the FoS taxonomy. The FoS taxonomy has levels from L1-L6.
We want to search the web for the concepts at L3 and L4. The result will be used as a description 
for each concept and will be saved in the data folder. 
The scripts receive a list with the level to search and the path to save the results. 
Each web result, returns multiple documents. We will make use of an LLM to summarize the documents and provide an overall description for each concept.
The LLM is Llama3.2-3b and is already served in an ollama server. To recreate the script, you need to have ollama installed and running,
pull the LLM of your choice and provide the API information as env variables to the config file.
"""

import json
import os
import argparse

from duckduckgo_api_haystack import DuckduckgoApiWebSearch
from haystack.components.websearch import SerperDevWebSearch
from haystack.utils import Secret
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack import Pipeline
from tqdm import tqdm
from config import (
    DATA_PATH,
    FOS_TAXONOMY_PATH,
    OLLAMA_HOST,
    OLLAMA_PORT,
    SERPERDEV_API_KEY
)


prompt_template = """
Answer the following query given the documents.
Your answer must have a scientific direction based on the documents and the query.
Do not provide personal opinions or beliefs.
Only provide the answer, nothing else.
Your answer must start with the word "Answer:".

Documents:
{% for document in documents %}
  {{document.content}}
{% endfor %}

Query: {{query}}
"""


def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--level",
        type=str,
        nargs="+",
        help="Levels to search in the taxonomy",
    )
    parser.add_argument(
        "--opath",
        type=str,
        help="Path to save the search results",
    )
    parser.add_argument(
        "--nresults",
        type=int,
        default=5,
        help="Number of results to web search"
    )
    parser.add_argument(
        "--websearch",
        type=str,
        default="duckduckgo",
        help="Web search engine to use"
    )
    args = parser.parse_args()
    return args
    ##############################################
    

def main():
    # Parse arguments
    args = parse_args()
    levels = args.level
    opath = args.opath
    nresults = args.nresults
    websearch_eng = args.websearch
    # load the taxonomy
    with open(FOS_TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    # retrieve the unique FoS concepts at the specified levels
    concepts = dict()
    for item in tqdm(taxonomy, desc="Parsing taxonomy"):
        for level in levels:
            if level in item:
                if item[level] == "" or item[level] is None or item[level] == "N/A":
                    continue
                if level in concepts:
                    concepts[level].add(item[level])
                else:
                    concepts[level] = {item[level]}
    # init the web search
    if websearch_eng == "duckduckgo":
        websearch = DuckduckgoApiWebSearch(top_k=nresults, max_search_frequency=10, max_results=6, backend="lite")
    else:
        # use SerperDevWebSearch. It provides 2500 free queries, enough for the task
        if SERPERDEV_API_KEY is None:
            raise ValueError("Please provide the SERPERDEV_API_KEY env variable")
        websearch = SerperDevWebSearch(api_key=Secret.from_token(SERPERDEV_API_KEY), top_k=nresults)
    # init the haystack pipeline
    pipe = Pipeline()
    pipe.add_component(name="prompt_builder", instance=PromptBuilder(template=prompt_template))
    pipe.add_component(
        name="llm", 
        instance=OllamaGenerator(
            model="llama3.2:3b", 
            url=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}", 
            generation_kwargs={"num_ctx": 8192, "temperature": 0.0}
        )
    )
    pipe.add_component(name="websearch", instance=websearch)
    # connect the components
    pipe.connect("websearch", "prompt_builder")
    pipe.connect("prompt_builder", "llm")
    pipe.draw(os.path.join(DATA_PATH, "websearch-pipeline.png"))
    # parse the concepts
    # check if we have a checkpoint
    if os.path.exists(opath):
        with open(opath, "r") as f:
            results = json.load(f)
    else:
        results = dict()
    for level in levels:
        for concept in tqdm(concepts[level], desc=f"Searching for concepts at level {level}"):
            if concept in results:
                continue
            query = f"What is {concept}?"
            try:
                result = pipe.run({"websearch": {"query": query}, "prompt_builder": {"query": query}})
            except Exception as e:
                print(f"Failed to search for {concept} at level {level}, error: {e}")
                # the websearch functionallity of haystack either fails with timeout or for other errors.
                # the error response is never informative. We will checkpoint the results here.
                with open(opath, "w") as f:
                    json.dump(results, f, indent=4)
                exit(1)
            # unpack results
            links = result["websearch"]["links"]
            reply = result["llm"]["replies"][0]
            llm_meta = result["llm"]["meta"]
            # save the results
            results[concept] = {
                "query": query,
                "links": links,
                "reply": reply,
                "llm_meta": llm_meta,
                "level": level
            }
    # save the results
    with open(opath, "w") as f:
        json.dump(results, f, indent=4)
    

if __name__ == "__main__":
    main()
