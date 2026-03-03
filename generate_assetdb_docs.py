#!/usr/bin/env python3
"""Generate enriched asset_db documentation from DeepWiki source files."""

import re
import os

SRC_DIR = "devin_wiki_raw/pages_assetdb"
DOCS_DIR = "docs/asset_db"

# Cross-reference link map: pattern -> replacement
LINK_MAP = [
    (r'\[Getting Started\]\(#2\)', '[Getting Started](./getting-started.md)'),
    (r'\[Installation\]\(#2\.1\)', '[Installation](./getting-started.md#installation)'),
    (r'\[Database Configuration\]\(#2\.2\)', '[Database Configuration](./getting-started.md#database-configuration)'),
    (r'\[Basic Usage Examples\]\(#2\.3\)', '[Basic Usage Examples](./getting-started.md#basic-usage-examples)'),
    (r'\[Architecture\]\(#3\)', '[Architecture](./index.md#architecture)'),
    (r'\[Repository Pattern\]\(#3\.1\)', '[Repository Pattern](./index.md#repository-pattern)'),
    (r'\[Data Model\]\(#3\.2\)', '[Data Model](./index.md#data-model)'),
    (r'\[OAM Integration\]\(#3\.3\)', '[OAM Integration](./index.md#open-asset-model-integration)'),
    (r'\[Open Asset Model Integration\]\(#3\.3\)', '[Open Asset Model Integration](./index.md#open-asset-model-integration)'),
    (r'\[SQL Repository\]\(#4\)', '[SQL Repository](./postgres.md#sql-repository-implementation)'),
    (r'\[SQL Entity Operations\]\(#4\.1\)', '[SQL Entity Operations](./postgres.md#sql-entity-operations)'),
    (r'\[SQL Edge Operations\]\(#4\.2\)', '[SQL Edge Operations](./postgres.md#sql-edge-operations)'),
    (r'\[SQL Tag Management\]\(#4\.3\)', '[SQL Tag Management](./postgres.md#sql-tag-management)'),
    (r'\[Neo4j Repository\]\(#5\)', '[Neo4j Repository](./triples.md#neo4j-repository)'),
    (r'\[Neo4j Entity Operations\]\(#5\.1\)', '[Neo4j Entity Operations](./triples.md#neo4j-entity-operations)'),
    (r'\[Neo4j Edge Operations\]\(#5\.2\)', '[Neo4j Edge Operations](./triples.md#neo4j-edge-operations)'),
    (r'\[Neo4j Tag Management\]\(#5\.3\)', '[Neo4j Tag Management](./triples.md#neo4j-tag-management)'),
    (r'\[Neo4j Schema and Constraints\]\(#5\.4\)', '[Neo4j Schema and Constraints](./triples.md#neo4j-schema-and-constraints)'),
    (r'\[Caching System\]\(#6\)', '[Caching System](./caching.md)'),
    (r'\[Cache Architecture\]\(#6\.1\)', '[Cache Architecture](./caching.md#cache-architecture)'),
    (r'\[Database Migrations\]\(#7\)', '[Database Migrations](./migrations.md)'),
    (r'\[SQL Schema Migrations\]\(#7\.1\)', '[SQL Schema Migrations](./migrations.md#sql-schema-migrations)'),
    (r'\[API Reference\]\(#10\)', '[API Reference](./api-reference.md)'),
    (r'\[Repository Interface\]\(#10\.1\)', '[Repository Interface](./api-reference.md#repository-interface)'),
    (r'\[Cache Interface\]\(#10\.2\)', '[Cache Interface](./api-reference.md#cache-interface)'),
    (r'\[Core Data Types\]\(#10\.3\)', '[Core Data Types](./api-reference.md#core-data-types)'),
    # Generic numbered refs
    (r'\[Installation\]\(#2\.1\)', '[Installation](./getting-started.md#installation)'),
    (r'\[#2\.1\]', '[Installation](./getting-started.md#installation)'),
    (r'\[#2\.2\]', '[Database Configuration](./getting-started.md#database-configuration)'),
    (r'\[#2\.3\]', '[Basic Usage Examples](./getting-started.md#basic-usage-examples)'),
    (r'\[#6\]', '[Caching System](./caching.md)'),
]


