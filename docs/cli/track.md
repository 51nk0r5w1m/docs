# track - Change Detection

The `track` subcommand identifies newly discovered assets over time, enabling continuous monitoring of attack surface changes.

## Synopsis

```bash
amass track [options]
```

## Options

### Target Selection

| Flag | Description | Example |
|------|-------------|---------|
| `-d` | Domain names (comma-separated) | `-d example.com` |
| `-df` | File containing domain names | `-df domains.txt` |

### Time Filtering

| Flag | Description | Example |
|------|-------------|---------|
| `-since` | Exclude assets discovered before date | `-since "01/02 15:04:05 2006 MST"` |

### Output Options

| Flag | Description |
|------|-------------|
| `-dir` | Data directory path |

## Examples

### Basic Change Detection

```bash
amass track -d example.com
```

Output:
```
[NEW] api-v2.example.com
[NEW] staging.example.com
[REMOVED] old-api.example.com
```

### Changes Since Date

```bash
amass track -d example.com -since "06/01 00:00:00 2024 UTC"
```

## Change Detection Workflow

```mermaid
flowchart TB
    subgraph Historical["Historical Data"]
        ENUM1[Enum 1<br/>Jan 2024]
        ENUM2[Enum 2<br/>Mar 2024]
        ENUM3[Enum 3<br/>Jun 2024]
    end

    subgraph Analysis
        COMPARE[Compare Assets]
        DIFF[Calculate Diff]
    end

    subgraph Output
        NEW[New Assets]
        REMOVED[Removed Assets]
        CHANGED[Changed Assets]
    end

    ENUM1 & ENUM2 & ENUM3 --> COMPARE
    COMPARE --> DIFF
    DIFF --> NEW & REMOVED & CHANGED
```

## Use Cases

### Security Monitoring

```bash
# Daily monitoring script
#!/bin/bash
amass enum -d example.com -passive -o /data/$(date +%Y%m%d).txt
amass track -d example.com -since "$(date -u +'%m/%d %H:%M:%S %Y UTC')" | mail -s "Attack Surface Changes" security@example.com
```

### Compliance Auditing

```bash
# Changes since a specific date
amass track -d example.com -since "01/01 00:00:00 2024 UTC"
```

## See Also

- [enum](enum.md) - Discover assets
- [subs](subs.md) - Current subdomain listing
