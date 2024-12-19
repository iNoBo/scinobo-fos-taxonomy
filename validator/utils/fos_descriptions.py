"""
This script is used to create a description of the FOS (Field of Study) from the FOS collection data.
In the collection we have the top 10 publications based on score for each FOS at Level 3 and 4.
We are going to use Llama3.2 to generate a brief description of each FOS based on the top 10 publications.
"""

import json
import os
import argparse

from haystack.components.builders.prompt_builder import PromptBuilder
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack import Pipeline, Document
from haystack import component
from haystack.components.classifiers import DocumentLanguageClassifier
from tqdm import tqdm
from config import (
    DATA_PATH,
    FOS_TAXONOMY_PATH,
    OLLAMA_HOST,
    OLLAMA_PORT
)


prompt_template = """
Summarize the following query using information from the provided publications.
Do not mention, quote or cite any of the publications, simply use them as information.
Do not mention the query in the summary. Just provide your summary.
The summary must be also be generalized based on the information contained in the publications and maintain a scientific focus.
Avoid personal opinions or beliefs.
Provide only the summary, and nothing else.
Begin your response with the word "Summary:".

Publications:
{% for publication in publications %}
  {{publication.content}}
{% endfor %}

Query: {{query}}
"""


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
    args = parser.parse_args()
    return args
    ##############################################


def main():
    # parse arguments
    args = parse_args()
    opath = args.opath
    ipath = args.ipath
    # load the taxonomy
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
    prompt_builder = PromptBuilder(template=prompt_template)
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
        publications = collection[fos]
        query = fos
        my_docs = []
        for doc in publications:
            title = doc["title"] 
            abstract = doc["paperAbstract"]
            my_text = title if title is not None else " " + " " + abstract if abstract is not None else " "
            my_text = my_text.rstrip().lstrip()
            my_docs.append(Document(content=my_text))
        lang_res = lang_classifier.run(documents=my_docs)
        # keep only the English documents
        my_docs = [doc for doc in lang_res['documents'] if doc.meta["language"] == "en"]
        if len(my_docs) == 0:
            collection[fos] = {
                "description": None,
                "publications": publications
            }
            continue
        results = pipe.run({"prompt_builder": {"query": query, "publications": my_docs}})
        description = results['llm']['replies'][0]
        collection[fos] = {
            "description": description,
            "publications": publications
        }
    # save the results
    with open(opath, "w") as f:
        json.dump(collection, f, indent=2)


if __name__ == "__main__":
    main()