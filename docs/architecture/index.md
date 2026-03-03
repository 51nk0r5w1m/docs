# Architecture Overview

OWASP Amass implements an **event-driven plugin architecture** centered on a core engine that processes asset discovery through sophisticated coordination mechanisms. The system implements the Open Asset Model (OAM) to standardize cyber asset representation across a graph database backend.

## System Architecture

```mermaid
flowchart TB
    subgraph CLI["CLI Layer"]
        CMD[amass command]
        CMD --> ENUM[enum]
        CMD --> ENGINE[engine]
        CMD --> ASSOC[assoc]
        CMD --> SUBS[subs]
        CMD --> TRACK[track]
        CMD --> VIZ[viz]
    end

    subgraph Core["Engine Core"]
        DISP[Dispatcher]
        REG[Registry]
        SM[SessionManager]
        GQL[GraphQL Server]
    end

    subgraph Plugins["Plugin Ecosystem"]
        DNS[DNS Plugins]
        API[API Plugins]
        SVC[Service Discovery]
        WHOIS[WHOIS Plugins]
    end

    subgraph Data["Data Layer"]
        CACHE[(Cache)]
        GDB[(Graph Database)]
        QUEUE[(Session Queue)]
    end

    subgraph External["External Services"]
        RESOLVERS[DNS Resolvers]
        APIS[External APIs]
        WHOIS_SRV[WHOIS Servers]
    end

    ENUM & ENGINE --> GQL
    GQL --> DISP
    DISP --> REG
    REG --> DNS & API & SVC & WHOIS
    SM --> CACHE & QUEUE
    DNS & API & SVC & WHOIS --> GDB
    DNS --> RESOLVERS
    API --> APIS
    WHOIS --> WHOIS_SRV
```

## Core Components

### Engine Core

The central `AmassEngine` orchestrates discovery operations through these key subsystems:

| Component | Purpose |
|-----------|---------|
| **Dispatcher** | Routes events through registered handler pipelines, processing assets sequentially based on type and priority |
| **Registry** | Manages plugin registration and constructs processing pipelines dynamically |
| **SessionManager** | Coordinates concurrent discovery sessions with isolated state, configuration, and caching |
| **GraphQL Server** | Exposes endpoints for session management and real-time monitoring |

### Event Processing Pipeline

Events flow through a deterministic pipeline where the system maintains session context including cache, queue, and scope definitions throughout processing.

```mermaid
sequenceDiagram
    participant Client
    participant GraphQL
    participant Dispatcher
    participant Registry
    participant Handler
    participant Database

    Client->>GraphQL: Create Session
    GraphQL->>Dispatcher: Initialize
    Client->>GraphQL: Submit Asset
    GraphQL->>Dispatcher: Asset Discovery Event
    Dispatcher->>Registry: Get Handler Pipeline
    Registry-->>Dispatcher: Ordered Handlers
    loop For Each Handler
        Dispatcher->>Handler: Process Event
        Handler->>Handler: Execute Callback
        Handler-->>Dispatcher: New Assets
    end
    Dispatcher->>Database: Store Results
    Database-->>Client: Updated Graph
```

## Session Management

The `SessionManager` coordinates multiple concurrent discovery sessions with isolated configuration and state:

```mermaid
flowchart LR
    subgraph Session["Session Context"]
        DB[(session.db)]
        CACHE[session.cache]
        QUEUE[session.queue]
        RANGER[session.ranger]
    end

    CONFIG[Configuration] --> Session
    Session --> SCOPE{Scope Validation}
    SCOPE --> PROCESS[Asset Processing]
```

| Component | Description |
|-----------|-------------|
| `session.db` | SQLite persistent storage for the session |
| `session.cache` | In-memory asset cache for deduplication |
| `session.queue` | Processing queue managing asset flow |
| `session.ranger` | CIDR range matching for network scope |

## Multi-Layer Storage Architecture

