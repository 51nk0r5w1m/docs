# Docker Deployment

---

## Docker Container Overview

The asset-db project provides a Docker container that packages a PostgreSQL database pre-configured for use with OWASP Amass. The container is based on the official `postgres:latest` image and includes automatic initialization scripts that set up the required database, user, extensions, and custom functions.

**Key Features:**

- **Automated Setup**: Database and user creation during container startup
- **pg_trgm Extension**: PostgreSQL trigram matching for efficient text search operations
- **Custom DNS Query Function**: The `names_to_addrs` function for optimized DNS relationship traversal
- **Health Monitoring**: Built-in health checks for container orchestration
- **UTC Timezone**: Database configured with UTC timezone for consistent timestamp handling

**Sources:** [Dockerfile:1-9](), 

---

## Dockerfile Structure

The Dockerfile defines a minimal PostgreSQL container with custom initialization logic.

### Container Configuration Diagram

```mermaid
graph TB
    BaseImage["postgres:latest<br/>Official PostgreSQL Image"]
    InitDir["/docker-entrypoint-initdb.d/<br/>Initialization Script Directory"]
    InitScript["1_assetdb.sh<br/>Database Setup Script"]
    HealthCheck["pg_isready<br/>Health Check Command"]
    Port5432["Port 5432<br/>PostgreSQL Default Port"]
    
    BaseImage -->|"Creates"| InitDir
    InitScript -->|"Copied to"| InitDir
    BaseImage -->|"Configured with"| HealthCheck
    BaseImage -->|"Exposes"| Port5432
    
    InitScript -->|"Executes on<br/>first startup"| InitDir
```

**Sources:** [Dockerfile:1-9]()

### Dockerfile Components

| Component | Configuration | Purpose |
|-----------|--------------|---------|
| **Base Image** | `postgres:latest` | Official PostgreSQL image with latest stable version |
| **Init Directory** | `/docker-entrypoint-initdb.d/` | PostgreSQL's automatic initialization script directory |
| **Init Script** | `1_assetdb.sh` | Asset-db specific setup (database, user, extensions, functions) |
| **Stop Signal** | `SIGINT` | Graceful shutdown signal |
| **Port** | `5432` | Standard PostgreSQL port |
| **Health Check** | `pg_isready -U postgres -d postgres` | Runs every 5 seconds with 10 retries |

The initialization script is named `1_assetdb.sh` to ensure it runs first if multiple initialization scripts are present. The script receives execute permissions via `chmod +x` [Dockerfile:4]().

**Sources:** [Dockerfile:1-9]()

---

## Database Initialization Process

The `initdb-assetdb.sh` script executes automatically when the PostgreSQL container starts for the first time. It performs a series of setup operations using environment variables for configuration.

### Initialization Sequence

```mermaid
sequenceDiagram
    participant Docker as Docker Engine
    participant PG as PostgreSQL Container
    participant InitScript as initdb-assetdb.sh
    participant DB as PostgreSQL Server
    
    Docker->>PG: Start container (first run)
    PG->>InitScript: Execute /docker-entrypoint-initdb.d/1_assetdb.sh
    
    Note over InitScript: Read environment variables:<br/>AMASS_DB, AMASS_USER, AMASS_PASSWORD
    
    InitScript->>DB: CREATE DATABASE :assetdb
    InitScript->>DB: ALTER DATABASE SET timezone TO 'UTC'
    InitScript->>DB: CREATE USER :username WITH PASSWORD
    
    Note over InitScript: Connect to new asset-db database
    
    InitScript->>DB: CREATE EXTENSION pg_trgm
    InitScript->>DB: GRANT USAGE ON SCHEMA public
    InitScript->>DB: GRANT CREATE ON SCHEMA public
    InitScript->>DB: GRANT ALL ON ALL TABLES
    
    InitScript->>DB: CREATE FUNCTION names_to_addrs(...)
    
    DB-->>PG: Initialization complete
    PG-->>Docker: Container ready
```


### Environment Variables

The initialization script requires the following environment variables:

| Variable | Purpose | Used In |
|----------|---------|---------|
| `POSTGRES_USER` | PostgreSQL superuser (typically `postgres`) | Database and user creation |
| `AMASS_DB` | Name of the asset-db database to create | Database creation |
| `AMASS_USER` | Username for the Amass application | User creation and privilege grants |
| `AMASS_PASSWORD` | Password for the Amass user | User authentication |

