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

## Best Practices

!!! tip "Session Management"
    - Use separate sessions for different targets
    - Set appropriate timeouts to prevent runaway sessions
    - Monitor queue size to track progress
    - Clean up completed sessions to free resources

!!! warning "Resource Usage"
    Each session consumes memory and disk space. For large enumerations, ensure adequate system resources.
