# Deployment Overview


This document describes the deployment strategies and distribution mechanisms for OWASP Amass. It covers the available installation methods, platform support, and the automated build and release pipeline that produces binaries, Docker images, and package manager distributions.

For detailed information about Docker-specific deployment, see [Docker Deployment](docker.md). For production configuration best practices, including API key management and resolver configuration, see [Configuration Best Practices](config-best-practices.md).

---

<div class="grid cards" markdown>

-   :material-docker:{ .lg .middle } **Docker Deployment**

    ---

    Run Amass in containers with multi-architecture support, volume management, and a multi-stage build.

    [:octicons-arrow-right-24: Docker Deployment](docker.md)

-   :material-cog:{ .lg .middle } **Configuration Best Practices**

    ---

    Production-tested guidance for resolvers, scope, API secrets, and performance tuning.

    [:octicons-arrow-right-24: Configuration Best Practices](config-best-practices.md)

</div>

## Deployment Overview

OWASP Amass provides three primary deployment methods:

1. **Direct Binary Installation** - Pre-compiled binaries for multiple operating systems and architectures, distributed via GitHub Releases
2. **Docker Containerization** - Multi-architecture container images hosted on Docker Hub
3. **Package Manager Installation** - Homebrew tap for macOS and Linux users

All deployment artifacts are automatically built and published through a CI/CD pipeline when version tags are pushed to the repository. The build process uses GoReleaser for binary compilation and Docker Buildx for multi-architecture container images.

---

## Release Pipeline Architecture

The following diagram illustrates the automated build and distribution pipeline that produces all deployment artifacts:

```mermaid
graph TD
    subgraph "Source Control"
        Git["Git Repository<br/>owasp-amass/amass"]
        Tag["Version Tag Push<br/>v*.*.*"]
    end
    
    subgraph "CI/CD - GitHub Actions"
        TestWorkflow["tests.yml<br/>3 OS Matrix<br/>Go 1.24.0"]
        LintWorkflow["lint.yml<br/>golangci-lint<br/>3 OS Matrix"]
        GoReleaserWorkflow["goreleaser.yml<br/>Binary Cross-compilation"]
        DockerWorkflow["docker.yml<br/>Multi-arch Build"]
    end
    
    subgraph "Build Process"
        GoReleaser["GoReleaser v2<br/>CGO_ENABLED=0"]
        Builds["Binary Builds<br/>11 Platform/Arch Combos"]
        Archives["Archives<br/>+ config.yaml<br/>+ datasources.yaml"]
        Checksums["checksums.txt<br/>SHA256"]
    end
    
    subgraph "Docker Build"
        BuildStage["golang:1.24.4-alpine<br/>go install ./..."]
        RuntimeStage["alpine:latest<br/>ca-certificates<br/>bash"]
        MultiArch["Multi-arch Images<br/>linux/amd64<br/>linux/arm64"]
    end
    
    subgraph "Distribution Channels"
        GitHubReleases["GitHub Releases<br/>Binary Downloads"]
        HomebrewTap["Homebrew Tap<br/>owasp-amass/homebrew-amass"]
        DockerHub["Docker Hub<br/>owaspamass/amass"]
    end
    
    Git --> Tag
    Tag --> TestWorkflow
    Tag --> LintWorkflow
    Tag --> GoReleaserWorkflow
    Tag --> DockerWorkflow
    
    GoReleaserWorkflow --> GoReleaser
    GoReleaser --> Builds
    Builds --> Archives
    Archives --> Checksums
    
    DockerWorkflow --> BuildStage
    BuildStage --> RuntimeStage
    RuntimeStage --> MultiArch
    
    Archives --> GitHubReleases
    Archives --> HomebrewTap
    Checksums --> GitHubReleases
    MultiArch --> DockerHub
```

**Release Pipeline Components**

The pipeline is triggered when a semantic version tag (matching pattern `v*.*.*`) is pushed to the repository. Four parallel workflows execute:

1. **Testing Workflow** - Executes the full test suite across three operating systems (Ubuntu, macOS, Windows) with Go 1.24.0
2. **Linting Workflow** - Runs `golangci-lint` on the same OS matrix to ensure code quality
3. **GoReleaser Workflow** - Cross-compiles binaries for all supported platforms and publishes to GitHub Releases and Homebrew
4. **Docker Workflow** - Builds multi-architecture container images using QEMU emulation and publishes to Docker Hub

