# Session & Scope Management

Amass implements isolated discovery sessions through the `SessionManager`, enabling concurrent enumerations with separate state, configuration, and caching.

## Session Architecture

```mermaid
flowchart TB
    subgraph Manager["Session Manager"]
        SM[SessionManager]
        SM --> S1[Session 1]
        SM --> S2[Session 2]
        SM --> S3[Session N]
    end

    subgraph Session["Session Components"]
        CONFIG[Configuration]
        DB[(session.db)]
        CACHE[session.cache]
        QUEUE[session.queue]
        RANGER[session.ranger]
    end

    S1 --> Session
```

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: NewSession()
    Created --> Configured: Load Config
    Configured --> Initialized: Create Resources
    Initialized --> Running: Start Discovery
    Running --> Processing: Process Queue
    Processing --> Running: More Assets
    Running --> Terminating: CancelSession()
    Terminating --> [*]: Release Resources
```

### Lifecycle Phases

| Phase | Operations |
|-------|------------|
| **Creation** | `manager.NewSession()` initializes session struct |
| **Configuration** | Load and validate settings |
| **Initialization** | Create temp directory, cache, queue, database |
| **Running** | Process discovery queue |
| **Termination** | `manager.CancelSession()` releases resources |

## Session Components

Each session maintains completely isolated data structures:

| Component | Type | Purpose |
|-----------|------|---------|
| `session.db` | SQLite | Per-session persistent storage |
| `session.cache` | In-memory | Asset deduplication cache |
| `session.queue` | QueueDB | Asset processing queue |
| `session.ranger` | CIDR Ranger | IP range matching |
| `session.config` | Config | Session-specific settings |

## Scope Configuration

### Scope Definition

Scope defines what targets are in-scope for discovery:

```mermaid
flowchart LR
    subgraph Scope["Scope Definition"]
        DOMAINS[Domains<br/>example.com]
        IPS[IP Addresses<br/>192.0.2.1]
        CIDRS[CIDR Blocks<br/>192.0.2.0/24]
        ASNS[ASN Numbers<br/>AS64496]
    end

    subgraph Validation
        CHECK{In Scope?}
    end

    ASSET[Discovered Asset] --> CHECK
    Scope --> CHECK
    CHECK -->|Yes| PROCESS[Process Asset]
    CHECK -->|No| DISCARD[Discard]
```

### Configuration Methods

| Method | Example |
|--------|---------|
| **CLI Flags** | `-d example.com -cidr 192.0.2.0/24` |
| **Config File** | `scope.domains: [example.com]` |
| **GraphQL API** | `createSessionFromJson(config: {...})` |

### Scope YAML Structure

```yaml
scope:
  domains:
    - example.com
    - example.org
  addresses:
    - 192.0.2.1
    - 192.0.2.10-20
  cidrs:
    - 192.0.2.0/24
    - 198.51.100.0/24
  asns:
    - 64496
    - 64497
  ports:
    - 80
    - 443
    - 8080
```

## Session Isolation

```mermaid
flowchart TB
    subgraph Session1["Session 1"]
        DB1[(Database)]
        CACHE1[Cache]
        QUEUE1[Queue]
    end

    subgraph Session2["Session 2"]
        DB2[(Database)]
        CACHE2[Cache]
        QUEUE2[Queue]
    end

    Session1 -.->|Isolated| Session2
