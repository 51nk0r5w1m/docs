# Plugin Registry & Pipelines

## Purpose and Scope

This page explains the plugin registry and asset pipeline system, which orchestrates how plugins process events in Amass. The registry manages handler registration from plugins, constructs priority-ordered pipelines for each asset type, and coordinates execution of handlers across multiple concurrent sessions.

## System Architecture

The plugin registry and pipeline system consists of four primary components:

```mermaid
graph TB
    subgraph "Registry Core"
        Registry["registry struct<br/>(engine/registry)"]
        HandlersMap["handlers map[string]map[int][]*Handler"]
        PipelinesMap["pipelines map[AssetType]*AssetPipeline"]
    end
    
    subgraph "Plugin Layer"
        DNSPlugin["dnsPlugin<br/>(dns.NewDNS)"]
        GLEIFPlugin["gleifPlugin"]
        HTTPPlugin["httpPlugin"]
    end
    
    subgraph "Handler Registration"
        Handler1["Handler<br/>Priority: 1<br/>TXT Handler"]
        Handler2["Handler<br/>Priority: 2<br/>CNAME Handler"]
        Handler3["Handler<br/>Priority: 3<br/>IP Handler"]
    end
    
    subgraph "Pipeline Infrastructure"
        AssetPipeline["AssetPipeline struct"]
        PipelineObj["Pipeline<br/>(caffix/pipeline)"]
        PipelineQueue["PipelineQueue struct<br/>(queue.Queue wrapper)"]
    end
    
    subgraph "Execution"
        Stage1["Stage: FQDN - Priority 1<br/>FIFO or FixedPool"]
        Stage2["Stage: FQDN - Priority 2<br/>Parallel"]
        Stage3["Stage: FQDN - Priority 3<br/>FixedPool"]
    end
    
    DNSPlugin -->|RegisterHandler| Registry
    GLEIFPlugin -->|RegisterHandler| Registry
    HTTPPlugin -->|RegisterHandler| Registry
    
    Registry -->|stores by type+priority| HandlersMap
    Registry -->|BuildPipelines| PipelinesMap
    
    HandlersMap -->|constructs| AssetPipeline
    
    AssetPipeline --> PipelineObj
    AssetPipeline --> PipelineQueue
    
    PipelineObj --> Stage1
    PipelineObj --> Stage2
    PipelineObj --> Stage3
    
    Handler1 --> Stage1
    Handler2 --> Stage2
    Handler3 --> Stage3
```

## Registry Component

The `registry` struct maintains the central index of all registered handlers and constructs asset pipelines on demand.

### Registry Data Structure

| Field | Type | Purpose |
|-------|------|---------|
| `handlers` | `map[string]map[int][]*Handler` | Maps asset type → priority → handlers |
| `pipelines` | `map[AssetType]*AssetPipeline` | Maps asset type → constructed pipeline |
| `logger` | `*slog.Logger` | Logging instance |

The two-level map structure enables efficient pipeline construction by iterating through priorities in order:

- **First level:** Asset type (e.g., `"FQDN"`, `"IPAddress"`)
- **Second level:** Priority integer (1–9)
- **Value:** Array of handlers at that priority

## Handler Structure

A `Handler` defines how a plugin processes a specific event type:

```mermaid
graph LR
    subgraph "Handler Definition"
        Handler["Handler struct"]
        Plugin["Plugin interface"]
        Name["Name: 'DNS-TXT'"]
        Priority["Priority: 1"]
        MaxInst["MaxInstances: 50"]
        EventType["EventType: FQDN"]
        Transforms["Transforms: ['FQDN']"]
        Callback["Callback: func(*Event) error"]
    end
    
    Handler --> Plugin
    Handler --> Name
    Handler --> Priority
    Handler --> MaxInst
    Handler --> EventType
    Handler --> Transforms
    Handler --> Callback
```

### Handler Fields

| Field | Type | Description |
|-------|------|-------------|
| `Plugin` | `Plugin` | Reference to parent plugin |
| `Name` | `string` | Unique handler identifier (e.g., `"DNS-TXT"`) |
| `Priority` | `int` | Execution order (1–9, lower = earlier) |
| `MaxInstances` | `int` | Concurrent execution limit (0 = unlimited) |
| `EventType` | `oam.AssetType` | Asset type this handler processes |
| `Transforms` | `[]string` | Allowed transformation outputs |
| `Callback` | `func(*Event) error` | Processing function |

## Handler Registration Process

Plugins register handlers during their `Start()` method:

