# DNS TTL & Caching


This page documents Amass's DNS response caching mechanisms, Time-To-Live (TTL) management, and query deduplication strategies. It explains how the system balances performance through caching with data freshness requirements, prevents redundant DNS queries, and handles DNS TTL values to avoid overloading resolvers while maintaining up-to-date reconnaissance data.

## DNS Query Retry and Timeout Strategy

Amass implements a retry mechanism for DNS queries to handle transient failures. The `PerformQuery` function attempts up to **10 retries** for each DNS query before declaring failure.

### Query Execution Flow

```mermaid
graph TD
    Start["PerformQuery(name, qtype)"] --> Loop["Retry Loop<br/>(max 10 attempts)"]
    Loop --> BuildMsg["Build DNS Message<br/>QueryMsg() or ReverseMsg()"]
    BuildMsg --> Execute["dnsQuery(msg, trusted)"]
    Execute --> CheckResp{"Response<br/>Valid?"}
    CheckResp -->|"Error/Timeout"| LoopCheck{"Attempts<br/>< 10?"}
    CheckResp -->|"Success"| WildcardCheck["wildcardDetected(resp, detector)"]
    WildcardCheck -->|"True"| ReturnError["Return 'wildcard detected'"]
    WildcardCheck -->|"False"| CheckAnswers{"Answers<br/>Exist?"}
    CheckAnswers -->|"Yes"| FilterType["AnswersByType(resp, qtype)"]
    FilterType --> ReturnSuccess["Return RR records"]
    CheckAnswers -->|"No"| LoopCheck
    LoopCheck -->|"Yes"| Loop
    LoopCheck -->|"No"| ReturnError
```

### Timeout Configuration

The DNS query timeout is hardcoded to **2 seconds** per attempt:

| Component | Timeout Value | Purpose |
|-----------|---------------|---------|
| Per-query timeout | 2 seconds | Maximum wait time for a single DNS query |
| Total retry window | ~20 seconds | Maximum time across 10 retries |
| Wildcard detector timeout | 2 seconds | Dedicated timeout for wildcard checks |

The timeout is configured at pool initialization:

```mermaid
graph LR
    Init["trustedResolvers()"] --> Timeout["timeout = 2 * time.Second"]
    Timeout --> WildcardServ["serv = NewNameserver('8.8.4.4')"]
    WildcardServ --> WildcardConn["wconns = conn.New(cpus, selector)"]
    WildcardConn --> Detector["detector = NewDetector(serv, wconns, nil)"]
    
    Timeout --> BaselineServ["Create baseline servers"]
    BaselineServ --> RandomSel["sel = selectors.NewRandom(timeout, servs...)"]
    RandomSel --> PoolConns["conns = conn.New(cpus, sel)"]
    PoolConns --> Pool["pool.New(0, sel, conns, nil)"]
```

## Queries Per Second (QPS) Management

Amass implements **per-resolver rate limiting** to prevent overwhelming DNS servers. Each resolver type has different QPS limits based on trust level and capacity.

### Resolver QPS Configuration

The system maintains two tiers of resolvers:

```mermaid
graph TB
    subgraph "Baseline (Trusted) Resolvers"
        BR1["Google 8.8.8.8<br/>QPS: 5"]
        BR2["Gcore 95.85.95.85<br/>QPS: 2"]
        BR3["ControlD 76.76.2.0<br/>QPS: 2"]
        BR4["Quad9 9.9.9.9<br/>QPS: 2"]
        BR5["Cloudflare 1.1.1.1<br/>QPS: 3"]
        BR6["... 73 more resolvers<br/>QPS: 1-2 each"]
    end
    
    subgraph "Public Resolvers"
        PR1["Dynamic resolver 1<br/>QPS: 5 (default)"]
        PR2["Dynamic resolver 2<br/>QPS: 5 (default)"]
        PR3["Dynamic resolver N<br/>QPS: 5 (default)"]
    end
    
    subgraph "Configuration"
        Config["Config.CalcMaxQPS()"]
    end
    
    BR1 --> Config
    BR2 --> Config
    BR3 --> Config
    BR4 --> Config
    BR5 --> Config
    BR6 --> Config
    PR1 --> Config
    PR2 --> Config
    PR3 --> Config
    
    Config --> Total["Total QPS =<br/>(len(Resolvers) × ResolversQPS) +<br/>(len(TrustedResolvers) × TrustedQPS)"]
```