---

## Binary Cross-Compilation Matrix

The GoReleaser configuration  defines a comprehensive cross-compilation matrix that produces binaries for the following combinations:

| Operating System | Architectures | Notes |
|-----------------|---------------|-------|
| **Linux** | amd64, 386, arm (v6/v7), arm64 | Full support for all architectures |
| **Darwin (macOS)** | amd64, arm64 | Excludes 386 and arm (deprecated/unsupported) |
| **Windows** | amd64 | Excludes 386, arm, arm64 (limited use case) |

All binaries are built with `CGO_ENABLED=0` , ensuring fully static binaries with no external C library dependencies. This configuration provides maximum portability and eliminates runtime dependency issues.

The build produces the main `amass` binary from  along with the OAM analysis tools (oam_enum, oam_subs, oam_assoc, oam_viz, oam_track, oam_i2y) and supporting utilities (amass_engine, ae_isready).

**Archive Contents**

Each release archive  includes:
- Compiled binary for the target platform
- `LICENSE` file
- `README.md` documentation
- `resources/config.yaml` - Default configuration template
- `resources/datasources.yaml` - Data source credentials template

---

## Docker Multi-Stage Build

The Docker deployment uses a multi-stage build process defined in  to minimize the final image size:

```mermaid
graph LR
    subgraph "Build Stage"
        BuildBase["golang:1.24.4-alpine"]
        GitInstall["apk add git"]
        GoInstall["go install ./..."]
        Binaries["Compiled Binaries<br/>/go/bin/"]
    end
    
    subgraph "Runtime Stage"
        RuntimeBase["alpine:latest"]
        Dependencies["bash<br/>ca-certificates<br/>upgrades"]
        BinaryCopy["COPY --from=build<br/>9 binaries"]
        UserSetup["Non-root User<br/>user:user"]
        Directories["/.config/amass<br/>/data"]
    end
    
    subgraph "Installed Binaries"
        AmassMain["/bin/amass"]
        OAMEnum["/bin/enum"]
        Engine["/bin/engine"]
        IsReady["/bin/ae_isready"]
        OAMSubs["/bin/subs"]
        OAMAssoc["/bin/assoc"]
        OAMViz["/bin/viz"]
        OAMTrack["/bin/track"]
        OAMi2y["/bin/i2y"]
    end
    
    BuildBase --> GitInstall
    GitInstall --> GoInstall
    GoInstall --> Binaries
    
    RuntimeBase --> Dependencies
    Dependencies --> BinaryCopy
    Binaries --> BinaryCopy
    BinaryCopy --> UserSetup
    UserSetup --> Directories
    
    BinaryCopy --> AmassMain
    BinaryCopy --> OAMEnum
    BinaryCopy --> Engine
    BinaryCopy --> IsReady
    BinaryCopy --> OAMSubs
    BinaryCopy --> OAMAssoc
    BinaryCopy --> OAMViz
    BinaryCopy --> OAMTrack
    BinaryCopy --> OAMi2y
```

**Build Stage** 
- Base: `golang:1.24.4-alpine`
- Installs Git for dependency fetching
- Compiles all binaries with `CGO_ENABLED=0`
- Outputs to `/go/bin/`

**Runtime Stage** 
- Base: `alpine:latest` (minimal footprint)
- Installs `bash` and `ca-certificates` for HTTPS/TLS operations
- Applies security updates with `apk upgrade`
- Copies only the compiled binaries (discards build dependencies)
- Creates non-root user `user` with UID/GID assignment 
- Sets up configuration directory `/.config/amass` 
- Creates data directory `/data` for output files 
- Sets `WORKDIR /data` as default working directory
- Configures `SIGINT` for graceful shutdown 
- Entrypoint: `/bin/amass` 

This architecture separates build-time dependencies from runtime, resulting in a significantly smaller image (alpine base ~5MB vs. golang ~300MB).

---

## Docker Multi-Architecture Support

The Docker workflow  builds images for multiple architectures using Docker Buildx with QEMU emulation:

