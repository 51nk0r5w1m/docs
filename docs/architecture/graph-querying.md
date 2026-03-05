# Graph Database and Querying

## Storage Architecture Overview

```mermaid
graph TB
    subgraph "Session-Specific Storage (Temporary)"
        Cache["Cache Repository<br/>(SQLite)<br/>cache.db"]
        Queue["Queue Database<br/>(SQLite + GORM)<br/>queue.db"]
    end

    subgraph "Persistent Storage (Configurable)"
        PersistentDB["Persistent Repository<br/>SQLite: assetdb.db<br/>Postgres: Network DB<br/>Neo4j: Network DB"]
    end

    subgraph "Engine Components"
        Plugin["Plugins"]
        Dispatcher["Dispatcher"]
    end

    Plugin -->|"CreateAsset()"| Cache
    Cache -->|"Flush every 1 min"| PersistentDB

    Dispatcher -->|"Append(entity)"| Queue
    Queue -->|"Next(type, num)"| Dispatcher
    Dispatcher -->|"Processed(entity)"| Queue

    Cache -.->|"Shares entity IDs"| Queue

    style Cache fill:#f9f9f9
    style Queue fill:#f9f9f9
    style PersistentDB fill:#e8e8e8
```

## Database Connection Flow

```mermaid
graph TD
    Session["Session Creation<br/>CreateSession(cfg)"]

    Session --> SelectDBMS["selectDBMS()<br/>Parse cfg.GraphDBs"]

    SelectDBMS --> CheckType{"Database Type?"}

    CheckType -->|"postgres"| Postgres["DSN:<br/>host=X port=Y user=Z<br/>password=W dbname=N<br/>Type: sqlrepo.Postgres"]
    CheckType -->|"sqlite/sqlite3"| SQLite["DSN:<br/>&lt;dir&gt;/assetdb.db<br/>?_pragma=busy_timeout(30000)<br/>&amp;_pragma=journal_mode(WAL)<br/>Type: sqlrepo.SQLite"]
    CheckType -->|"neo4j/bolt"| Neo4j["DSN: db.URL<br/>Type: neo4j.Neo4j"]

    Postgres --> InitDB["assetdb.New(dbtype, dsn)"]
    SQLite --> InitDB
    Neo4j --> InitDB

    InitDB --> AssignDB["s.db = store"]

    AssignDB --> CreateTmp["createTemporaryDir()<br/>&lt;outdir&gt;/session-&lt;uuid&gt;"]

    CreateTmp --> CreateCache["createFileCacheRepo()<br/>&lt;tmpdir&gt;/cache.db"]

    CreateCache --> NewCache["cache.New(c, s.db, 1min)"]

    NewCache --> CreateQueue["newSessionQueue(s)<br/>&lt;tmpdir&gt;/queue.db"]

    style InitDB fill:#f9f9f9
    style NewCache fill:#f9f9f9
    style CreateQueue fill:#f9f9f9
```

## Queue and Dispatcher Workflow

```mermaid
sequenceDiagram
    participant Plugin
    participant Dispatcher
    participant SessionQueue
    participant QueueDB
    participant Cache

    Plugin->>Dispatcher: DispatchEvent(event)
    Dispatcher->>SessionQueue: Has(entity)
    SessionQueue->>QueueDB: Has(entity.ID)
    QueueDB-->>Dispatcher: false

    Dispatcher->>SessionQueue: Append(entity)
    SessionQueue->>QueueDB: Append(type, ID)

    Note over Dispatcher: Every 1 second
    Dispatcher->>SessionQueue: Next(type, 500)
    SessionQueue->>QueueDB: Next(type, 500)
    QueueDB-->>SessionQueue: [entity_ids]
    SessionQueue->>Cache: FindEntityById(id)
    Cache-->>SessionQueue: entity
    SessionQueue-->>Dispatcher: [entities]

    Dispatcher->>Pipeline: Process(entity)
    Pipeline-->>Dispatcher: Completed

    Dispatcher->>SessionQueue: Processed(entity)
    SessionQueue->>QueueDB: Processed(entity.ID)
```

## Triple-Based Graph Traversal

Amass uses **triple-based queries** to traverse the graph database. A triple is a pattern `(subject, predicate, object)` describing a relationship traversal:

```
fqdn -> dns_record -> ipaddr
ipaddr -> netblock_contains -> netblock
netblock -> asn_announcement -> as
```

The `oam_assoc` command-line tool performs graph traversal using these triples:

```bash
oam_assoc -t1 "fqdn -> dns_record -> ipaddr" -t2 "ipaddr -> netblock_contains -> netblock"
# or load from file
oam_assoc -tf triples_file.txt
```

