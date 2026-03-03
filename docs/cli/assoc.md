# assoc - Graph Association Walk

The `assoc` subcommand queries the Open Asset Model (OAM) graph database along a walk defined by a sequence of triples (subject-predicate-object patterns).

## Synopsis

```bash
amass assoc [options] [-tf path] [-t1 triple] ... [-t10 triple]
```

## Description

`assoc` walks the OAM graph using triples — subject-predicate-object patterns — and outputs the results as pretty-printed JSON. Up to ten triples can be supplied on the command line (`-t1` through `-t10`), or provided via a file with `-tf`.

## Options

### Triple Input

| Flag | Description | Example |
|------|-------------|---------|
| `-t1` … `-t10` | Triples that define the association walk (positional, up to 10) | `-t1 "FQDN:a_record:IPAddress"` |
| `-tf` | Path to a file containing a list of triples | `-tf triples.txt` |

### Data Options

| Flag | Description | Example |
|------|-------------|---------|
| `-config` | Path to the YAML configuration file | `-config config.yaml` |
| `-dir` | Path to the directory containing the graph database | `-dir /data/amass` |

### Display Options

| Flag | Description |
|------|-------------|
| `-nocolor` | Disable colorized output |
| `-silent` | Disable all output |

## Triples

A triple is a `subject:predicate:object` string used to navigate the OAM graph. Each component may be a concrete type name or a wildcard (`*`) to match any value. Multiple triples define a multi-hop walk through the graph.

```
<SubjectType>:<Predicate>:<ObjectType>
```

### Example Triples

```
FQDN:a_record:IPAddress
IPAddress:contains:Netblock
Netblock:managed_by:AutonomousSystem
```

## Examples

### Single-Hop Walk

```bash
amass assoc -dir /data/amass -t1 "FQDN:a_record:IPAddress"
```

### Multi-Hop Walk

```bash
amass assoc -dir /data/amass \
    -t1 "FQDN:a_record:IPAddress" \
    -t2 "IPAddress:contains:Netblock" \
    -t3 "Netblock:managed_by:AutonomousSystem"
```

### Triples from File

```bash
amass assoc -dir /data/amass -tf walk_triples.txt
```

### With Configuration File

```bash
amass assoc -config config.yaml -t1 "FQDN:a_record:IPAddress"
```

## Output

Results are written to stdout as pretty-printed JSON.

```json
[
  {
    "subject": "www.example.com",
    "predicate": "a_record",
    "object": "93.184.216.34"
  }
]
```

## See Also

- [enum](enum.md) - Discover assets
- [viz](viz.md) - Visualize the graph
- [subs](subs.md) - Subdomain listing

