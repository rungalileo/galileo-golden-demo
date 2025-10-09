# Dataset Runs Feature Guide

## Overview

The **Runs** tab allows you to pull datasets from Galileo and run them through your agent to create **real production logs**. This is different from experiments, which are designed for evaluation with metrics and scorers.

## Key Differences: Runs vs Experiments

| Feature | Runs | Experiments |
|---------|------|-------------|
| **Purpose** | Create production-style logs | Evaluate agent performance |
| **Logs Created** | Real session logs in Galileo | Experiment logs with metrics |
| **Metrics** | No automatic metrics | Automatic scoring (context adherence, correctness, etc.) |
| **Use Case** | Testing, demos, chaos engineering | Performance evaluation, A/B testing |
| **Settings** | Honors chaos & guardrails | Focused on evaluation |

## How to Use

### Step 1: Access the Runs Tab

1. Launch the Streamlit app: `streamlit run app.py`
2. Navigate to the **🔄 Runs** tab (third tab)

### Step 2: Choose a Dataset Source

You have four options:

#### Option 1: Galileo Dataset (by name)
- Select "Galileo Dataset (by name)"
- Enter the name of a dataset you've created in Galileo Console
- Example: `finance-queries-synthetic`

#### Option 2: Galileo Dataset (by ID)
- Select "Galileo Dataset (by ID)"
- Enter the dataset ID from Galileo
- Example: `abc-123-def-456`

#### Option 3: Sample Test Data
- Select "Sample Test Data"
- Uses built-in 5 finance queries for quick testing

#### Option 4: Upload CSV File
- Select "Upload CSV File"
- Upload a CSV with an `input` column
- Each row's `input` will be processed as a query

### Step 3: Configure the Run

In the configuration form, set:

1. **Run Name**: Descriptive name for this run
   - Default: `dataset-run-YYYYMMDD-HHMM`
   - This name will appear in Galileo session logs

2. **Number of Cycles**: How many times to cycle through the dataset
   - Default: 1
   - Range: 1-100
   - Example: Setting this to 3 means each row will be processed 3 times

### Step 4: Review Active Settings

The run will automatically honor your current sidebar settings:

- **Guardrails**: If enabled, all input/output filtering applies
- **Chaos Engineering**: All active chaos modes will affect the run
- **Live Data**: Will use live or mock data based on your toggle

💡 **Tip**: Adjust these settings in the sidebar BEFORE starting the run

### Step 5: Start the Run

Click **🚀 Start Run** to begin processing. You'll see:
- Progress updates for each cycle and row
- Total queries processed
- Success/failure status

### Step 6: View Results in Galileo

