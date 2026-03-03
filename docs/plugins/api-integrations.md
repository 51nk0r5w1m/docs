# API Integration Plugins

API integration plugins query external authoritative data sources to enrich discovered assets with additional context such as organization identifiers, employee information, funding data, and registration records. These plugins extend beyond active DNS probing by leveraging third-party APIs to build comprehensive asset profiles.

## Overview

| Plugin | API Source | Primary Asset Types | Transformations | Priority Range |
|--------|------------|---------------------|-----------------|----------------|
| **GLEIF** | GLEIF API (gleif.org) | `Organization` → `Identifier` (LEI) | Organization hierarchies, legal names | 5–6 |
| **Aviato** | Aviato API (aviato.co) | `Organization` → `Person`, `FundsTransfer` | Employees, funding rounds, company data | 6–7 |
| **RDAP** | RDAP servers | `AutonomousSystem`, `Netblock` → `AutnumRecord`, `IPNetRecord` | Contact records, registration data | 1, 9 |
| **WHOIS** | WHOIS servers | `DomainRecord` | Name servers, registrant contacts | Variable |

All API plugins follow common architectural patterns: TTL-based caching to avoid redundant queries, rate limiting to respect API constraints, API key management through the configuration system, and source attribution with confidence scoring.

---

## Handler Registration and Priorities

```mermaid
graph TB
    subgraph "Event Types and Handler Registration"
        OrgEvent["Organization Event"]
        IdentEvent["Identifier Event"]
        ASNEvent["AutonomousSystem Event"]
        NetblockEvent["Netblock Event"]
    end
    
    subgraph "GLEIF Plugin (100 confidence)"
        FuzzyHandler["fuzzyCompletions Handler<br/>Priority: 6<br/>Organization → Identifier"]
        RelatedHandler["relatedOrgs Handler<br/>Priority: 5<br/>Identifier → Organization"]
    end
    
    subgraph "Aviato Plugin (90 confidence)"
        CompanySearch["companySearch Handler<br/>Priority: 6<br/>Organization → Identifier"]
        CompanyEnrich["companyEnrich Handler<br/>Priority: 7<br/>Identifier → Organization"]
        Employees["employees Handler<br/>Priority: 6<br/>Identifier → Person"]
        CompanyRounds["companyRounds Handler<br/>Priority: 7<br/>Identifier → Org/Account/FundsTransfer"]
    end
    
    subgraph "RDAP Plugin (100 confidence)"
        AutsysHandler["autsys Handler<br/>Priority: 9<br/>AutonomousSystem → AutnumRecord"]
        AutonumHandler["autnum Handler<br/>Priority: 1<br/>AutnumRecord → Contacts/Orgs"]
        NetblockHandler["netblock Handler<br/>Priority: 9<br/>Netblock → IPNetRecord"]
        IPNetHandler["ipnet Handler<br/>Priority: 1<br/>IPNetRecord → Contacts/Orgs"]
    end
    
    OrgEvent --> FuzzyHandler
    OrgEvent --> CompanySearch
    IdentEvent --> RelatedHandler
    IdentEvent --> CompanyEnrich
    IdentEvent --> Employees
    IdentEvent --> CompanyRounds
    ASNEvent --> AutsysHandler
    NetblockEvent --> NetblockHandler
    
    FuzzyHandler --> IdentEvent
    CompanySearch --> IdentEvent
    RelatedHandler --> OrgEvent
    CompanyEnrich --> OrgEvent
```

---

## API Plugin Architecture Patterns

```mermaid
graph TB
    Event["Event with Asset Entity"]
    
    subgraph "Handler Processing Flow"
        Check["handler.check()<br/>Validate asset type"]
        TTLCheck{"AssetMonitoredWithinTTL?"}
        Lookup["lookup()<br/>Query local cache"]
        Query["query()<br/>Call external API"]
        Store["store()<br/>Create new entities/edges"]
        Process["process()<br/>Dispatch new events"]
    end
    
    subgraph "External Resources"
        APIEndpoint["External API<br/>(GLEIF, Aviato, RDAP)"]
        RateLimit["Rate Limiter<br/>rate.Limiter"]
        ConfigCreds["Config Credentials<br/>API Keys"]
    end
    
    Event --> Check
    Check --> TTLCheck
    TTLCheck -->|Within TTL| Lookup
    TTLCheck -->|Expired| Query
    Query --> ConfigCreds
    Query --> RateLimit
    Query --> APIEndpoint
    Query --> Store
    Lookup --> Process
    Store --> Process
    Process --> Event
```

### TTL-Based Monitoring Pattern

All API plugins implement a lookup-before-query pattern to avoid redundant API calls:

