
# 🔥 Chaos Engineering for Galileo Testing

## Overview

The Chaos Engineering system simulates real-world failures and problematic patterns to showcase:

- **Galileo Observability**: Detect anomalies and issues automatically
- **Galileo Insights**: Surface patterns and suggest fixes
- **Galileo Guardrails**: Block problematic outputs
- **System Resilience**: How the agent handles failures

## Location

**Streamlit Sidebar → 🔥 Chaos Engineering → ⚙️ Chaos Controls**

## Chaos Modes

### 1. 🔌 Tool Instability (25% failure rate)

**What it does**: Randomly fails API calls to simulate network issues

**Simulates:**
- Network timeouts
- Service outages (503 errors)
- Connection refused
- Invalid API responses
- Endpoint unavailability

**Example errors:**
```
"Stock Price API temporarily unavailable (503 Service Unavailable)"
"Connection refused: Stock Price API server not responding"
"Stock Price API timeout after 30 seconds"
```

**Galileo will detect:**
- Sudden spike in tool errors
- Pattern of failed API calls
- Increased error rates

### 2. 🔢 Sloppiness (30% error rate)

**What it does**: Randomly transposes digits in numbers

**Simulates:**
- LLM hallucinations with numbers
- Data entry errors
- Transcription mistakes
- Calculation errors

**Examples:**
```
Original: "The price is $258.06"
Sloppy:   "The price is $285.06"  (5 and 8 transposed)

Original: "Buy 10 shares"
Sloppy:   "Buy 01 shares"  (1 and 0 transposed)

Original: "Total cost: $1,234.56"
Sloppy:   "Total cost: $1,243.56"  (3 and 4 transposed)
```

**Galileo will detect:**
- Hallucinations in numerical data
- Inconsistencies between tool output and agent response
- Factual accuracy issues

### 3. 📚 RAG Disconnects (20% failure rate)

**What it does**: Randomly prevents RAG from loading

**Simulates:**
- Vector database connection failures
- ChromaDB service outages
- Embedding model timeouts
- Document index corruption
- Network issues with vector DB

**Effects:**
- Agent doesn't have access to RAG documents
- Can't answer questions requiring historical data
- Must rely only on tools
- Degrades quality for document-based queries

**Galileo will detect:**
- Missing RAG retrievals in traces
- Quality degradation for certain query types
- Pattern of failures for document-based questions

### 4. ⏱️ Rate Limits (15% failure rate)

**What it does**: Simulates API quota exhaustion

**Simulates:**
- Daily API limit reached
- Per-minute rate limit exceeded
- Quota exhausted errors (429)

**Example errors:**
```
"Rate limit exceeded for Stock Price API. Please try again later. (429 Too Many Requests)"
```

**Galileo will detect:**
- Rate limit error patterns
- Time-of-day usage spikes
- Need for caching or rate limiting

### 5. 💥 Data Corruption (20% corruption rate)

**What it does**: Returns invalid or corrupted data from APIs

**Corruption types:**
- **Wrong prices**: Multiplies price by 0.5x to 2x
- **Negative values**: All changes become negative
- **Missing fields**: Removes random fields (volume, high, low, etc.)
- **Stale timestamps**: Returns very old timestamps
- **Wrong tickers**: Returns different ticker than requested

**Examples:**
```
Request: AAPL price
Returns: Price for "XXXX" ticker (wrong ticker)

Request: TSLA price  
Returns: Price of $876.00 (real: $438.00 - 2x corruption)

Request: NVDA data
Returns: Missing "volume" field
```

**Galileo will detect:**
- Data quality issues
- Inconsistent responses
- Missing required fields
- Anomalous values

## How to Use

### In Streamlit UI

1. **Run app**: `streamlit run app.py`
2. **Sidebar** → "🔥 Chaos Engineering"
3. **Expand** "⚙️ Chaos Controls"
4. **Check** the chaos modes you want to enable
5. **Chat** and see chaos in action!

### Quick Chaos Test

**Enable all chaos:**
1. ✓ Tool Instability
2. ✓ Sloppiness
3. ✓ RAG Disconnects
4. ✓ Rate Limits
5. ✓ Data Corruption

**Then ask**: "What's the price of AAPL?"

