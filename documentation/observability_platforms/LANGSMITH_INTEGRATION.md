# LangSmith Integration

## Overview
LangSmith has been integrated into the app as an optional observability platform to compare against Galileo.
## What Was Added

### 1. **Configuration** (`.streamlit/secrets.toml`)
```toml
LANGCHAIN_API_KEY = ""  # LangSmith API key (required)
```

**Note**: LangSmith automatically uses the same project name as Galileo:
- If `galileo.project` is set in `domains/{domain}/config.yaml` → uses that
- Otherwise defaults to: `galileo-demo-{domain_name}` (e.g., "galileo-demo-finance")

### 2. **Imports and Initialization** (`app.py`)
- Added LangSmith imports with fallback if not installed
- Created `initialize_langsmith_tracing(domain_name)` function to set up the LangChain tracer
- Tracer is stored in `st.session_state.langsmith_tracer`
- Project name uses the same logic as Galileo:
  1. Domain config: `galileo.project` in `domains/{domain}/config.yaml`
  2. Default: `galileo-demo-{domain_name}`

### 3. **UI Control** (Sidebar in `app.py`)
- New "LangSmith" checkbox in "Observability Platforms" sidebar
- Toggle checkbox to enable/disable LangSmith per domain
- Shows current project name when enabled
- Defaults to disabled, must be manually enabled by user
- Forces agent reinitialization when toggled

### 4. **Agent Integration** (`agent_frameworks/langgraph/agent.py`)
- Modified `__init__` to dynamically add LangSmith tracer to callbacks
- Checks `st.session_state.langsmith_tracer` and `st.session_state.logger_langsmith`
- Gracefully handles case where Streamlit is not available

## How It Works

1. **On App Load**: 
   - LangSmith checkbox defaults to disabled
   - User must manually enable it via the sidebar checkbox

2. **When Enabled**:
   - `initialize_langsmith_tracing(domain_name)` creates the tracer with the Galileo project name
   - Tracer is stored in session state

3. **When Agent is Created**:
   - Agent's `__init__` checks if LangSmith tracer exists
   - If found and enabled, adds it to the callbacks list alongside `GalileoCallback`

4. **During Chat**:
   - Every agent interaction sends traces to both Galileo and LangSmith
   - LangSmith captures: LLM calls, tool invocations, agent reasoning, token usage

5. **Toggling**:
   - User can enable/disable via sidebar checkbox
   - Toggling forces agent to reinitialize with updated callbacks
   - No app restart required (hot-swappable)

## Testing

### 1. **Check Configuration**
```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('LANGCHAIN_API_KEY:', 'SET' if os.getenv('LANGCHAIN_API_KEY') else 'NOT SET')"
```

### 2. **Run the App**
```bash
streamlit run app.py
```

### 3. **Verify in UI**
- Navigate to your domain (e.g., Finance, E-commerce)
- Check sidebar for "Observability Platforms" section
- Expand "Settings: Configure Loggers"
- Manually enable the LangSmith checkbox
- Should show: "📊 Project: **galileo-demo-finance**" (or your configured project name)

### 4. **Test Tracing**
1. Enable LangSmith in sidebar
2. Send a chat message (e.g., "What are my account options?")
3. Check terminal/console for:
   - "✅ LangSmith tracing initialized"
   - "   Project: galileo-demo-finance" (or your configured project name)
   - "✅ LangSmith tracer added to agent callbacks"
4. Visit https://smith.langchain.com
5. Navigate to your project (e.g., "galileo-demo-finance")
6. Verify traces are appearing

### 5. **Test Toggle**
1. Disable LangSmith checkbox
2. Send another message
3. Verify no LangSmith logs appear
4. Re-enable and verify traces resume

## Key Features

✅ **Hot-swappable**: No app restart needed  
✅ **Per-domain control**: Each domain can have LangSmith enabled/disabled independently  
✅ **Graceful fallback**: Works even if LangSmith isn't installed  
✅ **Multi-platform**: Works alongside Galileo, Phoenix, etc.  
✅ **Automatic**: No code changes needed in domain logic

## Viewing Traces

Traces are sent to: **https://smith.langchain.com**  
Project: Configured per domain (defaults to `galileo-demo-{domain_name}`)

Each trace includes:
- Full conversation history
- LLM prompts and responses
- Tool calls with arguments and results
- Token usage and latency
- Error details if any

The project name is shown in the UI when LangSmith is enabled.

## Implementation Notes

The implementation follows per-domain configuration:
- Uses per-domain session state keys (e.g., `logger_langsmith_{domain_name}`)
- Initializes in the sidebar section of `multi_domain_agent_app()`
- Works with the multi-domain architecture
- Defaults to disabled, must be manually enabled by user
- Automatically uses the same project name as Galileo (no separate configuration needed)
- Each domain sends traces to its corresponding LangSmith project
- Project name is stored in session state and displayed in the UI

## Dependencies

Required packages (should already be installed):
```bash
pip install langsmith langchain-classic
```

**Note**: This app uses `langchain_classic` for backward compatibility with older LangChain imports. The LangSmith tracer is imported from `langchain_classic.callbacks.tracers`.

If not installed, the app will show a warning but continue to work without LangSmith.