```mermaid
graph TD
    subgraph "Build Configuration"
        QEMUSetup["QEMU Setup<br/>docker/setup-qemu-action"]
        BuildxSetup["Docker Buildx<br/>docker/setup-buildx-action"]
        Platforms["Platforms<br/>linux/amd64<br/>linux/arm64"]
    end
    
    subgraph "Metadata Generation"
        MetaAction["docker/metadata-action"]
        Tags["Semantic Version Tags<br/>v{{major}}<br/>v{{major}}.{{minor}}<br/>v{{major}}.{{minor}}.{{patch}}"]
        Labels["OCI Labels<br/>title, description, vendor"]
    end
    
    subgraph "Build and Push"
        BuildPush["docker/build-push-action"]
        Context["Context: .<br/>File: ./Dockerfile"]
        Push["Push to DockerHub<br/>owaspamass/amass"]
    end
    
    subgraph "Published Tags"
        Tag1["owaspamass/amass:v4"]
        Tag2["owaspamass/amass:v4.1"]
        Tag3["owaspamass/amass:v4.1.2"]
    end
    
    QEMUSetup --> Platforms
    BuildxSetup --> Platforms
    Platforms --> BuildPush
    
    MetaAction --> Tags
    MetaAction --> Labels
    Tags --> BuildPush
    Labels --> BuildPush
    
    Context --> BuildPush
    BuildPush --> Push
    
    Push --> Tag1
    Push --> Tag2
    Push --> Tag3
```

**Platform Support**

The workflow  configures `linux/amd64` and `linux/arm64` as target platforms. QEMU emulation  enables cross-platform builds on the x86_64 GitHub Actions runner.

**Semantic Versioning Tags**

For a release tagged `v4.1.2`, the metadata action  generates three image tags:
- `owaspamass/amass:v4` - Major version (latest v4.x.x)
- `owaspamass/amass:v4.1` - Minor version (latest v4.1.x)
- `owaspamass/amass:v4.1.2` - Patch version (exact release)

This tagging strategy allows users to pin to specific stability levels (exact version, minor updates, or major version line).

**OCI Image Labels**

The workflow applies Open Container Initiative metadata :
- `org.opencontainers.image.title=OWASP Amass`
- `org.opencontainers.image.description=In-depth attack surface mapping and asset discovery`
- `org.opencontainers.image.vendor=OWASP Foundation`

---

## Deployment Topology Options

The following diagram illustrates common deployment topologies for OWASP Amass:

```mermaid
graph TB
    subgraph "Local Development"
        LocalBinary["Binary Installation<br/>go install<br/>homebrew"]
        LocalConfig["~/.config/amass/<br/>config.yaml<br/>datasources.yaml"]
        LocalData["Local Filesystem<br/>Graph Database<br/>Session Cache"]
        LocalBinary --> LocalConfig
        LocalBinary --> LocalData
    end
    
    subgraph "Container Deployment"
        DockerContainer["Docker Container<br/>owaspamass/amass"]
        VolumeConfig["Volume Mount<br/>/path/to/config:/.config/amass"]
        VolumeData["Volume Mount<br/>/path/to/data:/data"]
        DockerContainer --> VolumeConfig
        DockerContainer --> VolumeData
    end
    
    subgraph "Client-Server Topology"
        EngineServer["amass_engine<br/>Background Service<br/>GraphQL API"]
        EnumClient1["oam_enum Client #1<br/>Domain Enumeration"]
        EnumClient2["oam_enum Client #2<br/>IP Enumeration"]
        SharedDB["Shared Graph DB<br/>asset-db/"]
        EngineServer --> SharedDB
        EnumClient1 --> EngineServer
        EnumClient2 --> EngineServer
    end
    
    subgraph "Analysis Workstation"
        AnalysisTools["OAM Tools<br/>oam_assoc<br/>oam_subs<br/>oam_track<br/>oam_viz"]
        ExistingDB["Existing Graph DB<br/>Read-only Access"]
        OutputFiles["Output Files<br/>JSON, DOT, GEXF"]
        AnalysisTools --> ExistingDB
        AnalysisTools --> OutputFiles
    end
```

**Local Development Topology**