```

### Isolation Properties

| Property | Isolation Level |
|----------|-----------------|
| **Database** | Separate SQLite file per session |
| **Cache** | Independent in-memory cache |
| **Queue** | Separate processing queue |
| **Configuration** | Session-specific settings |
| **Temporary Files** | Unique temp directory |

## Queue Management

### Queue Table Schema

```sql
CREATE TABLE Element (
    entity_id TEXT PRIMARY KEY,
    etype TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Queue Operations

| Operation | Description |
|-----------|-------------|
| `Append()` | Add new asset to queue |
| `Next()` | Retrieve next unprocessed asset |
| `Processed()` | Mark asset as completed |
| `Delete()` | Remove from queue |

### Queue State Flow

```mermaid
stateDiagram-v2
    [*] --> Pending: Append()
    Pending --> Processing: Next()
    Processing --> Completed: Processed()
    Completed --> [*]: Delete()
    Processing --> Pending: Error/Retry
```

## CIDR Ranger

The session maintains a CIDR ranger for efficient IP range matching:

```go
// Check if IP is in scope
inScope := session.ranger.Contains(net.ParseIP("192.0.2.50"))
```

### Ranger Operations

| Operation | Description |
|-----------|-------------|
| `Add(cidr)` | Add CIDR block to ranger |
| `Contains(ip)` | Check if IP is in any range |
| `Remove(cidr)` | Remove CIDR block |

## Concurrent Sessions

Multiple sessions can run concurrently with complete isolation:

```mermaid
sequenceDiagram
    participant Client1
    participant Client2
    participant Manager
    participant Session1
    participant Session2

    Client1->>Manager: NewSession(config1)
    Manager->>Session1: Create
    Client2->>Manager: NewSession(config2)
    Manager->>Session2: Create

    par Parallel Execution
        Client1->>Session1: Submit Assets
        Session1->>Session1: Process Queue
    and
        Client2->>Session2: Submit Assets
        Session2->>Session2: Process Queue
    end

    Client1->>Manager: CancelSession(1)
    Client2->>Manager: CancelSession(2)
```

## Session Statistics

Query session progress via GraphQL:

```graphql
query {
  sessionStats(sessionId: "session-123") {
    assetsDiscovered
    assetsProcessed
    queueSize
    duration
    status
  }
}
```

## Technical Reference

### Session Object

The `Session` struct represents the state of an active engine enumeration. Each session is uniquely identified by a UUID and contains all necessary components to execute an independent enumeration operation.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `uuid.UUID` | Unique identifier for the session |
| `log` | `*slog.Logger` | Structured JSON logger for session events |
| `ps` | `*pubsub.Logger` | Publish-subscribe logger for GraphQL subscriptions |
| `cfg` | `*config.Config` | Session configuration including scope and transformations |
| `scope` | `*scope.Scope` | Determines which assets are in-scope for enumeration |
| `db` | `repository.Repository` | Primary database connection (SQLite, Postgres, or Neo4j) |
| `cache` | `*cache.Cache` | Two-tier cache with temporary and persistent storage |
| `queue` | `*sessionQueue` | Work queue backed by SQLite database |
| `ranger` | `cidranger.Ranger` | CIDR range manager for IP address matching |
| `tmpdir` | `string` | Temporary directory for session-specific files |
| `stats` | `*et.SessionStats` | Work item counters (completed vs total) |
| `done` | `chan struct{}` | Signals session termination |
| `finished` | `bool` | Indicates if session has been terminated |

**Session Component Architecture**

```mermaid
graph TB
    subgraph Session["Session (session.go)"]
        ID["id: uuid.UUID"]
        Config["cfg: *config.Config"]
        Scope["scope: *scope.Scope"]
        Logger["log: *slog.Logger"]
        PubSub["ps: *pubsub.Logger"]
        Stats["stats: *SessionStats"]
        Done["done: chan struct{}"]
    end

    subgraph Storage["Storage Layer"]
        DB["db: repository.Repository<br/>(SQLite/Postgres/Neo4j)"]
        Cache["cache: *cache.Cache<br/>(2-tier: temp + persistent)"]
        Queue["queue: *sessionQueue<br/>(SQLite work queue)"]
        TmpDir["tmpdir: string<br/>(session-UUID/)"]
    end

    subgraph Network["Network Utilities"]
        Ranger["ranger: cidranger.Ranger<br/>(CIDR matching)"]
    end

    Session --> Storage
    Session --> Network

    Queue --> QueueDB["QueueDB<br/>queue.db (SQLite)"]
    Cache --> CacheDB["Cache DB<br/>cache.db (SQLite)"]
    TmpDir --> QueueDB
    TmpDir --> CacheDB
```

### Session Creation Flow

Sessions are created via the `CreateSession` function, which performs the following initialization sequence:

1. **Configuration Validation**: Uses provided config or creates default
2. **Session Object Creation**: Generates UUID, initializes scope, ranger, and stats
3. **Database Setup**: Determines primary database from config and establishes connection
4. **Temporary Directory**: Creates `session-{UUID}` directory in output path
5. **Cache Initialization**: Creates file-based cache repository with 1-minute TTL
6. **Queue Creation**: Initializes SQLite-backed work queue

```mermaid
sequenceDiagram
    participant Client
    participant CreateSession
    participant Session
    participant DB as "Database"
    participant FS as "Filesystem"
    participant Cache
    participant Queue

    Client->>CreateSession: CreateSession(cfg)
    CreateSession->>Session: new Session{id: uuid.New()}
    CreateSession->>Session: setupDB()
    Session->>DB: selectDBMS() + assetdb.New()
    DB-->>Session: repository.Repository
    CreateSession->>FS: os.MkdirTemp("session-{UUID}")
    FS-->>Session: tmpdir path
    CreateSession->>Cache: cache.New(fileRepo, db, 1min)
    Cache-->>Session: *cache.Cache
    CreateSession->>Queue: newSessionQueue(session)
    Queue-->>Session: *sessionQueue
    CreateSession-->>Client: Session
```

### Database Selection

The `selectDBMS` method determines which database to use based on the `GraphDBs` configuration. If no primary database is specified, SQLite is used by default.

| System | DSN Format | Default Pragmas |
|--------|-----------|-----------------|
| **SQLite** | `{output_dir}/assetdb.db?_pragma=...` | `busy_timeout(30000)`, `journal_mode(WAL)` |
| **Postgres** | `host={host} port={port} user={user} password={pass} dbname={db}` | None |
| **Neo4j** | `{url}` (`bolt://` or `neo4j://`) | None |

### Session Manager

The `manager` struct is a singleton that manages the lifecycle of all active sessions. It provides thread-safe operations using a `sync.RWMutex` and maintains a map of session UUIDs to Session objects.

```mermaid
graph TB
    subgraph Manager["manager (manager.go)"]
        RWMutex["sync.RWMutex"]
        Logger["logger: *slog.Logger"]
        Sessions["sessions: map[uuid.UUID]et.Session"]
    end

    subgraph Operations["Operations"]
        New["NewSession(cfg)<br/>→ CreateSession + AddSession"]
        Add["AddSession(s)<br/>→ Lock + append to map"]
        Cancel["CancelSession(id)<br/>→ Kill + cleanup"]
        Get["GetSession(id)<br/>→ RLock + lookup"]
        GetAll["GetSessions()<br/>→ RLock + collect all"]
        Shutdown["Shutdown()<br/>→ CancelSession for all"]
    end

    subgraph Session1["Session 1"]
        S1ID["UUID: abc-123"]
        S1Queue["Queue"]
        S1Cache["Cache"]
        S1DB["DB"]
    end

    subgraph Session2["Session 2"]
        S2ID["UUID: def-456"]
        S2Queue["Queue"]
        S2Cache["Cache"]
        S2DB["DB"]
    end

    Manager --> Operations
    Sessions --> Session1
    Sessions --> Session2
```

### Session Termination

The `CancelSession` method performs graceful termination:

1. **Signal Termination**: Calls `s.Kill()` to close the `done` channel
2. **Wait for Completion**: Polls session stats every 500ms until all work items are completed
3. **Cleanup Resources**: Closes queue DB, cache, nullifies CIDR ranger, removes temp directory, closes primary DB
4. **Remove from Map**: Deletes the session from the manager's map

```mermaid
sequenceDiagram
    participant Manager
    participant Session
    participant Stats
    participant Queue
    participant Cache
    participant DB
    participant FS

    Manager->>Session: Kill()
    Session->>Session: close(done)
    Session->>Session: finished = true

    loop Every 500ms
        Manager->>Stats: Lock() + check completed vs total
        alt completed >= total
            Stats-->>Manager: Exit loop
        end
    end

    Manager->>Queue: Close()
    Manager->>Cache: Close()
    Manager->>Session: ranger = nil
    Manager->>FS: os.RemoveAll(tmpdir)
    Manager->>DB: Close()
    Manager->>Manager: delete(sessions, id)
```

### Queue Operations Detail

**Work Queue Flow**

```mermaid
graph LR
    subgraph Dispatcher["Dispatcher"]
        DispatchEvent["DispatchEvent(e)"]
    end

    subgraph SessionQueue["sessionQueue"]
        Has["Has(e) → db.Has(e.ID)"]
        Append["Append(e) → db.Append(type, id)"]
        Next["Next(type, num) → db.Next()<br/>+ cache.FindEntityById()"]
        Processed["Processed(e) → db.Processed(id)"]
    end

    subgraph QueueDB["QueueDB (SQLite)"]
        Insert["INSERT Element<br/>{Type, EntityID, Processed=false}"]
        Select["SELECT * WHERE<br/>etype=? AND processed=false<br/>ORDER BY created_at LIMIT ?"]
        Update["UPDATE processed=true<br/>WHERE entity_id=?"]
    end

    subgraph Cache["Session Cache"]
        Find["FindEntityById(id)<br/>→ *dbt.Entity"]
    end

    DispatchEvent -->|"1. Check duplicate"| Has
    Has --> QueueDB
    DispatchEvent -->|"2. Schedule"| Append
    Append --> Insert

    Dispatcher -->|"3. Fill pipelines"| Next
    Next --> Select
    Next --> Find

    Dispatcher -->|"4. Mark done"| Processed
    Processed --> Update
```

### GraphQL Client/Server Architecture

Sessions are exposed via a GraphQL API that enables remote enumeration control. The API follows a client-server architecture where `amass enum` acts as a client and `amass engine` runs the server.

```mermaid
graph TB
    subgraph Client["Client (client.go)"]
        CreateSess["CreateSession(cfg)<br/>→ createSessionFromJson mutation"]
        CreateAsset["CreateAsset(asset, token)<br/>→ createAsset mutation"]
        TermSess["TerminateSession(token)<br/>→ terminateSession mutation"]
        GetStats["SessionStats(token)<br/>→ sessionStats query"]
        Subscribe["Subscribe(token)<br/>→ logMessages subscription"]
    end

    subgraph Server["Server Resolvers (schema.resolvers.go)"]
        ResolvCreate["CreateSessionFromJSON<br/>(input.config)"]
        ResolvAsset["CreateAsset<br/>(input.sessionToken, data)"]
        ResolvTerm["TerminateSession<br/>(sessionToken)"]
        ResolvStats["SessionStats<br/>(sessionToken)"]
        ResolvLogs["LogMessages<br/>(sessionToken)"]
    end

    subgraph SessionMgr["SessionManager"]
        NewSession["NewSession(cfg)"]
        GetSession["GetSession(token)"]
        CancelSession["CancelSession(token)"]
    end

    subgraph DispatcherNode["Dispatcher"]
        DispatchEvent["DispatchEvent(event)"]
    end

    CreateSess -->|HTTP POST| ResolvCreate
    ResolvCreate --> NewSession
    NewSession -->|Return token| Client

    CreateAsset -->|HTTP POST| ResolvAsset
    ResolvAsset --> GetSession
    ResolvAsset --> DispatchEvent

    TermSess -->|HTTP POST| ResolvTerm
    ResolvTerm --> CancelSession

    GetStats -->|HTTP POST| ResolvStats
    ResolvStats --> GetSession

    Subscribe -->|WebSocket| ResolvLogs
    ResolvLogs --> GetSession
```

## Best Practices

!!! tip "Session Management"
    - Use separate sessions for different targets
    - Set appropriate timeouts to prevent runaway sessions
    - Monitor queue size to track progress
    - Clean up completed sessions to free resources

!!! warning "Resource Usage"
    Each session consumes memory and disk space. For large enumerations, ensure adequate system resources.
