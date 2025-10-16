# Galileo Golden Demo

A multi-turn agentic system that showcases Galileo across multiple domains and agent frameworks, designed to be used for product demos. The code itself is reusable and configurable for a variety of use cases.

## What This Repo Is

A multi-turn agentic system showcasing Galileo's observability capabilities with configurable domains and RAG integration. Built to be reusable for product demos with minimal setup time.

## What This Repo Isn't

Not a production reference architecture or replacement for customer-specific POCs requiring heavy customization.

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- Galileo API key
- Pinecone API keys (for both local and hosted environments)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd galileo-golden-demo
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**
   Copy the secrets template and add your API keys:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```
   
   Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   openai_api_key = "your_openai_api_key_here"
   galileo_api_key = "your_galileo_api_key_here"
   galileo_project = "your_project_name"
   galileo_log_stream = "your_log_stream_name"
   
   # Pinecone Configuration
   pinecone_api_key_local = "your_local_project_api_key"
   pinecone_api_key_hosted = "your_hosted_project_api_key"
   environment = "local"  # or "hosted"
   ```

5. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

## How to Add a New Domain
This demo code is designed to easily be extended to different domains, that way, SE's can spend less time
writing code and more time focusing on how to display Galileo in the best light. 

Adding a new domain is straightforward - simply copy the existing finance domain structure and customize the components:

### 1. Create Domain Directory Structure

```bash
mkdir domains/your_domain_name
cd domains/your_domain_name
```

Create the following structure:
```
your_domain_name/
├── config.yaml          # Domain configuration
├── system_prompt.json   # System prompt for the agent
├── dataset.csv          # Evaluation dataset (optional)
├── docs/               # RAG documents
│   ├── document1.pdf
│   └── document2.csv
└── tools/              # Domain-specific tools
    ├── schema.json     # Tool definitions (OpenAI format)
    └── logic.py        # Tool implementation
```

### 2. Configure Domain Settings

**config.yaml** - Main configuration file:
```yaml
domain:
  name: "your_domain"
  description: "Your domain description"

ui:
  app_title: "🤖 Your Domain Assistant"
  example_queries:
    - "Example query 1"
    - "Example query 2"

model:
  model_name: "gpt-4.1"
  temperature: 0.1

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "your_tool_name"

vectorstore:
  embedding_model: "text-embedding-3-large"
```

**system_prompt.json** - Define the agent's behavior:
```json
{
  "system_prompt": "You are a helpful assistant for [your domain]. Your role is to..."
}
```

**tools/schema.json** - Define available tools in OpenAI function format:
```json
[
  {
    "name": "your_tool_name",
    "description": "What your tool does",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param1"]
    }
  }
]
```

**tools/logic.py** - Implement tool functionality:
```python
def your_tool_name(param1: str) -> str:
    """
    Tool implementation
    """
    # Your logic here
    return "Tool result"

 TOOLS = [your_tool_name]
```

Make sure you export your tools in this file by creating a `TOOLS` array at the end of your file

### 3. Add Domain Documents

Place your RAG documents in the `docs/` directory:
- PDFs, text files, CSVs are all supported
- Documents will be automatically chunked and embedded

### 4. Set Up Vector Database

The app uses Pinecone for vector storage. This is a **one-time setup** per domain and environment:

```bash
# For local demos
python helpers/setup_vectordb.py your_domain_name local

# For hosted demos  
python helpers/setup_vectordb.py your_domain_name hosted
```

**Important Notes:**
- You need both project API keys to create indexes using the setup scripts
- Once indexes are created, you only need the environment and matching API key in your secrets file
- This processes documents from `domains/your_domain_name/docs/` directory
- Creates Pinecone indexes that persist in the cloud and don't need to be rebuilt

See [PINECONE_SETUP.md](PINECONE_SETUP.md) for detailed configuration instructions.

### 5. Update App Configuration (Temporary)

In `app.py`, change the domain configuration:
```python
DOMAIN = "your_domain_name"  # Change this line
```

*Note: This step is temporary while we finalize multi-domain support in the UI.*

## Underlying Architecture

### Data Flow

