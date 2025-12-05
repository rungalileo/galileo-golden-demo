# Chaos Engineering

The demo includes a **Chaos Engineering** system to showcase Galileo's observability and detection capabilities by intentionally injecting failures. Chaos modes can be toggled from the sidebar during demos.

## Quick Start

1. **Enable in UI**: Toggle chaos modes in the sidebar under "Chaos Engineering"
2. **Run Queries**: Ask normal questions - chaos is injected automatically based on configured rates
3. **Check Galileo**: View traces in Galileo Console to see detected issues
4. **Reset Stats**: Click "Reset Stats" to clear chaos counters between demos

## Understanding Chaos Modes

Each chaos mode tests different aspects of your AI system and demonstrates what Galileo can detect. All 5 modes work across **all domains** automatically - no custom code needed.

### 1. 🔧 Tool Instability (25% API failures)

**What it simulates**: External API calls failing (network errors, timeouts, 500 errors)

**Example**: `get_stock_price()` returns `{"error": "Service temporarily unavailable", "status_code": 503}`

**What Galileo detects**:
- ❌ **Span-level metrics**: FAIL (tool execution failed)
- ❌ **Trace-level metrics**: FAIL (query couldn't be answered)
- ❌ **Session-level metrics**: FAIL (user experience degraded)

**Observability story**: "External dependencies are unreliable. Galileo tracks when and how often your tools fail."

**How it works**:
- Wraps all domain tools automatically
- Randomly returns realistic HTTP errors (503, 504, 500, 401, 403, 404, timeouts)
- Errors are logged as structured JSON so Galileo captures them
- Occasionally injects latency (2-5 second delays)

---

### 2. 🔢 Sloppiness (30% number transposition)

**What it simulates**: Tool outputs getting corrupted during transmission to the LLM (e.g., numbers changing between tool execution and LLM processing)

**Example**: Tool returns `$178.45` → LLM receives `$423.89`

**What Galileo detects**:
- ✅ **Tool span metrics**: PASS (tool executed correctly, returned correct data)
- ✅ **LLM span metrics**: PASS (LLM processed the data it received correctly)
- ❌ **Cross-span detection**: FAIL (Galileo detects tool output ≠ what appears in LLM response)
- ❌ **Trace-level metrics**: FAIL (overall response contains incorrect information)

**Observability story**: "The tool worked fine and the LLM worked fine, but something went wrong in between. Galileo can detect when the data the LLM uses doesn't match what the tool actually returned."

**How it works**:
- After tools execute successfully, randomly corrupts numbers in tool messages
- Replaces numbers with similar magnitude values (0.5x to 3x)
- Preserves decimal places and formatting
- LLM receives corrupted data and responds based on wrong numbers

---

### 3. 💥 Data Corruption (20% LLM errors)

**What it simulates**: LLM randomly corrupting data it receives - making calculation errors, misreading numbers, or getting confused (e.g., LLM sees `$178.45` but says `$289.73`)

**Example**: Tool correctly returns `$178.45` → LLM receives `$178.45` → LLM incorrectly says `$289.73`

**What Galileo detects**:
- ✅ **Tool span metrics**: PASS (tool executed correctly, returned correct data)
- ❌ **LLM span metrics**: FAIL (hallucination detection catches LLM corrupting the data)
- ❌ **Trace-level metrics**: FAIL (overall response contains incorrect information)

**Observability story**: "The LLM made errors processing correct tool data. Galileo catches when LLMs corrupt information they receive."

**Key difference from Sloppiness**:
- **Sloppiness**: Data corrupted BEFORE LLM sees it (data in transit) → LLM span passes, but cross-span comparison fails
- **Data Corruption**: LLM corrupts AFTER receiving correct data (LLM hallucination) → LLM span fails

**How it works**:
- Injects a system prompt that forces the LLM to corrupt numerical data
- LLM receives correct tool data but is instructed to change numbers in its response
- Simulates LLM instability, calculation errors, and hallucinations
- Different from manual "Hallucination Demo" - this is automatic chaos testing

---

### 4. 📚 RAG Disconnects (20% failures)

**What it simulates**: Vector database or retrieval system becoming unavailable

**Example**: RAG tool returns `{"error": "Vector database connection failed", "status_code": 503}`

**What Galileo detects**:
- ❌ **Context quality metrics**: FAIL (no context retrieved)
- ❌ **Trace-level metrics**: FAIL (response lacks grounding)
- Enables testing how your agent handles knowledge base outages

**Observability story**: "Your RAG system went down. Galileo shows when agents are operating without proper context."

**How it works**:
- Wraps RAG retrieval tool automatically
- Per-query random check (not session-level)
- Returns realistic vector DB errors (Pinecone, ChromaDB, embedding failures)
- Allows testing agent behavior without context

---

### 5. ⏱️ Rate Limits (15% quota errors)

**What it simulates**: Hitting API rate limits on external services

**Example**: Tool calls get delayed or rejected with `429 Too Many Requests`

**What Galileo detects**:
- ⚠️ **Latency metrics**: Degraded (increased response times)
- ❌ **Reliability metrics**: FAIL (some requests blocked)

**Observability story**: "You're hitting rate limits. Galileo tracks latency and helps you identify bottlenecks."

**How it works**:
- Separate from Tool Instability (different error type)
- Returns 429 errors with realistic rate limit messages
- Simulates quota exhaustion scenarios
- Helps test retry logic and graceful degradation

---

## Chaos Statistics

The UI displays real-time counters for each chaos mode:

```
📊 Chaos Statistics
- Tool Instability: X   | Rate Limits: Y
- Sloppiness: X        | Data Corruption: Y
- RAG Chaos: X         |
```

**What each counter tracks**:
- **Tool Instability**: Number of API failures injected
- **Sloppiness**: Number of tool outputs with transposed numbers
- **RAG Chaos**: Number of RAG disconnections
- **Rate Limits**: Number of rate limit errors
- **Data Corruption**: Number of LLM corruption events

**Note**: Counters only track when chaos modes are enabled. Click "Reset Stats" to clear between demos.

---

## Technical Architecture

### Domain-Agnostic Design

Chaos engineering works across **all domains** without custom code:

1. **Tool Wrapping** (`chaos_wrapper.py`):
   - Automatically wraps all domain tools
   - No pattern matching needed
   - Works with any function signature

2. **Chaos Decision Logic** (`chaos_engine.py`):
   - Centralized "brain" that decides when chaos happens
   - Configurable failure rates
   - Statistics tracking

3. **Agent Integration** (`agent.py`):
   - Sloppiness: Corrupts tool messages before LLM sees them
   - Data Corruption: Injects system prompt to force LLM errors

### How Chaos is Applied

```python
# 1. Tools are wrapped at agent creation time
from chaos_wrapper import wrap_tools_with_chaos
wrapped_tools = wrap_tools_with_chaos(raw_tools)

# 2. Chaos engine decides at runtime
chaos = get_chaos_engine()
should_fail, error_msg = chaos.should_fail_api_call("Get Stock Price")

# 3. Errors returned as structured JSON (not raised)
return json.dumps({
    "error": error_msg,
    "status_code": "503",
    "chaos_injected": True
})
```

### Failure Rates (Configurable)

Default rates are set for realistic testing:

- Tool Instability: **25%** (1 in 4 API calls fail)
- Sloppiness: **30%** (3 in 10 outputs corrupted)
- Data Corruption: **20%** (1 in 5 LLM responses corrupt data)
- RAG Disconnects: **20%** (1 in 5 RAG queries fail)
- Rate Limits: **15%** (occasional quota hits)

Rates are tuned to show failures frequently enough for demos without breaking the experience.

---

## What Makes This Special

- 🌍 **Domain-Agnostic**: Works automatically across all domains without custom code
- 🎯 **Targeted Testing**: Each mode tests specific observability capabilities
- 📊 **Real-time Stats**: See chaos injection rates and counts in the UI
- 🔧 **Demo-Ready**: Perfect for showing Galileo's detection capabilities in action
- 🎛️ **Configurable**: Adjust failure rates per mode
- 📈 **Experiment-Ready**: Use with Galileo Experiments for aggregate analysis


