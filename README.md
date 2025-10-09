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
```

### 3. Add Domain Documents

Place your RAG documents in the `docs/` directory:
- PDFs, text files, CSVs are all supported
- Documents will be automatically chunked and embedded

### 4. Set Up Vector Database

Run this command once when adding a new domain:
```bash
python helpers/setup_vectordb.py your_domain_name
```

This creates a persistent vector database at `domains/your_domain_name/chroma_db/` that only needs to be set up once per domain.

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
4. **RAG Integration** → Vector database provides relevant context when needed
5. **Response Generation** → Agent synthesizes final response
6. **Observability** → All interactions logged to Galileo automatically

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
│   ├── setup_vectordb.py  # Vector database setup
│   └── test_vectordb.py   # Vector database testing
└── tools/                 # Shared tools
    └── rag_retrieval.py   # General RAG functionality (Currently Unused)
```

### For Sales Engineers

As an SE, you primarily need to focus on the `domains/` directory:

- **To customize for a demo**: Update the domain configuration files
- **To add new use cases**: Create a new domain following the structure above
- **For troubleshooting**: If you encounter issues with other files, reach out to the FDE team immediately

The system is designed so that domain customization requires just configuration updates and document additions.

## Running Experiments

This repo now supports running Galileo experiments programmatically! You can:
- 📊 Create synthetic datasets via Galileo API
- 🧪 Run experiments with your agent
- 📈 Evaluate with built-in metrics
- 🔍 Track everything in Galileo Console

### Quick Start

```bash
# Run experiment with inline test data
python experiment_cli.py --inline --experiment quick-test

# Or with a Galileo dataset
python experiment_cli.py --dataset-name my-dataset --experiment baseline-v1
```

See **[EXPERIMENTS_README.md](EXPERIMENTS_README.md)** for detailed instructions.

## Live Stock Data & News (Optional)

The finance agent can use **real-time stock prices** instead of mock data!

### 🎛️ Easiest: Use UI Controls

**No configuration files needed!**

1. Run: `streamlit run app.py`
2. **Sidebar** → "⚙️ Live Data Settings"
3. **Toggle ON** "Use Live Stock Data"
4. Ask: "What's the price of AAPL?" → Real-time data!

See **[UI_CONTROLS_GUIDE.md](UI_CONTROLS_GUIDE.md)** for details.

### Alternative: Command Line Setup

```bash
# 1. Install yfinance
pip install yfinance

# 2. Enable live data
echo 'USE_LIVE_DATA = "true"' >> .streamlit/secrets.toml

# 3. Run app
streamlit run app.py
```

### Or Use Setup Script

```bash
./setup_live_data.sh
```

**Supports:**
- ✅ Yahoo Finance (yfinance) - Free, no API key needed
- ✅ Alpha Vantage - Free tier with API key, includes news
- ✅ Automatic fallback to mock data if APIs fail

See **[LIVE_DATA_SETUP.md](LIVE_DATA_SETUP.md)** for full documentation.

## Chaos Engineering (Testing Galileo Insights)

Simulate real-world failures to test Galileo's observability and guardrails!

### Quick Chaos Test

```bash
streamlit run app.py
```

**Sidebar → 🔥 Chaos Engineering → Enable:**
- 🔢 **Sloppiness** - Transposes numbers (simulates hallucinations)
- 🔌 **Tool Instability** - Random API failures
- 📚 **RAG Disconnects** - Vector DB failures
- ⏱️ **Rate Limits** - API quota errors
- 💥 **Data Corruption** - Wrong/invalid data

**Then ask**: "What's the price of AAPL?" (repeat 5-10 times)

**Result**: Chaos creates varied failures that Galileo Insights will detect and recommend fixes for!

See **[CHAOS_ENGINEERING.md](CHAOS_ENGINEERING.md)** and **[CHAOS_QUICK_START.md](CHAOS_QUICK_START.md)** for details.

## Galileo Guardrails (Production Safety)

Real-time content filtering and safety for production deployments!

### Quick Start

```bash
pip install galileo-protect
streamlit run app.py
```

**Sidebar → 🛡️ Galileo Guardrails → Enable**

### Protections

**Input Filtering:**
- 🔒 **PII Detection** - Blocks SSN, account numbers, credit cards
- 🚫 **Sexism Detection** - Filters discriminatory content
- ⚠️ **Toxicity Detection** - Blocks harmful language

**Output Filtering:**
- 🔒 **PII Leakage Prevention** - Stops sensitive data exposure
- 🚫 **Inappropriate Content** - Blocks sexist/toxic responses
- ⚠️ **Safety Layer** - Comprehensive content filtering

**Trade Protection:**
- 📊 **Context Adherence** - Blocks trades < 70% confidence
- 🎯 **Hallucination Detection** - Catches wrong amounts/prices
- ⛔ **Auto-Block** - Prevents suspicious trades

### Test It

1. **Enable guardrails** (sidebar toggle)
2. **Try**: "Show me my account information"
3. **See**: 🛡️ **Guardrail Active** - PII blocked!

**Other tests:**
- "My SSN is 123-45-6789" → Input PII blocked
- Enable chaos + "Buy 10 shares" → Trade blocked if hallucinated

**Result:** Production-ready safety with real-time monitoring!

See **[GUARDRAILS_GUIDE.md](GUARDRAILS_GUIDE.md)** for full documentation.

## What's Coming Next

- **Live deployment URL** for easy demo access without local setup
- **Direct links to Galileo sessions/spans** from the UI
- **Hallucination logging buttons** for interactive evaluation
- ✅ **Experiment integration** for A/B testing different prompts/models *(now available!)*
- **Galileo Protect integration** for safety and compliance monitoring

## Updates and Issues

If you encounter any issues or have feedback please contact the FDE team via slack
