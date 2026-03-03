# Event Dispatcher

## Purpose and Scope

The Event Dispatcher is the central routing component of the Amass engine that manages the flow of events from discovery sources to asset processing pipelines. It coordinates between sessions, plugin handlers, and work queues to ensure events are processed in priority order while maintaining session isolation and resource efficiency.

## Overview

The Event Dispatcher implements the `et.Dispatcher` interface and serves as the orchestration hub for all asset discovery events in Amass. When a plugin discovers a new asset (e.g., a domain, IP address, or organization), it creates an `Event` and submits it to the dispatcher via `DispatchEvent()`. The dispatcher validates the event, adds it to the appropriate session's work queue, and ensures it flows through the correct asset pipeline based on its type.

The dispatcher operates asynchronously via a main event loop (`maintainPipelines()`) that continuously:

- Processes incoming events from the dispatch channel
- Refills asset pipeline queues from session work queues
- Handles completion callbacks from finished event processing
- Monitors memory usage and triggers garbage collection when needed

## Architecture and Components

### Dispatcher Structure

The core dispatcher implementation is the `dis` struct, which contains all necessary components for event routing:

```mermaid
graph TB
    subgraph "dis struct (engine/dispatcher/dispatcher.go)"
        Logger["logger *slog.Logger"]
        Reg["reg et.Registry"]
        Mgr["mgr et.SessionManager"]
        Done["done chan struct{}"]
        Dchan["dchan chan *et.Event"]
        Cchan["cchan chan *et.EventDataElement"]
    end
    
    subgraph "External Dependencies"
        Registry["Registry<br/>GetPipeline(AssetType)"]
        SessionMgr["SessionManager<br/>GetSessions()"]
        Pipelines["AssetPipeline<br/>Queue.Append()"]
        Sessions["Session<br/>Queue().Append()"]
    end
    
    Reg --> Registry
    Mgr --> SessionMgr
    Registry --> Pipelines
    SessionMgr --> Sessions
    
    Dchan -.->|"DispatchEvent()"| IncomingEvents["Incoming Events"]
    Cchan -.->|"completedCallback()"| CompletedWork["Completed Work"]
```

The `dis` struct fields serve specific purposes:

| Field | Purpose |
|-------|---------|
| `logger` | Logs errors and debugging information |
| `reg` | References the plugin registry to retrieve asset pipelines |
| `mgr` | References the session manager to access active sessions |
| `done` | Signals shutdown to the maintenance goroutine |
| `dchan` | Receives events submitted via `DispatchEvent()` (buffer: 100) |
| `cchan` | Receives completion notifications from pipeline sink functions (buffer: 100) |

### Event and EventDataElement

Events flow through the dispatcher wrapped in two data structures:

| Structure | Purpose | Key Fields |
|-----------|---------|------------|
| `Event` | Represents a discovered asset ready for processing | `Name`, `Entity`, `Session`, `Dispatcher`, `Meta` |
| `EventDataElement` | Wraps events for pipeline execution with error tracking | `Event`, `Error`, `Queue` |

The transformation from `Event` to `EventDataElement` occurs in `appendToPipeline()` when events are added to asset pipeline queues.

## Event Flow Architecture

### Dispatch Path

