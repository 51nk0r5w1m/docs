# Development Guide

A comprehensive guide for developers who want to contribute to or extend OWASP Amass.

=== "Overview"

    This document provides a comprehensive guide for developers who want to contribute to or extend OWASP Amass. It covers the complete development lifecycle including environment setup, building from source, testing requirements, code quality standards, and the automated release pipeline. For specific guidance on plugin development patterns and architecture, see [Architecture](../architecture/index.md). For production deployment configurations, see [Deployment](../deployment/index.md).

    ## Development Prerequisites

    Amass requires the following tools and versions for development:

    | Component | Version | Purpose |
    |-----------|---------|---------|
    | Go | 1.24.0+ | Core language runtime |
    | golangci-lint | latest | Code quality enforcement |
    | Git | Any recent | Source control |
    | Docker | Any recent | Container testing (optional) |
    | make | Any recent | Build automation (optional) |

    The codebase enforces `CGO_ENABLED=0` across all build and test workflows to ensure static binary compilation without C dependencies. This simplifies cross-platform distribution and container deployment.

    ## Repository Structure and Workflow

    ### Fork and Branch Strategy

    The project follows a standard GitHub fork-and-pull-request workflow with specific branch conventions. The primary development branch is `develop`, not `main`. All pull requests must target `develop`.

    ```mermaid
    graph LR
        Upstream["upstream<br/>(owasp-amass/amass)"]
        Fork["origin<br/>(yourname/amass)"]
        Local["Local Clone<br/>$GOPATH/src/github.com/owasp-amass/amass"]
    
        Upstream -->|"git fetch upstream"| Local
        Local -->|"git push origin"| Fork
        Fork -->|"Pull Request to develop"| Upstream
    
        Local -->|"Working Directory"| DevBranch["feature-branch"]
        DevBranch -->|"git rebase upstream/develop"| Local
    ```

    **Fork Setup Process:**

    The codebase must remain in its canonical Go import path location: `$GOPATH/src/github.com/owasp-amass/amass`. This is required because Go resolves imports based on absolute paths. The recommended setup is:

    1. Clone the original repository to the canonical path
    2. Rename the `origin` remote to `upstream`
    3. Add your fork as the new `origin` remote
    4. Create feature branches locally
    5. Push feature branches to your fork
    6. Submit pull requests from your fork to `upstream/develop`

    ### Development Workflow Rules

    The project enforces strict workflow discipline:

    - **Target Branch:** All pull requests must target `develop`, never `main` 
    - **Rebase Strategy:** Before submitting pull requests, rebase on top of the latest `develop` 
    - **Force Push Policy:** No force pushes to `develop` except when reverting broken commits 
    - **Code Formatting:** All code must be formatted with `gofmt` before commit 
    - **Linting:** Run `golangci-lint run ./...` before submitting pull requests 

    ## Build System

    ### Local Development Build

    The project uses standard Go tooling for local builds. No custom build scripts are required for development:

    ```bash
    go build -o amass ./cmd/amass

    go build ./cmd/...

    go fmt ./...

    golangci-lint run ./...
    ```

    The build system enforces `CGO_ENABLED=0` to produce statically-linked binaries without C dependencies. This is configured in all CI/CD workflows but should be set manually for local release builds.

    ### Cross-Platform Compilation

    The GoReleaser configuration defines the complete matrix of supported platforms:

    ```mermaid
    graph TB
        Source["Source Code<br/>./cmd/amass"]
    
        subgraph "Target Platforms"
            Linux["linux<br/>amd64, 386, arm, arm64"]
            Darwin["darwin<br/>amd64, arm64"]
            Windows["windows<br/>amd64"]
        end
    
        subgraph "Build Outputs"
            Binaries["Platform Binaries"]
            Archives["Release Archives<br/>+ config.yaml<br/>+ datasources.yaml<br/>+ LICENSE<br/>+ README.md"]
            Checksums["Checksums.txt"]
        end
    
        Source --> Linux
        Source --> Darwin
        Source --> Windows
    
        Linux --> Binaries
        Darwin --> Binaries
        Windows --> Binaries
    
        Binaries --> Archives
        Archives --> Checksums
    ```

    **Supported Platform Matrix:**

    | OS | Architectures | Notes |
    |---|---|---|
    | Linux | amd64, 386, arm (v6, v7), arm64 | Full support |
    | Darwin (macOS) | amd64, arm64 | No 386 or arm  |
    | Windows | amd64 | No 386, arm, or arm64  |

    The GoReleaser configuration explicitly ignores unsupported platform combinations to prevent build failures.

    ### Release Archive Structure

    Each release archive is structured as follows:

    ```
    amass_<os>_<arch>/
    ├── amass                    # Main binary
    ├── LICENSE                  # Apache 2.0 license
    ├── README.md               # Documentation
    ├── resources/
    │   ├── config.yaml         # Default configuration
    │   └── datasources.yaml    # Data source configuration
    ```

    The archive naming follows the pattern: `amass_<os>_<arch>v<arm_version>.tar.gz`

    ## Testing Framework

    ### Test Execution Matrix

    The continuous integration system runs tests across a comprehensive matrix:

    ```mermaid
    graph TB
        PushEvent["Git Push/PR Event"]
    
        subgraph "Test Matrix"
            Ubuntu["ubuntu-latest<br/>Go 1.24.0"]
            MacOS["macos-latest<br/>Go 1.24.0"]
            Windows["windows-latest<br/>Go 1.24.0"]
        end
    
        subgraph "Test Phases"
            SimpleTest["Simple Test<br/>go test -v ./..."]
            GCTest["GC Pressure Test<br/>GOGC=1 go test -v ./..."]
        end
    
        subgraph "Coverage Analysis"
            CoverageRun["Coverage Measurement<br/>go test -coverprofile=coverage.out"]
            CodeCov["Codecov Reporting"]
        end
    
        PushEvent --> Ubuntu
        PushEvent --> MacOS
        PushEvent --> Windows
    
        Ubuntu --> SimpleTest
        MacOS --> SimpleTest
        Windows --> SimpleTest
    
        Ubuntu --> GCTest
        MacOS --> GCTest
        Windows --> GCTest
    
        Ubuntu --> CoverageRun
        CoverageRun --> CodeCov
    ```

    **Test Phases:**

    1. **Simple Test:** Standard test execution with default garbage collection settings 
    2. **GC Pressure Test:** Tests run with aggressive garbage collection (`GOGC=1`) to catch memory management issues 
    3. **Coverage Analysis:** Measures code coverage and reports to Codecov (Ubuntu only) 

    ### Coverage Requirements

    The Codecov configuration defines coverage thresholds and reporting behavior:

    ```yaml
    coverage:
      range: 20..60      # Coverage range (not strict enforcement)
      round: up          # Round up coverage percentages
      precision: 2       # Two decimal places
    ```

    Key coverage settings:

    - **Path Fixes:** GitHub path remapping to handle module versioning 
    - **Ignored Paths:** The `resources/` directory is excluded from coverage 
    - **Comment Behavior:** Coverage comments appear only on new PRs with changes 
    - **Target Branch:** Comments only appear on PRs targeting `develop` 

    ## Code Quality Standards

    ### Linting Configuration

    The project uses `golangci-lint` with a 60-minute timeout to accommodate comprehensive analysis:

    ```mermaid
    graph LR
        Source["Source Code"]
        Lint["golangci-lint<br/>--timeout=60m<br/>--only-new-issues"]
    
        subgraph "Quality Checks"
            ArgCount["Argument Count<br/>threshold: 5"]
            ComplexLogic["Complex Logic<br/>threshold: 4"]
            FileLines["File Lines<br/>threshold: 500"]
            MethodComplexity["Method Complexity<br/>threshold: 5"]
            MethodCount["Method Count<br/>threshold: 20"]
            MethodLines["Method Lines<br/>threshold: 100"]
            NestedControl["Nested Control Flow<br/>threshold: 4"]
            ReturnStatements["Return Statements<br/>threshold: 10"]
            SimilarCode["Similar Code<br/>threshold: 10"]
            IdenticalCode["Identical Code<br/>threshold: 10"]
        end
    
        Source --> Lint
        Lint --> ArgCount
        Lint --> ComplexLogic
        Lint --> FileLines
        Lint --> MethodComplexity
        Lint --> MethodCount
        Lint --> MethodLines
        Lint --> NestedControl
        Lint --> ReturnStatements
        Lint --> SimilarCode
        Lint --> IdenticalCode
    ```

    **Code Quality Thresholds:**

    | Check | Threshold | Purpose |
    |-------|-----------|---------|
    | argument-count | 5 | Limit function parameter complexity |
    | complex-logic | 4 | Prevent overly complex conditional logic |
    | file-lines | 500 | Keep files manageable |
    | method-complexity | 5 | Limit cyclomatic complexity |
    | method-count | 20 | Prevent god objects |
    | method-lines | 100 | Keep functions readable |
    | nested-control-flow | 4 | Limit nesting depth |
    | return-statements | 10 | Prevent complex exit logic |
    | similar-code | 10 | Detect code duplication |
    | identical-code | 10 | Detect exact code duplication |

    The linter runs with `--only-new-issues` to focus on changes in pull requests rather than legacy code debt.

    ### Code Formatting

    The project enforces Line Feed (LF) line endings for all Go source files via `.gitattributes`:

    ```
    *.go text eol=lf
    ```

    This ensures consistent line endings across Windows, macOS, and Linux development environments.

    ## CI/CD Pipeline

    ### Workflow Trigger Matrix

    The project uses four GitHub Actions workflows with different trigger conditions:

    ```mermaid
    graph TB
        subgraph "Triggers"
            Push["Git Push<br/>branches: main, develop"]
            PR["Pull Request<br/>branch: develop"]
            Tag["Git Tag<br/>pattern: v*.*.*"]
        end
    
        subgraph "Workflows"
            TestWF["tests workflow<br/>(.github/workflows/go.yml)"]
            LintWF["lint workflow<br/>(.github/workflows/lint.yml)"]
            ReleaseWF["goreleaser workflow<br/>(.github/workflows/goreleaser.yml)"]
            DockerWF["docker workflow<br/>(.github/workflows/docker.yml)"]
        end
    
        Push --> TestWF
        PR --> TestWF
        Push --> LintWF
        PR --> LintWF
    
        Tag --> ReleaseWF
        Tag --> DockerWF
    ```

    **Workflow Purposes:**

    | Workflow | Trigger | Purpose |
    |----------|---------|---------|
    | tests | Push to main/develop, PRs to develop | Run test suite across platforms |
    | lint | Any push or PR | Enforce code quality standards |
    | goreleaser | Tags matching v*.*.* | Build and publish release binaries |
    | docker | Tags matching v*.*.* | Build and publish Docker images |

    ### Release Automation Pipeline

    The release process is fully automated when a semantic version tag is pushed:

    ```mermaid
    graph TB
        Tag["Git Tag: v1.2.3"]
    
        subgraph "Parallel Builds"
            GoReleaser["GoReleaser Build<br/>11 Platform-Arch Combos"]
            DockerBuild["Docker Build<br/>Multi-arch: amd64, arm64"]
        end
    
        subgraph "GoReleaser Outputs"
            Binaries["Platform Binaries"]
            Archives["Release Archives"]
            Checksums["SHA256 Checksums"]
            Changelog["Changelog Generation"]
        end
    
        subgraph "Distribution"
            GitHubRelease["GitHub Release<br/>owasp-amass/amass"]
            HomebrewTap["Homebrew Cask<br/>owasp-amass/homebrew-amass"]
            DockerHub["Docker Hub<br/>owaspamass/amass"]
        end
    
        Tag --> GoReleaser
        Tag --> DockerBuild
    
        GoReleaser --> Binaries
        Binaries --> Archives
        Archives --> Checksums
        GoReleaser --> Changelog
    
        Archives --> GitHubRelease
        Archives --> HomebrewTap
        DockerBuild --> DockerHub
    ```

    **GoReleaser Process:**

    1. **Dependency Management:** Runs `go mod tidy` before build 
    2. **Binary Compilation:** Cross-compiles for all platform combinations
    3. **Archive Creation:** Bundles binaries with configuration files and documentation
    4. **Checksum Generation:** Creates SHA256 checksums for all archives 
    5. **Changelog Generation:** Auto-generates changelog from commits, excluding merge commits 
    6. **GitHub Release:** Publishes release with all archives and checksums 
    7. **Homebrew Update:** Updates the Homebrew tap repository automatically 

    ### Docker Multi-Architecture Build

    The Docker workflow produces images for two architectures using QEMU emulation and Docker Buildx:

    ```mermaid
    graph TB
        Tag["Git Tag: v1.2.3"]
    
        subgraph "Build Setup"
            QEMU["QEMU Setup<br/>linux/amd64, linux/arm64"]
            Buildx["Docker Buildx<br/>Multi-platform Build"]
        end
    
        subgraph "Image Tagging"
            MetaAction["docker/metadata-action<br/>Semantic Version Tags"]
            Tags["Generated Tags:<br/>v1<br/>v1.2<br/>v1.2.3"]
        end
    
        subgraph "Build and Push"
            MultiArchBuild["docker/build-push-action<br/>Platforms: linux/amd64, linux/arm64"]
            DockerHub["Docker Hub<br/>owaspamass/amass:v1<br/>owaspamass/amass:v1.2<br/>owaspamass/amass:v1.2.3"]
        end
    
        Tag --> QEMU
        Tag --> MetaAction
        QEMU --> Buildx
        MetaAction --> Tags
        Buildx --> MultiArchBuild
        Tags --> MultiArchBuild
        MultiArchBuild --> DockerHub
    ```

    **Docker Build Process:**

    1. **Checkout:** Clones the repository at the tagged commit 
    2. **Authentication:** Logs into Docker Hub using secrets 
    3. **Metadata Generation:** Creates semantic version tags (v1, v1.2, v1.2.3) 
    4. **QEMU Setup:** Configures emulation for cross-architecture builds 
    5. **Buildx Configuration:** Sets up Docker Buildx with host networking 
    6. **Multi-Arch Build:** Builds and pushes images for both architectures 

    **Image Labels:**

    The Docker images include OCI standard labels:

    - `org.opencontainers.image.title`: "OWASP Amass"
    - `org.opencontainers.image.description`: "In-depth attack surface mapping and asset discovery"
    - `org.opencontainers.image.vendor`: "OWASP Foundation"

    ## Contributing Process

    ### Contribution Workflow

    ```mermaid
    sequenceDiagram
        participant Dev as Developer
        participant Fork as Fork Repository
        participant Discord as Discord Server
        participant PR as Pull Request
        participant CI as CI/CD Pipeline
        participant Upstream as Upstream Repository
    
        Dev->>Discord: Join Discord for discussion
        Dev->>Fork: Fork repository
        Dev->>Dev: Clone to canonical path
        Dev->>Dev: Create feature branch
        Dev->>Dev: Make changes
        Dev->>Dev: Run gofmt
        Dev->>Dev: Run golangci-lint
        Dev->>Dev: Run tests locally
        Dev->>Fork: Push feature branch
        Fork->>PR: Create pull request to develop
        PR->>CI: Trigger tests & lint workflows
        CI-->>PR: Report results
        PR->>Upstream: Merge to develop (if approved)
    ```

    **Required Steps Before Submitting:**

    1. **Join Discord:** Coordinate with the community at https://discord.gg/ANTyEDUXt5 
    2. **Review Documentation:** Check existing documentation at https://owasp-amass.github.io/docs/ 
    3. **Check Open Issues:** Review issues at https://github.com/owasp-amass/amass/issues 
    4. **Format Code:** Run `gofmt` on all modified files 
    5. **Lint Code:** Run `golangci-lint run ./...` to catch errors 
    6. **Rebase on Develop:** Ensure your branch is up to date with `develop` 

    ### License and Copyright

    All contributions are licensed under the Apache License 2.0. The copyright is held by Jeff Foley (2017-2025) as stated in the LICENSE file header.

    **Key License Terms:**

    - Permissive open source license
    - Allows commercial use, modification, distribution, and private use
    - Requires preservation of copyright and license notices
    - Provides patent grant from contributors
    - No warranty or liability

    ## Development Environment Setup

    ### Recommended IDE Configuration

    The repository includes a `.gitignore` that explicitly excludes JetBrains IDE configuration files (`.idea/`), indicating that some core contributors use JetBrains IDEs (GoLand/IntelliJ IDEA). However, any IDE or text editor that supports Go can be used.

    **Ignored Development Artifacts:**

    - Compiled binaries: `*.exe`, `*.dll`, `*.so`, `*.dylib`
    - Test binaries: `*.test`
    - Coverage outputs: `*.out`
    - Amass output files: `*.json`, `*.log`, `*.html`
    - IDE configurations: `.idea/`

    ### Docker Development Environment

    For developers who prefer containerized development, the `.dockerignore` file excludes unnecessary files from Docker builds:

    ```
    Dockerfile          # Build instructions (not needed in image)
    *.md                # Documentation
    .idea               # IDE configuration
    *.json, *.log       # Output files
    *.test, *.out       # Test artifacts
    *.exe, *.dll, *.so  # Compiled artifacts
    Archives            # *.zip, *.tar, *.gz, etc.
    ```

    This keeps Docker images minimal by excluding development-time artifacts.

    ## Git Author Attribution

    The project uses a `.mailmap` file to normalize author attribution across different email addresses:

    ```
    Jeff Foley <caffix@users.noreply.github.com> Jeff Foley <caffix@users.noreply.github.com>
    Jeff Foley <caffix@users.noreply.github.com> caffix <caffix@users.noreply.github.com>
    ```

    This ensures consistent authorship statistics in `git log` and `git shortlog` outputs regardless of which email address was used for commits.