```mermaid
graph TD
    CLI["oam_assoc CLI<br/>CLIWorkflow()"]

    CLI --> ParseArgs["Parse Arguments<br/>-t1...-t10 or -tf"]

    ParseArgs --> LoadFile{"Triple File<br/>Provided?"}

    LoadFile -->|"Yes"| ReadFile["GetListFromFile()<br/>Parse up to 10 triples"]
    LoadFile -->|"No"| ValidateTriples["Validate CLI triples"]

    ReadFile --> ValidateTriples

    ValidateTriples --> OpenDB["OpenGraphDatabase(cfg)<br/>Connect to asset-db"]

    OpenDB --> ParseTriples["Loop: triples.ParseTriple(tstr)<br/>Build []*triples.Triple"]

    ParseTriples --> Extract["triples.Extract(db, tris)<br/>Execute graph traversal"]

    Extract --> Results["Results map"]

    Results --> JSON["json.MarshalIndent(results)<br/>Pretty JSON output"]

    JSON --> Output["Print to stdout"]

    style Extract fill:#f9f9f9
    style OpenDB fill:#f9f9f9
```

## oam_subs: Subdomain Query Flow

```mermaid
graph TD
    Start["oam_subs -d domain.com"]

    Start --> GetDomain["FindEntitiesByContent()<br/>FQDN{Name: domain.com}"]

    GetDomain --> FindSubdomains["FindByFQDNScope(db, entity)<br/>Recursive subdomain discovery"]

    FindSubdomains --> BuildList["Build list of FQDN names"]

    BuildList --> GetAddrs["NamesToAddrs(db, time, names)<br/>Resolve FQDNs to IP addresses"]

    GetAddrs --> ASNLookup["ASNCache.AddrSearch(ip)<br/>Get ASN/netblock info"]

    ASNLookup --> Format["Format output with<br/>names, IPs, ASNs"]

    Format --> Print["Print summary table"]

    style FindSubdomains fill:#f9f9f9
    style GetAddrs fill:#f9f9f9
    style ASNLookup fill:#f9f9f9
```

## oam_track: Time-Based Filtering

```mermaid
graph TD
    Start["oam_track -d domain.com<br/>-since '01/02 15:04:05 2006 MST'"]

    Start --> ParseTime["time.Parse(TimeFormat, args.Since)"]

    ParseTime --> FindDomains["FindEntitiesByContent()<br/>with since filter"]

    FindDomains --> GetScope["FindByFQDNScope(db, entity, since)"]

    GetScope --> FilterAssets{"Filter assets where<br/>CreatedAt >= since<br/>AND LastSeen >= since"}

    FilterAssets --> NewAssets["Collect new asset names"]

    NewAssets --> Output["Print to stdout"]

    style FilterAssets fill:#f9f9f9
```

!!! tip "Auto-timestamp selection"
    If no `since` parameter is provided, `oam_track` automatically uses the most recent asset's `LastSeen` timestamp, truncated to midnight.

## oam_viz: Graph Data Extraction

```mermaid
graph TD
    Start["oam_viz -d domain.com<br/>-d3 / -dot / -gexf"]

    Start --> OpenDB["OpenGraphDatabase(cfg)"]

    OpenDB --> Extract["VizData(domains, start, db)<br/>Extract nodes and edges"]

    Extract --> BuildNodes["Build Node list:<br/>- FQDNs<br/>- IP addresses<br/>- Netblocks<br/>- ASNs"]

    BuildNodes --> BuildEdges["Build Edge list:<br/>- dns_record<br/>- netblock_contains<br/>- asn_announcement"]

    BuildEdges --> Format{"Output Format?"}

    Format -->|"D3"| D3["WriteD3Data()<br/>HTML + JavaScript"]
    Format -->|"DOT"| DOT["WriteDOTData()<br/>Graphviz format"]
    Format -->|"GEXF"| GEXF["WriteGEXFData()<br/>Gephi XML format"]

    D3 --> Save["Save to file"]
    DOT --> Save
    GEXF --> Save

    style Extract fill:#f9f9f9
```

---

# Database Connection Strings

=== "SQLite (Default)"

    ```
    {path}/assetdb.db?_pragma=busy_timeout(30000)&_pragma=journal_mode(WAL)
    ```

    **Pragma options:**
    - `busy_timeout(30000)` — Wait 30 seconds when database is locked
    - `journal_mode(WAL)` — Write-Ahead Logging for better concurrency

=== "PostgreSQL"

    ```
    host={host} port={port} user={user} password={password} dbname={dbname}
    ```

    ```bash
    export AMASS_DB_USER="amass"
    export AMASS_DB_PASSWORD="secret"
    export AMASS_DB_HOST="localhost"
    export AMASS_DB_PORT="5432"
    export AMASS_DB_NAME="assetdb"
    ```

=== "Neo4j"

    ```
    neo4j+s://{host}:{port}
    ```

    **Supported schemes:** `neo4j`, `neo4j+s`, `neo4j+sec`, `bolt`, `bolt+s`, `bolt+sec`

---

# Summary

| Capability | Details |
|------------|---------|
| **Standardized Assets** | OAM specification ensures consistent asset types across all plugins |
| **Three-Tier Storage** | Work queue for scheduling, cache for performance, graph DB for persistence |
| **Session Isolation** | Each enumeration session has dedicated temporary storage |
| **Flexible Backends** | SQLite for standalone use; PostgreSQL/Neo4j for production deployments |
| **Entity Wrapping** | `dbt.Entity` provides metadata layer over OAM assets |
| **Efficient Lifecycle** | Assets flow: discovery → cache → queue → pipeline → persistent storage |
| **Graph Traversal** | Triple-based queries via `oam_assoc`; direct repository API for tools |
