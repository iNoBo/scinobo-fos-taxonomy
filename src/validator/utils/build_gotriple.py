"""
This script is responsible for building the GoTriple dataset from the raw data.
The raw data reside under the folder: data/misc/gotriple and contain a CSV file and a JSON lines file, containing the Hierarchy.
These files are used to build the GoTriple dataset, which is a hierarchy of SSH FoS. We are going to reconstruct the hierarchy
and try to identify similar FoS in our own ontology. This will help improve the quality of the ontology and the validation process for the SSH FoS.
We are going to only use the json file and for each entry we will try to retrieve the most similar FoS in our ontology.
"""

import json
import os
import argparse
import httpx

from dotenv import load_dotenv
from tqdm import tqdm
from config import set_langfuse


# env variables
load_dotenv("./data/validation_envs.env", verbose=True) # this is not commited to the repo
METADATA_MAPPER_URL = os.getenv("METADATA_MAPPER_URL")
FOS_TAXONOMY_PATH = os.getenv("FOS_TAXONOMY_PATH")
LANGFUSE_PUBLIC_KEY= os.environ["LANGFUSE_PUBLIC_KEY"]
LANGFUSE_SECRET_KEY= os.environ["LANGFUSE_SECRET_KEY"]
LANGFUSE_HOST = os.environ["LANGFUSE_HOST"]


def parse_args():
    parser = argparse.ArgumentParser(description='Build GoTriple dataset')
    parser.add_argument('--input', type=str, default='data/misc/gotriple', help='Path to the input folder')
    parser.add_argument('--output', type=str, default='data/misc/gotriple', help='Path to the output folder')
    return parser.parse_args()


# init mapper client
def init_mapper():
    headers = {
    "Content-Type": "application/json"
    }
    mapper = httpx.Client(
        base_url=METADATA_MAPPER_URL,
        headers=headers,
        timeout=180,
    )
    return mapper


def search_mapper(my_mapper, fos_name):
    search_res = my_mapper.post(
        "/search/fos_taxonomy",
        json={
            "id": "placeholder",
            "text": fos_name,
            "k": 10,
            "approach": "cosine",
            "rerank": True
        },
        params={
            "index": "fos_taxonomy_labels_02_embed"
        }
    )
    if search_res.status_code != 200:
        # an error occured
        return []
    search_res = search_res.json()
    return search_res


def save_dataset(langfuse_instance, dataset, dataset_name, dataset_description=""):
    # Store generated dataset to langfuse for monitoring.   
    langfuse_instance.create_dataset(
        name=dataset_name,
        description=dataset_description
    )
    for item in dataset:
        langfuse_instance.create_dataset_item(
            dataset_name=dataset_name,
            input=item["label"],
            expected_output=item["retrieved_fos"],
            metadata= {
                "id": f'{item["id"]}-{item["retrieved_fos"]}',
                "pref_label": item["pref_label"],
                "alt_label": item["alt_label"],
                "exact_match": item["exact_match"],
                "close_match": item["close_match"],
                "broader": item["broader"],
                "narrower": item["narrower"],
                "retrieved_fos": item["retrieved_fos"],
                "retrieved_fos_level": item["retrieved_fos_level"],
                "reranker_score": item["reranker_score"]
            }
        )


def main():
    # parse arguments
    args = parse_args()
    input_folder = args.input
    output_folder = args.output
    os.makedirs(output_folder, exist_ok=True)
    ssh_json_file = os.path.join(input_folder, 'SSH-LCSH.json')
    # set up langfuse
    langfuse = set_langfuse()
    # load the data
    with open(ssh_json_file) as f:
        ssh_json = json.load(f)
    # init the mapper
    mapper = init_mapper()
    # dataset
    dataset = []
    # iterate over the json file
    for entry in tqdm(ssh_json, desc='Processing GoTriple'):
        # get the preferred label
        pref_label = [
            i['@value'] for i in entry["http://www.w3.org/2004/02/skos/core#prefLabel"] if i["@language"] == "en"
        ] if "http://www.w3.org/2004/02/skos/core#prefLabel" in entry else [i['@value'] for i in entry['http://purl.org/dc/elements/1.1/subject'] if i["@language"] == "en"]
        # search in alt labels if they exist
        alt_label = [
            i['@value'] for i in entry["http://www.w3.org/2004/02/skos/core#altLabel"] if i["@language"] == "en"
            ] if "http://www.w3.org/2004/02/skos/core#altLabel" in entry else []
        if not pref_label:
            my_label = alt_label[0] if alt_label else None
        else:
            my_label = pref_label[0]
        # search the mapper
        search_res = search_mapper(mapper, my_label)
        if not search_res:
            continue
        # unpack the search results
        for res in search_res["retrieved_results"]:
            doc = {
                "label": my_label,
                "id": entry["@id"],
                "pref_label": pref_label,
                "alt_label": alt_label,
                "exact_match": entry["http://www.w3.org/2004/02/skos/core#exactMatch"] if "http://www.w3.org/2004/02/skos/core#exactMatch" in entry else [],
                "close_match": entry["http://www.w3.org/2004/02/skos/core#closeMatch"] if "http://www.w3.org/2004/02/skos/core#closeMatch" in entry else [],
                "broader": entry["http://www.w3.org/2004/02/skos/core#broader"] if "http://www.w3.org/2004/02/skos/core#broader" in entry else [],
                "narrower": entry["http://www.w3.org/2004/02/skos/core#narrower"] if "http://www.w3.org/2004/02/skos/core#narrower" in entry else [],
                "retrieved_fos": res["fos_label"],
                "retrieved_fos_level": res["level"],
                "reranker_score": res["reranker_score"]
            }
            dataset.append(doc)
    save_dataset(
        langfuse_instance=langfuse,
        dataset=dataset,
        dataset_name="GoTriple-SciNoBo",
        dataset_description="GoTriple dataset along with retrieved SciNoBo FoS based on cosine similarity and reranker score."  
    )


if __name__ == '__main__':
    main()