1. **TTL Check** — Call `support.TTLStartTime()` to calculate the timestamp before which data is considered stale
2. **Monitored Check** — Call `support.AssetMonitoredWithinTTL()` to check if the asset has been queried recently
3. **Lookup Path** — If within TTL, query the session cache using `OutgoingEdges()` or `IncomingEdges()` with the TTL timestamp
4. **Query Path** — If stale or missing, call the external API, store results, and mark with `support.MarkAssetMonitored()`

```go
since, err := support.TTLStartTime(e.Session.Config(),
    string(oam.Organization), string(oam.Identifier), fc.plugin.name)

var id *dbt.Entity
if support.AssetMonitoredWithinTTL(e.Session, e.Entity, fc.plugin.source, since) {
    id = fc.lookup(e, e.Entity, since)  // Query cache
} else {
    id = fc.query(e, e.Entity)          // Call API
    support.MarkAssetMonitored(e.Session, e.Entity, fc.plugin.source)
}
```

### Rate Limiting Pattern

API plugins use `golang.org/x/time/rate.Limiter` to enforce API rate limits:

```go
// Aviato plugin initialization
limit := rate.Every(2 * time.Second)
return &aviato{
    rlimit: rate.NewLimiter(limit, 1),
}

// In query method
_ = ae.plugin.rlimit.Wait(context.TODO())
resp, err := http.RequestWebPage(ctx, &http.Request{URL: u, Header: headers})
```

---

## Data Enrichment Flow

```mermaid
graph TD
    BaseOrg["Base Organization Asset<br/>oamorg.Organization<br/>Name: 'Google LLC'"]
    
    subgraph "GLEIF Enrichment (Priority 6)"
        GLEIFSearch["fuzzyCompletions.query()<br/>GLEIFSearchFuzzyCompletions()"]
        LEIIdent["Identifier Asset<br/>Type: general.LEICode<br/>ID: 'XXXXX...'"]
        UpdateOrg["updateOrgFromLEIRecord()<br/>Set legal name, jurisdiction,<br/>founding date, status"]
    end
    
    subgraph "GLEIF Hierarchy Discovery (Priority 5)"
        ParentQuery["GLEIFGetDirectParentRecord()"]
        ChildQuery["GLEIFGetDirectChildrenRecords()"]
        ParentOrg["Parent Organization<br/>Relationship: subsidiary"]
        ChildOrgs["Child Organizations<br/>Relationship: subsidiary"]
    end
    
    subgraph "Aviato Enrichment (Priority 6)"
        CompanySearch["companySearch.query()<br/>POST /company/search<br/>DSL filters"]
        AviatoID["Identifier Asset<br/>Type: AviatoCompanyID<br/>ID: company UUID"]
    end
    
    subgraph "Aviato Details (Priority 7)"
        CompanyEnrich["companyEnrich.query()<br/>GET /company/enrich"]
        Employees["employees.query()<br/>GET /company/{id}/employees"]
        FundingRounds["companyRounds.query()<br/>GET /company/{id}/funding-rounds"]
        
        PersonAssets["Person Assets<br/>oampeople.Person<br/>Relationship: member"]
        FundTransfer["FundsTransfer Assets<br/>oamfinancial.FundsTransfer<br/>Account relationships"]
    end
    
    BaseOrg --> GLEIFSearch
    GLEIFSearch --> LEIIdent
    GLEIFSearch --> UpdateOrg
    UpdateOrg --> BaseOrg
    
    LEIIdent --> ParentQuery
    LEIIdent --> ChildQuery
    ParentQuery --> ParentOrg
    ChildQuery --> ChildOrgs
    
    BaseOrg --> CompanySearch
    CompanySearch --> AviatoID
    AviatoID --> CompanyEnrich
    AviatoID --> Employees
    AviatoID --> FundingRounds
    
    Employees --> PersonAssets
    FundingRounds --> FundTransfer
```

---

## GLEIF Plugin

The GLEIF plugin integrates with the Global Legal Entity Identifier Foundation (GLEIF) API to discover and enrich organization data with Legal Entity Identifiers (LEI codes) and corporate hierarchy information.

### Handler Structure

| Handler | Priority | Input Asset | Output Assets | Purpose |
|---------|----------|-------------|---------------|---------|
| `fuzzyCompletions` | 6 | `Organization` | `Identifier` (LEI), enriched `Organization` | Search for LEI codes via fuzzy name matching |
| `relatedOrgs` | 5 | `Identifier` (LEI) | `Organization` (parent/children) | Discover corporate hierarchy relationships |

