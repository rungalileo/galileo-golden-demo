# 🚀 Quick Start: Running Experiments

Get started with Galileo experiments in under 5 minutes!

## Prerequisites ✅

Make sure you have:
- [x] Python environment activated (`source venv/bin/activate`)
- [x] Galileo API key configured in `.streamlit/secrets.toml`
- [x] OpenAI API key configured
- [x] Agent domain set up (e.g., finance)

## Option 1: Fastest Start (30 seconds)

Run an experiment with built-in sample data:

```bash
python experiment_cli.py --inline --experiment my-first-test
```

That's it! This will:
✅ Use 5 built-in finance queries
✅ Process them through your agent
✅ Evaluate with Galileo metrics
✅ Show results you can view in Console

## Option 2: With Synthetic Dataset (5 minutes)

### Step 1: Create a Synthetic Dataset

**Using AI Assistant (Recommended):**

Ask your AI assistant in Cursor:
```
Create a Galileo synthetic dataset with these parameters:
- name: finance-queries-test
- description: Test queries for finance agent evaluation
- count: 20
- model: gpt-4o-mini
- data_types: General Query, Off-Topic Query
- sample_data: What was Costco's Q3 revenue?
How is the S&P 500 performing?
Should I invest in tech stocks?
```

The assistant will create the dataset and return a dataset ID.

**OR Using Galileo Console:**

1. Go to https://console.galileo.ai/datasets
2. Click "Create Dataset" → "Synthetic Data Generation"
3. Fill in the form with above parameters
4. Click "Generate" and wait ~2-3 minutes

### Step 2: Check Dataset Status

Ask your AI assistant:
```
Check the status of dataset finance-queries-test
```

Wait until generation is complete (you'll see "Complete" status).

### Step 3: Run the Experiment

```bash
python experiment_cli.py --dataset-name finance-queries-test --experiment baseline-v1
```

### Step 4: View Results

Go to https://console.galileo.ai and navigate to your project to see:
- Metrics for each query
- Full traces of agent execution
- RAG retrieval performance
- Tool usage patterns

## What You Get

Each experiment provides:

📊 **Metrics**
- Context Adherence: How well agent uses provided context
- Completeness: Coverage of query requirements
- Correctness: Accuracy vs expected output
- Toxicity: Content safety checks
- Chunk Attribution: RAG quality metrics

🔍 **Traces**
- Complete execution flow
- Tool calls and responses
- RAG retrievals
- Timing and token usage

📈 **Insights**
- Aggregate statistics
- Per-query breakdown
- Failure analysis
- Comparison across experiments

## Common Use Cases

### Test a Prompt Change

1. Edit `domains/finance/system_prompt.json`
2. Run experiment:
   ```bash
   python experiment_cli.py --dataset-name finance-queries-test --experiment prompt-v2
   ```
3. Compare results in Galileo Console

### Test Model Performance

1. Edit `domains/finance/config.yaml` (change `model_name`)
2. Run experiment:
   ```bash
   python experiment_cli.py --dataset-name finance-queries-test --experiment gpt4-test
   ```
3. Compare against baseline

### Test RAG Configuration

1. Edit RAG settings in `domains/finance/config.yaml`
2. Rebuild vector database: `python helpers/setup_vectordb.py finance`
3. Run experiment:
   ```bash
   python experiment_cli.py --dataset-name finance-queries-test --experiment rag-v2
   ```
4. Compare chunk attribution metrics

## Troubleshooting

**"Dataset not found"**
- Check dataset name is exact (case-sensitive)
- Verify it's in the correct Galileo project
- Try using `--dataset-id` instead

**"Agent initialization failed"**
- Run: `python helpers/setup_vectordb.py finance`
- Check API keys are configured
- Verify domain config is valid

**"No results showing in Console"**
- Verify GALILEO_PROJECT matches your Console project
- Check API key has write permissions
- Wait a few moments and refresh Console

## Next Steps

📚 **Learn More**
- Read [EXPERIMENTS_README.md](EXPERIMENTS_README.md) for detailed documentation
- See [example_full_workflow.py](example_full_workflow.py) for workflow examples

🔧 **Customize**
- Create datasets specific to your use case
- Define custom metrics
- Add new domains

🚀 **Scale Up**
- Generate larger datasets (50-100 samples)
- Run comparative experiments
- Set up continuous evaluation

## Getting Help

- Check [EXPERIMENTS_README.md](EXPERIMENTS_README.md) for detailed docs
- Run `python example_full_workflow.py` for interactive guide
- Contact FDE team via Slack for support

---

Happy experimenting! 🧪


