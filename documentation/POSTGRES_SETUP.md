# PostgreSQL with pgvector Setup Guide

This guide explains how to set up PostgreSQL with the pgvector extension for local and hosted demos.

## Overview

The demo uses **PostgreSQL with pgvector** for vector storage via LangChain's `PGVector` integration. Each domain/environment pair gets its own collection named `{domain}_{environment}_index` (e.g., `finance_local_index`).

## Step 1: Run PostgreSQL with pgvector in Docker

Based on the [pgvector Docker setup guide](https://medium.com/@adarsh.ajay/setting-up-postgresql-with-pgvector-in-docker-a-step-by-step-guide-d4203f6456bd):

```bash
# Pull the pgvector-enabled image
docker pull pgvector/pgvector:pg16

# Start PostgreSQL with pgvector
docker run -e POSTGRES_USER=postgres \
           -e POSTGRES_PASSWORD=mypassword \
           -e POSTGRES_DB=vectordb \
           --name golden-demo-postgres \
           -p 5432:5432 \
           -d pgvector/pgvector:pg16
```

Alternatively, using the `ankane/pgvector` image:

```bash
docker pull ankane/pgvector

docker run -e POSTGRES_USER=postgres \
           -e POSTGRES_PASSWORD=mypassword \
           -e POSTGRES_DB=vectordb \
           --name golden-demo-postgres \
           -p 5432:5432 \
           -d ankane/pgvector
```

## Step 2: Enable the pgvector Extension

Connect to the database and enable pgvector:

```bash
docker exec -it golden-demo-postgres psql -U postgres -d vectordb
```

Then run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify installation:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Step 3: Configure Secrets

Add your PostgreSQL credentials to `.streamlit/secrets.toml`:

```toml
postgres_host = "localhost"
postgres_port = "5432"
postgres_user = "postgres"
postgres_password = "mypassword"
postgres_db = "vectordb"

environment = "local"
```

## Step 4: Load Domain Documents

Run the setup script for each domain you want to use:

```bash
python helpers/setup_vectordb.py finance local
python helpers/setup_vectordb.py healthcare local
python helpers/setup_vectordb.py bank local
python helpers/setup_vectordb.py onlinestore local
```

For hosted/production demos, use `hosted` instead of `local`:

```bash
python helpers/setup_vectordb.py finance hosted
```

## Collection Naming

| Domain | Local Collection | Hosted Collection |
|--------|-----------------|-------------------|
| finance | `finance_local_index` | `finance_hosted_index` |
| healthcare | `healthcare_local_index` | `healthcare_hosted_index` |
| bank | `bank_local_index` | `bank_hosted_index` |
| onlinestore | `onlinestore_local_index` | `onlinestore_hosted_index` |

## Troubleshooting

**Connection refused**: Ensure the Docker container is running:

```bash
docker ps | grep golden-demo-postgres
```

**Extension not found**: Connect to the database and run `CREATE EXTENSION vector;`.

**Collection not found at runtime**: Re-run the setup script for that domain/environment:

```bash
python helpers/setup_vectordb.py <domain> <environment>
```

**psql not found locally**: Use `docker exec` to connect:

```bash
docker exec -it golden-demo-postgres psql -U postgres -d vectordb
```

## Stopping and Restarting

```bash
# Stop the container
docker stop golden-demo-postgres

# Start it again (data persists in the container)
docker start golden-demo-postgres

# Remove the container entirely (data will be lost)
docker rm -f golden-demo-postgres
```

For persistent data across container removals, add a volume mount:

```bash
docker run -e POSTGRES_USER=postgres \
           -e POSTGRES_PASSWORD=mypassword \
           -e POSTGRES_DB=vectordb \
           --name golden-demo-postgres \
           -p 5432:5432 \
           -v golden-demo-pgdata:/var/lib/postgresql/data \
           -d pgvector/pgvector:pg16
```
