# Plugin System

The plugin system is Amass's primary extensibility mechanism, enabling modular asset discovery and enrichment capabilities. Plugins implement handlers that transform input assets into related output assets through DNS queries, API calls, active probing, or other discovery techniques.

---

## Plugin Architecture

### Core Interface

All plugins implement the `et.Plugin` interface defined in the engine types package:

```mermaid
classDiagram
    class Plugin {
        <<interface>>
        +Name() string
        +Start(Registry) error
        +Stop()
    }
    
    class Registry {
        <<interface>>
        +RegisterHandler(Handler) error
        +Log() *slog.Logger
    }
    
    class Handler {
        +Plugin Plugin
        +Name string
        +Priority int
        +MaxInstances int
        +Transforms []string
        +EventType AssetType
        +Callback func(*Event) error
    }
    
    Plugin --> Registry : registers handlers
    Handler --> Plugin : references parent
```

The `Plugin` interface requires three methods:

- **`Name()`** — Returns the plugin's unique identifier string
- **`Start(Registry)`** — Called during engine initialization to register handlers and set up resources
- **`Stop()`** — Called during engine shutdown to clean up resources

### Plugin Lifecycle

```mermaid
sequenceDiagram
    participant E as Engine
    participant R as Registry
    participant P as Plugin
    participant H as Handler
    
    E->>P: NewPlugin()
    E->>P: Start(Registry)
    P->>P: Initialize resources
    P->>R: RegisterHandler(handler1)
    P->>R: RegisterHandler(handler2)
    R->>R: Build asset pipelines
    Note over E,H: Plugin operational
    E->>P: Stop()
    P->>P: Clean up resources
```

During the `Start()` phase, plugins typically:

1. Initialize logging with `r.Log().WithGroup("plugin").With("name", d.name)`
2. Create handler instances (often as nested structs)
3. Register each handler with the `Registry`
4. Start any background goroutines (e.g., session cleanup)

---

## Handler Registration and Execution

### Handler Structure

Each handler registered by a plugin must provide:

| Field | Type | Description |
|-------|------|-------------|
| `Plugin` | `et.Plugin` | Reference to parent plugin |
| `Name` | `string` | Unique handler identifier |
| `Priority` | `int` | Execution priority (1–9, lower executes first) |
| `MaxInstances` | `int` | Maximum concurrent handler instances (0 = unlimited) |
| `Transforms` | `[]string` | Output asset types this handler produces |
| `EventType` | `oam.AssetType` | Input asset type this handler processes |
| `Callback` | `func(*et.Event) error` | Function invoked when asset matches EventType |

### Priority-Based Execution

The priority system determines handler execution order, creating a processing pipeline:

```mermaid
graph LR
    FQDN["FQDN Event"] --> TXT["DNS-TXT<br/>Priority: 1"]
    TXT --> CNAME["DNS-CNAME<br/>Priority: 2"]
    CNAME --> IP["DNS-IP<br/>Priority: 3"]
    IP --> Subs["DNS-Subs<br/>Priority: 4"]
    Subs --> Apex["DNS-Apex<br/>Priority: 5"]
    Apex --> IPNet["IP-Netblock<br/>Priority: 4"]
    IPNet --> Rev["DNS-Reverse<br/>Priority: 8"]
    Rev --> Probe["HTTP-Probes<br/>Priority: 9"]
```

Priority assignment rationale:

- **Priority 1** — TXT record lookup (discovers organization identifiers)
- **Priority 2** — CNAME resolution (must resolve before IP lookup)
- **Priority 3** — A/AAAA resolution (base IP discovery)
- **Priority 4** — NS/MX/SRV enumeration (subdomain discovery)
- **Priority 5** — Apex domain hierarchy building
- **Priority 8** — PTR reverse DNS lookups
- **Priority 9** — Active HTTP service probing

### Handler Callback Pattern

```mermaid
sequenceDiagram
    participant D as Dispatcher
    participant H as Handler
    participant C as Cache
    participant Q as DNS/API
    
    D->>H: callback(Event)
    H->>H: Extract asset from Event.Entity
    H->>H: Check TTL (lookup or query?)
    alt Within TTL
        H->>C: Lookup cached results
        C-->>H: Return cached entities
    else Outside TTL
        H->>Q: Perform query
        Q-->>H: Return results
        H->>C: Store results
        H->>C: MarkAssetMonitored
    end
    H->>D: DispatchEvent for each result
    H-->>D: Return nil/error
```

All handler callbacks follow this pattern:

1. **Asset Extraction** — Extract typed asset from `e.Entity.Asset` (e.g., `*oamdns.FQDN`)
2. **TTL Check** — Determine if asset was recently monitored within TTL window
3. **Lookup/Query Decision** — Use cached results if within TTL, otherwise perform new query
4. **Storage** — Store new results in session cache with source attribution
5. **Event Emission** — Dispatch new events for discovered assets
6. **Error Handling** — Return nil on success or error on failure

