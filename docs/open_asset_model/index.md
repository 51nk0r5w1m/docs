# :simple-owasp: Open Asset Model

The **Amass Project's** [Open Asset Model](https://github.com/owasp-amass/open-asset-model) redefines the understanding of an attack surface. Shifting the paradigm away from narrow, internet infrastructure-focused collection, the **OAM** broadens its scope to include both physical and digital assets. This approach delivers a realistic view of **assets and their lesser-known associations**, utilizing adversarial tactics to gain visibility into potential risks and attack vectors that might otherwise be overlooked.

---

## **//** Overview

- **Deep Attack Surface Intelligence:** Identifies both **physical and digital assets**, moving beyond IT infrastructure.
- **Standardized Asset Framework:** Ensures **consistency in asset classification**, facilitating efficient data exchange and streamlined analysis.
- **Cyclic Discovery:** Recursively approaches data exploration, leveraging each finding to dynamically **expand the target scope**.
- **Community-Driven:** Developed and continuously refined by security experts within the **OWASP Amass** ecosystem.
- **Risk Mapping:** Exposes hidden attack vectors by **mapping asset relationships** and tracking their changes over time.

---

## :material-graph: Explore OAM Asset Types

---

<div class="grid cards" markdown>

-   :material-file-account:{ .lg .middle } __Account__

    ---

    Collect usernames, account types, and related attributes to track exposed user accounts

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/account/)

-   :material-registered-trademark:{ .lg .middle } __Domain Record__

    ---
    
    Gather domain insights, including Whois and registrar details

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/domain_record/)

-   :material-comment-outline:{ .lg .middle } __Contact Record__

    ---

    Link email addresses, phone numbers, and locations to discovered entities

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/contact_record/)

-   :material-dns:{ .lg .middle } __FQDN__

    ---

    Record domain resolutions, DNS records, and associated metadata

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/fqdn/)

-   :material-file-find:{ .lg .middle } __File__

    ---

    Capture file names and hashes to analyze digital artifacts

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/file/)

-   :material-bank:{ .lg .middle } __Funds Transfer__

    ---

    Identify bank accounts, payment systems, and transaction details

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/funds_transfer/)

-   :material-id-card:{ .lg .middle } __Identifier__

    ---

	Track unique IDs, references, or numerical values 

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/identifier/)

-   :material-router:{ .lg .middle } __IP Address__

    ---

    Discover IPs, subnets, and routing structures to uncover key infrastructure

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/ip_address/)

-   :material-office-building-marker:{ .lg .middle } __Organization__

    ---

    Uncover entity designations, locations, and operational details to expose connections

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/organization/)

-   :material-account-outline:{ .lg .middle } __Person__

    ---

     Collect names, locations, and attributes to build individual profiles 

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/person/)

-   :material-apps:{ .lg .middle } __Product__

    ---

     Identify online services, cloud providers, and software ecosystems 

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/product/)

-   :material-file-certificate-outline:{ .lg .middle } __TLS Certificate__

    ---

    Gather SSL/TLS certificate details, issuers, and expiration dates for asset verification

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/tls_certificate/)