```mermaid
flowchart TB
    subgraph Storage["Data Storage Layers"]
        direction TB
        L1[Cache Layer<br/>In-memory with TTL]
        L2[Graph Database<br/>SQLite / PostgreSQL]
        L3[Session Storage<br/>QueueDB with temp directories]
        L4[Asset Model<br/>OAM Entities & Edges]
    end

    L1 --> L2 --> L3 --> L4
```

### Database Support

| Backend | Use Case |
|---------|----------|
| **SQLite** | Local, single-user deployments |
| **PostgreSQL** | Enterprise concurrent access |

## Queue Management

The session queue uses SQLite with an `Element` table tracking processing state:

```mermaid
stateDiagram-v2
    [*] --> Pending: Asset Discovered
    Pending --> Processing: Dequeued
    Processing --> Completed: Handler Done
    Completed --> [*]: Removed
```

| Field | Purpose |
|-------|---------|
| `entity_id` | Unique asset identifier |
| `etype` | Asset type (FQDN, IP, etc.) |
| `processed` | Processing state flag |
| `created_at` | Queue entry timestamp |

## GraphQL API Interface

The engine exposes a GraphQL API for programmatic control:

### Mutations

| Operation | Description |
|-----------|-------------|
| `createSessionFromJson` | Initiate discovery sessions with configuration |
| `createAsset` | Submit seed assets for discovery |
| `terminateSession` | Stop running enumeration |

### Queries

| Operation | Description |
|-----------|-------------|
| `sessionStats` | Real-time discovery statistics |

### Subscriptions

| Operation | Description |
|-----------|-------------|
| `logMessages` | Stream session log messages |

**Default endpoint:** `http://127.0.0.1:4000/graphql`

## Configuration Priority

Settings are resolved in priority order:

```mermaid
flowchart LR
    CLI[Command-line Args<br/>Highest Priority] --> ENV[Environment Variables]
    ENV --> FILE[Configuration Files<br/>Lowest Priority]
    FILE --> FINAL[Final Configuration]
```

## External Service Integration

### DNS Resolution Infrastructure

The system manages multiple resolver pools with sophisticated rate limiting:

| Resolver Type | Description | Default QPS |
|---------------|-------------|-------------|
| **Baseline** | Google, Cloudflare, Quad9 | 15 |
| **Public Pool** | Dynamic from public-dns.info | 5 |
| **Custom** | User-specified resolvers | Configurable |
| **Trusted** | Higher rate limit resolvers | 15+ |

### DNS Operations

- Wildcard detection and filtering
- QPS rate limiting per resolver
- TTL-based response caching
- Response validation

## Technical Reference

The following diagrams provide deeper insight into Amass internals, sourced from the codebase analysis.

### Detailed Component Map

```mermaid
graph TB
    subgraph "User Interface Layer"
        MainCLI["cmd/amass/main.go<br/>Main CLI Entry Point"]
        EnumCmd["internal/enum<br/>Enum Client"]
        EngineCmd["internal/amass_engine<br/>Engine Server"]
        OAMTools["OAM Analysis Tools<br/>assoc, subs, track, viz"]
    end

    subgraph "Core Engine - engine/"
        Dispatcher["dispatcher.Dispatcher<br/>dispatcher/dispatcher.go"]
        SessionMgr["sessions.Manager<br/>sessions/manager.go"]
        Registry["registry.Registry<br/>registry/registry.go"]
        GraphQLAPI["api/graphql/server<br/>GraphQL API"]
    end

    subgraph "Plugin System"
        PluginInterface["types.Plugin interface<br/>types/registry.go"]
        HandlerRegistry["Handler Registration<br/>priority 1-9"]
        AssetPipelines["AssetPipeline<br/>types/registry.go"]
    end

    subgraph "Session Layer - engine/sessions/"
        Session["Session struct<br/>session.go"]
        SessionQueue["sessionQueue<br/>queue.go"]
        QueueDB["queuedb.QueueDB<br/>queuedb/queue_db.go"]
    end

    subgraph "Data Layer"
        Cache["cache.Cache<br/>asset-db/cache"]
        Repository["repository.Repository<br/>asset-db/repository"]
        SQLiteQueue["SQLite Queue DB<br/>queue.db"]
    end

    MainCLI --> EnumCmd
    MainCLI --> EngineCmd
    MainCLI --> OAMTools

    EnumCmd --> GraphQLAPI
    GraphQLAPI --> SessionMgr
    GraphQLAPI --> Dispatcher

    EngineCmd --> SessionMgr
    EngineCmd --> Dispatcher
    EngineCmd --> Registry

    Dispatcher --> SessionMgr
    Dispatcher --> Registry

    Registry --> PluginInterface
    Registry --> HandlerRegistry
    Registry --> AssetPipelines

    SessionMgr --> Session
    Session --> SessionQueue
    SessionQueue --> QueueDB
    Session --> Cache
    Session --> Repository

    QueueDB --> SQLiteQueue
    Cache --> Repository

    OAMTools --> Repository
```

