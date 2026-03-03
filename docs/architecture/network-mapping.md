# Network Infrastructure Mapping

Amass performs comprehensive network mapping through coordinated plugin operations, correlating IP addresses, network blocks, and autonomous system numbers (ASNs) to build complete infrastructure maps.

## Network Discovery Architecture

```mermaid
flowchart TB
    subgraph Discovery["Asset Discovery"]
        FQDN[FQDN<br/>example.com]
        DNS[DNS Resolution]
    end

    subgraph Network["Network Mapping"]
        IP[IP Address<br/>192.0.2.1]
        NET[Netblock<br/>192.0.2.0/24]
        ASN[ASN<br/>AS64496]
    end

    subgraph Attribution["Organization Attribution"]
        ORG[Organization<br/>Example Inc]
        WHOIS[WHOIS Data]
    end

    FQDN --> DNS --> IP
    IP --> NET --> ASN --> ORG
    IP --> WHOIS --> ORG
```

## IP-to-Network Correlation

### Discovery Pipeline

1. **DNS Resolution** - Resolve FQDNs to IP addresses
2. **Netblock Lookup** - Query WHOIS/RDAP for network allocation
3. **ASN Attribution** - Identify autonomous system ownership
4. **Organization Mapping** - Link infrastructure to entities

```mermaid
sequenceDiagram
    participant DNS
    participant IPPlugin
    participant WHOIS
    participant BGP
    participant Database

    DNS->>IPPlugin: IP Address Discovered
    IPPlugin->>WHOIS: Query IP Registration
    WHOIS-->>IPPlugin: Netblock + ASN
    IPPlugin->>BGP: Query ASN Details
    BGP-->>IPPlugin: Organization Info
    IPPlugin->>Database: Store Relationships
```

## BGP Tools Integration

The `BGP.Tools` plugin provides autonomous system intelligence:

### Plugin Components

| File | Function |
|------|----------|
| `plugin.go` | Main BGP.Tools integration |
| `autsys.go` | ASN lookup and enrichment |
| `netblock.go` | Network block discovery |

### Data Retrieved

| Data Type | Description |
|-----------|-------------|
| **ASN Information** | AS number, name, description |
| **Network Blocks** | CIDR ranges allocated to ASN |
| **Organization** | Entity owning the ASN |
| **Peers** | BGP peering relationships |

## WHOIS Integration

### Query Types

| Query | Purpose |
|-------|---------|
| **IP WHOIS** | Network block allocation |
| **Domain WHOIS** | Domain registration data |
| **ASN WHOIS** | Autonomous system details |
| **Reverse WHOIS** | Find related domains |

### RDAP Support

Modern RDAP (Registration Data Access Protocol) queries provide structured JSON responses:

```mermaid
flowchart LR
    QUERY[RDAP Query] --> SERVER[RDAP Server]
    SERVER --> RESPONSE[JSON Response]
    RESPONSE --> PARSE[Parse Data]
    PARSE --> ASSETS[Create Assets]
```

## Network Relationship Model

```mermaid
flowchart TB
    subgraph Assets["Discovered Assets"]
        FQDN1[www.example.com]
        FQDN2[api.example.com]
        IP1[192.0.2.1]
        IP2[192.0.2.2]
        NET[192.0.2.0/24]
        ASN[AS64496]
        ORG[Example Inc]
    end

    FQDN1 -->|resolves_to| IP1
    FQDN2 -->|resolves_to| IP2
    IP1 -->|belongs_to| NET
    IP2 -->|belongs_to| NET
    NET -->|member_of| ASN
    ASN -->|owned_by| ORG
```

### Relationship Types

| Source | Relation | Target |
|--------|----------|--------|
| IP Address | `belongs_to` | Netblock |
| Netblock | `member_of` | ASN |
| ASN | `owned_by` | Organization |
| FQDN | `resolves_to` | IP Address |

## Recursive Discovery

Network discoveries trigger further enumeration:

