# :simple-owasp: Asset Database

The **Asset Database** is the persistent store for all
entities and relations discovered during an Amass
enumeration. It is backed by the
[`owasp-amass/asset-db`][asset-db] library, which
provides a unified repository interface over multiple
storage backends.

[asset-db]: https://github.com/owasp-amass/asset-db

Every Amass **Session** receives its own database
connection. Assets are stored as typed entities
following the [Open Asset Model][oam]; the connections
between them are stored as directed edges (relations)
with optional properties attached to both entities
and edges.

[oam]: ../open_asset_model/index.md

## :material-database: Supported Backends

| Backend | Connection String | Best For |
| :--- | :--- | :--- |
| **SQLite** | Auto-created | Dev, quick scans |
| **PostgreSQL** | `postgres://u:p@host:5432/db` | Production |
| **Neo4j** | `neo4j://u:p@host:7687/db` | Graph queries |

If no database is configured, Amass automatically
creates a local SQLite database in its configuration
directory.

## :material-cog: Configuring the Database

Set the connection string in `config.yaml`:

```yaml
options:
  database: "postgres://amass:amass4OWASP@host:5432/db"
```

You can also configure the database via environment
variables, which take precedence over the config file:

```text
AMASS_DB_USER      database username
AMASS_DB_PASSWORD  database password
AMASS_DB_HOST      database host
AMASS_DB_PORT      database port
AMASS_DB_NAME      database name
```

## :material-graph-outline: How It Fits Together

The asset database sits at the center of the data
model. The Amass engine writes every discovered asset
into the database during enumeration. Assets are
stored once and referenced many times — the same IP
address discovered by multiple data sources is a
single entity with multiple `SourceProperty`
annotations.

Relations between assets (e.g., an FQDN resolving to
an IP address via a `dns_record` relation) are stored
as directed edges. This graph structure is what makes
the [Triples Query Language](triples.md) possible.

## :material-page-next: Next Steps

- [Getting Started](getting-started.md) — installation and quick start guide
- [PostgreSQL Setup](postgres.md) — production PostgreSQL setup guide
- [Triples Query Language](triples.md) — traverse the asset graph with subject-predicate-object queries
- [Caching](caching.md) — performance caching layer
- [Database Migrations](migrations.md) — schema management
- [API Reference](api-reference.md) — complete API documentation


---

## Architecture

## Purpose and Scope

This document provides an architectural overview of the `asset-db` repository, a Go library that provides unified, multi-backend database storage for asset management in the OWASP Amass ecosystem. It explains the core design patterns, supported database backends, and how the system integrates with the Open Asset Model (OAM) to store and query relationships between security reconnaissance assets.