def clean_content(text):
    """Clean DeepWiki source content."""
    # Remove <details>...</details> blocks
    while re.search(r'<details[\s\S]*?</details>', text):
        text = re.sub(r'<details[\s\S]*?</details>', '', text)
    # Remove Sources: lines and **Sources:** lines
    text = re.sub(r'^Sources:.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\*Sources:\*\*.*$', '', text, flags=re.MULTILINE)
    # Remove [filename.ext:N-M]() style links
    text = re.sub(
        r'\[[^\]]*\.(?:go|py|ts|js|sql|sh|yaml|yml|toml|json):[^\]]*\]\([^\)]*\)',
        '', text
    )
    # Remove standalone file links like [db.go]() or [repository/repository.go]()
    text = re.sub(
        r'\[[^\]]*\.(?:go|py|ts|js|sql|sh|yaml|yml|toml|json)\]\(\)',
        '', text
    )
    # Fix cross-references
    for pattern, replacement in LINK_MAP:
        text = re.sub(pattern, replacement, text)
    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def remove_duplicate_h1(text):
    """Remove duplicate H1 heading (DeepWiki puts title twice)."""
    lines = text.split('\n')
    # Find first H1
    first_h1_idx = None
    for i, line in enumerate(lines):
        if line.startswith('# ') and first_h1_idx is None:
            first_h1_idx = i
        elif line.startswith('# ') and first_h1_idx is not None:
            # Check if they're close (within 3 lines)
            if i - first_h1_idx <= 3:
                # Remove the first one
                lines[first_h1_idx] = ''
            break
    return '\n'.join(lines)


def read_source(filename):
    """Read and clean a source file."""
    path = os.path.join(SRC_DIR, filename)
    with open(path, 'r') as f:
        text = f.read()
    text = remove_duplicate_h1(text)
    return clean_content(text)


def strip_h1(text):
    """Remove the H1 heading from a piece of content (for embedding as subsection)."""
    lines = text.split('\n')
    result = []
    skipped = False
    for line in lines:
        if not skipped and line.startswith('# '):
            skipped = True
            continue
        result.append(line)
    return '\n'.join(result).lstrip('\n')


def downgrade_headings(text, levels=1):
    """Downgrade all headings by `levels` (e.g., # -> ##, ## -> ###)."""
    lines = text.split('\n')
    result = []
    for line in lines:
        if line.startswith('#'):
            # Count leading #
            m = re.match(r'^(#+)(.*)', line)
            if m:
                hashes = m.group(1)
                rest = m.group(2)
                new_hashes = '#' * (len(hashes) + levels)
                line = new_hashes + rest
        result.append(line)
    return '\n'.join(result)