**Password Handling:** The script wraps `AMASS_PASSWORD` in single quotes and stores it in `TEMPPASS`  to properly escape special characters in the password.


### Database Setup Operations

The script performs two `psql` invocations:

1. **Database and User Creation** :
   - Uses `\getenv` to safely inject environment variables into SQL
   - Creates the database specified in `AMASS_DB`
   - Sets database timezone to UTC for consistent timestamp handling
   - Creates the Amass user with the specified password

2. **Extensions and Privileges** :
   - Connects to the newly created database
   - Installs `pg_trgm` extension for trigram-based text search
   - Grants schema privileges (USAGE, CREATE) to the Amass user
   - Grants all privileges on existing tables to the Amass user
   - Creates the `names_to_addrs` custom function


---

## The names_to_addrs Function

The `names_to_addrs` function is a custom PostgreSQL stored procedure that efficiently resolves FQDNs to IP addresses by traversing DNS relationship edges in the asset database. This function is particularly useful for OWASP Amass queries that need to correlate domain names with their resolved IP addresses within a specific time window.

### Function Signature

```sql
names_to_addrs(TEXT, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE) 
RETURNS TABLE(fqdn TEXT, ip_addr TEXT)
```

**Parameters:**
- **Parameter 1 (TEXT)**: Comma-separated list of FQDNs to resolve
- **Parameter 2 (TIMESTAMP)**: Start time (`_from`) for filtering relationships
- **Parameter 3 (TIMESTAMP)**: End time (`_to`) for filtering relationships

**Returns:** A table with two columns:
- `fqdn`: The input FQDN
- `ip_addr`: The resolved IP address


### Resolution Strategy

The function implements a three-phase resolution strategy, attempting progressively more complex relationship traversals until all FQDNs are resolved or all strategies are exhausted.

```mermaid
flowchart TD
    Start["Input: Comma-separated FQDNs<br/>Time window: _from to _to"]
    ParseNames["Parse input into _names array"]
    
    Phase1["Phase 1: Indirect DNS Resolution<br/>(SRV, MX, NS records)"]
    Phase1Query["Query: FQDN → Service Record → IP<br/>Join entities and edges tables<br/>Filter by record types: 33, 2, 15<br/>Then A/AAAA record types: 1, 28"]
    Phase1Remove["Remove resolved names from _names array"]
    
    Phase2["Phase 2: Direct A/AAAA Resolution"]
    Phase2Query["Query: FQDN → IP (direct)<br/>Join entities and edges tables<br/>Filter by record types: 1, 28"]
    Phase2Remove["Remove resolved names from _names array"]
    
    Phase3["Phase 3: CNAME Traversal"]
    Phase3Loop["For each remaining name in _names"]
    Phase3Recursive["Recursive CTE: traverse_cname<br/>Follow CNAME chain (record type 5)<br/>Find terminal A/AAAA records"]
    Phase3Return["Return FQDN → IP mappings"]
    
    End["Output: Table of fqdn, ip_addr pairs"]
    
    Start --> ParseNames
    ParseNames --> Phase1
    Phase1 --> Phase1Query
    Phase1Query --> Phase1Remove
    Phase1Remove --> Phase2
    
    Phase2 --> Phase2Query
    Phase2Query --> Phase2Remove
    Phase2Remove --> Phase3
    
    Phase3 --> Phase3Loop
    Phase3Loop --> Phase3Recursive
    Phase3Recursive --> Phase3Return
    Phase3Return --> End
```


### Phase 1: Indirect DNS Resolution via Service Records

The first phase handles FQDNs that resolve through intermediate service records (SRV, MX, NS).

**Query Pattern:**
```
FQDN (entity) → [DNS relation] → Service FQDN (entity) → [DNS relation] → IP Address (entity)
```

**Implementation Details:**
- Performs a four-way join across `entities` and `edges` tables 
- First hop: Filters for DNS record types 33 (SRV), 2 (NS), or 15 (MX) 
- Second hop: Filters for A (type 1) or AAAA (type 28) records 
- Applies time window filter: `r1.updated_at >= _from AND r1.updated_at <= _to` 
- Removes resolved FQDNs from the `_names` array using `array_remove()` 