```mermaid
graph TB
    PluginOrUser["Plugin/User<br/>Discovers Asset"]
    DispatchEvent["DispatchEvent(e *et.Event)"]
    Validation["Event Validation<br/>• e != nil<br/>• e.Session != nil<br/>• !e.Session.Done()<br/>• e.Entity != nil"]
    DchanSend["dchan <- e<br/>Send to dispatch channel"]
    
    MaintainLoop["maintainPipelines()<br/>Main Event Loop"]
    SelectBlock["select on channels"]
    ProcessEvent["safeDispatch(e)"]
    
    QueueCheck["Check if e.Session.Queue()<br/>.Has(e.Entity)"]
    QueueAppend["e.Session.Queue()<br/>.Append(e.Entity)"]
    StatsIncr["Session.Stats()<br/>.WorkItemsTotal++"]
    
    AppendPipeline["appendToPipeline(e)"]
    GetPipeline["reg.GetPipeline(<br/>e.Entity.Asset.AssetType())"]
    CreateEDE["NewEventDataElement(e)"]
    MarkProcessed["e.Session.Queue()<br/>.Processed(e.Entity)"]
    EnqueuePipeline["ap.Queue.Append(data)"]
    
    PipelineExec["Pipeline Execution<br/>Handler Tasks"]
    SinkFunc["Pipeline Sink<br/>cchan <- ede"]
    CompletedCallback["completedCallback(data)"]
    UpdateStats["Session.Stats()<br/>.WorkItemsCompleted++"]
    
    PluginOrUser --> DispatchEvent
    DispatchEvent --> Validation
    Validation -->|"valid"| DchanSend
    Validation -->|"invalid"| ErrorReturn["Return Error"]
    
    DchanSend --> MaintainLoop
    MaintainLoop --> SelectBlock
    SelectBlock -->|"case e := <-d.dchan"| ProcessEvent
    
    ProcessEvent --> QueueCheck
    QueueCheck -->|"already queued"| SkipReturn["Return nil<br/>(deduplicate)"]
    QueueCheck -->|"new"| QueueAppend
    QueueAppend --> StatsIncr
    StatsIncr -->|"e.Meta != nil"| AppendPipeline
    StatsIncr -->|"e.Meta == nil"| Done1["Done<br/>(queued only)"]
    
    AppendPipeline --> GetPipeline
    GetPipeline --> CreateEDE
    CreateEDE --> MarkProcessed
    MarkProcessed --> EnqueuePipeline
    
    EnqueuePipeline --> PipelineExec
    PipelineExec --> SinkFunc
    SinkFunc --> MaintainLoop
    SelectBlock -->|"case e := <-d.cchan"| CompletedCallback
    CompletedCallback --> UpdateStats
```

!!! info "Key behaviours"
    - **Validation**: Event, session, and entity must be non-nil; session must be active.
    - **Deduplication**: `Queue.Has()` silently drops events for entities already in the queue.
    - **Conditional dispatch**: Events with `e.Meta == nil` are queued but not immediately sent to a pipeline — they are picked up by the periodic queue-fill mechanism instead.

## Pipeline Queue Management

### Fill Algorithm

The dispatcher automatically refills asset pipeline queues every second via `fillPipelineQueues()`:

```mermaid
graph TB
    FillTimer["Timer fires<br/>(every 1 second)"]
    GetSessions["sessions := mgr.GetSessions()"]
    CheckEmpty["len(sessions) == 0?"]
    
    ScanPipelines["Scan all oam.AssetList<br/>for low queues"]
    CheckQueueSize["ap.Queue.Len() <<br/>MinPipelineQueueSize?"]
    CollectTypes["ptypes = append<br/>(low queue types)"]
    
    CalcRequestSize["numRequested =<br/>MaxPipelineQueueSize /<br/>len(sessions)"]
    
    IterSessions["For each session"]
    CheckSessionDone["s.Done()?"]
    IterTypes["For each atype in ptypes"]
    RequestEntities["entities := s.Queue()<br/>.Next(atype, numRequested)"]
    
    CreateEvent["Create Event:<br/>• Name = atype + entity.Key()<br/>• Entity = entity<br/>• Session = s"]
    AppendCall["appendToPipeline(e)"]
    
    FillTimer --> GetSessions
    GetSessions --> CheckEmpty
    CheckEmpty -->|"yes"| Return["Return"]
    CheckEmpty -->|"no"| ScanPipelines
    
    ScanPipelines --> CheckQueueSize
    CheckQueueSize -->|"< 100"| CollectTypes
    CheckQueueSize -->|">= 100"| NextType["Check next type"]
    CollectTypes --> CalcRequestSize
    
    CalcRequestSize --> IterSessions
    IterSessions --> CheckSessionDone
    CheckSessionDone -->|"done"| NextSession["Continue to<br/>next session"]
    CheckSessionDone -->|"active"| IterTypes
    
    IterTypes --> RequestEntities
    RequestEntities -->|"len > 0"| CreateEvent
    RequestEntities -->|"len == 0"| NextType2["Next type"]
    CreateEvent --> AppendCall
    AppendCall --> NextType2
```

**Queue thresholds:**

| Constant | Value | Purpose |
|----------|-------|---------|
| `MinPipelineQueueSize` | 100 | Refill trigger threshold |
| `MaxPipelineQueueSize` | 500 | Maximum items distributed per refill cycle |

