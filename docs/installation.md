# Installation & Deployment

Multiple installation methods are available depending on your platform and use case.

## Installation Methods

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
