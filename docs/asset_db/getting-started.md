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
| Go Version | 1.23.1 or higher (as specified in [go.mod:3]()) |
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

**Sources**: [go.mod:1-48]()

---

## Quick Start

### Installation

Add asset-db to your Go project:

```bash
go get github.com/owasp-amass/asset-db
```

The module will automatically resolve all required dependencies listed in [go.mod:5-16]().

**Sources**: [go.mod:1-3]()

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

**Sources**: [go.mod:1-48](), ,

## Installation

This page describes how to install the `asset-db` module as a Go dependency in your application and configure the necessary database backends. For information about configuring specific database connections, see [Database Configuration](./getting-started.md#database-configuration). For basic usage examples after installation, see [Basic Usage Examples](./getting-started.md#basic-usage-examples).

---

## Overview

The `asset-db` system is distributed as a Go module that can be imported into any Go application. The installation process involves adding the module to your project and ensuring the appropriate database backend is available. The system supports three database backends: PostgreSQL, SQLite, and Neo4j, each with different installation requirements.

---

## Prerequisites

### Go Version Requirement

The `asset-db` module requires **Go 1.23.1** or later. This version requirement is specified in [go.mod:3]().

```bash
# Verify your Go version
go version
```

### Database Backend Selection

Before installation, determine which database backend(s) you will use:

| Database Backend | Use Case | Additional Setup Required |
|-----------------|----------|---------------------------|
| **SQLite** | Development, testing, embedded applications | None (pure Go driver) |
| **PostgreSQL** | Production deployments, ACID compliance | PostgreSQL server installation |
| **Neo4j** | Graph-heavy queries, relationship-focused workloads | Neo4j server installation |

---

## Installation Steps

### Step 1: Add Module to Your Project

Add the `asset-db` module to your Go project using `go get`:

```bash
go get github.com/owasp-amass/asset-db
```

This command automatically downloads the module and its dependencies, updating your `go.mod` and `go.sum` files.

### Step 2: Core Dependencies

When you install `asset-db`, the following core dependencies are automatically installed:

```mermaid
graph TB
    AssetDB["github.com/owasp-amass/asset-db"]
    
    subgraph "Core Dependencies"
        OAM["github.com/owasp-amass/open-asset-model@v0.13.6"]
        UUID["github.com/google/uuid@v1.6.0"]
        StringSet["github.com/caffix/stringset@v0.2.0"]
    end
    
    subgraph "SQL Database Support"
        GORM["gorm.io/gorm@v1.25.12"]
        PGDriver["gorm.io/driver/postgres@v1.5.11"]
        SQLiteDriver["github.com/glebarez/sqlite@v1.11.0"]
        Datatypes["gorm.io/datatypes@v1.2.5"]
    end
    
    subgraph "Graph Database Support"
        Neo4jDriver["github.com/neo4j/neo4j-go-driver/v5@v5.27.0"]
    end
    
    subgraph "Migration System"
        SQLMigrate["github.com/rubenv/sql-migrate@v1.7.1"]
    end
    
    AssetDB --> OAM
    AssetDB --> UUID
    AssetDB --> StringSet
    AssetDB --> GORM
    AssetDB --> PGDriver
    AssetDB --> SQLiteDriver
    AssetDB --> Datatypes
    AssetDB --> Neo4jDriver
    AssetDB --> SQLMigrate
    
    GORM --> PGDriver
    GORM --> SQLiteDriver
```

**Diagram: Module Dependency Structure** - Shows the direct dependencies that are automatically installed with `asset-db`, mapped to their specific versions as declared in `go.mod`.

---

## Database-Specific Installation

### SQLite (Embedded Database)

**No additional installation required.** SQLite support is provided through a pure Go driver (`glebarez/sqlite`), which is automatically included with the module.

The SQLite driver dependencies include:
- `github.com/glebarez/sqlite@v1.11.0` - GORM-compatible SQLite driver
- `github.com/glebarez/go-sqlite@v1.22.0` - Underlying pure Go SQLite implementation
- `modernc.org/sqlite@v1.34.5` - Pure Go SQLite engine

These are automatically installed as indirect dependencies when you install `asset-db`.

---

### PostgreSQL

**PostgreSQL server must be installed separately.** The Go driver (`pgx/v5`) is included with `asset-db`, but you need a running PostgreSQL instance.

#### PostgreSQL Server Installation

Choose one of the following methods:

**Option 1: Using Docker (Recommended for Development)**

The repository includes a Docker setup for PostgreSQL. See [PostgreSQL Docker Container](#8.1) for details.

```bash
# Pull and run PostgreSQL container
docker pull postgres:latest
docker run --name asset-db-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=assetdb \
  -p 5432:5432 \
  -d postgres:latest
```

**Option 2: Native Installation**

Follow the official PostgreSQL installation guide for your operating system: https://www.postgresql.org/download/

#### PostgreSQL Driver Dependencies

The following packages provide PostgreSQL connectivity:
- `gorm.io/driver/postgres@v1.5.11` - GORM PostgreSQL driver
- `github.com/jackc/pgx/v5@v5.7.2` - PostgreSQL driver and toolkit
- `github.com/jackc/pgpassfile@v1.0.0` - Password file parsing
- `github.com/jackc/pgservicefile@v0.0.0-20240606120523-5a60cdf6a761` - Service file parsing
- `github.com/jackc/puddle/v2@v2.2.2` - Connection pooling

These are automatically installed as dependencies.

---

### Neo4j

**Neo4j server must be installed separately.** The Go driver (`neo4j-go-driver/v5`) is included with `asset-db`, but you need a running Neo4j instance.

#### Neo4j Server Installation

**Option 1: Using Docker (Recommended for Development)**

```bash
# Pull and run Neo4j container
docker pull neo4j:latest
docker run --name asset-db-neo4j \
  -e NEO4J_AUTH=neo4j/yourpassword \
  -p 7474:7474 \
  -p 7687:7687 \
  -d neo4j:latest
```

**Option 2: Neo4j Desktop or Native Installation**

Download Neo4j Desktop or Community Edition from: https://neo4j.com/download/

#### Neo4j Driver Dependencies

The Neo4j support is provided by:
- `github.com/neo4j/neo4j-go-driver/v5@v5.27.0` - Official Neo4j Go driver

This is automatically installed as a dependency.

---

## Verification

After installation, verify that the module is correctly installed and importable:

### Step 1: Create a Test File

Create a file named `verify_install.go`:

```go
package main

import (
    "fmt"
    "github.com/owasp-amass/asset-db"
)

func main() {
    // This will compile successfully if installation is correct
    fmt.Println("asset-db module is correctly installed")
    
    // You can check the version by examining go.mod
    fmt.Println("Ready to create repository instances")
}
```

### Step 2: Run the Verification

```bash
go run verify_install.go
```

If the module is installed correctly, this will compile and run without errors.

### Step 3: Verify Dependencies

Check that all dependencies are correctly resolved:

```bash
# List all dependencies
go list -m all | grep -E "(gorm|neo4j|sqlite|asset)"

# Verify module integrity
go mod verify
```

Expected output should include lines similar to:
```
github.com/owasp-amass/asset-db v0.x.x
github.com/owasp-amass/open-asset-model v0.13.6
github.com/neo4j/neo4j-go-driver/v5 v5.27.0
gorm.io/gorm v1.25.12
github.com/glebarez/sqlite v1.11.0
```

---

## Installation Flow

```mermaid
sequenceDiagram
    participant Dev as "Developer"
    participant GoCmd as "go get command"
    participant GoProxy as "Go Module Proxy"
    participant Project as "Project go.mod/go.sum"
    
    Dev->>GoCmd: "go get github.com/owasp-amass/asset-db"
    GoCmd->>GoProxy: "Fetch module@latest"
    GoProxy-->>GoCmd: "asset-db module + version"
    
    GoCmd->>GoProxy: "Resolve dependencies"
    Note over GoProxy: "Fetches dependencies:<br/>- gorm.io/gorm@v1.25.12<br/>- neo4j-go-driver/v5@v5.27.0<br/>- open-asset-model@v0.13.6<br/>- glebarez/sqlite@v1.11.0<br/>- rubenv/sql-migrate@v1.7.1"
    
    GoProxy-->>GoCmd: "All dependencies resolved"
    
    GoCmd->>Project: "Update go.mod (direct dependencies)"
    GoCmd->>Project: "Update go.sum (all dependencies + hashes)"
    
    GoCmd-->>Dev: "Installation complete"
    
    Note over Dev: "Module ready for import"
```

**Diagram: Installation Sequence** - Shows the complete flow from running `go get` to having the module ready for use, including dependency resolution through the Go module proxy.

---

## Troubleshooting

### Issue: Go Version Too Old

**Error:** `go.mod requires go >= 1.23.1`

**Solution:** Upgrade your Go installation to version 1.23.1 or later.

### Issue: Database Driver Import Errors

**Error:** `could not import gorm.io/driver/postgres`

**Solution:** Ensure all dependencies are downloaded:
```bash
go mod download
go mod tidy
```

### Issue: Module Checksum Mismatch

**Error:** `verifying module: checksum mismatch`

**Solution:** Clear the module cache and re-download:
```bash
go clean -modcache
go mod download
```

### Issue: Neo4j Driver Compatibility

**Error:** `incompatible with neo4j server version`

**Solution:** The driver supports Neo4j 5.x. Ensure your Neo4j server is version 5.0 or later, or use the Docker image recommended above.

---

## Next Steps

After successful installation:

1. **Configure Database Connection:** See [Database Configuration](./getting-started.md#database-configuration) for details on connecting to PostgreSQL, SQLite, or Neo4j
2. **Initialize Repository:** Learn how to create repository instances using the factory pattern
3. **Run Migrations:** Understand how database schemas are automatically initialized
4. **Basic Operations:** Try creating entities and edges with [Basic Usage Examples](./getting-started.md#basic-usage-examples)

## Database Configuration

This page documents how to configure and connect to different database backends supported by asset-db. It covers connection string formats, database type identifiers, and connection parameters for PostgreSQL, SQLite, and Neo4j.

For information about database schema initialization and migrations, see [Database Migrations](./migrations.md). For details about the repository abstraction that these configurations support, see [Repository Pattern](./index.md#repository-pattern).

---

## Supported Database Types

The asset-db system supports three database backend types, identified by string constants defined in the repository implementations:

| Database Type | Constant | Implementation | Use Case |
|--------------|----------|----------------|----------|
| PostgreSQL | `"postgres"` | `sqlrepo.Postgres` | Production deployments, ACID compliance, advanced querying |
| SQLite | `"sqlite"` | `sqlrepo.SQLite` | Embedded databases, file-based storage, development |
| SQLite In-Memory | `"sqlite_memory"` | `sqlrepo.SQLiteMemory` | Testing, ephemeral storage, maximum performance |
| Neo4j | `"neo4j"` | `neo4j.Neo4j` | Graph-centric queries, relationship-heavy workloads |

---

## Database Type Resolution

The following diagram shows how the `assetdb.New()` function resolves database types to their respective implementations:

```mermaid
graph TB
    NewFunc["assetdb.New(dbtype, dsn)"]
    TypeSwitch{"Database Type"}
    
    SQLiteMemCheck["dbtype == sqlrepo.SQLiteMemory"]
    GenerateDSN["Generate random in-memory DSN:<br/>file:memN?mode=memory&cache=shared"]
    
    RepoNew["repository.New(dbtype, dsn)"]
    Migrate["migrateDatabase(dbtype, dsn)"]
    
    SQLiteMigrate["sqlMigrate('sqlite3', ...)"]
    PostgresMigrate["sqlMigrate('postgres', ...)"]
    NeoMigrate["neoMigrate(dsn)"]
    
    SQLRepo["sqlRepository"]
    NeoRepo["neoRepository"]
    
    NewFunc --> SQLiteMemCheck
    SQLiteMemCheck -->|"Yes"| GenerateDSN
    GenerateDSN --> RepoNew
    SQLiteMemCheck -->|"No"| RepoNew
    
    RepoNew --> TypeSwitch
    TypeSwitch -->|"sqlrepo.Postgres<br/>sqlrepo.SQLite<br/>sqlrepo.SQLiteMemory"| SQLRepo
    TypeSwitch -->|"neo4j.Neo4j"| NeoRepo
    
    NewFunc --> Migrate
    Migrate --> TypeSwitch
    TypeSwitch -->|"sqlrepo.SQLite<br/>sqlrepo.SQLiteMemory"| SQLiteMigrate
    TypeSwitch -->|"sqlrepo.Postgres"| PostgresMigrate
    TypeSwitch -->|"neo4j.Neo4j"| NeoMigrate
```

---

## Connection String Formats

### PostgreSQL DSN

PostgreSQL uses a standard connection string format supported by the `pgx` driver:

```
host=localhost user=myuser password=mypass dbname=assetdb port=5432 sslmode=disable
```

Common parameters:
- `host` - Database server hostname or IP
- `port` - Database server port (default: 5432)
- `user` - Database username
- `password` - Database password
- `dbname` - Database name
- `sslmode` - SSL mode (`disable`, `require`, `verify-ca`, `verify-full`)

The DSN is passed directly to `gorm.Open(postgres.Open(dsn), ...)` for connection.

---

### SQLite DSN

SQLite uses a file path as the DSN:

```
/path/to/database.db
```

Or with URI parameters:

```
file:/path/to/database.db?_journal_mode=WAL
```

The DSN is passed to `gorm.Open(sqlite.Open(dsn), ...)` using the `glebarez/sqlite` driver, which is a pure Go SQLite implementation.

---

### SQLite In-Memory DSN

For SQLite in-memory databases, the DSN is automatically generated by `assetdb.New()` when the database type is `sqlrepo.SQLiteMemory`:

```
file:mem{random}?mode=memory&cache=shared
```

The random number (0-999) is appended to create unique in-memory database instances. The `cache=shared` parameter allows multiple connections to access the same in-memory database.

---

### Neo4j DSN

Neo4j uses a URL-based connection string format:

```
neo4j://localhost:7687/databasename
bolt://localhost:7687/databasename
neo4j+s://localhost:7687/databasename
```

With authentication:

```
neo4j://username:password@localhost:7687/databasename
```

Components:
- **Scheme**: `neo4j`, `bolt`, `neo4j+s`, `neo4j+ssc`, `bolt+s`, `bolt+ssc`
- **Username/Password**: Optional, extracted from URL user info
- **Host/Port**: Neo4j server location
- **Path**: Database name (extracted and used separately)

The Neo4j implementation parses the DSN to extract authentication credentials and the database name, then reconstructs a connection URL without the path component.

---

## Creating a Repository

The `assetdb.New()` function is the main entry point for creating a repository with a configured database:

```go
func New(dbtype, dsn string) (repository.Repository, error)
```

This function:
1. Handles special DSN generation for `sqlrepo.SQLiteMemory`
2. Calls `repository.New(dbtype, dsn)` to create the repository implementation
3. Calls `migrateDatabase(dbtype, dsn)` to initialize/update the database schema
4. Returns a `repository.Repository` interface

Example usage patterns:

| Database Type | Call Example |
|--------------|--------------|
| PostgreSQL | `assetdb.New("postgres", "host=localhost user=admin password=pass dbname=assets")` |
| SQLite | `assetdb.New("sqlite", "/var/lib/assetdb.db")` |
| SQLite In-Memory | `assetdb.New("sqlite_memory", "")` |
| Neo4j | `assetdb.New("neo4j", "neo4j://user:pass@localhost:7687/assetdb")` |

---

## Connection Parameters and Pooling

Each database backend configures connection pooling and timeout parameters differently:

### PostgreSQL Connection Parameters

```mermaid
graph LR
    subgraph PostgresConfig["postgresDatabase()"]
        GORMOpen["gorm.Open(postgres.Open(dsn), ...)"]
        GetDB["db.DB()"]
        PoolConfig["Connection Pool Configuration"]
    end
    
    subgraph PoolSettings["Pool Settings"]
        MaxIdle["SetMaxIdleConns(5)"]
        MaxOpen["SetMaxOpenConns(10)"]
        MaxLifetime["SetConnMaxLifetime(1 hour)"]
        MaxIdleTime["SetConnMaxIdleTime(10 minutes)"]
    end
    
    GORMOpen --> GetDB
    GetDB --> PoolConfig
    PoolConfig --> MaxIdle
    PoolConfig --> MaxOpen
    PoolConfig --> MaxLifetime
    PoolConfig --> MaxIdleTime
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MaxIdleConns` | 5 | Maximum idle connections in pool |
| `MaxOpenConns` | 10 | Maximum open connections total |
| `ConnMaxLifetime` | 1 hour | Maximum connection reuse duration |
| `ConnMaxIdleTime` | 10 minutes | Maximum idle time before closing |

---

### SQLite Connection Parameters

SQLite connection pools are configured differently based on the database mode:

| Mode | MaxOpenConns | MaxIdleConns | Use Case |
|------|--------------|--------------|----------|
| File-based (`sqlrepo.SQLite`) | 3 | 5 | Disk-based storage |
| In-memory (`sqlrepo.SQLiteMemory`) | 50 | 100 | Testing, high-performance temporary storage |

Both modes share the same lifetime parameters:
- `ConnMaxLifetime`: 1 hour
- `ConnMaxIdleTime`: 10 minutes

The higher connection limits for in-memory databases enable better concurrent access for testing scenarios.

---

### Neo4j Connection Parameters

Neo4j driver configuration is set during driver creation:

```mermaid
graph TB
    subgraph DriverConfig["neo4jdb.NewDriverWithContext()"]
        DSNParse["Parse DSN for auth & dbname"]
        Auth["Setup Authentication"]
        ConfigFunc["Configure driver"]
    end
    
    subgraph ConfigSettings["Driver Configuration"]
        MaxPool["MaxConnectionPoolSize: 20"]
        MaxLife["MaxConnectionLifetime: 1 hour"]
        Liveness["ConnectionLivenessCheckTimeout: 10 minutes"]
    end
    
    subgraph Verification["Connection Verification"]
        VerifyCtx["context.WithTimeout(5 seconds)"]
        VerifyConn["driver.VerifyConnectivity(ctx)"]
    end
    
    DSNParse --> Auth
    Auth --> ConfigFunc
    ConfigFunc --> MaxPool
    ConfigFunc --> MaxLife
    ConfigFunc --> Liveness
    ConfigFunc --> Verification
    Verification --> VerifyCtx
    VerifyCtx --> VerifyConn
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MaxConnectionPoolSize` | 20 | Maximum connections in pool |
| `MaxConnectionLifetime` | 1 hour | Maximum connection reuse duration |
| `ConnectionLivenessCheckTimeout` | 10 minutes | Timeout for liveness checks |
| Connectivity verification timeout | 5 seconds | Initial connection validation |

**Authentication modes:**
- No authentication: Used when DSN has no user info
- Basic authentication: Username and password extracted from DSN user info

---

## Configuration Summary

The following table summarizes the complete configuration landscape for all supported database backends:

| Aspect | PostgreSQL | SQLite (File) | SQLite (Memory) | Neo4j |
|--------|-----------|---------------|-----------------|-------|
| **DSN Format** | Key-value string | File path | Auto-generated | URL with auth |
| **Driver** | `gorm + pgx v5` | `gorm + glebarez/sqlite` | `gorm + glebarez/sqlite` | `neo4j-go-driver v5` |
| **Max Open Conns** | 10 | 3 | 50 | 20 (pool size) |
| **Max Idle Conns** | 5 | 5 | 100 | N/A |
| **Conn Lifetime** | 1 hour | 1 hour | 1 hour | 1 hour |
| **Idle Timeout** | 10 minutes | 10 minutes | 10 minutes | N/A |
| **Liveness Check** | N/A | N/A | N/A | 10 minutes |
| **Auth Support** | Yes (DSN) | No | No | Yes (URL) |
| **Migration System** | `sql-migrate` | `sql-migrate` | `sql-migrate` | Cypher-based |

## Basic Usage Examples

This page provides practical code examples for common operations in asset-db. It demonstrates how to initialize a repository, create entities and edges, add metadata through tags, and perform basic queries. These examples assume you have already installed asset-db ([see Installation](#2.1)) and configured your database connection ([see Database Configuration](#2.2)).

For detailed information about the repository interface and all available methods, see [Repository Interface](./api-reference.md#repository-interface). For advanced usage patterns including caching, see [Caching System](./caching.md).

---

## Initializing a Repository

The entry point for using asset-db is the `repository.New()` factory function, which creates the appropriate repository implementation based on the database type.

### Basic Initialization Pattern

The initialization process follows a simple factory pattern:

```mermaid
graph LR
    App["Application Code"]
    Factory["repository.New()"]
    SQLRepo["sqlRepository instance"]
    NeoRepo["neoRepository instance"]
    Repo["repository.Repository interface"]
    
    App -->|"New(dbtype, dsn)"| Factory
    Factory -->|"dbtype='postgres'<br/>or 'sqlite'"| SQLRepo
    Factory -->|"dbtype='neo4j'"| NeoRepo
    SQLRepo -.->|implements| Repo
    NeoRepo -.->|implements| Repo
    Factory -->|returns| Repo
    App -->|uses| Repo
```

### Example: PostgreSQL Repository

```go
import (
    "github.com/owasp-amass/asset-db/repository"
)

// Initialize PostgreSQL repository
repo, err := repository.New("postgres", 
    "host=localhost port=5432 user=myuser password=mypass dbname=assetdb")
if err != nil {
    // Handle error
}
defer repo.Close()
```

### Example: SQLite Repository

```go
// Initialize SQLite file-based repository
repo, err := repository.New("sqlite", "assets.db")
if err != nil {
    // Handle error
}
defer repo.Close()

// Or use in-memory SQLite for testing
repo, err := repository.New("sqlite_memory", ":memory:")
```

### Example: Neo4j Repository

```go
// Initialize Neo4j repository
repo, err := repository.New("neo4j", 
    "bolt://localhost:7687")
if err != nil {
    // Handle error
}
defer repo.Close()
```

---

## Working with Entities (Assets)

Entities represent nodes in the asset graph. The asset-db system uses the Open Asset Model (OAM) to define standardized asset types.

### Entity Lifecycle Operations

```mermaid
graph TB
    Asset["oam.Asset<br/>(FQDN, IPAddress, etc.)"]
    CreateAsset["CreateAsset(asset)"]
    Entity["types.Entity<br/>(with ID, timestamps)"]
    
    FindById["FindEntityById(id)"]
    FindByContent["FindEntitiesByContent(asset, since)"]
    FindByType["FindEntitiesByType(assetType, since)"]
    DeleteEntity["DeleteEntity(id)"]
    
    Asset -->|input| CreateAsset
    CreateAsset -->|returns| Entity
    Entity -->|query by ID| FindById
    Entity -->|query by content| FindByContent
    Entity -->|query by type| FindByType
    Entity -->|remove| DeleteEntity
```

### Example: Creating an FQDN Entity

```go
import (
    "github.com/owasp-amass/open-asset-model/dns"
)

// Create an FQDN asset
fqdn := &dns.FQDN{Name: "www.example.com"}

// Store it as an entity
entity, err := repo.CreateAsset(fqdn)
if err != nil {
    // Handle error
}

// The entity now has an ID and timestamps
fmt.Printf("Entity ID: %s\n", entity.ID)
fmt.Printf("Created At: %s\n", entity.CreatedAt)
fmt.Printf("Last Seen: %s\n", entity.LastSeen)
```

### Example: Creating an IP Address Entity

```go
import (
    "net/netip"
    "github.com/owasp-amass/open-asset-model/network"
)

// Create an IP address asset
ip, _ := netip.ParseAddr("192.168.1.1")
ipAsset := &network.IPAddress{
    Address: ip,
    Type:    "IPv4",
}

entity, err := repo.CreateAsset(ipAsset)
if err != nil {
    // Handle error
}
```

### Example: Creating Other Asset Types

```go
import (
    "net/netip"
    "github.com/owasp-amass/open-asset-model/network"
    oamreg "github.com/owasp-amass/open-asset-model/registration"
)

// Autonomous System
as := &network.AutonomousSystem{Number: 15169}
asEntity, err := repo.CreateAsset(as)

// Netblock (CIDR)
cidr, _ := netip.ParsePrefix("198.51.100.0/24")
netblock := &network.Netblock{
    CIDR: cidr,
    Type: "IPv4",
}
netblockEntity, err := repo.CreateAsset(netblock)

// Registration Record
autnumRecord := &oamreg.AutnumRecord{
    Number: 15169,
    Handle: "AS15169",
    Name:   "GOOGLE",
}
recordEntity, err := repo.CreateAsset(autnumRecord)
```

### Duplicate Asset Handling

When you create an asset that already exists (same content), the system updates the `LastSeen` timestamp rather than creating a duplicate.

```go
// Create asset first time
entity1, _ := repo.CreateAsset(&dns.FQDN{Name: "example.com"})

// Wait a moment
time.Sleep(time.Second)

// Create same asset again
entity2, _ := repo.CreateAsset(&dns.FQDN{Name: "example.com"})

// entity1.ID == entity2.ID (same entity)
// entity2.LastSeen > entity1.LastSeen (updated timestamp)
```

---

## Querying Entities

The repository provides multiple ways to find entities based on different criteria.

### Query Methods Summary

| Method | Purpose | Returns |
|--------|---------|---------|
| `FindEntityById(id)` | Find specific entity by ID | Single entity or error |
| `FindEntitiesByContent(asset, since)` | Find entities matching asset content | List of entities |
| `FindEntitiesByType(assetType, since)` | Find all entities of a specific type | List of entities |

### Example: Finding Entity by ID

```go
// Retrieve a specific entity
entity, err := repo.FindEntityById("entity-uuid-here")
if err != nil {
    // Handle error (entity not found)
}
```

### Example: Finding Entities by Content

```go
import (
    "time"
)

// Find all entities matching this FQDN
fqdn := &dns.FQDN{Name: "www.example.com"}
start := time.Now().Add(-24 * time.Hour) // Last 24 hours

entities, err := repo.FindEntitiesByContent(fqdn, start)
if err != nil {
    // Handle error
}

// entities is a slice of all matching entities
for _, entity := range entities {
    fmt.Printf("Found: %s\n", entity.ID)
}
```

### Example: Finding Entities by Type

```go
import (
    oam "github.com/owasp-amass/open-asset-model"
)

// Find all FQDN entities
start := time.Now().Add(-7 * 24 * time.Hour) // Last 7 days

entities, err := repo.FindEntitiesByType(oam.FQDN, start)
if err != nil {
    // Handle error
}

// Or find all IP addresses
ipEntities, err := repo.FindEntitiesByType(oam.IPAddress, start)
```

---

## Working with Edges (Relationships)

Edges represent directed relationships between entities. Each edge has a source entity (`FromEntity`), a destination entity (`ToEntity`), and a relation type from the Open Asset Model.

### Edge Creation Pattern

```mermaid
graph LR
    FromEntity["types.Entity<br/>(source)"]
    ToEntity["types.Entity<br/>(destination)"]
    Relation["oam.Relation<br/>(BasicDNSRelation,<br/>SimpleRelation, etc.)"]
    
    Edge["types.Edge"]
    CreateEdge["CreateEdge(edge)"]
    StoredEdge["types.Edge<br/>(with ID, timestamps)"]
    
    FromEntity -->|FromEntity field| Edge
    ToEntity -->|ToEntity field| Edge
    Relation -->|Relation field| Edge
    Edge -->|input| CreateEdge
    CreateEdge -->|returns| StoredEdge
```

### Example: Creating a DNS Relationship

```go
import (
    "github.com/owasp-amass/asset-db/types"
    "github.com/owasp-amass/open-asset-model/dns"
)

// Create two FQDN entities
domain, _ := repo.CreateAsset(&dns.FQDN{Name: "example.com"})
subdomain, _ := repo.CreateAsset(&dns.FQDN{Name: "www.example.com"})

// Create a DNS record relationship
edge := &types.Edge{
    Relation: &dns.BasicDNSRelation{
        Name: "dns_record",
        Header: dns.RRHeader{
            RRType: 5, // CNAME record
            Class:  1,
            TTL:    3600,
        },
    },
    FromEntity: domain,
    ToEntity:   subdomain,
}

createdEdge, err := repo.CreateEdge(edge)
if err != nil {
    // Handle error
}
```

### Example: Creating Simple Relationships

```go
import (
    "github.com/owasp-amass/open-asset-model/general"
)

// AS announces netblock
asEntity, _ := repo.CreateAsset(&network.AutonomousSystem{Number: 15169})
netblockEntity, _ := repo.CreateAsset(&network.Netblock{CIDR: cidr, Type: "IPv4"})

edge := &types.Edge{
    Relation: &general.SimpleRelation{Name: "announces"},
    FromEntity: asEntity,
    ToEntity: netblockEntity,
}

createdEdge, err := repo.CreateEdge(edge)
```

### Example: FQDN to IP Address Relationship

```go
// FQDN resolves to IP address
fqdnEntity, _ := repo.CreateAsset(&dns.FQDN{Name: "www.domain.com"})
ipEntity, _ := repo.CreateAsset(&network.IPAddress{Address: ip, Type: "IPv4"})

edge := &types.Edge{
    Relation: &dns.BasicDNSRelation{
        Name: "dns_record",
        Header: dns.RRHeader{RRType: 1}, // A record
    },
    FromEntity: fqdnEntity,
    ToEntity: ipEntity,
}

createdEdge, err := repo.CreateEdge(edge)
```

---

## Querying Edges

The repository provides methods to traverse the graph by finding incoming and outgoing edges for any entity.

### Edge Query Methods

```mermaid
graph LR
    Entity["types.Entity"]
    Incoming["IncomingEdges(entity, since, labels...)"]
    Outgoing["OutgoingEdges(entity, since, labels...)"]
    InEdges["[]*types.Edge<br/>(edges pointing to entity)"]
    OutEdges["[]*types.Edge<br/>(edges originating from entity)"]
    
    Entity -->|query| Incoming
    Entity -->|query| Outgoing
    Incoming -->|returns| InEdges
    Outgoing -->|returns| OutEdges
```

### Example: Finding Outgoing Edges

```go
// Find all edges originating from an entity
start := time.Now().Add(-24 * time.Hour)

// Get all outgoing edges (no label filter)
edges, err := repo.OutgoingEdges(sourceEntity, start)
if err != nil {
    // Handle error
}

// Get only DNS record edges
dnsEdges, err := repo.OutgoingEdges(sourceEntity, start, "dns_record")
if err != nil {
    // Handle error
}

for _, edge := range dnsEdges {
    fmt.Printf("Edge from %s to %s\n", 
        edge.FromEntity.ID, edge.ToEntity.ID)
}
```

### Example: Finding Incoming Edges

```go
// Find all edges pointing to an entity
start := time.Now().Add(-24 * time.Hour)

// Get all incoming edges
edges, err := repo.IncomingEdges(destinationEntity, start)
if err != nil {
    // Handle error
}

// Get only specific relation types
dnsEdges, err := repo.IncomingEdges(destinationEntity, start, "dns_record")
if err != nil {
    // Handle error
}

for _, edge := range dnsEdges {
    fmt.Printf("Edge from %s to %s\n", 
        edge.FromEntity.ID, edge.ToEntity.ID)
}
```

### Example: Filtering Edges by Multiple Labels

```go
// Query with multiple relation labels
edges, err := repo.OutgoingEdges(entity, start, "dns_record", "contains")
if err != nil {
    // Handle error
}

// Query all relations (empty label list)
allEdges, err := repo.OutgoingEdges(entity, start)
```

---

## Working with Tags (Properties)

Tags allow you to attach metadata (properties) to entities and edges. Each tag contains an Open Asset Model property and has its own lifecycle tracking (`CreatedAt`, `LastSeen`).

### Tag Operations Flow

```mermaid
graph TB
    Property["oam.Property<br/>(SimpleProperty,<br/>DNSRecordProperty, etc.)"]
    Entity["types.Entity"]
    Edge["types.Edge"]
    
    CreateEntityProp["CreateEntityProperty(entity, property)"]
    CreateEdgeProp["CreateEdgeProperty(edge, property)"]
    
    EntityTag["types.EntityTag<br/>(with ID, timestamps)"]
    EdgeTag["types.EdgeTag<br/>(with ID, timestamps)"]
    
    GetEntityTags["GetEntityTags(entity, since, names...)"]
    GetEdgeTags["GetEdgeTags(edge, since, names...)"]
    
    Property -->|input| CreateEntityProp
    Entity -->|input| CreateEntityProp
    CreateEntityProp -->|returns| EntityTag
    
    Property -->|input| CreateEdgeProp
    Edge -->|input| CreateEdgeProp
    CreateEdgeProp -->|returns| EdgeTag
    
    Entity -->|query| GetEntityTags
    Edge -->|query| GetEdgeTags
    GetEntityTags -->|returns| EntityTag
    GetEdgeTags -->|returns| EdgeTag
```

### Example: Adding Properties to an Entity

```go
import (
    "github.com/owasp-amass/open-asset-model/general"
)

// Create an entity
entity, _ := repo.CreateAsset(&dns.FQDN{Name: "example.com"})

// Add a simple property
property := &general.SimpleProperty{
    PropertyName:  "source",
    PropertyValue: "passive_dns",
}

tag, err := repo.CreateEntityProperty(entity, property)
if err != nil {
    // Handle error
}

fmt.Printf("Tag ID: %s\n", tag.ID)
fmt.Printf("Property Name: %s\n", tag.Property.Name())
fmt.Printf("Property Value: %s\n", tag.Property.Value())
```

### Example: Adding Properties to an Edge

```go
// Create edge between entities
edge, _ := repo.CreateEdge(&types.Edge{
    Relation: &dns.BasicDNSRelation{
        Name: "dns_record",
        Header: dns.RRHeader{RRType: 5},
    },
    FromEntity: sourceEntity,
    ToEntity:   destEntity,
})

// Add property to the edge
property := &general.SimpleProperty{
    PropertyName:  "resolver",
    PropertyValue: "8.8.8.8",
}

tag, err := repo.CreateEdgeProperty(edge, property)
if err != nil {
    // Handle error
}
```

### Example: Retrieving Tags

```go
// Get all tags for an entity
start := time.Now().Add(-24 * time.Hour)

allTags, err := repo.GetEntityTags(entity, start)
if err != nil {
    // Handle error
}

// Get tags with specific property names
specificTags, err := repo.GetEntityTags(entity, start, "source", "confidence")
if err != nil {
    // Handle error
}

for _, tag := range specificTags {
    fmt.Printf("Property: %s = %s\n", 
        tag.Property.Name(), tag.Property.Value())
}
```

### Tag Update Behavior

When you create a property that already exists (same name and value), the system updates the `LastSeen` timestamp. If you create a property with the same name but different value, it creates a new tag.

```go
// Create initial property
prop1 := &general.SimpleProperty{
    PropertyName:  "status",
    PropertyValue: "active",
}
tag1, _ := repo.CreateEntityProperty(entity, prop1)

time.Sleep(time.Second)

// Same property again - updates LastSeen
tag2, _ := repo.CreateEntityProperty(entity, prop1)
// tag1.ID == tag2.ID
// tag2.LastSeen > tag1.LastSeen

// Different value - creates new tag
prop1.PropertyValue = "inactive"
tag3, _ := repo.CreateEntityProperty(entity, prop1)
// tag3.ID != tag1.ID (new tag created)
```

---

## Deleting Data

The repository provides methods to delete entities, edges, and tags.

### Example: Deleting an Edge

```go
err := repo.DeleteEdge(edgeID)
if err != nil {
    // Handle error
}
```

### Example: Deleting an Entity

```go
err := repo.DeleteEntity(entityID)
if err != nil {
    // Handle error
}

// Verify deletion
_, err = repo.FindEntityById(entityID)
// err will be non-nil (entity not found)
```

### Example: Deleting Tags

```go
// Delete entity tag
err := repo.DeleteEntityTag(tagID)
if err != nil {
    // Handle error
}

// Delete edge tag
err = repo.DeleteEdgeTag(tagID)
if err != nil {
    // Handle error
}
```

---

## Complete Example: Building a Simple Asset Graph

This example demonstrates a typical workflow: creating entities, linking them with edges, and adding metadata.

```go
package main

import (
    "fmt"
    "net/netip"
    "time"
    
    "github.com/owasp-amass/asset-db/repository"
    "github.com/owasp-amass/asset-db/types"
    "github.com/owasp-amass/open-asset-model/dns"
    "github.com/owasp-amass/open-asset-model/general"
    "github.com/owasp-amass/open-asset-model/network"
)

func main() {
    // Initialize repository
    repo, err := repository.New("sqlite", "example.db")
    if err != nil {
        panic(err)
    }
    defer repo.Close()
    
    // Create an FQDN entity
    fqdn, err := repo.CreateAsset(&dns.FQDN{Name: "www.example.com"})
    if err != nil {
        panic(err)
    }
    fmt.Printf("Created FQDN: %s\n", fqdn.ID)
    
    // Create an IP address entity
    ip, _ := netip.ParseAddr("192.0.2.1")
    ipAddr, err := repo.CreateAsset(&network.IPAddress{
        Address: ip,
        Type:    "IPv4",
    })
    if err != nil {
        panic(err)
    }
    fmt.Printf("Created IP: %s\n", ipAddr.ID)
    
    // Create DNS A record relationship
    edge, err := repo.CreateEdge(&types.Edge{
        Relation: &dns.BasicDNSRelation{
            Name: "dns_record",
            Header: dns.RRHeader{
                RRType: 1, // A record
                TTL:    300,
            },
        },
        FromEntity: fqdn,
        ToEntity:   ipAddr,
    })
    if err != nil {
        panic(err)
    }
    fmt.Printf("Created edge: %s\n", edge.ID)
    
    // Add metadata to the FQDN
    sourceTag, err := repo.CreateEntityProperty(fqdn, &general.SimpleProperty{
        PropertyName:  "source",
        PropertyValue: "certificate_transparency",
    })
    if err != nil {
        panic(err)
    }
    fmt.Printf("Added tag: %s\n", sourceTag.ID)
    
    // Query all outgoing edges from the FQDN
    start := time.Now().Add(-1 * time.Hour)
    edges, err := repo.OutgoingEdges(fqdn, start)
    if err != nil {
        panic(err)
    }
    
    fmt.Printf("\nFound %d outgoing edges\n", len(edges))
    for _, e := range edges {
        fmt.Printf("  Edge: %s -> %s (%s)\n",
            e.FromEntity.ID,
            e.ToEntity.ID,
            e.Relation.Label())
    }
    
    // Query tags on the FQDN
    tags, err := repo.GetEntityTags(fqdn, start)
    if err != nil {
        panic(err)
    }
    
    fmt.Printf("\nFound %d tags\n", len(tags))
    for _, tag := range tags {
        fmt.Printf("  %s = %s\n",
            tag.Property.Name(),
            tag.Property.Value())
    }
}
```

## See Also

- [Asset Database Overview](./index.md)
- [PostgreSQL Setup](./postgres.md)
- [Caching](./caching.md)
- [API Reference](./api-reference.md)
