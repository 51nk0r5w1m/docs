# Aviato Plugin

The Aviato Plugin integrates with the Aviato API to enrich organization data with company information, funding rounds, and employee relationships. This plugin discovers employees working at target organizations, enriches company profiles with legal names and operational details, and tracks funding round information. For information about other API integration plugins, see [API Integration Plugins](#6.3). For DNS-based discovery, see [DNS Discovery Plugins](#6.2).

## Overview

The Aviato plugin (`engine/plugins/api/aviato/`) provides four specialized handlers that query the Aviato commercial API at `https://data.api.aviato.co/`. The plugin operates on `Organization` and `Identifier` assets, creating enriched organization profiles and discovering employee relationships through the `member` edge type.

The plugin implements rate limiting at 0.5 requests per second (one request every 2 seconds) and supports multiple API keys for distributing load. All handlers use TTL-based caching to avoid redundant API queries within configured time windows.

## Plugin Architecture

The Aviato plugin is instantiated via `NewAviato()`  and registers four handlers during its `Start()` method :

| Handler Name | Priority | Event Type | Transforms | Purpose |
|-------------|----------|------------|------------|---------|
| `Aviato-Company-Search-Handler` | 6 | `Organization` | `Identifier` | Search for Aviato company ID |
| `Aviato-Employees-Handler` | 6 | `Identifier` | `Person` | Discover employee relationships |
| `Aviato-Company-Enrich-Handler` | 7 | `Identifier` | `Organization` | Enrich organization data |
| `Aviato-Company-Rounds-Handler` | 7 | `Identifier` | `Organization`, `Account`, `FundsTransfer` | Discover funding rounds |

The plugin struct  maintains:
- `name`: Plugin identifier ("Aviato")
- `log`: Structured logger
- `rlimit`: Rate limiter (0.5 QPS)
- `companyEnrich`, `companyRounds`, `employees`, `companySearch`: Handler instances
- `source`: Source metadata with 90% confidence rating

## Handler Registration and Data Flow

```mermaid
graph TB
    subgraph "Event Sources"
        OrgAsset["Organization Asset<br/>org.Organization"]
        IdentAsset["Identifier Asset<br/>general.Identifier"]
    end
    
    subgraph "Priority 6 Handlers"
        CompanySearch["companySearch<br/>Aviato-Company-Search-Handler"]
        Employees["employees<br/>Aviato-Employees-Handler"]
    end
    
    subgraph "Priority 7 Handlers"
        CompanyEnrich["companyEnrich<br/>Aviato-Company-Enrich-Handler"]
        CompanyRounds["companyRounds<br/>Aviato-Company-Rounds-Handler"]
    end
    
    subgraph "API Endpoints"
        SearchAPI["POST /company/search"]
        EnrichAPI["GET /company/enrich"]
        EmployeesAPI["GET /company/{id}/employees"]
        RoundsAPI["GET /company/{id}/rounds"]
    end
    
    subgraph "Created Assets"
        AviatoID["Identifier<br/>Type: aviato_company_id"]
        PersonAsset["Person<br/>people.Person"]
        EnrichedOrg["Updated Organization<br/>+ LegalName + Headcount"]
    end
    
    OrgAsset -->|"EventType: Organization"| CompanySearch
    CompanySearch --> SearchAPI
    SearchAPI --> AviatoID
    
    AviatoID -->|"EventType: Identifier"| Employees
    AviatoID -->|"EventType: Identifier"| CompanyEnrich
    AviatoID -->|"EventType: Identifier"| CompanyRounds
    
    Employees --> EmployeesAPI
    EmployeesAPI --> PersonAsset
    
    CompanyEnrich --> EnrichAPI
    EnrichAPI --> EnrichedOrg
    
    CompanyRounds --> RoundsAPI
```

## Company Search Handler

The `companySearch` handler  converts `Organization` assets into Aviato-specific company identifiers. This handler executes first (priority 6) in the Aviato pipeline.

### Search Process

```mermaid
graph TD
    OrgEvent["Event<br/>Entity: Organization"]
    
    CheckCache["support.AssetMonitoredWithinTTL()<br/>Check if recently queried"]
    
    LookupCache["companySearch.lookup()<br/>Query cache for existing ID"]
    
    QueryAPI["companySearch.query()<br/>POST to /company/search"]
    
    ExtractBrand["org.ExtractBrandName()<br/>Extract company brand name"]
    
    BuildDSL["Build DSL filter<br/>operation: eq, value: brand"]
    
    APIRequest["POST /company/search<br/>Authorization: Bearer {key}"]
    
    ParseResponse["Parse companySearchResult<br/>Extract Items[0].ID"]
    
    StoreID["companySearch.store()<br/>Create Identifier asset"]
    
    CreateEdge["Create id edge<br/>Organization --id--> Identifier"]
    
    DispatchEvent["Dispatch Identifier event<br/>Triggers priority 7 handlers"]
    
    OrgEvent --> CheckCache
    CheckCache -->|"Not monitored"| QueryAPI
    CheckCache -->|"Monitored"| LookupCache
    
    QueryAPI --> ExtractBrand
    ExtractBrand --> BuildDSL
    BuildDSL --> APIRequest
    APIRequest --> ParseResponse
    ParseResponse --> StoreID
    
    LookupCache --> DispatchEvent
    StoreID --> CreateEdge
    CreateEdge --> DispatchEvent
```

### DSL Query Structure

The handler constructs a domain-specific language (DSL) query :

```json
{
  "dsl": {
    "offset": 0,
    "limit": 10,
    "filters": [
      {
        "name": {
          "operation": "eq",
          "value": "<extracted_brand_name>"
        }
      }
    ]
  }
}
```

The `dsl` struct  and `dslEvalObj` struct  define this query format. The handler uses `org.ExtractBrandName()`  to normalize organization names before querying.

### Response Processing

The API returns a `companySearchResult`  containing matching companies. The handler selects the first match  and creates an `Identifier` asset with:
- `Type`: `AviatoCompanyID` constant 
- `ID`: Company ID from API response
- `UniqueID`: Formatted as `aviato_company_id:{company_id}`

## Company Enrich Handler

The `companyEnrich` handler  receives `Identifier` events with type `AviatoCompanyID` and enriches the associated `Organization` asset with detailed company information.

### Enrichment Data Flow

```mermaid
graph LR
    IdentEvent["Identifier Event<br/>Type: aviato_company_id"]
    
    ValidateType["Check oamid.Type<br/>== AviatoCompanyID"]
    
    CheckTTL["support.AssetMonitoredWithinTTL()<br/>Check freshness"]
    
    FindOrg["companyEnrich.lookup()<br/>Traverse id edge to Organization"]
    
    QueryEnrich["GET /company/enrich?id={id}<br/>companyEnrichResult"]
    
    UpdateOrg["Update Organization fields<br/>Active, LegalName, Headcount"]
    
    CreateLegalID["Create Identifier<br/>Type: legal_name"]
    
    LinkLegalID["Create id edge<br/>Organization --id--> LegalName"]
    
    DispatchOrg["Dispatch Organization event<br/>With enriched data"]
    
    IdentEvent --> ValidateType
    ValidateType -->|"Valid"| CheckTTL
    CheckTTL -->|"Not fresh"| FindOrg
    FindOrg --> QueryEnrich
    QueryEnrich --> UpdateOrg
    UpdateOrg --> CreateLegalID
    CreateLegalID --> LinkLegalID
    LinkLegalID --> DispatchOrg
```

### Enrichment Fields

The `companyEnrichResult` struct  contains extensive company data. The handler updates the following `Organization` fields :

| Field | Source | Type |
|-------|--------|------|
| `Active` | `data.Status == "active"` | boolean |
| `NonProfit` | `data.IsNonProfit` | boolean |
| `Headcount` | `data.Headcount` | integer |
| `LegalName` | `data.LegalName` | string |

When a `LegalName` is discovered and the organization lacks one, the handler:
1. Creates a new `Identifier` asset with type `general.LegalName` 
2. Links it to the organization via an `id` edge 
3. Tags the identifier with `SourceProperty` 

## Employees Handler

The `employees` handler  discovers employee relationships by querying the Aviato API for personnel associated with a company. This handler operates at priority 6, alongside the company search handler.

### Employee Discovery Process

```mermaid
graph TD
    IdentEvent["Identifier Event<br/>Type: aviato_company_id"]
    
    CheckType["employees.check()<br/>Validate Type == AviatoCompanyID"]
    
    CheckTTL["support.AssetMonitoredWithinTTL()<br/>Person asset TTL"]
    
    LookupCache["employees.lookup()<br/>Find existing member edges"]
    
    QueryAPI["employees.query()<br/>Paginated API calls"]
    
    GetOrg["employees.getAssociatedOrg()<br/>Traverse id edge backward"]
    
    PaginationLoop["Loop through pages<br/>perPage=1000"]
    
    APICall["GET /company/{id}/employees<br/>?perPage=1000&page={n}"]
    
    ParseEmployees["Parse employeesResult<br/>Extract Employees array"]
    
    StoreEmployees["employees.store()<br/>Create Person assets"]
    
    FullNameParse["support.FullNameToPerson()<br/>Parse name into Person"]
    
    CreateMember["Create member edge<br/>Organization --member--> Person"]
    
    DispatchPersons["employees.process()<br/>Dispatch Person events"]
    
    IdentEvent --> CheckType
    CheckType -->|"Valid"| CheckTTL
    CheckTTL -->|"Not monitored"| QueryAPI
    CheckTTL -->|"Monitored"| LookupCache
    
    QueryAPI --> GetOrg
    GetOrg --> PaginationLoop
    PaginationLoop --> APICall
    APICall --> ParseEmployees
    ParseEmployees -->|"More pages"| PaginationLoop
    ParseEmployees -->|"Done"| StoreEmployees
    
    StoreEmployees --> FullNameParse
    FullNameParse --> CreateMember
    CreateMember --> DispatchPersons
```

### Pagination Handling

The employees endpoint supports pagination with the following parameters :
- `perPage`: Set to 1000 records per page
- `page`: Zero-indexed page number
- Response includes `Pages` field indicating total pages

The handler iterates through API keys if rate limits or errors occur, allowing failover across multiple keys .

### Employee Data Structure

Each employee record (`employeeResult` ) contains:
- `Person.FullName`: Used to create `people.Person` asset
- `Person.ID`: Aviato person identifier
- `PositionList`: Array of job titles and descriptions
- `StartDate`/`EndDate`: Employment period

The handler uses `support.FullNameToPerson()`  to parse full names into structured `Person` assets with `GivenName` and `FamilyName` fields.

### Relationship Creation

For each employee, the handler:
1. Creates a `people.Person` asset 
2. Adds `SourceProperty` metadata 
3. Creates a `member` edge from Organization to Person 
4. Dispatches a new Person event 

## Company Rounds Handler

The `companyRounds` handler  is registered to discover funding round information. This handler is defined but the implementation file was not provided in the source files. Based on the type definitions, it processes `companyFundingRound` data  which includes:

| Field | Description |
|-------|-------------|
| `MoneyRaised` | Funding amount |
| `Stage` | Round type (Seed, Series A, etc.) |
| `AnnouncedOn` | Date of announcement |
| `LeadPersonInvestors` | Lead individual investors |
| `PersonInvestors` | Other individual investors |
| `LeadCompanyInvestors` | Lead institutional investors |
| `CompanyInvestors` | Other institutional investors |

The handler is registered with priority 7 and transforms to `Organization`, `Account`, and `FundsTransfer` asset types .

## API Integration Details

### Rate Limiting

The plugin implements strict rate limiting via `golang.org/x/time/rate` :

```go
limit := rate.Every(2 * time.Second)
rlimit: rate.NewLimiter(limit, 1)
```

This enforces a maximum of **0.5 requests per second** (one request every 2 seconds) across all handlers. Each handler calls `rlimit.Wait(context.TODO())` before making API requests , , .

### Authentication

All API requests use Bearer token authentication :

```
Authorization: Bearer {apikey}
```

The plugin retrieves API keys from the configuration system :
1. Calls `e.Session.Config().GetDataSourceConfig()`
2. Extracts `Apikey` from each credential in `ds.Creds`
3. Iterates through keys on failure for redundancy

### API Endpoints

| Endpoint | Method | Purpose | Handler |
|----------|--------|---------|---------|
| `/company/search` | POST | Search by company name | `companySearch` |
| `/company/enrich?id={id}` | GET | Get company details | `companyEnrich` |
| `/company/{id}/employees?perPage={n}&page={p}` | GET | List employees | `employees` |
| `/company/{id}/rounds` | GET | Get funding rounds | `companyRounds` |

All endpoints use the base URL `https://data.api.aviato.co` and require `Content-Type: application/json` headers.

### Error Handling

All handlers implement consistent error handling :
1. Check HTTP status code (expect 200)
2. Validate response body is non-empty
3. Check for error strings in response
4. Log errors with structured logging via `e.Session.Log().Error()`
5. Continue to next API key on failure

The handlers use 20-second timeouts for all HTTP requests , , .

## TTL-Based Caching Strategy

All handlers implement TTL-based caching to prevent redundant API queries. The caching flow:

```mermaid
graph LR
    Event["Event Received"]
    
    GetTTL["support.TTLStartTime()<br/>Get TTL from config"]
    
    CheckMonitored["support.AssetMonitoredWithinTTL()<br/>Check if recently queried"]
    
    LookupCache["Handler.lookup()<br/>Query cache for results"]
    
    QueryAPI["Handler.query()<br/>Call Aviato API"]
    
    MarkMonitored["support.MarkAssetMonitored()<br/>Record query timestamp"]
    
    Process["Handler.process()<br/>Dispatch new events"]
    
    Event --> GetTTL
    GetTTL --> CheckMonitored
    CheckMonitored -->|"Fresh data"| LookupCache
    CheckMonitored -->|"Stale/missing"| QueryAPI
    LookupCache --> Process
    QueryAPI --> MarkMonitored
    MarkMonitored --> Process
```

The TTL configuration specifies cache duration for each asset type pair:
- **Company Search**: `Organization` → `Identifier` TTL
- **Company Enrich**: `Identifier` → `Organization` TTL
- **Employees**: `Identifier` → `Person` TTL

Each handler calls `support.AssetMonitoredWithinTTL()` , ,  to check if the asset was queried within the TTL window. If cached data exists, the handler retrieves it from the cache instead of making an API request.

## Configuration

To enable the Aviato plugin, add the following to your `config.yaml`:

```yaml
datasources:
  - name: Aviato
    ttl: 4320  # 72 hours
    creds:
      - apikey: "your_aviato_api_key_1"
      - apikey: "your_aviato_api_key_2"  # Optional: additional keys for redundancy
```

Multiple API keys provide failover capability when rate limits are hit or errors occur. The plugin automatically rotates through available keys.

The `ttl` value controls how long cached results remain valid before re-querying the API. A 72-hour TTL balances data freshness with API quota conservation.
