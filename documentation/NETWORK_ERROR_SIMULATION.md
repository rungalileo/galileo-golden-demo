# Network Error Simulation with Galileo Observability

## Overview

The chaos engine now simulates **comprehensive, realistic HTTP errors** that are properly logged to Galileo with detailed metadata. This demonstrates how Galileo helps debug network failures in production.

## ✅ What's Implemented

### HTTP Error Simulation

**Tool Instability Mode** (25% failure rate) simulates:

#### Server Errors (5xx)
- ✅ **500 Internal Server Error** - Server-side failures
- ✅ **502 Bad Gateway** - Upstream server issues
- ✅ **503 Service Unavailable** - Server overload/maintenance
- ✅ **504 Gateway Timeout** - Upstream timeout

#### Client Errors (4xx)
- ✅ **401 Unauthorized** - Authentication failures
- ✅ **403 Forbidden** - Permission denied
- ✅ **404 Not Found** - Resource missing
- ✅ **405 Method Not Allowed** - Wrong HTTP method
- ✅ **429 Too Many Requests** - Rate limiting (separate chaos mode)

#### Network/Connection Errors
- ✅ **Connection Timeout** - Network delays
- ✅ **Connection Refused** - Server not responding
- ✅ **DNS Resolution Failed** - Domain not found
- ✅ **SSL Certificate Failed** - Certificate issues
- ✅ **Connection Reset** - TCP connection dropped
- ✅ **Network Unreachable** - Route to host failed

#### Response/Data Errors
- ✅ **Malformed JSON** - Invalid response format
- ✅ **Empty Response** - 204 No Content
- ✅ **Wrong Content-Type** - Expected JSON, got HTML

## 🔥 Galileo Logging

### What Gets Logged

Every error is logged to Galileo with **detailed metadata**:

```python
{
  "input": {"ticker": "AAPL"},
  "output": {
    "error": "Stock Price API internal error (500 Internal Server Error)",
    "success": false
  },
  "metadata": {
    "ticker": "AAPL",
    "error": "true",
    "error_type": "network_failure",
    "status_code": "500",
    "chaos_injected": "true",
    "failure_rate": "25%"
  },
  "tags": [
    "stocks",
    "price", 
    "error",
    "chaos",
    "status_500"
  ],
  "duration_ns": 1500000  // 1.5ms
}
```

### Metadata Fields

| Field | Description | Example Values |
|-------|-------------|----------------|
| `error` | Error occurred | `"true"` |
| `error_type` | Category of error | `"network_failure"`, `"rate_limit"` |
| `status_code` | HTTP status or error type | `"500"`, `"503"`, `"timeout"`, `"ssl_error"` |
| `chaos_injected` | Simulated failure | `"true"` |
| `failure_rate` | Probability of failure | `"25%"`, `"15%"` |

### Tags for Filtering

Each error gets tagged for easy filtering in Galileo:
- `error` - All errors
- `chaos` - Chaos-injected errors
- `status_XXX` - Specific status code (e.g., `status_500`, `status_503`)
- `rate_limit` - Rate limit errors specifically
- `network_failure` - Network-related errors

## 📊 What This Demonstrates

### In Galileo UI, you can:

1. **Track Error Rates by Status Code**
   - Filter by `status_500`, `status_503`, etc.
   - See which errors occur most frequently
   - Compare error rates across time

2. **Analyze Failure Patterns**
   - Group by `error_type` metadata
   - Identify if failures are network, auth, or rate-limit
   - Spot patterns in when failures occur

3. **Debug Specific Errors**
   - Click into any failed span
   - See exact error message
   - View request context (ticker, parameters)
   - Check duration to spot timeouts

4. **Monitor Error Recovery**
   - See how agent handles different error types
   - Track retry logic
   - Identify which errors are recoverable

## 🎯 Demo Scenarios

### Scenario 1: Network Outage

```python
# Enable Tool Instability
os.environ["CHAOS_TOOL_INSTABILITY"] = "true"

# Query same stock 10 times
for i in range(10):
    try:
        response = agent.chat("What's the price of AAPL?")
    except Exception as e:
        print(f"Call {i+1}: {e}")
```

**In Galileo:**
- See ~2-3 failures (25% rate)
- Mix of 500, 503, timeout errors
- Each failure logged with full context
- Compare duration of successful vs failed calls

### Scenario 2: Rate Limiting

