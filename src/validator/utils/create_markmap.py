"""
This script is used to create a markmap from a given taxonomy file and initial level 1 fos.
To create the markmap (mindmap) all we have to do is create a correctly formatted markdown file.
Then we can add it here: https://markmap.js.org/repl to create the mindmap.

For our own scinobo fos taxonomy, the format of the markdown file is:
---
title: scinobo-fos-taxonomy
markmap:
  colorFreezeLevel: 2
---
## <a specific level 1 fos>

- <a specific level 2 fos under the level 1 fos>
    - <a specific level 3 fos under the level 2 fos>
        - <a specific level 4 fos under the level 3 fos>
            - <a specific level 5 fos under the level 4 fos>

- <a specific level 2 fos under the level 1 fos>
    - <a specific level 3 fos under the level 2 fos>
        - <a specific level 4 fos under the level 3 fos>
            - <a specific level 5 fos under the level 4 fos>

....        
"""


import json
import argparse
import os
from tqdm import tqdm

# env variables
FOS_TAXONOMY_PATH = os.getenv("FOS_TAXONOMY_PATH")
GOTRIPLE_TAXONOMY_PATH = os.getenv("GOTRIPLE_TAXONOMY_PATH")


def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--opath",
        type=str,
        required=True,
        help="Path to the dir to save the search results",
    )
    parser.add_argument(
        "--fos",
        type=str,
        nargs='+',
        help="The FOS to process",
        default=None # if None, all level 1 fos will be processed
    )
    parser.add_argument(
        "--filename",
        type=str,
        required=True,
        help="The filename to save the search results",
    )
    parser.add_argument(
        "--taxonomy_type",
        type=str,
        required=True,
        help="The taxonomy type to use"
    )
    args = parser.parse_args()
    return args
    ##############################################


def get_fos_labels_hierarchy(fos_taxonomy_data):
    """
    Get the Field of Study (FoS) names hierarchy in the form of nested dictionaries.
    """
    hierarchy = {}
    for d in fos_taxonomy_data:
        l1 = d["level_1"]
        l2 = d["level_2"]
        l3 = d["level_3"]
        l4 = d["level_4"]
        l5_name = d["level_5_name"] 
        l5_topics = d["level_5"]      
        if l1 not in hierarchy:
            hierarchy[l1] = {}
        if l2 not in hierarchy[l1]:
            hierarchy[l1][l2] = {}
        if l3 != 'N/A':
            if l3 not in hierarchy[l1][l2]:
                hierarchy[l1][l2][l3] = {}
        if l4 != 'N/A':
            if l4 not in hierarchy[l1][l2][l3]:
                hierarchy[l1][l2][l3][l4] = {}
        if l5_name != 'N/A':
            if l5_name not in hierarchy[l1][l2][l3][l4]:
                hierarchy[l1][l2][l3][l4][l5_name] = {       
                    "l5_topics": [topic.strip() for topic in l5_topics.split("----")]
                }
    return hierarchy


def create_markmap_scinobo(opath, fos, filename):
    # load fos taxonomy
    with open(FOS_TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    # create a taxonomy dict to be used for the markmap
    taxonomy2write = get_fos_labels_hierarchy(taxonomy)
    # create the formatted markdown file
    with open(os.path.join(opath, filename), "w") as f:
        f.write("---\n")
        f.write("title: scinobo-fos-taxonomy\n")
        f.write("markmap:\n")
        f.write("  colorFreezeLevel: 2\n")
        f.write("  initialExpandLevel: 1\n")
        f.write("---")
        f.write("\n")
        f.write("\n")
        for level1_fos in taxonomy2write:
            if fos is not None and level1_fos not in fos:
                continue
            f.write(f"## {level1_fos}\n\n")
            for level2_fos in taxonomy2write[level1_fos].keys():
                f.write(f"- {level2_fos}\n")
                for level3_fos in taxonomy2write[level1_fos][level2_fos].keys():
                    f.write(f"    - {level3_fos}\n")
                    for level4_fos in taxonomy2write[level1_fos][level2_fos][level3_fos].keys():
                        f.write(f"        - {level4_fos}\n")
                        for level5_fos in taxonomy2write[level1_fos][level2_fos][level3_fos][level4_fos]:
                            f.write(f"            - {level5_fos}\n")
            f.write("\n")


def get_gotriple_label(entry):
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
    return my_label


def get_hierarchy(item, iddict):
    children = []
    for child in item.get("http://www.w3.org/2004/02/skos/core#narrower", []):
        child_id = child["@id"]
        if child_id in iddict:
            children.append(iddict[child_id])
    return children


# create a recursive function to get the hierarchy under the current item
def recursive_get_children(item, iddict):
    children = get_hierarchy(item, iddict)
    if not children:
        return {}
    result = {}
    for child in children:
        child_name = get_gotriple_label(child)
        result[f"{child_name}---{child['@id']}"] = recursive_get_children(child, iddict)
    return result
    
    
def create_markmap_gotriple(opath, fos, filename):    
    # load gotriple taxonomy
    with open(GOTRIPLE_TAXONOMY_PATH, "r") as f:
        taxonomy = json.load(f)
    iddict = {item["@id"]: item for item in taxonomy}
    hierarchy = {}
    for item in tqdm(taxonomy, desc="Flattening hierarchy"):
        name = get_gotriple_label(item)
        if name not in fos:
            continue
        children_hierarchy = recursive_get_children(item, iddict)
        hierarchy[f"{name}---{item['@id']}"] = children_hierarchy
    # create the formatted markdown file based on the above hierarchy dict
    # create the formatted markdown file
    with open(os.path.join(opath, filename), "w") as f:
        f.write("---\n")
        f.write("title: gotriple-taxonomy\n")
        f.write("markmap:\n")
        f.write("  colorFreezeLevel: 2\n")
        f.write("  initialExpandLevel: 1\n")
        f.write("---\n\n")
        # Function to recursively write the hierarchy
        def write_hierarchy(node, level=0):
            indent = "  " * level
            for key, children in node.items():
                # Extract name from the key (remove the ID part)
                name = key.split("---")[0]
                id = key.split("---")[1]
                if level == 0:
                    f.write(f"## [{name}]({id})\n\n")
                else:
                    f.write(f"{indent}- [{name}]({id})\n")
                
                if children:
                    write_hierarchy(children, level + 1)
            if level == 0:
                f.write("\n")
        # Write the hierarchy
        write_hierarchy(hierarchy)


def main():
    # unpack args
    opath = args.opath
    os.makedirs(opath, exist_ok=True)
    filename = args.filename
    fos = args.fos
    taxonomy_type = args.taxonomy_type
    if taxonomy_type == "scinobo":
        create_markmap_scinobo(opath, fos, filename)
    elif taxonomy_type == "gotriple":
        create_markmap_gotriple(opath, fos, filename)
    else:
        raise ValueError(f"Unknown taxonomy type: {taxonomy_type}")
    
    
if __name__ == "__main__":
    args = parse_args()
    main()