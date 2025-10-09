# Galileo Guardrails Guide

## Overview

Galileo Guardrails provide **real-time content filtering and safety** for the finance agent, protecting against:
- **PII leakage** (account numbers, SSN, credit cards)
- **Inappropriate content** (sexism, toxicity)
- **Hallucinated trades** (low context adherence)

## Quick Start

### 1. Install Dependencies

```bash
pip install galileo-protect
```

### 2. Enable in UI

1. Start the app: `streamlit run app.py`
2. Open sidebar → **🛡️ Galileo Guardrails**
3. Toggle **"Enable Guardrails"** ON
4. See active protections in details

### 3. Test It

**Try these queries to see guardrails in action:**

1. **"Show me my account information"** → Triggers PII output guardrail
2. **"My SSN is 123-45-6789"** → Triggers PII input guardrail
3. **Enable chaos + "Buy 10 shares of NVDA"** → May trigger hallucination guardrail

## Features

### 🔒 Input Filtering

**What it does:**
- Scans user input for PII, sexism, toxicity
- Blocks inappropriate queries before processing
- Shows shield icon (🛡️) when triggered

**Protections:**
- **PII**: Account numbers, SSN, credit cards, addresses, phone numbers
- **Sexism**: Sexist or discriminatory language
- **Toxicity**: Harmful, offensive, or abusive content

**Example:**
```
User: "My SSN is 123-45-6789, can you help me?"

Response:
🛡️ Guardrail Active: Your input contains personally identifiable 
information (PII). Please rephrase without including sensitive data 
like account numbers, SSN, or personal details.
```

### 🔒 Output Filtering

**What it does:**
- Scans agent responses for PII, sexism, toxicity
- Blocks responses that leak sensitive data
- Protects users from inappropriate content

**Protections:**
- **PII Leakage**: Prevents exposing account numbers, SSN, etc.
- **Sexism**: Blocks discriminatory responses
- **Toxicity**: Prevents harmful or offensive output

**Example:**
```
User: "Show me my account information"

Agent tries to return:
Name: John Smith
SSN: 123-45-6789
Account: BA-9876543210

Guardrail blocks it:
🛡️ Guardrail Active: The response contains sensitive information 
and has been blocked for your protection.
```

### 📊 Trade Protection

**What it does:**
- Checks context adherence for trade actions
- Blocks trades if confidence < 70%
- Detects hallucinated trade amounts

**How it works:**
1. Agent processes trade request
2. Guardrail measures context adherence
3. If < 70%, trade is blocked
4. User sees warning with attempted action

**Example (with chaos enabled):**
```
User: "Buy 10 shares of NVDA"

Agent (chaos transposes number): "Purchased 01 shares..." ❌

Guardrail detects low context adherence (45%):
🛡️ Trade Blocked: Low context adherence detected (45%). The trade 
details may be inaccurate or hallucinated. Please verify and try again.

Attempted action: I've purchased 01 shares of NVDA at $500.00...
```

### ✅ Trade Success Messages

When guardrails **pass** a trade:
```
✅ Trade Executed Successfully

I've purchased 10 shares of NVDA at $450.00 for a total of $4,500.00.
Your order has been placed successfully.
```

## Configuration

### Enable/Disable Globally

**Via UI:**
- Toggle in sidebar: **🛡️ Galileo Guardrails** → Enable Guardrails

**Via Environment Variable:**
```bash
export GUARDRAILS_ENABLED=true
```

**Via Code:**
```python
from guardrails_config import get_guardrails_manager

guardrails = get_guardrails_manager()
guardrails.enable()  # or guardrails.disable()
```

### Adjust Thresholds

Edit `guardrails_config.py`:
```python
self.pii_threshold = 0.5  # 50%
self.sexism_threshold = 0.5  # 50%
self.toxicity_threshold = 0.5  # 50%
self.context_adherence_threshold = 0.70  # 70% for trades
```

## Testing Guardrails

### Test PII Output

**Setup:**
1. Enable guardrails
2. Ask: **"Show me my account information"**
3. Agent calls `get_account_information()` tool
4. Tool returns PII data (account number, SSN, etc.)
5. **Output guardrail blocks it** 🛡️

**Expected Result:**
```
🛡️ Guardrail Active: The response contains sensitive information 
and has been blocked for your protection.
```

### Test PII Input

**Setup:**
1. Enable guardrails
2. Ask: **"My SSN is 123-45-6789, can you help?"**
3. **Input guardrail blocks it** 🛡️

**Expected Result:**
```
🛡️ Guardrail Active: Your input contains personally identifiable 
information (PII). Please rephrase without including sensitive data.
```

### Test Hallucinated Trades

**Setup:**
1. Enable guardrails
2. Enable chaos → Sloppiness (transposes numbers)
3. Ask: **"Buy 10 shares of NVDA"**
4. Chaos might transpose: "01 shares"
5. **Trade guardrail detects low context adherence** 🛡️

