# Build Chaos Logs Guide

## Purpose

Generate a large number of agent traces with chaos-induced errors to:
- Build up patterns for Galileo Insights to detect
- Test observability at scale
- Create realistic failure scenarios
- Showcase Galileo's anomaly detection

## Quick Start (30 Seconds!)

```bash
python quick_chaos_demo.py
```

**What this does:**
- Generates 10 test queries
- Runs each query 3 times
- Enables ALL chaos modes
- Creates 30 traces in Galileo
- Includes variety of failures

**Result**: Rich log data perfect for testing Galileo Insights!

## Advanced Usage

### With Galileo Dataset

```bash
# Fetch dataset from Galileo and run with chaos
python build_chaos_logs.py --dataset-name finance-queries --runs 3 --all-chaos
```

**What this does:**
- Fetches your actual dataset from Galileo API
- Runs each row 3 times
- Creates N×3 traces (N = dataset size)

### With Specific Chaos Modes

```bash
# Only number transpositions (hallucinations)
python build_chaos_logs.py --count 20 --runs 3 --sloppiness

# Only API failures
python build_chaos_logs.py --count 20 --runs 3 --tool-instability

# Combination
python build_chaos_logs.py --count 20 --runs 3 --sloppiness --tool-instability
```

### Custom Chaos Rates

```bash
# More aggressive sloppiness (50% instead of 30%)
python build_chaos_logs.py --count 15 --runs 3 --sloppiness --sloppiness-rate 0.5

# Higher API failure rate (50% instead of 25%)
python build_chaos_logs.py --count 15 --runs 3 --tool-instability --tool-failure-rate 0.5
```

## Command Line Options

### Dataset Source

| Option | Description | Example |
|--------|-------------|---------|
| `--dataset-name` | Fetch from Galileo by name | `--dataset-name my-dataset` |
| `--dataset-id` | Fetch from Galileo by ID | `--dataset-id abc123` |
| `--count` | Generate inline queries | `--count 20` |

**Default**: Generates 10 inline queries if none specified

### Execution

| Option | Default | Description |
|--------|---------|-------------|
| `--runs` | 3 | Times to run each query |
| `--delay` | 0.5 | Seconds between runs |

### Chaos Modes

| Flag | Effect | Default Rate |
|------|--------|--------------|
| `--all-chaos` | Enable all modes | - |
| `--tool-instability` | API failures | 25% |
| `--sloppiness` | Number transpositions | 30% |
| `--rag-chaos` | RAG disconnects | 20% |
| `--rate-limit` | Rate limit errors | 15% |
| `--data-corruption` | Data corruption | 20% |

### Chaos Rates (Advanced)

| Option | Default | Range |
|--------|---------|-------|
| `--tool-failure-rate` | 0.25 | 0.0 - 1.0 |
| `--sloppiness-rate` | 0.30 | 0.0 - 1.0 |
| `--rag-failure-rate` | 0.20 | 0.0 - 1.0 |
| `--rate-limit-rate` | 0.15 | 0.0 - 1.0 |
| `--corruption-rate` | 0.20 | 0.0 - 1.0 |

## Examples

### Example 1: Quick Demo Build

```bash
python quick_chaos_demo.py
```

**Creates:**
- 30 traces (10 queries × 3 runs)
- All chaos modes enabled
- Variety of failures

**Time**: ~2-3 minutes

### Example 2: Large Dataset with Chaos

```bash
python build_chaos_logs.py \
  --dataset-name finance-eval-dataset \
  --runs 3 \
  --all-chaos
```

**Creates:**
- N×3 traces (N = dataset size)
- All chaos modes
- Production-like failure patterns

**Time**: ~5-10 minutes for 50-row dataset

### Example 3: Focus on Hallucinations

```bash
python build_chaos_logs.py \
  --count 30 \
  --runs 3 \
  --sloppiness \
  --sloppiness-rate 0.4
```

**Creates:**
- 90 traces (30 queries × 3 runs)
- 40% will have number transpositions
- Perfect for testing hallucination detection

**Time**: ~3-4 minutes

### Example 4: Stress Test

```bash
python build_chaos_logs.py \
  --count 50 \
  --runs 5 \
  --all-chaos \
  --tool-failure-rate 0.4 \
  --sloppiness-rate 0.5
```

**Creates:**
- 250 traces (50 queries × 5 runs)
- Higher chaos rates
- Extreme failure scenarios

**Time**: ~10-15 minutes

## What Gets Logged

### Each Trace Contains

1. **Input**: The query from dataset
2. **Agent Execution**:
   - Tool calls (get_stock_price, etc.)
   - RAG retrievals (if enabled and not disconnected)
   - LLM calls
   - Response generation
3. **Output**: Agent's response (potentially with chaos)
4. **Metadata**:
   - Run number
   - Session ID
   - Chaos flag
5. **Errors** (if chaos triggered):
   - API failures
   - Rate limits
   - RAG failures

### Where to Find

**Galileo Console:**
- Project: `finance-agent-experiments` (or your project)
- Log Stream: `chaos-log-builder`
- Traces: Filter by session ID or time range

## Output During Execution

