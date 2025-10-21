# Chaos Tools Quick Start

## What Are Chaos Tools?

Deliberately confusing tools that demonstrate Galileo's observability value by creating realistic problems that are hard to debug without proper observability.

## Quick Enable

```bash
export USE_CHAOS_TOOLS=true
```

## What Happens

- **Normal**: 5 well-behaved tools
- **Chaos Mode**: 22 tools (5 standard + 17 chaos variants)

The agent now faces realistic tool proliferation with subtle issues.

## The 17 Chaos Tools

| Tool | Issue | Demonstrates |
|------|-------|--------------|
| `get_stock_price_fast` | Returns minimal data | Incomplete responses |
| `fetch_stock_price` | No fallback handling | Brittle integrations |
| `lookup_stock_price` | Returns string not JSON | Format inconsistency |
| `get_stock_data` | Different JSON structure | Breaking changes |
| `get_current_stock_price` | 2 second delay | Performance issues |
| `get_stock_price_accurate` | 1-5 second random delay | Unpredictable latency |
| `retrieve_stock_price` | 10% wrong ticker | Intermittent bugs |
| `query_stock_price` | 5% data corruption | Data quality issues |
| `get_multiple_stock_prices` | 500ms per ticker | Inefficiency |
| `get_stock_with_news` | Two separate calls | Poor optimization |
| `get_stock_price_v2` | Wrapped in v2 metadata | API versioning |
| `get_stock_price_unstable_schema` | 30% different schema | Version drift |
| `get_stock_price_evolving` | 20% surprise fields | Schema evolution |
| `get_stock_price_deprecated` | 15% missing fields | Field deprecation |
| `get_stock_price_breaking_change` | 10% type changes | Breaking changes |
| `get_stock_price_yfinance_direct` | No fallback | Direct API risk |
| `get_stock_price_alpha_vantage_direct` | Requires API key | Configuration dependency |

**Note:** All chaos tools still log to Galileo for proper observability!

### 🔥 NEW: Pattern 6 - API Schema Evolution

The 5 newest chaos tools simulate real-world API changes:
- **Version drift** during rolling deployments
- **Breaking changes** that slip through
- **Schema evolution** with undocumented fields
- **Deprecation chaos** during transitions
- **Type changes** without versioning

## Quick Demo

```bash
# Run the interactive demo
python demo_chaos_tools.py
```

This shows all 6 chaos patterns in action!

## Use in Experiments

```bash
# Enable chaos tools
export USE_CHAOS_TOOLS=true

# Run your experiment
streamlit run app.py
# or
python run_experiment.py
```

## Key Demo Points

1. **Tool Proliferation**: Agent faces 22 similar tools instead of 5
2. **API Schema Changes**: 30% chance of different response format
3. **Performance Impact**: Some tools add 2-5 seconds latency
4. **Subtle Bugs**: 5-15% failure rate that's hard to catch
5. **Data Quality**: Incomplete, malformed, or evolving responses
6. **Breaking Changes**: Field types change, fields disappear
7. **Value Proposition**: Galileo makes all of this visible!

**All tools log to Galileo** - showing that even with full observability, tool proliferation and API evolution create real challenges.

## Disable

```bash
export USE_CHAOS_TOOLS=false
# or
unset USE_CHAOS_TOOLS
```

## Full Documentation

See [`CHAOS_TOOLS_GUIDE.md`](CHAOS_TOOLS_GUIDE.md) for complete details.