1. **User Input** → Streamlit UI captures user message
2. **Agent Processing** → AgentFactory creates domain-specific agent
3. **Tool Execution** → Agent decides which tools to call based on user intent
4. **RAG Integration** → Pinecone vector database provides relevant context when needed
5. **Response Generation** → Agent synthesizes final response
6. **Observability** → All interactions logged to Galileo automatically

### Vector Database Architecture

The app uses **Pinecone** for vector storage with environment-based configuration:

- **Local Demos**: Uses `galileo-demo-local` Pinecone project
- **Hosted Demos (i.e. streamlit)**: Uses `galileo-demo-hosted` Pinecone project
- **Index Naming**: `{domain}-{environment}-index` (e.g., `finance-local-index`)
- **Automatic Selection**: When the app executes vectorDB searches, the app automatically uses the correct project based on environment setting

See [PINECONE_SETUP.md](PINECONE_SETUP.md) for detailed configuration instructions.

## Code Structure

```
galileo-golden-demo/
├── app.py                    # Streamlit application entry point
├── agent_factory.py          # Agent creation and management
├── base_agent.py            # Abstract base agent class
├── domain_manager.py        # Domain configuration management
├── setup_env.py            # Environment setup utilities
├── run_streamlit.py        # Alternative app runner
├── requirements.txt         # Python dependencies
├── agent_frameworks/        # Agent framework implementations
│   └── langgraph/
│       ├── agent.py         # LangGraph agent implementation
│       └── langgraph_rag.py # RAG integration for LangGraph
├── domains/                 # Domain-specific configurations
│   └── finance/            # Example finance domain
│       ├── config.yaml     # Domain configuration
│       ├── system_prompt.json
│       ├── dataset.csv     # Evaluation data
│       ├── docs/          # RAG documents
│       └── tools/         # Domain tools
├── helpers/                # Utility scripts
│   ├── setup_vectordb.py  # Pinecone vector database setup
│   └── test_vectordb.py   # Vector database testing
├── tools/                 # Shared tools
│   └── rag_retrieval.py   # General RAG functionality (not implemented)
└── PINECONE_SETUP.md      # Detailed Pinecone configuration guide
```

### For Sales Engineers

As an SE, you primarily need to focus on the `domains/` directory:

- **To customize for a demo**: Update the domain configuration files
- **To add new use cases**: Create a new domain following the structure above
- **For troubleshooting**: If you encounter issues with other files, reach out to the FDE team immediately

The system is designed so that domain customization requires just configuration updates and document additions.

## Running Experiments

The demo includes scripts to create Galileo datasets and run experiments to evaluate your agents:

### Creating Datasets

Create a Galileo dataset from a domain's CSV file:

```bash
# Preview the dataset before creating
python experiments/create_galileo_dataset.py finance --preview

# Create the dataset in Galileo
python experiments/create_galileo_dataset.py finance
```

This script:
- Reads the `domains/{domain}/dataset.csv` file
- Uses the domain configuration from `domains/{domain}/config.yaml`
- Creates a Galileo dataset with the naming convention: `"{Domain} Domain Dataset"`
- Returns the dataset ID for use in experiments

### Running Experiments

Run experiments to evaluate your agents using the created dataset:

```bash
# Run experiment with default name
python experiments/run_experiment.py finance

# Run experiment with custom name
python experiments/run_experiment.py finance --experiment-name "finance-evaluation-v1"
```

The experiment script:
- Loads the dataset created by `create_galileo_dataset.py`
- Runs each input through the LangGraph agent
- Evaluates responses metrics defined in code
- Logs all traces to Galileo as an experiment

### Experiment Workflow

1. **Create Dataset**: Use `create_galileo_dataset.py` to convert your domain's CSV into a Galileo dataset, if it doesn't exist already
2. **Run Experiment**: Use `run_experiment.py` to evaluate your agent against the dataset
3. **Analyze Results**: View experiment results and traces in the Galileo Console

## What's Coming Next

- **Live deployment URL** for easy demo access without local setup
- **Direct links to Galileo sessions/spans** from the UI
- **Hallucination logging buttons** for interactive evaluation
- **Galileo Protect integration** for safety and compliance monitoring

## Updates and Issues

If you encounter any issues or have feedback please contact the FDE team via slack
