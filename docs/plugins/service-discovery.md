# Service Discovery Plugins


Service Discovery Plugins actively probe and identify running services on discovered assets. These plugins transform passive asset discoveries (FQDNs and IP addresses) into detailed service information including HTTP endpoints, TLS certificates, and service fingerprints.

!!! info "Active scanning required"
    Service discovery plugins require `Config.Active == true` to operate. HTTP-Probes and JARM plugins skip processing entirely when active scanning is disabled.

## Overview

Service discovery plugins operate at **priority 9** in the event processing pipeline, running after DNS resolution and API enrichment have identified basic assets. These plugins:

1. **Actively probe** HTTP/HTTPS endpoints on configured ports
2. **Extract TLS certificates** from HTTPS connections
3. **Fingerprint services** using JARM TLS fingerprinting
4. **Discover organization affiliations** via DNS TXT records containing site verification tokens
5. **Create Service assets** with detailed metadata (headers, response bodies, certificates)

| Plugin Name | Handler Priority | Event Types | Purpose |
|-------------|-----------------|-------------|---------|
| DNS-SD | 9 | FQDN | Extracts organization identifiers from TXT records |
| HTTP-Probes | 9 | FQDN, IPAddress | Probes HTTP/HTTPS services, extracts TLS certificates |
| JARM-Fingerprint | N/A | Service | Generates JARM fingerprints for TLS services |

---

## System Architecture

### Service Discovery Flow

```mermaid
graph TD
    FQDN["FQDN Event<br/>(Priority 1-3)"]
    IPAddr["IPAddress Event<br/>(Priority 3-4)"]
    
    DNS_SD["DNS-SD Plugin<br/>txtHandler"]
    HTTP_FQDN["HTTP-Probes<br/>fqdnEndpoint"]
    HTTP_IP["HTTP-Probes<br/>ipaddrEndpoint"]
    
    TXT_Lookup["TXT Record Lookup<br/>Cache Query"]
    HTTP_Probe["HTTP Request<br/>Ports 80/443/8080/8443"]
    TLS_Extract["TLS Certificate<br/>Extraction"]
    
    Org_Asset["Organization Asset<br/>oamorg.Organization"]
    Service_Asset["Service Asset<br/>platform.Service"]
    Cert_Asset["TLSCertificate Asset<br/>oamcert.TLSCertificate"]
    
    JARM_Plugin["JARM-Fingerprint<br/>jarmPlugin"]
    JARM_Hash["JARM Hash<br/>EdgeProperty"]
    
    FQDN --> DNS_SD
    FQDN --> HTTP_FQDN
    IPAddr --> HTTP_IP
    
    DNS_SD --> TXT_Lookup
    TXT_Lookup --> Org_Asset
    
    HTTP_FQDN --> HTTP_Probe
    HTTP_IP --> HTTP_Probe
    
    HTTP_Probe --> TLS_Extract
    HTTP_Probe --> Service_Asset
    TLS_Extract --> Cert_Asset
    
    Service_Asset --> JARM_Plugin
    JARM_Plugin --> JARM_Hash
    
    Cert_Asset -.-> JARM_Plugin
```

---

## DNS-SD Plugin

The **DNS-SD** (DNS Service Discovery) plugin analyzes DNS TXT records to discover organization affiliations through site verification tokens. When services like Google, Microsoft, or Adobe verify domain ownership, they require placing specific TXT records that contain company identifiers.

### Plugin Registration

The DNS-SD plugin registers a single handler:

```mermaid
graph LR
    Registry["Registry"]
    DNS_Plugin["dnsPlugin<br/>Name: DNS-SD<br/>Confidence: 80"]
    TXT_Handler["txtHandler<br/>Priority: 9<br/>EventType: FQDN"]
    
    Registry --> DNS_Plugin
    DNS_Plugin --> TXT_Handler
```

### TXT Record Processing

The `txtHandler` processes FQDN events by:

1. **Querying the cache** for existing TXT records using `GetEntityTags` with relationship type `"dns_record"`
2. **Filtering for TXT records** by checking `prop.Header.RRType == dns.TypeTXT`
3. **Matching verification prefixes** against a database of 100+ known service verification patterns
4. **Creating Organization assets** when matches are found

```mermaid
sequenceDiagram
    participant Event as Event[FQDN]
    participant Handler as txtHandler
    participant Cache as Session.Cache()
    participant OrgCreate as org.CreateOrgAsset()
    participant Dispatch as Dispatcher

    Event->>Handler: check(e)
    Handler->>Handler: TTLStartTime()
    Handler->>Cache: GetEntityTags(entity, "dns_record")
    Cache-->>Handler: []Tag (TXT records)
    Handler->>Handler: Match prefixes
    Handler->>OrgCreate: CreateOrgAsset()
    OrgCreate-->>Handler: Organization Entity
    Handler->>Dispatch: DispatchEvent(Organization)
```

### Site Verification Database

The plugin maintains a comprehensive database of verification record prefixes mapped to organization names:

