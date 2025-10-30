# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run the main Streamlit application
streamlit run app.py

# Alternative runner
python run_streamlit.py
```

### Experiments
```bash
# Run experiment with inline test data
python experiment_cli.py --inline --experiment quick-test

# Run experiment with Galileo dataset
python experiment_cli.py --dataset-name my-dataset --experiment baseline-v1

# Create synthetic dataset
python create_synthetic_dataset.py

# Verify experiment results
python verify_experiment.py
```

### Domain Management
```bash
# Set up vector database for a new domain
python helpers/setup_vectordb.py <domain_name>

# Test vector database functionality
python helpers/test_vectordb.py
```

### Testing and Verification
```bash
# Test agent tool usage
python test_agent_tool_usage.py

# Run simple experiment test
python test_simple_experiment.py

# Verify chaos tools functionality
python verify_chaos_tools.py
```

### Live Data Setup
```bash
# Enable live stock data (optional)
./setup_live_data.sh

# Check available scorers
python check_available_scorers.py
```

## Architecture

### Core Components

**Agent Factory Pattern**: The system uses `AgentFactory` to create domain-specific agents. Each agent is built on a framework (currently LangGraph) and configured for specific domains (finance, etc.).

**Domain-Based Configuration**: All functionality is organized by domains in the `domains/` directory. Each domain contains:
- `config.yaml` - Domain settings, model config, RAG settings, available tools
- `system_prompt.json` - Agent behavior definition
- `tools/` - Domain-specific tool implementations
- `docs/` - RAG documents for knowledge retrieval
- `dataset.csv` - Optional evaluation data

**Multi-Framework Support**: Built with framework abstraction via `BaseAgent` class. Currently implements LangGraph but designed to support CrewAI, AutoGen, etc.

**Observability Integration**: Deep integration with Galileo for logging, experiments, and guardrails. OTLP tracing is initialized before LangChain imports to ensure proper instrumentation.

### Key Files

- `app.py` - Main Streamlit application with UI controls for chaos engineering, live data, and guardrails
- `agent_factory.py` - Creates and manages domain-specific agents
- `base_agent.py` - Abstract base class for all agent frameworks
- `domain_manager.py` - Handles domain discovery and configuration loading
- `tracing_setup.py` - Initializes OTLP tracing (Phoenix/Arize AX)
- `chaos_engine.py` - Chaos engineering for testing observability
- `guardrails_config.py` - Galileo Protect integration for safety

### Environment Setup

Environment variables are loaded in this order:
1. Global config: `~/.config/secrets/myapps.env`
2. Local project: `.env` file (if present)
3. Streamlit secrets: `.streamlit/secrets.toml`

Required secrets in `.streamlit/secrets.toml`:
```toml
openai_api_key = "your_key"
galileo_api_key = "your_key"
galileo_project = "project_name"
galileo_log_stream = "stream_name"
```

### RAG System

Each domain can have RAG enabled via `config.yaml`. Documents in `domains/<domain>/docs/` are automatically chunked and embedded using ChromaDB. Vector databases are persistent and only need setup once per domain.

### Chaos Engineering

The system includes built-in chaos engineering to test Galileo's observability:
- Sloppiness (number transposition)
- Tool instability (random API failures)
- RAG disconnects (vector DB failures)
- Rate limiting (API quota errors)
- Data corruption

### Guardrails Integration

Galileo Protect provides real-time content filtering:
- PII detection and blocking
- Toxicity/sexism filtering
- Trade protection with confidence scoring
- Hallucination detection

## Adding New Domains

1. Create directory structure in `domains/<new_domain>/`
2. Add `config.yaml`, `system_prompt.json`, `tools/schema.json`, `tools/logic.py`
3. Place RAG documents in `docs/` subdirectory
4. Run `python helpers/setup_vectordb.py <new_domain>` to create vector database
5. Update `DOMAIN` variable in `app.py` (temporary until multi-domain UI complete)

Tool implementations in `tools/logic.py` should export functions matching the schema definitions in `tools/schema.json`.