```
🔥 CHAOS LOG BUILDER
================================================================================

🔥 Chaos Configuration:
   ✓ Tool Instability (rate: 25.0%)
   ✓ Sloppiness (rate: 30.0%)
   ✓ RAG Chaos (rate: 20.0%)

📥 Fetching dataset from Galileo: finance-queries
   ✓ Loaded dataset: finance-queries

📊 Dataset Summary:
   Total queries: 15
   Runs per query: 3
   Total traces to create: 45

🔧 Initializing Galileo session: chaos-a7f3b2c1

🤖 Initializing LangGraph agent for domain: finance
   ✓ Agent initialized with 4 tools

================================================================================
PROCESSING QUERIES
================================================================================

📝 Query 1/15: What's the current price of AAPL?...
   Run 1/3: ✓ Success (156 chars)
   Run 2/3: ❌ FAILED - Stock Price API timeout
   Run 3/3: ✓ Success (162 chars)
   Progress: 3/45 (6.7%)

📝 Query 2/15: Buy 10 shares of NVDA...
   Run 1/3: ✓ Success (245 chars)
   Run 2/3: ✓ Success (238 chars)  ← May have transposed numbers!
   Run 3/3: ❌ FAILED - Rate limit exceeded
   Progress: 6/45 (13.3%)

...
```

## Expected Patterns

After running with chaos, Galileo Insights should detect:

### Pattern 1: API Reliability (Tool Instability)
```
"High failure rate detected in Stock Price API"
Severity: Medium
Affected: 25% of tool calls
Recommendation: Implement retry logic with exponential backoff
```

### Pattern 2: Numerical Hallucinations (Sloppiness)
```
"Numerical inconsistencies detected in agent responses"
Severity: High
Affected: 30% of responses
Recommendation: Add validation guardrail for numerical outputs
```

### Pattern 3: RAG Availability (RAG Chaos)
```
"RAG retrieval failures affecting response quality"
Severity: Medium
Affected: 20% of queries
Recommendation: Implement fallback mechanism for vector DB outages
```

### Pattern 4: Rate Limiting (Rate Limit Chaos)
```
"API rate limits frequently exceeded"
Severity: Low-Medium
Affected: 15% of calls
Recommendation: Implement caching or request throttling
```

### Pattern 5: Data Quality (Data Corruption)
```
"Inconsistent or invalid data from external sources"
Severity: Medium
Affected: 20% of responses
Recommendation: Add data validation before using API responses
```

## Best Practices

### For Galileo Insights Testing

**Recommended:**
```bash
# Generate enough data for pattern detection
python build_chaos_logs.py --count 30 --runs 3 --all-chaos

# Wait 5-10 minutes for Insights to analyze
# Check Insights tab in Galileo Console
```

**Minimum:** 50+ traces for good pattern detection  
**Optimal:** 100+ traces for comprehensive analysis

### For Specific Pattern Testing

**Test hallucinations:**
```bash
python build_chaos_logs.py --count 20 --runs 5 --sloppiness
# Creates: 100 traces, ~30 with transposed numbers
```

**Test API resilience:**
```bash
python build_chaos_logs.py --count 20 --runs 5 --tool-instability
# Creates: 100 traces, ~25 with API failures
```

### For Demo Prep

**Before demo:**
```bash
# Generate logs 30+ minutes before demo
python quick_chaos_demo.py

# Let Galileo Insights analyze
# Prepare to show detected patterns
```

**During demo:**
- Show the log stream with chaos traces
- Navigate to Insights
- Point out detected patterns
- Show recommendations

## Monitoring Progress

The script shows real-time progress:
- ✓ = Successful run
- ❌ = Failed run (chaos triggered)
- Progress percentage
- Chaos statistics at the end

## Troubleshooting

### "No module named 'galileo'"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "Failed to start Galileo session"

Check API key:
```bash
cat .streamlit/secrets.toml | grep galileo_api_key
```

### "Chaos not triggering"

Chaos is probabilistic. With default rates:
- Run 10 queries → expect ~3 chaos events
- Run 50 queries → expect ~15 chaos events
- Run 100 queries → expect ~30 chaos events

### Script runs but no traces in Console

1. Check project name matches Galileo Console
2. Verify API key has write permissions
3. Wait a few moments and refresh
4. Check log stream name: `chaos-log-builder`

## Cleanup

### Clear Old Logs (Optional)

In Galileo Console:
1. Navigate to log stream: `chaos-log-builder`
2. Delete old sessions if needed
3. Or rename log stream in script

### Reset Chaos Stats

The chaos engine maintains counters. Reset with:
```python
from chaos_engine import get_chaos_engine
chaos = get_chaos_engine()
chaos.reset_stats()
```

## Comparison: Experiment vs. Log Builder

| Feature | Experiments | Log Builder |
|---------|-------------|-------------|
| Purpose | Evaluation with metrics | Build error logs |
| Metrics | ✅ Yes | ❌ No |
| Datasets | Formal datasets | Any queries |
| Multiple runs | One per row | Configurable (3, 5, etc.) |
| Use case | A/B testing, evaluation | Pattern generation, Insights testing |
| Output | Experiment results | Log traces |

**Use Log Builder when:** You want to build up error patterns for Insights  
**Use Experiments when:** You want to evaluate agent performance

## Summary

**Quick Start:**
```bash
python quick_chaos_demo.py
```

**Advanced:**
```bash
python build_chaos_logs.py --dataset-name my-data --runs 3 --all-chaos
```

**Purpose:** Generate chaos-induced errors for Galileo Insights to analyze

**Result:** Detected patterns, recommendations, and insights!

---

**Scripts:**
- 🔥 `build_chaos_logs.py` - Full-featured builder
- ⚡ `quick_chaos_demo.py` - One-command demo
- 📖 `BUILD_CHAOS_LOGS_GUIDE.md` - This guide

**Try it:** `python quick_chaos_demo.py` → Wait → Check Insights! 🔍