```mermaid
graph TB
    subgraph "Plugin Registration"
        Plugin["gleif Plugin"]
        Registry["et.Registry"]
        
        Plugin --> FuzzyHandler["fuzzyCompletions Handler<br/>Priority: 6<br/>EventType: Organization<br/>Transforms: [Identifier]"]
        Plugin --> RelatedHandler["relatedOrgs Handler<br/>Priority: 5<br/>EventType: Identifier<br/>Transforms: [Organization]"]
    end
    
    subgraph "Event Flow"
        OrgEvent["et.Event<br/>Asset: Organization"]
        LEIEvent["et.Event<br/>Asset: Identifier (LEI)"]
        
        OrgEvent --> FuzzyCheck["fuzzyCompletions.check()"]
        LEIEvent --> RelatedCheck["relatedOrgs.check()"]
    end
    
    subgraph "Outputs"
        FuzzyCheck --> LEICreated["LEI Identifier Created"]
        FuzzyCheck --> OrgEnriched["Organization Enriched"]
        RelatedCheck --> ParentOrg["Parent Organization"]
        RelatedCheck --> ChildOrgs["Child Organizations"]
    end
    
    Registry --> FuzzyHandler
    Registry --> RelatedHandler
    FuzzyHandler --> FuzzyCheck
    RelatedHandler --> RelatedCheck
```

### Fuzzy Completions Handler

The `fuzzyCompletions` handler processes `Organization` events and attempts to find matching LEI codes using GLEIF's fuzzy completion search API.

```mermaid
graph TD
    OrgEvent["Organization Event<br/>(e.g., 'Google Inc.')"]
    OrgEvent --> CheckTTL["Check TTL Monitor"]
    CheckTTL -->|"Within TTL"| Lookup["lookup()<br/>Check Cache for Existing LEI"]
    CheckTTL -->|"Expired/None"| Query["query()<br/>Perform GLEIF Search"]
    Query --> ExtractBrand["ExtractBrandName()<br/>(e.g., 'Google Inc.' → 'Google')"]
    ExtractBrand --> FuzzyAPI["GLEIFSearchFuzzyCompletions()<br/>API: /fuzzycompletions?field=entity.legalName&q=..."]
    FuzzyAPI --> Filter["filterFuzzyCompletions()<br/>Match Algorithm"]
    Filter --> NameMatch["NameMatch()<br/>Exact/Partial Match"]
    NameMatch --> LocationMatch["LocMatch()<br/>Postal Code Comparison"]
    LocationMatch --> ScoreCalc["Score Calculation<br/>Exact: +30<br/>Single Result: +30<br/>Location Match: +40"]
    ScoreCalc --> GetRecord["GLEIFGetLEIRecord()<br/>Retrieve Full LEI Data"]
    GetRecord --> Store["store()<br/>Create LEI Identifier<br/>Enrich Organization"]
    Store --> Process["process()<br/>Dispatch LEI Event"]
```

**Scoring System:**

- Exact match: 30 points
- Single match bonus: +30 points
- Location match: +40 points
- Partial match: Smith-Waterman-Gotoh algorithm (0–30 points)

### Organization Enrichment from LEI Records

The `updateOrgFromLEIRecord()` method enriches organization assets with:

- Legal name and alternate names as identifiers
- Founding date, jurisdiction, registration ID
- Legal address, headquarters address, other addresses as locations
- Additional identifiers: BIC codes, MIC codes, OpenCorp ID, S&P Global ID

### Related Organizations Handler

The `relatedOrgs` handler discovers corporate hierarchy by querying direct parent and child LEI records:

```mermaid
graph LR
    LEIIdentifier["LEI Identifier<br/>(e.g., GLEIF LEI code)"]
    ParentRecord["GLEIFGetDirectParentRecord()<br/>Parent Organization"]
    ChildRecords["GLEIFGetDirectChildrenRecords()<br/>Subsidiary Organizations"]
    SubsidiaryEdge["Relationship:<br/>subsidiary"]
    
    LEIIdentifier --> ParentRecord
    LEIIdentifier --> ChildRecords
    ParentRecord -->|"creates"| SubsidiaryEdge
    ChildRecords -->|"creates"| SubsidiaryEdge
```

---

## Aviato Plugin

The Aviato plugin provides corporate intelligence through four specialized handlers that discover employees, funding rounds, and detailed company data.

### Custom Identifier Types

```go
const (
    AviatoPersonID  = "aviato_person_id"
    AviatoCompanyID = "aviato_company_id"
)
```

### Handler Pipeline