!!! tip "Load balancing"
    `numRequested = MaxPipelineQueueSize / len(sessions)` distributes pipeline slots evenly across active sessions. With 5 sessions, each can contribute up to 100 items per cycle.

## Completion Callbacks

### Callback Processing

When a pipeline completes processing an event, it flows through a sink function:

```mermaid
graph LR
    PipelineTask["Pipeline Handler Task"]
    HandlerCallback["h.Callback(ede.Event)"]
    TaskReturn["Return data, error"]
    
    PipelineSink["Pipeline Sink Function"]
    ExtractEDE["Extract EventDataElement<br/>from pipeline.Data"]
    SendCompletion["ede.Queue <- ede<br/>(Send to cchan)"]
    
    MaintainLoop["maintainPipelines()<br/>select statement"]
    CaseReceive["case e := <-d.cchan"]
    CompletedCB["completedCallback(e)"]
    
    LogError["Log error if<br/>ede.Error != nil"]
    IncrementStats["stats.WorkItemsCompleted++"]
    
    PipelineTask --> HandlerCallback
    HandlerCallback --> TaskReturn
    TaskReturn --> PipelineSink
    
    PipelineSink --> ExtractEDE
    ExtractEDE --> SendCompletion
    
    SendCompletion --> MaintainLoop
    MaintainLoop --> CaseReceive
    CaseReceive --> CompletedCB
    
    CompletedCB --> LogError
    LogError --> IncrementStats
```

**Statistics tracking:** Each completion increments `Session.Stats().WorkItemsCompleted`, paired with the `WorkItemsTotal` increment in `safeDispatch()`. Clients can monitor progress via the GraphQL `sessionStats()` query.

**Error logging:** Errors are accumulated by handlers using `multierror`, allowing multiple handler failures to be tracked per event. Errors are logged in `completedCallback()` but do not halt processing.

## Memory Management

### Garbage Collection Strategy

The dispatcher monitors heap memory every 10 seconds and triggers GC when necessary:

```mermaid
graph TB
    MemTimer["Timer fires<br/>(every 10 seconds)"]
    CheckOnHeap["checkOnTheHeap()"]
    ReadMemStats["runtime.ReadMemStats<br/>(&mstats)"]
    
    CompareHeap["Compare:<br/>HeapAlloc vs NextGC"]
    CalcDiff["diff = HeapAlloc - NextGC"]
    CheckThreshold["bToMb(diff) > 500?"]
    
    TriggerGC["runtime.GC()"]
    Continue["Continue"]
    
    MemTimer --> CheckOnHeap
    CheckOnHeap --> ReadMemStats
    ReadMemStats --> CompareHeap
    CompareHeap -->|"HeapAlloc <= NextGC"| Continue
    CompareHeap -->|"HeapAlloc > NextGC"| CalcDiff
    CalcDiff --> CheckThreshold
    CheckThreshold -->|"yes"| TriggerGC
    CheckThreshold -->|"no"| Continue
```

!!! warning "GC threshold"
    GC is only triggered when `HeapAlloc - NextGC > 500 MB`. This prevents excessive GC cycles while ensuring memory doesn't grow unbounded during large enumeration sessions.

## Main Event Loop

### maintainPipelines() Structure

The dispatcher's main loop implements a multiplexed event processing model:

