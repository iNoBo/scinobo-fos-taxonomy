"""
This python file contains the functions to interact with a Neo4j database. 
Specifically to interact with the taxonomy-neo4j and the venue-graph-neo4j.
This script will contain functions to insert data into the Neo4j database,
to connect to a database and to query the database.

NOTE: We have installed the community edition of neo4j in our local server. This edition only supports one database.
To resolve this you must deploy two seperate containers of neo4j published in different ports, with different data volumes and container names.
"""

import os
import json

from config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    DATA_PATH,
    FOS_TAXONOMY_PATH
)
from neo4j import GraphDatabase
from utils.multigraph import MultiGraph
from utils.venue_parser import VenueParser


def init_driver():
    # NOTE: the main python module working with the neo4j instance is responsible for closing the driver and the session.
    if NEO4J_URI is None or NEO4J_USER is None or NEO4J_PASSWORD is None:
        raise RuntimeError("Neo4j env variables are not set")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("Neo4j driver initialized")
    return driver


def create_nodes_csv(my_graph, my_taxonomy):
    """
    This function creates a csv file with the nodes of the graph. The CSV must have the following format:
    **nodes.csv**
    ```
    id,name,roles
    1,Venue A,venue
    2,Venue B,venue
    3,Field L1,L1
    4,Venue C,venue:L3:is_L6
    5,Venue D,venue:L3
    ...
    """
    # based on the taxonomy create two dicts: L4_ID -> L4_name and L5_ID -> L5_name
    L4_dict = {item["level_4_id"]: item["level_4"] for item in my_taxonomy}
    L5_dict = {item["level_5_id"]: item["level_5_name"] for item in my_taxonomy}
    nodes = my_graph.nodes(data=True)
    node_dict = {node[0]: idx for idx, node in enumerate(nodes, start=1)}
    with open(os.path.join(DATA_PATH, "neo4j-imports", "nodes.csv"), "w") as f:
        f.write("id|name|L4_name|L5_name|roles\n")
        for idx, node in enumerate(nodes, start=1):
            # check if the node is a L4 or L5 so that we can get the ID and the name
            f.write(f"{idx}|{node[0]}|{L4_dict.get(node[0], '-')}|{L5_dict.get(node[0], '-')}|{':'.join(node[1])}\n")
    print("Nodes CSV created")
    return node_dict


def create_fullnames_csv(abbrev_dict, node_dict):
    """
    This function creates a csv file with the full names of the venues. The CSV must have the following format:
    **fullnames.csv**
    ```
    abbreviation,full_name
    VA,Venue Alpha
    VA,Venue Arena
    VB,Venue Beta
    VC,Venue Center
    ...
    """
    my_list = []
    for full_name, abbrev in abbrev_dict.items():
        if abbrev not in node_dict:
            continue
        my_list.append((node_dict[abbrev], full_name))
    # sort the list by the node id
    my_list.sort(key=lambda x: x[0])
    with open(os.path.join(DATA_PATH, "neo4j-imports", "fullnames.csv"), "w") as f:
        f.write("id|full_name\n")
        for item in my_list:
            f.write(f"{item[0]}|{item[1]}\n")
    print("Fullnames CSV created")
    

def create_edges_csv(my_graph, node_dict):
    """
    This function creates a csv file with the edges of the graph. The CSV must have the following format:
    **edges.csv**
    ```
    source,target,type
    1,2,cites
    1,3,in_L1
    ...
    ```
    """
    edges = my_graph.edges(data=True)
    my_list = []
    for edge in edges:
        # these source/target are strings. Use the node_dict to
        # convert them to the corresponding integer id
        source = edge[0]
        target = edge[1]
        if not edge[2]:
            continue
        for rel_type in edge[2]:
            my_list.append((node_dict[source], node_dict[target], rel_type, edge[2][rel_type]))
    # sort the list by the source node id
    my_list.sort(key=lambda x: x[0])
    with open(os.path.join(DATA_PATH, "neo4j-imports", "edges.csv"), "w") as f:
        f.write("source|target|type|weight\n")
        for idx, item in enumerate(my_list, start=1):
            f.write(f"{item[0]}|{item[1]}|{item[2]}|{item[3]}\n")
    print("Edges CSV created")


def retrieve_venue_neigh_per_fos(fos_label, level, rel, driver):
    cypher_query = f"""
    MATCH (l3:Node {{name: "{fos_label}"}})-[:HAS_ROLE]->(:Role {{name: "{level}"}})
    
    // One-hop nodes: Directly connected via $rel and have role "venue"
    MATCH (l3)<-[r:{rel}]-(venue:Node)-[:HAS_ROLE]->(:Role {{name: "venue"}})
    
    //get the fullnames of the venues if existing
    OPTIONAL MATCH (venue)-[r1:HAS_FULL_NAME]->(fn:FullName)
    
    RETURN l3, venue, r, r1, fn;
    """
    records, _, _ = driver.execute_query(cypher_query, fos_label=fos_label, level=level, rel=rel, database_="neo4j")
    return records


if __name__ == "__main__":
    with open(FOS_TAXONOMY_PATH, "r") as f:
        fos_taxonomy = json.load(f)
    my_graph = MultiGraph(os.path.join(DATA_PATH, 'scinobo_inference_graph.json'))
    venue_parser = VenueParser(abbreviation_dict=os.path.join(DATA_PATH, 'misc', 'venues_maps.p'))
    abbrev_dict = venue_parser.abbreviation_dict
    node_dict = create_nodes_csv(my_graph, fos_taxonomy)
    create_fullnames_csv(abbrev_dict, node_dict)
    create_edges_csv(my_graph, node_dict)