**Expected Result:**
```
🛡️ Trade Blocked: Low context adherence detected (45%). The trade 
details may be inaccurate or hallucinated. Please verify and try again.

Attempted action: I've purchased 01 shares of NVDA...
```

### Test Toxicity (Manual)

**Try toxic input:**
```
"You're a terrible assistant and I hate you"
```

**Expected:** Input guardrail blocks it

**Try triggering toxic output:**
(Harder to test - would require prompting the LLM to generate toxic content)

## UI Controls

### Main Toggle

**Location:** Sidebar → 🛡️ Galileo Guardrails

**Options:**
- ✅ **Enabled**: All guardrails active
- ❌ **Disabled**: All content passes through unchecked

### Details Expander

**Shows:**
- Active protections (input, output, trade)
- Real-time statistics
- Block rates

### Test Expander

**Quick test buttons:**
1. **Test: PII Output** → Triggers PII output guardrail
2. **Test: PII Input** → Triggers PII input guardrail
3. **Test: Hallucinated Trade** → May trigger trade guardrail

## Statistics

### Available Metrics

```python
stats = guardrails.get_stats()
```

**Returns:**
```python
{
    "input_checks": 10,
    "input_blocks": 2,
    "output_checks": 10,
    "output_blocks": 1,
    "trade_checks": 3,
    "trade_blocks": 1,
    "enabled": True,
    "block_rate": 20.0  # percentage
}
```

### View in UI

**Location:** Sidebar → Guardrails Details → Stats

**Displays:**
- Input/Output/Trade checks
- Blocks per category
- Overall block rate (progress bar)

### Reset Stats

**UI:** Click "Reset Stats" button

**Code:**
```python
guardrails.reset_stats()
```

## Architecture

### Integration Points

**1. Agent Input (before processing)**
```python
# Check user input
input_result = guardrails.check_input(user_input)
if not input_result.passed:
    return input_result.message  # Blocked!
```

**2. Agent Output (after processing)**
```python
# Check agent response
output_result = guardrails.check_output(response, context, user_input)
if not output_result.passed:
    return output_result.message  # Blocked!
```

**3. Trade Actions (special handling)**
```python
# Check if it's a trade
if is_trade:
    trade_result = guardrails.check_trade(response, context, user_input)
    if not trade_result.passed:
        return trade_result.message  # Blocked!
    else:
        # Add success indicator
        response = f"✅ Trade Executed Successfully\n\n{response}"
```

### Guardrail Rules

**Input Rules:**
```python
Rule(metric=GalileoScorers.input_pii, operator=RuleOperator.gt, target_value=0.5)
Rule(metric=GalileoScorers.input_sexism, operator=RuleOperator.gt, target_value=0.5)
Rule(metric=GalileoScorers.input_toxicity, operator=RuleOperator.gt, target_value=0.5)
```

**Output Rules:**
```python
Rule(metric=GalileoScorers.output_pii, operator=RuleOperator.gt, target_value=0.5)
Rule(metric=GalileoScorers.output_sexism, operator=RuleOperator.gt, target_value=0.5)
Rule(metric=GalileoScorers.output_toxicity, operator=RuleOperator.gt, target_value=0.5)
```

**Trade Rules:**
```python
Rule(metric=GalileoScorers.context_adherence, operator=RuleOperator.lt, target_value=0.70)
```

### Fake Database (PII Testing)

**Location:** `domains/finance/fake_database.py`

**Contains:**
- 3 fake users with realistic PII
- Account numbers, SSN, credit cards, addresses
- Used by `get_account_information()` tool

**Purpose:** Generate PII data to test output guardrails

## Best Practices

### For Demos

**1. Show the protection:**
```
1. Enable guardrails
2. Ask: "Show me my account information"
3. See 🛡️ block message
4. Explain: "This protects sensitive data from leaking"
```

**2. Show the stats:**
```
1. Run a few queries (some trigger guardrails)
2. Open Guardrails Details
3. Show block rate increasing
4. Explain: "Real-time monitoring and blocking"
```

**3. Combine with chaos:**
```
1. Enable guardrails + sloppiness
2. Ask: "Buy 10 shares of NVDA"
3. Chaos transposes → "01 shares"
4. Guardrail blocks trade (low context adherence)
5. Explain: "Prevents hallucinated trades"
```

### For Production

**1. Always enable guardrails:**
```bash
export GUARDRAILS_ENABLED=true
```

**2. Monitor block rates:**
- High block rate → May need to adjust thresholds or prompts
- Zero blocks → Might want to test with more diverse inputs

**3. Log blocked attempts:**
- All blocks are logged to Galileo Console
- Review in Insights for patterns

**4. Fine-tune thresholds:**
- Start conservative (50% for PII/sexism/toxicity, 70% for trades)
- Adjust based on false positives/negatives