Single-user installation with the binary installed via `go install` or Homebrew. Configuration files reside in `~/.config/amass/` on Unix-like systems. The graph database and session cache are stored locally on the filesystem.

**Container Deployment Topology**

Docker-based deployment with external volume mounts for configuration and data persistence. The container runs as non-root user `user`  with working directory `/data` . Configuration files are mounted at `/.config/amass` and output data is persisted to `/data`.

**Client-Server Topology**

Distributed deployment where `amass_engine` runs as a background service exposing a GraphQL API (see page [Session Management](#4.2)). Multiple `oam_enum` clients connect to the shared engine to submit enumeration jobs. All clients share a common graph database, enabling collaborative asset discovery.

**Analysis Workstation Topology**

Post-enumeration analysis workflow where OAM tools (`oam_assoc`, `oam_subs`, `oam_track`, `oam_viz`) operate on previously collected graph data. These tools provide read-only access to the database and produce various output formats (JSON, graph visualization files).

---

## Installation Methods

### Binary Installation

**Via Go Install**
```bash
go install -v github.com/owasp-amass/amass/v5/...@latest
```

This command installs all Amass binaries to `$GOPATH/bin/`:
- `amass` - Main CLI dispatcher
- `amass_engine` - Background enumeration engine
- `oam_enum` - Enumeration client
- `oam_assoc` - Asset association queries
- `oam_subs` - Subdomain summary
- `oam_track` - New asset tracking
- `oam_viz` - Graph visualization
- `oam_i2y` - Ingestion utilities
- `ae_isready` - Engine readiness probe

**Via GitHub Releases**

Download pre-compiled binaries from the GitHub Releases page. Each release includes:
1. Platform-specific archives (`.tar.gz` or `.zip`)
2. SHA256 checksums file 
3. Configuration templates (`config.yaml`, `datasources.yaml`)

Extract the archive and add the binary to your system `PATH`.

**Via Homebrew (macOS/Linux)**
```bash
brew tap owasp-amass/amass
brew install amass
```

The Homebrew tap  is automatically updated by the GoReleaser workflow when new versions are tagged. It provides automatic dependency management and system integration.

### Docker Installation

**Pull from Docker Hub**
```bash
docker pull owaspamass/amass:latest
```

**Run with Configuration and Data Volumes**
```bash
docker run -v /path/to/config:/.config/amass \
           -v /path/to/output:/data \
           owaspamass/amass enum -d example.com
```

The container expects:
- Configuration files mounted at `/.config/amass/` 
- Output directory mounted at `/data/` 
- Commands passed as arguments to the `amass` entrypoint 

**Access OAM Tools in Container**
```bash
docker run -v /path/to/data:/data \
           --entrypoint /bin/subs \
           owaspamass/amass -dir /data/asset-db
```

Override the entrypoint to access other binaries:
- `/bin/enum` - oam_enum
- `/bin/engine` - amass_engine
- `/bin/subs` - oam_subs
- `/bin/assoc` - oam_assoc
- `/bin/viz` - oam_viz
- `/bin/track` - oam_track
- `/bin/i2y` - oam_i2y
- `/bin/ae_isready` - Engine readiness probe

---

## Configuration File Management

Amass expects configuration files in the following locations:

| File | Default Location | Purpose |
|------|-----------------|---------|
| `config.yaml` | `~/.config/amass/config.yaml` | Main configuration (scope, resolvers, plugins) |
| `datasources.yaml` | `~/.config/amass/datasources.yaml` | API credentials for external services |

**Configuration Directory Structure**

In Docker deployments, the configuration directory is `/.config/amass/`  with ownership set to the non-root `user:user` .

In binary installations, the default is `$HOME/.config/amass/` on Unix-like systems.

**Environment Variable Override**

The `AMASS_CONFIG` environment variable can override the default configuration file location:
```bash
export AMASS_CONFIG=/custom/path/config.yaml
amass enum -d example.com
```

**Configuration Templates**

Release archives include template files :
- `resources/config.yaml` - Commented example configuration
- `resources/datasources.yaml` - API credential templates

For detailed configuration options and production best practices, see [Configuration Best Practices](config-best-practices.md).

---

## Data Persistence and Volume Management

### Graph Database Storage

Amass stores discovered assets in a graph database using the Open Asset Model (OAM) format. The database location is configurable via:

**CLI Arguments**
```bash
amass enum -dir /path/to/asset-db -d example.com
```

**Docker Volume Mount**
```bash
docker run -v /host/asset-db:/data/asset-db \
           owaspamass/amass enum -dir /data/asset-db -d example.com
```

The graph database persists all discovered assets, relationships, and metadata. Multiple enumeration sessions can target the same database to build a comprehensive asset inventory over time.

### Session Cache and Work Queue

During enumeration, Amass maintains session-specific caches and work queues (typically SQLite) for:
- Deduplication of discovered assets
- TTL-based DNS result caching
- Event queue management

These temporary data structures are stored within the session directory and can be safely deleted after enumeration completes.

### Docker Volume Strategy

Recommended volume mount strategy for containerized deployments:

```bash
docker run \
  -v /host/config:/root/.config/amass:ro \
  -v /host/data:/data \
  owaspamass/amass enum -d example.com
```

- Configuration volume mounted read-only (`:ro`)
- Data volume mounted read-write for database and output files
- Working directory set to `/data` by default 

---

## Production Deployment Considerations

### Non-Root Execution

The Docker image runs as non-root user `user`  for security. Binary installations should follow the same principle:

```bash
useradd -r -s /bin/false amass

chown -R amass:amass /opt/amass
chown -R amass:amass /var/lib/amass

sudo -u amass amass enum -d example.com
```

### Resource Limits

For containerized production deployments, apply resource constraints:

```bash
docker run --memory=4g \
           --cpus=2 \
           --ulimit nofile=65536:65536 \
           -v /host/config:/root/.config/amass:ro \
           -v /host/data:/data \
           owaspamass/amass enum -d example.com
```

The DNS resolution system can open many concurrent connections. Set appropriate file descriptor limits (`nofile`).

### Signal Handling

The Docker image is configured with `STOPSIGNAL SIGINT`  for graceful shutdown. The engine will:
1. Stop accepting new work
2. Complete in-flight operations
3. Flush caches to persistent storage
4. Release resources

Allow sufficient grace period (30-60 seconds) for clean termination.

### Multi-Architecture Deployment

The Docker images support both `linux/amd64` and `linux/arm64` . Docker automatically selects the appropriate architecture:

```bash
docker run --platform linux/arm64 owaspamass/amass enum -d example.com
```

For Kubernetes deployments, node selectors can target specific architectures:

```yaml
nodeSelector:
  kubernetes.io/arch: arm64
```

---

## Health Checks and Readiness Probes

The `ae_isready` utility  provides health checking for the `amass_engine` background service:

```bash
/bin/ae_isready

readinessProbe:
  exec:
    command:
    - /bin/ae_isready
  initialDelaySeconds: 10
  periodSeconds: 5
```

This probe queries the engine's GraphQL API to verify it is accepting connections and processing requests.

---

## Continuous Integration and Testing

### Test Matrix

The test workflow  executes on:
- **Operating Systems**: Ubuntu, macOS, Windows
- **Go Version**: 1.24.0
- **Test Modes**: 
  - Standard test execution: `go test -v ./...`
  - GC pressure testing: `GOGC=1 go test -v ./...`

### Coverage Reporting

Coverage is measured  and reported to Codecov:
```bash
CGO_ENABLED=0 go test -v -coverprofile=coverage.out ./...
```

Configuration in  sets:
- Coverage range: 20-60%
- Precision: 2 decimal places
- Round up for threshold calculation

### Linting Standards

The lint workflow  runs `golangci-lint` with:
- 60-minute timeout
- Only new issues flagged (no historical debt)
- Cross-platform validation (3 OS matrix)

---

## Distribution Checksums and Verification

All binary releases include SHA256 checksums . Verify downloads:

```bash
wget https://github.com/owasp-amass/amass/releases/download/v4.1.0/amass_linux_amd64.tar.gz
wget https://github.com/owasp-amass/amass/releases/download/v4.1.0/amass_checksums.txt

sha256sum -c amass_checksums.txt --ignore-missing
```

Expected output:
```
amass_linux_amd64.tar.gz: OK
```

This verifies the binary has not been tampered with during download.
