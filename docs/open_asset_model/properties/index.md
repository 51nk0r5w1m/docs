# :simple-owasp: Properties

In the [OWASP](https://owasp.org) [Open Asset Model](https://github.com/owasp-amass/open-asset-model), a **property** is a typed, descriptive annotation attached to an asset or relation. Properties enrich the graph with granular metadata—timestamps, names, identifiers, classifications, fingerprints, and other scalar or structured values—without altering the core topology of the asset graph.

Properties are **first-class elements** of the model. They provide the facts that support inferences, highlight critical traits, and enable high-resolution filtering or grouping of graph data. Each property is tied to the context in which it was discovered, and many include source attribution for traceability.

## :material-database-outline: Why *Properties* Matter

If assets are the **nouns** and relations are the **verbs** of the graph, then **properties are the adjectives**. They give each node and edge its character.

Properties bring three core advantages to the OAM:

1. **Precision** – Properties allow representation of fine-grained detail like last time enumerated and confidence score of evidence.
2. **Traceability** – Many property types (e.g., `SourceProperty`, `DNSRecordProperty`) retain the discovery method and timestamp.
3. **Flexibility** – Because properties are modular and loosely typed, new data can be integrated without schema migrations.

## :material-graph-outline: Property Definition

> **Property**: *A typed key-value annotation attached to an asset or relation, used to describe a specific observable or characteristic.*

Each property answers three questions:

1. **What kind of information is this?**  
   The **type** (e.g., `SimpleProperty`, `DNSRecordProperty`, `VulnProperty`).

2. **What does it say?**  
   A **key-value pair** or structured object expressing some fact about the asset.

3. **Where did it come from?**  
   Optional **source metadata**, such as the tool, timestamp, or confidence level.

## :material-graph-outline: Core Property Types

| Property Type         | Purpose                                      | Example Use Case |
|-----------------------|----------------------------------------------|------------------|
| `SimpleProperty`      | Generic key-value metadata                   | Tag a domain with `last_monitored = 2025-06-20` |
| `SourceProperty`      | Key-value pair with discovery context        | Tag an IP with `whois_country = US` from RDAP |
| `DNSRecordProperty`   | Structured DNS lookup result                 | Record an `A` record resolution for an FQDN |
| `VulnProperty`        | Basic vulnerability data                     | Attach `CVE-2023-1234` to a service asset |

Each property is evaluated in the context of its parent asset or relation and contributes to filtering, scoring, reporting, and pivot logic within the model.

## :material-graph-outline: Property Schema (Conceptually)

Example of a basic `SourceProperty` attached to an `IPAddress`:

```json
{
  "type": "SourceProperty",
  "name": "RDAP",
  "confidence": 75,
}
```

Example of a DNSRecordProperty on an FQDN:

```json
{
  "type": "DNSRecordProperty",
  "property_name": "dns_record",
  "header": {
    "rr_type": 6,
    "class": 1,
    "ttl": 86400,
  },
  "data": "example.com. 86400 IN SOA ns1.example.com. admin.example.com.",
}
```

## :material-graph-outline: Properties in Graph Queries

Properties are not directly navigable edges, but they are critical for filtering and analysis. They can be used in:

assoc queries to filter assets by specific values.

Temporal analysis to find stale, newly discovered, or frequently updated assets.

## :material-graph-outline: Where to Go Next

Explore the types of data used to enrich and explain assets in the graph:

- [Assets](../assets/index.md) – The core entities in the graph.
- [Relations](../relations/index.md) – Overview of Relations in the Open Asset Model.
- [Triples](../../asset_db/triples.md) – Performing graph queries using SPARQL-style syntax.

---

## Technical Reference

### Property Interface Architecture

```mermaid
graph TB
    subgraph "Property Interface"
        Interface["Property Interface"]
        Name["Name() string<br/>Returns property name"]
        Value["Value() string<br/>Returns string representation"]
        PropType["PropertyType() PropertyType<br/>Returns type constant"]
        JSON["JSON() ([]byte, error)<br/>Serializes to JSON"]
    end

    Interface --> Name
    Interface --> Value
    Interface --> PropType
    Interface --> JSON

    subgraph "PropertyType Enumeration"
        DNSRecordProp["DNSRecordProperty"]
        SimpleProp["SimpleProperty"]
        SourceProp["SourceProperty"]
        VulnProp["VulnProperty"]
    end

    PropType -.returns one of.-> DNSRecordProp
    PropType -.returns one of.-> SimpleProp
    PropType -.returns one of.-> SourceProp
    PropType -.returns one of.-> VulnProp
```

### PropertyType Constants

```mermaid
graph LR
    PropertyType["PropertyType"]

    PropertyType --> DNSRecord["DNSRecordProperty<br/>DNS resource record data"]
    PropertyType --> Simple["SimpleProperty<br/>Generic key-value pairs"]
    PropertyType --> Source["SourceProperty<br/>Data source attribution"]
    PropertyType --> Vuln["VulnProperty<br/>Vulnerability information"]
```

| Constant | String Value | Purpose |
|----------|--------------|---------|
| `DNSRecordProperty` | `"DNSRecordProperty"` | DNS records that don't reference other assets (e.g., TXT, SPF) |
| `SimpleProperty` | `"SimpleProperty"` | Generic key-value properties |
| `SourceProperty` | `"SourceProperty"` | Data source metadata with confidence scores |
| `VulnProperty` | `"VulnProperty"` | Vulnerability or security information |

### Concrete Implementations

#### DNSRecordProperty Structure

```mermaid
graph TB
    subgraph "DNSRecordProperty Structure"
        DNSRecord["DNSRecordProperty"]
        PropName["PropertyName: string<br/>JSON: property_name"]
        Header["Header: RRHeader<br/>JSON: header"]
        Data["Data: string<br/>JSON: data"]
    end

    DNSRecord --> PropName
    DNSRecord --> Header
    DNSRecord --> Data

    subgraph "RRHeader Structure"
        RRHeader["RRHeader"]
        RRType["RRType: int<br/>DNS record type code"]
        Class["Class: int<br/>DNS class (usually 1)"]
        TTL["TTL: int<br/>Time-to-live in seconds"]
    end

    Header -.contains.-> RRHeader
    RRHeader --> RRType
    RRHeader --> Class
    RRHeader --> TTL

    subgraph "Interface Implementation"
        NameMethod["Name() string<br/>Returns PropertyName"]
        ValueMethod["Value() string<br/>Returns Data"]
        TypeMethod["PropertyType()<br/>Returns DNSRecordProperty"]
        JSONMethod["JSON() ([]byte, error)<br/>Marshals struct"]
    end

    DNSRecord -.implements.-> NameMethod
    DNSRecord -.implements.-> ValueMethod
    DNSRecord -.implements.-> TypeMethod
    DNSRecord -.implements.-> JSONMethod
```

#### SimpleProperty Structure

```mermaid
graph TB
    subgraph "SimpleProperty Structure"
        Simple["SimpleProperty"]
        PropName["PropertyName: string<br/>JSON: property_name"]
        PropValue["PropertyValue: string<br/>JSON: property_value"]
    end

    Simple --> PropName
    Simple --> PropValue

    subgraph "Interface Implementation"
        NameImpl["Name() string<br/>Returns PropertyName"]
        ValueImpl["Value() string<br/>Returns PropertyValue"]
        TypeImpl["PropertyType()<br/>Returns SimpleProperty"]
        JSONImpl["JSON() ([]byte, error)<br/>Marshals struct"]
    end

    Simple -.implements.-> NameImpl
    Simple -.implements.-> ValueImpl
    Simple -.implements.-> TypeImpl
    Simple -.implements.-> JSONImpl
```

#### SourceProperty Structure

```mermaid
graph TB
    subgraph "SourceProperty Structure"
        Source["SourceProperty"]
        SourceField["Source: string<br/>JSON: name"]
        Confidence["Confidence: int<br/>JSON: confidence"]
    end

    Source --> SourceField
    Source --> Confidence

    subgraph "Interface Implementation"
        NameImpl["Name() string<br/>Returns Source field"]
        ValueImpl["Value() string<br/>Returns Confidence as string"]
        TypeImpl["PropertyType()<br/>Returns SourceProperty"]
        JSONImpl["JSON() ([]byte, error)<br/>Marshals struct"]
    end

    Source -.implements.-> NameImpl
    Source -.implements.-> ValueImpl
    Source -.implements.-> TypeImpl
    Source -.implements.-> JSONImpl

    ValueConversion["strconv.Itoa(p.Confidence)<br/>Converts int to string"]
    ValueImpl -.uses.-> ValueConversion
```

### Property vs. Relationship Distinction

```mermaid
graph TB
    Decision{"Does the data<br/>reference another<br/>asset in the graph?"}

    Decision -->|Yes| Relationship["Use Relation<br/>Creates graph edge<br/>Example: DNS A record<br/>pointing to IP address"]

    Decision -->|No| Property["Use Property<br/>Attaches metadata<br/>Example: DNS TXT record<br/>containing text data"]

    subgraph "Relationship Examples"
        RelEx1["FQDN → IPAddress<br/>(A record)"]
        RelEx2["Service → TLSCertificate<br/>(certificate relation)"]
        RelEx3["Organization → Location<br/>(location relation)"]
    end

    Relationship -.examples.-> RelEx1
    Relationship -.examples.-> RelEx2
    Relationship -.examples.-> RelEx3

    subgraph "Property Examples"
        PropEx1["FQDN with TXT record<br/>(SPF, DMARC)"]
        PropEx2["Asset with source<br/>(data provenance)"]
        PropEx3["Asset with custom tag<br/>(metadata)"]
    end

    Property -.examples.-> PropEx1
    Property -.examples.-> PropEx2
    Property -.examples.-> PropEx3
```

| Criterion | Use Relationship | Use Property |
|-----------|------------------|--------------|
| References another asset? | Yes | No |
| Creates graph traversal path? | Yes | No |
| Represents edge data? | Yes | No |
| Represents node metadata? | No | Yes |
| Example: DNS A record | `BasicDNSRelation` | N/A |
| Example: DNS TXT record | N/A | `DNSRecordProperty` |
| Example: Data source info | N/A | `SourceProperty` |

---

© 2025 Jeff Foley — Licensed under Apache 2.0.
