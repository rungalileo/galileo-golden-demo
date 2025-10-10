# Pinecone Setup Guide

This guide explains how to set up vector databases for both local and hosted environments using Pinecone.

## Overview

The system supports two Pinecone projects:
- **`galileo-demo-local`**: For local demos
  - [View Project](https://app.pinecone.io/organizations/-OXhGwcgoRgnBDSiTTTr/projects/db0e9ee6-ce44-4fa7-a9aa-ac2926064bf1/indexes)
- **`galileo-demo-hosted`**: For hosted demos
  - [View Project](https://app.pinecone.io/organizations/-OXhGwcgoRgnBDSiTTTr/projects/b8ac86ad-c718-43fa-81e2-a5c59eb5e2ee/indexes)

Each project has its own API key and indexes.

### Environment Separation

**Important**: Both environments use **cloud-hosted Pinecone indexes** - nothing is stored locally on your machine. Local in this context, is refering to local demos.

- **"local" environment**: Demos being run and developed locally on your machine
  - Uses `galileo-demo-local` Pinecone project
  - Safe for experimentation and development
  - Won't affect hosted demos

- **"hosted" environment**: Demos running on hosted platforms (like Streamlit Cloud)
  - Uses `galileo-demo-hosted` Pinecone project  
  - Stable for production demos
  - Protected from developer experiments

**Why Two Environments?**
This separation ensures that when developers experiment with RAG configurations, chunk sizes, or document updates, they don't break the hosted demos that customers and stakeholders are using. Each environment has its own isolated vector database.

## Configuration

### 1. Add API Keys and Environment to Secrets

Add both Pinecone API keys and environment setting to your `.streamlit/secrets.toml`:

```toml
# Pinecone Configuration
# Each project has its own API key, need both to create vector dbs for both local and hosted demos
pinecone_api_key_local = "your_local_project_api_key"    # For galileo-demo-local project
pinecone_api_key_hosted = "your_hosted_project_api_key"  # For galileo-demo-hosted project

# Environment Configuration
# Set to "local" for local development, "hosted" for production
environment = "local"
```

### 2. Environment Selection

The `environment` variable tells the application which Pinecone project to use for RAG:
- **`"local"`**: Uses `galileo-demo-local` project and `PINECONE_API_KEY_LOCAL`
- **`"hosted"`**: Uses `galileo-demo-hosted` project and `PINECONE_API_KEY_HOSTED`

### 3. Document Requirements

Before setting up vector databases, ensure your domain has documents in the `docs/` directory:

```
domains/finance/docs/
├── costco-10-q.pdf
├── SP500_transcripts.csv
└── other_documents.pdf
```

### 4. Set Up Vector Databases

#### For Local Development
```bash
python helpers/setup_vectordb.py finance local
```

This will:
- Process documents from `domains/finance/docs/` directory
- Use the `PINECONE_API_KEY_LOCAL` from your secrets
- Create/update index: `finance-local-index` in the `galileo-demo-local` project
- Embed and store document chunks in Pinecone for local demos

#### For Hosted/Production
```bash
python helpers/setup_vectordb.py finance hosted
```

This will:
- Process documents from `domains/finance/docs/` directory
- Use the `PINECONE_API_KEY_HOSTED` from your secrets
- Create/update index: `finance-hosted-index` in the `galileo-demo-hosted` project
- Embed and store document chunks in Pinecone for hosted demos

## Index Naming Convention

Indexes are named: `{domain}-{environment}-index`

Examples:
- `finance-local-index` (in galileo-demo-local project)
- `finance-hosted-index` (in galileo-demo-hosted project)
- `healthcare-local-index` (in galileo-demo-local project)
- `healthcare-hosted-index` (in galileo-demo-hosted project)

## Application Usage

The application automatically uses the correct Pinecone project based on the `environment` variable:

- **Local deployments**: Set `environment = "local"` → Uses `galileo-demo-local` project
- **Hosted deployments**: Set `environment = "hosted"` → Uses `galileo-demo-hosted` project

The application code uses `helpers.pinecone_utils.get_pinecone_api_key()` to automatically get the correct API key and project.

## Workflow

1. **Development**: Run `python helpers/setup_vectordb.py finance local` to build local indexes
2. **Production**: Run `python helpers/setup_vectordb.py finance hosted` to build hosted indexes
3. **Deploy**: Each environment uses its respective Pinecone project automatically

This pattern keeps local and hosted environments completely separate while using the same codebase.
