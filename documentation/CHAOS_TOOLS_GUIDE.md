# Chaos Tools Guide

## Overview

The `chaos_tools.py` module contains deliberately confusing tools designed to demonstrate the value of Galileo's observability platform. These tools look similar to the standard tools but have subtle issues that are hard to spot without proper observability.

## Purpose

Use chaos tools to showcase how Galileo helps identify:
1. **Suboptimal tool choices** - Agent picks wrong similar-looking tool
2. **Performance bottlenecks** - Unnecessary latency and inefficient calls
3. **Subtle data corruption** - Random bugs that only appear sometimes
4. **Error-prone paths** - Tools without proper fallback handling
5. **Data quality issues** - Incomplete or malformed responses

**Note:** All tools log to Galileo for proper observability!

## Enabling Chaos Tools

Set the environment variable:

```bash
export USE_CHAOS_TOOLS=true
```

Or in your `.streamlit/secrets.toml`:

```toml
USE_CHAOS_TOOLS = "true"
```

When enabled, **17 additional confusing tools** are added alongside the 5 standard tools, giving the agent 22 tools to choose from!

## The 7 Chaos Patterns

**Note:** All chaos tools still log to Galileo! This ensures proper observability while demonstrating other common issues.

### Pattern 1: Tools With Missing Fallbacks or Minimal Data

**Tools:**
- `get_stock_price_fast()` - Returns minimal data structure (loses metadata)
- `fetch_stock_price()` - No fallback handling

**What This Demonstrates:**
- Missing fallback mechanisms leading to failures
- Incomplete data structures that lose important metadata
- Brittle integrations without graceful degradation

**Expected Agent Behavior:**
- Agent might pick "fast" variant thinking it's better
- Responses work but lack crucial metadata (volume, high/low, etc.)
- Failures when live data unavailable and no fallback exists
- Galileo shows successful calls but with incomplete data

---

### Pattern 2: Tools With Different Return Formats

**Tools:**
- `lookup_stock_price()` - Returns plain string "178.72" instead of JSON
- `get_stock_data()` - Returns camelCase JSON instead of snake_case

**What This Demonstrates:**
- Breaking changes in data format
- Downstream parsing failures
- Agent confusion when data doesn't match expected format

**Expected Agent Behavior:**
- Agent calls this tool successfully
- Tries to parse response and fails
- May hallucinate data when parsing fails
- Galileo shows the tool succeeded but agent failed to use output

---

### Pattern 3: Tools With Artificial Latency

**Tools:**
- `get_current_stock_price()` - 2 second fixed delay
- `get_stock_price_accurate()` - 1-5 second random delay

**What This Demonstrates:**
- Performance bottlenecks
- Unpredictable response times
- Total request duration inflation

**Expected Agent Behavior:**
- Agent picks "accurate" variant thinking it's better
- User experiences slow responses
- Galileo's duration tracking shows the bottleneck clearly

---

### Pattern 4: Tools With Subtle Bugs

**Tools:**
- `retrieve_stock_price()` - 10% chance returns wrong ticker
- `query_stock_price()` - 5% chance corrupts price/change/volume

**What This Demonstrates:**
- Intermittent bugs that are hard to reproduce
- Data corruption that looks valid
- Need for data validation and monitoring

**Expected Agent Behavior:**
- Most calls work fine, making bug hard to spot
- Occasionally gives wrong information
- Galileo logs show input vs output mismatch
- Can correlate user reports with specific tool calls

---

### Pattern 5: Inefficient But Working Tools

**Tools:**
- `get_multiple_stock_prices()` - 500ms delay per ticker
- `get_stock_with_news()` - Makes two separate inefficient calls

**What This Demonstrates:**
- Suboptimal tool selection
- N+1 query problems
- Wasted API calls and latency

**Expected Agent Behavior:**
- Agent might use `get_multiple_stock_prices()` for single ticker
- Uses `get_stock_with_news()` instead of two separate calls when not needed
- Galileo shows duration and helps optimize tool selection

---

### Pattern 6: API Schema Evolution (NEW! 🔥)

**Tools:**
- `get_stock_price_v2()` - Wraps response in v2 metadata layer
- `get_stock_price_unstable_schema()` - 30% chance returns different schema
- `get_stock_price_evolving()` - 20% chance adds surprise fields
- `get_stock_price_deprecated()` - 15% chance removes deprecated fields
- `get_stock_price_breaking_change()` - 10% chance changes field types

**What This Demonstrates:**
- **Version drift** - API returns mix of old/new formats during rollouts
- **Breaking changes** - Fields disappear or change types unexpectedly
- **Schema evolution** - New undocumented fields appear without warning
- **Deprecation chaos** - Fields randomly missing during transition periods
- **Type changes** - Numbers become strings, floats truncate to ints

**Real-World Scenarios:**
- **Rolling deployments**: Some servers on v1, some on v2
- **A/B testing**: Different response formats for different users
- **Beta features**: New fields randomly appear for testing
- **Deprecation periods**: Old fields gradually removed
- **Breaking migrations**: Type changes without proper versioning

**Expected Agent Behavior:**
- First request works, second request fails due to schema change
- Agent gets confused when response structure varies
- Parsing breaks when field types change
- New fields cause unexpected behavior
- Missing fields cause errors in downstream logic
- Galileo traces show exact schema differences between calls

**Why This Is Sneaky:**
These are THE MOST realistic API problems that happen in production:
- During rolling deployments
- During API migrations
- During deprecation periods
- During beta testing
- After breaking changes slip through

