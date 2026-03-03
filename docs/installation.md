# Installation & Deployment

Multiple installation methods are available depending on your platform and use case.

## Installation Methods

### Installation Path Overview

```mermaid
graph TB
    subgraph "Installation Methods"
        GoInstall["Go Install<br/><code>go install</code>"]
        Docker["Docker Pull<br/><code>docker pull</code>"]
        Homebrew["Homebrew<br/><code>brew install</code>"]
        Source["Build from Source<br/><code>goreleaser</code>"]
    end

    subgraph "Distribution Channels"
        GoProxy["Go Module Proxy<br/>proxy.golang.org"]
        DockerHub["Docker Hub<br/>owaspamass/amass"]
        BrewTap["Homebrew Tap<br/>owasp-amass/homebrew-amass"]
        GitHub["GitHub Releases<br/>github.com/owasp-amass/amass"]
    end

    subgraph "Installed Binaries"
        AmassMain["/bin/amass<br/>Main CLI dispatcher"]
        AmassEngine["/bin/amass_engine<br/>Background engine service"]
        OAMEnum["/bin/oam_enum<br/>Enumeration client"]
        OAMSubs["/bin/oam_subs<br/>Subdomain summary"]
        OAMAssoc["/bin/oam_assoc<br/>Association queries"]
        OAMViz["/bin/oam_viz<br/>Graph visualization"]
        OAMTrack["/bin/oam_track<br/>Asset tracking"]
        OAMi2y["/bin/oam_i2y<br/>Import to YAML"]
        AEIsReady["/bin/ae_isready<br/>Engine health check"]
    end

    subgraph "Configuration Files"
        ConfigYAML["resources/config.yaml<br/>Main configuration"]
        DatasourcesYAML["resources/datasources.yaml<br/>API credentials"]
    end

    GoInstall --> GoProxy
    Docker --> DockerHub
    Homebrew --> BrewTap
    Source --> GitHub

    GoProxy --> AmassMain
    DockerHub --> AmassMain
    BrewTap --> AmassMain
    GitHub --> AmassMain

    AmassMain -.-> AmassEngine
    AmassMain -.-> OAMEnum
    AmassMain -.-> OAMSubs
    AmassMain -.-> OAMAssoc
    AmassMain -.-> OAMViz
    AmassMain -.-> OAMTrack
    AmassMain -.-> OAMi2y
    AmassMain -.-> AEIsReady

    GitHub --> ConfigYAML
    GitHub --> DatasourcesYAML
```

### Go Install (Recommended for Developers)

Install directly from source using Go 1.24.0+:

```bash
CGO_ENABLED=0 go install github.com/owasp-amass/amass/v5/cmd/amass@latest
```

The binary will be available in `$GOPATH/bin`.

### Pre-built Releases

