# DNS System

Amass implements a sophisticated DNS resolution system with multiple resolver pools, intelligent rate limiting, wildcard detection, and caching.

## Resolver Architecture

```mermaid
flowchart TB
    subgraph Resolvers["Resolver Pools"]
        BASELINE[Baseline Resolvers<br/>Google, Cloudflare, Quad9]
        PUBLIC[Public Resolvers<br/>from public-dns.info]
        CUSTOM[Custom Resolvers<br/>-r flag]
        TRUSTED[Trusted Resolvers<br/>-tr flag]
    end

    subgraph Processing["Query Processing"]
        RATE[Rate Limiter]
        WILD[Wildcard Detector]
        CACHE[(DNS Cache)]
        VALID[Response Validator]
    end

    subgraph Output
        RESULT[DNS Response]
        ASSET[Asset Creation]
    end

    QUERY[DNS Query] --> RATE
    RATE --> BASELINE & PUBLIC & CUSTOM & TRUSTED
    BASELINE & PUBLIC & CUSTOM & TRUSTED --> WILD
    WILD --> CACHE
    CACHE --> VALID
    VALID --> RESULT --> ASSET
```

## Resolver Types

| Type | Description | Default QPS |
|------|-------------|-------------|
| **Baseline** | Curated reliable resolvers (Google 8.8.8.8, Cloudflare 1.1.1.1, Quad9 9.9.9.9) | 15 |
| **Public** | Dynamic pool from public-dns.info with reliability filtering | 5 |
| **Custom** | User-specified via `-r` flag | Configurable |
| **Trusted** | High-priority resolvers via `-tr` flag | 15+ |

## Rate Limiting

The system enforces strict query rate limits per resolver:

```mermaid
flowchart LR
    subgraph Limits["Rate Limits"]
        PUB[Public: 5 QPS]
        BASE[Baseline: 15 QPS]
        TRUST[Trusted: 15+ QPS]
    end

    QUERY[Query] --> LIMITER{Rate Limiter}
    LIMITER -->|Under limit| RESOLVER[Execute Query]
    LIMITER -->|Over limit| WAIT[Wait/Queue]
    WAIT --> LIMITER
```

### Configuration Flags

| Flag | Description | Default |
|------|-------------|---------|
| `-dns-qps` | Maximum total DNS queries per second | Unlimited |
| `-rqps` | Max QPS per untrusted resolver | 5 |
| `-trqps` | Max QPS per trusted resolver | 15 |

## Wildcard Detection

The wildcard detector prevents false positives from catch-all DNS configurations:

```mermaid
flowchart TB
    QUERY[Query: random.example.com] --> CHECK{Wildcard Check}
    CHECK -->|Random subdomain resolves| WILDCARD[Wildcard Detected]
    CHECK -->|No response| SAFE[Safe to Enumerate]
    WILDCARD --> FILTER[Filter Results]
    SAFE --> PROCESS[Process Normally]
```

### Detection Method

1. Generate random subdomain string
2. Query `random-string.target.com`
3. If resolves → domain has wildcard DNS
4. Filter subsequent results against wildcard response

## DNS Caching

Responses are cached respecting TTL values:

| Cache Layer | Storage | TTL |
|-------------|---------|-----|
| **In-Memory** | Session cache | Query duration |
| **File** | Disk cache | DNS TTL |
| **Database** | Graph DB | Permanent |

## DNS Discovery Handlers

The DNS plugin ecosystem includes specialized handlers executed by priority:

| Handler | Priority | Function |
|---------|----------|----------|
| DNS TXT Handler | 1 | Extract TXT record data (SPF, DKIM, etc.) |
| DNS CNAME Handler | 2 | Follow CNAME relationships |
| DNS IP Handler | 3 | Resolve A/AAAA records |
| DNS Subdomain Handler | 4 | Enumerate subdomains |
| DNS Apex Handler | 5 | Analyze root domain records |
| DNS Reverse Handler | 8 | Perform reverse DNS lookups |

## DNS Discovery Techniques

### Subdomain Enumeration

```mermaid
flowchart LR
    subgraph Passive["Passive Sources"]
        CT[Certificate Transparency]
        APIS[Third-party APIs]
        ARCHIVES[Web Archives]
    end

    subgraph Active["Active Techniques"]
        BRUTE[Brute Forcing]
        NSEC[NSEC Walking]
        ZONE[Zone Transfers]
    end

    Passive --> RESULTS[(Discovered Subdomains)]
    Active --> RESULTS
```

### Techniques

| Technique | Description | Mode |
|-----------|-------------|------|
| **Brute Forcing** | Wordlist-based subdomain guessing | Active |
| **NSEC Walking** | Exploit DNSSEC NSEC/NSEC3 records | Active |
| **Zone Transfer** | AXFR queries (rarely successful) | Active |
| **Reverse DNS** | PTR record lookups from IPs | Active |
| **Certificate Transparency** | CT log analysis | Passive |
| **API Queries** | Third-party data sources | Passive |

