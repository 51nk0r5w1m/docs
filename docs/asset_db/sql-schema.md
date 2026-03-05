# Database Schema & Migrations


This document covers the SQL schema migration system for PostgreSQL and SQLite databases in the asset-db repository. It details the migration scripts, table structures, indexes, constraints, and the execution mechanism using the `sql-migrate` library.

For Neo4j graph database schema initialization, see [Neo4j Schema Initialization](#7.2).

---

# Migration Architecture

The SQL migration system uses the `rubenv/sql-migrate` library to manage database schema versioning. Migration scripts are embedded directly into the Go binary using Go's `embed` package, ensuring that schema definitions are always available at runtime without external file dependencies.

## Embedded Migration Files

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

# Migration Execution Flow

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

# Schema Structure

The SQL schema implements a property graph model with four core tables: `entities`, `entity_tags`, `edges`, and `edge_tags`. This structure corresponds to the types defined in .

## Entity-Relationship Diagram

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

# PostgreSQL Schema Details

## Table Definitions

The PostgreSQL schema uses native JSONB columns for storing serialized Open Asset Model content, providing efficient querying and indexing capabilities.

### Entities Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `entity_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `VARCHAR(255)` | - | Asset type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Asset` object |

### Entity Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `VARCHAR(255)` | - | Property type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Property` object |
| `entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `entities(entity_id)` |

### Edges Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `edge_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `VARCHAR(255)` | - | Relation type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Relation` object |
| `from_entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | Source entity reference |
| `to_entity_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | Destination entity reference |

### Edge Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INT` | `PRIMARY KEY`, `GENERATED ALWAYS AS IDENTITY` | Auto-incrementing primary key |
| `created_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP without time zone` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `VARCHAR(255)` | - | Property type from Open Asset Model |
| `content` | `JSONB` | - | Serialized `oam.Property` object |
| `edge_id` | `INT` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `edges(edge_id)` |

## Foreign Key Constraints

PostgreSQL uses named constraints for referential integrity:

- `fk_entity_tags_entities`: Links `entity_tags.entity_id` to `entities.entity_id` 
- `fk_edges_entities_from`: Links `edges.from_entity_id` to `entities.entity_id` 
- `fk_edges_entities_to`: Links `edges.to_entity_id` to `entities.entity_id` 
- `fk_edge_tags_edges`: Links `edge_tags.edge_id` to `edges.edge_id` 

All foreign keys use `ON DELETE CASCADE` to ensure dependent records are automatically removed when parent records are deleted.

---

# SQLite Schema Details

## Table Definitions

The SQLite schema is structurally similar to PostgreSQL but uses `TEXT` columns for JSON content and requires explicit foreign key enforcement.

### Foreign Key Enforcement

SQLite requires explicit enablement of foreign key constraints:

```sql
PRAGMA foreign_keys = ON;
```

### Entities Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `entity_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `TEXT` | - | Asset type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Asset` object |

### Entity Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `TEXT` | - | Property type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Property` object |
| `entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `entities(entity_id)` |

### Edges Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `edge_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `etype` | `TEXT` | - | Relation type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Relation` object |
| `from_entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | Source entity reference |
| `to_entity_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | Destination entity reference |

### Edge Tags Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing primary key |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modification time |
| `ttype` | `TEXT` | - | Property type from Open Asset Model |
| `content` | `TEXT` | - | JSON-serialized `oam.Property` object |
| `edge_id` | `INTEGER` | `FOREIGN KEY`, `ON DELETE CASCADE` | References `edges(edge_id)` |

---

# Index Strategy

Both PostgreSQL and SQLite schemas include identical indexing strategies to optimize common query patterns.

## Index Definitions

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

## Temporal Query Optimization

All `updated_at` indexes support the repository's temporal query pattern, where operations accept a `since` parameter to retrieve only records modified after a specific timestamp. This is critical for the caching system's synchronization strategy.

---

# PostgreSQL vs SQLite Differences

## Content Storage

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Content Column Type | `JSONB` | `TEXT` |
| JSON Querying | Native JSONB operators | String-based parsing |
| Indexing Content | GIN indexes supported | Full-text search extensions |
| Storage Efficiency | Binary JSON format | String serialization |

**PostgreSQL:**   
**SQLite:** 

## Identity/Auto-increment

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Primary Key Generation | `GENERATED ALWAYS AS IDENTITY` | `INTEGER PRIMARY KEY` (implicit auto-increment) |
| Syntax | SQL standard | SQLite-specific |

**PostgreSQL:**   
**SQLite:** 

## Foreign Key Handling

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Foreign Keys | Always enforced | Requires `PRAGMA foreign_keys = ON` |
| Constraint Naming | Named constraints (e.g., `fk_entity_tags_entities`) | Anonymous constraints |

**PostgreSQL:**   
**SQLite:** , [24-26]()

## Timestamp Types

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| Timestamp Type | `TIMESTAMP without time zone` | `DATETIME` |
| Default Value | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` |

---

# Migration Execution Example

## Code Integration

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

## PostgreSQL Migration Execution

The PostgreSQL example demonstrates the complete migration flow:

1. **Open GORM Connection:** 
2. **Get SQL Database:** 
3. **Create Migration Source:** 
4. **Execute Migrations:** 
5. **Verify Tables:** 

## SQLite Migration Execution

The SQLite example follows the same pattern but uses SQLite-specific configuration:

1. **Open GORM Connection:** 
2. **Get SQL Database:** 
3. **Create Migration Source:** 
4. **Execute Migrations:** 
5. **Verify Tables:** 

---

# Migration Directives

The `sql-migrate` library uses special comment directives to identify migration sections:

## Up Migration

```sql
-- +migrate Up
```

Marks the beginning of forward migration SQL statements. This section is executed when upgrading the database schema.

**PostgreSQL:**   
**SQLite:** 

## Down Migration

```sql
-- +migrate Down
```

Marks the beginning of rollback migration SQL statements. This section is executed when downgrading the database schema.

**PostgreSQL:**   
**SQLite:** 

## Rollback Order

The down migration drops objects in reverse dependency order:

1. Drop `edge_tags` indexes and table
2. Drop `edges` indexes and table
3. Drop `entity_tags` indexes and table
4. Drop `entities` indexes and table

This ensures foreign key constraints are not violated during schema teardown.

**PostgreSQL:**   
**SQLite:** 

---

# Schema Version Tracking

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