For installation and configuration details, see [Getting Started](./getting-started.md). For implementation details of specific components, see [Architecture](./index.md#architecture), [SQL Repository](./postgres.md#sql-repository-implementation), [Neo4j Repository](./triples.md#neo4j-repository), and [Caching System](./caching.md).

---

## Role in the OWASP Amass Ecosystem

The `asset-db` library serves as the persistence layer for OWASP Amass, providing a flexible storage backend for asset intelligence gathered during network reconnaissance and attack surface mapping. It stores assets (FQDNs, IP addresses, organizations, autonomous systems) and their relationships as a property graph, enabling complex queries about network infrastructure and ownership.

The library is designed as a standalone Go module (`github.com/owasp-amass/asset-db`) that can be imported and used independently of Amass, making it suitable for any application requiring graph-based asset storage with multiple database backend options.

---

## Core Features

### Layered Architecture

## Architectural Overview

The asset-db system follows a layered architecture that separates concerns through well-defined abstractions. The system is designed to provide a unified interface for asset management while supporting multiple database backends (PostgreSQL, SQLite, and Neo4j).

### Design Patterns

## Design Patterns

### Repository Pattern

## Interface Definition

The `repository.Repository` interface defines the contract that all database implementations must fulfill. Located in , this interface provides a comprehensive set of operations organized into four functional groups:

## Factory Pattern Implementation

The system uses the Factory Pattern to instantiate the appropriate repository implementation based on the specified database type. This pattern provides two key benefits:

1. **Decoupling:** Client code depends only on the `repository.Repository` interface, not concrete implementations
2. **Extensibility:** New database backends can be added without modifying client code

### Data Model

This page documents the core data model of asset-db, which implements a property graph structure consisting of four primary types: Entity, Edge, EntityTag, and EdgeTag. These types form the foundation for representing assets and their relationships across all repository implementations.

For details on how these types are used in repository operations, see [Repository Pattern](./index.md#repository-pattern). For information about the Open Asset Model types stored within these structures, see [Open Asset Model Integration](./index.md#open-asset-model-integration).

---

## Overview

The asset-db data model implements a **labeled property graph** with first-class support for temporal tracking. Assets are represented as entities (nodes), relationships between assets are represented as edges (directed relationships), and both entities and edges can have multiple associated tags (properties/metadata).

All content in entities and edges is defined using the Open Asset Model (OAM), ensuring type safety and standardization across the OWASP Amass ecosystem. Tags provide extensible metadata storage without modifying the core entity or edge structures.

---

## Core Data Types

### Type Definitions

The following table summarizes the four core types defined in the `types` package:

| Type | Purpose | Key Fields | Content Type |
|------|---------|------------|--------------|
| `Entity` | Represents a node/asset in the graph | `ID`, `CreatedAt`, `LastSeen`, `Asset` | `oam.Asset` |
| `Edge` | Represents a directed relationship between entities | `ID`, `CreatedAt`, `LastSeen`, `Relation`, `FromEntity`, `ToEntity` | `oam.Relation` |
| `EntityTag` | Metadata/properties attached to an entity | `ID`, `CreatedAt`, `LastSeen`, `Property`, `Entity` | `oam.Property` |
| `EdgeTag` | Metadata/properties attached to an edge | `ID`, `CreatedAt`, `LastSeen`, `Property`, `Edge` | `oam.Property` |

---

### Entity Structure

```mermaid
classDiagram
    class Entity {
        +string ID
        +time.Time CreatedAt
        +time.Time LastSeen
        +oam.Asset Asset
    }
    
    class Asset {
        <<interface>>
        +AssetType() AssetType
        +JSON() (string, error)
    }
    
    Entity --> Asset : contains
```

**Entity Diagram: Structure and Open Asset Model Integration**

The `Entity` type represents a node in the property graph. Each entity has:

- **ID**: Unique identifier (string representation, database-specific)
- **CreatedAt**: Timestamp when the entity was first created
- **LastSeen**: Timestamp when the entity was last observed/updated
- **Asset**: An Open Asset Model asset (FQDN, IPAddress, Organization, etc.)

The `Asset` field contains the actual asset data and must implement the `oam.Asset` interface, which provides type identification and JSON serialization.

---

### Edge Structure

```mermaid
classDiagram
    class Edge {
        +string ID
        +time.Time CreatedAt
        +time.Time LastSeen
        +oam.Relation Relation
        +*Entity FromEntity
        +*Entity ToEntity
    }
    
    class Relation {
        <<interface>>
        +RelationType() RelationType
        +JSON() (string, error)
    }
    
    class Entity {
        +string ID
        +time.Time CreatedAt
        +time.Time LastSeen
        +oam.Asset Asset
    }
    
    Edge --> Relation : contains
    Edge --> Entity : FromEntity
    Edge --> Entity : ToEntity
```

**Edge Diagram: Directed Relationships Between Entities**

The `Edge` type represents a directed relationship in the property graph. Each edge has:

- **ID**: Unique identifier
- **CreatedAt**: Timestamp when the edge was first created
- **LastSeen**: Timestamp when the edge was last observed/updated
- **Relation**: An Open Asset Model relation (BasicDNSRelation, SimpleRelation, etc.)
- **FromEntity**: Pointer to the source entity
- **ToEntity**: Pointer to the target entity

Edges are always directed from `FromEntity` to `ToEntity`, establishing a clear semantic relationship direction (e.g., "domain points to IP address").

---

### EntityTag Structure

```mermaid
classDiagram
    class EntityTag {
        +string ID
        +time.Time CreatedAt
        +time.Time LastSeen
        +oam.Property Property
        +*Entity Entity
    }
    
    class Property {
        <<interface>>
        +PropertyType() PropertyType
        +JSON() (string, error)
    }
    
    class Entity {
        +string ID
        +oam.Asset Asset
    }
    
    EntityTag --> Property : contains
    EntityTag --> Entity : associated with
```

**EntityTag Diagram: Extensible Metadata for Entities**

The `EntityTag` type attaches metadata to entities. Each entity tag has:

- **ID**: Unique identifier
- **CreatedAt**: Timestamp when the tag was first created
- **LastSeen**: Timestamp when the tag was last observed/updated
- **Property**: An Open Asset Model property (SimpleProperty, DNSRecordProperty, etc.)
- **Entity**: Pointer to the associated entity

Multiple tags can be attached to a single entity, allowing flexible metadata storage without modifying the entity structure.

---

### EdgeTag Structure

```mermaid
classDiagram
    class EdgeTag {
        +string ID
        +time.Time CreatedAt
        +time.Time LastSeen
        +oam.Property Property
        +*Edge Edge
    }
    
    class Property {
        <<interface>>
        +PropertyType() PropertyType
        +JSON() (string, error)
    }
    
    class Edge {
        +string ID
        +oam.Relation Relation
    }
    
    EdgeTag --> Property : contains
    EdgeTag --> Edge : associated with
```

**EdgeTag Diagram: Extensible Metadata for Edges**

The `EdgeTag` type attaches metadata to edges. Each edge tag has:

- **ID**: Unique identifier
- **CreatedAt**: Timestamp when the tag was first created
- **LastSeen**: Timestamp when the tag was last observed/updated
- **Property**: An Open Asset Model property
- **Edge**: Pointer to the associated edge

Multiple tags can be attached to a single edge, enabling relationship metadata such as confidence scores, data sources, or additional context.

---

## Graph Relationships

The following diagram illustrates how the four core types relate to form a complete property graph:

```mermaid
graph TB
    subgraph "Graph Structure"
        E1["Entity #1<br/>(Node)"]
        E2["Entity #2<br/>(Node)"]
        Edge1["Edge<br/>(Directed Relationship)"]
    end
    
    subgraph "Metadata Layer"
        ET1["EntityTag 1<br/>(Property)"]
        ET2["EntityTag 2<br/>(Property)"]
        ET3["EntityTag 3<br/>(Property)"]
        EdgeTag1["EdgeTag 1<br/>(Property)"]
        EdgeTag2["EdgeTag 2<br/>(Property)"]
    end
    
    E1 -->|"FromEntity"| Edge1
    Edge1 -->|"ToEntity"| E2
    
    E1 -.->|"has many"| ET1
    E1 -.->|"has many"| ET2
    E2 -.->|"has many"| ET3
    
    Edge1 -.->|"has many"| EdgeTag1
    Edge1 -.->|"has many"| EdgeTag2
```

**Complete Property Graph Model: Entities, Edges, and Tags**

This diagram shows:
- **Entities** are nodes that can be connected by edges
- **Edges** are directed relationships from one entity to another
- **EntityTags** provide many-to-one metadata relationships with entities
- **EdgeTags** provide many-to-one metadata relationships with edges

---

## Temporal Tracking

All four core types include temporal tracking fields that enable time-based queries and data lifecycle management:

| Field | Type | Purpose |
|-------|------|---------|
| `CreatedAt` | `time.Time` | Records when the entity/edge/tag was first created in the database |
| `LastSeen` | `time.Time` | Records when the entity/edge/tag was last observed or updated |

These timestamps enable:
- **Historical queries**: Find entities/edges/tags created or updated within a time range
- **Data freshness**: Determine how recently data was observed
- **Cache invalidation**: Track when cached data becomes stale (see [Cache Architecture](./caching.md#cache-architecture))

The repository interface methods often accept a `since time.Time` parameter to filter results based on `LastSeen` timestamps.

---

## Database Schema Mappings

The core data types map to database schemas differently depending on the backend.

### SQL Schema (PostgreSQL and SQLite)

The SQL schema consists of four tables that directly correspond to the four core types:

```mermaid
erDiagram
    entities ||--o{ entity_tags : "has many"
    entities ||--o{ edges : "from_entity_id"
    entities ||--o{ edges : "to_entity_id"
    edges ||--o{ edge_tags : "has many"
    
    entities {
        int entity_id PK
        timestamp created_at
        timestamp updated_at
        varchar etype
        jsonb content
    }
    
    entity_tags {
        int tag_id PK
        timestamp created_at
        timestamp updated_at
        varchar ttype
        jsonb content
        int entity_id FK
    }
    
    edges {
        int edge_id PK
        timestamp created_at
        timestamp updated_at
        varchar etype
        jsonb content
        int from_entity_id FK
        int to_entity_id FK
    }
    
    edge_tags {
        int tag_id PK
        timestamp created_at
        timestamp updated_at
        varchar ttype
        jsonb content
        int edge_id FK
    }
```

**SQL Schema: Entity-Relationship Diagram**

#### Field Mappings

| Go Type Field | SQL Column | Notes |
|---------------|------------|-------|
| `Entity.ID` | `entities.entity_id` | Auto-generated integer primary key |
| `Entity.CreatedAt` | `entities.created_at` | Default: `CURRENT_TIMESTAMP` |
| `Entity.LastSeen` | `entities.updated_at` | Updated on each modification |
| `Entity.Asset` | `entities.etype` + `entities.content` | Type stored as string, content as JSONB (PostgreSQL) or TEXT (SQLite) |
| `Edge.FromEntity` | `edges.from_entity_id` | Foreign key to `entities.entity_id` |
| `Edge.ToEntity` | `edges.to_entity_id` | Foreign key to `entities.entity_id` |
| `EntityTag.Entity` | `entity_tags.entity_id` | Foreign key with CASCADE delete |
| `EdgeTag.Edge` | `edge_tags.edge_id` | Foreign key with CASCADE delete |

#### Key Schema Features

**Indexes for Performance:**
- All tables have indexes on `updated_at` for temporal queries
- Entity and edge type fields (`etype`) are indexed for type-based filtering
- Foreign key columns are indexed for join performance

**Cascading Deletes:**
- Deleting an entity automatically deletes all its entity tags
- Deleting an entity automatically deletes all edges connected to it
- Deleting an edge automatically deletes all its edge tags

**JSON Storage:**
- PostgreSQL uses native `JSONB` type for `content` fields
- SQLite uses `TEXT` type with JSON serialization

---

### Neo4j Schema

In Neo4j, the data model maps to native graph concepts:

```mermaid
graph LR
    subgraph "Neo4j Graph Model"
        E1["(:Entity)<br/>node with Asset properties"]
        E2["(:Entity)<br/>node with Asset properties"]
        R["[Relation]<br/>relationship with Relation properties"]
        
        E1 -->|"[:Relation]"| E2
        
        ET1["(:EntityTag)<br/>separate node"]
        ET2["(:EntityTag)<br/>separate node"]
        EdgeT["(:EdgeTag)<br/>separate node"]
        
        E1 -.->|"[:HAS_TAG]"| ET1
        E1 -.->|"[:HAS_TAG]"| ET2
        R -.->|"[:HAS_TAG]"| EdgeT
    end
```

**Neo4j Graph Model: Nodes and Relationships**

#### Neo4j Mapping

| Go Type | Neo4j Concept | Label/Type | Properties |
|---------|---------------|------------|------------|
| `Entity` | Node | `:Entity` | `id`, `created_at`, `last_seen`, `asset_type`, plus all Asset fields |
| `Edge` | Relationship | Dynamic (based on `Relation.Type()`) | `id`, `created_at`, `last_seen`, plus all Relation fields |
| `EntityTag` | Node | `:EntityTag` | `id`, `created_at`, `last_seen`, `property_type`, plus all Property fields |
| `EdgeTag` | Node | `:EdgeTag` | `id`, `created_at`, `last_seen`, `property_type`, plus all Property fields |

#### Neo4j Schema Features

- **Entity nodes** are labeled `:Entity` and have properties flattened from the contained `oam.Asset`
- **Edges** are native Neo4j relationships with dynamic types based on `oam.Relation.Type()`
- **Tags** are separate nodes connected with `:HAS_TAG` relationships
- **Constraints** ensure uniqueness on `id` fields for all node types
- **Indexes** on `last_seen` and type fields for performance

The Neo4j schema is initialized with constraints and indexes. For details, see [Neo4j Schema and Constraints](./triples.md#neo4j-schema-and-constraints).

---

## Type System Integration

All content fields in the core types use Open Asset Model interfaces:

| Core Type | Content Field | OAM Interface | Examples |
|-----------|--------------|---------------|----------|
| `Entity` | `Asset` | `oam.Asset` | `FQDN`, `IPAddress`, `Organization`, `AutonomousSystem` |
| `Edge` | `Relation` | `oam.Relation` | `BasicDNSRelation`, `SimpleRelation`, `OwnershipRelation` |
| `EntityTag` | `Property` | `oam.Property` | `SimpleProperty`, `DNSRecordProperty`, `GeoLocationProperty` |
| `EdgeTag` | `Property` | `oam.Property` | `SimpleProperty`, `ConfidenceProperty`, `SourceProperty` |

Each OAM interface provides:
- **Type identification**: Methods to determine the specific asset/relation/property type
- **JSON serialization**: Standardized serialization for database storage
- **Type safety**: Compile-time guarantees about data structure

For comprehensive documentation of OAM types and their usage, see [Open Asset Model Integration](./index.md#open-asset-model-integration).

---

## Repository Interface Operations

The `Repository` interface provides methods for creating, retrieving, and deleting all four core types:

```mermaid
graph TB
    subgraph "Entity Operations"
        CreateEntity["CreateEntity(*Entity)"]
        FindEntityById["FindEntityById(id)"]
        FindEntitiesByContent["FindEntitiesByContent(asset, since)"]
        FindEntitiesByType["FindEntitiesByType(atype, since)"]
        DeleteEntity["DeleteEntity(id)"]
    end
    
    subgraph "Edge Operations"
        CreateEdge["CreateEdge(*Edge)"]
        FindEdgeById["FindEdgeById(id)"]
        IncomingEdges["IncomingEdges(entity, since, labels)"]
        OutgoingEdges["OutgoingEdges(entity, since, labels)"]
        DeleteEdge["DeleteEdge(id)"]
    end
    
    subgraph "EntityTag Operations"
        CreateEntityTag["CreateEntityTag(entity, tag)"]
        FindEntityTagById["FindEntityTagById(id)"]
        FindEntityTagsByContent["FindEntityTagsByContent(prop, since)"]
        GetEntityTags["GetEntityTags(entity, since, names)"]
        DeleteEntityTag["DeleteEntityTag(id)"]
    end
    
    subgraph "EdgeTag Operations"
        CreateEdgeTag["CreateEdgeTag(edge, tag)"]
        FindEdgeTagById["FindEdgeTagById(id)"]
        FindEdgeTagsByContent["FindEdgeTagsByContent(prop, since)"]
        GetEdgeTags["GetEdgeTags(edge, since, names)"]
        DeleteEdgeTag["DeleteEdgeTag(id)"]
    end
```

**Repository Operations: CRUD Methods for Core Types**

Each type has:
- **Creation**: Methods to create new instances
- **Retrieval by ID**: Methods to find by unique identifier
- **Content-based search**: Methods to find by OAM content matching
- **Associated queries**: Methods to find tags for entities/edges, or edges for entities
- **Deletion**: Methods to remove instances

For complete method signatures and usage details, see [Repository Interface](./api-reference.md#repository-interface).

---

## Data Flow Example

The following diagram shows how the core types are used in a typical operation to create an entity with tags and connect it to another entity:

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Repository
    participant DB as Database
    
    Note over C,DB: Create First Entity
    C->>R: CreateEntity(entity1)
    R->>DB: Store Entity with Asset content
    DB-->>R: Return entity1 with ID
    R-->>C: entity1
    
    Note over C,DB: Add Tag to Entity
    C->>R: CreateEntityTag(entity1, tag)
    R->>DB: Store EntityTag with Property content
    DB-->>R: Return tag with ID
    R-->>C: tag
    
    Note over C,DB: Create Second Entity
    C->>R: CreateEntity(entity2)
    R->>DB: Store Entity with Asset content
    DB-->>R: Return entity2 with ID
    R-->>C: entity2
    
    Note over C,DB: Create Edge Between Entities
    C->>R: CreateEdge(edge: entity1 -> entity2)
    R->>DB: Store Edge with Relation content
    DB-->>R: Return edge with ID
    R-->>C: edge
    
    Note over C,DB: Query Relationships
    C->>R: OutgoingEdges(entity1, since)
    R->>DB: Query edges where from_entity = entity1
    DB-->>R: [edge]
    R-->>C: [edge]
```

**Data Flow: Creating and Querying a Property Graph**

This sequence shows:
1. Entities are created with their `oam.Asset` content
2. Tags are attached to entities using `CreateEntityTag`
3. Edges establish directed relationships between entities
4. Queries can traverse the graph using `OutgoingEdges` and `IncomingEdges`

### Open Asset Model Integration

## Purpose and Scope

This page describes how the asset-db system integrates with the Open Asset Model (OAM) for standardized asset, property, and relationship definitions. It covers the OAM type system, how OAM types are embedded in the core data structures, and how they are serialized for database storage. For details on the core data structures themselves, see [Data Model](./index.md#data-model). For implementation-specific storage details, see [SQL Repository](./postgres.md#sql-repository-implementation) and [Neo4j Repository](./triples.md#neo4j-repository).

---

## What is the Open Asset Model

The Open Asset Model (OAM) is a standardized schema for representing assets and their relationships in the OWASP Amass ecosystem. It provides a common vocabulary and type system that enables interoperability between different tools and databases.

The asset-db system uses OAM version `v0.13.6` as specified in [go.mod:10]():

```
github.com/owasp-amass/open-asset-model v0.13.6
```

OAM defines three primary type categories:

| OAM Type | Purpose | Used In |
|----------|---------|---------|
| `oam.Asset` | Represents network assets (domains, IPs, organizations, etc.) | `types.Entity` |
| `oam.Property` | Represents metadata and properties of assets or relationships | `types.EntityTag`, `types.EdgeTag` |
| `oam.Relation` | Represents relationships between assets | `types.Edge` |

---

## Core Type Embedding

The asset-db type system directly embeds OAM types within its core data structures, creating a clean separation between the data model (entity, edge, tag) and the domain model (asset, property, relation).

### Type Structure Mapping

```mermaid
graph TB
    subgraph "types Package - Data Model"
        Entity["types.Entity<br/>ID, CreatedAt, LastSeen"]
        EntityTag["types.EntityTag<br/>ID, CreatedAt, LastSeen"]
        Edge["types.Edge<br/>ID, CreatedAt, LastSeen"]
        EdgeTag["types.EdgeTag<br/>ID, CreatedAt, LastSeen"]
    end
    
    subgraph "OAM Package - Domain Model"
        Asset["oam.Asset<br/>Interface for asset types"]
        Property["oam.Property<br/>Interface for property types"]
        Relation["oam.Relation<br/>Interface for relation types"]
    end
    
    Entity -->|"Asset field"| Asset
    EntityTag -->|"Property field"| Property
    Edge -->|"Relation field"| Relation
    EdgeTag -->|"Property field"| Property
    
    Entity -.->|"references"| EntityTag
    Edge -.->|"references"| EdgeTag
```

Each core type embeds exactly one OAM type as defined in :

- `Entity.Asset` (line 18): Stores the actual asset information
- `EntityTag.Property` (line 26): Stores metadata about an entity
- `Edge.Relation` (line 35): Defines the relationship type between entities
- `EdgeTag.Property` (line 45): Stores metadata about an edge

---

## Serialization and Storage Strategy

OAM types are serialized to JSON for database storage. The database schema uses two fields to represent each OAM-typed object:

| Database Field | Purpose | Example Values |
|----------------|---------|----------------|
| `etype` / `ttype` | Stores the OAM type name as a string | `"FQDN"`, `"IPAddress"`, `"BasicDNSRelation"` |
| `content` | Stores the serialized OAM object | JSON representation of the asset/property/relation |

### Storage Format by Database

```mermaid
graph LR
    subgraph "In-Memory (Go)"
        EntityGo["types.Entity<br/>Asset: oam.Asset"]
        EdgeGo["types.Edge<br/>Relation: oam.Relation"]
    end
    
    subgraph "PostgreSQL Storage"
        EntityPG["entities table<br/>etype: VARCHAR<br/>content: JSONB"]
        EdgePG["edges table<br/>etype: VARCHAR<br/>content: JSONB"]
    end
    
    subgraph "SQLite Storage"
        EntitySQL["entities table<br/>etype: TEXT<br/>content: TEXT"]
        EdgeSQL["edges table<br/>etype: TEXT<br/>content: TEXT"]
    end
    
    subgraph "Neo4j Storage"
        EntityNeo["Node<br/>:Entity label<br/>type property<br/>JSON properties"]
        EdgeNeo["Relationship<br/>type property<br/>JSON properties"]
    end
    
    EntityGo -->|"Serialize"| EntityPG
    EntityGo -->|"Serialize"| EntitySQL
    EntityGo -->|"Serialize"| EntityNeo
    
    EdgeGo -->|"Serialize"| EdgePG
    EdgeGo -->|"Serialize"| EdgeSQL
    EdgeGo -->|"Serialize"| EdgeNeo
```

#### PostgreSQL Schema

In PostgreSQL, OAM content is stored as native JSONB for efficient querying :

```sql
CREATE TABLE IF NOT EXISTS entities(
    entity_id INT GENERATED ALWAYS AS IDENTITY,
    ...
    etype VARCHAR(255),
    content JSONB,
    PRIMARY KEY(entity_id)
);
```

#### SQLite Schema

In SQLite, OAM content is stored as TEXT (JSON string) :

```sql
CREATE TABLE IF NOT EXISTS entities(
    entity_id INTEGER PRIMARY KEY,
    ...
    etype TEXT,
    content TEXT
);
```

The `etype` field is indexed in both databases ,  to enable efficient queries by asset type.

---

## OAM Asset Types

Assets represent the nodes in the graph - the actual network entities being tracked. Common OAM asset types include:

| Asset Type | Description | Example Content |
|------------|-------------|-----------------|
| `FQDN` | Fully Qualified Domain Name | `{"name": "example.com"}` |
| `IPAddress` | IPv4 or IPv6 address | `{"address": "192.0.2.1", "type": "IPv4"}` |
| `Netblock` | CIDR network range | `{"cidr": "192.0.2.0/24"}` |
| `AutonomousSystem` | AS Number | `{"number": 64512}` |
| `Organization` | Entity or company | `{"name": "Example Corp"}` |
| `Location` | Geographic location | `{"address": "123 Main St"}` |
| `ContactRecord` | Contact information | `{"email": "admin@example.com"}` |
| `EmailAddress` | Email address | `{"address": "user@example.com"}` |
| `Phone` | Phone number | `{"number": "+1-555-0123"}` |
| `URL` | Web resource locator | `{"url": "https://example.com/path"}` |

These asset types are defined in the OAM package and stored in the `Entity.Asset` field . The `etype` database field contains the string name of the asset type for efficient filtering and querying.

---

## OAM Property Types

Properties represent metadata that can be attached to entities or edges. They are stored in `EntityTag` and `EdgeTag` structures. Common OAM property types include:

| Property Type | Used For | Example Content |
|---------------|----------|-----------------|
| `SimpleProperty` | Generic key-value metadata | `{"key": "source", "value": "recon"}` |
| `DNSRecordProperty` | DNS record information | `{"type": "A", "value": "192.0.2.1"}` |
| `TLSCertificateProperty` | Certificate details | `{"subject": "CN=example.com"}` |
| `PortProperty` | Open port information | `{"port": 443, "protocol": "tcp"}` |
| `ServiceProperty` | Running service details | `{"name": "https", "version": "1.1"}` |
| `VulnerabilityProperty` | Security vulnerability | `{"cve": "CVE-2021-1234"}` |

Properties are stored in the `Property` field of both `EntityTag`  and `EdgeTag`  structures, with the property type name stored in the `ttype` database field.

**Example Usage:**

An entity representing a domain might have multiple tags:
- A `DNSRecordProperty` tag containing its A record
- A `TLSCertificateProperty` tag with certificate information
- Multiple `SimpleProperty` tags for additional metadata

---

## OAM Relation Types

Relations define the typed edges between entities in the graph. They specify the semantic meaning of relationships. Common OAM relation types include:

| Relation Type | Description | From Asset → To Asset |
|---------------|-------------|----------------------|
| `BasicDNSRelation` | DNS resolution | `FQDN` → `IPAddress` |
| `SimpleRelation` | Generic relationship | Any → Any |
| `ASNToIPRelation` | AS ownership | `AutonomousSystem` → `Netblock` |
| `IPToNetblockRelation` | IP membership | `IPAddress` → `Netblock` |
| `FQDNToFQDNRelation` | Domain hierarchy | `FQDN` → `FQDN` |
| `ContactToOrgRelation` | Organization membership | `ContactRecord` → `Organization` |
| `WhoisRelation` | WHOIS registration | `FQDN` → `Organization` |
| `SSLCertRelation` | Certificate binding | `FQDN` → `TLSCertificateProperty` |

Relations are stored in the `Edge.Relation` field  and define directed relationships from `FromEntity` to `ToEntity`.

### Relation Storage Schema

```mermaid
graph TB
    subgraph "Entity Storage"
        E1["Entity 1<br/>Asset: FQDN<br/>example.com"]
        E2["Entity 2<br/>Asset: IPAddress<br/>192.0.2.1"]
    end
    
    subgraph "Edge Storage"
        Edge["Edge<br/>Relation: BasicDNSRelation<br/>FromEntity → ToEntity"]
    end
    
    E1 -->|"FromEntity"| Edge
    Edge -->|"ToEntity"| E2
```

The database enforces referential integrity through foreign keys :

```sql
CONSTRAINT fk_edges_entities_from
    FOREIGN KEY(from_entity_id)
        REFERENCES entities(entity_id)
        ON DELETE CASCADE,
CONSTRAINT fk_edges_entities_to
    FOREIGN KEY(to_entity_id)
        REFERENCES entities(entity_id)
        ON DELETE CASCADE
```

---

## Type System Benefits

The integration of OAM provides several key benefits:

### Standardization Across OWASP Amass Ecosystem

All tools in the OWASP Amass ecosystem use the same OAM definitions, ensuring:
- Consistent asset representation across different tools
- Interoperable data exchange between components
- Unified querying and analysis capabilities

### Type Safety and Validation

By using OAM's typed interfaces:
- Asset types are validated at the OAM level
- Relationships can be constrained to valid asset type pairs
- Properties are strongly typed rather than arbitrary key-value pairs

### Extensibility

New asset types, properties, and relations can be added to OAM without changing the asset-db schema:
- The `etype`/`ttype` fields accommodate any OAM type name
- The `content` fields store arbitrary JSON structure
- Repositories handle serialization/deserialization transparently

### Database-Agnostic Domain Model

The OAM integration allows the same domain model to work across different database backends:
- PostgreSQL uses native JSONB for efficient querying
- SQLite uses TEXT storage for portability
- Neo4j stores OAM data as node/relationship properties
- All repositories expose the same `oam.Asset`, `oam.Property`, and `oam.Relation` interfaces

---

## Content Serialization Flow

The following diagram illustrates how OAM objects flow from creation through serialization to database storage and back:

```mermaid
sequenceDiagram
    participant App as "Application Code"
    participant Types as "types Package"
    participant Repo as "Repository<br/>Implementation"
    participant Serde as "JSON<br/>Serializer"
    participant DB as "Database"
    
    Note over App,DB: Creating an Entity with OAM Asset
    
    App->>Types: "Create Entity with<br/>oam.Asset (e.g., FQDN)"
    Types->>Types: "Entity.Asset = fqdnAsset"
    App->>Repo: "CreateEntity(entity)"
    Repo->>Serde: "Serialize Asset to JSON"
    Serde->>Serde: "Extract type name<br/>(Asset.AssetType())"
    Serde-->>Repo: "etype, content JSON"
    Repo->>DB: "INSERT with<br/>etype='FQDN'<br/>content={...}"
    DB-->>Repo: "entity_id"
    Repo-->>App: "Entity with ID"
    
    Note over App,DB: Retrieving an Entity
    
    App->>Repo: "FindEntityById(id)"
    Repo->>DB: "SELECT etype, content"
    DB-->>Repo: "etype='FQDN',<br/>content={...}"
    Repo->>Serde: "Deserialize based on etype"
    Serde->>Serde: "Create oam.Asset<br/>from JSON + type"
    Serde-->>Repo: "oam.Asset"
    Repo->>Types: "Populate Entity.Asset"
    Repo-->>App: "Entity with oam.Asset"
```

This flow is implemented differently in each repository but maintains the same contract:
- SQL repositories use GORM with JSON serialization
- Neo4j repositories use custom Cypher queries with property mapping

---

## Summary

The Open Asset Model integration provides a standardized, type-safe foundation for representing network assets in the asset-db system:

- **Three OAM Types**: `Asset`, `Property`, and `Relation` are embedded in `Entity`, `EntityTag`/`EdgeTag`, and `Edge` respectively
- **Database Storage**: Type names stored in `etype`/`ttype` fields, content serialized to JSON in `content` fields
- **Cross-Database Compatibility**: Same OAM types work across PostgreSQL (JSONB), SQLite (TEXT), and Neo4j (properties)
- **Ecosystem Integration**: Ensures interoperability with other OWASP Amass tools through shared type definitions

For details on how specific repositories handle OAM serialization and queries, see [SQL Entity Operations](./postgres.md#sql-entity-operations) and [Neo4j Entity Operations](./triples.md#neo4j-entity-operations).

---

*© 2025 Jeff Foley — Licensed under Apache 2.0.*