| Verification Prefix | Organization |
|---------------------|--------------|
| `google-site-verification=` | Google LLC |
| `MS=` | Microsoft Corporation |
| `apple-domain-verification=` | Apple Inc. |
| `facebook-domain-verification=` | Meta Platforms, Inc. |
| `amazonses=` / `amazonses:` | Amazon Web Services, Inc. |

The complete database includes **100+ verification patterns** for services including Zoom, Slack, Adobe, Shopify, Stripe, Twilio, and many others. When a match is found, a `"verified_for"` relationship edge is created between the FQDN and the Organization asset.

---

## HTTP-Probes Plugin

The **HTTP-Probes** plugin is the core service discovery mechanism, actively probing HTTP and HTTPS endpoints to discover running web services, extract TLS certificates, and collect service metadata.

### Plugin Architecture

```mermaid
graph TB
    HTTP_Plugin["httpProbing<br/>Name: HTTP-Probes<br/>Confidence: 100"]
    
    FQDN_Handler["fqdnEndpoint<br/>Priority: 9<br/>EventType: FQDN<br/>Transforms: Service, TLSCertificate"]
    
    IP_Handler["ipaddrEndpoint<br/>Priority: 9<br/>EventType: IPAddress<br/>MaxInstances: 100<br/>Transforms: Service, TLSCertificate"]
    
    Query_Func["query(target, port)<br/>HTTP Request<br/>5 second timeout"]
    
    Store_Func["store(resp, entity, port)<br/>Create Service Asset<br/>Extract Certificates<br/>Create Relationships"]
    
    HTTP_Plugin --> FQDN_Handler
    HTTP_Plugin --> IP_Handler
    
    FQDN_Handler --> Query_Func
    IP_Handler --> Query_Func
    
    Query_Func --> Store_Func
```

### Port Configuration

The plugin probes ports specified in `Config.Scope.Ports`. Default ports:

| Port | Protocol |
|------|----------|
| 80 | HTTP |
| 443 | HTTPS |
| 8080 | HTTP (alternate) |
| 8443 | HTTPS (alternate) |

Protocol selection: ports 80 and 8080 use `http`; all others default to `https`.

### FQDN Endpoint Handler

The `fqdnEndpoint` handler processes FQDN events with these filtering criteria:

1. **Active scanning enabled** — `Config.Active == true`
2. **DNS resolution exists** — Asset has A, AAAA, or CNAME records
3. **In scope** — FQDN passes scope validation

TTL-based caching avoids redundant probes:

```mermaid
graph TD
    Check["check(event)"]
    TTL_Check{"AssetMonitoredWithinTTL?"}
    Lookup["lookup(cache, since)"]
    Query["query(probe endpoints)"]
    Mark["MarkAssetMonitored()"]
    
    Check --> TTL_Check
    TTL_Check -->|"Yes"| Lookup
    TTL_Check -->|"No"| Query
    Query --> Mark
    Lookup --> Process["process(findings)"]
    Query --> Process
```

### IPAddress Endpoint Handler

The `ipaddrEndpoint` handler includes additional filtering:

1. **Reserved address check** — Skips RFC 1918 private addresses
2. **Scope validation** — IP must be in configured CIDR ranges

When an IP address is probed, the handler also initiates a **sweep** of nearby addresses:

```mermaid
graph LR
    Target_IP["Target IP<br/>e.g., 192.168.1.50"]
    Sweep["IPAddressSweep<br/>Size: 25 addresses"]
    Subnet["Subnet Calculation<br/>/18 for IPv4<br/>/64 for IPv6"]
    Nearby["Nearby IPs<br/>25 addresses around target"]
    
    Target_IP --> Sweep
    Sweep --> Subnet
    Subnet --> Nearby
    Nearby --> Dispatch["Dispatch new<br/>IPAddress Events"]
```

### Service Asset Creation

The `store` function creates comprehensive Service assets from HTTP responses:

```mermaid
graph TB
    Response["HTTP Response"]
    
    TLS_Chain["TLS Certificate Chain<br/>resp.TLS.PeerCertificates"]
    Service_Asset["platform.Service<br/>Output: body<br/>OutputLen: length<br/>Attributes: headers"]
    
    Cert_Chain["Certificate Chain Loop"]
    First_Cert["First Certificate<br/>oamcert.TLSCertificate"]
    Issuer_Certs["Issuing Certificates<br/>issuing_certificate edges"]
    
    Port_Rel["PortRelation<br/>PortNumber: port<br/>Protocol: http/https"]
    Cert_Rel["SimpleRelation<br/>Name: certificate"]
    
    Response --> TLS_Chain
    Response --> Service_Asset
    
    TLS_Chain --> Cert_Chain
    Cert_Chain --> First_Cert
    Cert_Chain --> Issuer_Certs
    
    Service_Asset --> Port_Rel
    Service_Asset --> Cert_Rel
```

**Service Asset (`platform.Service`):**

| Field | Description |
|-------|-------------|
| `ID` | Unique hash-based identifier |
| `Output` | HTTP response body (truncated) |
| `OutputLen` | Response length in bytes |
| `Attributes` | HTTP headers as map |

**TLS Certificate Asset (`oamcert.TLSCertificate`):**