def update_index_md():
    """Update docs/asset_db/index.md with architecture section."""
    index_path = os.path.join(DOCS_DIR, 'index.md')
    with open(index_path, 'r') as f:
        existing = f.read()

    # Read source content
    src1 = read_source('1.md')
    src3 = read_source('3.md')
    src31 = read_source('3.1.md')
    src32 = read_source('3.2.md')
    src33 = read_source('3.3.md')

    # Extract specific sections from 1.md
    def extract_section(text, heading):
        """Extract a section by heading."""
        pattern = rf'(^{re.escape(heading)}.*?)(?=^##|\Z)'
        m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return ''

    # From 1.md: Purpose and Scope, Role in ecosystem, Core Features
    src1_body = strip_h1(src1)
    # Extract purpose/scope, role, core features
    purpose_section = extract_section(src1_body, '## Purpose and Scope')
    role_section = extract_section(src1_body, '## Role in the OWASP Amass Ecosystem')
    features_section = extract_section(src1_body, '## Core Features')

    # From 3.md: layered architecture diagram + design patterns
    src3_body = strip_h1(src3)
    arch_overview = extract_section(src3_body, '## Architectural Overview')
    design_patterns = extract_section(src3_body, '## Design Patterns')

    # From 3.1.md: Repository Pattern - interface tables
    src31_body = strip_h1(src31)
    # Just take the interface definition section
    repo_interface = extract_section(src31_body, '## Interface Definition')
    factory_pattern = extract_section(src31_body, '## Factory Pattern Implementation')

    # From 3.2.md: classDiagram Mermaid blocks and type tables
    src32_body = strip_h1(src32)

    # From 3.3.md: OAM integration
    src33_body = strip_h1(src33)

    # Build the architecture section
    arch_section = """## Architecture

""" + (purpose_section + '\n\n' if purpose_section else '') + \
(role_section + '\n\n' if role_section else '') + \
(features_section + '\n\n' if features_section else '') + \
"""### Layered Architecture

""" + arch_overview + """

### Design Patterns

""" + design_patterns + """

### Repository Pattern

""" + repo_interface + """

""" + factory_pattern + """

### Data Model

""" + src32_body + """

### Open Asset Model Integration

""" + src33_body

    # Clean up triple blank lines
    arch_section = re.sub(r'\n{3,}', '\n\n', arch_section)

    # Update Next Steps section
    new_next_steps = """## :material-page-next: Next Steps

- [Getting Started](getting-started.md) — installation and quick start guide
- [PostgreSQL Setup](postgres.md) — production PostgreSQL setup guide
- [Triples Query Language](triples.md) — traverse the asset graph with subject-predicate-object queries
- [Caching](caching.md) — performance caching layer
- [Database Migrations](migrations.md) — schema management
- [API Reference](api-reference.md) — complete API documentation"""

    # Replace the existing Next Steps section
    existing = re.sub(
        r'## :material-page-next: Next Steps.*?(?=\n---|\Z)',
        new_next_steps + '\n\n',
        existing,
        flags=re.DOTALL
    )

    # Insert architecture section before the footer
    footer = '*© 2025 Jeff Foley — Licensed under Apache 2.0.*'
    if footer in existing:
        existing = existing.replace(
            footer,
            arch_section + '\n\n---\n\n' + footer
        )
    else:
        existing = existing.rstrip() + '\n\n' + arch_section

    with open(index_path, 'w') as f:
        f.write(existing)
    print(f"Updated {index_path}")


def update_postgres_md():
    """Update docs/asset_db/postgres.md with SQL repository sections."""
    path = os.path.join(DOCS_DIR, 'postgres.md')
    with open(path, 'r') as f:
        existing = f.read()

    src4 = read_source('4.md')
    src41 = read_source('4.1.md')
    src42 = read_source('4.2.md')
    src43 = read_source('4.3.md')
    src71 = read_source('7.1.md')

    def make_subsection(src, h2_title):
        """Convert a source file's content to a subsection under h2_title."""
        body = strip_h1(src)
        # Downgrade headings so ## -> ###
        body = downgrade_headings(body, levels=1)
        return f'### {h2_title}\n\n' + body.lstrip()

    sql_repo_section = """## SQL Repository Implementation

""" + strip_h1(downgrade_headings(src4, 0)) + """

""" + make_subsection(src41, 'SQL Entity Operations') + """

""" + make_subsection(src42, 'SQL Edge Operations') + """

""" + make_subsection(src43, 'SQL Tag Management')

    migrations_section = """## Database Schema & Migrations

""" + strip_h1(src71)

    new_content = sql_repo_section + '\n\n' + migrations_section
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)

    existing = existing.rstrip() + '\n\n' + new_content + '\n'

    with open(path, 'w') as f:
        f.write(existing)
    print(f"Updated {path}")


def update_triples_md():
    """Update docs/asset_db/triples.md with Neo4j sections."""
    path = os.path.join(DOCS_DIR, 'triples.md')
    with open(path, 'r') as f:
        existing = f.read()

    src5 = read_source('5.md')
    src51 = read_source('5.1.md')
    src52 = read_source('5.2.md')
    src53 = read_source('5.3.md')
    src54 = read_source('5.4.md')

    def make_subsection(src, h3_title):
        body = strip_h1(src)
        body = downgrade_headings(body, levels=1)
        return f'### {h3_title}\n\n' + body.lstrip()

    neo4j_section = """## Neo4j Repository

""" + strip_h1(src5) + """

""" + make_subsection(src51, 'Neo4j Entity Operations') + """

""" + make_subsection(src52, 'Neo4j Edge Operations') + """

""" + make_subsection(src53, 'Neo4j Tag Management') + """

""" + make_subsection(src54, 'Neo4j Schema and Constraints')

    neo4j_section = re.sub(r'\n{3,}', '\n\n', neo4j_section)
    existing = existing.rstrip() + '\n\n' + neo4j_section + '\n'

    with open(path, 'w') as f:
        f.write(existing)
    print(f"Updated {path}")