```mermaid
graph TB
    OrgInput["Organization Input<br/>'Google Inc'"]
    
    CompanySearch["companySearch Handler<br/>Priority: 6<br/>POST /company/search"]
    CompanyID["Identifier Created<br/>aviato_company_id: UUID"]
    
    subgraph "Priority 7 Handlers"
        CompanyEnrich["companyEnrich<br/>GET /company/enrich"]
        CompanyRounds["companyRounds<br/>GET /company/{id}/funding-rounds"]
    end
    
    subgraph "Priority 6 Handler"
        Employees["employees<br/>GET /company/{id}/employees"]
    end
    
    EnrichedOrg["Enriched Organization<br/>+ legal name<br/>+ headcount<br/>+ nonprofit status"]
    PersonList["Person Assets<br/>Relationship: member"]
    FundsList["FundsTransfer Assets<br/>+ Accounts<br/>+ Investors (Person/Org)"]
    
    OrgInput --> CompanySearch
    CompanySearch --> CompanyID
    CompanyID --> CompanyEnrich
    CompanyID --> CompanyRounds
    CompanyID --> Employees
    
    CompanyEnrich --> EnrichedOrg
    Employees --> PersonList
    CompanyRounds --> FundsList
```

### Company Search DSL

The company search handler uses a Domain-Specific Language (DSL) for filtering:

```go
filters := []map[string]*dslEvalObj{
    {
        "name": &dslEvalObj{
            Operation: "eq",
            Value:     brand,
        },
    },
}
reqDSL := &dsl{Offset: 0, Limit: 10, Filters: filters}
```

### Funding Rounds Data Model

The `companyRounds` handler creates a financial relationship graph:

1. **Organization Checking Account** — Creates a default checking account for the target organization
2. **Seed Account** — Creates a temporary account representing the funding source
3. **FundsTransfer Asset** — Represents the funding round with amount, currency, and date
4. **Investor Discovery** — Creates `Person` and `Organization` assets for investors, linking them to the seed account

---

## RDAP Plugin

The RDAP plugin queries Registration Data Access Protocol servers for authoritative registration data about IP networks and autonomous systems.

### Four-Handler Architecture

| Handler | Direction | Priority | Purpose |
|---------|-----------|---------|---------|
| `autsys` | `AutonomousSystem` → `AutnumRecord` | 9 | Creates registration records from ASN assets |
| `autnum` | `AutnumRecord` → `FQDN`, `ContactRecord`, `Organization`, etc. | 1 | Expands registration records |
| `netblock` | `Netblock` → `IPNetRecord` | 9 | Creates registration records from netblock assets |
| `ipnet` | `IPNetRecord` → `FQDN`, `ContactRecord`, `Organization`, etc. | 1 | Expands registration records |

### Bootstrap Client Configuration

RDAP uses a bootstrap client with disk caching to discover the correct RDAP server for any given resource:

```go
c := cache.NewDiskCache()
c.Dir = filepath.Join(outdir, ".openrdap")

bs := &bootstrap.Client{Cache: c}
rd.client = &rdap.Client{
    HTTP:      httpClient,
    Bootstrap: bs,
}
```

### VCard Processing

RDAP responses contain VCard contact data, which the plugin parses to create `ContactRecord` assets with related entities:

```go
v := entity.VCard
if adr := v.GetFirst("adr"); adr != nil {
    // Create Location asset from address label
}
if email := strings.ToLower(v.Email()); email != "" {
    // Create Identifier asset with EmailAddress type
}
if phone := support.PhoneToOAMPhone(v.Tel(), "", v.Country()); phone != nil {
    // Create Phone asset
}
```

---

## WHOIS Plugin

The WHOIS plugin handles traditional WHOIS queries for domain registration data.

### Domain Record Transformation

The `domrec` handler processes `DomainRecord` events and creates relationships to discovered assets:

- Name servers as `FQDN` assets
- WHOIS server as `FQDN` asset
- Contact records for registrar, registrant, admin, technical, and billing contacts

### Contact Record Creation

Each contact type creates a `ContactRecord` with relationships to:

| Asset Type | Relationship | Notes |
|------------|-------------|-------|
| `Person` | — | If name parses successfully |
| `Location` | — | From street address parsing |
| `Identifier` | — | Email addresses |
| `Phone` | — | Regular and fax numbers |
| `URL` | — | Referral URLs |
| `Organization` | — | Organization name |

---

## Integration with Support Utilities

API plugins rely heavily on the support package utilities:

| Function | Purpose |
|----------|---------|
| `support.TTLStartTime()` | Calculate TTL timestamp |
| `support.AssetMonitoredWithinTTL()` | Check if asset was recently queried |
| `support.MarkAssetMonitored()` | Mark asset as monitored |
| `support.StreetAddressToLocation()` | Parse addresses into Location assets |
| `support.FullNameToPerson()` | Parse names into Person assets |
| `support.PhoneToOAMPhone()` | Parse phone numbers into Phone assets |
| `support.ProcessAssetsWithSource()` | Create edges with source attribution |
| `org.CreateOrgAsset()` | Create Organization assets with proper relationships |
| `org.ExtractBrandName()` | Extract brand from organization name |
| `org.NameMatch()` | Match organization names |
| `org.LocMatch()` | Match organization locations |

For detailed documentation on these utilities, see [Enrichment Plugins & Support Utilities](enrichment.md).
