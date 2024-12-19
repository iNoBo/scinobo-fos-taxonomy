"""
This script is used to create a description of the FOS (Field of Study) from the FOS collection data.
In the collection we have the top 10 publications based on score for each FOS at Level 3 and 4.
We are going to use Llama3.2 to generate a brief description of each FOS based on the top 10 publications.
"""

import json
import os
import argparse
import distutils.util

from haystack.components.builders.prompt_builder import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack import Pipeline, Document
from haystack.components.classifiers import DocumentLanguageClassifier
from tqdm import tqdm
from config import (
    DATA_PATH,
    FOS_TAXONOMY_PATH,
    OLLAMA_HOST,
    OLLAMA_PORT,
    set_langfuse
)


def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--opath",
        type=str,
        help="Path to save the search results",
    )
    parser.add_argument(
        "--ipath",
        type=str,
        help="Path of the saved collection",
    )
    parser.add_argument(
        "--lang_detect",
        type=lambda x:bool(distutils.util.strtobool(x)),
        help="Path of the saved collection",
    )
    parser.add_argument(
        "--level",
        type=str,
        help="Level of the FOS to process"
    )
    parser.add_argument(
        "--prompt_name",
        type=str,
        help="Name of the prompt to use"
    )
    args = parser.parse_args()
    return args
    ##############################################


def process_docs(docs):
    my_docs = []
    for doc in docs:
        title = doc["title"] 
        abstract = doc["paperAbstract"]
        my_text = title if title is not None else " " + " " + abstract if abstract is not None else " "
        my_text = my_text.rstrip().lstrip()
        my_docs.append(Document(content=my_text))
    return my_docs


def main():
    # parse arguments
    args = parse_args()
    opath = args.opath
    ipath = args.ipath
    level = args.level
    lang_detect = args.lang_detect
    prompt_name = args.prompt_name
    # init langfuse
    langfuse = set_langfuse()
    # load the taxonomy
    with open(FOS_TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    taxonomy_dict = {item['level_5_id']: item for item in taxonomy}
    # load the collection
    with open(ipath, "r") as f:
        collection = json.load(f)
    # build the pipeline
    lang_classifier = DocumentLanguageClassifier(languages=["en"])
    llm = OllamaGenerator(
        model="llama3.2:3b", 
        url=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}", 
        generation_kwargs={"num_ctx": 8192, "temperature": 0.0}
    )
    # get the specified prompt from langfuse
    prompt_template = langfuse.get_prompt(prompt_name)
    prompt_builder = PromptBuilder(template=prompt_template.prompt)
    pipe = Pipeline()
    # init components
    # pipe.add_component(instance=lang_classifier, name="language_classifier")
    # pipe.add_component(instance=doc_processor, name="doc_processor")
    pipe.add_component(instance=llm, name="llm")
    pipe.add_component(instance=prompt_builder, name="prompt_builder")
    # connect components
    pipe.connect("prompt_builder", "llm")
    pipe.draw(os.path.join(DATA_PATH, "haystack-pipelines", "publication-description-pipeline.png"))
    # run the pipeline
    for fos in tqdm(collection, desc="Processing FOS"):
        if level != "level_5":
            publications = collection[fos]
            query = fos
            my_docs = process_docs(publications)
        else:
            # this requires a different approach to processing
            # since we can have identical level_5 names under different level_4 names with different publications
            # when processing this collection some level_5 were excluded from the taxonomy
            # here we can also use the topic description of the level_5 for providing some information to the LLM
            if fos not in taxonomy_dict:
                # delete the entry from the collection; no need to have it
                del collection[fos]
                continue
            query = taxonomy_dict[fos]["level_5_name"]
            my_docs = [Document(content=doc[1].lower().rstrip().lstrip()) for doc in collection[fos]['representative_docs'] if doc]
            topic_description = collection[fos]['l5_topic_description']
            publications = collection[fos]
        # detect the language of the documents
        if lang_detect:
            lang_res = lang_classifier.run(documents=my_docs)
            # keep only the English documents
            my_docs = [doc for doc in lang_res['documents'] if doc.meta["language"] == "en"]
        if len(my_docs) == 0:
            collection[fos] = {
                "description": None,
                "publications": publications
            }
            continue
        results = pipe.run(
            {"prompt_builder": {"query": query, "publications": my_docs}}
        ) if level != "level_5" else pipe.run(
            {"prompt_builder": {"query": query, "publications": my_docs, "topic_description": topic_description}}
        )
        description = results['llm']['replies'][0]
        collection[fos] = {
            "description": description,
            "publications": publications # this key name is ambiguous, maybe it should be changed.
        }
    # save the results
    with open(opath, "w") as f:
        json.dump(collection, f, indent=2)


if __name__ == "__main__":
    main()