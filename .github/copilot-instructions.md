# Copilot Instructions

## What this repo is

This is the **documentation site** for the [OWASP Amass](https://github.com/owasp-amass/amass) project — a static site built with [Zensical](https://zensical.org). It is **not** the Amass Go source code; that lives in a separate repository.

## Build and serve

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Local dev server (http://127.0.0.1:8000)
zensical serve

# Build static site to site/
zensical build
```

If `.venv/` doesn't exist yet:
```bash
python -m venv .venv
source .venv/bin/activate
pip install zensical
```

There are no automated tests. CI runs `zensical build` on PRs and deploys to GitHub Pages on push to `main`.

## Configuration

**`zensical.toml` is the primary config.** `mkdocs.yml` is kept for legacy reference only — do not edit it.

- Site nav is defined in the `nav` array inside `zensical.toml` (TOML array-of-table format)
- Adding a new page requires both creating the `.md` file under `docs/` and adding a nav entry in `zensical.toml`
- Custom CSS lives in `stylesheets/extra.css` (referenced as `docs/stylesheets/extra.css` in the built site)

## Docs structure

```
docs/
├── index.md                    # Homepage with installation instructions
├── architecture/               # Engine internals: plugins, data-flow, DNS, sessions
├── cli/                        # Command reference: enum, engine, subs, assoc, track, viz
├── configuration/              # Config file format, data sources, transformations
├── asset_db/                   # SQLite/PostgreSQL asset database
├── open_asset_model/
│   ├── assets/                 # One .md per OAM asset type (FQDN, IPAddress, etc.)
│   ├── relations/              # One .md per relation type
│   └── properties/             # One .md per property type
├── data_sources/               # 40+ data source plugin descriptions
├── dashboards/                 # Grafana/visualization dashboards
├── changelog/
└── contributing/
```

## Markdown conventions

Pages use the full pymdownx extension suite configured in `zensical.toml`. Common patterns:

- **Admonitions**: `!!! info "Title"`, `!!! warning`, `??? info "Collapsible"`
- **Code annotations**: numbered callouts inside fenced blocks with `# (1)!` syntax
- **Mermaid diagrams**: fenced blocks with ` ```mermaid ` — supported natively
- **Grid cards**: `<div class="grid cards" markdown>` with `-` list items
- **Icon syntax**: `:material-icon-name:`, `:fontawesome-brands-github:`, `:simple-owasp:`
- **Tabbed content**: `=== "Tab name"` blocks using `pymdownx.tabbed`

## OAM reference pages

Each asset type, relation, and property under `open_asset_model/` follows a consistent pattern: description, properties/fields table, usage examples. When adding a new OAM entity, follow the structure of an existing sibling file (e.g., `open_asset_model/assets/fqdn.md`).

## Deployment

Push to `main` triggers `.github/workflows/docs.yml`, which builds with `zensical build` and deploys `site/` to GitHub Pages at `https://owasp-amass.github.io/docs/`. PRs only run the build step (no deploy).