```python
# Enable Rate Limit Chaos
os.environ["CHAOS_RATE_LIMIT"] = "true"

# Rapid-fire requests
for i in range(20):
    agent.chat(f"Get price for {ticker}")
```

**In Galileo:**
- Filter by `rate_limit` tag
- See 429 errors scattered through requests
- Track which requests got rate-limited
- Analyze rate limit patterns

### Scenario 3: Mixed Failures

```python
# Enable multiple chaos modes
os.environ["CHAOS_TOOL_INSTABILITY"] = "true"
os.environ["CHAOS_RATE_LIMIT"] = "true"

# Run experiment
for query in dataset:
    agent.chat(query)
```

**In Galileo:**
- Multiple error types: 500, 503, 429, timeout
- Different error_type metadata
- Can filter/group by any dimension
- See overall error rate vs success rate

## 🔍 Galileo Queries

### Find All Network Errors
```
tags: error, chaos
```

### Find Specific Status Code
```
metadata.status_code: 500
```

### Find Timeout Errors
```
metadata.status_code: timeout
```

### Find Rate Limit Errors
```
tags: rate_limit
```

### Find All 5xx Errors
```
metadata.status_code: (500 OR 502 OR 503 OR 504)
```

### Find SSL Errors
```
metadata.status_code: ssl_error
```

## 📈 Metrics to Track

In Galileo dashboards, track:

1. **Error Rate by Status Code**
   - Group by `metadata.status_code`
   - Chart over time
   - Compare to success rate

2. **Error Type Distribution**
   - Pie chart by `metadata.error_type`
   - Shows network vs auth vs rate-limit

3. **Average Duration by Status**
   - Compare duration_ns for different status codes
   - Timeouts should show higher duration
   - 500s usually fast

4. **Chaos Impact**
   - Filter `metadata.chaos_injected: true`
   - See impact of chaos testing
   - Compare to real errors

## 🎬 Demo Talking Points

### 1. "Real-world network failures happen constantly..."
- Show mix of 500, 503, 504 errors
- Point out different error types
- Demonstrate intermittent failures (25% rate)

### 2. "Without observability, these are invisible..."
- Show error traces in Galileo
- Highlight detailed metadata
- Compare to logs (just says "failed")

### 3. "Galileo shows exactly what failed and why..."
- Click into specific error
- Show status code, error message, duration
- Demonstrate filtering by error type

### 4. "Track patterns over time..."
- Show error rate trending
- Identify if certain times have more errors
- Spot cascading failures

### 5. "Debug production issues faster..."
- Filter to specific status code
- See all instances of that error
- Identify common patterns

## 🚀 Usage

### Enable in UI
```
Sidebar → Chaos Engineering → Chaos Controls
✅ Tool Instability (network errors)
✅ Rate Limits (429 errors)
```

### Enable via Code
```python
from chaos_engine import get_chaos_engine

chaos = get_chaos_engine()
chaos.enable_tool_instability(True)  # 25% failure rate
chaos.enable_rate_limit_chaos(True)  # 15% rate limit
```

### View in Galileo
1. Go to Galileo Console
2. Navigate to your project
3. Filter spans by `tags: error`
4. Group by `metadata.status_code`
5. Analyze patterns!

## 💡 Key Benefits

1. **Comprehensive Error Coverage** - All common HTTP errors simulated
2. **Detailed Metadata** - Status codes, error types, context
3. **Easy Filtering** - Tags and metadata for powerful queries
4. **Realistic Scenarios** - Intermittent failures like production
5. **Proper Observability** - Every error logged with full context

This demonstrates that **even with network failures, Galileo provides complete visibility** into what's happening with your agent!

---

## Technical Details

### Error Extraction
The `_extract_status_code()` helper parses error messages to categorize failures:
- Looks for HTTP status codes (500, 503, etc.)
- Classifies network errors (timeout, ssl_error, dns_error)
- Categorizes response errors (invalid_response)
- Defaults to "500" for unknown errors

### Logging Flow
```
1. Chaos engine decides to fail (25% chance)
2. Generates realistic error message with status code
3. Tool extracts status code from message
4. Logs to Galileo with detailed metadata
5. Raises exception to agent
6. Agent sees failure and can retry/handle
```

### Future Enhancements
Potential additions:
- [ ] Configurable failure rates per status code
- [ ] Simulate transient vs permanent failures
- [ ] Circuit breaker simulation
- [ ] Exponential backoff tracking
- [ ] Error correlation across multiple tools