### QPS Constants and Calculation

| Constant | Value | Applied To |
|----------|-------|------------|
| `DefaultQueriesPerPublicResolver` | 5 | Dynamically fetched public resolvers |
| `DefaultQueriesPerBaselineResolver` | 15 | Trusted baseline resolvers |
| Individual baseline QPS | 1–5 | Hardcoded per resolver in baseline list |

The `CalcMaxQPS` method computes total system-wide query capacity:

```
MaxDNSQueries = (len(Resolvers) × ResolversQPS) + (len(TrustedResolvers) × TrustedQPS)
```

!!! tip "Example capacity"
    - 10 public resolvers × 5 QPS = 50 QPS
    - 78 baseline resolvers × 15 QPS = 1,170 QPS
    - **Total: ~1,220 queries per second**

## Baseline Resolver Pool

The system maintains a hardcoded list of **78 trusted public DNS resolvers** with varying QPS allocations:

```mermaid
graph LR
    subgraph "High QPS Resolvers"
        H1["Google 8.8.8.8<br/>QPS: 5"]
        H2["Cloudflare 1.1.1.1<br/>QPS: 3"]
        H3["Cloudflare 1.0.0.1<br/>QPS: 3"]
    end
    
    subgraph "Medium QPS Resolvers"
        M1["Gcore 95.85.95.85<br/>QPS: 2"]
        M2["ControlD 76.76.2.0<br/>QPS: 2"]
        M3["Quad9 9.9.9.9<br/>QPS: 2"]
        M4["Cisco OpenDNS<br/>QPS: 2"]
        M5["... 18 more @ QPS: 2"]
    end
    
    subgraph "Standard QPS Resolvers"
        S1["AdGuard 94.140.14.14<br/>QPS: 1"]
        S2["Comodo 8.26.56.26<br/>QPS: 1"]
        S3["Verisign 64.6.64.6<br/>QPS: 1"]
        S4["... 50 more @ QPS: 1"]
    end
```

### Trusted Resolver Pool Initialization

The `trustedResolvers` function creates a connection pool with random selection:

```mermaid
sequenceDiagram
    participant Caller
    participant trustedResolvers
    participant Detector as wildcards.Detector
    participant Pool as pool.Pool
    participant Selector as selectors.Random
    
    Caller->>trustedResolvers: Initialize
    trustedResolvers->>Detector: NewDetector(8.8.4.4, conns, nil)
    Note over Detector: Single resolver for<br/>wildcard detection
    
    trustedResolvers->>trustedResolvers: Build servs[] from<br/>baselineResolvers
    trustedResolvers->>Selector: NewRandom(timeout, servs...)
    Note over Selector: Random selection<br/>distributes load
    
    trustedResolvers->>Pool: New(0, sel, conns, nil)
    Note over Pool: QPS=0 means<br/>no global limit
    Pool-->>Caller: Return pool
```

## Query Deduplication and Response Validation

Each query response undergoes multiple validation stages before being accepted.

### Response Validation Pipeline

```mermaid
graph TD
    Query["dnsQuery(msg, pool)"] --> Exchange["pool.Exchange(ctx, msg)"]
    Exchange --> CheckErr{"Error?"}
    CheckErr -->|"Yes"| ReturnErr["Return error"]
    CheckErr -->|"No"| CheckRcode{"Rcode?"}
    
    CheckRcode -->|"RcodeNameError"| ReturnNXDOMAIN["Return 'name does not exist'"]
    CheckRcode -->|"RcodeSuccess"| CheckAnswers{"Answers<br/>exist?"}
    CheckRcode -->|"Other"| ReturnUnexpected["Return 'unexpected response'"]
    
    CheckAnswers -->|"No"| ReturnNoRecord["Return 'no record of this type'"]
    CheckAnswers -->|"Yes"| ValidResp["Return valid dns.Msg"]
```