### Phase 2: Direct A/AAAA Resolution

The second phase handles FQDNs that directly resolve to IP addresses without intermediate service records.

**Query Pattern:**
```
FQDN (entity) → [BasicDNSRelation] → IP Address (entity)
```

**Implementation Details:**
- Performs a three-way join: `entities (fqdns)` → `edges` → `entities (ips)` 
- Filters for `BasicDNSRelation` edges with label `'dns_record'` 
- Matches only A (type 1) or AAAA (type 28) records 
- Applies time window filter 
- Removes resolved FQDNs from the `_names` array 


### Phase 3: CNAME Chain Traversal

The final phase handles FQDNs that require following CNAME chains to reach the final IP address.

**Query Pattern:**
```
FQDN → CNAME → CNAME → ... → FQDN → IP Address
```

**Implementation Details:**
- Iterates over remaining unresolved FQDNs using `FOREACH _name IN ARRAY _names` 
- Uses a recursive Common Table Expression (CTE) named `traverse_cname` 
- The CTE recursively follows CNAME records (type 5) 
- Base case: Starts with the input FQDN 
- Recursive case: Finds CNAME targets and adds them to the traversal 
- Terminal case: Queries for A/AAAA records from any FQDN in the CNAME chain 
- Returns results with the original input FQDN, not the resolved CNAME target 


### Function Characteristics

The function is declared with the following characteristics :

- **`IMMUTABLE`**: Result depends only on input parameters, not database state
- **`STRICT`**: Returns NULL if any parameter is NULL (PostgreSQL automatically handles this)
- **Language**: `plpgsql` (PostgreSQL procedural language)

These characteristics enable PostgreSQL's query optimizer to cache and optimize function calls.


---

## Using the Docker Container

### Building the Container

```bash
docker build -t asset-db-postgres .
```

This builds the container using the `Dockerfile` in the current directory and tags it as `asset-db-postgres`.

**Sources:** [Dockerfile:1-9]()

### Running the Container

```bash
docker run -d \
  --name asset-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres_admin_password \
  -e AMASS_DB=asset_db \
  -e AMASS_USER=amass \
  -e AMASS_PASSWORD=amass_secure_password \
  -p 5432:5432 \
  asset-db-postgres
```

**Environment Variables Explained:**

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL superuser (required by base image) |
| `POSTGRES_PASSWORD` | `postgres_admin_password` | Superuser password (required by base image) |
| `AMASS_DB` | `asset_db` | Name of the database to create for asset-db |
| `AMASS_USER` | `amass` | Username that the application will use |
| `AMASS_PASSWORD` | `amass_secure_password` | Password for the application user |


### Health Check Verification

The container includes a health check that runs every 5 seconds [Dockerfile:7-8]():

```bash
# Check container health status
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' asset-db | jq
```

The health check uses `pg_isready -U postgres -d postgres` to verify that PostgreSQL is accepting connections.

**Sources:** [Dockerfile:7-8]()

### Connecting to the Database

Once the container is running and healthy, connect using the application credentials:

```bash
# Using psql
psql -h localhost -p 5432 -U amass -d asset_db

# Connection string format for asset-db
postgres://amass:amass_secure_password@localhost:5432/asset_db?sslmode=disable
```

For programmatic access from the asset-db library, use `assetdb.New()` with the connection string:

```go
repo, err := assetdb.New("postgres", 
    "host=localhost port=5432 user=amass password=amass_secure_password dbname=asset_db sslmode=disable")
```


### Docker Compose Integration

For production deployments, consider using Docker Compose with volume persistence:

```yaml
version: '3.8'
services:
  postgres:
    build: .
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      AMASS_DB: asset_db
      AMASS_USER: amass
      AMASS_PASSWORD: ${AMASS_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres", "-d", "postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres-data:
```

**Sources:** [Dockerfile:7-8](), 

---

## Container Initialization Flow

The complete container startup and initialization process follows this sequence:

