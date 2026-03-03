# Setting Up a PostgreSQL Database for OWASP Amass

The OWASP Amass framework can store collected data in a PostgreSQL database. This page walks you through the recommended setup process, including environment variables, database initialization, and configuration in your `config.yaml` file.

> **Note:** These instructions assume PostgreSQL is already installed and running on your system (e.g., `localhost:5432`). You’ll need access to a user with sufficient privileges (typically `postgres`).

## 1. Define Environment Variables

Before running the setup commands, export the following environment variables to define your database, user, and passwords. These values will be used in the setup process and your Amass configuration.

```bash
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export AMASS_DB=assetdb
export AMASS_USER=amass
export AMASS_PASSWORD=amass4OWASP
```

??? info "Secrets Management"
    Consider storing these in a `.env` file and loading them with `source .env` to avoid retyping. Never commit secrets to version control.

## 2. Create the Amass Database and User

Run the following commands in your shell to initialize the database and create a dedicated user for Amass. This uses the `psql` CLI with inline SQL for automation.

```bash
# Add single quotes around the password to handle special characters
export TEMPPASS="'$AMASS_PASSWORD'"

# Create the database and user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    \getenv assetdb AMASS_DB
    \getenv username AMASS_USER
    \getenv password TEMPPASS

    CREATE DATABASE :assetdb;
    ALTER DATABASE :assetdb SET timezone TO 'UTC';
    CREATE USER :username WITH PASSWORD :password;
EOSQL
```

This will:

* Create the `assetdb` database
* Set its default timezone to UTC (recommended for consistency)
* Create a new user (`amass`) with the specified password

## 3. Enable Extensions and Grant Privileges

Next, connect to the new database and enable the required PostgreSQL extension and assign privileges to the Amass user.

```bash
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$AMASS_DB" <<-EOSQL
    \getenv username AMASS_USER

    CREATE EXTENSION pg_trgm SCHEMA public;

    GRANT USAGE ON SCHEMA public TO :username;
    GRANT CREATE ON SCHEMA public TO :username;
    GRANT ALL ON ALL TABLES IN SCHEMA public TO :username;
EOSQL
```

This will:

* Enable the `pg_trgm` extension (used by Amass for efficient fuzzy string matching)
* Grant the necessary privileges for Amass to create and manage data within the `public` schema

## 4. Update Your Amass Configuration

Once your database is set up, update your Amass `config.yaml` file with the connection string:

```yaml
options:
  # Be sure to replace the credentials with values matching your environment
  database: "postgres://amass:amass4OWASP@127.0.0.1:5432/assetdb"
```

??? info "Security Reminder"
    Avoid committing passwords to source control. Where possible, consider injecting the connection string using an environment variable (e.g., `${AMASS_DB_URI}`).

## 5. Test the Connection

You can test whether the Amass framework is successfully connecting to your PostgreSQL database by running a standard enumeration command:

```bash
amass enum -config config.yaml
```

If the configuration is correct, the collected data will be stored in the PostgreSQL backend you configured.

## ✅ You're Done!

Amass is now ready to store data in your PostgreSQL database. This enables you to persist, analyze, and query discovered assets using SQL or integrate with other tooling and dashboards.

## Troubleshooting Tips

* **Connection Refused?** Ensure PostgreSQL is listening on `127.0.0.1:5432` and that the database server is running.
* **Authentication Failed?** Double-check your environment variable values, especially the user and password.
* **Extension Errors?** Make sure the `pg_trgm` extension is available and installed. You can check with `\dx` in `psql`.

## See Also