## Troubleshooting

### Guardrails Not Available

**Error:** "Guardrails not available - install galileo-protect"

**Fix:**
```bash
pip install galileo-protect
```

### Guardrails Not Blocking

**Possible causes:**
1. **Disabled** - Check toggle in UI
2. **Threshold too high** - Lower in `guardrails_config.py`
3. **Content not detected** - Try more obvious examples

**Debug:**
```python
guardrails = get_guardrails_manager()
print(f"Enabled: {guardrails.is_enabled()}")
print(f"Stats: {guardrails.get_stats()}")
```

### False Positives

**If guardrails block legitimate content:**

1. **Adjust thresholds:**
```python
self.pii_threshold = 0.7  # More lenient (was 0.5)
```

2. **Check Galileo Console:**
- View the triggered rule
- See confidence score
- Determine if adjustment needed

### Trade Guardrail Not Triggering

**If trades pass when they shouldn't:**

1. **Lower threshold:**
```python
self.context_adherence_threshold = 0.60  # More strict (was 0.70)
```

2. **Enable chaos to test:**
```python
# Sloppiness will trigger trade guardrails
chaos.enable_sloppiness(True)
```

## Galileo Console

### Viewing Blocked Attempts

**Steps:**
1. Go to Galileo Console
2. Navigate to your project
3. Filter by log stream
4. Look for traces with guardrail metadata

**Metadata includes:**
- `guardrail_triggered: true`
- `guardrail_type: "pii"` (or "sexism", "toxicity", "context_adherence")
- `guardrail_score: 0.85`

### Insights Analysis

**What to look for:**
- **High PII output rate** → Tool is leaking data, fix tool logic
- **High toxicity input** → Users sending inappropriate queries
- **High trade blocks** → Agent hallucinating, tune prompts or model

## Examples

### Example 1: Safe Query

```
User: "What's the current price of AAPL?"

Guardrails:
- ✅ Input check: PASS (no PII, toxicity, sexism)
- Agent processes...
- ✅ Output check: PASS (no PII, toxicity, sexism)

Response: "The current price of AAPL is $150.00..."
```

### Example 2: PII in Input

```
User: "My account number is BA-9876543210, can you help?"

Guardrails:
- ❌ Input check: FAIL (PII detected: account number)

Response:
🛡️ Guardrail Active: Your input contains personally identifiable 
information (PII). Please rephrase without including sensitive data.
```

### Example 3: PII in Output

```
User: "Show me my account information"

Agent calls get_account_information() → Returns:
"Name: John Smith, SSN: 123-45-6789, Account: BA-9876543210..."

Guardrails:
- ❌ Output check: FAIL (PII detected: SSN, account number, name)

Response:
🛡️ Guardrail Active: The response contains sensitive information 
and has been blocked for your protection.
```

### Example 4: Hallucinated Trade (Chaos)

```
User: "Buy 10 shares of NVDA at $450"

Agent (chaos transposes): "Purchased 01 shares at $045..."

Guardrails:
- Trade detected
- Context adherence: 35% (< 70% threshold)
- ❌ Trade check: FAIL

Response:
🛡️ Trade Blocked: Low context adherence detected (35%). The trade 
details may be inaccurate or hallucinated. Please verify and try again.

Attempted action: I've purchased 01 shares of NVDA at $045.00...
```

### Example 5: Successful Trade

```
User: "Buy 10 shares of NVDA"

Agent: "Purchased 10 shares at $450.00..."

Guardrails:
- Trade detected
- Context adherence: 95% (> 70% threshold)
- ✅ Trade check: PASS

Response:
✅ Trade Executed Successfully

I've purchased 10 shares of NVDA at $450.00 for a total of $4,500.00.
Your order has been placed successfully.
```

## Summary

**Guardrails protect your agent from:**
- 🔒 PII leakage
- 🚫 Inappropriate content
- 🎯 Hallucinated trades

**Enable in UI:**
- Sidebar → 🛡️ Galileo Guardrails → Toggle ON

**Test it:**
- "Show me my account information" → PII output blocked
- "My SSN is 123-45-6789" → PII input blocked
- Enable chaos + trade query → Hallucinated trade blocked

**Monitor it:**
- View stats in UI
- Check Galileo Console
- Review Insights

**Result:**
- Production-ready safety
- Real-time protection
- Comprehensive logging

---

**Files:**
- 🛡️ `guardrails_config.py` - Main guardrails module
- 📊 `domains/finance/fake_database.py` - PII test data
- 🤖 `agent_frameworks/langgraph/agent.py` - Agent integration
- 🎨 `app.py` - UI controls
- 📖 `GUARDRAILS_GUIDE.md` - This guide

**Test it now:** `streamlit run app.py` → Enable Guardrails → Try examples! 🚀