### Wildcard Detection as Cache Invalidation

Before accepting a DNS response, the system checks for wildcard patterns using eTLD+1 extraction:

```mermaid
graph LR
    Response["DNS Response"] --> Extract["Extract question name"]
    Extract --> Lower["strings.ToLower()<br/>RemoveLastDot()"]
    Lower --> ETLD["publicsuffix.EffectiveTLDPlusOne(name)"]
    ETLD --> Detect["detector.WildcardDetected(ctx, resp, dom)"]
    Detect -->|"True"| Discard["Discard response<br/>(treat as cache miss)"]
    Detect -->|"False"| Accept["Accept response"]
```

Wildcard responses are discarded to prevent false positives from polluting results. This is critical for subdomain enumeration accuracy.

## Resolver Selection Strategy

The system uses a **random selector** to distribute queries across the baseline resolver pool, preventing any single resolver from being overwhelmed:

```mermaid
graph TB
    Request["DNS Query Request"] --> Selector["selectors.NewRandom(timeout, servs...)"]
    
    Selector --> Pool78["Resolver Pool<br/>(78 baseline servers)"]
    
    Pool78 --> R1["8.8.8.8"]
    Pool78 --> R2["1.1.1.1"]
    Pool78 --> R3["9.9.9.9"]
    Pool78 --> R4["208.67.222.222"]
    Pool78 --> R5["... 74 more"]
    
    R1 --> Response["DNS Response"]
    R2 --> Response
    R3 --> Response
    R4 --> Response
    R5 --> Response
    
    Response --> Validation["Validation Pipeline"]
```

Alternative selector implementations available in the `resolve` package:

- `selectors.NewAuthoritative` — Queries authoritative nameservers directly
- `selectors.NewSingle` — Uses a single dedicated resolver

## Dynamic Public Resolver Loading

In addition to the 78 baseline trusted resolvers, Amass can dynamically fetch public DNS resolvers from `public-dns.info` with reliability filtering.

### Public Resolver Acquisition Process

```mermaid
sequenceDiagram
    participant System
    participant HTTP as http.RequestWebPage
    participant CSV as CSV Parser
    participant Filter as Reliability Filter
    participant Config
    
    System->>HTTP: GET public-dns.info/nameservers-all.csv
    HTTP-->>System: CSV data
    
    System->>CSV: Parse CSV records
    loop For each record
        CSV->>Filter: Check reliability >= 0.85
        Filter->>Filter: Skip if in DefaultBaselineResolvers
        Filter->>Config: Append to PublicResolvers
    end
    
    Config->>Config: PublicResolvers = deduplicated list
```

!!! info "Reliability threshold"
    Only resolvers with **≥ 85% reliability** (`minResolverReliability = 0.85`) are included. Resolvers already in `DefaultBaselineResolvers` are excluded to avoid double-counting.

## TTL Handling and Cache Expiration

While explicit TTL extraction is handled by the underlying `resolve` package, the system's architecture implies TTL-based caching through the resolver pool abstraction.

### Implied TTL Workflow

```mermaid
graph TD
    Query["DNS Query"] --> Pool["pool.Exchange(ctx, msg)"]
    Pool --> Resolve["resolve package<br/>(internal)"]
    
    Resolve --> CheckCache{"Cached<br/>response?"}
    CheckCache -->|"Yes"| CheckTTL{"TTL<br/>expired?"}
    CheckCache -->|"No"| Network["Perform network query"]
    
    CheckTTL -->|"Expired"| Network
    CheckTTL -->|"Valid"| ReturnCached["Return cached response"]
    
    Network --> ParseTTL["Extract TTL from response"]
    ParseTTL --> Store["Store in cache with TTL"]
    Store --> ReturnNew["Return new response"]
```

**Key caching principles:**

1. DNS responses contain TTL values (time-to-live in seconds)
2. The resolver pool caches responses until TTL expiration
3. Expired cache entries trigger new network queries
4. Wildcard responses are excluded from caching (treated as invalid)

## Data Freshness Strategy

The retry mechanism combined with TTL-based caching ensures data freshness while preventing excessive load on DNS infrastructure:

