# Multi-Domain Setup Guide

## Overview

This demo supports **multiple domains** with separate Galileo projects for each. The app automatically discovers all domains in the `domains/` directory and creates navigation pages for each.

**Benefits:**
- ✅ Separate Galileo projects per domain for better organization
- ✅ Automatic domain discovery and routing
- ✅ Independent experiments, traces, and datasets per domain
- ✅ Easy to add new domains without code changes

## Quick Start: Adding a New Domain

### Step 1: Create Domain Structure

```bash
domains/
  my_domain/
    ├── config.yaml           # Domain configuration
    ├── system_prompt.json    # System prompt
    ├── dataset.csv           # Sample test data (optional)
    ├── tools/
    │   ├── schema.json       # Tool definitions
    │   └── logic.py          # Tool implementations
    └── docs/                 # Documents for RAG (optional)
```

### Step 2: Configure Your Domain

Edit `domains/my_domain/config.yaml`:

```yaml
domain:
  name: "my_domain"
  description: "What this domain does"

# Galileo Configuration (OPTIONAL)
# If not specified, defaults to: "galileo-demo-{domain_name}"
galileo:
  project: "galileo-demo-my_domain"    # Galileo project name
  log_stream: "default"                # Log stream (optional)

ui:
  app_title: "🤖 My Domain Assistant"
  example_queries:
    - "Example query 1"
    - "Example query 2"

model:
  model_name: "gpt-4o"
  temperature: 0.7

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "my_tool_1"
  - "my_tool_2"
```

### Step 3: Done! 🎉

The app automatically:
- ✅ Discovers your new domain
- ✅ Creates a page at `/my_domain`
- ✅ Uses Galileo project: `galileo-demo-my_domain` (or your custom name)
- ✅ Sets up routing and navigation

## Galileo Project Configuration

### Default Behavior (Recommended)

**If you don't specify** `galileo.project`, the system automatically uses:

```
galileo-demo-{domain_name}
```

**Examples:**
- Domain: `finance` → Project: `galileo-demo-finance`
- Domain: `healthcare` → Project: `galileo-demo-healthcare`
- Domain: `legal` → Project: `galileo-demo-legal`

### Custom Project Names (Optional)

To use a custom project name, add the `galileo` section:

```yaml
galileo:
  project: "my-custom-project-name"
  log_stream: "custom-stream"
```

## Complete Example

```yaml
# domains/healthcare/config.yaml
domain:
  name: "healthcare"
  description: "Medical assistant"

# Optional: Use custom project name
galileo:
  project: "healthcare-prod"

ui:
  app_title: "🏥 Healthcare Assistant"
  example_queries:
    - "What are diabetes symptoms?"
    - "Explain this medical report"

model:
  model_name: "gpt-4o"
  temperature: 0.3

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "get_patient_info"
  - "schedule_appointment"

protect:
  metrics:
    - name: "input_toxicity"
      operator: "gt"
      threshold: 0.7
  messages:
    - "Cannot process harmful queries."
```

## How It Works

1. **Domain Discovery**: App scans `domains/` on startup
2. **Config Loading**: Each domain's `config.yaml` is loaded
3. **Default Domain**: Root URL (`/`) defaults to "finance" domain (or first available)
4. **Project Selection**: 
   - Uses `galileo.project` if specified
   - Otherwise defaults to `galileo-demo-{domain_name}`
5. **Environment Setup**: Sets `GALILEO_PROJECT` per domain
6. **Navigation**: Creates pages at `/{domain_name}`

## FAQ

**Q: Do I need to create the Galileo project first?**  
**A:** No! It's created automatically when you first use the domain.

**Q: Can I use the same project for multiple domains?**  
**A:** Yes, but we recommend separate projects for better organization.

**Q: Where are API keys stored?**  
**A:** In `.streamlit/secrets.toml` (shared across all domains).

## Notes

- Each domain maintains separate session state and agents
- Switching domains resets the conversation
- Experiments and datasets are scoped to each domain's project

