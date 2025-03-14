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

## Venue Graph - neo4j Integration

To create the venue graph in a neo4j installation, follow these detailed steps. Ensure you have an already installed neo4j instance, either locally or in the cloud. If you need help with the installation, refer to the [neo4j installation guide](https://neo4j.com/docs/operations-manual/current/installation/). The abovementioned graph visualization is an initial attempt to visualize a graph model. However, as you can see below, the attributes (roles) of each node (for example a node can also be a venue, an L3, an L2 etc), will be created as separate nodes and linked with relationships to their nodes. This will serve us later, as the cypher queries for exploring the graph will be easier to express and write. We are also going to add nodes for the full names of a node with role: venue. Since an abbrieviated venue name, can have many original names. These type of relationship is visible in the fullnames.csv.

### Prepare CSV Files

Prepare two CSV files: one for nodes and one for edges. Ensure the files are formatted as follows:

**nodes.csv**
```
id,name,roles
1,Venue A,venue
2,Venue B,venue
3,Field L1,L1
4,Venue C,venue:L3:is_L6
5,Venue D,venue:L3
...
```

**fullnames.csv**
```
id,full_name
1,Venue Alpha
2,Venue Arena
3,Venue Beta
3,Venue Center
...
```

**edges.csv**
```
source,target,type
1,2,cites
1,3,in_L1
...
```

### Load CSV Files into neo4j
By default, paths are resolved relative to the Neo4j import directory. When deploying your instance set the import directory to where
your CSV files are located or save them directly to the import directory. For more information, check: [neo4j imports](https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/#_import_local_files).
Use the following Cypher queries to load the CSV data into neo4j.

**Load Nodes:**
```cypher
// Create constraint first (run once)
CREATE CONSTRAINT FOR (n:Node) REQUIRE n.id IS UNIQUE; // this also creates an index at the id.

// Load and process data
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row FIELDTERMINATOR '|'

// Merge on unique ID and set properties
MERGE (n:Node {id: toInteger(row.id)})
ON CREATE SET
  n.name = row.name,
  n.L4_name = row.L4_name,
  n.L5_name = row.L5_name

// Process roles
WITH n, row
UNWIND split(row.roles, ':') AS role

// Merge roles and relationships
MERGE (r:Role {name: TRIM(role)}) // TRIM removes whitespace
MERGE (n)-[:HAS_ROLE]->(r);
```

**Create index in node names**
```cypher
CREATE INDEX node_name_index FOR (n:Node) ON (n.name);
```

**Load Fullnames:**
```cypher
// Add a uniqueness constraint (run once)
CREATE CONSTRAINT FOR (fn:FullName) REQUIRE fn.name IS UNIQUE;

// Load data with batching (Neo4j ≥ 4.4)
:auto
LOAD CSV WITH HEADERS FROM 'file:///fullnames.csv' AS row FIELDTERMINATOR '|'
CALL {
  WITH row
  MATCH (n:Node {id: toInteger(row.id)})
  MERGE (fn:FullName {name: row.full_name})
  MERGE (n)-[:HAS_FULL_NAME]->(fn)
} IN TRANSACTIONS OF 10000 ROWS;
```

**Load Edges:**
```cypher
// note you can sort the edges.csv beforehand by the id, to improve indexing performance.
:auto
LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row FIELDTERMINATOR '|'
CALL {
  WITH row
  MATCH (source:Node {id: toInteger(row.source)}), (target:Node {id: toInteger(row.target)})
  CALL apoc.create.relationship(
    source,
    row.type,
    {weight: toFloat(row.weight) },
    target
  ) YIELD rel
  RETURN rel
} IN TRANSACTIONS OF 10000 ROWS
RETURN *;
```

### Verify the Graph

Run a simple query to verify the graph creation:
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25;
```

This will display a subset of your graph, showing the nodes and their relationships.

### Conclusion

You have successfully created the venue graph in neo4j using CSV files. For more advanced configurations and optimizations, refer to the [neo4j CSV import guide](https://neo4j.com/docs/operations-manual/current/tools/import/).