### Engine Initialization

```mermaid
graph LR
    subgraph "Engine Initialization"
        EngineStart["Engine Start"]
        CreateManager["sessions.NewManager()"]
        CreateRegistry["registry.New()"]
        CreateDispatcher["dispatcher.NewDispatcher()"]
    end

    subgraph "Registry"
        Handlers["handlers map[string]map[int][]*Handler"]
        Pipelines["pipelines map[AssetType]*AssetPipeline"]
        BuildPipelines["BuildPipelines()"]
    end

    subgraph "Dispatcher"
        DispatchChan["dchan chan *Event"]
        CompleteChan["cchan chan *EventDataElement"]
        MaintainPipelines["maintainPipelines()"]
    end

    subgraph "SessionManager"
        Sessions["sessions map[uuid.UUID]Session"]
        NewSession["NewSession()"]
        CancelSession["CancelSession()"]
    end

    EngineStart --> CreateManager
    EngineStart --> CreateRegistry
    CreateManager --> CreateDispatcher
    CreateRegistry --> CreateDispatcher

    CreateRegistry --> Handlers
    CreateRegistry --> Pipelines

    CreateDispatcher --> DispatchChan
    CreateDispatcher --> CompleteChan
    CreateDispatcher --> MaintainPipelines

    CreateManager --> Sessions

    BuildPipelines --> Pipelines
    NewSession --> Sessions
```

### Event Dispatch Flow

```mermaid
graph TB
    subgraph "Event Structure"
        EventStruct["Event struct<br/>Name: string<br/>Entity: *dbt.Entity<br/>Meta: interface{}<br/>Dispatcher: Dispatcher<br/>Session: Session"]
    end

    subgraph "Event Creation and Dispatch"
        UserInput["User Input<br/>Domain/IP/CIDR"]
        CreateEvent["Create Event"]
        DispatchEvent["Dispatcher.DispatchEvent()"]
        SafeDispatch["safeDispatch()"]
    end

    subgraph "Queue Management"
        SessionQueue["Session.Queue()"]
        QueueAppend["queue.Append(entity)"]
        QueueDB["QueueDB.Append()"]
        WorkItemsTotal["stats.WorkItemsTotal++"]
    end

    subgraph "Pipeline Processing"
        FillQueues["fillPipelineQueues()"]
        GetPipeline["registry.GetPipeline(assetType)"]
        AssetPipeline["AssetPipeline<br/>Pipeline + Queue"]
        AppendPipeline["appendToPipeline()"]
    end

    subgraph "Handler Execution"
        HandlerTask["handlerTask()"]
        PluginCallback["handler.Callback(event)"]
        NewEvents["Generate New Events"]
        CompleteCallback["completedCallback()"]
        WorkItemsCompleted["stats.WorkItemsCompleted++"]
    end

    UserInput --> CreateEvent
    CreateEvent --> EventStruct
    EventStruct --> DispatchEvent
    DispatchEvent --> SafeDispatch

    SafeDispatch --> QueueAppend
    QueueAppend --> QueueDB
    SafeDispatch --> WorkItemsTotal
    SafeDispatch --> AppendPipeline

    FillQueues --> SessionQueue
    SessionQueue --> GetPipeline
    GetPipeline --> AssetPipeline
    AssetPipeline --> AppendPipeline

    AppendPipeline --> AssetPipeline
    AssetPipeline --> HandlerTask
    HandlerTask --> PluginCallback
    PluginCallback --> NewEvents
    PluginCallback --> CompleteCallback

    NewEvents --> DispatchEvent
    CompleteCallback --> WorkItemsCompleted
```