Binary packages are available from [GitHub Releases](https://github.com/owasp-amass/amass/releases) for multiple platforms:

| Platform | Architectures |
|----------|---------------|
| **Linux** | amd64, 386, arm, arm64, ARMv6, ARMv7 |
| **Windows** | amd64 |
| **macOS** | amd64, arm64 (Apple Silicon) |

Each release archive includes binaries, documentation, and default configuration files.

### Building from Source

For development or customization, build Amass from source.

```bash
# Clone the repository
git clone https://github.com/owasp-amass/amass.git
cd amass

# Build all binaries
go build -v ./cmd/...

# Or install to $GOPATH/bin
go install -v ./cmd/...
```

**Build Process:**

```mermaid
graph LR
    subgraph "Build Stage"
        BuildBase["golang:1.24.4-alpine<br/>Base image"]
        GitInstall["apk add git<br/>Install Git"]
        CopySource["COPY source files<br/>/go/src/github.com/owasp-amass/amass"]
        GoInstallStep["go install ./...<br/>CGO_ENABLED=0"]
    end

    subgraph "Runtime Stage"
        RuntimeBase["alpine:latest<br/>Minimal base"]
        AddPackages["apk add bash ca-certificates<br/>Runtime dependencies"]
        CopyBinaries["COPY from build stage<br/>All binaries to /bin"]
        UserSetup["Create user 'user'<br/>Setup /data volume"]
    end

    subgraph "Installed Components"
        Bin_amass["/bin/amass"]
        Bin_enum["/bin/enum"]
        Bin_engine["/bin/engine"]
        Bin_subs["/bin/subs"]
        Bin_assoc["/bin/assoc"]
        Bin_viz["/bin/viz"]
        Bin_track["/bin/track"]
        Bin_i2y["/bin/i2y"]
        Bin_isready["/bin/ae_isready"]
    end

    BuildBase --> GitInstall
    GitInstall --> CopySource
    CopySource --> GoInstallStep

    RuntimeBase --> AddPackages
    AddPackages --> CopyBinaries
    CopyBinaries --> UserSetup

    GoInstallStep --> Bin_amass
    GoInstallStep --> Bin_enum
    GoInstallStep --> Bin_engine
    GoInstallStep --> Bin_subs
    GoInstallStep --> Bin_assoc
    GoInstallStep --> Bin_viz
    GoInstallStep --> Bin_track
    GoInstallStep --> Bin_i2y
    GoInstallStep --> Bin_isready
```

The repository uses GitHub Actions for automated testing and building:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **tests** | Push to main/develop, PRs | Run test suite on 3 OS |
| **lint** | Push, PRs | Code quality checks |
| **goreleaser** | Tag push `v*.*.*` | Create releases |
| **docker** | Tag push `v*.*.*` | Build Docker images |

### Docker

```bash
# Pull the latest image
docker pull owaspamass/amass:latest

# Basic enumeration
docker run --rm owaspamass/amass enum -d example.com

# With persistent storage
docker run --rm -v /host/data:/data owaspamass/amass enum -d example.com
```

**Docker Image Details:**

| Property | Value |
|----------|-------|
| Registry | `owaspamass/amass` |
| Platforms | linux/amd64, linux/arm64 |
| Base | Alpine Linux |
| Security | Non-root user |

### Homebrew (macOS)

```bash
brew tap owasp-amass/homebrew-amass
brew install amass
```

## Included Binaries

The installation provides multiple executables:

| Binary | Purpose |
|--------|---------|
| `amass` | Main CLI entry point |
| `enum` | Primary asset discovery interface |
| `engine` | Core enumeration service |
| `ae_isready` | Health check utility |
| `subs` | Subdomain analysis tool |
| `assoc` | Asset association analyzer |
| `viz` | Graph visualization generator |
| `track` | Change detection tool |
| `i2y` | Data format converter |

## System Requirements

### Minimum Resources

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 512 MB | 2 GB+ |
| **Disk** | 100 MB | 1 GB+ |
| **Network** | Internet connectivity | Low-latency connection |

### Platform Support

- Linux (all distributions)
- macOS (Intel and Apple Silicon)
- Windows (64-bit)

## Configuration Directories

### Configuration File Locations

```mermaid
graph TB
    subgraph "Configuration Sources"
        DefaultConfig["Default Config<br/>resources/config.yaml"]
        DefaultDataSources["Default Data Sources<br/>resources/datasources.yaml"]
        EnvVar["Environment Variable<br/>AMASS_CONFIG"]
        CLIFlag["CLI Flag<br/>-config path"]
    end

    subgraph "Search Locations"
        CurrentDir["./config.yaml<br/>Current directory"]
        ConfigDir["~/.config/amass/config.yaml<br/>User config directory"]
        CustomPath["Custom path from<br/>ENV or CLI"]
    end

    subgraph "Loaded Configuration"
        ConfigStruct["Config struct<br/>config.Config"]
        ResolverSettings["DNS Resolvers<br/>Trusted + Public"]
        ScopeSettings["Scope<br/>Domains, IPs, CIDRs, ASNs"]
        APIKeys["API Credentials<br/>Data sources"]
    end

    CLIFlag --> CustomPath
    EnvVar --> CustomPath
    DefaultConfig --> CurrentDir
    DefaultConfig --> ConfigDir

    CustomPath --> ConfigStruct
    CurrentDir --> ConfigStruct
    ConfigDir --> ConfigStruct
    DefaultDataSources --> ConfigStruct

    ConfigStruct --> ResolverSettings
    ConfigStruct --> ScopeSettings
    ConfigStruct --> APIKeys
```

### System-wide Configuration

| Platform | Path |
|----------|------|
| Linux/macOS | `/etc/amass/` |
| Windows | `C:\ProgramData\amass\` |

### User Configuration

| Platform | Path |
|----------|------|
| Linux/macOS | `~/.config/amass/` |
| Windows | `%APPDATA%\amass\` |
| Docker | `/.config/amass/` |

## Docker Deployment

### Basic Usage

```bash
docker run --rm owaspamass/amass enum -d example.com
```

### With Volume Mounts

```bash
# Mount configuration
docker run --rm \
    -v /host/config:/.config/amass \
    owaspamass/amass enum -d example.com

# Mount output directory
docker run --rm \
    -v /host/output:/output \
    owaspamass/amass enum -d example.com -o /output/results.txt
```

### Docker Compose

For production deployments with PostgreSQL:

```bash
git clone https://github.com/owasp-amass/amass-docker-compose.git
cd amass-docker-compose

# Configure passwords in config/assetdb.env
# Update config/config.yaml with database credentials

docker compose run --rm enum -active -d example.com
```

## Verification

Validate successful installation:

```bash
# Check version
amass -version

# Display help
amass help

# Test enumeration (5 minute timeout)
amass enum -d example.com -timeout 5
```

### Expected Output Structure

```mermaid
graph TD
    AmassCmd["amass command"]
    VersionFlag["--version flag"]
    HelpOutput["Help output<br/>Shows subcommands"]

    Subcommands["Available subcommands:<br/>enum, engine, intel, viz,<br/>track, db, help"]

    AmassCmd -->|"-version"| VersionFlag
    AmassCmd -->|"-h"| HelpOutput
    HelpOutput --> Subcommands
```

## Quick Start Guide

### Basic Enumeration Workflow

```mermaid
graph TB
    subgraph "Input Preparation"
        Domain["Target Domain<br/>example.com"]
        ScopeConfig["Scope Definition<br/>Domains, IPs, CIDRs, ASNs"]
    end

    subgraph "Asset Conversion"
        MakeAssets["makeAssets()"]
        ConvertScope["convertScopeToAssets()"]
    end

    subgraph "Asset Types Created"
        FQDNAsset["oamdns.FQDN<br/>Name: example.com"]
        IPAsset["oamnet.IPAddress<br/>Address, Type"]
        NetblockAsset["oamnet.Netblock<br/>CIDR, Type"]
        ASNAsset["oamnet.AutonomousSystem<br/>Number"]
    end

    subgraph "Execution"
        EnumCmd["amass enum -d example.com"]
        EngineStart["Engine starts background service"]
        PluginExec["Plugins execute discovery"]
    end

    subgraph "Output"
        StdoutResults["Discovered subdomains<br/>to stdout"]
        GraphDB["Graph database<br/>~/.config/amass/"]
    end

    Domain --> ScopeConfig
    ScopeConfig --> MakeAssets
    MakeAssets --> ConvertScope

    ConvertScope --> FQDNAsset
    ConvertScope --> IPAsset
    ConvertScope --> NetblockAsset
    ConvertScope --> ASNAsset

    FQDNAsset --> EnumCmd
    IPAsset --> EnumCmd
    NetblockAsset --> EnumCmd
    ASNAsset --> EnumCmd

    EnumCmd --> EngineStart
    EngineStart --> PluginExec
    PluginExec --> StdoutResults
    PluginExec --> GraphDB
```

### Running Your First Enumeration

```bash
# Enumerate a single domain
amass enum -d example.com

# Enumerate multiple domains
amass enum -d example.com,example.org

# Specify a custom configuration file
amass enum -config /path/to/config.yaml -d example.com

# Docker-based enumeration with persistent storage
mkdir -p ~/amass-output
docker run -v ~/amass-output:/data owaspamass/amass enum -d example.com
```

**Input to OAM asset type mapping:**

| Input Type | OAM Asset Type |
|-----------|----------------|
| Domain | `oamdns.FQDN{Name: "example.com"}` |
| IP Address | `oamnet.IPAddress{Address, Type}` |
| CIDR Range | `oamnet.Netblock{CIDR, Type}` |
| ASN | `oamnet.AutonomousSystem{Number}` |

## Next Steps

After completing the quick start, explore these resources:

| Topic | Description |
|-------|-------------|
| **Architecture** | Understanding system components |
| **CLI Commands** | Full command reference |
| **Configuration** | Advanced configuration options |
| **Data Sources** | Configuring API credentials |

### Common Next Actions

1. **Configure API Keys:** Add credentials to `datasources.yaml` for enhanced discovery.

2. **Run the Engine Service:** For continuous enumeration, run the engine as a background service:
   ```bash
   amass engine
   ```

3. **Analyze Results:** Use OAM tools to query and visualize collected data:
   ```bash
   oam_subs -d example.com
   oam_viz -d example.com -o graph.html
   ```

4. **Track Changes:** Monitor for new assets over time:
   ```bash
   oam_track -d example.com -since 2024-01-01
   ```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Command not found | Ensure `$GOPATH/bin` is in `$PATH` |
| Permission denied | Check file permissions on config directories |
| Network errors | Verify DNS resolver connectivity |
| Out of memory | Increase available RAM or use `-timeout` |

### Docker Health Checks

Use the included `ae_isready` binary for container orchestration:

```bash
docker exec amass-container ae_isready
```