-   :material-web-refresh:{ .lg .middle } __URL__

    ---

    Log web addresses and associated content to track online presence

    [:octicons-arrow-right-24: Learn more](https://owasp-amass.github.io/docs/open-asset-model/assets/url/)

</div>

---

## Technical Reference

This section provides architectural diagrams and schema details drawn from the OAM Go package internals.

### Package Structure

OAM is organized into domain-specific Go packages, each containing related asset types:

```mermaid
graph TB
    subgraph "open-asset-model"
        Base["oam (base package)<br/>AssetType interface<br/>Relation interface"]

        General["general<br/>• Identifier<br/>• SourceProperty<br/>• SimpleRelation<br/>• PortRelation<br/>• Location"]

        DNS["dns<br/>• FQDN"]

        Network["network<br/>• IPAddress<br/>• Netblock<br/>• AutonomousSystem"]

        Org["org<br/>• Organization"]

        Registration["registration<br/>• DomainRecord<br/>• AutnumRecord<br/>• IPNetRecord"]

        Certificate["certificate<br/>• TLSCertificate"]

        Contact["contact<br/>• ContactRecord<br/>• Phone"]

        People["people<br/>• Person"]

        Platform["platform<br/>• Service"]

        Financial["financial<br/>• FundsTransfer"]

        Account["account<br/>• Account"]

        URL["url<br/>• URL"]
    end

    subgraph "Amass Integration"
        DBTypes["asset-db/types<br/>dbt.Entity<br/>dbt.Edge"]
        EngineTypes["engine/types<br/>et.Event<br/>et.Asset"]
    end

    Base --> General
    Base --> DNS
    Base --> Network
    Base --> Org
    Base --> Registration
    Base --> Certificate
    Base --> Contact
    Base --> People
    Base --> Platform
    Base --> Financial
    Base --> Account
    Base --> URL

    General --> DBTypes
    DNS --> DBTypes
    Network --> DBTypes
    Org --> DBTypes

    DBTypes --> EngineTypes
```

| Package | Purpose | Key Types |
|---------|---------|-----------|
| `oam` (base) | Core interfaces and types | `AssetType`, `Relation` |
| `general` | Cross-cutting assets and relations | `Identifier`, `SourceProperty`, `SimpleRelation` |
| `dns` | DNS infrastructure | `FQDN` |
| `network` | Network infrastructure | `IPAddress`, `Netblock`, `AutonomousSystem` |
| `org` | Organizational entities | `Organization` |
| `registration` | Registry records | `DomainRecord`, `AutnumRecord`, `IPNetRecord` |
| `certificate` | TLS/SSL certificates | `TLSCertificate` |
| `contact` | Contact information | `ContactRecord`, `Phone` |
| `people` | Individual persons | `Person` |
| `platform` | Running services | `Service` |
| `account` | Financial accounts | `Account` |
| `financial` | Financial transactions | `FundsTransfer` |
| `url` | Web resources | `URL` |

---

### Asset Instantiation Pattern

All OAM assets follow a consistent lifecycle from creation to event dispatch:

```mermaid
graph LR
    A["Create OAM Asset<br/>oamdns.FQDN"] --> B["Wrap in dbt.Entity<br/>session.Cache().CreateAsset()"]
    B --> C["Add Source Property<br/>general.SourceProperty"]
    C --> D["Create Edge<br/>session.Cache().CreateEdge()"]
    D --> E["Add Edge Property<br/>general.SourceProperty"]
    E --> F["Dispatch Event<br/>et.Event with Entity"]
```

---

### Asset-to-Entity Wrapping

OAM assets are wrapped in `dbt.Entity` structures for storage and event propagation:

```mermaid
graph TB
    subgraph "OAM Layer"
        OAM["OAM Asset<br/>e.g., oamdns.FQDN<br/>implements AssetType()"]
    end

    subgraph "Database Layer"
        Entity["dbt.Entity<br/>• ID: string<br/>• Asset: oam.Asset<br/>• CreatedAt: time.Time<br/>• LastSeen: time.Time"]

        Properties["dbt.Property<br/>• general.SourceProperty<br/>• Custom properties"]

        Edge["dbt.Edge<br/>• Relation: oam.Relation<br/>• FromEntity: dbt.Entity<br/>• ToEntity: dbt.Entity"]
    end

    subgraph "Event Layer"
        Event["et.Event<br/>• Name: string<br/>• Entity: dbt.Entity<br/>• Session: et.Session<br/>• Meta: interface{}"]
    end

    OAM --> Entity
    Entity --> Properties
    Entity --> Edge
    Entity --> Event
```

---

### Data Flow: Discovery to Storage

```mermaid
graph TB
    subgraph "Discovery Phase"
        Plugin["Plugin<br/>(e.g., DNS-IP)"]
        Discovery["Discover Data<br/>(DNS query result)"]
    end

    subgraph "Asset Creation Phase"
        CreateOAM["Create OAM Asset<br/>oamnet.IPAddress<br/>{Address: 192.0.2.1}"]
        WrapEntity["Wrap in dbt.Entity<br/>session.Cache().CreateAsset()"]
        AddSource["Add SourceProperty<br/>{Source: 'DNS-IP', Confidence: 100}"]
    end

    subgraph "Relationship Phase"
        CreateEdge["Create Edge<br/>FQDN --dns_record--> IPAddress"]
        AddEdgeSource["Add Edge SourceProperty"]
    end

    subgraph "Graph Storage"
        Cache["Session Cache<br/>(In-Memory)"]
        GraphDB["Graph Database<br/>(Asset-DB)"]
    end

    subgraph "Event Dispatch"
        DispatchEvent["Dispatch et.Event<br/>{Entity: ipEntity}"]
        OtherPlugins["Other Plugins<br/>(e.g., IP-Reverse)"]
    end

    Plugin --> Discovery
    Discovery --> CreateOAM
    CreateOAM --> WrapEntity
    WrapEntity --> AddSource
    AddSource --> CreateEdge
    CreateEdge --> AddEdgeSource
    AddEdgeSource --> Cache
    Cache --> GraphDB
    AddEdgeSource --> DispatchEvent
    DispatchEvent --> OtherPlugins
```

**Process steps:**

1. **Discovery**: Plugin queries external source (DNS, API, etc.)
2. **Asset Creation**: Raw data converted to typed OAM asset
3. **Entity Wrapping**: Asset stored in cache, returns `dbt.Entity`
4. **Attribution**: `SourceProperty` added to entity
5. **Relationship Creation**: Edge created between related entities
6. **Edge Attribution**: `SourceProperty` added to edge
7. **Storage**: Entity and edge persisted to graph database
8. **Event Dispatch**: New entity wrapped in `et.Event` for further processing

---

### Scope Conversion to Assets

User-provided scope (domains, IPs, CIDRs, ASNs) is converted to OAM assets during enumeration initialization:

```mermaid
graph LR
    subgraph "Configuration Scope"
        Domains["config.Scope.Domains<br/>[]string"]
        IPs["config.Scope.Addresses<br/>[]net.IP"]
        CIDRs["config.Scope.CIDRs<br/>[]*net.IPNet"]
        ASNs["config.Scope.ASNs<br/>[]int"]
    end

    subgraph "OAM Assets"
        FQDNAsset["oamdns.FQDN"]
        IPAsset["oamnet.IPAddress"]
        NetblockAsset["oamnet.Netblock"]
        ASAsset["oamnet.AutonomousSystem"]
    end

    subgraph "Engine Assets"
        EngineAsset["et.Asset<br/>{Name, Data: AssetData}"]
    end

    Domains --> FQDNAsset
    IPs --> IPAsset
    CIDRs --> NetblockAsset
    ASNs --> ASAsset

    FQDNAsset --> EngineAsset
    IPAsset --> EngineAsset
    NetblockAsset --> EngineAsset
    ASAsset --> EngineAsset
```

---

### Common Relation Types

| Relation Name | From Asset | To Asset | Semantic Meaning |
|--------------|------------|----------|------------------|
| `dns_record` | FQDN | IPAddress | DNS A/AAAA resolution |
| `id` | Organization | Identifier | Organization identifier |
| `subsidiary` | Organization | Organization | Parent-child relationship |
| `member` | Organization | Person | Employment relationship |
| `port` | IPAddress/FQDN | Service | Network service binding |
| `legal_address` | Organization | Location | Legal registered address |
| `hq_address` | Organization | Location | Headquarters address |
| `location` | ContactRecord | Location | Associated address |
| `organization` | ContactRecord | Organization | Associated company |
| `person` | ContactRecord | Person | Associated individual |
| `phone` | ContactRecord | Phone | Contact phone number |
| `url` | ContactRecord | URL | Related web resource |
| `common_name` | TLSCertificate | FQDN | Certificate CN field |
| `san_dns_name` | TLSCertificate | FQDN | Certificate SAN entry |
| `certificate` | Service | TLSCertificate | TLS certificate used |
| `account` | Organization | Account | Financial account ownership |
| `sender` | FundsTransfer | Account | Funds source |
| `recipient` | FundsTransfer | Account | Funds destination |

---

### Asset Type Constants

All asset types are referenced as typed constants in the `oam` base package:

```go
const (
    FQDN             AssetType = "fqdn"
    IPAddress        AssetType = "ip_address"
    Netblock         AssetType = "netblock"
    AutonomousSystem AssetType = "autonomous_system"
    Organization     AssetType = "organization"
    Identifier       AssetType = "identifier"
    DomainRecord     AssetType = "domain_record"
    AutnumRecord     AssetType = "autnum_record"
    IPNetRecord      AssetType = "ipnet_record"
    TLSCertificate   AssetType = "tls_certificate"
    ContactRecord    AssetType = "contact_record"
    Person           AssetType = "person"
    Service          AssetType = "service"
    Location         AssetType = "location"
    Phone            AssetType = "phone"
    URL              AssetType = "url"
    Account          AssetType = "account"
)
```

These constants are used in handler registration, transformation configuration, and TTL management per asset type.

---

### OAM Specification Architecture

#### Core Interface Specifications

```mermaid
graph LR
    Asset["Asset Interface"]
    Relation["Relation Interface"]
    Property["Property Interface"]

    Asset -->|"Key() string"| KeyMethod["Unique identifier"]
    Asset -->|"AssetType() AssetType"| TypeMethod["Type constant"]
    Asset -->|"JSON() ([]byte, error)"| JSONMethod["Serialization"]

    Relation -->|"Label() string"| LabelMethod["Relationship name"]
    Relation -->|"RelationType() RelationType"| RTypeMethod["Relation category"]
    Relation -->|"JSON() ([]byte, error)"| RJSONMethod["Serialization"]

    Property -->|"Name() string"| NameMethod["Property name"]
    Property -->|"Value() string"| ValueMethod["Property value"]
    Property -->|"PropertyType() PropertyType"| PTypeMethod["Property category"]
    Property -->|"JSON() ([]byte, error)"| PJSONMethod["Serialization"]
```

#### Three-Tier Architecture Overview

```mermaid
graph TB
    subgraph Layer1["Core Abstraction Layer (Interfaces)"]
        Asset["Asset Interface<br/>Key() string<br/>AssetType() AssetType<br/>JSON() ([]byte, error)"]
        Relation["Relation Interface<br/>Label() string<br/>RelationType() RelationType<br/>JSON() ([]byte, error)"]
        Property["Property Interface<br/>Name() string<br/>Value() string<br/>PropertyType() PropertyType<br/>JSON() ([]byte, error)"]
    end

    subgraph Layer2["Type System Layer (Enumerations)"]
        AssetType["AssetType<br/>21 constants<br/>Account, FQDN, IPAddress, etc."]
        RelationType["RelationType<br/>5 constants<br/>BasicDNSRelation, PortRelation, etc."]
        PropertyType["PropertyType<br/>4 constants<br/>DNSRecordProperty, SimpleProperty, etc."]
    end

    subgraph Layer3["Concrete Implementation Layer"]
        FileStruct["file.File struct<br/>implements Asset"]
        FQDNStruct["network.FQDN struct<br/>implements Asset"]
        BasicDNS["dns.BasicDNSRelation struct<br/>implements Relation"]
        SimpleRel["general.SimpleRelation struct<br/>implements Relation"]
        SourceProp["property.SourceProperty struct<br/>implements Property"]
    end

    Asset -.->|"returns"| AssetType
    Relation -.->|"returns"| RelationType
    Property -.->|"returns"| PropertyType

    FileStruct -.->|"implements"| Asset
    FQDNStruct -.->|"implements"| Asset
    BasicDNS -.->|"implements"| Relation
    SimpleRel -.->|"implements"| Relation
    SourceProp -.->|"implements"| Property

    FileStruct -.->|"returns model.File"| AssetType
    BasicDNS -.->|"returns BasicDNSRelation"| RelationType
```

#### Asset Type Taxonomy

```mermaid
graph TD
    Root["AssetType Enumeration"]

    Root --> Network["Network Infrastructure<br/>(6 types)"]
    Root --> Org["Organizational<br/>(5 types)"]
    Root --> Digital["Digital Artifacts<br/>(5 types)"]
    Root --> Financial["Financial<br/>(2 types)"]
    Root --> Product["Product<br/>(2 types)"]
    Root --> Registration["Registration<br/>(3 types)"]
    Root --> Identity["Identity<br/>(1 type)"]

    Network --> FQDN["FQDN"]
    Network --> IPAddress["IPAddress"]
    Network --> Netblock["Netblock"]
    Network --> AutonomousSystem["AutonomousSystem"]

    Org --> Organization["Organization"]
    Org --> Person["Person"]
    Org --> Location["Location"]
    Org --> Phone["Phone"]
    Org --> ContactRecord["ContactRecord"]

    Digital --> File["File"]
    Digital --> URL["URL"]
    Digital --> Service["Service"]
    Digital --> TLSCertificate["TLSCertificate"]
    Digital --> DomainRecord["DomainRecord"]

    Financial --> Account["Account"]
    Financial --> FundsTransfer["FundsTransfer"]

    Product --> ProductType["Product"]
    Product --> ProductRelease["ProductRelease"]

    Registration --> DomainRec["DomainRecord"]
    Registration --> AutnumRecord["AutnumRecord"]
    Registration --> IPNetRecord["IPNetRecord"]

    Identity --> Identifier["Identifier"]
```

#### Relationship Validation System

```mermaid
graph TB
    Discover["Discovery Tool<br/>(e.g., OWASP Amass)"]
    ValidRel["ValidRelationship()"]
    GetTransform["GetTransformAssetTypes()"]
    Central["assetTypeRelations()"]

    Discover -->|"src, label, rtype, dest"| ValidRel
    ValidRel --> GetTransform
    GetTransform --> Central

    Central --> FQDNMap["fqdnRels"]
    Central --> IPMap["ipRels"]
    Central --> OrgMap["orgRels"]
    Central --> ServiceMap["serviceRels"]

    FQDNMap --> PortLabel["'port' label"]
    FQDNMap --> DNSLabel["'dns_record' label"]
    FQDNMap --> NodeLabel["'node' label"]

    DNSLabel --> BasicDNS["BasicDNSRelation:<br/>[FQDN, IPAddress]"]
    DNSLabel --> PrefDNS["PrefDNSRelation:<br/>[FQDN]"]
    DNSLabel --> SRVDNS["SRVDNSRelation:<br/>[FQDN]"]

    PortLabel --> PortRel["PortRelation:<br/>[Service]"]
```

#### RelationType Constants

| RelationType | Purpose | Used For |
|--------------|---------|----------|
| `BasicDNSRelation` | Basic DNS records | A, AAAA, CNAME, NS records |
| `PrefDNSRelation` | DNS records with preference | MX records with priority values |
| `SRVDNSRelation` | DNS service records | SRV records with priority/weight/port |
| `PortRelation` | Service port connections | Port-based service relationships |
| `SimpleRelation` | Generic connections | Most non-DNS relationships |

#### PropertyType Constants

| PropertyType | Purpose |
|--------------|---------|
| `DNSRecordProperty` | DNS-specific metadata (TTL, record type) |
| `SimpleProperty` | Generic key-value properties |
| `SourceProperty` | Data source attribution |
| `VulnProperty` | Vulnerability information |