Once complete:
- Go to [Galileo Console](https://console.galileo.ai)
- Look for sessions with your run name
- Each query creates a separate session log with full traces

## Use Cases

### 1. Chaos Engineering Testing

Generate problematic logs to test observability:

```
1. Enable chaos modes in sidebar:
   - ✅ Tool Instability
   - ✅ Sloppiness
   - ✅ RAG Disconnects

2. Load a dataset with typical queries

3. Set cycles to 3-5 to generate multiple variations

4. Run and analyze logs in Galileo for:
   - API failures
   - Hallucinations
   - RAG issues
```

### 2. Guardrails Testing

Test how guardrails handle various inputs:

```
1. Create a dataset with edge cases:
   - PII in queries
   - Toxic content
   - Off-topic requests

2. Enable guardrails in sidebar

3. Run dataset with 1 cycle

4. Review Galileo logs to see which queries were blocked
```

### 3. Demo Data Generation

Populate Galileo with realistic demo data:

```
1. Create a dataset of representative queries

2. Disable chaos modes

3. Run with 2-3 cycles for variety

4. Use these logs for demos and screenshots
```

### 4. Baseline Log Creation

Create a baseline for monitoring:

```
1. Create a "golden" dataset of expected queries

2. Disable chaos, enable guardrails

3. Run with 1 cycle

4. Use as baseline for comparing future behavior
```

## Example Workflow

### Scenario: Test Agent with Chaos Enabled

**Goal**: Generate 50 logs with chaos to test observability

**Steps**:

1. **Create Dataset in Galileo**:
   - Go to Galileo Console
   - Create dataset: `finance-chaos-test`
   - Add 10 varied finance queries

2. **Enable Chaos in Sidebar**:
   - ✅ Tool Instability (25% failure rate)
   - ✅ Sloppiness (30% number errors)
   - ✅ Data Corruption (20% corrupt data)

3. **Configure Run**:
   - Dataset Source: Galileo Dataset (by name)
   - Dataset Name: `finance-chaos-test`
   - Run Name: `chaos-test-oct-2025`
   - Number of Cycles: 5 (10 rows × 5 cycles = 50 total logs)

4. **Start Run**:
   - Click "Start Run"
   - Wait for completion (may take a few minutes)

5. **Analyze in Galileo**:
   - Go to Galileo Console
   - Filter sessions by name: `chaos-test-oct-2025`
   - Review traces for:
     - Failed API calls
     - Transposed numbers
     - Corrupted data
     - Agent recovery strategies

## Tips and Best Practices

### Dataset Creation

✅ **DO**:
- Include varied query types (simple, complex, edge cases)
- Use realistic user language
- Add queries that test specific features
- Keep datasets focused (10-50 rows is usually enough)

❌ **DON'T**:
- Make datasets too large (use cycles instead)
- Include only happy-path queries
- Forget to test error cases

### Cycle Configuration

- **1 cycle**: Good for initial testing, baseline creation
- **3-5 cycles**: Ideal for chaos testing (creates variety)
- **10+ cycles**: Use for load testing or generating large log sets

### Settings Management

1. **Before Each Run**: Review sidebar settings
2. **Document Settings**: Note which chaos modes were active
3. **Consistent Naming**: Use descriptive run names with dates

### Performance Considerations

- Each query takes 2-10 seconds depending on:
  - Agent complexity
  - RAG retrievals
  - Tool calls
  - Chaos failures

- Estimated time for a run:
  ```
  Time = (Dataset Size × Cycles × Avg Query Time)
  
  Example: 10 rows × 3 cycles × 5 seconds = 150 seconds (~2.5 minutes)
  ```

## Troubleshooting

### Dataset Not Found

**Error**: "Failed to load dataset"

**Solution**:
- Check dataset name spelling (case-sensitive)
- Verify dataset exists in Galileo Console
- Try using dataset ID instead of name

### Agent Errors During Run

**Error**: Individual queries failing

**Solution**:
- Check if chaos modes are too aggressive
- Review agent configuration
- Check environment variables (API keys, etc.)
- Look at error details in status display

### Progress Appears Stuck

**Issue**: Progress not updating

**Solution**:
- Be patient - some queries take time
- Check terminal for error messages
- If truly stuck, refresh the page and restart

### No Logs in Galileo

**Issue**: Run completed but no logs visible

**Solution**:
- Check you're in the correct Galileo project
- Search by session name (from run config)
- Wait a few minutes for logs to sync
- Verify `GALILEO_PROJECT` environment variable

## Advanced Usage

### Creating Datasets via MCP Tool

You can use the AI assistant to create synthetic datasets:

```
"Create a Galileo dataset with 20 finance queries about:
- Stock prices
- Company earnings
- Investment advice
- Market trends"
```

Then use the dataset name in the Runs tab.

### Combining with Experiments

1. **First**: Run dataset in Runs tab (creates logs)
2. **Then**: Run same dataset in Experiments tab (evaluates quality)
3. **Compare**: Logs vs metrics to understand behavior

### Scripting Runs

You can also run datasets programmatically:

```python
from galileo.datasets import get_dataset
from agent_factory import AgentFactory
from galileo import galileo_context

# Load dataset
dataset = get_dataset(name="my-dataset")

# Initialize agent
factory = AgentFactory()
agent = factory.create_agent(domain="finance", framework="LangGraph")

# Process each row
for row in dataset:
    session_id = f"run-{uuid.uuid4().hex[:8]}"
    galileo_context.start_session(name="My Run", external_id=session_id)
    
    response = agent.process_query([{"role": "user", "content": row["input"]}])
    
    galileo_context.end_session()
```

## FAQ

**Q: What's the maximum dataset size?**
A: No hard limit, but keep it reasonable. Use cycles instead of huge datasets.

**Q: Can I stop a run in progress?**
A: Not currently - refresh the page to cancel, but partial logs may exist.

**Q: Do runs count toward Galileo usage limits?**
A: Yes, each session log counts as a normal log.

**Q: Can I use runs for A/B testing?**
A: Not really - use Experiments tab for A/B testing. Runs are for log generation.

**Q: How do I know if guardrails triggered?**
A: Check the Galileo logs - blocked queries will show guardrail triggers.

**Q: Can I run multiple datasets in parallel?**
A: No, run them sequentially. Each run should complete before starting the next.

## Related Documentation

- [Experiments Guide](EXPERIMENTS_README.md)
- [Chaos Engineering Guide](CHAOS_ENGINEERING.md)
- [Guardrails Guide](GUARDRAILS_GUIDE.md)
- [Quick Start](QUICKSTART_EXPERIMENTS.md)

## Support

For issues or questions:
1. Check [Galileo Documentation](https://docs.galileo.ai)
2. Review logs in Galileo Console
3. Check terminal output for errors