```mermaid
sequenceDiagram
    participant User as User/Orchestrator
    participant Docker as Docker Engine
    participant PGContainer as PostgreSQL Container
    participant PGServer as PostgreSQL Server
    participant InitScript as 1_assetdb.sh
    
    User->>Docker: docker run with environment variables
    Docker->>PGContainer: Start container
    PGContainer->>PGServer: Start PostgreSQL daemon
    
    Note over PGContainer: Check /docker-entrypoint-initdb.d/
    
    PGContainer->>InitScript: Execute initialization scripts
    
    InitScript->>InitScript: Export TEMPPASS='$AMASS_PASSWORD'
    InitScript->>PGServer: psql as POSTGRES_USER
    InitScript->>PGServer: CREATE DATABASE :assetdb
    InitScript->>PGServer: ALTER DATABASE SET timezone TO 'UTC'
    InitScript->>PGServer: CREATE USER :username WITH PASSWORD
    
    InitScript->>PGServer: psql --dbname AMASS_DB
    InitScript->>PGServer: CREATE EXTENSION pg_trgm
    InitScript->>PGServer: GRANT privileges to AMASS_USER
    InitScript->>PGServer: CREATE FUNCTION names_to_addrs(...)
    
    PGServer-->>InitScript: All operations successful
    InitScript-->>PGContainer: Exit 0
    
    PGContainer->>PGContainer: Run health check
    PGContainer->>PGServer: pg_isready -U postgres -d postgres
    PGServer-->>PGContainer: Ready
    
    PGContainer-->>Docker: Container healthy
    Docker-->>User: Container ready for connections
```

**Sources:** [Dockerfile:1-9](), 

---

## Summary

The Docker deployment provides a turnkey PostgreSQL database configured specifically for asset-db usage. The key components are:

1. **Dockerfile**: Minimal configuration extending `postgres:latest`
2. **Initialization Script**: Automated setup of database, user, extensions, and custom functions
3. **Health Checks**: Built-in monitoring for container orchestration
4. **names_to_addrs Function**: Optimized DNS relationship traversal for OWASP Amass queries

This container is production-ready and includes all necessary extensions and functions for efficient asset graph storage and querying.

**Sources:** [Dockerfile:1-9](),

## PostgreSQL Docker Container

### Dockerfile Configuration

The asset-db PostgreSQL container is built using the official PostgreSQL base image with a custom initialization script.

**Container Specification**

| Component | Value | Purpose |
|-----------|-------|---------|
| Base Image | `postgres:latest` | Official PostgreSQL Docker image |
| Init Script | `/docker-entrypoint-initdb.d/1_assetdb.sh` | Automatic database setup on first run |
| Exposed Port | `5432` | Standard PostgreSQL port |
| Stop Signal | `SIGINT` | Graceful shutdown signal |
| Health Check | `pg_isready -U postgres -d postgres` | Every 5s with 10 retries |

The Dockerfile [Dockerfile:1-9]() performs the following operations:

1. Creates the initialization directory [Dockerfile:2]()
2. Copies the initialization script [Dockerfile:3]()
3. Makes the script executable [Dockerfile:4]()
4. Configures health checking and networking [Dockerfile:5-8]()

**Sources:** [Dockerfile:1-9]()

---

### Container Initialization Flow

The PostgreSQL container automatically executes scripts in `/docker-entrypoint-initdb.d/` on first startup. The asset-db initialization follows a specific sequence.

**Initialization Sequence Diagram**

```mermaid
sequenceDiagram
    participant Docker as "Docker Engine"
    participant PG as "postgres:latest<br/>Container"
    participant InitScript as "1_assetdb.sh"
    participant PSQL as "psql Client"
    participant DB as "PostgreSQL Server"

    Docker->>PG: "Start container"
    PG->>PG: "Initialize PostgreSQL server"
    PG->>InitScript: "Execute /docker-entrypoint-initdb.d/1_assetdb.sh"
    
    InitScript->>InitScript: "Process environment variables<br/>AMASS_PASSWORD, AMASS_USER, AMASS_DB"
    
    InitScript->>PSQL: "Connect as POSTGRES_USER"
    PSQL->>DB: "CREATE DATABASE :assetdb"
    DB-->>PSQL: "Database created"
    
    PSQL->>DB: "ALTER DATABASE SET timezone TO 'UTC'"
    DB-->>PSQL: "Timezone configured"
    
    PSQL->>DB: "CREATE USER :username WITH PASSWORD"
    DB-->>PSQL: "User created"
    
    InitScript->>PSQL: "Connect to AMASS_DB"
    PSQL->>DB: "CREATE EXTENSION pg_trgm"
    DB-->>PSQL: "Extension installed"
    
    PSQL->>DB: "GRANT privileges to AMASS_USER"
    DB-->>PSQL: "Privileges granted"
    
    PSQL->>DB: "CREATE FUNCTION names_to_addrs(...)"
    DB-->>PSQL: "Function created"
    
    InitScript-->>PG: "Initialization complete"
    PG-->>Docker: "Container ready"
```