This demonstrates Galileo's value in catching:
- Schema inconsistencies across requests
- Breaking changes in real-time
- Field deprecation issues
- Type mismatches
- Version drift problems

---

### Pattern 7: Direct API Access (Bypasses Wrappers)

**Tools:**
- `get_stock_price_yfinance_direct()` - Direct yfinance call, no fallback
- `get_stock_price_alpha_vantage_direct()` - Requires API key, no fallback

**What This Demonstrates:**
- Brittle integrations without error handling
- Missing fallback mechanisms
- API dependency failures

**Expected Agent Behavior:**
- Agent might pick specific provider thinking it's better
- Fails when that provider is unavailable
- Should have used wrapper with fallback logic
- Galileo shows failure rate by tool choice

---

## Comparison: Standard vs Chaos Tools

| Feature | Standard Tools | Chaos Tools |
|---------|---------------|-------------|
| **Count** | 5 tools | +17 chaos tools (22 total) |
| **Galileo Logging** | ✅ Always logged | ✅ Always logged |
| **Fallback Handling** | ✅ Mock data fallback | ❌ Some fail without fallback |
| **Return Format** | ✅ Consistent JSON | ⚠️ Mixed formats |
| **Data Completeness** | ✅ Full metadata | ⚠️ Some return minimal data |
| **Performance** | ✅ Optimized | ⚠️ Artificial delays |
| **Reliability** | ✅ Always correct | ⚠️ Intermittent bugs |
| **API Robustness** | ✅ Graceful degradation | ❌ Direct API calls |

## Running Experiments With Chaos Tools

### Example 1: Compare Tool Selection

```bash
# Run without chaos tools (baseline)
export USE_CHAOS_TOOLS=false
python run_experiment.py

# Run with chaos tools
export USE_CHAOS_TOOLS=true
python run_experiment.py
```

Then compare in Galileo:
- Which tools were selected?
- Were any calls missing from traces?
- What was the average duration?
- Any failures or anomalies?

### Example 2: Showcase Observability Gaps

```python
# In your demo script
import os
os.environ["USE_CHAOS_TOOLS"] = "true"

# Ask agent the same question multiple times
queries = [
    "What's the current price of AAPL?",
    "Get me the stock price for Apple",
    "Look up AAPL stock price",
]

# Agent might use different tools each time
# Some calls won't appear in Galileo (the ones that skip logging)
```

### Example 3: Performance Analysis

```python
# Enable chaos tools
os.environ["USE_CHAOS_TOOLS"] = "true"

# Ask questions that trigger different tools
results = []
for ticker in ["AAPL", "MSFT", "GOOGL"]:
    start = time.time()
    response = agent.chat(f"What's the price of {ticker}?")
    duration = time.time() - start
    results.append(duration)

# Some queries will be much slower (if agent picks slow tools)
# Galileo will show exactly which tools caused the slowdown
```

## Key Takeaways for Demos

1. **Tool Proliferation**: Shows how too many similar tools confuse LLMs
2. **Performance Impact**: Demonstrates how tool choice affects latency
3. **Data Quality**: Shows subtle bugs and incomplete data that only observability catches
4. **Error Handling**: Reveals brittle integrations without fallbacks
5. **Format Inconsistencies**: Highlights parsing issues from varied response formats

**All tools log to Galileo** - demonstrating that even with full observability, tool proliferation creates real problems that need to be tracked and optimized.

## Disabling Chaos Tools

```bash
export USE_CHAOS_TOOLS=false
# or
unset USE_CHAOS_TOOLS
```

The system automatically falls back to the 5 standard, well-behaved tools.

## Tool Selection Matrix

When an agent sees "get stock price" functionality, it now has 18+ tools to choose from:

1. ✅ `get_stock_price()` - **The correct choice** (has everything)
2. ⚠️ `get_stock_price_fast()` - Minimal data
3. ⚠️ `fetch_stock_price()` - No fallback
4. ⚠️ `lookup_stock_price()` - Wrong format
5. ⚠️ `get_stock_data()` - Different structure
6. ⚠️ `get_current_stock_price()` - 2s delay
7. ⚠️ `get_stock_price_accurate()` - Random delay
8. ⚠️ `retrieve_stock_price()` - 10% wrong ticker
9. ⚠️ `query_stock_price()` - 5% data corruption
10. ⚠️ `get_multiple_stock_prices()` - Inefficient
11. ⚠️ `get_stock_price_v2()` - Wrapped format
12. ⚠️ `get_stock_price_unstable_schema()` - Schema varies
13. ⚠️ `get_stock_price_evolving()` - Surprise fields
14. ⚠️ `get_stock_price_deprecated()` - Fields missing
15. ⚠️ `get_stock_price_breaking_change()` - Type changes
16. ⚠️ `get_stock_price_yfinance_direct()` - Brittle
17. ⚠️ `get_stock_price_alpha_vantage_direct()` - Brittle

**Without Galileo**: Hard to know which was used or why it failed

**With Galileo**: See exactly which tool was called, its inputs/outputs, duration, and success rate

## Best Practices for Demos

1. **Start Clean**: Show baseline with USE_CHAOS_TOOLS=false
2. **Enable Chaos**: Turn on chaos tools and run same queries
3. **Compare Traces**: Show side-by-side in Galileo
4. **Highlight Issues**: Point out missing traces, slow calls, wrong data
5. **Resolution**: Show how Galileo helped identify the problem

---

## Questions?

This demonstrates how real-world systems accumulate technical debt:
- Multiple similar tools (different teams, legacy code, etc.)
- Some missing observability
- Some with performance issues
- Some with subtle bugs

Galileo makes it visible and debuggable!

