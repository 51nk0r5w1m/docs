# Data Flow

Understanding how assets flow through Amass helps optimize enumeration strategies and interpret results.

## Asset Discovery Flow

## Enumeration Workflow

The `enum` command follows this sequence:

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Engine
    participant GraphQL
    participant Plugins
    participant Database

    User->>CLI: amass enum -d example.com
    CLI->>CLI: Parse arguments
    CLI->>CLI: Load configuration
    CLI->>Engine: Connect to GraphQL
    Engine->>GraphQL: Create session
    GraphQL-->>Engine: Session ID
    CLI->>GraphQL: Submit seed assets

    loop Discovery Loop
        GraphQL->>Plugins: Process queue
        Plugins->>Plugins: DNS/API/WHOIS queries
        Plugins->>Database: Store discoveries
        Plugins->>GraphQL: New assets to queue
    end

    CLI->>GraphQL: Poll statistics
    GraphQL-->>CLI: Progress updates
    User->>CLI: Ctrl+C or timeout
    CLI->>GraphQL: Terminate session
    CLI->>Database: Aggregate results
    CLI-->>User: Display findings
```

## Asset Relationship Building

As assets are discovered, Amass builds a relationship graph following the Open Asset Model:

### Relationship Types

| Source | Relation | Target |
|--------|----------|--------|
| FQDN | `resolves_to` | IP Address |
| IP Address | `belongs_to` | Netblock |
| Netblock | `member_of` | ASN |
| ASN | `owned_by` | Organization |
| FQDN | `registered_to` | Organization |
| FQDN | `protected_by` | Certificate |
| Certificate | `issued_to` | Organization |
| Person | `works_for` | Organization |
| FQDN | `contains` | FQDN (subdomain) |

## DNS Resolution Flow

### Resolver Rate Limiting

| Resolver Type | Default QPS | Purpose |
|---------------|-------------|---------|
| Baseline | 15 | Reliable fallback |
| Public | 5 | Distributed load |
| Custom | Configurable | User preference |
| Trusted | 15+ | High-volume queries |

## Caching Strategy

### Cache Layers

| Layer | Storage | TTL | Purpose |
|-------|---------|-----|---------|
| **Memory** | In-process | Session | Rapid deduplication |
| **File** | Disk | Configurable | Cross-session persistence |
| **Database** | SQLite/PostgreSQL | Permanent | Long-term storage |

## Queue Processing

The session queue manages asset processing state:

```mermaid
stateDiagram-v2
    [*] --> Queued: Asset Discovered
    Queued --> Dequeued: Next() called
    Dequeued --> Processing: Handler assigned
    Processing --> Completed: Success
    Processing --> Failed: Error
    Completed --> [*]: Removed
    Failed --> Queued: Retry
```

### Queue Operations

| Operation | Description |
|-----------|-------------|
| `Append` | Add new asset to queue |
| `Next` | Retrieve next unprocessed asset |
| `Processed` | Mark asset as completed |
| `Delete` | Remove from queue |

## Output Generation

### Output Commands

| Command | Purpose | Formats |
|---------|---------|---------|
| `enum` | Discovery results | Text, JSON |
| `subs` | Subdomain listing | Text, JSON |
| `assoc` | Relationship analysis | Text, JSON |
| `track` | Change detection | Text, JSON |
| `viz` | Visualizations | D3, DOT, GEXF |

## Feedback Loops

Discoveries feed back into the processing queue, creating cascading discovery:

### Example Cascade

```
example.com (seed)
    │
    ├─► DNS TXT → mail.example.com
    │   └─► Resolves to 192.0.2.10
    │       └─► Netblock 192.0.2.0/24
    │           └─► ASN 64496
    │               └─► Example Inc
    │
    ├─► Certificate → *.example.com
    │   └─► SAN: api.example.com
    │       └─► New FQDN queued
    │
    └─► Brute Force → www.example.com
        └─► HTTP Probe → Redirects to cdn.example.com
            └─► New FQDN queued