def create_getting_started():
    """Create docs/asset_db/getting-started.md."""
    path = os.path.join(DOCS_DIR, 'getting-started.md')

    src2 = read_source('2.md')
    src21 = read_source('2.1.md')
    src22 = read_source('2.2.md')
    src23 = read_source('2.3.md')

    intro = strip_h1(src2)
    install = strip_h1(src21)
    config = strip_h1(src22)
    usage = strip_h1(src23)

    content = f"""# Getting Started with Asset DB

{intro}

## Installation

{install}

## Database Configuration

{config}

## Basic Usage Examples

{usage}

## See Also

- [Asset Database Overview](./index.md)
- [PostgreSQL Setup](./postgres.md)
- [Caching](./caching.md)
- [API Reference](./api-reference.md)
"""
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_caching():
    """Create docs/asset_db/caching.md."""
    path = os.path.join(DOCS_DIR, 'caching.md')

    src6 = read_source('6.md')
    src61 = read_source('6.1.md')

    intro = strip_h1(src6)
    arch = strip_h1(src61)

    content = f"""# Caching System

{intro}

## Cache Architecture

{arch}

## See Also

- [Asset Database Overview](./index.md)
- [API Reference](./api-reference.md)
"""
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_migrations():
    """Create docs/asset_db/migrations.md."""
    path = os.path.join(DOCS_DIR, 'migrations.md')

    src7 = read_source('7.md')
    src71 = read_source('7.1.md')

    intro = strip_h1(src7)
    schema = strip_h1(src71)

    content = f"""# Database Migrations

{intro}

## SQL Schema Migrations

{schema}

## See Also

- [Asset Database Overview](./index.md)
- [PostgreSQL Setup](./postgres.md)
"""
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def create_api_reference():
    """Create docs/asset_db/api-reference.md."""
    path = os.path.join(DOCS_DIR, 'api-reference.md')

    src10 = read_source('10.md')
    src101 = read_source('10.1.md')
    src102 = read_source('10.2.md')
    src103 = read_source('10.3.md')

    intro = strip_h1(src10)
    repo_iface = strip_h1(src101)
    cache_iface = strip_h1(src102)
    data_types = strip_h1(src103)

    content = f"""# API Reference

{intro}

## Repository Interface

{repo_iface}

## Cache Interface

{cache_iface}

## Core Data Types

{data_types}

## See Also

- [Architecture](./index.md#architecture)
- [Caching](./caching.md)
- [Getting Started](./getting-started.md)
"""
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(path, 'w') as f:
        f.write(content)
    print(f"Created {path}")


def update_zensical_toml():
    """Add new nav entries to zensical.toml under asset_db section."""
    toml_path = 'zensical.toml'
    with open(toml_path, 'r') as f:
        content = f.read()

    # Find the asset_db nav section and add new entries after Triples
    old_nav = '{ "Triples" = "asset_db/triples.md" },'
    new_nav = '''{ "Triples" = "asset_db/triples.md" },
    { "Getting Started" = "asset_db/getting-started.md" },
    { "Caching" = "asset_db/caching.md" },
    { "Migrations" = "asset_db/migrations.md" },
    { "API Reference" = "asset_db/api-reference.md" },'''

    if old_nav in content and '{ "Getting Started" = "asset_db/getting-started.md" }' not in content:
        content = content.replace(old_nav, new_nav)
        with open(toml_path, 'w') as f:
            f.write(content)
        print(f"Updated {toml_path}")
    else:
        print(f"zensical.toml already updated or pattern not found")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Generating asset_db documentation...")
    update_index_md()
    update_postgres_md()
    update_triples_md()
    create_getting_started()
    create_caching()
    create_migrations()
    create_api_reference()
    update_zensical_toml()
    print("Done!")
