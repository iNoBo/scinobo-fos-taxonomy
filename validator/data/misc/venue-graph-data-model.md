# Venue Graph Data Model

The venue graph data model is designed to represent the relationships between various academic venues and fields of study (FoS). This document outlines the structure of the nodes and edges within the graph.

## Nodes

Each node in the graph can have one or more of the following roles:
- `venue`
- `L1`
- `L2`
- `L3`
- `L4`
- `L5`
- `is_L6`

Nodes can be connected to each other through various types of edges. Each node must have a unique ID and a unique name. Some nodes may have multiple attributes, meaning a node can be both a venue and an FoS at a certain level.

## Edge Types

The edges in the graph represent different types of relationships between the nodes. The following are the possible edge types:

- **venue - venue**: A venue cites another venue.
    - Edge type: `cites`
    
- **venue - in_L1**: A venue belongs to a certain L1.
    - Edge type: `in_L1`
    
- **venue - in_L2**: A venue belongs to a certain L2.
    - Edge type: `in_L2`
    
- **venue - in_L3**: A venue belongs to a certain L3.
    - Edge type: `in_L3`
    
- **venue - in_L4**: A venue belongs to a certain L4.
    - Edge type: `in_L4`
    
- **is_L6 - in_L5**: A word that belongs to a certain L5 is under a certain L5.
    - Edge type: `in_L5`
    
- **L2 - specializes_L1**: An L2 FoS is a child of the L1 FoS.
    - Edge type: `specializes_L1`
    
- **L3 - specializes_L2**: An L3 FoS is a child of the L2 FoS.
    - Edge type: `specializes_L2`
    
- **L4 - specializes_L3**: An L4 FoS is a child of the L3 FoS.
    - Edge type: `specializes_L3`
    
- **L5 - specializes_L4**: An L5 FoS is a child of the L4 FoS.
    - Edge type: `specializes_L4`
    
- **is_L6 - is_L6**: A co-occurrence of L6 words.
    - Edge type: `weight`

## Example Graph Visualization

![Graph Example](scinobo-venue-graph-data-model.drawio.svg)

This image represents an example of how the venue graph might be visualized, showing the nodes and their connections based on the described data model.
