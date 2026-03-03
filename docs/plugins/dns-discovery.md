# DNS Discovery Plugins

## Purpose and Scope

The DNS Discovery Plugin suite is responsible for performing comprehensive DNS-based reconnaissance to discover FQDNs, IP addresses, and their relationships. This includes querying various DNS record types (TXT, CNAME, A/AAAA, NS, MX, SRV, PTR), managing the domain hierarchy, and triggering cascading discovery through event dispatch.

## Overview

The DNS plugin consists of six specialized handlers that process different DNS record types in a priority-ordered pipeline. Each handler follows a consistent pattern: check incoming events, query or lookup DNS records, store results in the graph database, and dispatch new events for discovered assets.

```mermaid
graph TB
    subgraph "DNS Plugin Registration"
        dnsPlugin["dnsPlugin<br/>(plugin.go)"]
        Registry["et.Registry"]
    end
    
    subgraph "Handler Pipeline - Priority Ordered"
        H1["dnsTXT<br/>Priority: 1<br/>(txt.go)"]
        H2["dnsCNAME<br/>Priority: 2<br/>(cname.go)"]
        H3["dnsIP<br/>Priority: 3<br/>(ip.go)"]
        H4["dnsSubs<br/>Priority: 4<br/>(subs.go)"]
        H5["dnsApex<br/>Priority: 5<br/>(apex.go)"]
        H8["dnsReverse<br/>Priority: 8<br/>(reverse.go)"]
    end
    
    subgraph "Event Flow"
        FQDNEvent["et.Event<br/>EventType: oam.FQDN"]
        IPEvent["et.Event<br/>EventType: oam.IPAddress"]
    end
    
    subgraph "Data Storage"
        Cache["e.Session.Cache()"]
        Assets["Assets:<br/>oamdns.FQDN<br/>oamnet.IPAddress"]
        Edges["Edges:<br/>dns_record<br/>ptr_record<br/>node"]
    end
    
    dnsPlugin -->|"RegisterHandler()"| Registry
    Registry -->|"Routes events"| H1
    Registry -->|"Routes events"| H2
    Registry -->|"Routes events"| H3
    Registry -->|"Routes events"| H4
    Registry -->|"Routes events"| H5
    Registry -->|"Routes events"| H8
    
    FQDNEvent --> H1
    FQDNEvent --> H2
    FQDNEvent --> H3
    FQDNEvent --> H4
    FQDNEvent --> H5
    IPEvent --> H8
    
    H1 --> Cache
    H2 --> Cache
    H3 --> Cache
    H4 --> Cache
    H5 --> Cache
    H8 --> Cache
    
    Cache --> Assets
    Cache --> Edges
```

## Plugin Architecture

### Main Plugin Structure

The `dnsPlugin` struct serves as the parent plugin that manages all DNS handlers.

| Field | Type | Purpose |
|-------|------|---------|
| `name` | `string` | Plugin name: `"DNS"` |
| `txt`, `cname`, `ip`, `subs`, `apex`, `reverse` | Handler structs | Individual DNS record handlers |
| `firstSweepSize`, `secondSweepSize`, `maxSweepSize` | `int` | IP address sweep sizes (25, 100, 250) |
| `source` | `*et.Source` | Source attribution with 100% confidence |
| `apexLock` | `sync.Mutex` | Protects apex list access |
| `apexList` | `map[string]*dbt.Entity` | Tracks discovered apex domains |

### Handler Registration

During plugin startup, each handler registers with the engine registry specifying its priority, event type, and transforms:

```mermaid
graph LR
    subgraph "Start() Method Flow"
        Start["dnsPlugin.Start(r et.Registry)"]
        CreateHandlers["Create handler instances:<br/>dnsTXT, dnsCNAME, dnsIP<br/>dnsSubs, dnsApex, dnsReverse"]
        Register["r.RegisterHandler(&et.Handler{...})"]
    end
    
    subgraph "Handler Configuration"
        Config["Handler Fields:<br/>• Plugin: &dnsPlugin<br/>• Name: unique identifier<br/>• Priority: 1-9<br/>• MaxInstances: support.MaxHandlerInstances<br/>• Transforms: asset types<br/>• EventType: oam.FQDN or oam.IPAddress<br/>• Callback: handler.check()"]
    end
    
    Start --> CreateHandlers
    CreateHandlers --> Register
    Register --> Config
```

---

## DNS Handlers

### dnsTXT Handler (Priority 1)

The TXT record handler queries DNS TXT records, which may contain organization identifiers, verification records, and other metadata.

**Handler Flow:**

