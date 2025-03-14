"""
This script defines a class `MultiGraph` that extends the functionality of the `networkx.MultiDiGraph` class.
It provides additional methods for saving and loading the graph, adding entities and relationships, plotting degree distribution,
exporting to Gephi format, calculating annotation coverage, and inferring relationships between entities.

Classes:
- MultiGraph: A subclass of `networkx.MultiDiGraph` with additional methods.

Methods:
- save(path): Save the graph object to a file using pickle.
- add_entities(from_entities, to_entities, relationship_type, relationships, cutoff=0): Add entities and relationships to the graph.
- load(path): Load the graph object from a file using pickle.
- plot_degree_dist(nbins): Plot the degree distribution of the graph.
- export_gephi(filename="my_graph.gexf"): Export the graph to Gephi format.
- annotation_coverage(relationship, entity): Calculate the annotation coverage for a given relationship and entity.
- infer_layer(entity_chain, relationship_chain, overwrite=False, max_links=2, filters=[0, 0], new_relationship="default"): Infer relationships between entities based on existing relationships.

Attributes:
- None

Dependencies:
- networkx
- os
- pickle
- tqdm
- matplotlib.pyplot

Usage:
- Create an instance of the `MultiGraph` class and use its methods to manipulate and analyze the graph.
- Call the `save` method to save the graph to a file.
- Call the `load` method to load a saved graph from a file.
- Call the `add_entities` method to add entities and relationships to the graph.
- Call the `plot_degree_dist` method to plot the degree distribution of the graph.
- Call the `export_gephi` method to export the graph to Gephi format.
- Call the `annotation_coverage` method to calculate the annotation coverage for a given relationship and entity.
- Call the `infer_layer` method to infer relationships between entities based on existing relationships.
"""

import networkx as nx
import os
import json

from tqdm import tqdm


def mydate():
    from datetime import date
    return date.today().strftime("%m_%d_%y")