```mermaid
graph TB
    Start["maintainPipelines()<br/>Goroutine start"]
    InitTimers["Initialize timers:<br/>• ctick (1s) - queue refill<br/>• mtick (10s) - memory check"]
    
    OuterLoop["for loop<br/>(infinite)"]
    CheckDone1["select case <-d.done"]
    BreakLoop["break loop"]
    
    CheckMemTimer["case <-mtick.C"]
    MemCheck["checkOnTheHeap()"]
    ResetMem["mtick.Reset(10s)"]
    
    InnerSelect["select statement<br/>(inner)"]
    CheckCtick["case <-ctick.C"]
    FillQueues["fillPipelineQueues()"]
    ResetCtick["ctick.Reset(1s)"]
    
    CheckDispatch["case e := <-d.dchan"]
    SafeDispatch["safeDispatch(e)"]
    LogError["Log error if failed"]
    
    CheckCompletion["case e := <-d.cchan"]
    Completed["completedCallback(e)"]
    
    Start --> InitTimers
    InitTimers --> OuterLoop
    OuterLoop --> CheckDone1
    CheckDone1 -->|"shutdown"| BreakLoop
    CheckDone1 -->|"default"| CheckMemTimer
    
    CheckMemTimer -->|"timer fired"| MemCheck
    MemCheck --> ResetMem
    CheckMemTimer -->|"not ready"| InnerSelect
    ResetMem --> InnerSelect
    
    InnerSelect --> CheckCtick
    InnerSelect --> CheckDispatch
    InnerSelect --> CheckCompletion
    
    CheckCtick --> FillQueues
    FillQueues --> ResetCtick
    ResetCtick --> OuterLoop
    
    CheckDispatch --> SafeDispatch
    SafeDispatch --> LogError
    LogError --> OuterLoop
    
    CheckCompletion --> Completed
    Completed --> OuterLoop
```

**Nested select pattern:** Two nested select statements ensure:

- Shutdown is checked on every iteration
- Memory management runs at lower frequency (10 s)
- Event dispatch and completion callbacks are processed immediately when available
- Queue refills occur regularly without blocking other operations

## Integration with Registry and Sessions

```mermaid
graph TB
    subgraph "Dispatcher (engine/dispatcher)"
        DisStruct["dis struct"]
        DispatchEvent["DispatchEvent()"]
        MaintainLoop["maintainPipelines()"]
        SafeDisp["safeDispatch()"]
        AppendPipe["appendToPipeline()"]
    end
    
    subgraph "Registry (engine/registry)"
        RegInterface["Registry interface"]
        GetPipeline["GetPipeline(AssetType)"]
        AssetPipeline["AssetPipeline struct:<br/>• Pipeline<br/>• Queue"]
        HandlerTask["handlerTask()"]
    end
    
    subgraph "Session Manager (engine/sessions)"
        MgrInterface["SessionManager interface"]
        GetSessions["GetSessions()"]
        SessionObj["Session struct"]
        SessionQueue["SessionQueue interface"]
    end
    
    subgraph "Session Queue (engine/sessions/queuedb)"
        QueueDB["QueueDB (SQLite)"]
        Has["Has(entity)"]
        Append["Append(entity)"]
        Next["Next(atype, num)"]
        Processed["Processed(entity)"]
    end
    
    DisStruct -->|"stores"| RegInterface
    DisStruct -->|"stores"| MgrInterface
    
    DispatchEvent --> SafeDisp
    SafeDisp --> GetPipeline
    SafeDisp --> Has
    SafeDisp --> Append
    SafeDisp --> AppendPipe
    
    MaintainLoop --> GetSessions
    MaintainLoop --> Next
    
    AppendPipe --> GetPipeline
    AppendPipe --> Processed
    
    GetPipeline --> AssetPipeline
    AssetPipeline --> HandlerTask
    HandlerTask -.->|"cchan"| MaintainLoop
    
    GetSessions --> SessionObj
    SessionObj --> SessionQueue
    SessionQueue --> QueueDB
```

**Session Queue interaction** — key operations:

| Operation | Purpose |
|-----------|---------|
| `Has()` | Deduplication check before queueing |
| `Append()` | Add new entity to session's work queue |
| `Next()` | Retrieve entities for pipeline processing |
| `Processed()` | Mark entity as being actively processed |

## Error Handling

| Layer | Mechanism |
|-------|-----------|
| **API Validation** | Return errors from `DispatchEvent()` |
| **Internal Logging** | Log errors without stopping the loop |
| **Pipeline Errors** | Accumulate in `EventDataElement.Error` via `multierror` |
| **Session Logging** | Log via session's structured logger |

Non-blocking error handling ensures one problematic event doesn't halt the entire enumeration.

## Related

- [Engine Core](engine-core.md) — Dispatcher, SessionManager, and Registry overview
- [Plugin Registry & Pipelines](plugin-registry.md) — How handlers are registered and pipelines constructed
- [DNS Wildcard Detection](dns-wildcard.md) — Wildcard filtering during DNS resolution
- [DNS TTL & Caching](dns-caching.md) — Retry, timeout, and resolver pool configuration