### Session Internals

```mermaid
graph TB
    subgraph "Session Structure"
        SessionFields["Session struct<br/>id: uuid.UUID<br/>cfg: *config.Config<br/>scope: *scope.Scope<br/>db: repository.Repository<br/>queue: *sessionQueue<br/>cache: *cache.Cache<br/>tmpdir: string<br/>stats: *SessionStats<br/>done: chan struct{}"]
    end

    subgraph "Session Creation"
        NewUUID["uuid.New()"]
        SetupDB["setupDB()"]
        CreateTmpDir["createTemporaryDir()"]
        CreateCache["cache.New(repo, db, ttl)"]
        CreateQueue["newSessionQueue(s)"]
    end

    subgraph "Database Selection"
        CheckPrimary["Find Primary DB"]
        PostgresPath["Postgres DSN"]
        SQLitePath["SQLite DSN"]
        Neo4jPath["Neo4j DSN"]
        InitStore["assetdb.New(dbtype, dsn)"]
    end

    subgraph "Temporary Directory Structure"
        TmpDir["session-{UUID}/"]
        CacheDB["cache.db<br/>SQLite cache repository"]
        QueueDBFile["queue.db<br/>SQLite work queue"]
    end

    SessionFields --> NewUUID
    NewUUID --> SetupDB
    SetupDB --> CheckPrimary
    CheckPrimary --> PostgresPath
    CheckPrimary --> SQLitePath
    CheckPrimary --> Neo4jPath
    PostgresPath --> InitStore
    SQLitePath --> InitStore
    Neo4jPath --> InitStore

    SetupDB --> CreateTmpDir
    CreateTmpDir --> TmpDir
    TmpDir --> CreateCache
    TmpDir --> CreateQueue

    CreateCache --> CacheDB
    CreateQueue --> QueueDBFile
```

### Storage Tier Details

```mermaid
graph TB
    subgraph "Storage Tier Overview"
        PersistentDB["Persistent Storage<br/>Primary Graph Database"]
        SessionCache["Session Cache<br/>cache.Cache"]
        WorkQueue["Work Queue<br/>queuedb.QueueDB"]
    end

    subgraph "Repository Layer"
        RepInterface["Repository interface<br/>CreateAsset()<br/>FindEntityById()<br/>Link()<br/>IncomingEdges()<br/>OutgoingEdges()"]
        SQLRepo["sqlrepo (Postgres/SQLite)"]
        Neo4jRepo["neo4j (Neo4j)"]
    end

    subgraph "Cache Layer"
        CacheStruct["Cache struct<br/>cache: repository.Repository<br/>store: repository.Repository<br/>ttl: time.Duration"]
        CacheCreate["CreateAsset()<br/>cache → store if needed"]
        TTLManagement["TTL-based expiration"]
    end

    subgraph "Queue Database"
        QueueStruct["QueueDB struct<br/>db: *gorm.DB"]
        ElementTable["Element table<br/>ID, etype, entity_id<br/>processed, created_at"]
        QueueIndexes["Indexes:<br/>idx_created_at, idx_etype<br/>idx_entity_id (unique)<br/>idx_processed"]
    end

    PersistentDB --> RepInterface
    RepInterface --> SQLRepo
    RepInterface --> Neo4jRepo

    SessionCache --> CacheStruct
    CacheStruct --> CacheCreate
    CacheStruct --> TTLManagement

    WorkQueue --> QueueStruct
    QueueStruct --> ElementTable
    ElementTable --> QueueIndexes
```