### Brute Force Configuration

| Flag | Description |
|------|-------------|
| `-brute` | Enable brute forcing |
| `-w` | Custom wordlist path |
| `-min-for-recursive` | Minimum discoveries before recursive brute forcing |
| `-max-depth` | Maximum subdomain label depth |

## DNS Resolution Flow

```mermaid
sequenceDiagram
    participant Plugin
    participant Dispatcher
    participant RateLimiter
    participant Resolver
    participant Cache

    Plugin->>Dispatcher: DNS Query Request
    Dispatcher->>Cache: Check Cache
    alt Cache Hit
        Cache-->>Plugin: Cached Response
    else Cache Miss
        Dispatcher->>RateLimiter: Request Slot
        RateLimiter-->>Dispatcher: Approved
        Dispatcher->>Resolver: Execute Query
        Resolver-->>Dispatcher: DNS Response
        Dispatcher->>Cache: Store (with TTL)
        Dispatcher-->>Plugin: Fresh Response
    end
```

## Feedback Loop

Discovered assets generate new DNS queries, enabling cascading discovery:

```
example.com (seed)
    │
    ├─► DNS Resolution → 192.0.2.1
    │   └─► Reverse DNS → mail.example.com (new FQDN)
    │       └─► DNS Resolution → 192.0.2.10
    │
    ├─► TXT Records → SPF includes mx.example.com
    │   └─► DNS Resolution (new FQDN queued)
    │
    └─► Certificate → SAN: api.example.com
        └─► DNS Resolution (new FQDN queued)
```

## Best Practices

!!! tip "DNS Performance"
    - Use trusted resolvers (`-tr`) for higher throughput
    - Set appropriate rate limits to avoid resolver blocks
    - Enable caching for repeated queries
    - Use passive mode (`-passive`) for stealth reconnaissance

!!! warning "Rate Limiting"
    Aggressive DNS queries can trigger rate limiting or blocks from DNS providers. Always respect the configured QPS limits.

## Technical Reference

The following diagrams detail DNS internals from the resolver infrastructure and query execution subsystems.

### Resolver Pool Architecture

```mermaid
graph TB
    subgraph "Configuration Layer"
        ConfigYAML["config.yaml<br/>Resolver Lists"]
        DefaultBaseline["DefaultBaselineResolvers<br/>17 Trusted IPs"]
        PublicDNSInfo["public-dns.info<br/>CSV Download"]
    end

    subgraph "Resolver Pool Management"
        BaselinePool["baselineResolvers<br/>78 Trusted Servers<br/>Variable QPS"]
        TrustedPool["trusted *pool.Pool"]
        PublicPool["PublicResolvers []string"]
    end

    subgraph "Selection and Execution"
        RandomSelector["selectors.NewRandom()<br/>Load Distribution"]
        ConnPool["conn.New()<br/>Connection Pool"]
        PoolExec["pool.New()<br/>Query Execution"]
    end

    subgraph "Wildcard Detection"
        WildcardDetector["detector *wildcards.Detector<br/>8.8.4.4 Single Server"]
        EffectiveTLD["publicsuffix.EffectiveTLDPlusOne()<br/>Domain Extraction"]
    end

    ConfigYAML --> BaselinePool
    DefaultBaseline --> BaselinePool
    PublicDNSInfo --> PublicPool

    BaselinePool --> TrustedPool
    PublicPool --> TrustedPool

    TrustedPool --> RandomSelector
    RandomSelector --> ConnPool
    ConnPool --> PoolExec

    WildcardDetector --> EffectiveTLD
    PoolExec --> WildcardDetector
```

### DNS Plugin Layer

```mermaid
graph TB
    subgraph "DNS Plugin Layer"
        TXTHandler["dnsTXT Handler"]
        CNAMEHandler["dnsCNAME Handler"]
        IPHandler["dnsIP Handler"]
        PTRHandler["dnsReverse Handler"]
    end

    subgraph "Support Package"
        PerformQuery["support.PerformQuery(name, qtype)"]
        QueryLoop["Retry loop (10x)"]
        TrustedPool["trusted *pool.Pool<br/>(78 baseline resolvers)"]
        WildcardDetector["detector *wildcards.Detector<br/>(8.8.4.4)"]
    end

    subgraph "Resolve Library"
        PoolExchange["pool.Exchange(ctx, msg)"]
        RandomSelector["Random resolver selection"]
        Connection["TCP/UDP connection"]
        NetworkQuery["DNS protocol query"]
    end

    TXTHandler --> PerformQuery
    CNAMEHandler --> PerformQuery
    IPHandler --> PerformQuery
    PTRHandler --> PerformQuery

    PerformQuery --> QueryLoop
    QueryLoop --> TrustedPool
    TrustedPool --> PoolExchange

    QueryLoop --> WildcardDetector

    PoolExchange --> RandomSelector
    RandomSelector --> Connection
    Connection --> NetworkQuery
```

### PerformQuery Execution Flow

