# Data Flow

Understanding how assets flow through Amass helps optimize enumeration strategies and interpret results.

## Asset Discovery Flow

```mermaid
flowchart TB
    subgraph Input["Seed Input"]
        DOMAIN[Domain Names]
        IPS[IP Addresses]
        ASNS[ASN Numbers]
        CIDRS[CIDR Blocks]
    end

    subgraph Engine["Amass Engine"]
        GQL[GraphQL API]
        DISP[Dispatcher]
        QUEUE[(Asset Queue)]
    end

    subgraph Processing["Plugin Processing"]
        DNS[DNS Resolution]
        NET[Network Mapping]
        ORG[Org Intelligence]
        SVC[Service Discovery]
    end

    subgraph Storage["Persistent Storage"]
        CACHE[(Cache Layer)]
        GRAPH[(Graph Database)]
    end

    subgraph Output["Results"]
        ASSETS[Discovered Assets]
        RELS[Relationships]
        VIZ[Visualizations]
    end

    DOMAIN & IPS & ASNS & CIDRS --> GQL
    GQL --> DISP --> QUEUE
    QUEUE --> DNS & NET & ORG & SVC
    DNS & NET & ORG & SVC --> CACHE --> GRAPH
    GRAPH --> ASSETS & RELS & VIZ
```

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

```mermaid
flowchart LR
    subgraph Discovery["Asset Discovery"]
        FQDN[FQDN<br/>example.com]
        IP[IP Address<br/>192.0.2.1]
        NET[Netblock<br/>192.0.2.0/24]
        ASN[ASN<br/>AS64496]
        ORG[Organization<br/>Example Inc]
        CERT[Certificate<br/>*.example.com]
    end

    FQDN -->|resolves_to| IP
    IP -->|belongs_to| NET
    NET -->|member_of| ASN
    ASN -->|owned_by| ORG
    FQDN -->|registered_to| ORG
    FQDN -->|protected_by| CERT
    CERT -->|issued_to| ORG
```

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

```mermaid
flowchart TB
    subgraph Input
        QUERY[DNS Query]
    end

    subgraph Resolvers["Resolver Selection"]
        BASELINE[Baseline Resolvers<br/>Google, Cloudflare, Quad9]
        PUBLIC[Public Pool<br/>Dynamic resolvers]
        CUSTOM[Custom Resolvers<br/>User-specified]
        TRUSTED[Trusted Resolvers<br/>Higher rate limits]
    end

    subgraph Processing
        RATE[Rate Limiter]
        WILD[Wildcard Detection]
        CACHE[(DNS Cache)]
        VALID[Response Validation]
    end

    subgraph Output
        RESULT[DNS Response]
        ASSET[New Asset]
    end

    QUERY --> RATE
    RATE --> BASELINE & PUBLIC & CUSTOM & TRUSTED
    BASELINE & PUBLIC & CUSTOM & TRUSTED --> WILD
    WILD --> CACHE
    CACHE --> VALID
    VALID --> RESULT --> ASSET
```

### Resolver Rate Limiting

| Resolver Type | Default QPS | Purpose |
|---------------|-------------|---------|
| Baseline | 15 | Reliable fallback |
| Public | 5 | Distributed load |
| Custom | Configurable | User preference |
| Trusted | 15+ | High-volume queries |

## Caching Strategy

```mermaid
flowchart LR
    subgraph Request
        NEW[New Query]
    end

    subgraph Cache["Cache Layer"]
        CHECK{Cache Hit?}
        TTL{TTL Valid?}
        STORE[Store Result]
    end

    subgraph Backend
        DNS[DNS Resolver]
        API[External API]
    end

    NEW --> CHECK
    CHECK -->|Yes| TTL
    TTL -->|Yes| CACHED[Return Cached]
    TTL -->|No| DNS & API
    CHECK -->|No| DNS & API
    DNS & API --> STORE --> RESULT[Return Fresh]
```

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

```mermaid
flowchart TB
    subgraph Database
        GRAPH[(Graph Database)]
    end

    subgraph Queries
        SUBS[Subdomains Query]
        ASSOC[Associations Query]
        TRACK[Changes Query]
    end

    subgraph Formats
        TEXT[Text Output]
        JSON[JSON Export]
        DOT[DOT Graph]
        D3[D3 Visualization]
        GEXF[Gephi GEXF]
    end

    GRAPH --> SUBS & ASSOC & TRACK
    SUBS --> TEXT & JSON
    ASSOC --> TEXT & JSON & DOT
    TRACK --> TEXT & JSON
    GRAPH --> D3 & GEXF
```

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

```mermaid
flowchart LR
    subgraph Loop["Discovery Feedback"]
        A[Seed Domain] --> B[DNS Resolution]
        B --> C[Subdomains Found]
        C --> D[Queue New FQDNs]
        D --> E[Process Subdomains]
        E --> F[More Discoveries]
        F --> D
    end
```

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