```
IP 192.0.2.1 discovered
    │
    ├─► WHOIS Query → Netblock 192.0.2.0/24
    │   │
    │   ├─► Reverse DNS on range → New FQDNs
    │   │   └─► mail.example.com
    │   │   └─► ftp.example.com
    │   │
    │   └─► ASN Lookup → AS64496
    │       │
    │       └─► Organization → Example Inc
    │           │
    │           └─► GLEIF/Aviato → Related entities
    │
    └─► BGP Tools → Peer ASNs
        └─► AS64497 (CDN Provider)
```

## Infrastructure Correlation

### Multi-Source Correlation

```mermaid
flowchart TB
    subgraph Sources["Data Sources"]
        DNS[DNS Records]
        WHOIS[WHOIS/RDAP]
        BGP[BGP Tools]
        CT[Certificate Transparency]
    end

    subgraph Correlation["Correlation Engine"]
        MERGE[Merge Data]
        DEDUP[Deduplicate]
        RELATE[Build Relations]
    end

    subgraph Output["Infrastructure Map"]
        GRAPH[(Graph Database)]
    end

    DNS & WHOIS & BGP & CT --> MERGE
    MERGE --> DEDUP --> RELATE --> GRAPH
```

### Correlation Points

| Data Point | Sources |
|------------|---------|
| **IP Address** | DNS A/AAAA, Certificate SAN, WHOIS |
| **Organization** | WHOIS registrant, Certificate issuer, GLEIF |
| **Network Block** | WHOIS, BGP announcements |
| **ASN** | WHOIS, BGP Tools, DNS TXT |

## Rate Limiting

Network queries respect rate limits:

| Service | Default Limit |
|---------|---------------|
| WHOIS Servers | 1 QPS |
| RDAP Servers | 5 QPS |
| BGP.Tools | 10 QPS |

## Output Examples

### Network Summary

```
Target: example.com

Network Infrastructure:
├── Netblock: 192.0.2.0/24
│   ├── ASN: AS64496 (Example Inc)
│   ├── IPs: 192.0.2.1, 192.0.2.2, 192.0.2.10
│   └── Hosts: www, api, mail
│
└── Netblock: 198.51.100.0/24
    ├── ASN: AS64497 (CDN Provider)
    ├── IPs: 198.51.100.50
    └── Hosts: cdn
```

## Best Practices

!!! tip "Network Mapping"
    - Use passive mode for initial reconnaissance
    - Correlate data from multiple sources
    - Respect WHOIS rate limits
    - Track ASN relationships for infrastructure pivoting

!!! warning "Legal Considerations"
    WHOIS queries and network reconnaissance may be subject to terms of service and legal restrictions. Ensure proper authorization before scanning.

## Technical Deep Dive

### Event-Driven Processing Model

Every network asset discovery generates an **Event** — the fundamental unit of work that flows through the Amass engine.

```mermaid
graph LR
    subgraph "Event Structure"
        Event["et.Event"]
        Event --> Name["Name: string<br/>'FQDN - example.com'"]
        Event --> Entity["Entity: *dbt.Entity<br/>(wraps OAM Asset)"]
        Event --> Meta["Meta: interface{}<br/>(optional metadata)"]
        Event --> Dispatcher["Dispatcher: et.Dispatcher"]
        Event --> Session["Session: et.Session"]
    end

    subgraph "Event Processing Wrapper"
        EDE["et.EventDataElement"]
        EDE --> EventRef["Event: *et.Event"]
        EDE --> Error["Error: error"]
        EDE --> Queue["Queue: chan *EventDataElement"]
    end

    Event -.wrapped in.-> EDE
```

### Complete Event Flow

This diagram shows how a discovered network asset travels from creation through pipeline processing to completion:

```mermaid
graph TB
    subgraph "1. Event Creation"
        Input["User Input / Plugin Discovery"]
        Input --> CreateEvent["Create et.Event"]
        CreateEvent --> Event["Event{<br/>Name, Entity,<br/>Session, Dispatcher}"]
    end

    subgraph "2. Dispatch & Queue"
        Event --> Dispatch["dispatcher.DispatchEvent()"]
        Dispatch --> Validate{"Validate<br/>Event"}
        Validate --> |Valid| CheckDup{"Already<br/>in Queue?"}
        CheckDup --> |No| QAppend["session.Queue().Append()"]
        QAppend --> QDB[("queue.db<br/>SQLite")]
        QDB --> WaitFill["Wait for<br/>fillPipelineQueues()"]
    end

    subgraph "3. Pipeline Processing"
        WaitFill --> GetNext["session.Queue().Next()"]
        GetNext --> Wrap["Wrap in<br/>EventDataElement"]
        Wrap --> APQueue["AssetPipeline.Queue"]
        APQueue --> Pipeline["Pipeline Execution"]

        Pipeline --> P1["Priority 1<br/>Handlers"]
        P1 --> P2["Priority 2<br/>Handlers"]
        P2 --> Pn["Priority N<br/>Handlers"]
    end

    subgraph "4. Handler Processing"
        Pn --> Handler["Handler.Callback()"]
        Handler --> CheckTrans["Check<br/>Transformations"]
        CheckTrans --> |Allowed| Execute["Execute Logic"]
        Execute --> NewEvents["Generate<br/>New Events?"]
        NewEvents --> |Yes| Dispatch
    end

    subgraph "5. Completion"
        Pn --> Sink["Pipeline Sink"]
        Sink --> Complete["Completion Callback"]
        Complete --> UpdateStats["Increment<br/>WorkItemsCompleted"]
        Complete --> Mark["Mark Processed<br/>in Queue"]
    end

    CheckDup --> |Yes| Skip["Skip: Duplicate"]
    Validate --> |Invalid| Reject["Reject"]
```

Key properties of this model:

1. Events can generate new events recursively (discovery cascade)
2. The session queue prevents duplicate processing
3. Pipelines execute handlers in strict priority order
4. Transformations filter which handlers execute for a given asset
5. Completion callbacks track overall progress statistics

### Handler Priority System

Handlers registered by plugins execute in **priority order** from 1 (highest) to 9 (lowest). For network infrastructure mapping, this ordering ensures DNS resolution completes before IP enrichment, and IP enrichment completes before service probing:

```mermaid
graph LR
    subgraph "Priority Levels"
        P1["Priority 1<br/>DNS TXT Records<br/>(Org Discovery)"]
        P2["Priority 2<br/>DNS CNAME<br/>(Alias Resolution)"]
        P3["Priority 3<br/>DNS A/AAAA<br/>(IP Discovery)"]
        P4["Priority 4<br/>DNS NS/MX/SRV<br/>(Subdomain Enum)"]
        P5["Priority 5<br/>DNS Apex<br/>(Domain Hierarchy)"]
        P6["Priority 6<br/>Company Search<br/>(API Queries)"]
        P7["Priority 7<br/>Company Enrich<br/>(Funding/Employees)"]
        P8["Priority 8<br/>DNS Reverse<br/>(PTR Lookups)"]
        P9["Priority 9<br/>Service Discovery<br/>(HTTP/TLS Probes)"]
    end

    P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9
```

DNS TXT records at priority 1 may reveal organization identifiers, enabling CNAME resolution (priority 2) which yields IP addresses (priority 3), ultimately enabling service discovery (priority 9).

### Asset Pipeline Structure

For each OAM asset type, the registry constructs a pipeline of all registered handlers for that type, ordered by priority:

```mermaid
graph TB
    subgraph "Asset Pipeline for oam.FQDN"
        Input["PipelineQueue<br/>et.PipelineQueue"]

        Input --> Stage1["Priority 1 Stage<br/>DNS TXT Handler"]
        Stage1 --> Stage2["Priority 2 Stage<br/>DNS CNAME Handler"]
        Stage2 --> Stage3["Priority 3 Stage<br/>DNS A/AAAA Handler"]
        Stage3 --> Stage4["Priority 4 Stage<br/>DNS NS/MX/SRV Handler"]
        Stage4 --> Stage5["Priority 5 Stage<br/>DNS Apex Handler"]

        Stage5 --> Sink["Sink<br/>Completion Callback"]
    end

    subgraph "Stage Types"
        FIFO["FIFO<br/>(MaxInstances = 0)"]
        FixedPool["FixedPool<br/>(MaxInstances > 0)"]
        Parallel["Parallel<br/>(Multiple handlers<br/>same priority)"]
    end
```

