# Braintrust Integration

## Overview
Braintrust has been integrated into the app as an optional observability platform to compare against Galileo.

## What Was Added

### 1. **Configuration** (`.streamlit/secrets.toml.template`)
```toml
BRAINTRUST_API_KEY = ""          # Braintrust API key (required)
```

**Note**: Braintrust automatically uses the same project name as Galileo:
- If `galileo.project` is set in `domains/{domain}/config.yaml` → uses that
- Otherwise defaults to: `galileo-demo-{domain_name}` (e.g., "galileo-demo-finance")

### 2. **Imports and Initialization** (`app.py`)
- Added Braintrust imports with fallback if not installed:
  ```python
  from braintrust import init_logger as braintrust_init_logger
  from braintrust_langchain import BraintrustCallbackHandler
  ```
- Created `initialize_braintrust_tracing(domain_name)` function that:
  1. Calls `braintrust_init_logger()` to initialize the logger
  2. Creates `BraintrustCallbackHandler()` 
  3. Stores handler in `st.session_state.braintrust_handler`
- Project name uses the same logic as Galileo:
  1. Domain config: `galileo.project` in `domains/{domain}/config.yaml`
  2. Default: `galileo-demo-{domain_name}`

### 3. **UI Control** (Sidebar in `app.py`)
- New "Braintrust" checkbox in "Observability Platforms" sidebar
- Toggle to enable/disable Braintrust per domain
- Shows current project name when enabled
- Defaults to disabled (like LangSmith)
- Forces agent reinitialization when toggled

### 4. **Agent Integration** (`agent_frameworks/langgraph/agent.py`)
- Modified `__init__` to dynamically add Braintrust handler to callbacks
- Checks `st.session_state.braintrust_handler` and `st.session_state.logger_braintrust`
- Gracefully handles case where Streamlit is not available

## How It Works

1. **On App Load**: 
   - Braintrust checkbox defaults to disabled
   - User must manually enable it via the sidebar checkbox

2. **When Enabled**:
   - `initialize_braintrust_tracing()` creates the handler and stores it in session state
   - Agent's `__init__` checks if Braintrust handler exists
   - If found and enabled, adds it to the callbacks list alongside `GalileoCallback`

3. **During Chat**:
   - Every agent interaction sends traces to both Galileo and Braintrust
   - Braintrust captures: LLM calls, tool invocations, agent reasoning, token usage

4. **Toggling**:
   - User can enable/disable via sidebar checkbox
   - Toggling forces agent to reinitialize with updated callbacks
   - No app restart required (hot-swappable)

## Testing

### 1. **Check Configuration**
```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('BRAINTRUST_API_KEY:', 'SET' if os.getenv('BRAINTRUST_API_KEY') else 'NOT SET'); print('BRAINTRUST_PROJECT:', os.getenv('BRAINTRUST_PROJECT'))"
```

### 2. **Run the App**
```bash
streamlit run app.py
```

### 3. **Verify in UI**
- Navigate to your domain (e.g., Finance, E-commerce)
- Check sidebar for "Observability Platforms" section
- Expand "Settings: Configure Loggers"
- Manually enable the Braintrust checkbox
- Should show: "📊 Project: **galileo-demo-finance**" (or your configured project name)

### 4. **Test Tracing**
1. Enable Braintrust in sidebar
2. Send a chat message (e.g., "What are my account options?")
3. Check terminal/console for:
   - "✅ Braintrust tracing initialized"
   - "   Project: galileo-demo-finance" (or your configured project name)
   - "✅ Braintrust handler added to agent callbacks"
4. Visit https://www.braintrust.dev
5. Navigate to your project (e.g., "galileo-demo-finance")
6. Verify traces are appearing

### 5. **Test Toggle**
1. Disable Braintrust checkbox
2. Send another message
3. Verify no Braintrust logs appear
4. Re-enable and verify traces resume

## Key Features

✅ **Hot-swappable**: No app restart needed  
✅ **Per-domain control**: Each domain can have Braintrust enabled/disabled independently  
✅ **Graceful fallback**: Works even if Braintrust isn't installed  
✅ **Multi-platform**: Works alongside Galileo, LangSmith, Phoenix, etc.  
✅ **Automatic**: No code changes needed in domain logic

## Viewing Traces

Traces are sent to: **https://www.braintrust.dev**  
Project: Configured per domain (defaults to `galileo-demo-{domain_name}`)

Each trace includes:
- Full conversation history
- LLM prompts and responses
- Tool calls with arguments and results
- Token usage and latency
- Error details if any

The project name is shown in the UI when Braintrust is enabled.

## Implementation Notes

The implementation follows the same pattern as LangSmith:
- Uses per-domain session state keys (e.g., `logger_braintrust_{domain_name}`)
- Initializes in the sidebar section of `multi_domain_agent_app()`
- Works with the multi-domain architecture
- Defaults to disabled, must be manually enabled by user
- Automatically uses the same project name as Galileo (no separate configuration needed)
- Each domain sends traces to its corresponding Braintrust project
- Project name is stored in session state and displayed in the UI

## Dependencies

Required packages (should already be in `requirements.txt`):
```bash
pip install braintrust braintrust-langchain
```

If not installed, the app will show a warning but continue to work without Braintrust.

## Resources

- Braintrust Documentation: https://www.braintrust.dev/docs
- LangChain Integration: https://www.braintrust.dev/docs/integrations/langchain