class MultiGraph(nx.MultiDiGraph):
    """
    A subclass of `nx.MultiDiGraph` that represents a multi-graph with additional functionality.

    This class extends the functionality of the `nx.MultiDiGraph` class from the NetworkX library.
    It provides methods for saving and loading the graph, adding entities and relationships, plotting
    degree distribution, exporting to Gephi format, calculating annotation coverage, and inferring layers.

    Attributes:
        None

    Methods:
        save(path): Saves the graph to a file.
        add_entities(from_entities, to_entities, relationship_type, relationships, cutoff=0): Adds entities and relationships to the graph.
        load(path): Loads the graph from a file.
        plot_degree_dist(nbins): Plots the degree distribution of the graph.
        export_gephi(filename="my_graph.gexf"): Exports the graph to Gephi format.
        annotation_coverage(relationship, entity): Calculates the annotation coverage of a relationship for a given entity.
        infer_layer(entity_chain, relationship_chain, overwrite=False, max_links=2, filters=[0, 0], new_relationship="default"): Infers a layer of relationships based on existing relationships and entities.
    """
    def save(self, path):
        """
        Save the Multigraph object to a file.

        Parameters:
        - path (str): The path to the file where the Multigraph object will be saved.

        Returns:
        None
        """
        # Convert the MultiGraph to node-link data format
        data = nx.node_link_data(self)
        # Save the data to a JSON file
        with open(path, 'w') as f:
            json.dump(data, f)
        assert (os.path.isfile(path))

    def add_entities(self, from_entities, to_entities, relationship_type, relationships, cutoff=0):
        """
            Add entities and relationships to the my_graph.

            Parameters:
            - from_entities (str): The attribute name for the 'from' entities.
            - to_entities (str): The attribute name for the 'to' entities.
            - relationship_type (str): The attribute name for the relationship type.
            - relationships (dict): A dictionary containing the relationships between entities.
            - cutoff (int, optional): The minimum value for a relationship to be included. Defaults to 0.
            """        
        sources = [k for k in relationships.keys() if k]
        targets = [k for d in relationships.values() for k, _ in d.items() if k]
        self.add_nodes_from(sources)
        self.add_nodes_from(targets)
        for node in sources:
            self.nodes[node][from_entities] = True
        for node in targets:
            self.nodes[node][to_entities] = True
        for (k, v) in relationships.items():
            self.add_edges_from(
                [(k, t, {relationship_type: v[t] / sum(list(v.values()))}) for t in v if v[t] >= cutoff if k if t])

    def load(self, path):
        """
        Load a serialized my_graph from a file.

        Parameters:
        path (str): The path to the file containing the serialized my_graph.

        Returns:
        None
        """
        with open(path, 'r') as f:
            data = json.load(f)
        G = nx.node_link_graph(data)
        super().__init__(G)

    def infer_layer(self, entity_chain, relationship_chain, overwrite=False, max_links=2, filters=[0, 0], new_relationship="default"):
        """
        Infers relationships between entities in the graph based on specified entity and relationship chains.

        Args:
            entity_chain (list): A list of length 3 representing the chain of entity attributes in the graph.
            relationship_chain (list): A list of length 2 representing the chain of relationship attributes in the graph.
            overwrite (bool, optional): If True, existing relationships will be overwritten. Defaults to False.
            max_links (int, optional): The maximum number of links to infer for each entity. Defaults to 2.
            filters (list, optional): A list of length 2 representing the filters to apply on the relationships. Defaults to [0, 0].
            new_relationship (str, optional): The name of the new relationship to be created. Defaults to "default".

        Returns:
            None
        """
        assert (len(relationship_chain) == 2)
        assert (len(entity_chain) == 3)
        assert (len(filters) <= 2)

        """ Predefines for working along with the API"""
        starting_entities = [n[0] for n in list(self.nodes(data=entity_chain[0])) if n[1] if n[0]]

        new_edges = {}
        for entity in tqdm(starting_entities, disable=False, desc='Inferring relationships'):

            """ Predefines for working along with the API"""
            edgelist_existing = list(self.edges(data=relationship_chain[1], nbunch=entity))
            edgelist_neighbors = list(self.edges(data=relationship_chain[0], nbunch=entity))

            if not overwrite:
                existing_assignments = [field[1:] for field in edgelist_existing if
                                        field[2]]
                if existing_assignments:
                    continue

            neighbors = [neigh[1:] for neigh in edgelist_neighbors if neigh[2] if
                         self.nodes[neigh[1]][entity_chain[1]] if neigh[2] >= filters[0] if neigh[1]]
            aggregate_dict = {}
            for neigh in neighbors:
                prev_weight = neigh[1]

                """ Predefines for working along with the API"""
                edgelist_fos = list(self.edges(data=relationship_chain[1], nbunch=neigh[0]))

                fos = [field[1:] for field in edgelist_fos if field[2] if
                       self.nodes[field[1]][entity_chain[2]] if field[2] >= filters[1] if field[1]]
                total_weights = sum([field[1] for field in fos])
                for field in fos:
                    fieldname = field[0]
                    curr_weight = field[1] / total_weights
                    try:
                        aggregate_dict[fieldname] += prev_weight * curr_weight
                    except KeyError:
                        aggregate_dict[fieldname] = prev_weight * curr_weight
                    '''
                    try:
                        assert(aggregate_dict[fieldname]<=1)
                    except AssertionError:
                        print(aggregate_dict[fieldname],'invalid weight')
                        print('entity',entity)
                        print('neighbor fos',fos)
                        assert(False)
                    '''
            candidates = sorted(aggregate_dict.items(), key=lambda kv: kv[1], reverse=True)
            new_edges[entity] = candidates[:max_links]

        if new_relationship == "default":
            new_relationship = relationship_chain[1]
        for entity, edges in new_edges.items():
            for edge in edges:
                self.add_edge(entity, edge[0])
                self.edges[entity, edge[0], 0][new_relationship] = edge[1]

    def __init__(self, path=None):
        # super().__init__()
        if path and os.path.isfile(path):
            self.load(path)