**Sources:** [Dockerfile:1-9](), 

---

### Environment Variables

The initialization script requires specific environment variables to configure the database and user credentials.

**Required Environment Variables**

| Variable | Purpose | Used In |
|----------|---------|---------|
| `POSTGRES_USER` | PostgreSQL superuser (default: `postgres`) | Database creation context |
| `AMASS_DB` | Name of the asset-db database to create | Target database name |
| `AMASS_USER` | Asset-db application username | Database user to create |
| `AMASS_PASSWORD` | Password for `AMASS_USER` | User authentication |

The script uses PostgreSQL's `\getenv` meta-command to read environment variables into psql variables , and wraps the password in single quotes to handle special characters .


---

### Database and User Provisioning

The first phase of initialization creates the database and user with appropriate configuration.

**Database Creation Process**

```mermaid
flowchart TD
    Start["Start: initdb-assetdb.sh"]
    WrapPass["Wrap AMASS_PASSWORD<br/>in single quotes<br/>(line 5)"]
    ConnectSuper["Connect as POSTGRES_USER<br/>(line 8)"]
    LoadEnv["Load environment variables<br/>AMASS_DB, AMASS_USER, TEMPPASS<br/>(lines 9-11)"]
    CreateDB["CREATE DATABASE :assetdb<br/>(line 12)"]
    SetTZ["ALTER DATABASE SET timezone TO 'UTC'<br/>(line 13)"]
    CreateUser["CREATE USER :username<br/>WITH PASSWORD :password<br/>(line 14)"]
    Phase2["Proceed to extension<br/>and permissions phase"]
    
    Start --> WrapPass
    WrapPass --> ConnectSuper
    ConnectSuper --> LoadEnv
    LoadEnv --> CreateDB
    CreateDB --> SetTZ
    SetTZ --> CreateUser
    CreateUser --> Phase2
```

The database is configured with UTC timezone to ensure consistent timestamp handling across the distributed Amass system .


---

### PostgreSQL Extensions and Permissions

After database creation, the script installs the `pg_trgm` extension and grants necessary privileges to the application user.

**Extension and Permission Setup**

The second psql session connects to the newly created database :

| Operation | Command | Purpose |
|-----------|---------|---------|
| Install trigram extension | `CREATE EXTENSION pg_trgm SCHEMA public` | Enables fuzzy text matching for content searches |
| Grant schema usage | `GRANT USAGE ON SCHEMA public` | Allow user to access public schema |
| Grant schema creation | `GRANT CREATE ON SCHEMA public` | Allow user to create objects (migrations) |
| Grant table access | `GRANT ALL ON ALL TABLES IN SCHEMA public` | Full access to existing tables |

The `pg_trgm` extension  is critical for the SQL repository's content-based entity search operations, enabling efficient similarity matching on JSON content fields using trigram indexes.


---

### The names_to_addrs Function

The initialization script creates a custom PL/pgSQL function `names_to_addrs` that performs complex DNS resolution queries across the entity-edge graph structure.

#### Function Signature

```
names_to_addrs(TEXT, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE)
RETURNS TABLE(fqdn TEXT, ip_addr TEXT)
```

**Parameters:**
- `$1` (TEXT): Comma-separated list of FQDN names to resolve
- `$2` (TIMESTAMP): Start of time range (`_from`)
- `$3` (TIMESTAMP): End of time range (`_to`)

**Returns:** Table with columns `fqdn` and `ip_addr`


---

#### Function Logic Overview

The `names_to_addrs` function implements a three-phase DNS resolution strategy to find IP addresses for given FQDNs.

**Resolution Strategy Diagram**

