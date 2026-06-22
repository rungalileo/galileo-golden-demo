# Galileo Golden Demo

A multi-turn agentic system that showcases Galileo across multiple domains and agent frameworks, designed to be used for product demos.

## Getting Started

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/) running locally (default: `http://localhost:11434`)
- Docker Desktop (for local PostgreSQL + pgvector)
- Galileo API key
- (Optional) OpenAI API key (only needed if you use the sidebar **Hosted (OpenAI)** provider)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd galileo-golden-demo
   ```

2. **Install Ollama and pull models**

   This demo uses **Ollama** for local inference when the sidebar **Model provider** is set to **Local (Ollama)**.

   Verify Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

   Pull the models used by this demo:
   ```bash
   # Default chat model (agent + tool calling)
   ollama pull gemma4

   # Embedding model for RAG (required for retrieval)
   ollama pull nomic-embed-text
   ```

3. **Start PostgreSQL with pgvector (Docker)**

   ```bash
   docker pull pgvector/pgvector:pg16

   docker run -e POSTGRES_USER=postgres \
              -e POSTGRES_PASSWORD=mypassword \
              -e POSTGRES_DB=vectordb \
              --name golden-demo-postgres \
              -p 5432:5432 \
              -d pgvector/pgvector:pg16
   ```

   Enable the `vector` extension.

   Note: the container can take a few seconds to initialize. If you see a socket/connection error, wait and retry.
   ```bash
   # Wait for Postgres to be ready
   until docker exec golden-demo-postgres pg_isready -U postgres -d vectordb >/dev/null 2>&1; do sleep 1; done

   # Enable the pgvector extension
   docker exec golden-demo-postgres psql -U postgres -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"

   # Verify
   docker exec golden-demo-postgres psql -U postgres -d vectordb -c "\\dx"
   ```

4. **Set up virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install requirements**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. **Configure secrets**

   Copy the template and fill in values:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```

   Minimum required values:
   - `galileo_api_key`
   - `postgres_password` (must match the `POSTGRES_PASSWORD` you used for Docker)

7. **Set up vector databases (per domain)**

   RAG uses the local pgvector index. Load documents for each domain you plan to use:

   ```bash
   python helpers/setup_vectordb.py healthcare local
   python helpers/setup_vectordb.py bank local
   ```

8. **Run the Streamlit app**

   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`.

## Model Selection

Use the sidebar **Model** section to choose how the app runs:

- **Local (Ollama)** — uses models pulled locally (default: `gemma4`).
- **Hosted (OpenAI)** — uses OpenAI models via `openai_api_key` in `.streamlit/secrets.toml`.

## Multi-Domain Support

This demo supports multiple domains with automatic routing and separate Galileo projects per domain.

By default, each domain uses the Galileo project name: `galileo-demo-{domain_name}` (e.g. `galileo-demo-finance`).
You can override this in `domains/{domain}/config.yaml`.

## Underlying Architecture (High Level)

- **UI**: Streamlit (`app.py`)
- **Agent framework**: LangGraph (`agent_frameworks/langgraph/`)
- **RAG storage**: PostgreSQL + pgvector (`langchain-postgres`)
- **Embeddings**: local Ollama embedding model (default: `nomic-embed-text`)
