# Neo4j Edge Operations


This document describes the edge (relationship) operations in the Neo4j repository implementation. Edges represent directed relationships between entities in the graph database, enabling traversal and querying of asset connections. For entity-level operations, see [Neo4j Entity Operations](#5.1). For tag management on edges, see [Neo4j Tag Management](#5.3).

## Overview

The Neo4j repository stores edges as native graph relationships in Neo4j, using relationship types derived from the Open Asset Model. Each edge connects two entity nodes and includes temporal metadata (creation time, last seen) along with relationship-specific properties.

**Key Features:**
- Relationship validation against OAM taxonomy
- Duplicate edge detection and timestamp updates
- Bidirectional edge traversal (incoming/outgoing)
- Temporal filtering with `since` parameter
- Label-based filtering for relationship types
- Native Cypher query execution


---

## Edge Data Model

Edges in Neo4j are represented as relationships between entity nodes. The relationship type corresponds to the OAM relation label (e.g., `DNS_RECORD`, `NODE`, `SIMPLE_RELATION`).

```mermaid
graph LR
    subgraph "Graph Structure"
        FromEntity["(from:Entity)<br/>entity_id: UUID"]
        ToEntity["(to:Entity)<br/>entity_id: UUID"]
        Relationship["[r:RELATIONSHIP_TYPE]<br/>edge_id: elementId<br/>created_at: LocalDateTime<br/>updated_at: LocalDateTime<br/>+ relation properties"]
    end
    
    FromEntity -->|"relationship type"| Relationship
    Relationship --> ToEntity
    
    subgraph "types.Edge Representation"
        EdgeStruct["types.Edge<br/>ID: string<br/>CreatedAt: time.Time<br/>LastSeen: time.Time<br/>Relation: oam.Relation<br/>FromEntity: *types.Entity<br/>ToEntity: *types.Entity"]
    end
    
    Relationship -.->|"converted to"| EdgeStruct
```

**Sources:** , [types/types.go]()

---

## Edge Creation

### Validation and Creation Flow

The `CreateEdge` method performs comprehensive validation before creating relationships in the graph database.

```mermaid
flowchart TD
    Start["CreateEdge(edge *types.Edge)"]
    
    ValidateInput["Validate Input:<br/>- edge != nil<br/>- Relation != nil<br/>- FromEntity/ToEntity exist<br/>- Assets != nil"]
    
    ValidateOAM["Validate Against OAM:<br/>oam.ValidRelationship()<br/>Check: FromAssetType -[Label]-> ToAssetType"]
    
    SetTimestamp["Set LastSeen:<br/>if edge.LastSeen.IsZero()<br/>then time.Now()"]
    
    CheckDup{"isDuplicateEdge()?<br/>Check existing relationships"}
    
    UpdateExisting["Update existing edge:<br/>edgeSeen(edge, updated)"]
    
    ReturnExisting["Return existing edge"]
    
    SetCreated["Set CreatedAt:<br/>if edge.CreatedAt.IsZero()<br/>then time.Now()"]
    
    BuildProps["Build properties map:<br/>edgePropsMap(edge)"]
    
    ExecuteCypher["Execute Cypher:<br/>MATCH (from:Entity {entity_id})<br/>MATCH (to:Entity {entity_id})<br/>CREATE (from)-[r:TYPE props]->(to)"]
    
    ConvertResult["Convert relationship to Edge:<br/>relationshipToEdge(rel)"]
    
    ReturnNew["Return new edge"]
    
    Error["Return error"]
    
    Start --> ValidateInput
    ValidateInput -->|"Valid"| ValidateOAM
    ValidateInput -->|"Invalid"| Error
    ValidateOAM -->|"Valid"| SetTimestamp
    ValidateOAM -->|"Invalid"| Error
    SetTimestamp --> CheckDup
    CheckDup -->|"Duplicate"| UpdateExisting
    UpdateExisting --> ReturnExisting
    CheckDup -->|"New"| SetCreated
    SetCreated --> BuildProps
    BuildProps --> ExecuteCypher
    ExecuteCypher -->|"Success"| ConvertResult
    ExecuteCypher -->|"Error"| Error
    ConvertResult --> ReturnNew
```


### Implementation Details

#### Input Validation

The method first validates all required fields:

```
Validation checks (edge.go:24-27):
- edge != nil
- edge.Relation != nil
- edge.FromEntity != nil && edge.FromEntity.Asset != nil
- edge.ToEntity != nil && edge.ToEntity.Asset != nil
```


#### OAM Taxonomy Validation

The relationship must be valid according to the Open Asset Model taxonomy:

```
oam.ValidRelationship(
    edge.FromEntity.Asset.AssetType(),
    edge.Relation.Label(),
    edge.Relation.RelationType(),
    edge.ToEntity.Asset.AssetType()
)
```

Returns error if invalid: `"{FromType} -{Label}-> {ToType} is not valid in the taxonomy"`


#### Cypher Query Construction

The relationship is created using a three-part Cypher query:

```
MATCH (from:Entity {entity_id: '{fromID}'})
MATCH (to:Entity {entity_id: '{toID}'})
CREATE (from)-[r:RELATIONSHIP_TYPE $props]->(to)
RETURN r
```

The relationship type is uppercased from the relation label (e.g., `dns_record` → `DNS_RECORD`).


---

## Duplicate Edge Handling

### Duplicate Detection Logic

The `isDuplicateEdge` method prevents duplicate relationships between the same entities with identical relation content.

```mermaid
flowchart TD
    Start["isDuplicateEdge(edge, updated)"]
    
    GetOutgoing["Get outgoing edges:<br/>OutgoingEdges(edge.FromEntity)"]
    
    IterateEdges["Iterate through outgoing edges"]
    
    CheckMatch{"Match found?<br/>- ToEntity.ID match<br/>- DeepEqual(Relations)"}
    
    UpdateTimestamp["Update timestamp:<br/>edgeSeen(out, updated)"]
    
    FetchEdge["Fetch updated edge:<br/>FindEdgeById(out.ID)"]
    
    ReturnTrue["Return (edge, true)"]
    
    ReturnFalse["Return (nil, false)"]
    
    Start --> GetOutgoing
    GetOutgoing --> IterateEdges
    IterateEdges --> CheckMatch
    CheckMatch -->|"Match"| UpdateTimestamp
    UpdateTimestamp --> FetchEdge
    FetchEdge --> ReturnTrue
    CheckMatch -->|"No match"| IterateEdges
    IterateEdges -->|"No more edges"| ReturnFalse
```

**Duplicate Criteria:**
1. Same `ToEntity.ID`
2. `reflect.DeepEqual(edge.Relation, out.Relation)` returns true


### Timestamp Update

When a duplicate is detected, the `edgeSeen` method updates the `updated_at` timestamp:

```
Cypher query (edge.go:117):
MATCH ()-[r]->() 
WHERE elementId(r) = $eid 
SET r.updated_at = localDateTime('{timestamp}')
```


---

## Edge Retrieval

### Find Edge By ID

The `FindEdgeById` method retrieves a specific edge using its Neo4j element ID:

```
MATCH (from:Entity)-[r]->(to:Entity) 
WHERE elementId(r) = $eid 
RETURN r, from.entity_id AS fid, to.entity_id AS tid
```

**Returns:**
- `types.Edge` with populated `FromEntity.ID` and `ToEntity.ID`
- Error if edge not found


---

## Edge Traversal

### Incoming Edges

The `IncomingEdges` method finds all edges pointing to a specific entity:

**Method Signature:**
```
IncomingEdges(entity *types.Entity, since time.Time, labels ...string) ([]*types.Edge, error)
```

**Cypher Queries:**

| Condition | Query Pattern |
|-----------|---------------|
| No temporal filter | `MATCH (:Entity {entity_id: $eid})<-[r]-(from:Entity) RETURN r, from.entity_id AS fid` |
| With `since` filter | `MATCH (:Entity {entity_id: $eid})<-[r]-(from:Entity) WHERE r.updated_at >= localDateTime('{since}') RETURN r, from.entity_id AS fid` |

**Label Filtering:**

After query execution, results are filtered by relationship type if labels are specified:

```
Post-processing (edge.go:214-227):
- If labels provided, check each relationship
- Compare r.Type against provided labels (case-insensitive)
- Only include matching relationships
```


### Outgoing Edges

The `OutgoingEdges` method finds all edges originating from a specific entity:

**Method Signature:**
```
OutgoingEdges(entity *types.Entity, since time.Time, labels ...string) ([]*types.Edge, error)
```

**Cypher Queries:**

| Condition | Query Pattern |
|-----------|---------------|
| No temporal filter | `MATCH (:Entity {entity_id: $eid})-[r]->(to:Entity) RETURN r, to.entity_id AS tid` |
| With `since` filter | `MATCH (:Entity {entity_id: $eid})-[r]->(to:Entity) WHERE r.updated_at >= localDateTime('{since}') RETURN r, to.entity_id AS tid` |

**Label Filtering:**

Identical to incoming edges, with post-processing label filtering.


### Traversal Patterns

```mermaid
graph TD
    subgraph "Incoming Edge Traversal"
        ExtFrom1["(from1:Entity)"]
        ExtFrom2["(from2:Entity)"]
        ExtFrom3["(from3:Entity)"]
        Target["(target:Entity)<br/>{entity_id: 'xyz'}"]
        
        ExtFrom1 -->|"[r1:TYPE1]"| Target
        ExtFrom2 -->|"[r2:TYPE2]"| Target
        ExtFrom3 -->|"[r3:TYPE1]"| Target
    end
    
    subgraph "Outgoing Edge Traversal"
        Source["(source:Entity)<br/>{entity_id: 'abc'}"]
        ExtTo1["(to1:Entity)"]
        ExtTo2["(to2:Entity)"]
        ExtTo3["(to3:Entity)"]
        
        Source -->|"[r4:TYPE1]"| ExtTo1
        Source -->|"[r5:TYPE2]"| ExtTo2
        Source -->|"[r6:TYPE1]"| ExtTo3
    end
    
    subgraph "Filter Options"
        SinceFilter["Temporal Filter:<br/>r.updated_at >= since"]
        LabelFilter["Label Filter:<br/>r.Type in labels"]
    end
```


---

## Edge Deletion

The `DeleteEdge` method removes a relationship from the graph:

**Cypher Query:**
```
MATCH ()-[r]->() 
WHERE elementId(r) = $eid 
DELETE r
```

**Note:** This only deletes the relationship; entity nodes remain intact.


---

## Data Conversion

### Relationship to Edge Conversion

The Neo4j driver returns relationships as `neo4jdb.Relationship` objects, which must be converted to `types.Edge`:

```mermaid
flowchart LR
    NeoRel["neo4jdb.Relationship<br/>- ElementId<br/>- Type<br/>- Properties<br/>- StartNodeElementId<br/>- EndNodeElementId"]
    
    Extract["Extract Properties:<br/>- edge_id (elementId)<br/>- created_at<br/>- updated_at<br/>- relation properties"]
    
    ConvertRel["Convert Relation:<br/>relationshipPropsToRelation()"]
    
    BuildEdge["types.Edge<br/>- ID: string<br/>- CreatedAt: time.Time<br/>- LastSeen: time.Time<br/>- Relation: oam.Relation"]
    
    NeoRel --> Extract
    Extract --> ConvertRel
    ConvertRel --> BuildEdge
```

**Key Functions:**

| Function | Purpose | Location |
|----------|---------|----------|
| `relationshipToEdge` | Converts Neo4j relationship to `types.Edge` | [repository/neo4j/extract_edge.go]() |
| `relationshipPropsToRelation` | Extracts OAM relation from relationship properties | [repository/neo4j/extract_edge.go]() |
| `edgePropsMap` | Creates property map for relationship creation | [repository/neo4j/property_edge.go]() |


---

## Testing

The Neo4j edge operations include comprehensive integration tests:

| Test | Description | File Reference |
|------|-------------|----------------|
| `TestCreateEdge` | Tests edge creation, validation, and duplicate handling |  |
| `TestFindEdgeById` | Tests edge retrieval by ID |  |
| `TestIncomingEdges` | Tests incoming edge traversal and filtering |  |
| `TestOutgoingEdges` | Tests outgoing edge traversal and filtering |  |
| `TestDeleteEdge` | Tests edge deletion |  |

**Test Scenarios:**
- Invalid label validation
- Duplicate edge detection with timestamp updates
- Temporal filtering with `since` parameter
- Label filtering with multiple relationship types
- Edge deletion and verification


---

## Error Handling

The edge operations return errors in the following scenarios:

| Error Condition | Error Message | Method |
|----------------|---------------|---------|
| Null inputs | "failed input validation checks" | `CreateEdge` |
| Invalid OAM relationship | "{FromType} -{Label}-> {ToType} is not valid in the taxonomy" | `CreateEdge` |
| No records returned | "no records returned from the query" | `CreateEdge` |
| Nil relationship | "the record value for the relationship is nil" | `CreateEdge`, `FindEdgeById` |
| Edge not found | "no edge was found" | `FindEdgeById` |
| Zero edges found | "zero edges found" | `IncomingEdges`, `OutgoingEdges` |


---

## Performance Considerations

### Indexes

The Neo4j schema includes indexes on relationship properties to optimize edge queries:

```
Edge-related indexes (schema.go):
- CREATE INDEX edgetag_range_index_edge_id 
  FOR (n:EdgeTag) ON (n.edge_id)
```

**Note:** Relationships do not support unique constraints or indexes on their properties in Neo4j. Performance is optimized through:
1. Entity node indexes on `entity_id`
2. Efficient Cypher query patterns
3. Label filtering in application layer when needed


### Query Optimization

**Best Practices:**
1. Use temporal filtering (`since` parameter) to limit result sets
2. Specify relationship labels to reduce post-processing
3. Index entity nodes for fast relationship endpoint lookups
4. Leverage Neo4j's native graph traversal algorithms
