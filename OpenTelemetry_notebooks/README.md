# OpenTelemetry Notebooks

This folder contains Jupyter notebooks demonstrating OpenTelemetry integration with Galileo.

## Available Notebooks

### `otel_galileo_demo.ipynb`

A comprehensive demo notebook showing how to:
- Set up OpenTelemetry with Galileo's OTLP endpoint
- Automatically instrument OpenAI, LangChain, and LangGraph
- Create custom spans for manual tracing
- View traces in Galileo Console

## Prerequisites

Before running the notebooks:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install jupyter notebook
   ```

2. **Configure secrets:**
   Make sure your `.streamlit/secrets.toml` has:
   ```toml
   galileo_api_key = "your-api-key"
   galileo_project = "your-project-name"
   galileo_log_stream = "your-log-stream-name"
   openai_api_key = "your-openai-key"
   ```

3. **Optional - Enable Galileo OTLP endpoint:**
   ```toml
   otel_exporter_otlp_endpoint = "https://api.galileo.ai/otel/traces"
   ```
   (If not set, traces will still be generated but won't be exported to Galileo via OTLP)

## Running the Notebook

1. **Start Jupyter from the project root:**
   ```bash
   cd /path/to/galileo-golden-demo
   jupyter notebook
   ```
   This ensures the notebook can find `requirements.txt` and project modules.

2. **Navigate to `OpenTelemetry_notebooks` folder** and open `otel_galileo_demo.ipynb`

3. **Important**: The first cell will:
   - Detect the project root automatically
   - Verify that `requirements.txt` exists
   - Set up the Python path correctly

4. **Run cells sequentially** - each cell builds on the previous one

5. **View traces** in Galileo Console after running queries

## What You'll See

The notebook demonstrates:

- ✅ **Automatic Instrumentation**: OpenAI, LangGraph, and HTTP calls are automatically traced
- ✅ **Manual Tracing**: Custom spans for business logic
- ✅ **Trace Visualization**: Complete trace graphs in Galileo
- ✅ **Performance Metrics**: Token usage, latency, and more

## Troubleshooting

### Notebook can't find modules or requirements.txt
- **Start Jupyter from the project root directory**, not from the notebook folder
- The notebook automatically detects the project root and adds it to `sys.path`
- If you see path errors, check the first cell output - it shows the detected project root
- You can also manually set the project root in the first cell if needed

### Traces not appearing in Galileo
- Check that `OTEL_EXPORTER_OTLP_ENDPOINT` is set correctly
- Verify your `GALILEO_API_KEY`, `GALILEO_PROJECT`, and `GALILEO_LOG_STREAM` are set
- Enable console exporter to see if traces are being generated: `os.environ["OTEL_CONSOLE_EXPORTER"] = "true"`

### Missing dependencies
- Install all requirements: `pip install -r requirements.txt`
- Install Jupyter: `pip install jupyter notebook`

## Resources

- [Galileo OpenTelemetry Documentation](https://v2docs.galileo.ai/how-to-guides/third-party-integrations/otel)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference)