```

## Performance Considerations

### Parallelism

| Component | Concurrency |
|-----------|-------------|
| DNS Resolvers | Pool of resolvers with individual rate limits |
| HTTP Probes | Configurable concurrent connections |
| API Calls | Per-service rate limiting |
| Queue Processing | Multiple handlers per asset type |

### Optimization Tips

!!! tip "Enumeration Performance"
    - Use `-dns-qps` to control overall DNS query rate
    - Configure trusted resolvers (`-tr`) for higher throughput
    - Use `-passive` mode for stealth reconnaissance
    - Set appropriate `-timeout` to bound enumeration time

## Technical Reference

The following diagrams detail the internal pipeline mechanics sourced from the engine codebase.

### End-to-End Data Flow (Internal)

```mermaid
graph TB
    subgraph "Input Layer"
        GraphQL["GraphQL API<br/>CreateAsset mutation"]
        CLI["CLI Input<br/>Domain/IP/CIDR"]
    end

    subgraph "Event Creation"
        Event["et.Event<br/>{Name, Entity, Session}"]
        Entity["dbt.Entity<br/>wraps oam.Asset"]
    end

    subgraph "Dispatcher"
        Dispatch["Dispatcher.DispatchEvent()"]
        SafeDispatch["safeDispatch()"]
        AppendPipeline["appendToPipeline()"]
    end

    subgraph "Session Queue"
        QueueDB["QueueDB (SQLite)<br/>queue.db in tmpdir"]
        QueueAppend["Append(entity)"]
        QueueNext["Next(atype, num)"]
    end

    subgraph "Pipeline System"
        FillQueues["fillPipelineQueues()"]
        AssetPipeline["AssetPipeline<br/>{Pipeline, Queue}"]
        PriorityStages["Priority 1-9 Stages"]
    end

    subgraph "Handler Execution"
        HandlerTask["handlerTask()"]
        Callback["Handler.Callback(event)<br/>Plugin-specific"]
    end

    subgraph "Data Storage"
        Cache["Cache<br/>cache.db (SQLite)"]
        CreateAsset["Cache.CreateAsset()<br/>Creates dbt.Entity"]
        CreateEdge["Cache.CreateEdge()<br/>Relationships"]
        DB["Persistent DB<br/>(Postgres/SQLite/Neo4j)"]
    end

    subgraph "Event Completion"
        CompletedCallback["completedCallback()"]
        Stats["SessionStats<br/>WorkItemsCompleted++"]
    end

    GraphQL --> Event
    CLI --> Event
    Event --> Entity
    Entity --> Dispatch

    Dispatch --> SafeDispatch
    SafeDispatch --> QueueAppend
    SafeDispatch --> AppendPipeline

    QueueAppend --> QueueDB
    QueueDB --> QueueNext
    QueueNext --> FillQueues

    FillQueues --> AssetPipeline
    AssetPipeline --> PriorityStages
    PriorityStages --> HandlerTask
    HandlerTask --> Callback

    Callback --> CreateAsset
    Callback --> CreateEdge
    CreateAsset --> Cache
    CreateEdge --> Cache

    Cache --> DB

    Callback --> Dispatch

    HandlerTask --> CompletedCallback
    CompletedCallback --> Stats
```

### Safe Dispatch Logic

```mermaid
graph TD
    Start["safeDispatch(event)"]
    CheckPipeline{"GetPipeline(assetType)<br/>exists?"}
    CheckQueued{"session.Queue().Has(entity)<br/>already queued?"}
    Append["session.Queue().Append(entity)"]
    IncrementStats["stats.WorkItemsTotal++"]
    CheckMeta{"event.Meta != nil?"}
    AppendToPipeline["appendToPipeline(event)"]
    End["Return"]

    Start --> CheckPipeline
    CheckPipeline -->|No pipeline| End
    CheckPipeline -->|Pipeline exists| CheckQueued
    CheckQueued -->|Already queued| End
    CheckQueued -->|Not queued| Append
    Append --> IncrementStats
    IncrementStats --> CheckMeta
    CheckMeta -->|No meta| End
    CheckMeta -->|Has meta| AppendToPipeline
    AppendToPipeline --> End
```

### Priority-Based Pipeline Construction

```mermaid
graph LR
    subgraph "Pipeline Construction"
        BuildPipelines["BuildPipelines()"]
        BuildAssetPipeline["buildAssetPipeline(atype)"]
        AssetPipeline["AssetPipeline<br/>{Pipeline, Queue}"]
    end

    subgraph "Stage Creation"
        Priority1["Priority 1 Stage<br/>DNS-TXT"]
        Priority2["Priority 2 Stage<br/>DNS-CNAME"]
        Priority3["Priority 3 Stage<br/>DNS-IP"]
        Priority4["Priority 4 Stage<br/>DNS-Subs"]
        Priority5["Priority 5 Stage<br/>DNS-Apex"]
        Priorities6to9["Priorities 6-9<br/>API/Enrichment"]
    end

    BuildPipelines --> BuildAssetPipeline
    BuildAssetPipeline --> Priority1
    Priority1 --> Priority2
    Priority2 --> Priority3
    Priority3 --> Priority4
    Priority4 --> Priority5
    Priority5 --> Priorities6to9
    Priorities6to9 --> AssetPipeline
```

### Handler Execution and Transformation Filtering

```mermaid
graph TD
    Start["handlerTask() receives EventDataElement"]
    CheckDone{"ctx.Done() or<br/>session.Done()?"}
    GetTransforms["transformationsByType(config, assetType)"]
    CheckExcludes{"allExcludesPlugin()?"}
    CheckMatch{"Plugin matches transformation<br/>or transform.To?"}
    ExecuteCallback["handler.Callback(event)"]
    ReturnData["Return EventDataElement"]
    SkipHandler["Skip handler execution"]

    Start --> CheckDone
    CheckDone -->|Terminated| ReturnData
    CheckDone -->|Active| GetTransforms
    GetTransforms --> CheckExcludes
    CheckExcludes -->|Excluded| SkipHandler
    CheckExcludes -->|Not excluded| CheckMatch
    CheckMatch -->|Match| ExecuteCallback
    CheckMatch -->|No match| SkipHandler
    ExecuteCallback --> ReturnData
    SkipHandler --> ReturnData