```mermaid
graph TD
    Check["dnsTXT.check(e *et.Event)"]
    ValidateFQDN["Extract oamdns.FQDN from e.Entity"]
    TTLCheck["support.TTLStartTime()"]
    MonitorCheck{"support.AssetMonitoredWithinTTL()?"}
    Lookup["lookup()<br/>Retrieve from cache"]
    Query["query()<br/>support.PerformQuery(dns.TypeTXT)"]
    Store["store()<br/>CreateEntityProperty(DNSRecordProperty)"]
    Process["process()<br/>Log TXT records"]
    AddRecordType["support.AddDNSRecordType(dns.TypeTXT)"]
    
    Check --> ValidateFQDN
    ValidateFQDN --> TTLCheck
    TTLCheck --> MonitorCheck
    MonitorCheck -->|"Yes"| Lookup
    MonitorCheck -->|"No"| Query
    Query --> Store
    Store --> Process
    Lookup --> Process
    Process --> AddRecordType
```

**Key Functions:**

- `check()` — Entry point that validates FQDN and determines lookup vs. query path
- `lookup()` — Retrieves cached TXT records using `GetEntityTags()` with `dns_record` tag
- `query()` — Performs DNS TXT query via `support.PerformQuery()` and marks asset monitored
- `store()` — Creates `DNSRecordProperty` with RRType, Class, TTL, and TXT data
- `process()` — Logs discovered TXT records

---

### dnsCNAME Handler (Priority 2)

The CNAME handler resolves canonical name aliases, creating edges from alias to target FQDNs.

**Data Structure:**

```mermaid
graph LR
    AliasFQDN["Alias FQDN<br/>(www.example.com)"]
    TargetFQDN["Target FQDN<br/>(lb.example.com)"]
    Edge["dbt.Edge<br/>Relation: oamdns.BasicDNSRelation<br/>RRType: dns.TypeCNAME (5)"]
    
    AliasFQDN -->|"FromEntity"| Edge
    Edge -->|"ToEntity"| TargetFQDN
    Edge -->|"Property"| SourceProp["general.SourceProperty<br/>Source: DNS-CNAME<br/>Confidence: 100"]
```

!!! info "Unique Behavior"
    Discovered CNAME targets are dispatched as new events, triggering recursive resolution. CNAME chains are followed until an A/AAAA record is found.

---

### dnsIP Handler (Priority 3)

The IP handler resolves A and AAAA records, creating edges from FQDNs to IP addresses.

- Query types: `dns.TypeA`, `dns.TypeAAAA`
- Skips processing if a CNAME record already exists (`support.HasDNSRecordType(e, int(dns.TypeCNAME))`)
- Triggers IP address sweeps for in-scope assets

**Sweep sizes by condition:**

| Condition | Sweep Size |
|-----------|------------|
| IP in scope (passive) | 100 addresses |
| IP in scope (active) | 250 addresses |
| FQDN in scope, IP not | 25 addresses |

---

### dnsSubs Handler (Priority 4)

The subdomain handler queries NS, MX, and SRV records to discover subdomains and services.

**Record Types:**

| DNS Type | Code | Relation Type | Purpose |
|----------|------|---------------|---------|
| NS | 2 | `oamdns.BasicDNSRelation` | Name server discovery |
| MX | 15 | `oamdns.PrefDNSRelation` | Mail server discovery |
| SRV | 33 | `oamdns.SRVDNSRelation` | Service discovery |

The handler queries 171 predefined SRV record labels concurrently (e.g., `_http._tcp`, `_ldap._tcp`, `_xmpp-server._tcp`).

**Traversal Strategy:**

```mermaid
graph TD
    FQDN["Input FQDN:<br/>mail.dev.example.com"]
    CheckScope{"In scope or<br/>referenced by<br/>NS/MX from<br/>in-scope asset?"}
    GetApex["Extract eTLD+1:<br/>example.com"]
    Traverse["Traverse from FQDN to apex:<br/>mail.dev.example.com<br/>→ dev.example.com<br/>→ example.com"]
    Query["Query NS, MX, SRV<br/>for each level"]
    Store["Store relationships<br/>and apex domains"]
    
    FQDN --> CheckScope
    CheckScope -->|"Yes"| GetApex
    GetApex --> Traverse
    Traverse --> Query
    Query --> Store
```

!!! note "Session Deduplication"
    The handler maintains a per-session string set (`subsSession.strset`) to avoid re-querying the same FQDN within a session. Sessions are released via a background goroutine when `s.session.Done()` returns true.

---

### dnsApex Handler (Priority 5)

The apex handler builds the domain hierarchy by creating `node` relationships from apex domains to their subdomains.

**Processing Logic:**

1. Checks if the FQDN has any DNS record types (via `e.Meta` containing `support.FQDNMeta`)
2. Finds the parent apex domain by searching `apexList` for the longest matching suffix
3. Creates a `general.SimpleRelation` edge with name `"node"` from apex to subdomain

**Apex List Management:**

- `addApex()` — Adds a domain to the apex list (thread-safe)
- `getApex()` — Retrieves an apex entity by name
- `getApexList()` — Returns all apex domain names

---

### dnsReverse Handler (Priority 8)

The reverse DNS handler performs PTR lookups to discover FQDNs associated with IP addresses.

**Processing Flow:**