```mermaid
sequenceDiagram
    participant P as dnsPlugin
    participant R as Registry
    participant HM as handlers map
    
    P->>P: Start(registry)
    P->>P: Create dnsTXT handler
    P->>R: RegisterHandler(&Handler{<br/>Name: "DNS-TXT"<br/>Priority: 1<br/>EventType: FQDN<br/>Callback: dnsTXT.check})
    R->>HM: Store in handlers["FQDN"][1]
    
    P->>P: Create dnsCNAME handler
    P->>R: RegisterHandler(&Handler{<br/>Name: "DNS-CNAME"<br/>Priority: 2<br/>EventType: FQDN})
    R->>HM: Store in handlers["FQDN"][2]
    
    P->>P: Create dnsIP handler
    P->>R: RegisterHandler(&Handler{<br/>Name: "DNS-IP"<br/>Priority: 3<br/>EventType: FQDN<br/>Transforms: ["IPAddress"]})
    R->>HM: Store in handlers["FQDN"][3]
```

### DNS Plugin Registration Example

The DNS plugin registers six handlers:

| Handler | Priority | Event Type | Transforms | Purpose |
|---------|----------|------------|------------|---------|
| DNS-TXT | 1 | FQDN | `["FQDN"]` | Extract organization IDs from TXT records |
| DNS-CNAME | 2 | FQDN | `["FQDN"]` | Resolve CNAME aliases |
| DNS-IP | 3 | FQDN | `["IPAddress"]` | Resolve A/AAAA records to IP addresses |
| DNS-Subdomains | 4 | FQDN | `["FQDN"]` | Enumerate NS/MX/SRV subdomains |
| DNS-Apex | 5 | FQDN | `["FQDN"]` | Build domain hierarchy relationships |
| DNS-Reverse | 8 | IPAddress | `["FQDN"]` | Reverse DNS PTR lookups |

## Pipeline Construction

The registry builds pipelines after all plugins have registered their handlers via `BuildPipelines()`:

```mermaid
graph TD
    Start["BuildPipelines()"] --> IterTypes["Iterate asset types<br/>in handlers map"]
    IterTypes --> BuildOne["buildAssetPipeline(atype)"]
    
    BuildOne --> IterPrio["For priority 1 to 9"]
    IterPrio --> CheckHandlers{"handlers[atype][priority]<br/>exists?"}
    CheckHandlers -->|No| NextPrio["Next priority"]
    NextPrio --> IterPrio
    
    CheckHandlers -->|Yes| CountHandlers{"len(handlers) == 1?"}
    
    CountHandlers -->|Yes| CheckMax{"MaxInstances > 0?"}
    CheckMax -->|Yes| FixedPool["pipeline.FixedPool(id, task, max)"]
    CheckMax -->|No| FIFO["pipeline.FIFO(id, task)"]
    
    CountHandlers -->|No| Parallel["pipeline.Parallel(id, tasks...)"]
    
    FixedPool --> AddStage["Append to stages[]"]
    FIFO --> AddStage
    Parallel --> AddStage
    
    AddStage --> NextPrio
    IterPrio -->|Done| CreatePipeline["pipeline.NewPipeline(stages...)"]
    CreatePipeline --> CreateQueue["NewPipelineQueue()"]
    CreateQueue --> StartExec["go ExecuteBuffered(ctx, queue, sink)"]
    StartExec --> Return["Return AssetPipeline"]
```

### Pipeline Stage Types

| Stage Type | Condition | Behaviour |
|------------|-----------|-----------|
| **FixedPool** | Single handler, `MaxInstances > 0` | Worker pool with fixed concurrency |
| **FIFO** | Single handler, `MaxInstances == 0` | Sequential processing |
| **Parallel** | Multiple handlers at same priority | All handlers execute concurrently |

### Pipeline Execution

Each constructed pipeline runs in its own goroutine:

```go
go func(p *AssetPipeline) {
    if err := p.Pipeline.ExecuteBuffered(context.TODO(), p.Queue, makeSink(), bufsize); err != nil {
        r.logger.Error(fmt.Sprintf("Pipeline terminated: %v", err), "OAM type", atype)
    }
}(ap)
```

## AssetPipeline Structure

Each asset type has its own `AssetPipeline` instance:

```mermaid
graph TB
    subgraph "AssetPipeline for FQDN"
        AP["AssetPipeline struct"]
        Pipeline["Pipeline<br/>(caffix/pipeline)"]
        Queue["PipelineQueue"]
    end
    
    subgraph "Pipeline Stages (Priority Order)"
        S1["Stage 1: DNS-TXT<br/>FixedPool(50)"]
        S2["Stage 2: DNS-CNAME<br/>FixedPool(50)"]
        S3["Stage 3: DNS-IP<br/>FixedPool(50)"]
        S4["Stage 4: DNS-Subs<br/>FIFO"]
        S5["Stage 5: DNS-Apex<br/>FixedPool(50)"]
    end
    
    subgraph "Queue Contents"
        Q1["EventDataElement<br/>Entity: example.com"]
        Q2["EventDataElement<br/>Entity: mail.example.com"]
        Q3["EventDataElement<br/>Entity: www.example.com"]
    end
    
    AP --> Pipeline
    AP --> Queue
    
    Pipeline --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    
    Queue --> Q1
    Queue --> Q2
    Queue --> Q3
```

| Field | Type | Description |
|-------|------|-------------|
| `Pipeline` | `*pipeline.Pipeline` | The actual pipeline execution engine |
| `Queue` | `*PipelineQueue` | Input queue for events |

## PipelineQueue Implementation

The `PipelineQueue` wraps a standard queue and implements the `pipeline.InputSource` interface:

```mermaid
graph TB
    subgraph "PipelineQueue"
        PQ["PipelineQueue struct"]
        InnerQueue["queue.Queue<br/>(caffix/queue)"]
    end
    
    subgraph "InputSource Interface"
        Next["Next(ctx) bool<br/>Waits for data"]
        Data["Data() pipeline.Data<br/>Returns EventDataElement"]
        Error["Error() error<br/>Returns nil"]
    end
    
    subgraph "Queue Operations"
        Append["Append(data)<br/>Add to queue"]
        Signal["Signal()<br/>Notify waiters"]
        Len["Len() int<br/>Queue size"]
    end
    
    PQ --> InnerQueue
    PQ -.implements.-> Next
    PQ -.implements.-> Data
    PQ -.implements.-> Error
    
    InnerQueue --> Append
    InnerQueue --> Signal
    InnerQueue --> Len
```

**`Next(ctx context.Context) bool`** — Blocks until data is available or context is cancelled. Checks every 100 ms, also listens on the queue's signal channel.

**`Data() pipeline.Data`** — Dequeues the next `EventDataElement`, skipping events from terminated sessions.

**`Error() error`** — Always returns `nil`.

## Event Flow Through Pipelines

```mermaid
sequenceDiagram
    participant D as Dispatcher
    participant SQ as SessionQueue<br/>(SQLite)
    participant AP as AssetPipeline
    participant PQ as PipelineQueue
    participant S1 as Stage 1: Priority 1
    participant S2 as Stage 2: Priority 2
    participant S3 as Stage 3: Priority 3
    participant Sink as Sink Function
    participant CC as Completion Callback
    
    D->>D: DispatchEvent(event)
    D->>SQ: Append(entity)
    D->>PQ: Append(EventDataElement)
    PQ->>PQ: Signal waiters
    
    Note over AP: ExecuteBuffered running in goroutine
    AP->>PQ: Next(ctx)
    PQ-->>AP: true (data available)
    AP->>PQ: Data()
    PQ-->>AP: EventDataElement
    
    AP->>S1: Execute handlerTask
    S1->>S1: Check transformations
    S1->>S1: handler.Callback(event)
    S1->>D: DispatchEvent (new events)
    S1-->>AP: EventDataElement (modified)
    
    AP->>S2: Execute handlerTask
    S2->>S2: handler.Callback(event)
    S2->>D: DispatchEvent (new events)
    S2-->>AP: EventDataElement
    
    AP->>S3: Execute handlerTask
    S3->>S3: handler.Callback(event)
    S3->>D: DispatchEvent (new events)
    S3-->>AP: EventDataElement
    
    AP->>Sink: Send to sink
    Sink->>CC: Send on completion channel
    CC->>D: completedCallback
    D->>D: Increment WorkItemsCompleted
```

## Handler Task Execution

Each handler in a pipeline stage executes via the `handlerTask` wrapper function:

```mermaid
graph TD
    Start["handlerTask(handler)"] --> Check1{"data == nil?"}
    Check1 -->|Yes| ErrNil["Return error"]
    Check1 -->|No| Extract["Extract EventDataElement"]
    
    Extract --> Check2{"Context done?"}
    Check2 -->|Yes| SendQueue["Send to completion queue"]
    Check2 -->|No| Check3{"Session done?"}
    Check3 -->|Yes| SendQueue
    
    Check3 -->|No| GetTransforms["Get transformations<br/>from session config"]
    GetTransforms --> Check4{"len(transformations) > 0?"}
    
    Check4 -->|No| Execute["Execute handler.Callback(event)"]
    Check4 -->|Yes| CheckExclude{"allExcludesPlugin?"}
    
    CheckExclude -->|Yes| Skip["Skip handler"]
    CheckExclude -->|No| CheckMatch{"tosContainPlugin OR<br/>CheckTransformations?"}
    
    CheckMatch -->|Yes| Execute
    CheckMatch -->|No| Skip
    
    Execute --> CheckErr{"Error from callback?"}
    CheckErr -->|Yes| AppendErr["Append to ede.Error"]
    CheckErr -->|No| Return
    AppendErr --> Return["Return data"]
    Skip --> Return
    SendQueue --> ReturnNil["Return nil"]
```

### Transformation Filtering

Handler task applies transformation filtering before executing the callback:

1. **Get transformations** — Retrieves transformations from session config for the event's asset type
2. **Check "all" exclusions** — If transformation is `"all → all exclude: [pluginName]"`, skip this plugin
3. **Check plugin match** — If transformation explicitly lists this plugin, execute
4. **Check transform types** — If handler's `Transforms` field matches transformation's "to" types, execute

!!! info "Why transformation filtering?"
    This system lets users control which plugins process which asset types via configuration, without modifying plugin code.

## Priority System

### DNS Plugin Priority Assignment

| Priority | Handler | Rationale |
|----------|---------|-----------|
| 1 | DNS-TXT | Extract organization IDs first for enrichment |
| 2 | DNS-CNAME | Resolve aliases before IP lookup |
| 3 | DNS-IP | Resolve to IPs after CNAME chain |
| 4 | DNS-Subdomains | Enumerate NS/MX after basic resolution |
| 5 | DNS-Apex | Build hierarchy after subdomain discovery |
| 8 | DNS-Reverse | Reverse lookup after forward resolution |

### Priority Guidelines

| Range | Stage |
|-------|-------|
| 1–3 | Critical early processing (TXT, CNAME, IP resolution) |
| 4–6 | Secondary discovery (subdomains, company search) |
| 7–9 | Enrichment and follow-up (company data, reverse DNS) |

Handlers at the same priority from different plugins execute in **parallel**; from the same plugin they execute **sequentially**.

## Concurrency Control

| `MaxInstances` | Behaviour | Stage Type |
|----------------|-----------|------------|
| `0` | Unlimited / sequential | FIFO |
| `> 0` | Fixed worker pool | FixedPool |

Most DNS handlers use `MaxInstances: support.MaxHandlerInstances` (typically 50), creating a `FixedPool` stage that processes up to 50 DNS queries concurrently per pipeline.

## Dispatcher Integration

The dispatcher maintains pipelines by periodically refilling their queues from session queues:

```mermaid
graph TB
    subgraph "Dispatcher Loop"
        Tick["Every 1 second"]
        Fill["fillPipelineQueues()"]
    end
    
    subgraph "Fill Process"
        GetSess["Get all sessions"]
        IterTypes["For each asset type"]
        CheckQLen{"Pipeline queue < 100?"}
        NextEnt["Session.Queue().Next(type, num)"]
        CreateEvt["Create Event"]
        Append["appendToPipeline(event)"]
    end
    
    Tick --> Fill
    Fill --> GetSess
    GetSess --> IterTypes
    IterTypes --> CheckQLen
    CheckQLen -->|Yes| NextEnt
    CheckQLen -->|No| IterTypes
    NextEnt --> CreateEvt
    CreateEvt --> Append
    Append --> IterTypes
```

## Error Handling

Pipeline execution collects errors in `EventDataElement`:

```go
if err := r.Callback(ede.Event); err != nil {
    ede.Error = multierror.Append(ede.Error, err)
}
```

The sink function sends completed events (including accumulated errors) to the completion channel, where the dispatcher logs them. Errors do not stop pipeline processing — they are logged and the event is marked complete.

## Related

- [Engine Core](engine-core.md) — Overview of Dispatcher, SessionManager, and Registry
- [Event Dispatcher](event-dispatcher.md) — Event routing, queue filling, and completion callbacks
- [DNS Wildcard Detection](dns-wildcard.md) — Wildcard filtering in DNS resolution
- [DNS TTL & Caching](dns-caching.md) — Resolver pool, retry, and QPS management