| Stage Type | When Used | Behavior |
|------------|-----------|----------|
| `FIFO` | Single handler, `MaxInstances = 0` | Serial processing, unlimited goroutines |
| `FixedPool` | Single handler, `MaxInstances > 0` | Concurrent processing, limited pool |
| `Parallel` | Multiple handlers, same priority | All handlers run concurrently |

### Transformation Matching

Transformation rules in `config.yaml` control which plugins are permitted to process which asset types. This is evaluated for every handler execution:

```mermaid
flowchart TD
    Start["Handler Execution"]
    Start --> HasTrans{"Transformations<br/>defined for<br/>asset type?"}

    HasTrans --> |No| Execute["Execute Handler"]

    HasTrans --> |Yes| AllExclude{"Is plugin in<br/>'all' exclude list?"}
    AllExclude --> |Yes| Skip["Skip Handler"]

    AllExclude --> |No| PluginMatch{"Is plugin<br/>explicitly<br/>listed in 'to'?"}
    PluginMatch --> |Yes| Execute

    PluginMatch --> |No| TransMatch{"Does plugin produce<br/>transformation<br/>in config?"}
    TransMatch --> |Yes| Execute
    TransMatch --> |No| Skip
```

Example transformation configuration:

```yaml
transformations:
  - from: FQDN
    to: all
    exclude:
      - dnsSubs
  - from: IPAddress
    to: dnsReverse
```

### OAM Asset Type Hierarchy

Network assets discovered during mapping are represented using the Open Asset Model (OAM). The full hierarchy of asset types recognized by the engine:

```mermaid
graph TB
    subgraph "Network Assets"
        FQDN["oam.FQDN<br/>oamdns.FQDN{Name}"]
        IP["oam.IPAddress<br/>oamnet.IPAddress{Address, Type}"]
        Netblock["oam.Netblock<br/>oamnet.Netblock{CIDR, Type}"]
        ASN["oam.AutonomousSystem<br/>oamnet.AutonomousSystem{Number}"]
    end

    subgraph "Organizational Assets"
        Org["oam.Organization<br/>org.Organization{Name}"]
        Contact["oam.ContactRecord<br/>contact.ContactRecord"]
        Person["oam.Person<br/>people.Person{Name}"]
        Location["oam.Location<br/>contact.Location{Address}"]
    end

    subgraph "Service Assets"
        Service["oam.Service<br/>platform.Service{Port, Protocol}"]
        TLS["oam.TLSCertificate<br/>oamcert.TLSCertificate"]
        URL["oam.URL<br/>url.URL{Raw}"]
    end

    subgraph "Registration Assets"
        Domain["oam.DomainRecord<br/>oamreg.DomainRecord"]
        IPNet["oam.IPNetRecord<br/>oamreg.IPNetRecord"]
        Autnum["oam.AutnumRecord<br/>oamreg.AutnumRecord"]
    end
```

### Session Queue Schema

Each enumeration session tracks work items in a dedicated SQLite-backed queue, preventing duplicate processing of discovered assets:

```mermaid
erDiagram
    Element {
        uint64 ID PK
        time CreatedAt
        time UpdatedAt
        string Type "oam.AssetType"
        string EntityID "dbt.Entity.ID"
        bool Processed
    }
```

| Method | Purpose |
|--------|---------|
| `Has(e)` | Check if entity is already queued |
| `Append(e)` | Add entity to queue |
| `Next(atype, num)` | Get next batch of unprocessed entities |
| `Processed(e)` | Mark entity as processed |
