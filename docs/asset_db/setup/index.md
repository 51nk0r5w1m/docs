# Getting Started with Asset DB

This guide provides the essential steps to install and begin using asset-db in your Go application. It covers installation, basic configuration, and simple usage patterns to help you store and query assets using the Repository pattern.

For detailed information on specific topics, see:
- **Installation details and dependencies**: [Installation](./getting-started.md#installation)
- **Configuring specific database backends**: [Database Configuration](./getting-started.md#database-configuration)
- **Complete usage examples and patterns**: [Basic Usage Examples](./getting-started.md#basic-usage-examples)
- **Architecture and design patterns**: [Architecture](./index.md#architecture)

---

## Prerequisites

**System Requirements**

| Requirement | Details |
|------------|---------|
| Go Version | 1.23.1 or higher (as specified in ) |
| Database | One of: PostgreSQL, SQLite, or Neo4j |
| Platform | Any platform supported by Go |

**Core Dependencies**

The system requires several key dependencies managed through Go modules:

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `github.com/owasp-amass/open-asset-model` | v0.13.6 | Asset type definitions |
| `gorm.io/gorm` | v1.25.12 | SQL ORM for PostgreSQL/SQLite |
| `github.com/neo4j/neo4j-go-driver/v5` | v5.27.0 | Neo4j graph database driver |
| `github.com/glebarez/sqlite` | v1.11.0 | Pure Go SQLite implementation |
| `github.com/rubenv/sql-migrate` | v1.7.1 | Database migration system |

**Sources**: 

---

## Quick Start

### Installation

Add asset-db to your Go project:

```bash
go get github.com/owasp-amass/asset-db
```

The module will automatically resolve all required dependencies listed in .

**Sources**: 

---

### Initialization Flow

The following diagram shows how the initialization process works, mapping user actions to specific code entities:

**Diagram: Initialization and Repository Creation**

```mermaid
graph TB
    User["User Application"]
    NewFunc["assetdb.New(dbtype, dsn)<br/>[db.go:32]"]
    MigrateFunc["migrateDatabase(dbtype, dsn)<br/>[db.go:47]"]
    RepoNew["repository.New(dbtype, dsn)<br/>[repository.go:49]"]
    
    subgraph "Migration Systems"
        SQLMigrate["sqlMigrate()<br/>[db.go:61]<br/>Uses sql-migrate.Exec()"]
        NeoMigrate["neoMigrate()<br/>[db.go:85]<br/>Calls InitializeSchema()"]
    end
    
    subgraph "Repository Implementations"
        SQLRepo["sqlrepo.New()<br/>For postgres/sqlite"]
        NeoRepo["neo4j.New()<br/>For neo4j"]
    end
    
    subgraph "Return Value"
        RepoInterface["repository.Repository<br/>[repository.go:20-46]"]
    end
    
    User -->|"1. Call with dbtype & dsn"| NewFunc
    NewFunc -->|"2. Migrate schema first"| MigrateFunc
    MigrateFunc -->|"If postgres/sqlite"| SQLMigrate
    MigrateFunc -->|"If neo4j"| NeoMigrate
    NewFunc -->|"3. Create repository"| RepoNew
    RepoNew -->|"dbtype='postgres'<br/>dbtype='sqlite'"| SQLRepo
    RepoNew -->|"dbtype='neo4j'"| NeoRepo
    SQLRepo -.->|"Implements"| RepoInterface
    NeoRepo -.->|"Implements"| RepoInterface
    NewFunc -->|"4. Return"| RepoInterface
    RepoInterface -->|"5. Use for operations"| User
```

**Sources**: , , 

---

### Minimal Working Example

The simplest way to get started is using SQLite in-memory mode, which requires no external database setup:

```go
import (
    "github.com/owasp-amass/asset-db"
    "github.com/owasp-amass/asset-db/repository/sqlrepo"
)

// Create in-memory SQLite database
repo, err := assetdb.New(sqlrepo.SQLiteMemory, "")
if err != nil {
    // handle error
}
defer repo.Close()
```

The `assetdb.New()` function at  performs two critical steps:
1. **Schema Migration**: Calls `migrateDatabase()` at  to initialize database schema
2. **Repository Creation**: Delegates to `repository.New()` at  to create the appropriate implementation

For `sqlrepo.SQLiteMemory`, a random in-memory DSN is generated at  in the format `file:mem{N}?mode=memory&cache=shared`.

**Sources**: , 

---

## Database Type Constants

The system defines specific constants for database types that must be used when calling `assetdb.New()`:

**Diagram: Database Type Selection**

```mermaid
graph LR
    User["Application Code"]
    NewFunc["assetdb.New(dbtype, dsn)"]
    
    subgraph "SQL Constants [sqlrepo package]"
        Postgres["sqlrepo.Postgres<br/>'postgres'"]
        SQLite["sqlrepo.SQLite<br/>'sqlite3'"]
        SQLiteMem["sqlrepo.SQLiteMemory<br/>'sqlite_memory'"]
    end
    
    subgraph "Graph Constants [neo4j package]"
        Neo4j["neo4j.Neo4j<br/>'neo4j'"]
    end
    
    User -->|"Specify dbtype"| NewFunc
    Postgres -.->|"Production SQL"| NewFunc
    SQLite -.->|"Embedded SQL"| NewFunc
    SQLiteMem -.->|"Testing/Development"| NewFunc
    Neo4j -.->|"Graph Database"| NewFunc
```

The string comparison at  is case-insensitive, but using the package constants ensures type safety.

**Sources**: 

---

## Connection String Format

Each database type requires a specific DSN (Data Source Name) format:

| Database Type | DSN Format | Example |
|--------------|------------|---------|
| PostgreSQL | `host=X user=Y password=Z dbname=W port=P sslmode=M` | `host=localhost user=postgres password=secret dbname=assets port=5432 sslmode=disable` |
| SQLite File | File path | `./assets.db` or `/var/data/assets.db` |
| SQLite Memory | Empty string (`""`) | Automatically generated at  |
| Neo4j | `neo4j://host:port/database` | `neo4j://user:pass@localhost:7687/assetdb` |

For Neo4j, the DSN is parsed at  to extract authentication credentials and database name. The URL format follows the pattern:
- Scheme: `neo4j://` or `bolt://`
- Authentication: Optional `username:password@`
- Host and Port: `hostname:port`
- Database: `/dbname` in the path

**Sources**: , 

---

## Schema Migration

**Automatic Migration Process**

All schema initialization happens automatically during `assetdb.New()`. The migration system:

1. **Detects Database Type**: At , determines which migration path to use
2. **SQL Databases**: Uses `sql-migrate` library () with embedded migration files
3. **Neo4j**: Creates constraints and indexes via Cypher ()

**Diagram: Migration Flow**

```mermaid
graph TB
    NewCall["assetdb.New(dbtype, dsn)"]
    Migrate["migrateDatabase(dbtype, dsn)<br/>[db.go:47-59]"]
    
    subgraph "SQL Migration Path"
        SQLMig["sqlMigrate()<br/>[db.go:61]"]
        EmbedFS["Embedded SQL Files<br/>pgmigrations.Migrations()<br/>sqlitemigrations.Migrations()"]
        MigrateExec["migrate.Exec(sqlDb, name, source, Up)<br/>[db.go:78]"]
    end
    
    subgraph "Neo4j Migration Path"
        NeoMig["neoMigrate()<br/>[db.go:85]"]
        ParseURL["url.Parse(dsn)<br/>[db.go:86]"]
        Driver["neo4jdb.NewDriverWithContext()<br/>[db.go:101]"]
        InitSchema["neomigrations.InitializeSchema()<br/>[db.go:118]"]
    end
    
    NewCall --> Migrate
    Migrate -->|"postgres/sqlite"| SQLMig
    Migrate -->|"neo4j"| NeoMig
    
    SQLMig --> EmbedFS
    EmbedFS --> MigrateExec
    
    NeoMig --> ParseURL
    ParseURL --> Driver
    Driver --> InitSchema
```

**Migration File Locations**

- PostgreSQL: [migrations/postgres]() package via 
- SQLite: [migrations/sqlite3]() package via 
- Neo4j: [migrations/neo4j]() package via 

The `EmbedFileSystemMigrationSource` at  loads embedded SQL files, ensuring migrations are bundled with the binary.

**Sources**: , 

---

## Repository Interface

Once initialized, the `repository.Repository` interface provides all data access methods:

**Core Operations by Category**

| Category | Methods | Purpose |
|----------|---------|---------|
| **Entity** | `CreateEntity`, `FindEntityById`, `FindEntitiesByContent`, `FindEntitiesByType`, `DeleteEntity` | Manage nodes/assets |
| **Edge** | `CreateEdge`, `FindEdgeById`, `IncomingEdges`, `OutgoingEdges`, `DeleteEdge` | Manage relationships |
| **Entity Tags** | `CreateEntityTag`, `GetEntityTags`, `FindEntityTagsByContent`, `DeleteEntityTag` | Metadata for entities |
| **Edge Tags** | `CreateEdgeTag`, `GetEdgeTags`, `FindEdgeTagsByContent`, `DeleteEdgeTag` | Metadata for edges |

The complete interface is defined at .

**Sources**: 

---

## Basic Operation Pattern

All operations follow a consistent pattern with OAM (Open Asset Model) integration:

**Diagram: Entity Creation Pattern**

```mermaid
sequenceDiagram
    participant App as "Application"
    participant Repo as "repository.Repository"
    participant OAM as "oam.Asset"
    participant DB as "Database"
    
    App->>OAM: Create oam.Asset<br/>(e.g., FQDN, IPAddress)
    App->>Repo: CreateAsset(asset)<br/>[repository.go:23]
    Repo->>Repo: Convert to types.Entity
    Repo->>DB: INSERT/CREATE entity
    DB-->>Repo: Entity with ID
    Repo-->>App: *types.Entity
```

**Key Type Conversion Points**

1. **Application Layer**: Uses `oam.Asset` types from the Open Asset Model
2. **Repository Layer**: Converts to `types.Entity` for storage
3. **Database Layer**: Persists as JSON (SQL) or properties (Neo4j)

The `CreateAsset()` convenience method at  handles the OAM-to-Entity conversion automatically.

**Sources**: 

---

## Next Steps

Now that you understand the basic setup, proceed to:

1. **[Installation](./getting-started.md#installation)**: Detailed dependency management and platform-specific considerations
2. **[Database Configuration](./getting-started.md#database-configuration)**: Specific setup instructions for PostgreSQL, SQLite, and Neo4j
3. **[Basic Usage Examples](./getting-started.md#basic-usage-examples)**: Complete code examples for common operations

For deeper understanding of the system architecture and design patterns, see [Architecture](./index.md#architecture).

**Sources**: , ,

