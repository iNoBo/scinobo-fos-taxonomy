"""
This script is responsible for mapping venue names into their respective URLs.
It makes use of:
- neo4j to get the neighborhood of venues that are of interest along with their abbreviation and fullname.
- searches these abbreviations and fullname using the venue-mapper API that is hosted in our propreitary server.
- saves the venue2url mapping in a json file for further crawling.
"""

import json
import httpx
import os
import argparse

from tqdm import tqdm
from utils.neo4j_utils import init_driver, retrieve_venue_neigh_per_fos
from dotenv import load_dotenv


# env variables
load_dotenv("./data/validation_envs.env", verbose=True) # this is not commited to the repo
METADATA_MAPPER_URL = os.getenv("METADATA_MAPPER_URL")
FOS_TAXONOMY_PATH = os.getenv("FOS_TAXONOMY_PATH")


def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--opath",
        type=str,
        help="Path to save the search results",
    )
    parser.add_argument(
        "--rel",
        type=str,
        help="The rel type to use to get the venues from the neo4j database", 
    )
    parser.add_argument(
        "--level",
        type=str,
        help="Level of the FOS to process"
    )
    parser.add_argument(
        "--level_key",
        type=str,
        help="Level of the FOS to get from the taxonomy"
    )
    args = parser.parse_args()
    return args
    ##############################################
    

# init mapper client
def init_mapper():
    headers = {
    "Content-Type": "application/json"
    }
    mapper = httpx.Client(
        base_url=METADATA_MAPPER_URL,
        headers=headers,
        timeout=120,
    )
    return mapper


def search_mapper(my_mapper, ven_name):
    search_res = my_mapper.post(
        "/search/publication_venues",
        json={
            "id": "placeholder",
            "text": ven_name,
            "k": 10,
            "approach": "cosine",
            "rerank": True
        }
    )
    if search_res.status_code != 200:
        # an error occured
        return []
    search_res = search_res.json()
    if not search_res["retrieved_results"]:
        # no results
        return []
    # filter the results based on the reranker_score
    search_res = [item for item in search_res["retrieved_results"] if item["reranker_score"] >= 0.92 and item['url'] is not None]
    return search_res


def main():
    # parse arguments
    args = parse_args()
    opath = args.opath
    rel = args.rel
    level = args.level
    level_key = args.level_key
    # init neo4j driver
    driver = init_driver()
    # init mapper client
    mapper = init_mapper()
    # load taxonomy
    with open(FOS_TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    # get venues per L3 FoS
    my_ls = list(set([item[level_key] for item in taxonomy if item[level_key] != "N/A"]))
    venues_res = []
    for fos in tqdm(my_ls, desc="Parsing the FoS searching for venues"):
        venue_records = retrieve_venue_neigh_per_fos(
            fos, 
            level=level, 
            rel=rel,
            driver=driver
        )
        # unpack records. Each row will be converted to
        # {fos_name: "", level: "", venue_name: "", weight: "", venue_fullname: ""}
        for record in venue_records:
            # each record is a tuple of 5 elements with the following order:
            # (l3, venue, r, r1, fn)
            if record[4] is None:
                # no fullname
                full_name = None
            else:
                full_name = record[4]._properties["name"]
            # venue is always available
            venue_name = record[1]._properties["name"] # this is the abbreviation
            # r is always available and we can get the weight
            weight = record[2]._properties["weight"]
            # append to the list
            venues_res.append({
                "fos_name": fos,
                "level": level,
                "venue_name": venue_name,
                "weight": weight,
                "venue_fullname": full_name
            })
    # close neo4j driver
    driver.close()
    # aggregate the venues by their abbreviation
    venues_dict = {}
    for venue in venues_res:
        if venue["venue_name"] not in venues_dict:
            venues_dict[venue["venue_name"]] = {
                "fos": venue["fos_name"],
                "level": venue["level"],
                "weight": venue["weight"],
                "fullnames": [venue["venue_fullname"]] if venue["venue_fullname"] is not None else []
            }
        else:
            venues_dict[venue["venue_name"]]["fullnames"].append(venue["venue_fullname"])
    # get the urls using the mapper. 
    # first search for the abbreviation -- get the results with reranker_score >= 0.9
    # each returned record from the mapper also has the following schema:
    # {
    #  "venue_name": "jama cardiol",
    #  "full_name": "jama cardiology",
    #  "venue_id": "b6979ead-e857-4f0c-a910-44f0d6247ba9",
    #  "url": "http://cardiology.jamanetwork.com/journal.aspx",
    #  "score": 1.9073076,
    #  "reranker_score": 0.9984943866729736
    #}
    for ven_abbrev, ven_items in tqdm(venues_dict.items(), desc="Searching in venue mapper"):
        try:
            res = search_mapper(mapper, ven_abbrev)
        except Exception as e:
            print(f"An error occured while searching for {ven_abbrev}")
            print(e)
            res = []
        # check if we have fullnames
        if len(ven_items["fullnames"]) != 0:
            # we also have fullnames. Search for the fullnames as well
            for full_name in ven_items["fullnames"]:
                res += search_mapper(mapper, full_name)
        ven_items["urls"] = res
    # save the results
    with open(opath, "w") as f:
        json.dump(venues_dict, f)
            
    
if __name__ == "__main__":
    main()