```mermaid
graph TD
    IPEvent["Event: oamnet.IPAddress"]
    CheckReserved{"Reserved<br/>address?"}
    CreateReverse["dns.ReverseAddr():<br/>1.2.3.4 →<br/>4.3.2.1.in-addr.arpa"]
    CreatePTR["createPTRAlias():<br/>Create FQDN entity<br/>Create ptr_record edge"]
    MonitorCheck{"Monitored<br/>within TTL?"}
    Lookup["lookup()<br/>Cached PTR records"]
    Query["query()<br/>support.PerformQuery(dns.TypePTR)"]
    Store["store()<br/>Create FQDN asset<br/>Create dns_record edge"]
    Process["process()<br/>Dispatch FQDN events"]
    
    IPEvent --> CheckReserved
    CheckReserved -->|"Yes"| Exit["Return"]
    CheckReserved -->|"No"| CreateReverse
    CreateReverse --> CreatePTR
    CreatePTR --> MonitorCheck
    MonitorCheck -->|"Yes"| Lookup
    MonitorCheck -->|"No"| Query
    Query --> Store
    Store --> Process
    Lookup --> Process
```

The handler creates two types of relationships:

1. **ptr_record** — From IP address to reverse DNS FQDN (e.g., `4.3.2.1.in-addr.arpa`)
2. **dns_record** — From reverse DNS FQDN to target FQDN (e.g., `server.example.com`)

---

## Handler Processing Pattern

All DNS handlers follow a consistent four-phase pattern:

```mermaid
graph LR
    subgraph "Phase 1: Check"
        Check["check(e *et.Event)<br/>• Validate asset type<br/>• Calculate TTL start time<br/>• Determine lookup vs query"]
    end
    
    subgraph "Phase 2: Retrieve"
        Lookup["lookup()<br/>• Query cache with TTL filter<br/>• Retrieve existing entities/edges"]
        Query["query()<br/>• Perform DNS query<br/>• Mark asset monitored"]
    end
    
    subgraph "Phase 3: Store"
        Store["store()<br/>• Create assets (FQDN, IPAddress)<br/>• Create edges with DNS relations<br/>• Add SourceProperty"]
    end
    
    subgraph "Phase 4: Process"
        Process["process()<br/>• Dispatch new events<br/>• Log discoveries<br/>• Update metadata"]
    end
    
    Check --> Lookup
    Check --> Query
    Lookup --> Process
    Query --> Store
    Store --> Process
```

---

## Data Storage Patterns

### Edge Types

| Relation Type | Fields | Used By |
|---------------|--------|---------|
| `oamdns.BasicDNSRelation` | `Name`, `Header` (RRType, Class, TTL) | CNAME, A/AAAA, NS, PTR |
| `oamdns.PrefDNSRelation` | `Name`, `Header`, `Preference` | MX |
| `oamdns.SRVDNSRelation` | `Name`, `Header`, `Priority`, `Weight`, `Port` | SRV |
| `general.SimpleRelation` | `Name` | Apex hierarchy, PTR alias |

Every edge receives a `general.SourceProperty` tag for source tracking.

---

## Event Dispatching and Cascading Discovery

DNS handlers dispatch events for newly discovered assets, enabling cascading discovery:

```mermaid
graph LR
    FQDN1["FQDN Event:<br/>example.com"]
    TXT["dnsTXT:<br/>TXT records"]
    CNAME["dnsCNAME:<br/>CNAME → lb.example.com"]
    IP["dnsIP:<br/>A → 1.2.3.4"]
    FQDN2["FQDN Event:<br/>lb.example.com"]
    IPEvent["IP Event:<br/>1.2.3.4"]
    Reverse["dnsReverse:<br/>PTR → server.example.com"]
    FQDN3["FQDN Event:<br/>server.example.com"]
    
    FQDN1 --> TXT
    FQDN1 --> CNAME
    FQDN1 --> IP
    CNAME -->|"Dispatch"| FQDN2
    IP -->|"Dispatch"| IPEvent
    IPEvent --> Reverse
    Reverse -->|"Dispatch"| FQDN3
    FQDN3 --> CNAME
    FQDN3 --> IP
```

This recursive event model enables comprehensive reconnaissance from a single seed domain.

---

## Integration with Support Package

All DNS handlers rely on the shared support package for common functionality:

| Function | Purpose |
|----------|---------|
| `support.PerformQuery()` | Execute DNS queries with retry logic |
| `support.TTLStartTime()` | Calculate TTL-based cache window |
| `support.AssetMonitoredWithinTTL()` | Check if asset was recently queried |
| `support.MarkAssetMonitored()` | Mark asset as monitored |
| `support.AddDNSRecordType()` | Add DNS record type to event metadata |
| `support.HasDNSRecordType()` | Check if event has specific record type |
| `support.IPAddressSweep()` | Perform IP address range sweep |
| `support.ScrapeSubdomainNames()` | Extract FQDNs from text |

For detailed documentation on these utilities, see [Enrichment Plugins & Support Utilities](enrichment.md).