```mermaid
flowchart TD
    Input["Input: Comma-separated FQDNs<br/>Time range: _from to _to"]
    Parse["Parse input into _names array<br/>(line 36)"]
    
    Phase1["Phase 1: SRV/MX/NS Records<br/>(lines 38-56)"]
    Phase1Query["Query: FQDN → Server FQDN → IP<br/>Join: fqdns → r1 → srvs → r2 → ips<br/>Filter: r1.rr_type IN (33,2,15)<br/>r2.rr_type IN (1,28)"]
    Phase1Remove["Remove resolved names from _names"]
    
    Phase2["Phase 2: Direct A/AAAA Records<br/>(lines 58-71)"]
    Phase2Query["Query: FQDN → IP<br/>Join: fqdns → edges → ips<br/>Filter: edges.rr_type IN (1,28)"]
    Phase2Remove["Remove resolved names from _names"]
    
    Phase3["Phase 3: CNAME Resolution<br/>(lines 73-98)"]
    Phase3Loop["For each remaining name"]
    Phase3CTE["Recursive CTE: traverse_cname<br/>Follow CNAME chain (rr_type=5)<br/>(lines 75-85)"]
    Phase3Query["Query final A/AAAA records<br/>from CTE results"]
    
    Output["Output: Table of (fqdn, ip_addr) pairs"]
    
    Input --> Parse
    Parse --> Phase1
    Phase1 --> Phase1Query
    Phase1Query --> Phase1Remove
    Phase1Remove --> Phase2
    
    Phase2 --> Phase2Query
    Phase2Query --> Phase2Remove
    Phase2Remove --> Phase3
    
    Phase3 --> Phase3Loop
    Phase3Loop --> Phase3CTE
    Phase3CTE --> Phase3Query
    Phase3Query --> Output
```


---

#### Phase 1: Indirect DNS Records (SRV/MX/NS)

The first phase handles DNS records that point to an intermediate server name, which then resolves to an IP address.

**Query Structure:**

```
SELECT srvs.content->>'name' AS "name", ips.content->>'address' AS "addr"
FROM entities AS fqdns
INNER JOIN edges AS r1 ON fqdns.entity_id = r1.from_entity_id
INNER JOIN entities AS srvs ON r1.to_entity_id = srvs.entity_id
INNER JOIN edges AS r2 ON srvs.entity_id = r2.from_entity_id
INNER JOIN entities AS ips ON r2.to_entity_id = ips.entity_id
WHERE ...
```

**Join Pattern:**

```mermaid
graph LR
    FQDN["entities: fqdns<br/>(etype='FQDN')"]
    R1["edges: r1<br/>(etype IN PrefDNSRelation,SRVDNSRelation)<br/>(rr_type IN 33,2,15)"]
    SRV["entities: srvs<br/>(etype='FQDN')"]
    R2["edges: r2<br/>(etype=BasicDNSRelation)<br/>(rr_type IN 1,28)"]
    IP["entities: ips<br/>(etype='IPAddress')"]
    
    FQDN -->|"from_entity_id"| R1
    R1 -->|"to_entity_id"| SRV
    SRV -->|"from_entity_id"| R2
    R2 -->|"to_entity_id"| IP
```

**RR Types Handled:**
- **Type 33:** SRV (Service record)
- **Type 2:** NS (Name server)
- **Type 15:** MX (Mail exchange)
- **Type 1:** A (IPv4 address)
- **Type 28:** AAAA (IPv6 address)

Successfully resolved names are removed from the `_names` array  to avoid duplicate resolution in subsequent phases.


---

#### Phase 2: Direct A/AAAA Records

The second phase handles FQDNs that have direct IP address mappings without intermediate records.

**Query Structure:**

```
SELECT fqdns.content->>'name' AS "name", ips.content->>'address' AS "addr"
FROM entities AS fqdns
INNER JOIN edges ON fqdns.entity_id = edges.from_entity_id
INNER JOIN entities AS ips ON edges.to_entity_id = ips.entity_id
WHERE fqdns.etype = 'FQDN'
  AND ips.etype = 'IPAddress'
  AND edges.etype = 'BasicDNSRelation'
  AND edges.content->>'label' = 'dns_record'
  AND edges.content->'header'->'rr_type' IN ('1', '28')
  AND edges.updated_at >= _from AND edges.updated_at <= _to
  AND fqdns.content->>'name' = ANY(_names)
```