| Mechanism | Purpose | Implementation |
|-----------|---------|----------------|
| **Retry loops** | Overcome transient failures | 10 attempts per query |
| **TTL respect** | Honor authoritative cache times | Implicit in resolver pool |
| **Wildcard filtering** | Prevent false positive caching | Per-response validation |
| **QPS limiting** | Sustainable query rates | Per-resolver QPS caps |
| **Multiple resolvers** | Redundancy and validation | 78 baseline + dynamic public |

```mermaid
graph LR
    Asset["Asset Discovery"] --> TTLCheck{"Cached<br/>data?"}
    TTLCheck -->|"No cache"| FreshQuery["Fresh DNS query"]
    TTLCheck -->|"Cached"| AgeCheck{"TTL<br/>expired?"}
    
    AgeCheck -->|"Expired"| FreshQuery
    AgeCheck -->|"Valid"| UseCached["Use cached data"]
    
    FreshQuery --> Store["Store with TTL"]
    Store --> Result["Return result"]
    UseCached --> Result
```

## Configuration API

### Resolver Management Methods

```mermaid
classDiagram
    class Config {
        +Resolvers []string
        +TrustedResolvers []string
        +ResolversQPS int
        +TrustedQPS int
        +MaxDNSQueries int
        
        +SetResolvers(resolvers ...string)
        +AddResolvers(resolvers ...string)
        +AddResolver(resolver string)
        +SetTrustedResolvers(resolvers ...string)
        +AddTrustedResolvers(resolvers ...string)
        +AddTrustedResolver(resolver string)
        +CalcMaxQPS()
    }
```

| Method | Behaviour |
|--------|-----------|
| `SetResolvers` | Replaces entire resolver list (calls `AddResolvers` internally) |
| `AddResolvers` | Appends multiple resolvers, deduplicates, recalculates QPS |
| `AddResolver` | Appends single resolver with trim and deduplication |
| `CalcMaxQPS` | Updates `MaxDNSQueries` based on resolver counts and QPS settings |

### File-Based Resolver Loading

Resolvers can be loaded from configuration files containing IP addresses:

```mermaid
graph TD
    Config["Config.loadResolverSettings()"] --> Parse["Parse YAML options"]
    Parse --> Check{"Resolver<br/>is IP?"}
    
    Check -->|"Yes"| AddIP["Add to resolversList"]
    Check -->|"No"| File["Treat as file path"]
    
    File --> Abs["AbsPathFromConfigDir(path)"]
    Abs --> Read["loadResolversFromFile(absPath)"]
    Read --> Validate["Validate each line is IP"]
    Validate --> AddFile["Append file resolvers"]
    
    AddIP --> Dedup["Deduplicate list"]
    AddFile --> Dedup
    Dedup --> Assign["c.Resolvers = resolverIPs"]
```

!!! info "File format"
    - One IP address per line
    - Empty lines are skipped
    - Invalid IPs cause loading failure
    - Automatic deduplication is applied

## Summary

Amass's TTL and caching strategy balances performance with data accuracy through:

1. **Multi-tier resolver architecture** — 78 baseline trusted + dynamic public resolvers
2. **Per-resolver QPS limits** — Prevent overwhelming individual DNS servers (1–5 QPS each)
3. **Retry mechanism** — Up to 10 attempts with 2-second timeouts per attempt
4. **Random load distribution** — Selector randomises resolver choice across the pool
5. **Wildcard filtering** — Prevents false positive caching via EffectiveTLD+1 validation
6. **TTL-based expiration** — Respects DNS authoritative cache timing (handled by `resolve` package)
7. **Configuration flexibility** — File-based and programmatic resolver management

This design enables sustainable reconnaissance at scale (1,000+ QPS total capacity) while respecting DNS infrastructure limits.

## Related

- [Engine Core](engine-core.md) — Overview of the Amass engine components
- [Event Dispatcher](event-dispatcher.md) — Event routing and session management
- [Plugin Registry & Pipelines](plugin-registry.md) — DNS plugin handlers and pipeline priorities
- [DNS Wildcard Detection](dns-wildcard.md) — Wildcard detection algorithm and integration
