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