=== "Building from Source"

    This document provides instructions for building OWASP Amass from source code. It covers prerequisites, repository setup, build commands, and cross-compilation options. For installing pre-built binaries, see [Installation](../installation.md). For information about the automated release pipeline, see [Release Process](#release-process). For testing and code quality tools, see [Testing and Code Quality](#testing-and-code-quality).

    ## Prerequisites

    Building Amass requires a specific Go version and environment configuration.

    ### Required Software

    | Requirement | Version | Purpose |
    |------------|---------|---------|
    | Go | 1.24+ | Compilation toolchain |
    | Git | Any recent | Source code management |
    | Make (optional) | Any recent | Build automation |

    The minimum Go version is defined in , which specifies `go 1.24.4`. The project uses pure Go with no C dependencies, as indicated by `CGO_ENABLED=0` in all build workflows , , and .

    ### Development Tools (Optional)

    | Tool | Purpose | Usage |
    |------|---------|-------|
    | `gofmt` | Code formatting | `go fmt ./...` |
    | `golangci-lint` | Static analysis | `golangci-lint run ./...` |

    These tools are recommended for contributors. The `golangci-lint` tool runs with a 60-minute timeout in CI .

    ## Repository Structure

    ```mermaid
    graph TB
        subgraph "Repository Root"
            GoMod["go.mod<br/>Module Definition"]
            GoSum["go.sum<br/>Dependency Checksums"]
            Goreleaser[".goreleaser.yaml<br/>Release Configuration"]
        end
    
        subgraph "Main Binary - cmd/amass"
            MainCmd["main.go<br/>CLI Entry Point"]
        end
    
        subgraph "OAM Tools - cmd/*"
            AssocCmd["cmd/oam_assoc"]
            SubsCmd["cmd/oam_subs"]
            TrackCmd["cmd/oam_track"]
            VizCmd["cmd/oam_viz"]
            EnumCmd["cmd/oam_enum"]
            I2YCmd["cmd/oam_i2y"]
        end
    
        subgraph "Core Packages"
            Engine["engine/<br/>Core Engine"]
            Plugins["engine/plugins/<br/>Discovery Plugins"]
            Support["engine/plugins/support/<br/>Shared Utilities"]
        end
    
        subgraph "Build Artifacts"
            Binary["amass<br/>(or amass.exe)"]
            OAMBinaries["oam_* binaries"]
        end
    
        GoMod --> MainCmd
        GoMod --> AssocCmd
        GoMod --> SubsCmd
        GoMod --> TrackCmd
        GoMod --> VizCmd
        GoMod --> EnumCmd
        GoMod --> I2YCmd
    
        MainCmd --> Engine
        Engine --> Plugins
        Plugins --> Support
    
        MainCmd --> Binary
        AssocCmd --> OAMBinaries
        SubsCmd --> OAMBinaries
        TrackCmd --> OAMBinaries
        VizCmd --> OAMBinaries
        EnumCmd --> OAMBinaries
        I2YCmd --> OAMBinaries
    ```

    ## Cloning the Repository

    ### Standard Clone

    ```bash
    git clone https://github.com/owasp-amass/amass.git
    cd amass
    ```

    ### Fork-based Development

    For contributors, Go's import path requirements necessitate a specific workflow. The code must reside at `$GOPATH/src/github.com/owasp-amass/amass`, not at the fork location .

    ```bash
    git clone https://github.com/owasp-amass/amass.git
    cd amass

    git remote rename origin upstream

    git remote add origin git@github.com:yourusername/amass.git

    git checkout -b feature-branch develop
    ```

    To pull updates from upstream:

    ```bash
    git fetch upstream
    git rebase upstream/develop
    ```

    ## Building the Main Binary

    ### Basic Build

    The main Amass binary is built from :

    ```bash
    go build -o amass ./cmd/amass

    go install ./cmd/amass
    ```

    ### Production Build

    For a production-grade build matching the official releases, use the same settings as the CI pipeline:

    ```bash
    CGO_ENABLED=0 go build \
      -ldflags="-s -w" \
      -o amass \
      ./cmd/amass
    ```

    | Flag | Purpose |
    |------|---------|
    | `CGO_ENABLED=0` | Disables C dependencies for static linking |
    | `-ldflags="-s -w"` | Strips debugging information to reduce binary size |

    ### Build Output

    The build produces a single executable:
    - **Linux/macOS:** `amass`
    - **Windows:** `amass.exe`

    ## Building OAM Tools

    The Open Asset Model (OAM) analysis tools are separate binaries:

    ```bash
    go build -o oam_assoc ./cmd/oam_assoc
    go build -o oam_subs ./cmd/oam_subs
    go build -o oam_track ./cmd/oam_track
    go build -o oam_viz ./cmd/oam_viz
    go build -o oam_enum ./cmd/oam_enum
    go build -o oam_i2y ./cmd/oam_i2y
    ```

    Or build all at once:

    ```bash
    for tool in assoc subs track viz enum i2y; do
      CGO_ENABLED=0 go build -o "oam_${tool}" "./cmd/oam_${tool}"
    done
    ```

    ## Dependency Management

    ### Installing Dependencies

    Dependencies are managed via Go modules. To download all dependencies:

    ```bash
    go mod download
    ```

    To verify and clean up dependencies:

    ```bash
    go mod tidy
    go mod verify
    ```

    The `go mod tidy` command is automatically run before releases .

    ### Key Dependencies

    The project has 42 direct dependencies , including:

    | Dependency | Purpose |
    |------------|---------|
    | `github.com/miekg/dns` | DNS protocol handling |
    | `github.com/owasp-amass/asset-db` | Graph database for asset storage |
    | `github.com/owasp-amass/open-asset-model` | OAM data model |
    | `github.com/owasp-amass/resolve` | DNS resolution infrastructure |
    | `github.com/glebarez/sqlite` | Embedded SQLite for queues |
    | `github.com/99designs/gqlgen` | GraphQL API generation |
    | `gorm.io/gorm` | ORM for database operations |

    ## Cross-Compilation

    ### Supported Platforms

    Amass supports cross-compilation for multiple operating systems and architectures, as defined in :

    ```mermaid
    graph LR
        subgraph "Operating Systems"
            Linux["linux"]
            Darwin["darwin<br/>(macOS)"]
            Windows["windows"]
        end
    
        subgraph "Architectures"
            AMD64["amd64<br/>(x86-64)"]
            I386["386<br/>(x86-32)"]
            ARM["arm<br/>(ARMv6, ARMv7)"]
            ARM64["arm64<br/>(ARMv8)"]
        end
    
        subgraph "Valid Combinations"
            L_AMD64["linux/amd64"]
            L_386["linux/386"]
            L_ARM["linux/arm"]
            L_ARM64["linux/arm64"]
            D_AMD64["darwin/amd64"]
            D_ARM64["darwin/arm64"]
            W_AMD64["windows/amd64"]
        end
    
        Linux --> L_AMD64
        Linux --> L_386
        Linux --> L_ARM
        Linux --> L_ARM64
    
        Darwin --> D_AMD64
        Darwin --> D_ARM64
    
        Windows --> W_AMD64
    
        AMD64 --> L_AMD64
        AMD64 --> D_AMD64
        AMD64 --> W_AMD64
    
        I386 --> L_386
    
        ARM --> L_ARM
    
        ARM64 --> L_ARM64
        ARM64 --> D_ARM64
    ```

    **Excluded Combinations** :
    - `darwin/386` - macOS no longer supports 32-bit
    - `darwin/arm` - macOS doesn't run on 32-bit ARM
    - `windows/386` - Not included in official builds
    - `windows/arm` - Not included in official builds
    - `windows/arm64` - Not included in official builds

    ### Cross-Compilation Commands

    To build for a specific platform:

    ```bash
    GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o amass-linux-amd64 ./cmd/amass

    GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 go build -o amass-darwin-arm64 ./cmd/amass

    GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o amass-windows-amd64.exe ./cmd/amass

    GOOS=linux GOARCH=arm GOARM=7 CGO_ENABLED=0 go build -o amass-linux-armv7 ./cmd/amass
    ```

    For ARM builds, the `GOARM` variable specifies the ARM version :
    - `GOARM=6` - ARMv6 (Raspberry Pi 1, Zero)
    - `GOARM=7` - ARMv7 (Raspberry Pi 2, 3, 4 in 32-bit mode)

    ## Development Workflow

    ### Build-Test-Lint Cycle

    ```mermaid
    graph TD
        Edit["Edit Source Code"] --> Format["go fmt ./..."]
        Format --> Build["go build ./..."]
        Build --> Test["go test -v ./..."]
        Test --> Lint["golangci-lint run ./..."]
        Lint --> Decision{All Pass?}
        Decision -->|No| Edit
        Decision -->|Yes| Commit["git commit"]
        Commit --> Push["git push"]
    ```

    ### Running Tests

    The test suite runs on three operating systems in CI :

    ```bash
    go test -v ./...

    GOGC=1 go test -v ./...

    go test -v -coverprofile=coverage.out ./...

    go tool cover -html=coverage.out
    ```

    The coverage report is submitted to Codecov  with a target range of 20-60% .

    ### Code Quality Checks

    ```bash
    go fmt ./...

    golangci-lint run ./...

    golangci-lint run --timeout=60m ./...
    ```

    The linter configuration runs across three operating systems with a 60-minute timeout .

    ## Build Artifacts and Packaging

    ### Archive Structure

    When using GoReleaser, archives include additional files :

    ```
    amass_linux_amd64/
    ├── amass                      # Main binary
    ├── LICENSE                    # Apache 2.0 license
    ├── README.md                  # Project documentation
    ├── resources/
    │   ├── config.yaml           # Example configuration
    │   └── datasources.yaml      # Example data source config
    ```

    ### Archive Naming

    Archives follow this pattern :
    ```
    amass_{{ .Os }}_{{ .Arch }}{{ if .Arm }}v{{ .Arm }}{{ end }}
    ```

    Examples:
    - `amass_linux_amd64.tar.gz`
    - `amass_darwin_arm64.tar.gz`
    - `amass_linux_armv7.tar.gz`

    ## Troubleshooting

    ### Common Build Issues

    | Issue | Cause | Solution |
    |-------|-------|----------|
    | `go: module not found` | Missing dependencies | Run `go mod download` |
    | `package X is not in GOROOT` | Wrong Go version | Upgrade to Go 1.24+ |
    | `cgo: not found` | CGO enabled by default | Set `CGO_ENABLED=0` |
    | Import path issues with fork | Code not at expected path | Follow fork workflow in [CONTRIBUTING.md](#contributing) |

    ### Verifying Build

    After building, verify the binary:

    ```bash
    ./amass version

    ldd amass  # Should show "not a dynamic executable" or minimal libraries

    file amass
    ```

=== "Testing & Code Quality"

    This page documents the testing infrastructure, code quality standards, and continuous integration workflows used in the OWASP Amass project. It covers the automated test suite, linting configuration, coverage requirements, and the GitHub Actions CI/CD pipelines that enforce these standards.

    For information about building Amass from source, see [Building from Source](#building-from-source). For details on the release process and deployment, see [Release Process](#release-process).

    ## Test Suite Structure

    The Amass project maintains a comprehensive test suite executed through standard Go testing tools. Tests are organized alongside the source code they validate, following Go conventions.

    ### Test Execution

    The test suite runs in two configurations to ensure robustness under different conditions:

    | Test Configuration | Environment | Purpose |
    |-------------------|-------------|---------|
    | Simple Test | Default GOGC | Standard validation of functionality |
    | GC Pressure Test | `GOGC=1` | Validates behavior under high garbage collection pressure |

    Both configurations execute the full test suite using `go test -v ./...`  and .

    ### Multi-Platform Testing

    Tests execute on three operating systems to ensure cross-platform compatibility:

    - **Ubuntu Latest** (Linux)
    - **macOS Latest** (Darwin)
    - **Windows Latest**

    All platforms use Go 1.24.0 with `CGO_ENABLED=0` , matching the production build configuration.

    ### Test Workflow Triggers

    ```mermaid
    graph LR
        subgraph "Trigger Events"
            Push_Main["Push to main"]
            Push_Develop["Push to develop"]
            PR_Develop["Pull Request to develop"]
        end
    
        subgraph "Test Jobs"
            Test_Matrix["Test Matrix Job<br/>(3 OS × Go 1.24.0)"]
            Coverage["Coverage Job<br/>(Ubuntu only)"]
        end
    
        subgraph "Test Execution"
            Simple["go test -v ./..."]
            GC_Pressure["go test -v ./...<br/>GOGC=1"]
            Coverage_Run["go test -v -coverprofile=coverage.out ./..."]
        end
    
        subgraph "Reporting"
            Codecov["Codecov Report"]
        end
    
        Push_Main --> Test_Matrix
        Push_Develop --> Test_Matrix
        PR_Develop --> Test_Matrix
        PR_Develop --> Coverage
    
        Test_Matrix --> Simple
        Test_Matrix --> GC_Pressure
    
        Coverage --> Coverage_Run
        Coverage_Run --> Codecov
    ```

    **Test Workflow Architecture**: Tests trigger on pushes to main or develop branches and pull requests targeting develop. The test matrix runs both simple and GC pressure tests across all platforms, while coverage measurement runs only on Ubuntu.

    ## Code Coverage Requirements

    ### Coverage Configuration

    Coverage tracking uses Codecov with custom path fixes to correctly map module paths:

    ```yaml
    fixes:
      - "github.com/owasp-amass/amass/v5/::github.com/owasp-amass/amass/"
    ```

    ### Coverage Thresholds

    | Metric | Value | Behavior |
    |--------|-------|----------|
    | Range | 20-60% | Coverage is considered acceptable within this range |
    | Rounding | Up | Coverage percentages round upward |
    | Precision | 2 decimal places | Report precision level |

    ### Coverage Exclusions

    The `./resources/**/*` directory is excluded from coverage analysis  as it contains configuration files and data sources rather than executable code.

    ### Coverage Reporting

    Coverage reports post as comments on pull requests with the layout `"reach, diff, files"` . Comments only appear on new pull requests that have changes and require both base and head commit coverage data .

    Coverage measurement executes using:
    ```bash
    CGO_ENABLED=0 go test -v -coverprofile=coverage.out ./...
    ```

    ## Code Quality Standards

    ### Linting Infrastructure

    The project enforces code quality through `golangci-lint`, executed via GitHub Actions on every push and pull request.

    ```mermaid
    graph TB
        subgraph "Lint Workflow Triggers"
            Any_Push["Push Event"]
            Any_PR["Pull Request Event"]
        end
    
        subgraph "Lint Matrix Execution"
            Lint_Ubuntu["golangci-lint<br/>Ubuntu Latest<br/>Go 1.24.0"]
            Lint_MacOS["golangci-lint<br/>macOS Latest<br/>Go 1.24.0"]
            Lint_Windows["golangci-lint<br/>Windows Latest<br/>Go 1.24.0"]
        end
    
        subgraph "Lint Configuration"
            Timeout["--timeout=60m"]
            Only_New["--only-new-issues: true"]
            Latest_Version["version: latest"]
        end
    
        Any_Push --> Lint_Ubuntu
        Any_Push --> Lint_MacOS
        Any_Push --> Lint_Windows
    
        Any_PR --> Lint_Ubuntu
        Any_PR --> Lint_MacOS
        Any_PR --> Lint_Windows
    
        Lint_Ubuntu --> Timeout
        Lint_Ubuntu --> Only_New
        Lint_Ubuntu --> Latest_Version
    
        Lint_MacOS --> Timeout
        Lint_MacOS --> Only_New
        Lint_MacOS --> Latest_Version
    
        Lint_Windows --> Timeout
        Lint_Windows --> Only_New
        Lint_Windows --> Latest_Version
    ```

    **Linting Pipeline**: The lint workflow executes on all platforms for every code change, using extended timeout to accommodate the large codebase and reporting only new issues to focus developer attention.

    The linter runs with a 60-minute timeout  and focuses on new issues with `only-new-issues: true` , preventing noise from pre-existing code that may not meet current standards.

    ### Code Climate Complexity Metrics

    Code Climate enforces maintainability standards through complexity thresholds configured in `.codeclimate.yml`:

    | Metric | Threshold | Description |
    |--------|-----------|-------------|
    | Argument Count | 5 | Maximum function parameters |
    | Complex Logic | 4 | Cognitive complexity limit |
    | File Lines | 500 | Maximum lines per file |
    | Method Complexity | 5 | Cyclomatic complexity per method |
    | Method Count | 20 | Maximum methods per file |
    | Method Lines | 100 | Maximum lines per method |
    | Nested Control Flow | 4 | Maximum nesting depth |
    | Return Statements | 10 | Maximum returns per method |
    | Similar Code | 10 | Duplicate code threshold |
    | Identical Code | 10 | Exact duplicate threshold |

    The `resources/` directory is excluded from Code Climate analysis .

    ### Code Formatting Standards

    The project uses `gofmt` for consistent formatting. Contributors must format code before each commit:

    ```bash
    go fmt ./...
    ```

    The Go standard formatting tool ensures consistent style across the entire codebase. Most editors can run `gofmt` automatically on file save.

    Git attributes enforce LF line endings for Go files across all platforms:

    ```
    *.go text eol=lf
    ```

    ## GitHub Actions CI/CD Workflows

    ### Workflow Architecture

    ```mermaid
    graph TB
        subgraph "Source Events"
            Git_Push["Git Push<br/>(main, develop)"]
            Pull_Request["Pull Request<br/>(to develop)"]
            Tag_Push["Tag Push<br/>(v*.*.*)"]
        end
    
        subgraph "Quality Workflows"
            Tests_Workflow[".github/workflows/go.yml<br/>tests workflow"]
            Lint_Workflow[".github/workflows/lint.yml<br/>lint workflow"]
        end
    
        subgraph "Release Workflows"
            GoReleaser_Workflow[".github/workflows/goreleaser.yml<br/>goreleaser workflow"]
            Docker_Workflow[".github/workflows/docker.yml<br/>docker workflow"]
        end
    
        subgraph "Test Jobs"
            Test_Job["Test Job<br/>3 OS matrix"]
            Coverage_Job["Coverage Job<br/>Ubuntu + Codecov"]
        end
    
        subgraph "Lint Jobs"
            Lint_Job["Lint Job<br/>3 OS matrix<br/>golangci-lint"]
        end
    
        Git_Push --> Tests_Workflow
        Pull_Request --> Tests_Workflow
        Git_Push --> Lint_Workflow
        Pull_Request --> Lint_Workflow
    
        Tag_Push --> GoReleaser_Workflow
        Tag_Push --> Docker_Workflow
    
        Tests_Workflow --> Test_Job
        Tests_Workflow --> Coverage_Job
    
        Lint_Workflow --> Lint_Job
    ```

    **CI/CD Workflow Structure**: Quality checks (tests and linting) run on every code change, while release workflows (goreleaser and docker) trigger only on version tags.

    ### Tests Workflow Configuration

    The `tests` workflow  includes two jobs:

    **Test Job Configuration:**
    ```yaml
    strategy:
      matrix:
        os: [ "ubuntu-latest", "macos-latest", "windows-latest" ]
        go-version: [ "1.24.0" ]
    runs-on: ${{ matrix.os }}
    env:
      CGO_ENABLED: 0
    ```

    **Coverage Job Configuration:**
    ```yaml
    runs-on: ubuntu-latest
    steps:
      - name: measure coverage
        run: CGO_ENABLED=0 go test -v -coverprofile=coverage.out ./...
      - name: report coverage
        run: bash <(curl -s https://codecov.io/bash)
    ```

    ### Lint Workflow Configuration

    The `lint` workflow  triggers on all pushes and pull requests:

    ```yaml
    on:
      push:
      pull_request:
    ```

    Each platform runs independently with the same configuration:

    ```yaml
    strategy:
      matrix:
        os: [ "ubuntu-latest", "macos-latest", "windows-latest" ]
        go-version: [ "1.24.0" ]
    ```

    The `golangci-lint-action` executes with:
    - Latest linter version
    - 60-minute timeout for complete analysis
    - Only new issues reported

    ## Developer Workflow

    ### Pre-Commit Checklist

    Before committing code, developers should:

    1. **Format Code**: Run `go fmt ./...` to ensure consistent formatting 
    2. **Run Linter**: Execute `golangci-lint run ./...` to catch errors and maintain clean code 
    3. **Run Tests Locally**: Execute `go test -v ./...` to validate changes

    ### Contributing Standards

    ```mermaid
    graph LR
        subgraph "Fork Setup"
            Fork["Fork Repository"]
            Clone["Clone to GOPATH"]
            Remote_Origin["git remote rename<br/>origin → upstream"]
            Add_Fork["git remote add origin<br/>(fork URL)"]
        end
    
        subgraph "Development"
            Branch["Create Feature Branch<br/>from develop"]
            Code["Write Code"]
            Format["go fmt ./..."]
            Lint["golangci-lint run ./..."]
            Test["go test -v ./..."]
            Commit["Commit Changes"]
        end
    
        subgraph "Pull Request"
            Rebase["git rebase<br/>upstream/develop"]
            Push["Push to Fork"]
            PR["Create PR to develop"]
        end
    
        subgraph "CI Validation"
            Test_CI["Tests Workflow<br/>(3 OS)"]
            Lint_CI["Lint Workflow<br/>(3 OS)"]
            Coverage_CI["Coverage Report"]
        end
    
        Fork --> Clone
        Clone --> Remote_Origin
        Remote_Origin --> Add_Fork
    
        Add_Fork --> Branch
        Branch --> Code
        Code --> Format
        Format --> Lint
        Lint --> Test
        Test --> Commit
    
        Commit --> Rebase
        Rebase --> Push
        Push --> PR
    
        PR --> Test_CI
        PR --> Lint_CI
        PR --> Coverage_CI
    ```

    **Development Workflow**: Developers fork the repository, create feature branches from develop, ensure code quality through local tools, and submit pull requests that undergo automated CI validation.

    ### Branch Strategy

    - **`main`**: Stable release branch
    - **`develop`**: Active development branch (default target for PRs)
    - **Feature branches**: Created from `develop` on developer forks

    No force pushes to `develop` except when reverting broken commits . All pull requests must target `develop`, not `main` .

    ### Environment Configuration

    All builds and tests use:
    - **Go Version**: 1.24.0
    - **CGO**: Disabled (`CGO_ENABLED=0`)

    This configuration matches production builds to ensure test environments accurately reflect deployment conditions.

    ## Build Validation

    ### Pre-Release Hooks

    The build system runs validation before creating releases:

    ```yaml
    before:
      hooks:
      - go mod tidy
    ```

    This ensures dependency consistency before producing release artifacts.

    ### Build Configuration

    All release builds use `CGO_ENABLED=0`  to produce static binaries without C dependencies, improving portability and eliminating runtime library requirements.

    The build targets 11 platform-architecture combinations:
    - Linux: amd64, 386, arm (v6/v7), arm64
    - Darwin: amd64, arm64
    - Windows: amd64

    ## Quality Gates

    ### Required Checks

    All pull requests must pass:

    1. **Test Matrix**: All 6 test runs (3 OS × 2 configurations) must succeed
    2. **Lint Matrix**: All 3 lint checks (3 OS) must pass with no new issues
    3. **Coverage**: Coverage must be measured and reported (no specific threshold enforced)

    ### Code Review Process

    After automated checks pass, code requires human review following GitHub standard practices. The project maintainer reviews changes for:
    - Architectural consistency
    - Security implications
    - Performance considerations
    - Documentation completeness

    ### Ignored Artifacts

    Testing and build artifacts excluded from version control:

    | Pattern | Purpose |
    |---------|---------|
    | `*.test` | Test binaries |
    | `*.out` | Coverage profiles |
    | `*.json` | Output data files |
    | `*.log` | Log files |
    | `*.html` | HTML reports |
    | `.idea` | JetBrains IDE files |

    Docker builds exclude additional patterns including archives, compressed files, and build artifacts .

=== "Custom Plugins"

    This page provides a comprehensive tutorial for developing custom plugins that extend Amass's discovery capabilities. It covers the required interfaces, handler registration, event processing patterns, and integration with the cache and DNS systems.

    For information about the overall plugin architecture and existing plugin categories, see [Architecture](../architecture/index.md). For details on the plugin interfaces and priority system, see [Architecture](../architecture/plugins.md). For existing DNS, API, service discovery, and enrichment plugins, see sections [6.2](#6.2) through [6.5](#6.5).

    ## Overview

    An Amass plugin is a self-contained module that registers one or more **handlers** to process specific asset types. When an event matching the handler's `EventType` is dispatched, the handler's callback function executes to perform discovery, enrichment, or transformation operations. Plugins interact with:

    - **Registry (`et.Registry`)**: Used during startup to register handlers with the engine
    - **Event (`et.Event`)**: Contains the asset entity, session context, and dispatcher for generating new events
    - **Session (`et.Session`)**: Provides access to configuration, cache, scope checking, and logging
    - **Support utilities**: Helper functions for DNS queries, TTL management, and asset creation

    ## Plugin Interface

    All plugins must implement the `et.Plugin` interface with three methods:

    ```go
    type Plugin interface {
        Name() string
        Start(r Registry) error
        Stop()
    }
    ```

    ### Name Method

    Returns a unique identifier for the plugin used in logging and source attribution.

    **Example from DNS plugin:**
    ```go
    func (d *dnsPlugin) Name() string {
        return d.name  // "DNS"
    }
    ```

    ### Start Method

    Called during engine initialization to register handlers. This is where you configure the plugin's behavior by registering one or more handlers with specific priorities, event types, and transforms.

    **Pattern from DNS plugin:**
    ```go
    func (d *dnsPlugin) Start(r et.Registry) error {
        d.log = r.Log().WithGroup("plugin").With("name", d.name)
    
        // Register TXT handler with priority 1 (highest)
        d.txt = &dnsTXT{...}
        if err := r.RegisterHandler(&et.Handler{
            Plugin:       d,
            Name:         d.txt.name,
            Priority:     1,
            MaxInstances: support.MaxHandlerInstances,
            Transforms:   []string{string(oam.FQDN)},
            EventType:    oam.FQDN,
            Callback:     d.txt.check,
        }); err != nil {
            return err
        }
    
        // Register additional handlers...
        return nil
    }
    ```

    ### Stop Method

    Called during engine shutdown to cleanup resources. Close channels, release goroutines, and finalize any pending operations.

    **Example from DNS plugin:**
    ```go
    func (d *dnsPlugin) Stop() {
        close(d.subs.done)  // Signal background goroutines to exit
        d.log.Info("Plugin stopped")
    }
    ```

    ## Handler Registration

    Handlers are registered using the `et.Handler` struct, which configures how and when the handler executes:

    ```go
    type Handler struct {
        Plugin       Plugin
        Name         string
        Priority     int
        MaxInstances int
        Transforms   []string
        EventType    oam.AssetType
        Callback     func(*Event) error
    }
    ```

    ### Handler Fields

    | Field | Description | Example |
    |-------|-------------|---------|
    | `Plugin` | Reference to parent plugin | `d` (the plugin instance) |
    | `Name` | Unique handler identifier | `"DNS-TXT"` |
    | `Priority` | Execution order (1-9, lower=higher) | `1` (TXT), `2` (CNAME), `3` (A/AAAA) |
    | `MaxInstances` | Concurrent execution limit | `support.MaxHandlerInstances` (100) |
    | `Transforms` | Asset types produced | `[]string{string(oam.FQDN)}` |
    | `EventType` | Asset type consumed | `oam.FQDN` |
    | `Callback` | Handler function | `d.txt.check` |

    ### Priority System

    Handlers execute in priority order (1-9, lower number = higher priority). This ensures dependencies are satisfied before dependent handlers run:

    ```mermaid
    graph TD
        Priority1["Priority 1<br/>DNS-TXT<br/>Extract organization IDs"]
        Priority2["Priority 2<br/>DNS-CNAME<br/>Resolve aliases"]
        Priority3["Priority 3<br/>DNS-IP<br/>Get A/AAAA records"]
        Priority4["Priority 4<br/>DNS-Subdomains<br/>Find NS/MX/SRV"]
        Priority5["Priority 5<br/>DNS-Apex<br/>Build hierarchy"]
        Priority8["Priority 8<br/>DNS-Reverse<br/>PTR lookups"]
        Priority9["Priority 9<br/>HTTP-Probes<br/>Service discovery"]
    
        Priority1 --> Priority2
        Priority2 --> Priority3
        Priority3 --> Priority4
        Priority4 --> Priority5
        Priority5 --> Priority8
        Priority8 --> Priority9
    ```

    ### Transforms Declaration

    The `Transforms` field declares which asset types the handler can produce. This information is used by the configuration system to validate transformation rules and TTL settings:

    **Example from BGP.Tools plugin:**
    ```go
    // Netblock handler transforms IPAddress → Netblock
    if err := r.RegisterHandler(&et.Handler{
        Transforms: []string{string(oam.Netblock)},
        EventType:  oam.IPAddress,
        // ...
    }); err != nil {
        return err
    }

    // Autsys handler transforms Netblock → AutonomousSystem
    if err := r.RegisterHandler(&et.Handler{
        Transforms: []string{string(oam.AutonomousSystem)},
        EventType:  oam.Netblock,
        // ...
    }); err != nil {
        return err
    }
    ```

    ## Writing Handler Callbacks

    Handler callbacks follow a standard pattern: extract asset, check TTL, query/lookup data, store results, dispatch events.

    ### Handler Callback Signature

    ```go
    func (h *handlerStruct) check(e *et.Event) error {
        // Implementation
    }
    ```

    ### Standard Handler Pattern

    Here's the complete pattern used by most handlers:

    ```mermaid
    graph TD
        Start["Handler Callback Invoked"]
        Extract["Extract Asset from Event"]
        CheckTTL["Check TTL Configuration"]
        MonitorCheck{"Asset Monitored<br/>Within TTL?"}
        Lookup["Lookup from Cache"]
        Query["Query External Source"]
        Store["Store Results in Cache"]
        Process["Dispatch New Events"]
        End["Return"]
    
        Start --> Extract
        Extract --> CheckTTL
        CheckTTL --> MonitorCheck
        MonitorCheck -->|Yes| Lookup
        MonitorCheck -->|No| Query
        Query --> Store
        Lookup --> Process
        Store --> Process
        Process --> End
    ```

    ### Complete Handler Example

    Here's a complete handler implementation from the DNS TXT plugin:

    ```go
    type dnsTXT struct {
        name   string
        plugin *dnsPlugin
        source *et.Source
    }

    func (d *dnsTXT) check(e *et.Event) error {
        // 1. Extract asset from event
        _, ok := e.Entity.Asset.(*oamdns.FQDN)
        if !ok {
            return errors.New("failed to extract the FQDN asset")
        }
    
        // 2. Get TTL start time for this transformation
        since, err := support.TTLStartTime(e.Session.Config(), "FQDN", "FQDN", d.plugin.name)
        if err != nil {
            return err
        }
    
        // 3. Check if asset was recently monitored
        var txtRecords []dns.RR
        var props []*oamdns.DNSRecordProperty
        if support.AssetMonitoredWithinTTL(e.Session, e.Entity, d.source, since) {
            // Lookup from cache
            props = d.lookup(e, e.Entity, since)
        } else {
            // Query DNS and store
            txtRecords = d.query(e, e.Entity)
            d.store(e, e.Entity, txtRecords)
        }
    
        // 4. Process results (log and update event metadata)
        if len(txtRecords) > 0 {
            d.process(e, e.Entity, txtRecords, props)
            support.AddDNSRecordType(e, int(dns.TypeTXT))
        }
        return nil
    }
    ```

    ### Extracting Assets

    Use type assertions to extract the specific asset type from `e.Entity.Asset`:

    ```go
    // FQDN asset
    fqdn, ok := e.Entity.Asset.(*oamdns.FQDN)
    if !ok {
        return errors.New("failed to extract the FQDN asset")
    }

    // IPAddress asset
    ip, ok := e.Entity.Asset.(*oamnet.IPAddress)
    if !ok {
        return errors.New("failed to extract the IPAddress asset")
    }

    // Netblock asset
    nb, ok := e.Entity.Asset.(*oamnet.Netblock)
    if !ok {
        return errors.New("failed to extract the Netblock asset")
    }
    ```

    ### TTL-Based Caching Pattern

    The TTL system prevents redundant queries. Always check if an asset was recently monitored:

    ```go
    // Get TTL start time from configuration
    since, err := support.TTLStartTime(
        e.Session.Config(),
        "FQDN",        // From asset type
        "IPAddress",   // To asset type
        d.plugin.name, // Plugin name
    )
    if err != nil {
        return err
    }

    // Check if asset was monitored within TTL
    if support.AssetMonitoredWithinTTL(e.Session, e.Entity, d.source, since) {
        // Use cached data
        results = d.lookup(e, e.Entity, since)
    } else {
        // Perform fresh query
        results = d.query(e, e.Entity)
        d.store(e, e.Entity, results)
        support.MarkAssetMonitored(e.Session, e.Entity, d.source)
    }
    ```

    ## Implementing Query and Lookup Methods

    ### Query Method Pattern

    Queries external sources (DNS, APIs, WHOIS) and returns raw results:

    ```go
    func (d *dnsTXT) query(e *et.Event, name *dbt.Entity) []dns.RR {
        var txtRecords []dns.RR
    
        fqdn, ok := name.Asset.(*oamdns.FQDN)
        if !ok {
            return txtRecords
        }
    
        // Use support utility for DNS query
        if rr, err := support.PerformQuery(fqdn.Name, dns.TypeTXT); err == nil {
            txtRecords = append(txtRecords, rr...)
            support.MarkAssetMonitored(e.Session, name, d.source)
        }
    
        return txtRecords
    }
    ```

    ### Lookup Method Pattern

    Retrieves previously stored data from the cache within the TTL window:

    ```go
    func (d *dnsTXT) lookup(e *et.Event, fqdn *dbt.Entity, since time.Time) []*oamdns.DNSRecordProperty {
        var props []*oamdns.DNSRecordProperty
    
        n, ok := fqdn.Asset.(*oamdns.FQDN)
        if !ok || n == nil {
            return props
        }
    
        // Get entity tags (properties) created since TTL start time
        if tags, err := e.Session.Cache().GetEntityTags(fqdn, since, "dns_record"); err == nil {
            for _, tag := range tags {
                if prop, ok := tag.Property.(*oamdns.DNSRecordProperty); ok && prop.Header.RRType == int(dns.TypeTXT) {
                    props = append(props, prop)
                }
            }
        }
    
        return props
    }
    ```

    ### Store Method Pattern

    Persists discovered data in the cache as assets, edges, and properties:

    ```go
    func (d *dnsTXT) store(e *et.Event, fqdn *dbt.Entity, rr []dns.RR) {
        for _, record := range rr {
            if record.Header().Rrtype != dns.TypeTXT {
                continue
            }
        
            txtValue := strings.Join((record.(*dns.TXT)).Txt, " ")
        
            // Create entity property (tag on the FQDN entity)
            _, err := e.Session.Cache().CreateEntityProperty(fqdn, &oamdns.DNSRecordProperty{
                PropertyName: "dns_record",
                Header: oamdns.RRHeader{
                    RRType: int(dns.TypeTXT),
                    Class:  int(record.Header().Class),
                    TTL:    int(record.Header().Ttl),
                },
                Data: txtValue,
            })
            if err != nil {
                msg := fmt.Sprintf("failed to create entity property for %s: %s", txtValue, err)
                e.Session.Log().Error(msg, "error", err.Error(),
                    slog.Group("plugin", "name", d.plugin.name, "handler", d.name))
            }
        }
    }
    ```

    ## Cache Operations

    ### Creating Assets

    Assets are created using `e.Session.Cache().CreateAsset()`:

    ```go
    // Create FQDN asset
    fqdn, err := e.Session.Cache().CreateAsset(&oamdns.FQDN{Name: "example.com"})
    if err != nil || fqdn == nil {
        return nil
    }

    // Create IPAddress asset
    ip, err := e.Session.Cache().CreateAsset(&oamnet.IPAddress{
        Address: netip.MustParseAddr("192.0.2.1"),
        Type:    "IPv4",
    })

    // Create Netblock asset
    nb, err := e.Session.Cache().CreateAsset(&oamnet.Netblock{
        Type: "IPv4",
        CIDR: netip.MustParsePrefix("192.0.2.0/24"),
    })
    ```

    ### Creating Edges (Relationships)

    Edges connect two assets with a typed relationship:

    ```go
    // Create CNAME relationship: alias -> target
    edge, err := e.Session.Cache().CreateEdge(&dbt.Edge{
        Relation: &oamdns.BasicDNSRelation{
            Name: "dns_record",
            Header: oamdns.RRHeader{
                RRType: int(dns.TypeCNAME),
                Class:  int(record.Header().Class),
                TTL:    int(record.Header().Ttl),
            },
        },
        FromEntity: alias,
        ToEntity:   target,
    })
    ```

    ### Adding Source Properties

    Source properties track provenance and confidence:

    ```go
    // Add source to entity
    _, _ = e.Session.Cache().CreateEntityProperty(entity, &general.SourceProperty{
        Source:     d.source.Name,
        Confidence: d.source.Confidence,
    })

    // Add source to edge
    _, _ = e.Session.Cache().CreateEdgeProperty(edge, &general.SourceProperty{
        Source:     d.source.Name,
        Confidence: d.source.Confidence,
    })
    ```

    ## Dispatching Events

    After storing discovered assets, dispatch events to trigger downstream handlers:

    ```go
    func (d *dnsCNAME) process(e *et.Event, alias []*relAlias) {
        for _, a := range alias {
            target := a.target.Asset.(*oamdns.FQDN)
        
            // Dispatch event for discovered FQDN
            _ = e.Dispatcher.DispatchEvent(&et.Event{
                Name:    target.Name,
                Entity:  a.target,
                Session: e.Session,
            })
        
            // Log the discovery
            e.Session.Log().Info("relationship discovered", "from", d.plugin.source.Name, 
                "relation", "cname_record", "to", target.Name, 
                slog.Group("plugin", "name", d.plugin.name, "handler", d.name))
        }
    }
    ```

    ## Using Support Utilities

    The `support` package provides common functionality:

    ### DNS Operations

    ```go
    // Perform DNS query with retry logic
    rr, err := support.PerformQuery("example.com", dns.TypeA)

    // Scrape subdomains from text
    subdomains := support.ScrapeSubdomainNames(htmlContent)

    // Extract URLs from text
    urls := support.ExtractURLsFromString(htmlContent)
    ```

    ### TTL Management

    ```go
    // Get TTL start time
    since, err := support.TTLStartTime(cfg, "FQDN", "IPAddress", "DNS")

    // Check if asset was monitored within TTL
    if support.AssetMonitoredWithinTTL(session, entity, source, since) {
        // Use cached data
    }

    // Mark asset as monitored
    support.MarkAssetMonitored(session, entity, source)
    ```

    ### IP Address Operations

    ```go
    // Get netblock for IP address
    entry := support.IPNetblock(session, "192.0.2.1")

    // Add netblock to session's CIDR ranger
    err := support.AddNetblock(session, "192.0.2.0/24", 64512, source)

    // Perform IP address sweep
    support.IPAddressSweep(e, ipAddr, source, 25, func(e *et.Event, addr *oamnet.IPAddress, src *et.Source) {
        // Callback for each IP in sweep
    })
    ```

    ### API Key Retrieval

    ```go
    // Get API key from configuration
    apiKey, err := support.GetAPI("GLEIF", e)
    if err != nil {
        return err
    }
    ```

    ## Complete Plugin Example

    Here's a complete minimal plugin that discovers IP netblocks:

    ```go
    package plugins

    import (
        "errors"
        "log/slog"
        "net/netip"
    
        "github.com/owasp-amass/amass/v5/engine/plugins/support"
        et "github.com/owasp-amass/amass/v5/engine/types"
        dbt "github.com/owasp-amass/asset-db/types"
        oam "github.com/owasp-amass/open-asset-model"
        "github.com/owasp-amass/open-asset-model/general"
        oamnet "github.com/owasp-amass/open-asset-model/network"
    )

    // Plugin struct
    type ipNetblock struct {
        name   string
        log    *slog.Logger
        source *et.Source
    }

    // Constructor
    func NewIPNetblock() et.Plugin {
        return &ipNetblock{
            name: "IP-Netblock",
            source: &et.Source{
                Name:       "IP-Netblock",
                Confidence: 100,
            },
        }
    }

    // Name returns plugin identifier
    func (d *ipNetblock) Name() string {
        return d.name
    }

    // Start registers handlers
    func (d *ipNetblock) Start(r et.Registry) error {
        d.log = r.Log().WithGroup("plugin").With("name", d.name)
    
        name := d.name + "-Handler"
        if err := r.RegisterHandler(&et.Handler{
            Plugin:       d,
            Name:         name,
            Priority:     4,
            MaxInstances: support.MaxHandlerInstances,
            Transforms:   []string{string(oam.Netblock)},
            EventType:    oam.IPAddress,
            Callback:     d.lookup,
        }); err != nil {
            return err
        }
    
        d.log.Info("Plugin started")
        return nil
    }

    // Stop cleans up resources
    func (d *ipNetblock) Stop() {
        d.log.Info("Plugin stopped")
    }

    // Handler callback
    func (d *ipNetblock) lookup(e *et.Event) error {
        // Extract asset
        ip, ok := e.Entity.Asset.(*oamnet.IPAddress)
        if !ok {
            return errors.New("failed to extract the IPAddress asset")
        }
    
        // Wait for netblock to be available (added by BGP.Tools or other source)
        var entry *sessions.CIDRangerEntry
        for i := 0; i < 120; i++ {
            entry = support.IPNetblock(e.Session, ip.Address.String())
            if entry != nil {
                break
            }
            time.Sleep(time.Second)
        }
        if entry == nil {
            return nil
        }
    
        // Store netblock and AS
        nb, as := d.store(e, entry)
        if nb == nil || as == nil {
            return nil
        }
    
        // Dispatch events
        d.process(e, e.Entity, nb, as)
        return nil
    }

    // Store results in cache
    func (d *ipNetblock) store(e *et.Event, entry *sessions.CIDRangerEntry) (*dbt.Entity, *dbt.Entity) {
        // Create netblock asset
        netblock := &oamnet.Netblock{
            Type: "IPv4",
            CIDR: netip.MustParsePrefix(entry.Net.String()),
        }
        if netblock.CIDR.Addr().Is6() {
            netblock.Type = "IPv6"
        }
    
        nb, err := e.Session.Cache().CreateAsset(netblock)
        if err != nil || nb == nil {
            return nil, nil
        }
    
        // Add source property
        _, _ = e.Session.Cache().CreateEntityProperty(nb, &general.SourceProperty{
            Source:     entry.Src.Name,
            Confidence: entry.Src.Confidence,
        })
    
        // Create edge: netblock -> IP
        edge, err := e.Session.Cache().CreateEdge(&dbt.Edge{
            Relation:   &general.SimpleRelation{Name: "contains"},
            FromEntity: nb,
            ToEntity:   e.Entity,
        })
        if err != nil || edge == nil {
            return nil, nil
        }
    
        // Add source to edge
        _, _ = e.Session.Cache().CreateEdgeProperty(edge, &general.SourceProperty{
            Source:     entry.Src.Name,
            Confidence: entry.Src.Confidence,
        })
    
        // Create AS asset
        as, err := e.Session.Cache().CreateAsset(&oamnet.AutonomousSystem{Number: entry.ASN})
        if err != nil || as == nil {
            return nil, nil
        }
    
        // Create edge: AS -> netblock
        edge, err = e.Session.Cache().CreateEdge(&dbt.Edge{
            Relation:   &general.SimpleRelation{Name: "announces"},
            FromEntity: as,
            ToEntity:   nb,
        })
    
        return nb, as
    }

    // Dispatch events for discovered assets
    func (d *ipNetblock) process(e *et.Event, ip, nb, as *dbt.Entity) {
        // Dispatch netblock event
        _ = e.Dispatcher.DispatchEvent(&et.Event{
            Name:    nb.Asset.Key(),
            Entity:  nb,
            Session: e.Session,
        })
    
        // Log discovery
        e.Session.Log().Info("relationship discovered", "from", nb.Asset.Key(), 
            "relation", "contains", "to", ip.Asset.Key(), 
            slog.Group("plugin", "name", d.name, "handler", d.name+"-Handler"))
    
        // Dispatch AS event
        asname := "AS" + as.Asset.Key()
        _ = e.Dispatcher.DispatchEvent(&et.Event{
            Name:    asname,
            Entity:  as,
            Session: e.Session,
        })
    
        e.Session.Log().Info("relationship discovered", "from", asname, 
            "relation", "announces", "to", nb.Asset.Key(), 
            slog.Group("plugin", "name", d.name, "handler", d.name+"-Handler"))
    }
    ```

    ## Plugin Data Flow Diagram

    ```mermaid
    graph TB
        EventReceived["Event Received<br/>e *et.Event"]
        ExtractAsset["Extract Asset<br/>e.Entity.Asset"]
        GetTTL["Get TTL Start Time<br/>support.TTLStartTime()"]
        CheckMonitored{"Asset Monitored?<br/>AssetMonitoredWithinTTL()"}
    
        subgraph "Cache Path"
            Lookup["Lookup from Cache<br/>e.Session.Cache().GetEntityTags()"]
        end
    
        subgraph "Query Path"
            Query["Query External Source<br/>DNS/API/WHOIS"]
            CreateAsset["Create Assets<br/>Cache().CreateAsset()"]
            CreateEdge["Create Edges<br/>Cache().CreateEdge()"]
            AddSource["Add Source Properties<br/>CreateEntityProperty()"]
            MarkMonitored["Mark Monitored<br/>support.MarkAssetMonitored()"]
        end
    
        ProcessResults["Process Results<br/>Log discoveries"]
        DispatchEvents["Dispatch Events<br/>e.Dispatcher.DispatchEvent()"]
        Return["Return nil"]
    
        EventReceived --> ExtractAsset
        ExtractAsset --> GetTTL
        GetTTL --> CheckMonitored
        CheckMonitored -->|Yes| Lookup
        CheckMonitored -->|No| Query
    
        Query --> CreateAsset
        CreateAsset --> CreateEdge
        CreateEdge --> AddSource
        AddSource --> MarkMonitored
    
        Lookup --> ProcessResults
        MarkMonitored --> ProcessResults
        ProcessResults --> DispatchEvents
        DispatchEvents --> Return
    ```

    ## Best Practices

    ### Priority Assignment

    Assign priorities based on dependencies:
    - **1-2**: Fundamental DNS records (TXT, CNAME)
    - **3-4**: Basic resolution (A/AAAA, NS/MX)
    - **5-6**: Hierarchy and search (Apex, organization search)
    - **7-8**: Enrichment and reverse lookups
    - **9**: Active probing

    ### Error Handling

    Always validate assets and handle errors gracefully:

    ```go
    // Validate asset extraction
    fqdn, ok := e.Entity.Asset.(*oamdns.FQDN)
    if !ok {
        return errors.New("failed to extract the FQDN asset")
    }

    // Handle cache errors
    if err != nil {
        e.Session.Log().Error(err.Error(), 
            slog.Group("plugin", "name", d.plugin.name, "handler", d.name))
        return nil  // Don't fail the handler
    }
    ```

    ### Scope Checking

    Check if assets are in scope before performing expensive operations:

    ```go
    // Check FQDN scope
    if _, conf := e.Session.Scope().IsAssetInScope(fqdn, 0); conf == 0 {
        return nil
    }

    // Check IP scope
    if !e.Session.Scope().IsAddressInScope(e.Session.Cache(), ip) {
        return nil
    }
    ```

    ### Asynchronous Operations

    Use goroutines for slow operations to avoid blocking the handler:

    ```go
    if support.AssetMonitoredWithinTTL(e.Session, e.Entity, src, since) {
        findings = append(findings, r.lookup(e, e.Entity, since)...)
    } else {
        go func() {
            if findings := append(findings, r.query(e, e.Entity)...); len(findings) > 0 {
                r.process(e, findings)
            }
        }()
        support.MarkAssetMonitored(e.Session, e.Entity, src)
    }
    ```

    ### Logging Standards

    Use structured logging with consistent fields:

    ```go
    e.Session.Log().Info("relationship discovered", 
        "from", fromName, 
        "relation", relationType, 
        "to", toName, 
        slog.Group("plugin", "name", d.plugin.name, "handler", d.name))

    e.Session.Log().Error("failed to process asset", 
        "error", err.Error(), 
        "asset", assetName,
        slog.Group("plugin", "name", d.plugin.name, "handler", d.name))
    ```

    ### Resource Cleanup

    Always clean up in the `Stop()` method:

    ```go
    func (d *dnsPlugin) Stop() {
        // Close channels
        close(d.subs.done)
    
        // Release locks and cleanup maps
        d.apexLock.Lock()
        d.apexList = nil
        d.apexLock.Unlock()
    
        // Log shutdown
        d.log.Info("Plugin stopped")
    }
    ```

    ## Integration and Testing

    After implementing a plugin:

    1. **Register with Engine**: Import the plugin package and register it in the engine initialization
    2. **Add Configuration**: Add configuration options to `config/config.yaml` for API keys, TTL values, etc.
    3. **Test Handlers**: Write unit tests for individual handler methods
    4. **Test Integration**: Run enumeration with your plugin enabled and verify discoveries
    5. **Check Logs**: Review structured logs to ensure proper attribution and discovery chains

    For information about testing and code quality requirements, see [Testing and Code Quality](#testing-and-code-quality).

=== "Release Process"

    This document describes the automated release pipeline for OWASP Amass, including the GoReleaser configuration for binary distributions, Docker multi-architecture builds, and distribution to GitHub Releases, Homebrew, and Docker Hub. For information about building from source during development, see [Building from Source](#building-from-source). For Docker deployment instructions, see [Docker Deployment](../deployment/docker.md).

    ## Overview of Release Pipeline

    The Amass release process is fully automated through GitHub Actions. When a semantic version tag (e.g., `v4.2.0`) is pushed to the repository, two parallel workflows execute:

    1. **goreleaser workflow** - Cross-compiles binaries for multiple platforms, creates release archives, generates checksums, publishes to GitHub Releases, and updates the Homebrew tap
    2. **docker workflow** - Builds multi-architecture Docker images and publishes them to Docker Hub with semantic version tags

    ```mermaid
    graph TB
        Developer["Developer pushes tag<br/>v*.*.*"]
    
        subgraph "GitHub Actions"
            TagEvent["Tag Push Event<br/>refs/tags/v*.*.*"]
        
            subgraph "goreleaser.yml"
                GRCheckout["Checkout<br/>fetch-depth: 0"]
                GRSetupGo["Setup Go 1.24.0"]
                GRRun["Run GoReleaser<br/>goreleaser release --clean"]
            end
        
            subgraph "docker.yml"
                DockerCheckout["Checkout"]
                DockerLogin["Login to DockerHub<br/>DOCKERHUB_USERNAME<br/>DOCKERHUB_TOKEN"]
                DockerMeta["Docker metadata-action<br/>Generate tags/labels"]
                SetupQEMU["Setup QEMU<br/>linux/amd64,linux/arm64"]
                SetupBuildx["Setup Docker Buildx<br/>driver-opts: network=host"]
                BuildPush["Build and push<br/>platforms: linux/amd64,linux/arm64"]
            end
        end
    
        subgraph "Artifacts"
            Binaries["Cross-compiled Binaries<br/>11 platform combinations"]
            Archives["Release Archives<br/>+ config.yaml<br/>+ datasources.yaml"]
            Checksums["amass_checksums.txt"]
            DockerImages["Docker Images<br/>owaspamass/amass"]
        end
    
        subgraph "Distribution"
            GitHubRelease["GitHub Releases<br/>github.com/owasp-amass/amass"]
            Homebrew["Homebrew Tap<br/>owasp-amass/homebrew-amass"]
            DockerHub["Docker Hub<br/>owaspamass/amass"]
        end
    
        Developer --> TagEvent
    
        TagEvent --> GRCheckout
        GRCheckout --> GRSetupGo
        GRSetupGo --> GRRun
    
        TagEvent --> DockerCheckout
        DockerCheckout --> DockerLogin
        DockerLogin --> DockerMeta
        DockerMeta --> SetupQEMU
        SetupQEMU --> SetupBuildx
        SetupBuildx --> BuildPush
    
        GRRun --> Binaries
        GRRun --> Archives
        GRRun --> Checksums
        BuildPush --> DockerImages
    
        Binaries --> GitHubRelease
        Archives --> GitHubRelease
        Archives --> Homebrew
        Checksums --> GitHubRelease
        DockerImages --> DockerHub
    ```

    ## Release Triggering

    Releases are triggered exclusively by pushing semantic version tags matching the pattern `v*.*.*` to the repository. Both the `goreleaser` and `docker` workflows listen for these tag push events.

    | Workflow | Trigger Pattern | File |
    |----------|----------------|------|
    | goreleaser | `tags: - 'v*.*.*'` |  |
    | docker | `tags: - 'v*.*.*'` |  |

    The workflows do not trigger on branch pushes or pull requests. The tag format must follow semantic versioning conventions (e.g., `v4.2.0`, `v4.2.1-rc.1`).

    ## GoReleaser Configuration

    The GoReleaser configuration at  defines the cross-compilation matrix, archive structure, and distribution settings.

    ### Build Matrix

    GoReleaser compiles the `./cmd/amass` main package into the `amass` binary for multiple operating systems and architectures:

    | OS | Architectures | Notes |
    |----|--------------|-------|
    | linux | amd64, 386, arm (v6, v7), arm64 | All combinations supported |
    | darwin | amd64, arm64 | 386 and arm excluded via ignore rules |
    | windows | amd64 | 386, arm, arm64 excluded via ignore rules |

    ```mermaid
    graph LR
        subgraph "Build Configuration"
            Main["main: ./cmd/amass<br/>binary: amass<br/>CGO_ENABLED=0"]
        end
    
        subgraph "Target Platforms"
            Linux["linux<br/>amd64, 386<br/>arm v6/v7, arm64"]
            Darwin["darwin<br/>amd64, arm64"]
            Windows["windows<br/>amd64"]
        end
    
        subgraph "Ignore Rules"
            Ignore["darwin/386<br/>darwin/arm<br/>windows/386<br/>windows/arm<br/>windows/arm64"]
        end
    
        Main --> Linux
        Main --> Darwin
        Main --> Windows
    
        Ignore -.->|"excluded"| Darwin
        Ignore -.->|"excluded"| Windows
    ```

    The build uses `CGO_ENABLED=0` to produce static binaries with no external dependencies, ensuring portability across different Linux distributions and versions.

    ### Archive Creation

    Each platform's binary is packaged into a named archive with configuration files:

    ```
    Archive naming: amass_{Os}_{Arch}{Armv}.tar.gz
    Example: amass_linux_amd64.tar.gz
             amass_linux_armv7.tar.gz
             amass_darwin_arm64.tar.gz
    ```

    Archives contain:
    - `amass` binary
    - `LICENSE` file
    - `README.md` documentation
    - `resources/config.yaml` - default configuration template
    - `resources/datasources.yaml` - data source definitions

    Configuration at :

    ```yaml
    archives:
      -
        name_template: "{{ .ProjectName }}_{{ .Os }}_{{ .Arch }}{{ if .Arm }}v{{ .Arm }}{{ end }}"
        wrap_in_directory: true
        files:
          - LICENSE
          - README.md
          - resources/config.yaml
          - resources/datasources.yaml
    ```

    ### Checksum Generation

    GoReleaser generates a unified checksum file named `amass_checksums.txt` containing SHA256 hashes of all release archives. Users can verify download integrity using:

    ```bash
    sha256sum -c amass_checksums.txt --ignore-missing
    ```

    ### GitHub Release Publication

    The workflow publishes releases to the `owasp-amass/amass` repository on GitHub. The release includes:

    - All platform archives
    - Checksum file
    - Auto-generated changelog (sorted descending, excluding merge commits and tag references)

    Authentication uses the built-in `GITHUB_TOKEN` provided by GitHub Actions. The workflow requires `contents: write` permission to create releases.

    ### Homebrew Tap Update

    GoReleaser automatically updates the Homebrew tap repository at `owasp-amass/homebrew-amass` with each release. The cask configuration:

    | Property | Value |
    |----------|-------|
    | Repository | owasp-amass/homebrew-amass |
    | Branch | main |
    | Commit Author | caffix <caffix@users.noreply.github.com> |
    | Homepage | https://owasp.org/www-project-amass/ |
    | License | Apache-2.0 |

    The tap update requires a separate GitHub token (`HOMEBREW_TAP_GITHUB_TOKEN`) with write access to the Homebrew repository. This token is stored as a GitHub Actions secret and passed to GoReleaser.

    ## Docker Multi-Architecture Build

    The Docker workflow at  builds container images for multiple architectures using QEMU emulation and Docker Buildx.

    ### Docker Build Process

    ```mermaid
    graph TD
        Checkout["Checkout source"]
        Login["DockerHub Login<br/>secrets.DOCKERHUB_USERNAME<br/>secrets.DOCKERHUB_TOKEN"]
        Meta["docker/metadata-action<br/>Generate tags + labels"]
        QEMU["docker/setup-qemu-action<br/>platforms:<br/>linux/amd64, linux/arm64"]
        Buildx["docker/setup-buildx-action<br/>driver-opts: network=host"]
        Build["docker/build-push-action<br/>context: .<br/>file: ./Dockerfile<br/>push: true"]
    
        Checkout --> Login
        Login --> Meta
        Meta --> QEMU
        QEMU --> Buildx
        Buildx --> Build
    
        subgraph "Generated Tags"
            Tag1["v4 (major)"]
            Tag2["v4.2 (major.minor)"]
            Tag3["v4.2.0 (full semver)"]
        end
    
        Meta --> Tag1
        Meta --> Tag2
        Meta --> Tag3
    
        Build --> Tag1
        Build --> Tag2
        Build --> Tag3
    ```

    ### Multi-Architecture Support

    The build supports two architectures: `linux/amd64` and `linux/arm64`. Cross-platform compilation is enabled through:

    1. **QEMU Setup** - Installs QEMU static binaries to emulate foreign architectures ()
    2. **Docker Buildx** - Uses the Docker Buildx builder with `network=host` driver option for improved build performance ()

    The build process creates a unified multi-architecture manifest, allowing Docker to automatically pull the correct image for the host architecture.

    ### Docker Image Tagging

    The `docker/metadata-action` generates three semantic version tags for each release:

    | Tag Pattern | Example | Description |
    |-------------|---------|-------------|
    | `v{{major}}` | `v4` | Major version (mutable, updates with each v4.x.y) |
    | `v{{major}}.{{minor}}` | `v4.2` | Major.minor version (mutable, updates with each v4.2.z) |
    | `v{{major}}.{{minor}}.{{patch}}` | `v4.2.0` | Full semantic version (immutable) |

    All images are published to `owaspamass/amass` on Docker Hub. The tagging strategy allows users to:
    - Pin to specific versions: `docker pull owaspamass/amass:v4.2.0`
    - Track minor versions: `docker pull owaspamass/amass:v4.2`
    - Auto-update with major versions: `docker pull owaspamass/amass:v4`

    ### Docker Image Metadata

    Images include standardized OCI labels:

    ```yaml
    org.opencontainers.image.title=OWASP Amass
    org.opencontainers.image.description=In-depth attack surface mapping and asset discovery
    org.opencontainers.image.vendor=OWASP Foundation
    ```

    These labels enable container registry UIs and tooling to display meaningful information about the images.

    ## Continuous Integration Workflows

    While not directly part of the release process, two CI workflows maintain code quality on every push:

    ### Test Workflow

    The `tests` workflow () runs on pushes to `main` and `develop` branches, and on pull requests:

    ```mermaid
    graph LR
        subgraph "Test Matrix"
            OS["3 Operating Systems<br/>ubuntu-latest<br/>macos-latest<br/>windows-latest"]
            Go["Go Version<br/>1.24.0"]
        end
    
        subgraph "Test Stages"
            Simple["Simple Test<br/>go test -v ./..."]
            GC["Test with GC Pressure<br/>GOGC=1<br/>go test -v ./..."]
        end
    
        subgraph "Coverage"
            Measure["Measure Coverage<br/>go test -coverprofile"]
            Report["Report to Codecov<br/>bash curl codecov.io"]
        end
    
        OS --> Simple
        Go --> Simple
        Simple --> GC
    
        OS --> Measure
        Go --> Measure
        Measure --> Report
    ```

    The workflow runs tests twice on each platform: once normally, and once with `GOGC=1` to stress-test garbage collection behavior. Coverage is measured only on Ubuntu and reported to Codecov.

    ### Lint Workflow

    The `lint` workflow () uses `golangci-lint` to enforce code quality standards:

    | Configuration | Value |
    |---------------|-------|
    | Matrix | 3 OS × Go 1.24.0 |
    | Timeout | 60 minutes |
    | Mode | only-new-issues: true |

    The workflow runs on every push and pull request, checking only newly introduced issues to avoid overwhelming developers with pre-existing problems.

    ## Build Artifacts Summary

    A complete release produces the following artifacts:

    ### Binary Distributions (11 total)

    | Platform | Archive Name |
    |----------|--------------|
    | Linux amd64 | `amass_linux_amd64.tar.gz` |
    | Linux 386 | `amass_linux_386.tar.gz` |
    | Linux arm v6 | `amass_linux_armv6.tar.gz` |
    | Linux arm v7 | `amass_linux_armv7.tar.gz` |
    | Linux arm64 | `amass_linux_arm64.tar.gz` |
    | Darwin amd64 | `amass_darwin_amd64.tar.gz` |
    | Darwin arm64 | `amass_darwin_arm64.tar.gz` |
    | Windows amd64 | `amass_windows_amd64.zip` |

    Plus 3 ARM variants for Linux (armv6, armv7, arm64 for 32-bit systems).

    ### Checksum File

    - `amass_checksums.txt` - SHA256 hashes of all archives

    ### Docker Images

    - `owaspamass/amass:v4` (multi-arch manifest)
    - `owaspamass/amass:v4.2` (multi-arch manifest)
    - `owaspamass/amass:v4.2.0` (multi-arch manifest)
      - linux/amd64 image layer
      - linux/arm64 image layer

    ### Homebrew Cask

    - Updated formula in `owasp-amass/homebrew-amass` repository

    ## Distribution Channels

    ```mermaid
    graph TB
        subgraph "Release Artifacts"
            Binaries["Binary Archives<br/>amass_os_arch.tar.gz"]
            Checksums["amass_checksums.txt"]
            Images["Docker Images<br/>owaspamass/amass"]
        end
    
        subgraph "Primary Distribution"
            GitHub["GitHub Releases<br/>github.com/owasp-amass/amass/releases"]
            DockerHub["Docker Hub<br/>hub.docker.com/r/owaspamass/amass"]
            Homebrew["Homebrew Tap<br/>github.com/owasp-amass/homebrew-amass"]
        end
    
        subgraph "Installation Methods"
            DirectDownload["Direct Download<br/>wget + tar -xzf"]
            BrewInstall["brew install amass"]
            DockerRun["docker run owaspamass/amass"]
            GoInstall["go install github.com/owasp-amass/amass/v4/...@latest"]
        end
    
        Binaries --> GitHub
        Checksums --> GitHub
        Binaries --> Homebrew
        Images --> DockerHub
    
        GitHub --> DirectDownload
        GitHub --> GoInstall
        Homebrew --> BrewInstall
        DockerHub --> DockerRun
    ```

    ### GitHub Releases

    Primary distribution channel at `https://github.com/owasp-amass/amass/releases`. Each release page includes:
    - All platform-specific binary archives
    - Checksum file for verification
    - Auto-generated changelog
    - Release notes (if manually added)

    ### Homebrew Tap

    macOS users can install via Homebrew:

    ```bash
    brew tap owasp-amass/amass
    brew install amass
    ```

    The tap repository at `github.com/owasp-amass/homebrew-amass` is automatically updated by GoReleaser. The cask downloads the appropriate Darwin binary from GitHub Releases.

    ### Docker Hub

    Container images are available at `https://hub.docker.com/r/owaspamass/amass`. Users can pull images:

    ```bash
    docker pull owaspamass/amass:v4

    docker pull owaspamass/amass:v4.2.0
    ```

    Images support both `linux/amd64` and `linux/arm64` architectures. Docker automatically selects the appropriate architecture for the host system.

    ## Release Prerequisites

    To execute a release, the following secrets must be configured in the GitHub repository:

    | Secret Name | Purpose | Used By |
    |-------------|---------|---------|
    | `GITHUB_TOKEN` | Built-in token for GitHub API access | goreleaser workflow (automatic) |
    | `HOMEBREW_TAP_GITHUB_TOKEN` | Write access to homebrew-amass repository | goreleaser workflow |
    | `DOCKERHUB_USERNAME` | Docker Hub account username | docker workflow |
    | `DOCKERHUB_TOKEN` | Docker Hub access token | docker workflow |

    The `GITHUB_TOKEN` is automatically provided by GitHub Actions. The other three must be manually configured as repository secrets.

    ## Performing a Release

    To create a new release:

    1. **Ensure all changes are merged to main branch**
    2. **Tag the release** with semantic version:
       ```bash
       git tag v4.2.0
       git push origin v4.2.0
       ```
    3. **Monitor GitHub Actions** - Both workflows will execute automatically:
       - View progress at `https://github.com/owasp-amass/amass/actions`
    4. **Verify release artifacts**:
       - Check GitHub Releases page for archives and checksums
       - Verify Docker Hub shows new tags
       - Confirm Homebrew tap repository has been updated

    The entire process typically completes within 10-15 minutes, depending on GitHub Actions queue times.
