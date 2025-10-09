# Dataset Runs - Quick Start

## What Are Runs?

**Runs** let you process datasets through your agent to create **real production logs** in Galileo.

## Quick Comparison

| Feature | Runs Tab | Experiments Tab |
|---------|----------|-----------------|
| Creates | Real session logs | Evaluation metrics |
| Purpose | Testing, demos, chaos | Performance evaluation |
| Output | Galileo session logs | Metric scores |

## 5-Minute Quick Start

### 1. Launch App
```bash
streamlit run app.py
```

### 2. Go to Runs Tab
Click the **🔄 Runs** tab (third tab)

### 3. Quick Test with Sample Data
- Select: **Sample Test Data**
- Run Name: `quick-test`
- Cycles: `1`
- Session Grouping: **Multi-turn** (or **Single-turn**)
- Click **🚀 Start Run**

### 4. View Results
- Go to [Galileo Console](https://console.galileo.ai)
- Find sessions named `Dataset Run - quick-test`
- Explore the logs!

## Common Workflows

### Chaos Testing
```
1. Sidebar → Enable chaos modes (Tool Instability, Sloppiness)
2. Runs tab → Load dataset
3. Set cycles to 3-5
4. Start run
5. Analyze problematic logs in Galileo
```

### Guardrails Testing
```
1. Sidebar → Enable Guardrails
2. Runs tab → Use dataset with edge cases
3. Set cycles to 1
4. Start run
5. Check which queries were blocked
```

### Demo Data Generation
```
1. Sidebar → Disable chaos
2. Runs tab → Load representative dataset
3. Set cycles to 2-3
4. Start run
5. Use logs for demos
```

## Dataset Sources

1. **Galileo Dataset (by name)**: Use existing Galileo datasets
2. **Galileo Dataset (by ID)**: Use dataset ID
3. **Sample Test Data**: Built-in 5 queries for quick testing
4. **Upload CSV**: Upload your own CSV with `input` column

## Key Features

✅ **Cycles**: Process dataset multiple times (e.g., 3x = each row processed 3 times)

✅ **Session Grouping**: Choose multi-turn (one session) or single-turn (separate sessions)

✅ **Honors Settings**: Automatically uses your chaos and guardrails settings

✅ **Real Logs**: Creates actual session logs (not experiment logs)

✅ **Progress Tracking**: See live progress for each cycle and row

## Session Grouping Modes

### Multi-turn (All queries in one session)
- **Use when**: You want to see all queries together as a conversation flow
- **Result**: One Galileo session with multiple turns
- **Good for**: Overall pattern analysis, simulating multi-turn conversations

### Single-turn (Each query as separate session)
- **Use when**: You want to evaluate each query independently
- **Result**: Multiple Galileo sessions, one per query
- **Good for**: Individual query analysis, easier filtering, A/B testing

## Tips

💡 **Start Small**: Use 5-10 row datasets with 1-3 cycles

💡 **Check Settings**: Review sidebar settings before each run

💡 **Name Clearly**: Use descriptive run names with dates

💡 **Monitor Progress**: Each query takes 2-10 seconds

## Next Steps

📖 [Full Runs Guide](RUNS_FEATURE_GUIDE.md) - Detailed documentation

🧪 [Experiments Guide](EXPERIMENTS_README.md) - For evaluation workflows

🔥 [Chaos Guide](CHAOS_ENGINEERING.md) - Chaos engineering details

🛡️ [Guardrails Guide](GUARDRAILS_GUIDE.md) - Guardrails configuration

