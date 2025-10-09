# 🔥 Chaos Engineering - Quick Start

## What is This?

Chaos Engineering lets you **intentionally break things** to test how well Galileo detects and helps fix problems.

## 30-Second Quick Start

```bash
streamlit run app.py
```

**In UI:**
1. **Sidebar** → "🔥 Chaos Engineering" 
2. **Expand** "⚙️ Chaos Controls"
3. **Check** "🔢 Sloppiness"
4. **Chat tab** → Ask: "What's the price of AAPL?" (5-10 times)
5. **Watch**: Some responses will have wrong numbers!

Example:
```
Ask: "What's the price of AAPL?"
Real: $258.06
Agent says: "$285.06"  ← Digits transposed! (2 and 5 swapped)
```

## The 5 Chaos Modes

| Mode | What It Breaks | Rate | Why It's Useful |
|------|----------------|------|-----------------|
| 🔌 **Tool Instability** | Makes APIs randomly fail | 25% | Tests error handling |
| 🔢 **Sloppiness** | Transposes numbers in responses | 30% | Creates hallucinations |
| 📚 **RAG Disconnects** | Prevents RAG from loading | 20% | Tests fallback logic |
| ⏱️ **Rate Limits** | Simulates API quota exhaustion | 15% | Tests throttling |
| 💥 **Data Corruption** | Returns wrong/invalid data | 20% | Tests validation |

## Try Each Mode

### Mode 1: Sloppiness (Easiest to See)

```
Enable: 🔢 Sloppiness
Ask: "What's the price of NVDA?"
Repeat 5 times
Result: 1-2 will have transposed digits
Example: $189.11 → $198.11 (8 and 9 swapped)
```

### Mode 2: Tool Instability

```
Enable: 🔌 Tool Instability  
Ask: "What's the price of TSLA?"
Repeat 10 times
Result: 2-3 will fail with API error
Example: "Stock Price API temporarily unavailable (503)"
```

### Mode 3: Data Corruption

```
Enable: 💥 Data Corruption
Ask: "What's the price of AAPL?"
Repeat 5 times
Result: 1-2 will have wrong prices or missing data
Example: Price 2x higher than real, or missing volume field
```

### Mode 4: RAG Disconnects

```
Enable: 📚 RAG Disconnects
Ask: "What was Costco's Q3 revenue?"
Repeat 5 times
Result: 1-2 will fail to access documents
Example: "Unable to access document database"
```

### Mode 5: Rate Limits

```
Enable: ⏱️ Rate Limits
Ask multiple price queries in succession
Result: Occasional "Rate limit exceeded" errors
```

## What Galileo Will Show

### In Traces

- ❌ Failed tool calls
- 🔢 Inconsistent numbers between tool output and response
- 📚 Missing RAG retrievals
- ⏱️ Rate limit errors
- 💥 Corrupted data in tool responses

### In Insights (Coming Soon!)

After collecting data, Galileo Insights will suggest:

- "High numerical hallucination rate - add validation guardrail"
- "API reliability issues - implement retry logic"
- "RAG failures detected - add health monitoring"
- And more!

## Real Demos

### Demo 1: Show Observability

```
Story: "Let's see what happens when things go wrong..."

1. Enable Tool Instability
2. Ask for stock prices
3. Some fail → Show error in traces
4. Point out: "Galileo automatically detected this!"
```

### Demo 2: Show Hallucination Detection

```
Story: "LLMs can hallucinate numbers. Watch..."

1. Enable Sloppiness
2. Ask: "What's NVDA price?"
3. Agent says $198.11 but tool returned $189.11
4. Show Galileo flagging the inconsistency
```

### Demo 3: Show Guardrails

```
Story: "Guardrails can catch these issues..."

1. Configure guardrail: Block numerical inconsistencies
2. Enable Sloppiness
3. Transposed response gets blocked
4. Show prevention in action
```

## Tips for Great Demos

### Before Demo

- Test chaos modes beforehand
- Know which queries trigger which chaos
- Have Galileo Console ready

### During Demo

- Start with one chaos mode (Sloppiness is most visible)
- Show it happening live
- Navigate to Galileo to show detection
- Gradually add more chaos modes

### After Demo

- Show Insights recommendations
- Explain how to fix each issue
- Demonstrate guardrails blocking bad outputs

## Troubleshooting

### Chaos Not Happening

**Check:**
- Chaos mode is checked in UI
- "🔥 X chaos mode(s) active" shows at bottom
- Look at console/logs for "🔥 CHAOS:" messages

### Too Much Chaos

**Solution:**
- Uncheck some modes
- Reset stats to clear counters
- Restart with lower rates

### Not Seeing in Galileo

**Wait:**
- Chaos is probabilistic - try multiple queries
- Check traces tab for specific issues
- Insights may take time to analyze patterns

## Quick Reference

```
🔌 = API failures → Error handling
🔢 = Number errors → Hallucination detection  
📚 = RAG fails → Missing context handling
⏱️ = Rate limits → Quota management
💥 = Bad data → Data validation
```

**Enable → Test → Check Galileo → Show Insights**

---

**Full Details:** [CHAOS_ENGINEERING.md](CHAOS_ENGINEERING.md)

**Try it now:** `streamlit run app.py` → Enable chaos → See what breaks! 🔥

