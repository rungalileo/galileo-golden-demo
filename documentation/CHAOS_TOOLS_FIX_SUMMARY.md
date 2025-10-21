# Chaos Tools Loading Fix

## Problem
The chaos tools were not loading during dataset runs, even when the `USE_CHAOS_TOOLS` environment variable was set to `true`. The agent kept showing only 6 tools (5 base + 1 RAG) instead of 22 tools (17 chaos + 4 standard + 1 RAG).

## Root Cause
There were three main issues:

### 1. Missing Required Tools
`CHAOS_TOOLS` only contained 17 variations of `get_stock_price`, but the agent needs other tools to function:
- `get_market_news` - to fetch market news
- `get_account_information` - to check account balance
- `purchase_stocks` - to buy stocks
- `sell_stocks` - to sell stocks

Without these tools, the agent couldn't complete its tasks.

### 2. Circular Import Dependency
- `logic.py` tried to import `CHAOS_TOOLS` from `chaos_tools.py` at module load time
- `chaos_tools.py` imported `get_stock_price` and `get_market_news` from `logic.py` at module load time
- When loaded via `importlib.util.spec_from_file_location` (as done by the agent), relative imports failed, causing the circular dependency to break

### 3. JsonSchema Generation Error
- All tool functions have a `galileo_logger: Optional[GalileoLogger]` parameter
- Chaos tools don't have entries in `schema.json`, so LangChain tries to auto-generate JSON schemas from function signatures
- `GalileoLogger` is a complex object that can't be serialized to JSON Schema
- This caused: `[ERROR] Error processing query: Cannot generate a JsonSchema for core_schema.CallableSchema`

## Solution

### 1. Combine Chaos and Standard Tools
Updated `logic.py` to provide a complete tool set when chaos mode is enabled:
```python
TOOLS = CHAOS_TOOLS + [
    get_market_news,
    get_account_information,
    purchase_stocks,
    sell_stocks
]
```

This gives the agent:
- **17 confusing options** for stock price lookups (the chaos)
- **4 standard tools** for other operations (so the agent can still function)
- **Total: 21 tools** (plus RAG tool added separately by agent = 22 total)

### 2. Lazy Imports to Break Circular Dependency
Updated `chaos_tools.py` to use lazy imports via wrapper functions:

```python
# Wrapper functions that lazy-load the base functions
def _base_get_stock_price(ticker: str, galileo_logger=None) -> str:
    """Wrapper for base get_stock_price with lazy import."""
    return _get_base_function('get_stock_price')(ticker, galileo_logger)
```

This ensures:
- `chaos_tools.py` doesn't import from `logic.py` at module load time
- The import only happens when a chaos tool function is actually called
- By that point, `logic.py` is fully loaded, so there's no circular dependency

### 3. Auto-Generate Input Schemas for Chaos Tools
Updated `agent.py` to automatically create Pydantic input schemas for tools without `schema.json` entries:

```python
# If no schema found (e.g., for chaos tools), create a simple schema
# that excludes the galileo_logger parameter (which causes JsonSchema errors)
if "ticker" in params and len(params) == 1:
    from pydantic import BaseModel, Field
    class StockTickerInput(BaseModel):
        ticker: str = Field(..., description="The stock ticker symbol")
    args_schema = StockTickerInput
```

This ensures:
- Chaos tools get proper Pydantic input schemas automatically
- The `galileo_logger` parameter is excluded from the JSON schema
- No `JsonSchema for core_schema.CallableSchema` errors occur
- Tools can still receive the `galileo_logger` parameter at runtime (it's just not in the schema)

## Verification

Run a dataset experiment with chaos tools enabled and check the logs:
```
🔥 CHAOS MODE ENABLED: Replacing standard tools with confusing alternatives!
⚠️  Base get_stock_price tool is now OFF-LIMITS
🔧 21 total tools: 17 chaos stock price tools + 4 standard tools
```

The agent will now have to choose between 17 confusing variations of `get_stock_price` with different:
- Names (get_stock_price_fast, fetch_stock_price, lookup_stock_price, etc.)
- Behaviors (minimal data, artificial latency, subtle bugs, different formats)
- API versions (v2, unstable schema, evolving fields, deprecated fields, breaking changes)

This creates realistic confusion that showcases Galileo's observability value in debugging tool selection issues.

## How to Enable Chaos Tools

### Option 1: Streamlit UI
1. Go to the Chat tab
2. Expand "⚙️ Chaos Controls"
3. Check "🔧 Confusing Tools"
4. The agent will reload with chaos tools

### Option 2: Environment Variable
Set before running experiments:
```bash
export USE_CHAOS_TOOLS=true
python run_experiment.py
```

### Option 3: In Code
```python
import os
os.environ["USE_CHAOS_TOOLS"] = "true"
# Then import/create agent
```

## Expected Behavior

**Standard Mode (chaos tools OFF):**
- 5 base tools + 1 RAG = 6 total
- One clear `get_stock_price` function
- Predictable behavior

**Chaos Mode (chaos tools ON):**
- 17 chaos + 4 standard + 1 RAG = 22 total
- 17 confusing variations of stock price lookup
- Agent must choose between imperfect options
- Showcases Galileo's value in debugging tool selection and API evolution issues

