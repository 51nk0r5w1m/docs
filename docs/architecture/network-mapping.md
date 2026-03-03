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
