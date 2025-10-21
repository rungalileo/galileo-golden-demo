# Galileo Error Logging Fix - Status Codes Now Visible!

## Problem

Status codes from API errors were not appearing in Galileo traces because:

1. **Manual logging doesn't work with LangGraph** - LangGraph uses callbacks, not manual `GalileoLogger`
2. **The `galileo_logger` parameter was None** - Not passed through by LangGraph agent framework
3. **Metadata was lost** - Standard exceptions don't carry structured metadata

## Solution

Created a **custom `APIError` exception class** that embeds metadata directly in the error message string, making it searchable in Galileo.

### Custom Exception Class

```python
class APIError(Exception):
    """Custom exception for API errors with searchable metadata"""
    def __init__(self, message: str, status_code: str = "500", 
                 error_type: str = "network_failure", **kwargs):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.metadata = kwargs
        self.metadata['status_code'] = status_code
        self.metadata['error_type'] = error_type
    
    def __str__(self):
        # Format: [STATUS_CODE] message | metadata as key=value
        metadata_str = " | ".join([f"{k}={v}" for k, v in self.metadata.items()])
        return f"[{self.status_code}] {super().__str__()} | {metadata_str}"
```

### Error Format

Errors now appear in Galileo as:
```
[500] Stock Price API internal error (500 Internal Server Error) | ticker=AAPL | chaos_injected=True | status_code=500 | error_type=network_failure
```

## Searchability in Galileo

### Search by Status Code

**By visual tag:**
- Search: `[500]` - All 500 errors
- Search: `[429]` - All rate limit errors
- Search: `[503]` - All service unavailable errors
- Search: `[timeout]` - All timeout errors

**By metadata field:**
- Search: `status_code=500`
- Search: `status_code=503`
- Search: `status_code=timeout`

### Search by Error Type

- Search: `error_type=network_failure` - Network/API errors
- Search: `error_type=rate_limit` - Rate limiting errors

### Search by Context

- Search: `ticker=AAPL` - Errors for specific ticker
- Search: `chaos_injected=True` - Only simulated errors
- Search: `chaos_injected=False` - Only real errors

### Complex Queries

- `[500] AND ticker=AAPL` - 500 errors for AAPL
- `error_type=network_failure AND chaos_injected=True` - Simulated network errors
- `[429] OR [503]` - Rate limits or service unavailable

## Example Error Messages

### 1. Internal Server Error (500)
```
[500] Stock Price API internal error (500 Internal Server Error) | 
ticker=AAPL | chaos_injected=True | status_code=500 | error_type=network_failure
```

### 2. Rate Limit (429)
```
[429] Rate limit exceeded for Stock Price API. Please try again later. | 
ticker=MSFT | chaos_injected=True | status_code=429 | error_type=rate_limit
```

### 3. Service Unavailable (503)
```
[503] Stock Price API temporarily unavailable (503 Service Unavailable) | 
ticker=GOOGL | chaos_injected=True | status_code=503 | error_type=network_failure
```

### 4. Connection Timeout
```
[timeout] Stock Price API timeout after 30 seconds (Connection Timeout) | 
ticker=AMZN | chaos_injected=True | status_code=timeout | error_type=network_failure
```

## How It Works

### 1. Chaos Engine Triggers Error
```python
should_fail, error_msg = chaos.should_fail_api_call("Stock Price API")
# error_msg = "Stock Price API internal error (500 Internal Server Error)"
```

### 2. Extract Status Code
```python
status_code = _extract_status_code(error_msg)
# status_code = "500"
```

### 3. Raise Structured Exception
```python
raise APIError(
    error_msg,
    status_code=status_code,
    error_type="network_failure",
    ticker=ticker,
    chaos_injected=True
)
```

### 4. Galileo Captures Full Error String
```
[500] Stock Price API internal error (500 Internal Server Error) | 
ticker=AAPL | chaos_injected=True | status_code=500 | error_type=network_failure
```

## Benefits

### ✅ 1. No Manual Logging Needed
- Works automatically with LangChain/LangGraph callbacks
- No need to pass `galileo_logger` parameter
- No special configuration required

### ✅ 2. Fully Searchable
- Status codes in error message string
- Metadata embedded as `key=value` pairs
- Can search/filter in Galileo UI

### ✅ 3. Rich Context
- Includes ticker symbol
- Shows if chaos-injected vs real error
- Error type classification
- All metadata preserved

### ✅ 4. Clean Code
- Single custom exception class
- Simple to use: just raise `APIError(...)`
- No complex logging logic

### ✅ 5. Backwards Compatible
- Still raises exception (agent sees failure)
- Error message includes all info
- No changes needed to agent code

## Viewing in Galileo

### 1. Find All Network Errors
```
Filter spans by: error
Look for: [500], [503], [502], [504], [timeout]
```

### 2. Analyze Error Distribution
```
Group by: Extract status code from error message
Chart: Pie chart of error types
```

### 3. Track Rate Limits
```
Search: [429]
Count occurrences over time
See which tickers trigger rate limits
```

### 4. Debug Specific Issues
```
Search: ticker=AAPL AND [500]
See all 500 errors for AAPL
Check timestamps, patterns
```

### 5. Compare Chaos vs Real Errors
```
Filter 1: chaos_injected=True
Filter 2: chaos_injected=False
Compare error rates and types
```

## Migration from Old Code

### Before (Didn't Work)
```python
# Tried to manually log - but galileo_logger was None!
if galileo_logger:
    galileo_logger.add_tool_span(...)
raise Exception(error_msg)
```

### After (Works!)
```python
# Custom exception with embedded metadata
raise APIError(
    error_msg,
    status_code="500",
    error_type="network_failure",
    ticker=ticker,
    chaos_injected=True
)
```

## Testing

Enable chaos mode and run queries:

```python
# Enable Tool Instability
chaos.enable_tool_instability(True)

# Run queries
for i in range(10):
    try:
        agent.chat("What's the price of AAPL?")
    except Exception as e:
        print(f"Error: {e}")
```

**In Galileo:**
- Go to traces
- Search for `[500]` or `[503]` or `[429]`
- Click into failed spans
- See full error message with status code and metadata

## Technical Details

### Why This Works

1. **LangChain Callbacks**: Automatically capture exceptions
2. **Error Message**: String repr includes all metadata
3. **Searchable Format**: `key=value` pairs in error string
4. **Visual Tags**: `[status_code]` prefix for easy spotting

### Exception Attributes

The `APIError` class exposes:
- `e.status_code` - HTTP status code (string)
- `e.error_type` - Error category (string)
- `e.metadata` - Dict of all metadata
- `str(e)` - Full formatted message

### Status Code Extraction

Supports:
- HTTP codes: 500, 502, 503, 504, 401, 403, 404, 405, 429
- Error types: timeout, ssl_error, dns_error, invalid_response
- Default: "500" for unknown errors

## Summary

### ✅ Problem Solved
- Status codes NOW visible in Galileo traces
- Fully searchable and filterable
- Rich metadata included
- Works automatically with LangGraph

### ✅ How to Use
1. Chaos mode generates errors
2. Errors automatically include status codes
3. Search/filter in Galileo UI
4. No code changes needed!

### ✅ Example Searches in Galileo
- `[500]` - All 500 errors
- `status_code=503` - Service unavailable
- `error_type=rate_limit` - Rate limits
- `ticker=AAPL AND [500]` - Specific ticker errors

**Ready for demos showing comprehensive error tracking!** 🎉