This phase uses a simpler join pattern: FQDN → Edge → IP . The time range filtering ensures only relevant DNS records are considered .


---

#### Phase 3: CNAME Chain Resolution

The final phase handles remaining FQDNs by following CNAME (canonical name) chains using a recursive Common Table Expression (CTE).

**Recursive CTE Structure:**

```mermaid
graph TD
    Base["Base Case:<br/>VALUES(_name)"]
    Recursive["Recursive Case:<br/>SELECT cnames.content->>'name'<br/>FROM fqdns → edges → cnames<br/>WHERE edges.rr_type = '5' (CNAME)"]
    Traverse["Recursive CTE: traverse_cname<br/>Accumulates all names in chain"]
    Final["Final Query:<br/>Find A/AAAA records<br/>for any name in traverse_cname"]
    
    Base --> Traverse
    Recursive --> Traverse
    Traverse --> Recursive
    Traverse --> Final
```

The CTE  recursively follows CNAME records (RR type 5) until it finds all canonical names in the chain. The final query  then searches for A/AAAA records for any name in the traversed chain.

**CNAME Resolution Logic:**

1. Start with input name 
2. Find all CNAMEs pointing from current name 
3. Add discovered names to traversal set
4. Repeat until no more CNAMEs found
5. Query A/AAAA records for entire traversal set 
6. Return results with original input name as `fqdn` 

The function maintains the original input FQDN in the result , even when resolution required following CNAME chains, providing a clear mapping from queried name to discovered IP address.


---

### Function Properties

The `names_to_addrs` function is declared with specific properties affecting its behavior and optimization:

| Property | Value | Implication |
|----------|-------|-------------|
| Language | `plpgsql` | PostgreSQL procedural language |
| Volatility | `IMMUTABLE` | Result depends only on input parameters |
| Null handling | `STRICT` | Returns NULL if any parameter is NULL |

The `IMMUTABLE` property  signals to PostgreSQL that the function's results depend solely on its input parameters, enabling query plan optimization and potential result caching. The `STRICT` property  ensures the function doesn't execute at all when given NULL inputs, preventing unnecessary processing.


---

### Container Health and Lifecycle

The Dockerfile configures health checking to ensure the container is ready before accepting connections.

**Health Check Configuration:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Command | `pg_isready -U postgres -d postgres` | Verify server accepting connections |
| Interval | 5 seconds | Frequency of health checks |
| Timeout | 5 seconds | Maximum time for check to complete |
| Retries | 10 | Attempts before marking unhealthy |

The health check [Dockerfile:7-8]() uses PostgreSQL's built-in `pg_isready` utility to verify the server is accepting connections. With the configured parameters, the container allows up to 50 seconds (10 retries × 5 second interval) for the database to become ready before marking it as unhealthy.

The `SIGINT` stop signal [Dockerfile:5]() ensures PostgreSQL receives a graceful shutdown signal, allowing it to complete transactions and properly close files before termination.

**Sources:** [Dockerfile:5-8]()

---

### Integration with Asset-DB Schema

The initialized PostgreSQL database serves as the persistent storage layer for the SQL repository implementation. The `names_to_addrs` function operates on the schema created by SQL migrations.

**Schema Dependencies:**

```mermaid
erDiagram
    entities {
        uuid entity_id PK
        string etype
        jsonb content
        timestamp created_at
        timestamp updated_at
    }
    
    edges {
        uuid edge_id PK
        uuid from_entity_id FK
        uuid to_entity_id FK
        string etype
        jsonb content
        timestamp created_at
        timestamp updated_at
    }
    
    entities ||--o{ edges : "from_entity_id"
    entities ||--o{ edges : "to_entity_id"
```

The `names_to_addrs` function queries:
- **entities table:** Stores FQDN and IPAddress nodes with JSON content 
- **edges table:** Stores DNS relationships with JSON metadata 
- **etype field:** Entity/edge type for filtering 
- **content field:** JSON data containing names, addresses, and DNS header info [initdb-assetdb.sh:39,46-48]()
- **updated_at field:** Timestamp for temporal filtering 

For detailed schema structure and migration scripts, see [SQL Schema Migrations](#7.1).