**Possible outcomes:**
- ✅ Works fine (chaos didn't trigger)
- 🔌 API failure error
- 🔢 Price with transposed digits ($285.06 instead of $258.06)
- 💥 Corrupted data (wrong price, missing fields)
- ⏱️ Rate limit error

### For Experiments

Chaos modes carry over to experiments:

```bash
# Enable chaos in UI, then run experiment
python experiment_cli.py --inline --experiment chaos-test
```

**Each row** has independent chance of chaos, creating varied patterns!

## What Galileo Will Detect

### Galileo Insights Patterns

**Tool Instability:**
- "High API failure rate detected (25% of calls failing)"
- "Stock Price API showing intermittent connectivity issues"
- "Recommendation: Implement retry logic with exponential backoff"

**Sloppiness:**
- "Numerical hallucinations detected in 30% of responses"
- "Agent output inconsistent with tool output"
- "Recommendation: Add numerical validation guardrail"

**RAG Chaos:**
- "RAG retrieval missing in 20% of traces"
- "Quality degradation for document-based queries"
- "Recommendation: Implement fallback when RAG unavailable"

**Rate Limits:**
- "Rate limit errors occurring regularly"
- "15% of API calls being throttled"
- "Recommendation: Implement caching or reduce call frequency"

**Data Corruption:**
- "Anomalous price values detected"
- "Missing required fields in 20% of responses"
- "Recommendation: Add data validation before using API responses"

### Galileo Guardrails

You can configure guardrails to:

**Block responses with:**
- Transposed numbers (detected via factual accuracy)
- Corrupted data (detected via data quality checks)
- Missing required fields
- Stale or invalid data

**Alert on:**
- High error rates
- Repeated failures
- Quality degradation

## Example Interactions with Chaos

### Scenario 1: Tool Failure

```
You: What's the price of AAPL?

Agent: [Tries to call get_stock_price tool]
       [🔥 API fails with timeout]
       
       I apologize, but I'm currently unable to retrieve the 
       stock price due to a technical issue (Stock Price API 
       timeout after 30 seconds). Please try again in a moment.
```

### Scenario 2: Number Transposition (Hallucination)

```
You: What's the price of NVDA?

Agent: [Calls tool, gets price: $189.11]
       [🔥 Transposes to: $198.11]
       
       The current price of NVIDIA (NVDA) is $198.11 per share.
       ❌ HALLUCINATION! Actual price was $189.11
```

### Scenario 3: Data Corruption

```
You: Get me the price of TSLA

Agent: [Calls tool, gets price: $438.69]
       [🔥 Corrupts to 2x: $877.38]
       
       Tesla (TSLA) is trading at $877.38 per share.
       ❌ WRONG! Actual price is $438.69
```

### Scenario 4: RAG Disconnect

```
You: What was Costco's Q3 revenue?

Agent: [Tries to use RAG]
       [🔥 RAG disconnected]
       
       I apologize, but I'm unable to access the document database 
       at this moment. I don't have that information available.
```

### Scenario 5: Multiple Chaos Events

```
You: Buy 10 shares of AAPL

Agent: [Gets price: $258.06]
       [🔥 Transposes to: $285.06 in response]
       [🔥 Also corrupts data: wrong ticker]
       
       Transaction Details:
       - Stock: XXXX  ← Wrong ticker!
       - Shares: 10
       - Price: $285.06/share  ← Transposed!
       - Total: $2,860.60  ← Wrong calculation!
       
       Do you wish to proceed?
       
       ❌ MULTIPLE ISSUES! Galileo should flag this!
```

## Patterns Created for Galileo Insights

### Pattern 1: Intermittent Failures

**What**: 25% of API calls fail
**Insight**: "API reliability issues detected"
**Recommendation**: "Implement retry logic, consider backup data source"

### Pattern 2: Numerical Hallucinations

**What**: 30% of responses have transposed numbers
**Insight**: "High rate of factual inaccuracies in numerical data"
**Recommendation**: "Add validation guardrail for numerical outputs"

### Pattern 3: Data Quality Issues

**What**: 20% of responses have corrupted data
**Insight**: "Inconsistent data from API responses"
**Recommendation**: "Implement data validation before presenting to user"

### Pattern 4: RAG Degradation

**What**: 20% of attempts missing RAG
**Insight**: "Vector database connectivity issues"
**Recommendation**: "Add health checks, implement caching"

### Pattern 5: Rate Limiting

**What**: 15% of calls hit rate limits
**Insight**: "API quota being exceeded"
**Recommendation**: "Implement request throttling or upgrade API tier"

## Testing Scenarios

### Test 1: Detect Hallucinations

```
1. Enable: 🔢 Sloppiness
2. Ask 10 times: "What's the price of AAPL?"
3. Check Galileo: 3-4 should have transposed numbers
4. Insights should flag numerical inconsistencies
```

### Test 2: API Reliability

```
1. Enable: 🔌 Tool Instability
2. Run experiment with 20 rows
3. Check Galileo: ~5 should have API failures
4. Insights should recommend retry logic
```

### Test 3: Data Validation

```
1. Enable: 💥 Data Corruption
2. Ask: "Get price and buy 10 shares of TSLA"
3. Chaos might corrupt price in confirmation
4. Guardrails should flag inconsistent data
```

### Test 4: Multi-Chaos Stress Test

```
1. Enable ALL chaos modes
2. Run experiment with dataset
3. See variety of failures
4. Insights should detect multiple patterns
```

## Configuration

### Chaos Rates (Adjustable in code)

```python
# In chaos_engine.py
chaos.tool_failure_rate = 0.25      # 25% API failures
chaos.sloppiness_rate = 0.30        # 30% number errors
chaos.rag_failure_rate = 0.20       # 20% RAG disconnects
chaos.rate_limit_rate = 0.15        # 15% rate limits
chaos.data_corruption_rate = 0.20   # 20% data corruption
```

### Via UI

Currently rates are fixed, but you can enable/disable each mode independently.

## Real-World Equivalents

| Chaos Mode | Real-World Scenario |
|------------|---------------------|
| Tool Instability | AWS outage, network partition, DDoS attack |
| Sloppiness | LLM hallucination, float precision errors |
| RAG Disconnects | Vector DB crash, network split, index corruption |
| Rate Limits | API quota exceeded, throttling |
| Data Corruption | Bad data from source, parsing errors, stale cache |

## Benefits for Testing

### 1. Observability Testing

**Shows Galileo can detect:**
- Anomalous patterns
- Quality degradation
- Infrastructure issues
- Data inconsistencies

### 2. Guardrails Testing

**Shows guardrails can block:**
- Hallucinated numbers
- Corrupted data
- Stale information
- Invalid responses

### 3. Insights Testing

**Shows insights can recommend:**
- Retry logic for intermittent failures
- Validation for numerical outputs
- Caching strategies
- Fallback mechanisms
- Infrastructure improvements

### 4. Resilience Testing

**Shows how agent handles:**
- Partial failures
- Degraded service
- Invalid data
- Missing components

## Monitoring Chaos

### In UI

**Sidebar shows:**
- Number of active chaos modes
- Stats for each mode (how many times triggered)
- Reset button for statistics

### In Logs

Watch for chaos injections:
```
🔥 CHAOS: Injecting API failure for Stock Price API
🔥 CHAOS: Number transposition - '258' → '285'
🔥 CHAOS: RAG disconnected - Vector database connection timeout
🔥 CHAOS: Injecting rate limit error
🔥 CHAOS: Corrupted price 258.06 → 516.12
```

### In Galileo Console

**Traces will show:**
- Tool errors when APIs fail
- Incorrect outputs when numbers transposed
- Missing RAG spans when disconnected
- Rate limit error messages
- Corrupted data in tool outputs

## Use Cases

### Demo Scenario 1: Show Observability

```
1. Enable: Tool Instability + Sloppiness
2. Run experiment with 20 rows
3. Show Galileo Console
4. Point out detected anomalies
5. Show Insights recommendations
```

### Demo Scenario 2: Test Guardrails

```
1. Configure guardrail: Block if numerical mismatch
2. Enable: Sloppiness
3. Ask: "What's AAPL price?"
4. If transposed, guardrail should block
5. Show prevention in action
```

### Demo Scenario 3: Resilience Testing

```
1. Enable ALL chaos modes
2. Have conversation with agent
3. Show how it handles failures gracefully
4. Point out error handling in traces
```

### Demo Scenario 4: Insights Discovery

```
1. Enable: Sloppiness
2. Run large experiment (50+ rows)
3. Wait for Galileo Insights to analyze
4. Show discovered patterns
5. Show recommendations
```

## Advanced: Custom Chaos

You can modify chaos rates in the code:

```python
from chaos_engine import get_chaos_engine

chaos = get_chaos_engine()
chaos.tool_failure_rate = 0.50  # 50% failures (more aggressive)
chaos.sloppiness_rate = 0.10     # 10% errors (less aggressive)
```

## Expected Galileo Insights

With chaos enabled, Galileo Insights should detect:

### High-Confidence Patterns

1. **"Elevated error rate in stock_price_api tool"**
   - Triggered by: Tool Instability
   - Confidence: High
   - Recommendation: "Implement retry logic with exponential backoff"

2. **"Numerical hallucinations detected in agent responses"**
   - Triggered by: Sloppiness
   - Confidence: High
   - Recommendation: "Add guardrail to validate numerical outputs against tool data"

3. **"RAG retrieval failures affecting response quality"**
   - Triggered by: RAG Chaos
   - Confidence: Medium-High
   - Recommendation: "Add fallback mechanism when vector DB unavailable"

### Medium-Confidence Patterns

4. **"Inconsistent data quality from external APIs"**
   - Triggered by: Data Corruption
   - Confidence: Medium
   - Recommendation: "Implement data validation layer"

5. **"Rate limiting impacting user experience"**
   - Triggered by: Rate Limit Chaos
   - Confidence: Medium
   - Recommendation: "Consider caching or upgrading API tier"

## Observability Showcase

### What to Show in Demos

**Traces Tab:**
- Show failed tool calls with error messages
- Point out missing RAG spans (when disconnected)
- Highlight latency spikes

**Experiments Tab:**
- Show error rate statistics
- Compare chaos vs. non-chaos experiments
- Show quality degradation metrics

**Insights Tab:**
- Show automatically detected patterns
- Highlight recommendations
- Demonstrate AI-powered analysis

## Safety Notes

### For Demos

✅ **Safe to use in demos** - chaos is controlled and predictable  
✅ **Easy to toggle off** - disable any time via UI  
✅ **Doesn't affect system** - only simulates failures  
✅ **Reset statistics** - clean slate for each demo  

### For Production

⚠️ **DO NOT enable in production** - this is for testing only!  
⚠️ **Causes intentional failures** - will degrade user experience  
⚠️ **Simulates hallucinations** - returns incorrect data  

## Quick Start

### 1. Enable One Chaos Mode

```
Sidebar → Chaos Engineering → Enable "🔢 Sloppiness"
```

### 2. Test It

```
Ask: "What's the price of AAPL?"
Repeat 5-10 times
```

**Expected**: 3-4 responses will have transposed numbers

### 3. Check Galileo

<<<<<<< Updated upstream
- Go to traces
- Look for inconsistencies
- Wait for Insights to analyze
=======
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

### 2. 🔢 Sloppiness

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

### 3. 💥 Data Corruption

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

### 4. 📚 RAG Disconnects

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
- Returns realistic vector DB errors (PostgreSQL, ChromaDB, embedding failures)
- Allows testing agent behavior without context

---

### 5. ⏱️ Rate Limits

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
>>>>>>> Stashed changes

## Chaos Statistics

The UI shows real-time stats:

```
Active Chaos:
🔌 Tool Instability
🔢 Sloppiness (3 so far)
📚 RAG Chaos (1 so far)
⏱️ Rate Limits
💥 Data Corruption

🔥 5 chaos mode(s) active
```

**Reset button** clears counters for fresh testing.

## Summary

| Mode | Rate | Detects | Recommends |
|------|------|---------|------------|
| 🔌 Tool Instability | 25% | API reliability | Retry logic |
| 🔢 Sloppiness | 30% | Hallucinations | Validation guardrails |
| 📚 RAG Disconnects | 20% | Missing context | Fallback mechanisms |
| ⏱️ Rate Limits | 15% | Quota issues | Caching/throttling |
| 💥 Data Corruption | 20% | Data quality | Validation layer |

**Purpose**: Create realistic failure scenarios to showcase Galileo's detection and remediation capabilities.

**Try it**: Enable chaos modes and watch Galileo Insights discover patterns! 🔍

---

**Files:**
- 🔥 `chaos_engine.py` - Chaos logic
- 🎛️ `app.py` - UI controls
- 🛠️ `domains/finance/tools/logic.py` - Chaos integration
- 🤖 `agent_frameworks/langgraph/agent.py` - Response corruption
- 📖 `CHAOS_ENGINEERING.md` - This guide