---

## Plugin Registration Flow

```mermaid
sequenceDiagram
    participant M as main.go
    participant E as Engine
    participant R as Registry
    participant P1 as DNS Plugin
    participant P2 as HTTP Plugin
    participant P3 as BGPTools Plugin
    
    M->>E: NewEngine()
    E->>R: NewRegistry()
    M->>P1: NewDNS()
    M->>P2: NewHTTPProbing()
    M->>P3: NewBGPTools()
    M->>E: RegisterPlugin(P1)
    M->>E: RegisterPlugin(P2)
    M->>E: RegisterPlugin(P3)
    E->>P1: Start(Registry)
    P1->>R: RegisterHandler(dnsTXT)
    P1->>R: RegisterHandler(dnsCNAME)
    P1->>R: RegisterHandler(dnsIP)
    E->>P2: Start(Registry)
    P2->>R: RegisterHandler(fqdnEndpoint)
    P2->>R: RegisterHandler(ipaddrEndpoint)
    E->>P3: Start(Registry)
    P3->>R: RegisterHandler(netblock)
    P3->>R: RegisterHandler(autsys)
    R->>R: BuildAssetPipelines()
    Note over E,R: Engine ready for events
```

---

## Creating Custom Plugins

### Step 1: Implement the Plugin Interface

```go
package myplugin

import (
    "log/slog"
    et "github.com/owasp-amass/amass/v5/engine/types"
    oam "github.com/owasp-amass/open-asset-model"
)

type myPlugin struct {
    name   string
    log    *slog.Logger
    source *et.Source
}

func NewMyPlugin() et.Plugin {
    return &myPlugin{
        name: "MyPlugin",
        source: &et.Source{
            Name:       "MyPlugin",
            Confidence: 100,
        },
    }
}

func (p *myPlugin) Name() string { return p.name }

func (p *myPlugin) Start(r et.Registry) error {
    p.log = r.Log().WithGroup("plugin").With("name", p.name)
    return r.RegisterHandler(&et.Handler{
        Plugin:       p,
        Name:         p.name + "-Handler",
        Priority:     5,
        MaxInstances: 10,
        Transforms:   []string{string(oam.IPAddress)},
        EventType:    oam.FQDN,
        Callback:     p.handleFQDN,
    })
}

func (p *myPlugin) Stop() {}
```

### Step 2: Implement Handler Callback

```go
func (p *myPlugin) handleFQDN(e *et.Event) error {
    fqdn, ok := e.Entity.Asset.(*oamdns.FQDN)
    if !ok {
        return errors.New("failed to extract FQDN")
    }

    since, err := support.TTLStartTime(e.Session.Config(),
        string(oam.FQDN), string(oam.IPAddress), p.name)
    if err != nil {
        return err
    }

    var results []*dbt.Entity
    if support.AssetMonitoredWithinTTL(e.Session, e.Entity, p.source, since) {
        results = p.lookup(e, e.Entity, since)
    } else {
        results = p.query(e, fqdn)
        support.MarkAssetMonitored(e.Session, e.Entity, p.source)
    }

    p.process(e, results)
    return nil
}
```

### Key Considerations

!!! tip "Plugin development best practices"
    1. **Source Attribution** — Always attach `SourceProperty` to created entities and edges
    2. **TTL Caching** — Use `AssetMonitoredWithinTTL` to avoid redundant queries
    3. **Error Handling** — Return errors from callbacks to signal failure
    4. **Logging** — Use structured logging with plugin name context
    5. **Concurrency** — Set `MaxInstances` to limit concurrent handler executions
    6. **Priority** — Choose priority based on data dependencies (lower = earlier)

---

## Plugin Categories

<div class="grid cards" markdown>

-   :material-dns:{ .lg .middle } **DNS Discovery Plugins**

    ---

    Six specialized handlers covering TXT, CNAME, A/AAAA, NS/MX/SRV, apex hierarchy, and PTR reverse lookups.

    [:octicons-arrow-right-24: DNS Discovery](dns-discovery.md)

-   :material-api:{ .lg .middle } **API Integration Plugins**

    ---

    GLEIF, Aviato, RDAP, and WHOIS plugins that enrich discovered assets with legal entity, corporate intelligence, and registration data.

    [:octicons-arrow-right-24: API Integrations](api-integrations.md)

-   :material-server-network:{ .lg .middle } **Service Discovery Plugins**

    ---

    DNS-SD, HTTP-Probes, and JARM-Fingerprint plugins that actively probe endpoints to identify running services and TLS certificates.

    [:octicons-arrow-right-24: Service Discovery](service-discovery.md)

-   :material-layers-plus:{ .lg .middle } **Enrichment Plugins & Support Utilities**

    ---

    Horizontals scope expansion, IP-Netblock mapping, and the shared support utilities used by all plugin categories.

    [:octicons-arrow-right-24: Enrichment & Utilities](enrichment.md)

</div>