| Field | Description |
|-------|-------------|
| `SerialNumber` | X.509 serial number |
| `Subject` | Certificate subject DN |
| `Issuer` | Certificate issuer DN |
| `NotBefore` / `NotAfter` | Validity period |

**Relationship Types:**

| From Asset | Relation | To Asset | Purpose |
|------------|----------|----------|---------|
| FQDN/IPAddress | `port` (PortRelation) | Service | Associates service with endpoint and port |
| Service | `certificate` | TLSCertificate | Links service to its TLS certificate |
| TLSCertificate | `issuing_certificate` | TLSCertificate | Certificate chain hierarchy |

### TLS Certificate Chain

```mermaid
graph LR
    Service["Service Asset"]
    Leaf["TLSCertificate<br/>Leaf Certificate<br/>Subject: *.example.com"]
    Intermediate["TLSCertificate<br/>Intermediate CA<br/>Subject: Let's Encrypt"]
    Root["TLSCertificate<br/>Root CA<br/>Subject: ISRG Root"]
    
    Service -->|"certificate"| Leaf
    Leaf -->|"issuing_certificate"| Intermediate
    Intermediate -->|"issuing_certificate"| Root
```

### Service Identifier Generation

Service assets use a deterministic identifier generated by hashing the session ID and target address:

```go
hash := maphash.Hash
hash.SetSeed(MakeSeed())
serv := ServiceWithIdentifier(&hash, session.ID(), addr)
```

This ensures uniqueness within a session, deterministic regeneration, and collision resistance across different targets.

---

## JARM Fingerprint Plugin

The **JARM-Fingerprint** plugin generates TLS fingerprints for HTTPS services using the JARM fingerprinting technique, which analyzes server TLS handshake responses to create unique service signatures.

### Plugin Behavior

```mermaid
graph TD
    Service_Event["Service Event<br/>(from HTTP-Probes)"]
    JARM_Handler["jarmPlugin Handler<br/>MaxInstances: 25"]
    
    Cert_Check{"Has TLS<br/>Certificate?"}
    TTL_Check{"Monitored<br/>Within TTL?"}
    
    Query["query()<br/>Collect port relationships"]
    Target_Select["Select HTTPS targets<br/>FQDN > IPAddress priority"]
    
    Fingerprint["JARMFingerprint()<br/>10 TLS probes<br/>Generate hash"]
    
    Store["store()<br/>Add JARM EdgeProperty"]
    
    Service_Event --> JARM_Handler
    JARM_Handler --> Cert_Check
    Cert_Check -->|"No"| Skip["Skip"]
    Cert_Check -->|"Yes"| TTL_Check
    TTL_Check -->|"Already done"| Skip
    TTL_Check -->|"Not done"| Query
    Query --> Target_Select
    Target_Select --> Fingerprint
    Fingerprint --> Store
```

### JARM Fingerprinting Process

```mermaid
sequenceDiagram
    participant Plugin as jarmPlugin
    participant Support as support.JARMFingerprint()
    participant Target as Target Service
    
    Plugin->>Support: JARMFingerprint(asset, portrel)
    Support->>Support: GetProbes(host, port)
    
    loop For each of 10 probes
        Support->>Support: BuildProbe(config)
        Support->>Target: TCP Connect + TLS ClientHello
        Target-->>Support: TLS ServerHello
        Support->>Support: ParseServerHello()
    end
    
    Support->>Support: RawHashToFuzzyHash()
    Support-->>Plugin: JARM Hash (62 chars)
    Plugin->>Plugin: store(hash as EdgeProperty)
```

### JARM Probe Configuration

| Probe # | TLS Version | Cipher Suite Order | Extensions | ALPN |
|---------|-------------|-------------------|------------|------|
| 1 | TLS 1.2 | Forward | Standard | HTTP/1.1 |
| 2 | TLS 1.2 | Reverse | Standard | HTTP/1.1 |
| 3 | TLS 1.2 | Forward | Rare | HTTP/1.1 |
| 4 | TLS 1.2 | Forward | Standard | None |
| 5 | TLS 1.1 | Forward | Standard | None |
| 6 | TLS 1.2 | Forward | Standard | None |
| 7 | TLS 1.3 | Forward | Standard | HTTP/1.1 |
| 8 | TLS 1.3 | Reverse | Standard | HTTP/1.1 |
| 9 | TLS 1.3 | Forward | Invalid | HTTP/1.1 |
| 10 | TLS 1.2 | Forward | Standard | HTTP/1.1 |

### JARM Hash Storage

The JARM hash is stored as an **EdgeProperty** on the `port` relationship edge:

```mermaid
graph LR
    FQDN_IP["FQDN or IPAddress"]
    Service["Service Asset"]
    Port_Edge["Port Edge<br/>PortRelation"]
    JARM_Prop["SimpleProperty<br/>Name: JARM<br/>Value: hash"]
    
    FQDN_IP -->|"port"| Port_Edge
    Port_Edge --> Service
    Port_Edge -->|"property"| JARM_Prop
```

This approach associates the fingerprint with the specific port/protocol combination, allowing different fingerprints for different ports on the same host.

---