### GraphQL Client/Server Architecture

```mermaid
graph TB
    subgraph "Client: internal/enum"
        EnumCLI["enum command"]
        GraphQLClient["client.Client"]
        ClientOps["CreateSession()<br/>CreateAsset()<br/>TerminateSession()<br/>SessionStats()<br/>Subscribe()"]
    end

    subgraph "Communication Layer"
        HTTPClient["http.Client<br/>POST /graphql"]
        WSClient["websocket.Conn<br/>ws:// subscription"]
    end

    subgraph "Server: internal/amass_engine"
        EngineCLI["engine command"]
        GraphQLServer["GraphQL Server<br/>:4000/graphql"]
        Resolvers["schema.resolvers.go<br/>Mutation/Query/Subscription"]
    end

    subgraph "Engine Core"
        EngineDispatcher["Dispatcher"]
        EngineSessionMgr["SessionManager"]
        EngineRegistry["Registry"]
    end

    EnumCLI --> GraphQLClient
    GraphQLClient --> ClientOps
    ClientOps --> HTTPClient
    ClientOps --> WSClient

    HTTPClient --> GraphQLServer
    WSClient --> GraphQLServer

    GraphQLServer --> Resolvers
    Resolvers --> EngineDispatcher
    Resolvers --> EngineSessionMgr

    EngineSessionMgr --> EngineDispatcher
    EngineDispatcher --> EngineRegistry

    EngineCLI --> EngineSessionMgr
    EngineCLI --> EngineDispatcher
    EngineCLI --> EngineRegistry
```

### Configuration Loading

```mermaid
graph TB
    subgraph "Configuration Sources"
        CLIArgs["CLI Arguments<br/>--flag=value"]
        EnvVars["Environment Variables<br/>AMASS_CONFIG<br/>AMASS_DB_*<br/>AMASS_ENGINE_*"]
        YAMLFile["config.yaml<br/>User Config Dir"]
        SysYAML["config.yaml<br/>/etc/amass/"]
        Defaults["System Defaults<br/>config.NewConfig()"]
    end

    subgraph "Config Structure"
        ScopeSection["Scope *Scope<br/>Domains, IPs, ASNs, CIDRs, Ports"]
        ResolverSettings["Resolvers []string<br/>TrustedResolvers []string<br/>ResolversQPS int<br/>TrustedQPS int"]
        GraphDBSection["GraphDBs []*Database<br/>Primary, System, DSN"]
        EngineAPISection["EngineAPI *EngAPI<br/>URL, Host, Port, Path"]
        TransformSection["Transformations map[string]*Transformation"]
    end

    subgraph "Loading Process"
        AcquireConfig["AcquireConfig()"]
        LoadSettings["LoadSettings(path)"]
        UnmarshalYAML["yaml.Unmarshal"]
        LoadFunctions["loadDatabaseSettings()<br/>loadResolverSettings()<br/>loadTransformSettings()<br/>loadEngineSettings()"]
    end

    CLIArgs --> AcquireConfig
    EnvVars --> AcquireConfig
    YAMLFile --> AcquireConfig
    SysYAML --> AcquireConfig
    Defaults --> AcquireConfig

    AcquireConfig --> LoadSettings
    LoadSettings --> UnmarshalYAML
    UnmarshalYAML --> ScopeSection
    UnmarshalYAML --> ResolverSettings
    UnmarshalYAML --> GraphDBSection
    UnmarshalYAML --> EngineAPISection
    UnmarshalYAML --> TransformSection

    LoadSettings --> LoadFunctions
```

## Learn More

<div class="grid cards" markdown>

-   :material-puzzle:{ .lg .middle } **Plugin System**

    ---

    Understand how plugins extend Amass capabilities

    [:octicons-arrow-right-24: Plugin Architecture](plugins.md)

-   :material-api:{ .lg .middle } **Data Flow**

    ---

    How assets move through the discovery pipeline

    [:octicons-arrow-right-24: Data Flow](data-flow.md)

</div>