```mermaid
flowchart TD
    PerformQuery["PerformQuery(name, qtype)"]
    BuildMsg["Build DNS Message"]
    TypeCheck{"qtype == PTR?"}
    QueryMsg["utils.QueryMsg(name, qtype)"]
    ReverseMsg["utils.ReverseMsg(name)"]
    DnsQuery["dnsQuery(msg, trusted)"]
    WildcardCheck["wildcardDetected(resp, detector)"]
    ValidateAnswers["Validate Answer Records"]
    ExtractRR["Extract RRs by Type"]

    PerformQuery --> BuildMsg
    BuildMsg --> TypeCheck
    TypeCheck -->|No| QueryMsg
    TypeCheck -->|Yes| ReverseMsg
    QueryMsg --> DnsQuery
    ReverseMsg --> DnsQuery
    DnsQuery --> WildcardCheck
    WildcardCheck -->|Not Wildcard| ValidateAnswers
    WildcardCheck -->|Wildcard| ErrorReturn["Return wildcard error"]
    ValidateAnswers --> ExtractRR
    ExtractRR -->|RRs Found| Success["Return []dns.RR"]
    ExtractRR -->|No RRs| ErrorReturn

    subgraph "Retry Loop (up to 10 attempts)"
        BuildMsg
        TypeCheck
        QueryMsg
        ReverseMsg
        DnsQuery
        WildcardCheck
        ValidateAnswers
        ExtractRR
    end
```

### DNS Query Response Handling

```mermaid
flowchart LR
    Input["dns.Msg"]
    Exchange["pool.Exchange(ctx, msg)"]
    CheckRcode{"Check Rcode"}
    NameError["RcodeNameError"]
    Success["RcodeSuccess"]
    CheckAnswers{"len(Answer) > 0?"}

    Input --> Exchange
    Exchange --> CheckRcode
    CheckRcode -->|NameError| NameError
    CheckRcode -->|Success| Success
    CheckRcode -->|Other| OtherError["Return unexpected response error"]
    NameError --> ErrorNameNotExist["Error: name does not exist"]
    Success --> CheckAnswers
    CheckAnswers -->|Yes| ReturnResp["Return dns.Msg"]
    CheckAnswers -->|No| ErrorNoRecord["Error: no record of this type"]
```

### Wildcard Response Validation

```mermaid
flowchart TD
    Response["DNS Response"]
    ExtractName["Extract Question Name"]
    GetETLD1["publicsuffix.EffectiveTLDPlusOne(name)"]
    CallDetector["detector.WildcardDetected(ctx, resp, dom)"]
    WildcardResult{"Is Wildcard?"}
    CheckAnswers["Check len(resp.Answer) > 0"]
    FilterByType["utils.AnswersByType(resp, qtype)"]
    ValidateRRs{"len(rr) > 0?"}

    Response --> ExtractName
    ExtractName --> GetETLD1
    GetETLD1 --> CallDetector
    CallDetector --> WildcardResult
    WildcardResult -->|Yes| RejectWildcard["Reject: wildcard detected"]
    WildcardResult -->|No| CheckAnswers
    CheckAnswers --> FilterByType
    FilterByType --> ValidateRRs
    ValidateRRs -->|Yes| Accept["Accept Response"]
    ValidateRRs -->|No| RejectNoRR["Reject: no matching RRs"]
```

### Wildcard Detector Initialization

```mermaid
flowchart TD
    TrustedResolvers["trustedResolvers()"]
    CreateDetectorNS["servers.NewNameserver(8.8.4.4)"]
    CreateConns["conn.New(cpus, single_selector)"]
    CreateDetector["wildcards.NewDetector(serv, wconns, nil)"]

    TrustedResolvers --> CreateDetectorNS
    CreateDetectorNS --> CreateConns
    CreateConns --> CreateDetector
    CreateDetector --> DetectorInstance["detector (global var)"]
```

### Resolver Configuration Loading

```mermaid
graph TB
    subgraph "Configuration Loading"
        ConfigFile["config.yaml<br/>resolvers: [...]"]
        LoadSettings["loadResolverSettings()"]

        ConfigFile --> LoadSettings
        LoadSettings --> CheckFormat{"Is IP Address?"}

        CheckFormat -->|Yes| AddIP["Append to resolversList"]
        CheckFormat -->|No| ParsePath["Treat as File Path"]

        ParsePath --> LoadFile["loadResolversFromFile()"]
        LoadFile --> ParseLines["Split by Newlines"]
        ParseLines --> ValidateIP["net.ParseIP() Each Line"]
        ValidateIP --> AddIP

        AddIP --> Dedupe["stringset.Deduplicate()"]
        Dedupe --> Assign["c.Resolvers = resolverIPs"]
    end

    subgraph "Resolver Management Functions"
        SetResolvers["SetResolvers(...)"]
        AddResolvers["AddResolvers(...)"]
        CalcQPS["CalcMaxQPS()"]

        SetResolvers --> AddResolvers
        AddResolvers --> CalcQPS
    end

    Assign --> SetResolvers
```