```

### Cache Staging and Persistence

```mermaid
graph LR
    subgraph "Handler Processing"
        Handler["Plugin Handler<br/>e.g., dnsCNAME.store()"]
    end

    subgraph "Cache Layer - cache.db (SQLite)"
        CreateAsset["session.Cache().CreateAsset(asset)"]
        CreateEdge["session.Cache().CreateEdge(edge)"]
        CreateProperty["session.Cache().CreateEdgeProperty(prop)"]
    end

    subgraph "Persistent Storage"
        SyncTimer["Periodic Sync<br/>(1 minute interval)"]
        PersistentDB["Persistent DB<br/>(Postgres/Neo4j/SQLite)"]
    end

    Handler --> CreateAsset
    Handler --> CreateEdge
    CreateEdge --> CreateProperty

    CreateAsset --> SyncTimer
    CreateEdge --> SyncTimer
    CreateProperty --> SyncTimer

    SyncTimer --> PersistentDB
```

### Cascading Discovery Pattern

```mermaid
graph TB
    Input["User Input: example.com"]
    FQDN1["FQDN Event<br/>example.com"]

    subgraph "First Cascade"
        TXT["DNS-TXT Handler<br/>Discovers: google-site-verification"]
        CNAME["DNS-CNAME Handler<br/>Discovers: alias.example.com"]
        IP["DNS-IP Handler<br/>Discovers: 192.0.2.1"]
        Subs["DNS-Subs Handler<br/>Discovers: ns1.example.com"]
    end

    subgraph "Second Cascade"
        FQDN2["FQDN Event<br/>alias.example.com"]
        FQDN3["FQDN Event<br/>ns1.example.com"]
        IPEvent["IPAddress Event<br/>192.0.2.1"]
    end

    subgraph "Third Cascade"
        IP2["DNS-IP Handler<br/>Discovers: 192.0.2.2"]
        Reverse["DNS-Reverse Handler<br/>Discovers: server.example.com"]
        Sweep["IP Sweep<br/>Discovers: 192.0.2.0/24"]
    end

    Input --> FQDN1
    FQDN1 --> TXT
    FQDN1 --> CNAME
    FQDN1 --> IP
    FQDN1 --> Subs

    CNAME --> FQDN2
    Subs --> FQDN3
    IP --> IPEvent

    FQDN2 --> IP2
    IPEvent --> Reverse
    IPEvent --> Sweep
```

### Event Completion Tracking

```mermaid
graph LR
    SinkFunc["Pipeline Sink<br/>makeSink()"]
    CChannel["Completion Channel<br/>dispatcher.cchan"]
    CompletedCallback["completedCallback()"]
    Stats["SessionStats<br/>WorkItemsCompleted++"]

    SinkFunc --> CChannel
    CChannel --> CompletedCallback
    CompletedCallback --> Stats
```

### FQDN to IP: Full Sequence

```mermaid
sequenceDiagram
    participant User
    participant GraphQL as GraphQL API
    participant Disp as Dispatcher
    participant Queue as SessionQueue
    participant Pipeline as FQDN Pipeline
    participant IP_Handler as DNS-IP Handler
    participant Cache
    participant IPPipeline as IPAddress Pipeline
    participant Rev_Handler as DNS-Reverse Handler

    User->>GraphQL: CreateAsset(example.com)
    GraphQL->>Cache: CreateAsset(FQDN)
    GraphQL->>Disp: DispatchEvent(FQDN event)
    Disp->>Queue: Append(FQDN entity)
    Disp->>Pipeline: append to FQDN pipeline queue

    Pipeline->>IP_Handler: Execute priority 3 handler
    IP_Handler->>IP_Handler: PerformQuery(A/AAAA)
    IP_Handler->>Cache: CreateAsset(IPAddress: 192.0.2.1)
    IP_Handler->>Cache: CreateEdge(FQDN->IPAddress)
    IP_Handler->>Disp: DispatchEvent(IPAddress event)

    Disp->>Queue: Append(IPAddress entity)
    Disp->>IPPipeline: append to IPAddress pipeline queue

    IPPipeline->>Rev_Handler: Execute priority 8 handler
    Rev_Handler->>Rev_Handler: PerformQuery(PTR)
    Rev_Handler->>Cache: CreateAsset(FQDN: server.example.com)
    Rev_Handler->>Cache: CreateEdge(PTR relationship)
    Rev_Handler->>Disp: DispatchEvent(new FQDN event)

    Note over Disp: Cascading continues...
```