* [Amass Configuration](../configuration/index.md)
* [PostgreSQL Documentation](https://www.postgresql.org/docs/current/index.html)
* [PostgreSQL `pg_trgm` Extension Docs](https://www.postgresql.org/docs/current/pgtrgm.html)
* [Managing Environment Variables Securely](https://direnv.net/)

## SQL Repository Implementation

## Purpose and Scope

The SQL Repository provides a relational database implementation of the `Repository` interface using GORM as the ORM layer. It supports PostgreSQL for production deployments and SQLite for embedded/development use cases. This document covers the architecture, initialization, and data storage approach of the SQL repository implementation.

For detailed information about specific operations:
- Entity CRUD operations: see [SQL Entity Operations](./postgres.md#sql-entity-operations)
- Edge management and querying: see [SQL Edge Operations](./postgres.md#sql-edge-operations)  
- Tag creation and retrieval: see [SQL Tag Management](./postgres.md#sql-tag-management)

For the Neo4j graph database implementation, see [Neo4j Repository](./triples.md#neo4j-repository).

---

## Repository Architecture

The SQL repository is implemented by the `sqlRepository` struct defined in . It wraps a GORM database connection and implements all methods of the `Repository` interface.

### Core Components

```mermaid
graph TB
    RepositoryInterface["repository.Repository<br/>Interface"]
    sqlRepository["sqlRepository<br/>struct"]
    GORMDB["*gorm.DB<br/>ORM Connection"]
    
    subgraph "Database Backends"
        PostgresDriver["postgres.Open()<br/>PostgreSQL Driver"]
        SQLiteDriver["sqlite.Open()<br/>SQLite Driver"]
    end
    
    subgraph "Storage Layer"
        PostgresDB[("PostgreSQL<br/>Database")]
        SQLiteDB[("SQLite<br/>File or Memory")]
    end
    
    RepositoryInterface -.->|"implements"| sqlRepository
    sqlRepository -->|"sql.db"| GORMDB
    sqlRepository -->|"sql.dbtype"| DBType["dbtype: string<br/>'postgres', 'sqlite', 'sqlite_memory'"]
    
    GORMDB -->|"uses"| PostgresDriver
    GORMDB -->|"uses"| SQLiteDriver
    
    PostgresDriver --> PostgresDB
    SQLiteDriver --> SQLiteDB
```

---

## Database Type Constants

The SQL repository supports three database configurations, identified by string constants:

| Constant | Value | Purpose |
|----------|-------|---------|
| `Postgres` | `"postgres"` | Production PostgreSQL deployment |
| `SQLite` | `"sqlite"` | File-based SQLite database |
| `SQLiteMemory` | `"sqlite_memory"` | In-memory SQLite for testing |

---

## Initialization Process

The `New` function creates and configures a SQL repository instance. It establishes the database connection with appropriate driver settings and connection pooling parameters.

### Factory Function

```mermaid
graph LR
    Client["Client Code"]
    NewFunc["sqlrepo.New(dbtype, dsn)"]
    NewDatabase["newDatabase(dbtype, dsn)"]
    
    subgraph "Database Creation"
        PostgresFunc["postgresDatabase(dsn)"]
        SQLiteFunc["sqliteDatabase(dsn, conns, idles)"]
    end
    
    sqlRepo["sqlRepository{<br/>db: *gorm.DB<br/>dbtype: string<br/>}"]
    
    Client -->|"'postgres', dsn"| NewFunc
    NewFunc --> NewDatabase
    NewDatabase -->|"dbtype='postgres'"| PostgresFunc
    NewDatabase -->|"dbtype='sqlite'<br/>dbtype='sqlite_memory'"| SQLiteFunc
    PostgresFunc -->|"*gorm.DB"| NewFunc
    SQLiteFunc -->|"*gorm.DB"| NewFunc
    NewFunc --> sqlRepo
    sqlRepo -->|"return"| Client
```

**Key Implementation Details:**

The factory function routes to database-specific initialization based on the `dbtype` parameter :

- **PostgreSQL**: Uses `gorm.Open(postgres.Open(dsn))` with connection pooling configured for production workloads 
- **SQLite (file)**: Uses `gorm.Open(sqlite.Open(dsn))` with 3 max connections and 5 max idle connections 
- **SQLite (memory)**: Uses the same driver but with increased limits (50 max connections, 100 max idle) for test performance 

---

## Connection Pooling Configuration

Each database backend is configured with specific connection pooling parameters to optimize performance and resource usage.

### PostgreSQL Connection Pool

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MaxIdleConns` | 5 | Maintains 5 idle connections for quick reuse |
| `MaxOpenConns` | 10 | Limits concurrent connections to 10 |
| `ConnMaxLifetime` | 1 hour | Recycles connections after 1 hour |
| `ConnMaxIdleTime` | 10 minutes | Closes idle connections after 10 minutes |

### SQLite Connection Pool

**File-based SQLite:**
- `MaxOpenConns`: 3
- `MaxIdleConns`: 5
- Same lifetime settings as PostgreSQL

**In-memory SQLite:**
- `MaxOpenConns`: 50
- `MaxIdleConns`: 100  
- Optimized for high-throughput testing scenarios

---

## Data Storage Model

The SQL repository stores graph data (entities and edges) in relational tables using JSON serialization for flexible content storage.

### Table Structure

```mermaid
erDiagram
    entities ||--o{ edges : "from_entity_id"
    entities ||--o{ edges : "to_entity_id"
    entities ||--o{ entity_tags : "entity_id"
    edges ||--o{ edge_tags : "edge_id"
    
    entities {
        uint64 entity_id PK
        string etype
        string content
        timestamp created_at
        timestamp updated_at
    }
    
    edges {
        uint64 edge_id PK
        string type
        string content
        uint64 from_entity_id FK
        uint64 to_entity_id FK
        timestamp created_at
        timestamp updated_at
    }
    
    entity_tags {
        uint64 tag_id PK
        uint64 entity_id FK
        string ttype
        string content
        timestamp created_at
        timestamp updated_at
    }
    
    edge_tags {
        uint64 tag_id PK
        uint64 edge_id FK
        string ttype
        string content
        timestamp created_at
        timestamp updated_at
    }
```

### GORM Model Structs

The repository uses internal GORM model structs (not shown in provided files but referenced by operations) that map to these tables:

- `Entity` struct: Maps to `entities` table
- `Edge` struct: Maps to `edges` table with foreign key constraints
- `EntityTag` struct: Maps to `entity_tags` table
- `EdgeTag` struct: Maps to `edge_tags` table

---

## JSON Content Serialization

All Open Asset Model objects (Assets, Relations, Properties) are serialized to JSON for storage in the `content` fields. This approach provides:

1. **Schema Flexibility**: Supports arbitrary asset types without schema migrations
2. **OAM Compatibility**: Preserves full fidelity of OAM objects
3. **Query Capability**: JSON operators enable content-based queries

### Serialization Flow

```mermaid
graph LR
    Asset["oam.Asset<br/>(Go struct)"]
    JSON1["asset.JSON()"]
    Content1["content: string<br/>(JSON)"]
    
    Relation["oam.Relation<br/>(Go struct)"]
    JSON2["relation.JSON()"]
    Content2["content: string<br/>(JSON)"]
    
    Property["oam.Property<br/>(Go struct)"]
    JSON3["property.JSON()"]
    Content3["content: string<br/>(JSON)"]
    
    Asset --> JSON1 --> Content1
    Relation --> JSON2 --> Content2
    Property --> JSON3 --> Content3
    
    Content1 --> Store1["Entity.Content"]
    Content2 --> Store2["Edge.Content"]
    Content3 --> Store3["EntityTag.Content<br/>EdgeTag.Content"]
```

**Examples in Code:**

- Entity serialization: 
- Edge serialization: 
- Deserialization: 

---

## GORM Query Patterns

The SQL repository uses GORM's query builder extensively throughout its operations. Common patterns include:

### Basic CRUD Operations

| Operation | GORM Method | Example Location |
|-----------|-------------|------------------|
| Create | `db.Create(&model)` |  |
| Read by ID | `db.First(&model)` |  |
| Update | `db.Save(&model)` |  |
| Delete | `db.Delete(&model)` |  |

### Query Chaining

The repository builds complex queries by chaining GORM methods:

```mermaid
graph LR
    DB["sql.db"]
    Where1["Where('etype = ?', type)"]
    Where2["Where('updated_at >= ?', since)"]
    Find["Find(&entities)"]
    
    DB --> Where1
    Where1 --> Where2
    Where2 --> Find
```

**Example:** Finding entities by type with temporal filtering at 

---

## Duplicate Prevention

The SQL repository implements duplicate detection logic to prevent redundant data storage.

### Entity Deduplication

When creating an entity, the repository:

1. Searches for existing entities with matching content 
2. If found, updates the existing entity's timestamp instead of creating a new one 
3. Uses GORM's `Save` method which performs an upsert operation 

### Edge Deduplication

Edge creation uses the `isDuplicateEdge` helper function :

1. Queries existing outgoing edges from the source entity
2. Checks for matching destination entity and relation content using `reflect.DeepEqual`
3. If duplicate found, updates the timestamp via `edgeSeen` 
4. Returns the existing edge instead of creating a new one

---

## Timestamp Management

All entities and edges track two timestamps:

- `created_at`: When the record was first created (immutable after creation)
- `updated_at`: When the record was last seen/updated (modified on subsequent observations)

The repository uses UTC timezone consistently and converts to local time when returning results to clients .

---

## Repository Interface Methods

The `sqlRepository` implements all methods defined by the `Repository` interface. Operations are organized into three categories:

### Entity Operations

- `CreateEntity(*types.Entity) (*types.Entity, error)`
- `CreateAsset(oam.Asset) (*types.Entity, error)` - Convenience wrapper
- `FindEntityById(string) (*types.Entity, error)`
- `FindEntitiesByContent(oam.Asset, time.Time) ([]*types.Entity, error)`
- `FindEntitiesByType(oam.AssetType, time.Time) ([]*types.Entity, error)`
- `DeleteEntity(string) error`

Detailed documentation: [SQL Entity Operations](./postgres.md#sql-entity-operations)

### Edge Operations

- `CreateEdge(*types.Edge) (*types.Edge, error)`
- `FindEdgeById(string) (*types.Edge, error)`
- `IncomingEdges(*types.Entity, time.Time, ...string) ([]*types.Edge, error)`
- `OutgoingEdges(*types.Entity, time.Time, ...string) ([]*types.Edge, error)`
- `DeleteEdge(string) error`

Detailed documentation: [SQL Edge Operations](./postgres.md#sql-edge-operations)

### Tag Operations

- `CreateEntityTag(*types.EntityTag) (*types.EntityTag, error)`
- `GetEntityTags(*types.Entity, time.Time) ([]*types.EntityTag, error)`
- `CreateEdgeTag(*types.EdgeTag) (*types.EdgeTag, error)`
- `GetEdgeTags(*types.Edge, time.Time) ([]*types.EdgeTag, error)`

Detailed documentation: [SQL Tag Management](./postgres.md#sql-tag-management)

### Utility Methods

- `Close() error` - Closes the database connection 
- `GetDBType() string` - Returns the database type constant 

---

## Error Handling

The SQL repository propagates GORM errors to callers with minimal wrapping. Common error scenarios include:

| Scenario | Error Source | Example Location |
|----------|--------------|------------------|
| Record not found | `gorm.ErrRecordNotFound` |  |
| ID parsing failure | `strconv.ParseUint` |  |
| Database constraint violation | GORM/database driver |  |
| JSON serialization failure | `asset.JSON()` |  |

The repository also returns custom errors for semantic issues:
- `"zero entities found"` when queries return no results 
- `"failed input validation checks"` for nil parameters 
- OAM validation errors for invalid relationships 

---

## Performance Considerations

### Query Optimization

The SQL repository relies on proper database indexing for performance. Key indexes should include:

- Primary keys on `entity_id`, `edge_id`, `tag_id`
- Foreign key indexes on `from_entity_id`, `to_entity_id` in edges table
- Index on `etype` column for type-based queries
- Index on `updated_at` for temporal queries
- JSON path indexes for content-based queries (database-specific)

These indexes are created by the migration system (see [SQL Schema Migrations](./migrations.md#sql-schema-migrations)).

### Connection Pooling

The conservative connection limits (5-10 for PostgreSQL, 3 for SQLite) balance resource usage with throughput. For high-concurrency scenarios, consider:

- Wrapping the repository with the caching layer (see [Caching System](./caching.md))
- Adjusting pool sizes at

### SQL Entity Operations

This page documents entity CRUD (Create, Read, Delete) operations in the SQL repository implementation. It covers how entities representing assets are created, queried, and managed in PostgreSQL and SQLite databases using GORM. For edge (relationship) operations, see [SQL Edge Operations](./postgres.md#sql-edge-operations). For entity tag management, see [SQL Tag Management](./postgres.md#sql-tag-management).

### Overview

The SQL repository implements entity operations defined in the `Repository` interface using GORM as the ORM layer. Entities are stored in the `entities` table with JSON-serialized content. The implementation handles duplicate detection, timestamp management, and conversion between database records and `types.Entity` objects.

### Entity Storage Model

#### Database Schema

Entities in SQL repositories are stored using the `Entity` struct, which maps to the `entities` table:

| Field | Type | Purpose |
|-------|------|---------|
| `ID` | `uint64` | Auto-incrementing primary key |
| `Type` | `string` | Asset type (e.g., "FQDN", "IPAddress") from `oam.AssetType()` |
| `Content` | `string` | JSON-serialized asset data from `oam.Asset.JSON()` |
| `CreatedAt` | `time.Time` | First creation timestamp |
| `UpdatedAt` | `time.Time` | Last seen/update timestamp |

The `Content` field stores the complete asset as JSON, allowing flexible storage of any asset type defined in the Open Asset Model.

```mermaid
graph TB
    subgraph "types Package"
        TypesEntity["types.Entity<br/>ID: string<br/>CreatedAt: time.Time<br/>LastSeen: time.Time<br/>Asset: oam.Asset"]
    end
    
    subgraph "sqlrepo Package"
        SQLEntity["Entity struct<br/>ID: uint64<br/>Type: string<br/>Content: string (JSON)<br/>CreatedAt: time.Time<br/>UpdatedAt: time.Time"]
        
        Parse["Parse() method<br/>Deserializes JSON<br/>to oam.Asset"]
        
        JSONQuery["JSONQuery() method<br/>Builds GORM where clause"]
    end
    
    subgraph "Database"
        EntitiesTable["entities table<br/>PostgreSQL or SQLite"]
    end
    
    TypesEntity -->|"CreateEntity()"| SQLEntity
    SQLEntity -->|"GORM Save()"| EntitiesTable
    EntitiesTable -->|"GORM Find()"| SQLEntity
    SQLEntity -->|"Parse()"| TypesEntity
    
    SQLEntity -.->|"Uses"| Parse
    SQLEntity -.->|"Uses"| JSONQuery
```

### Create Operations

#### CreateEntity

The `CreateEntity` method persists a `types.Entity` to the database. It includes sophisticated duplicate detection logic that updates existing entities rather than creating duplicates.

```mermaid
flowchart TD
    Start["CreateEntity(input *types.Entity)"]
    Serialize["Serialize input.Asset to JSON<br/>jsonContent, err := input.Asset.JSON()"]
    CreateStruct["Create Entity struct<br/>Type = input.Asset.AssetType()<br/>Content = jsonContent"]
    CheckDup["FindEntitiesByContent()<br/>Check for existing entity"]
    
    DupExists{{"Duplicate<br/>exists?"}}
    SameType{{"Same<br/>AssetType?"}}
    UpdateExisting["Update existing:<br/>entity.ID = existing.ID<br/>entity.UpdatedAt = now"]
    SetNew["Set timestamps:<br/>entity.CreatedAt = now or input.CreatedAt<br/>entity.UpdatedAt = now or input.LastSeen"]
    
    Save["db.Save(&entity)<br/>GORM upsert operation"]
    Convert["Convert to types.Entity<br/>ID: strconv.FormatUint()<br/>Timestamps: UTC to Local"]
    Return["Return *types.Entity"]
    
    Start --> Serialize
    Serialize --> CreateStruct
    CreateStruct --> CheckDup
    CheckDup --> DupExists
    DupExists -->|"Yes"| SameType
    DupExists -->|"No"| SetNew
    SameType -->|"Yes"| UpdateExisting
    SameType -->|"No"| SetNew
    UpdateExisting --> Save
    SetNew --> Save
    Save --> Convert
    Convert --> Return
```

**Key behaviors:**
- **Duplicate detection:** Queries `FindEntitiesByContent` to check if entity already exists 
- **Update vs Insert:** If duplicate found with matching `AssetType`, updates `UpdatedAt` timestamp but preserves `ID` and `CreatedAt` 
- **GORM Save:** Uses `db.Save()` which performs upsert (insert or update based on primary key) 
- **ID conversion:** Database `uint64` ID converted to string for `types.Entity` 
- **Timezone handling:** Timestamps stored in UTC, returned in local time 

#### CreateAsset

The `CreateAsset` method is a convenience wrapper around `CreateEntity`:

```go
func (sql *sqlRepository) CreateAsset(asset oam.Asset) (*types.Entity, error) {
    return sql.CreateEntity(&types.Entity{Asset: asset})
}
```

It accepts an `oam.Asset` directly and wraps it in a `types.Entity` before calling `CreateEntity`.

### Query Operations

#### FindEntityById

Retrieves a single entity by its string ID.

| Operation | Implementation |
|-----------|----------------|
| **Input** | `id string` - Entity ID as string |
| **Conversion** | `strconv.ParseUint(id, 10, 64)` to convert to `uint64` |
| **Query** | `db.First(&entity)` - GORM query by primary key |
| **Parsing** | `entity.Parse()` - Deserializes JSON content to `oam.Asset` |
| **Output** | `*types.Entity` with populated `Asset` field |

**Error cases:**
- Invalid ID format (not a valid uint64)
- Entity not found in database
- JSON parsing failure

#### FindEntitiesByContent

Searches for entities matching specific asset content, with optional time filtering.

```mermaid
graph TD
    Input["FindEntitiesByContent(assetData, since)"]
    SerializeInput["Serialize input asset to JSON"]
    BuildQuery["entity.JSONQuery()<br/>Build JSON matching query"]
    
    ApplyFilters["tx.Where('etype = ?', type)"]
    CheckSince{{"since.IsZero()?"}}
    AddTimeFilter["tx.Where('updated_at >= ?', since.UTC())"]
    
    Execute["tx.Find(&entities)<br/>Execute GORM query"]
    Parse["Parse each Entity.Content<br/>to oam.Asset"]
    BuildResults["Build []*types.Entity slice"]
    Return["Return results"]
    
    Input --> SerializeInput
    SerializeInput --> BuildQuery
    BuildQuery --> ApplyFilters
    ApplyFilters --> CheckSince
    CheckSince -->|"No"| AddTimeFilter
    CheckSince -->|"Yes"| Execute
    AddTimeFilter --> Execute
    Execute --> Parse
    Parse --> BuildResults
    BuildResults --> Return
```

**Key features:**
- **Content matching:** Uses `JSONQuery()` method to build database-specific JSON query 
- **Type filtering:** Always filters by `etype` field 
- **Time filtering:** Optional `since` parameter filters by `updated_at >= since` 
- **Zero value handling:** If `since.IsZero()`, time filter is skipped 

#### FindEntitiesByType

Retrieves all entities of a specific asset type, with optional time filtering.

| Parameter | Type | Purpose |
|-----------|------|---------|
| `atype` | `oam.AssetType` | Asset type to filter (e.g., "FQDN", "IPAddress") |
| `since` | `time.Time` | Optional time filter for `updated_at >= since` |

**Query variations:**

```go
// Without time filter (since.IsZero())
db.Where("etype = ?", atype).Find(&entities)

// With time filter
db.Where("etype = ? AND updated_at >= ?", atype, since.UTC()).Find(&entities)
```

### Delete Operations

#### DeleteEntity

Removes an entity by ID from the database.

```mermaid
sequenceDiagram
    participant Client
    participant DeleteEntity
    participant GORM
    participant Database
    
    Client->>DeleteEntity: DeleteEntity(id string)
    DeleteEntity->>DeleteEntity: strconv.ParseUint(id, 10, 64)
    DeleteEntity->>GORM: db.Delete(&Entity{ID: entityId})
    GORM->>Database: DELETE FROM entities WHERE id = ?
    Database-->>GORM: Rows affected
    GORM-->>DeleteEntity: result.Error
    DeleteEntity-->>Client: error or nil
```

**Implementation details:**
- Converts string ID to `uint64` 
- Uses GORM's `Delete()` method with primary key 
- Returns error if conversion fails or deletion fails
- Does not check if entity exists before deletion

### Duplicate Handling Strategy

The SQL repository implements intelligent duplicate detection in `CreateEntity`:

```mermaid
graph LR
    subgraph "Duplicate Detection Flow"
        Call["CreateEntity called<br/>with new asset"]
        Query["FindEntitiesByContent()<br/>Search existing"]
        
        Check{{"Matching entity<br/>found?"}}
        TypeCheck{{"Same<br/>AssetType?"}}
        
        Update["Update existing:<br/>- Keep same ID<br/>- Keep CreatedAt<br/>- Update UpdatedAt"]
        Create["Create new:<br/>- New ID<br/>- Set CreatedAt<br/>- Set UpdatedAt"]
        
        Call --> Query
        Query --> Check
        Check -->|"Yes"| TypeCheck
        Check -->|"No"| Create
        TypeCheck -->|"Yes"| Update
        TypeCheck -->|"No"| Create
    end
```

**Rationale:** This prevents duplicate entities with identical content while updating the `LastSeen` timestamp to track recency. This is critical for time-based queries in discovery systems like OWASP Amass.

**Test validation:** The test `TestLastSeenUpdates` verifies that calling `CreateAsset` twice with the same asset updates `LastSeen` while preserving `ID` and `CreatedAt` .

### JSON Serialization

#### Encoding: Asset to JSON

The `CreateEntity` method serializes `oam.Asset` to JSON:

```go
jsonContent, err := input.Asset.JSON()
if err != nil {
    return nil, err
}
```

The JSON string is stored in the `Content` field of the database entity .

#### Decoding: JSON to Asset

The `Parse()` method (implementation in `Entity` struct) deserializes JSON back to `oam.Asset`:

```go
assetData, err := entity.Parse()
if err != nil {
    return nil, err
}
```

This method is called in all query operations to reconstruct the asset from database storage .

#### JSONQuery Method

The `JSONQuery()` method builds database-specific WHERE clauses for JSON content matching. This is used by `FindEntitiesByContent` to efficiently query entities with specific content .

### Time Handling

The SQL repository performs careful timezone conversions to ensure consistency:

#### Storage: Local/Input to UTC

```go
// For new entities
if input.CreatedAt.IsZero() {
    entity.CreatedAt = time.Now().UTC()
} else {
    entity.CreatedAt = input.CreatedAt.UTC()
}

if input.LastSeen.IsZero() {
    entity.UpdatedAt = time.Now().UTC()
} else {
    entity.UpdatedAt = input.LastSeen.UTC()
}
```

All timestamps are converted to UTC before storage .

#### Retrieval: UTC to Local

```go
return &types.Entity{
    ID:        strconv.FormatUint(entity.ID, 10),
    CreatedAt: entity.CreatedAt.In(time.UTC).Local(),
    LastSeen:  entity.UpdatedAt.In(time.UTC).Local(),
    Asset:     input.Asset,
}
```

Timestamps are converted back to local time when returning entities .

**Rationale:** Storing in UTC ensures consistency across different database servers and clients in different timezones. Converting to local time on retrieval maintains compatibility with client expectations.

### Integration with GORM

All SQL entity operations use GORM methods:

| GORM Method | Purpose | Used In |
|-------------|---------|---------|
| `db.Save(&entity)` | Insert or update based on primary key | `CreateEntity` |
| `db.First(&entity)` | Query single record by primary key | `FindEntityById` |
| `db.Where(...).Find(&entities)` | Query multiple records with conditions | `FindEntitiesByContent`, `FindEntitiesByType` |
| `db.Delete(&entity)` | Delete record by primary key | `DeleteEntity` |

The `sqlRepository` struct contains a `*gorm.DB` field that executes these operations against PostgreSQL or SQLite databases configured at initialization.

### SQL Edge Operations

### Purpose and Scope

This document details the SQL repository implementation for edge operations. Edges represent directed relationships between entities in the property graph model. The SQL implementation uses GORM to manage edges stored in relational databases (PostgreSQL and SQLite).

This page covers edge creation, querying, retrieval, and deletion operations. For entity management, see [SQL Entity Operations](./postgres.md#sql-entity-operations). For edge tag operations, see [SQL Tag Management](./postgres.md#sql-tag-management). For the Neo4j graph database implementation of edge operations, see [Neo4j Edge Operations](./triples.md#neo4j-edge-operations).

---

### Edge Table Structure

The SQL repository stores edges in an `edges` table with the following structure:

| Column | Type | Description |
|--------|------|-------------|
| `edge_id` | uint64 | Primary key, auto-incremented |
| `type` | string | Relation type from OAM |
| `content` | JSON | Serialized relation data |
| `from_entity_id` | uint64 | Foreign key to source entity |
| `to_entity_id` | uint64 | Foreign key to destination entity |
| `created_at` | timestamp | When the edge was first created |
| `updated_at` | timestamp | Last seen timestamp |

The `Edge` struct in the SQL repository maps to this table structure:

```
type Edge struct {
    ID           uint64
    Type         string
    Content      []byte
    FromEntityID uint64
    ToEntityID   uint64
    CreatedAt    time.Time
    UpdatedAt    time.Time
}
```

---

### Edge Creation Flow

#### CreateEdge Method

```mermaid
flowchart TD
    Start["CreateEdge(edge)"]
    Validate["Validate input fields<br/>(line 23-26)"]
    TaxCheck["Validate against OAM taxonomy<br/>oam.ValidRelationship()<br/>(line 28-32)"]
    DupCheck["isDuplicateEdge()<br/>(line 41-43)"]
    Found{{"Duplicate<br/>found?"}}
    ParseFrom["Parse FromEntity.ID<br/>(line 45-48)"]
    ParseTo["Parse ToEntity.ID<br/>(line 50-53)"]
    Serialize["Serialize Relation to JSON<br/>(line 55-58)"]
    Create["Create Edge struct<br/>with timestamps<br/>(line 60-71)"]
    Insert["sql.db.Create(&r)<br/>(line 73-76)"]
    Convert["toEdge(r)<br/>(line 77)"]
    Return["Return edge"]
    
    Start --> Validate
    Validate --> TaxCheck
    TaxCheck --> DupCheck
    DupCheck --> Found
    Found -->|"Yes"| Return
    Found -->|"No"| ParseFrom
    ParseFrom --> ParseTo
    ParseTo --> Serialize
    Serialize --> Create
    Create --> Insert
    Insert --> Convert
    Convert --> Return
    
    style DupCheck fill:#f9f9f9
    style Found fill:#f9f9f9
```

**Diagram: Edge Creation Process**

The `CreateEdge` method implements comprehensive validation and duplicate detection:

1. **Input Validation** : Verifies that the edge, relation, and both entities are non-nil
2. **Taxonomy Validation** : Calls `oam.ValidRelationship()` to ensure the relationship is valid according to the Open Asset Model taxonomy
3. **Duplicate Detection** : Checks if an identical edge already exists
4. **Timestamp Management** : Uses provided `LastSeen` timestamp or defaults to current UTC time
5. **Entity ID Parsing** : Converts string entity IDs to uint64
6. **Content Serialization** : Serializes the relation to JSON format
7. **Database Insert** : Uses GORM to insert the edge record

---

### Duplicate Edge Detection

#### isDuplicateEdge Logic

```mermaid
flowchart TD
    Start["isDuplicateEdge(edge, updated)"]
    Query["OutgoingEdges(FromEntity)<br/>(line 85)"]
    Iterate["Iterate through outgoing edges<br/>(line 86-98)"]
    Match{{"ToEntity.ID matches<br/>AND<br/>Relation content matches?"}}
    Update["edgeSeen(out, updated)<br/>(line 88)"]
    Fetch["FindEdgeById(out.ID)<br/>(line 90)"]
    ReturnDup["Return edge, true"]
    ReturnNew["Return nil, false"]
    
    Start --> Query
    Query --> Iterate
    Iterate --> Match
    Match -->|"Yes"| Update
    Update --> Fetch
    Fetch --> ReturnDup
    Match -->|"No"| Iterate
    Iterate -->|"No more edges"| ReturnNew
    
    style Match fill:#f9f9f9
```

**Diagram: Duplicate Edge Detection Mechanism**

The duplicate detection mechanism prevents redundant edges in the database:

- **Query Existing Edges** : Retrieves all outgoing edges from the source entity with the same label
- **Deep Comparison** : Compares both the destination entity ID and the relation content using `reflect.DeepEqual`
- **Update Timestamp** : If a duplicate is found, updates its `updated_at` timestamp via `edgeSeen()`
- **Return Existing** : Fetches and returns the existing edge instead of creating a new one

This approach ensures that re-discovering the same relationship updates the temporal information without creating duplicate records.

---

### Edge Timestamp Management

#### edgeSeen Method

The `edgeSeen` method updates the `updated_at` timestamp for an existing edge:

```mermaid
flowchart LR
    Input["Edge + new timestamp"]
    ParseID["Parse edge.ID<br/>(line 105-108)"]
    Serialize["Serialize Relation to JSON<br/>(line 110-113)"]
    ParseFrom["Parse FromEntity.ID<br/>(line 115-118)"]
    ParseTo["Parse ToEntity.ID<br/>(line 120-123)"]
    BuildStruct["Build Edge struct<br/>with new UpdatedAt<br/>(line 125-133)"]
    Save["sql.db.Save(&r)<br/>(line 135-138)"]
    
    Input --> ParseID
    ParseID --> Serialize
    Serialize --> ParseFrom
    ParseFrom --> ParseTo
    ParseTo --> BuildStruct
    BuildStruct --> Save
```

**Diagram: Edge Timestamp Update Flow**

The method preserves the original `created_at` timestamp while updating `updated_at` to reflect the most recent observation of the relationship.

---

### Querying Edges

#### Incoming and Outgoing Edge Queries

Both `IncomingEdges` and `OutgoingEdges` methods support:
- Temporal filtering via the `since` parameter
- Label filtering to retrieve edges of specific relation types
- Optional label filtering (returns all edges if no labels specified)

##### IncomingEdges Query Structure

```mermaid
flowchart TD
    Start["IncomingEdges(entity, since, labels...)"]
    ParseID["Parse entity.ID to int64<br/>(line 157-160)"]
    CheckSince{{"since.IsZero()?"}}
    QueryAll["WHERE to_entity_id = ?<br/>(line 165)"]
    QueryTime["WHERE to_entity_id = ?<br/>AND updated_at >= ?<br/>(line 167)"]
    Filter{{"labels<br/>provided?"}}
    FilterLoop["Filter by relation label<br/>(line 174-186)"]
    NoFilter["Use all edges<br/>(line 188)"]
    Return["Return filtered edges<br/>via toEdges()<br/>(line 194)"]
    
    Start --> ParseID
    ParseID --> CheckSince
    CheckSince -->|"Yes"| QueryAll
    CheckSince -->|"No"| QueryTime
    QueryAll --> Filter
    QueryTime --> Filter
    Filter -->|"Yes"| FilterLoop
    Filter -->|"No"| NoFilter
    FilterLoop --> Return
    NoFilter --> Return
    
    style CheckSince fill:#f9f9f9
    style Filter fill:#f9f9f9
```

**Diagram: IncomingEdges Query Flow**

##### OutgoingEdges Query Structure

The `OutgoingEdges` method follows the same pattern but queries on `from_entity_id` instead:

| Query Parameter | SQL WHERE Clause |
|----------------|------------------|
| No time filter | `from_entity_id = ?` |
| With time filter | `from_entity_id = ? AND updated_at >= ?` |

**Label Filtering Implementation:**

When labels are provided :
1. Parse each edge's JSON content to extract the relation
2. Compare the relation's label against the requested labels
3. Include the edge only if its label matches

---

### Edge Retrieval and Deletion

#### FindEdgeById

The `FindEdgeById` method retrieves a single edge by its ID:

```
func FindEdgeById(id string) (*types.Edge, error)
```

Implementation details :
- Parses the string ID
- Queries using `WHERE edge_id = ?`
- Converts the database `Edge` to `types.Edge` via `toEdge()`

#### DeleteEdge

The `DeleteEdge` method removes an edge from the database:

```
func DeleteEdge(id string) error
```

Implementation :
- Parses the string ID to uint64
- Delegates to `deleteEdges()` which executes: `DELETE FROM edges WHERE edge_id IN ?`

The `deleteEdges` helper method  accepts a slice of IDs, enabling batch deletion operations.

---

### Type Conversion Functions

#### Database to Domain Model Conversion

```mermaid
flowchart LR
    DB["Edge<br/>(database struct)"]
    Parse["Parse JSON content<br/>to oam.Relation<br/>(line 260)"]
    Build["Build types.Edge<br/>with converted fields<br/>(line 265-278)"]
    Domain["types.Edge<br/>(domain model)"]
    
    DB --> Parse
    Parse --> Build
    Build --> Domain
    
    Note1["FromEntity and ToEntity<br/>contain only IDs,<br/>not full asset content<br/>(line 272-276)"]
    
    Build -.-> Note1
```

**Diagram: Edge Type Conversion**

#### toEdge Function

The `toEdge` function  converts a database `Edge` struct to a `types.Edge`:

- Parses the JSON `Content` field back to an `oam.Relation`
- Converts numeric timestamps to `time.Time` in local timezone
- Creates entity references with IDs only (does not join to fetch full entity data)
- Converts uint64 IDs to string format

#### toEdges Function

The `toEdges` helper  applies `toEdge` to a slice of edges, filtering out any that fail to parse.

**Important Note:** The converted `FromEntity` and `ToEntity` objects contain only the ID field. Full entity content is not joined during edge queries for performance reasons. To retrieve complete entity data, use `FindEntityById()` on the entity IDs.

---

### Integration Testing Examples

The test suite demonstrates typical edge operations:

#### Basic Edge Creation and Query

From :

```
edge := &types.Edge{
    Relation:   tc.relation,
    FromEntity: sourceEntity,
    ToEntity:   destinationEntity,
}

e, err := store.CreateEdge(edge)
// Query incoming edges
incoming, err := store.IncomingEdges(destinationEntity, start, tc.relation.Label())
// Query outgoing edges  
outgoing, err := store.OutgoingEdges(sourceEntity, start, tc.relation.Label())
```

#### Duplicate Handling

From :

```
// Store duplicate relation - last_seen is updated
rr, err := store.CreateEdge(edge2)
// Verify LastSeen timestamp increased
assert(rr.LastSeen > originalEdge.LastSeen)
```

#### Unfiltered Edge Queries

From :

```
// Retrieve all outgoing edges (no label filter)
outs, err := store.OutgoingEdges(sourceEntity, time.Time{})
// Returns all edges regardless of relation type
```

---

### Error Handling

Edge operations return errors for the following conditions:

| Operation | Error Condition | Error Type |
|-----------|----------------|------------|
| `CreateEdge` | Nil input fields | "failed input validation checks" |
| `CreateEdge` | Invalid taxonomy relationship | "%s -%s-> %s is not valid in the taxonomy" |
| `CreateEdge` | Entity ID parse failure | Parse error |
| `CreateEdge` | JSON serialization failure | Serialization error |
| `CreateEdge` | Database insert failure | GORM error |
| `IncomingEdges` | Entity ID parse failure | Parse error |
| `IncomingEdges` | Zero edges found | "zero edges found" |
| `OutgoingEdges` | Entity ID parse failure | Parse error |
| `OutgoingEdges` | Zero edges found | "zero edges found" |
| `FindEdgeById` | Edge not found | GORM error (record not found) |
| `DeleteEdge` | ID parse failure | Parse error |
| `DeleteEdge` | Database delete failure | GORM error |

---

### Performance Considerations

#### Query Optimization

1. **Indexed Lookups:** The `from_entity_id` and `to_entity_id` columns should be indexed for efficient edge traversal queries
2. **Time-based Filtering:** The `updated_at` column enables temporal queries for incremental data retrieval
3. **Label Filtering:** Performed in-memory after database query, requires parsing JSON content

#### Duplicate Detection Cost

The `isDuplicateEdge` check  queries all outgoing edges with the same label and performs deep equality checks. For entities with many outgoing edges, this can be expensive. The cost is traded off against preventing duplicate records.

#### Lazy Entity Loading

Edge queries return entity references with IDs only, avoiding JOIN operations. This design improves query performance but requires separate queries to fetch full entity data when needed.

### SQL Tag Management

This document details how the SQL repository implementation manages entity and edge tags. Tags are metadata containers that store OAM properties (from the Open Asset Model) as JSON content attached to entities and edges. This page covers tag creation, retrieval, content-based searching, duplicate handling, and deletion.

For entity and edge operations themselves, see [SQL Entity Operations](./postgres.md#sql-entity-operations) and [SQL Edge Operations](./postgres.md#sql-edge-operations). For tag management in Neo4j, see [Neo4j Tag Management](./triples.md#neo4j-tag-management).

---

### Overview

Tags in the SQL repository serve as a flexible metadata system for attaching properties to both entities and edges. Each tag wraps an `oam.Property` object, serializes it to JSON, and stores it in the database with timestamp tracking. The system prevents duplicate tags and supports content-based queries.

---

### Database Schema and Core Structures

The SQL repository uses two separate tables for tags: `entity_tags` and `edge_tags`. Both follow a similar structure, storing the property type, JSON content, and foreign key references.

```mermaid
erDiagram
    entities ||--o{ entity_tags : "has many"
    edges ||--o{ edge_tags : "has many"
    
    entities {
        uint64 id PK
        string atype
        string content
        timestamp created_at
        timestamp updated_at
    }
    
    entity_tags {
        uint64 id PK
        string ttype
        string content
        uint64 entity_id FK
        timestamp created_at
        timestamp updated_at
    }
    
    edges {
        uint64 id PK
        string rtype
        string content
        uint64 from_entity_id FK
        uint64 to_entity_id FK
        timestamp created_at
        timestamp updated_at
    }
    
    edge_tags {
        uint64 id PK
        string ttype
        string content
        uint64 edge_id FK
        timestamp created_at
        timestamp updated_at
    }
```

#### Internal Tag Structures

The `EntityTag` and `EdgeTag` structs are internal GORM models that map to database tables:

| Field | Type | Description |
|-------|------|-------------|
| `ID` | `uint64` | Auto-incrementing primary key |
| `Type` | `string` | The property type (e.g., "simple_property") |
| `Content` | `string` | JSON-serialized property data |
| `EntityID` / `EdgeID` | `uint64` | Foreign key reference |
| `CreatedAt` | `time.Time` | Initial creation timestamp |
| `UpdatedAt` | `time.Time` | Last seen timestamp |

These internal structs are converted to `types.EntityTag` and `types.EdgeTag` for external API consumption.

---

### Entity Tag Operations

#### Creating Entity Tags

The `CreateEntityTag` function persists property metadata for an entity. It serializes the OAM property to JSON and implements duplicate detection logic.

```mermaid
flowchart TD
    Start["CreateEntityTag(entity, input)"]
    ParseID["Parse entity.ID to uint64"]
    Serialize["Serialize input.Property to JSON"]
    CreateStruct["Create EntityTag struct<br/>with Type, Content, EntityID"]
    
    CheckDup["GetEntityTags(entity, time.Time{}, prop.Name())"]
    DupFound{"Duplicates<br/>found?"}
    
    IterateDups["Iterate through existing tags"]
    MatchFound{"PropertyType &<br/>Value match?"}
    UpdateID["Set tag.ID = existing.ID<br/>Set tag.CreatedAt = existing.CreatedAt<br/>Set tag.UpdatedAt = now()"]
    
    SetNew["Set tag.CreatedAt from input<br/>or now()<br/>Set tag.UpdatedAt from input.LastSeen<br/>or now()"]
    
    Save["sql.db.Save(&tag)"]
    Return["Return types.EntityTag"]
    
    Start --> ParseID
    ParseID --> Serialize
    Serialize --> CreateStruct
    CreateStruct --> CheckDup
    CheckDup --> DupFound
    
    DupFound -->|Yes| IterateDups
    IterateDups --> MatchFound
    MatchFound -->|Yes| UpdateID
    MatchFound -->|No| IterateDups
    UpdateID --> Save
    
    DupFound -->|No| SetNew
    SetNew --> Save
    Save --> Return
```

**Key behaviors:**

1. **Duplicate Prevention**: The function queries existing tags with the same name 
2. **Type and Value Matching**: Duplicates are identified by matching `PropertyType()` and `Value()` 
3. **Update vs Insert**: Duplicates update `UpdatedAt` while preserving `CreatedAt`; new tags set both timestamps 
4. **GORM Save**: Uses `Save()` to perform INSERT or UPDATE based on whether `ID` is set 

#### Convenience Wrapper

The `CreateEntityProperty` function provides a simpler interface when you only have an `oam.Property`:

```go
// Wrapper that creates EntityTag from Property
func (sql *sqlRepository) CreateEntityProperty(entity *types.Entity, prop oam.Property) (*types.EntityTag, error)
```

#### Finding Entity Tags by ID

The `FindEntityTagById` function retrieves a single tag by its unique identifier:

```mermaid
flowchart LR
    Input["id (string)"]
    Parse["strconv.ParseUint(id, 10, 64)"]
    Query["sql.db.First(&tag)"]
    ParseContent["tag.Parse()"]
    Convert["Convert to types.EntityTag"]
    Output["Return *types.EntityTag"]
    
    Input --> Parse --> Query --> ParseContent --> Convert --> Output
```

#### Content-Based Tag Searching

The `FindEntityTagsByContent` function enables searching for tags by property content. It uses JSON field extraction to query specific property values.

```mermaid
flowchart TD
    Input["FindEntityTagsByContent(prop, since)"]
    Serialize["prop.JSON()"]
    CreateTag["Create EntityTag with<br/>Type and Content"]
    
    BuildQueries["tag.NameJSONQuery()<br/>tag.ValueJSONQuery()"]
    
    BaseQuery["tx = sql.db.Where('ttype = ?', tag.Type)"]
    SinceCheck{"since.IsZero()?"}
    AddSince["tx.Where('updated_at >= ?', since.UTC())"]
    
    Execute["tx.Where(nameQuery).Where(valueQuery).Find(&tags)"]
    Parse["Parse each tag.Content to Property"]
    Convert["Convert to []*types.EntityTag"]
    Return["Return results"]
    
    Input --> Serialize --> CreateTag --> BuildQueries
    BuildQueries --> BaseQuery --> SinceCheck
    SinceCheck -->|No| AddSince
    SinceCheck -->|Yes| Execute
    AddSince --> Execute
    Execute --> Parse --> Convert --> Return
```

The `NameJSONQuery()` and `ValueJSONQuery()` methods generate database-specific JSON extraction queries for PostgreSQL and SQLite. This allows efficient content filtering at the database level.

#### Retrieving All Entity Tags

The `GetEntityTags` function retrieves all tags for a specific entity with optional filtering:

**Function Signature:**
```go
func (sql *sqlRepository) GetEntityTags(entity *types.Entity, since time.Time, names ...string) ([]*types.EntityTag, error)
```

**Parameters:**
- `entity`: The entity whose tags to retrieve
- `since`: If not zero, only returns tags with `updated_at >= since`
- `names`: Optional property names to filter by

**Query Logic:**

| Condition | Query |
|-----------|-------|
| `since.IsZero()` | `WHERE entity_id = ?` |
| `!since.IsZero()` | `WHERE entity_id = ? AND updated_at >= ?` |

After database retrieval, the function filters results by property name if `names` are provided .

#### Deleting Entity Tags

The `DeleteEntityTag` function removes a tag by its ID:

```go
func (sql *sqlRepository) DeleteEntityTag(id string) error
```

It parses the string ID to `uint64`, creates an `EntityTag` struct with that ID, and uses GORM's `Delete()` method.

---

### Edge Tag Operations

Edge tag operations mirror entity tag operations but target edge relationships instead of entities.

#### Creating Edge Tags

The `CreateEdgeTag` function follows the same pattern as `CreateEntityTag`:

```mermaid
graph TB
    subgraph "CreateEdgeTag Flow"
        A["Parse edge.ID"]
        B["Serialize property to JSON"]
        C["Create EdgeTag struct"]
        D["Check for duplicates via GetEdgeTags"]
        E["Duplicate found?"]
        F["Update existing tag ID and timestamps"]
        G["Set new timestamps"]
        H["sql.db.Save(&tag)"]
        I["Return types.EdgeTag"]
    end
    
    A --> B --> C --> D --> E
    E -->|Yes| F --> H
    E -->|No| G --> H
    H --> I
```

**Duplicate detection logic:**
1. Queries existing edge tags with the same property name 
2. Compares `PropertyType()` and `Value()` 
3. Updates timestamp on match or creates new tag

#### Edge Tag Convenience Functions

Similar to entity tags, edge tags provide a convenience wrapper:

```go
func (sql *sqlRepository) CreateEdgeProperty(edge *types.Edge, prop oam.Property) (*types.EdgeTag, error)
```

#### Finding Edge Tags

Edge tag retrieval functions parallel their entity counterparts:

| Function | Purpose | Sources |
|----------|---------|---------|
| `FindEdgeTagById` | Retrieve by unique ID |  |
| `FindEdgeTagsByContent` | Search by property content |  |
| `GetEdgeTags` | Get all tags for an edge |  |
| `DeleteEdgeTag` | Remove by ID |  |

The implementation details match entity tag operations but operate on the `edge_tags` table with `edge_id` foreign keys instead of `entity_id`.

---

### Tag Lifecycle and Timestamp Management

Tags maintain two timestamps that track their lifecycle:

```mermaid
stateDiagram-v2
    [*] --> Created: CreateEntityTag/CreateEdgeTag<br/>with new property
    Created --> Updated: CreateEntityTag/CreateEdgeTag<br/>with duplicate property
    Updated --> Updated: Subsequent duplicate creates
    Updated --> Deleted: DeleteEntityTag/DeleteEdgeTag
    Deleted --> [*]
    
    note right of Created
        created_at: Set once
        updated_at: Set to now()
    end note
    
    note right of Updated
        created_at: Preserved
        updated_at: Updated to now()
    end note
```

#### Timestamp Behavior

**On Initial Creation** :
- `created_at`: Set from `input.CreatedAt` if provided, otherwise `time.Now().UTC()`
- `updated_at`: Set from `input.LastSeen` if provided, otherwise `time.Now().UTC()`

**On Duplicate Update** :
- `created_at`: Preserved from existing tag
- `updated_at`: Set to `time.Now().UTC()`

**Time Zone Handling:**
All timestamps are stored in UTC but converted to local time when returned via `types.EntityTag` or `types.EdgeTag` .

---

### JSON Content Storage and Querying

Tags store OAM properties as JSON strings in the `content` field. This enables flexible property storage while supporting content-based queries.

#### Serialization Process

```mermaid
flowchart LR
    Property["oam.Property<br/>(Go struct)"]
    JSON["property.JSON()<br/>(method call)"]
    String["JSON string<br/>(database storage)"]
    Parse["Parse()<br/>(method call)"]
    PropertyOut["oam.Property<br/>(Go struct)"]
    
    Property -->|"Serialize"| JSON
    JSON --> String
    String -->|"Deserialize"| Parse
    Parse --> PropertyOut
```

#### JSON Query Methods

The internal `EntityTag` and `EdgeTag` structs implement methods for generating database-specific JSON extraction queries:

- `NameJSONQuery()`: Extracts the property name field
- `ValueJSONQuery()`: Extracts the property value field

These methods handle differences between PostgreSQL's `->>` operator and SQLite's `json_extract()` function, abstracting database-specific syntax.

---

### Code Entity Mapping

The following diagram maps the public API functions to their internal implementations and database operations:

```mermaid
flowchart TB
    subgraph "Public API (repository.Repository interface)"
        CreateEntityTag["CreateEntityTag(entity, tag)"]
        CreateEntityProperty["CreateEntityProperty(entity, prop)"]
        FindEntityTagById["FindEntityTagById(id)"]
        FindEntityTagsByContent["FindEntityTagsByContent(prop, since)"]
        GetEntityTags["GetEntityTags(entity, since, names...)"]
        DeleteEntityTag["DeleteEntityTag(id)"]
        
        CreateEdgeTag["CreateEdgeTag(edge, tag)"]
        CreateEdgeProperty["CreateEdgeProperty(edge, prop)"]
        FindEdgeTagById["FindEdgeTagById(id)"]
        FindEdgeTagsByContent["FindEdgeTagsByContent(prop, since)"]
        GetEdgeTags["GetEdgeTags(edge, since, names...)"]
        DeleteEdgeTag["DeleteEdgeTag(id)"]
    end
    
    subgraph "sqlRepository Implementation"
        CreateEntityTagImpl["sqlRepository.CreateEntityTag<br/>[tag.go:21-76]"]
        CreateEntityPropertyImpl["sqlRepository.CreateEntityProperty<br/>[tag.go:82-84]"]
        FindEntityTagByIdImpl["sqlRepository.FindEntityTagById<br/>[tag.go:89-113]"]
        FindEntityTagsByContentImpl["sqlRepository.FindEntityTagsByContent<br/>[tag.go:120-169]"]
        GetEntityTagsImpl["sqlRepository.GetEntityTags<br/>[tag.go:174-226]"]
        DeleteEntityTagImpl["sqlRepository.DeleteEntityTag<br/>[tag.go:231-243]"]
        
        CreateEdgeTagImpl["sqlRepository.CreateEdgeTag<br/>[tag.go:249-304]"]
        CreateEdgePropertyImpl["sqlRepository.CreateEdgeProperty<br/>[tag.go:310-312]"]
        FindEdgeTagByIdImpl["sqlRepository.FindEdgeTagById<br/>[tag.go:317-346]"]
        FindEdgeTagsByContentImpl["sqlRepository.FindEdgeTagsByContent<br/>[tag.go:353-402]"]
        GetEdgeTagsImpl["sqlRepository.GetEdgeTags<br/>[tag.go:407-459]"]
        DeleteEdgeTagImpl["sqlRepository.DeleteEdgeTag<br/>[tag.go:464-476]"]
    end
    
    subgraph "GORM Database Operations"
        Save["db.Save(&tag)"]
        First["db.First(&tag)"]
        Where["db.Where(...).Find(&tags)"]
        Delete["db.Delete(&tag)"]
    end
    
    CreateEntityTag --> CreateEntityTagImpl --> Save
    CreateEntityProperty --> CreateEntityPropertyImpl --> CreateEntityTagImpl
    FindEntityTagById --> FindEntityTagByIdImpl --> First
    FindEntityTagsByContent --> FindEntityTagsByContentImpl --> Where
    GetEntityTags --> GetEntityTagsImpl --> Where
    DeleteEntityTag --> DeleteEntityTagImpl --> Delete
    
    CreateEdgeTag --> CreateEdgeTagImpl --> Save
    CreateEdgeProperty --> CreateEdgePropertyImpl --> CreateEdgeTagImpl
    FindEdgeTagById --> FindEdgeTagByIdImpl --> First
    FindEdgeTagsByContent --> FindEdgeTagsByContentImpl --> Where
    GetEdgeTags --> GetEdgeTagsImpl --> Where
    DeleteEdgeTag --> DeleteEdgeTagImpl --> Delete
```

---

### Usage Examples from Tests

The test suite demonstrates typical tag operations:

#### Entity Tag Test Flow

```mermaid
sequenceDiagram
    participant Test as Test Code
    participant Repo as sqlRepository
    participant DB as Database
    
    Test->>Repo: CreateAsset(&dns.FQDN{Name: "utica.edu"})
    Repo->>DB: INSERT entity
    DB-->>Repo: entity with ID
    Repo-->>Test: entity
    
    Test->>Repo: CreateEntityProperty(entity, SimpleProperty{Name:"test", Value:"foo"})
    Repo->>DB: Check for duplicates via GetEntityTags
    DB-->>Repo: No duplicates found
    Repo->>DB: INSERT entity_tag
    DB-->>Repo: tag with ID
    Repo-->>Test: tag (CreatedAt and LastSeen set)
    
    Note over Test: Wait 1 second
    
    Test->>Repo: CreateEntityProperty(entity, same property)
    Repo->>DB: Check for duplicates via GetEntityTags
    DB-->>Repo: Duplicate found
    Repo->>DB: UPDATE entity_tag (UpdatedAt only)
    DB-->>Repo: updated tag
    Repo-->>Test: tag (LastSeen updated, CreatedAt preserved)
    
    Test->>Repo: GetEntityTags(entity, since, "test")
    Repo->>DB: SELECT entity_tags WHERE entity_id = ? AND name = 'test'
    DB-->>Repo: matching tags
    Repo-->>Test: []*types.EntityTag
    
    Test->>Repo: DeleteEntityTag(tag.ID)
    Repo->>DB: DELETE entity_tag WHERE id = ?
    DB-->>Repo: Success
    Repo-->>Test: nil error
```

#### Edge Tag Test Flow

Edge tags follow an identical pattern but require an edge to be created first:

1. Create two entities (`CreateAsset`)
2. Create an edge between them (`CreateEdge`)
3. Attach properties to the edge via `CreateEdgeProperty`
4. Query and verify tags via `GetEdgeTags`
5. Clean up with `DeleteEdgeTag`

---

### Error Handling

The tag management system returns errors in the following scenarios:

| Scenario | Error Source | Functions Affected |
|----------|--------------|-------------------|
| Invalid ID format | `strconv.ParseUint` | `FindEntityTagById`, `DeleteEntityTag`, `FindEdgeTagById`, `DeleteEdgeTag` |
| JSON serialization failure | `property.JSON()` | `CreateEntityTag`, `CreateEdgeTag`, `FindEntityTagsByContent`, `FindEdgeTagsByContent` |
| Tag not found | `gorm.First` | `FindEntityTagById`, `FindEdgeTagById` |
| Database operation failure | `gorm.Save`, `gorm.Delete` | All create and delete operations |
| Zero results | Custom check | `FindEntityTagsByContent`, `GetEntityTags`, `FindEdgeTagsByContent`, `GetEdgeTags` |

The "zero tags found" error  is explicitly returned when queries produce no results, distinguishing between database errors and legitimate empty result sets.

## Database Schema & Migrations

## Purpose and Scope

This document covers the SQL schema migration system for PostgreSQL and SQLite databases in the asset-db repository. It details the migration scripts, table structures, indexes, constraints, and the execution mechanism using the `sql-migrate` library.

For Neo4j graph database schema initialization, see [Neo4j Schema Initialization](#7.2).

---

## Migration Architecture

The SQL migration system uses the `rubenv/sql-migrate` library to manage database schema versioning. Migration scripts are embedded directly into the Go binary using Go's `embed` package, ensuring that schema definitions are always available at runtime without external file dependencies.

### Embedded Migration Files

Each database type has its own migration package with embedded SQL files:

**PostgreSQL Migrations:**
- Package: `migrations/postgres`
- Embedded via: 
- Accessor function: `Migrations()` returns `embed.FS` 

**SQLite Migrations:**
- Package: `migrations/sqlite3`
- Embedded via: 
- Accessor function: `Migrations()` returns `embed.FS` 

---

## Migration Execution Flow

```mermaid
sequenceDiagram
    participant App as "Application Code"
    participant GORM as "gorm.DB"
    participant SQLMigrate as "sql-migrate Library"
    participant EmbedFS as "embed.FS (Migration Files)"
    participant DB as "Database (PostgreSQL/SQLite)"
    
    App->>GORM: "Open(dsn, config)"
    GORM-->>App: "gorm.DB instance"
    App->>GORM: "DB()"
    GORM-->>App: "*sql.DB"
    
    App->>EmbedFS: "Migrations()"
    EmbedFS-->>App: "embed.FS"
    
    App->>SQLMigrate: "migrate.EmbedFileSystemMigrationSource{}"
    App->>SQLMigrate: "migrate.Exec(sqlDb, dialect, source, Up)"
    
    SQLMigrate->>EmbedFS: "Read *.sql files"
    EmbedFS-->>SQLMigrate: "SQL scripts"
    
    SQLMigrate->>DB: "Parse +migrate Up directives"
    SQLMigrate->>DB: "Execute CREATE TABLE statements"
    SQLMigrate->>DB: "Execute CREATE INDEX statements"
    SQLMigrate->>DB: "Record migration version"
    
    DB-->>SQLMigrate: "Schema created"
    SQLMigrate-->>App: "Migration complete"
```

---

## Schema Structure

The SQL schema implements a property graph model with four core tables: `entities`, `entity_tags`, `edges`, and `edge_tags`. This structure corresponds to the types defined in .

### Entity-Relationship Diagram

```mermaid
erDiagram
    entities {
        INT entity_id PK "Auto-generated identity"
        TIMESTAMP created_at "Creation timestamp"
        TIMESTAMP updated_at "Last update timestamp"
        VARCHAR etype "Asset type identifier"
        JSONB_or_TEXT content "Serialized oam.Asset"
    }
    
    entity_tags {
        INT tag_id PK "Auto-generated identity"
        TIMESTAMP created_at "Creation timestamp"
        TIMESTAMP updated_at "Last update timestamp"
        VARCHAR ttype "Property type identifier"
        JSONB_or_TEXT content "Serialized oam.Property"
        INT entity_id FK "References entities"
    }
    
    edges {
        INT edge_id PK "Auto-generated identity"
        TIMESTAMP created_at "Creation timestamp"
        TIMESTAMP updated_at "Last update timestamp"
        VARCHAR etype "Relation type identifier"
        JSONB_or_TEXT content "Serialized oam.Relation"
        INT from_entity_id FK "Source entity"
        INT to_entity_id FK "Destination entity"
    }
    
    edge_tags {
        INT tag_id PK "Auto-generated identity"
        TIMESTAMP created_at "Creation timestamp"
        TIMESTAMP updated_at "Last update timestamp"
        VARCHAR ttype "Property type identifier"
        JSONB_or_TEXT content "Serialized oam.Property"
        INT edge_id FK "References edges"
    }
    
    entities ||--o{ entity_tags : "has many"
    entities ||--o{ edges : "from_entity_id"
    entities ||--o{ edges : "to_entity_id"
    edges ||--o{ edge_tags : "has many"
```

---

## PostgreSQL Schema Details

### Table Definitions

The PostgreSQL schema uses native JSONB columns for storing serialized Open Asset Model content, providing efficient querying and indexing capabilities.

#### Entities Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `entity_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `VARCHAR(255)` | - | Asset type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Asset` object |

#### Entity Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `VARCHAR(255)` | - | Property type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Property` object |
| `entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `entities(entity_id)` |

#### Edges Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `edge_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `VARCHAR(255)` | - | Relation type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Relation` object |
| `from_entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | Source entity reference |
| `to_entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | Destination entity reference |

#### Edge Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `VARCHAR(255)` | - | Property type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Property` object |
| `edge_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `edges(edge_id)` |

### Foreign Key Constraints

PostgreSQL uses named constraints for referential integrity:

- `fk_entity_tags_entities`: Links `entity_tags.entity_id` to `entities.entity_id` 
- `fk_edges_entities_from`: Links `edges.from_entity_id` to `entities.entity_id` 
- `fk_edges_entities_to`: Links `edges.to_entity_id` to `entities.entity_id` 
- `fk_edge_tags_edges`: Links `edge_tags.edge_id` to `edges.edge_id` 

All foreign keys use `ON DELETE CASCADE` to ensure dependent records are automatically removed when parent records are deleted.

---

## SQLite Schema Details

### Table Definitions

The SQLite schema is structurally similar to PostgreSQL but uses `TEXT` columns for JSON content and requires explicit foreign key enforcement.

#### Foreign Key Enforcement

SQLite requires explicit enablement of foreign key constraints:

```sql
PRAGMA foreign_keys = ON;
```

#### Entities Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `entity_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `TEXT` | - | Asset type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Asset` object |

#### Entity Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `TEXT` | - | Property type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Property` object |
| `entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `entities(entity_id)` |

#### Edges Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `edge_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `TEXT` | - | Relation type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Relation` object |
| `from_entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | Source entity reference |
| `to_entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | Destination entity reference |

#### Edge Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `TEXT` | - | Property type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Property` object |
| `edge_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `edges(edge_id)` |

---

## Index Strategy

Both PostgreSQL and SQLite schemas include identical indexing strategies to optimize common query patterns.

### Index Definitions

| Index Name | Table | Columns | Purpose |
|------------|-------|---------|---------|
| `idx_entities_updated_at` | `entities` | `updated_at` | Temporal queries filtering by last update time |
| `idx_entities_etype` | `entities` | `etype` | Type-based entity lookups |
| `idx_enttag_updated_at` | `entity_tags` | `updated_at` | Temporal queries for entity tags |
| `idx_enttag_entity_id` | `entity_tags` | `entity_id` | Fast lookup of tags for a specific entity |
| `idx_edge_updated_at` | `edges` | `updated_at` | Temporal queries for relationships |
| `idx_edge_from_entity_id` | `edges` | `from_entity_id` | Outgoing edge traversal |
| `idx_edge_to_entity_id` | `edges` | `to_entity_id` | Incoming edge traversal |
| `idx_edgetag_updated_at` | `edge_tags` | `updated_at` | Temporal queries for edge tags |
| `idx_edgetag_edge_id` | `edge_tags` | `edge_id` | Fast lookup of tags for a specific edge |

**PostgreSQL:** , [29-30](), [51-53](), [69-70]()

**SQLite:** , [29-30](), [48-50](), [64-65]()

### Temporal Query Optimization

All `updated_at` indexes support the repository's temporal query pattern, where operations accept a `since` parameter to retrieve only records modified after a specific timestamp. This is critical for the caching system's synchronization strategy.

---

## PostgreSQL vs SQLite Differences

### Content Storage

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Content Column Type | `JSONB` | `TEXT` |
| JSON Querying | Native JSONB operators | String-based parsing |
| Indexing Content | GIN indexes supported | Full-text search extensions |
| Storage Efficiency | Binary JSON format | String serialization |

**PostgreSQL:**   
**SQLite:** 

### Identity/Auto-increment

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Primary Key Generation | `GENERATED ALWAYS AS IDENTITY` | `INTEGER PRIMARY KEY` (implicit auto-increment) |
| Syntax | SQL standard | SQLite-specific |

**PostgreSQL:**   
**SQLite:** 

### Foreign Key Handling

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Foreign Keys | Always enforced | Requires `PRAGMA foreign_keys = ON` |
| Constraint Naming | Named constraints (e.g., `fk_entity_tags_entities`) | Anonymous constraints |

**PostgreSQL:**   
**SQLite:** , [24-26]()

### Timestamp Types

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Timestamp Type | `TIMESTAMP without time zone` | `DATETIME` |
| Default Value | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` |

---

## Migration Execution Example

### Code Integration

```mermaid
flowchart LR
    App["Application Code"]
    Embed["embed.FS<br/>(*.sql files)"]
    Factory["migrate.EmbedFileSystemMigrationSource"]
    Exec["migrate.Exec()"]
    DB["Database"]
    
    App -->|"Import migrations package"| Embed
    Embed -->|"Migrations()"| Factory
    Factory -->|"source + dialect"| Exec
    Exec -->|"Execute SQL"| DB
    
    subgraph "PostgreSQL"
        PGEmbed["postgres.Migrations()"]
        PGDialect["dialect: 'postgres'"]
    end
    
    subgraph "SQLite"
        SQLiteEmbed["sqlite3.Migrations()"]
        SQLiteDialect["dialect: 'sqlite3'"]
    end
```

### PostgreSQL Migration Execution

The PostgreSQL example demonstrates the complete migration flow:

1. **Open GORM Connection:** 
2. **Get SQL Database:** 
3. **Create Migration Source:** 
4. **Execute Migrations:** 
5. **Verify Tables:** 

### SQLite Migration Execution

The SQLite example follows the same pattern but uses SQLite-specific configuration:

1. **Open GORM Connection:** 
2. **Get SQL Database:** 
3. **Create Migration Source:** 
4. **Execute Migrations:** 
5. **Verify Tables:** 

---

## Migration Directives

The `sql-migrate` library uses special comment directives to identify migration sections:

### Up Migration

```sql
-- +migrate Up
```

Marks the beginning of forward migration SQL statements. This section is executed when upgrading the database schema.

**PostgreSQL:**   
**SQLite:** 

### Down Migration

```sql
-- +migrate Down
```

Marks the beginning of rollback migration SQL statements. This section is executed when downgrading the database schema.

**PostgreSQL:**   
**SQLite:** 

### Rollback Order

The down migration drops objects in reverse dependency order:

1. Drop `edge_tags` indexes and table
2. Drop `edges` indexes and table
3. Drop `entity_tags` indexes and table
4. Drop `entities` indexes and table

This ensures foreign key constraints are not violated during schema teardown.

**PostgreSQL:**   
**SQLite:** 

---

## Schema Version Tracking

The `sql-migrate` library automatically creates a `gorp_migrations` table to track applied migrations:

```mermaid
graph LR
    App["Application"]
    SQLMigrate["sql-migrate Library"]
    MigTable["gorp_migrations Table"]
    Schema["Application Schema"]
    
    App -->|"migrate.Exec()"| SQLMigrate
    SQLMigrate -->|"Check version"| MigTable
    SQLMigrate -->|"Apply new migrations"| Schema
    SQLMigrate -->|"Update version"| MigTable
```

This table stores:
- Migration ID (filename)
- Applied timestamp

This prevents duplicate execution of migrations and enables proper ordering of schema changes.
