# Galileo Guardrails - Implementation Summary

## ✅ What Was Implemented

### 1. Guardrails Configuration Module
**File:** `guardrails_config.py`

**Features:**
- Input filtering (PII, Sexism, Toxicity)
- Output filtering (PII, Sexism, Toxicity)
- Trade validation (Context Adherence < 70% = block)
- Shield icon responses (🛡️)
- Statistics tracking
- Enable/disable globally

### 2. Fake Database with PII
**File:** `domains/finance/fake_database.py`

**Contains:**
- 3 fake users with realistic PII:
  - Account numbers
  - SSN
  - Credit cards
  - Addresses
  - Phone numbers
  - Email addresses
  - Banking details

**Purpose:** Test PII output guardrails by requesting account info

### 3. New Tool: Get Account Information
**Files:**
- `domains/finance/tools/logic.py` - Tool implementation
- `domains/finance/tools/schema.json` - Tool schema
- `domains/finance/config.yaml` - Tool configuration

**Behavior:**
- Returns fake account info WITH PII
- **Triggers output PII guardrail** 🛡️
- Perfect for demonstrating protection

### 4. Agent Integration
**File:** `agent_frameworks/langgraph/agent.py`

**Integration Points:**
1. **Input Check** (before processing)
   - Scans user query for PII, sexism, toxicity
   - Blocks immediately if detected
   - Returns shield message

2. **Output Check** (after processing)
   - Scans agent response for PII, sexism, toxicity
   - Blocks before sending to user
   - Returns shield message

3. **Trade Check** (special handling)
   - Detects trade actions
   - Measures context adherence
   - Blocks if < 70% threshold
   - Shows attempted action + warning
   - Adds ✅ success message if passes

### 5. UI Controls
**File:** `app.py`

**Location:** Sidebar → 🛡️ Galileo Guardrails

**Controls:**
- Main toggle (Enable/Disable)
- Details expander:
  - Active protections list
  - Real-time statistics
  - Block rate progress bar
  - Reset button
- Test examples:
  - PII Output test
  - PII Input test
  - Hallucinated Trade test

## 🎯 How It Works

### User Flow

```
1. User enters query
   ↓
2. INPUT GUARDRAIL CHECK
   - PII? Sexism? Toxicity?
   ↓
3. If BLOCKED → Return 🛡️ message
   If PASSED → Continue
   ↓
4. Agent processes query
   ↓
5. Is it a TRADE?
   ↓
   YES:
   - Check context adherence
   - Block if < 70%
   - Add ✅ if passes
   ↓
6. OUTPUT GUARDRAIL CHECK
   - PII? Sexism? Toxicity?
   ↓
7. If BLOCKED → Return 🛡️ message
   If PASSED → Return response
```

### Trade Protection Flow

```
User: "Buy 10 shares of NVDA"
   ↓
Agent processes → "Purchased 10 shares at $450..."
   ↓
Is trade? YES
   ↓
Check context adherence
   ↓
Score: 95% (> 70%)
   ↓
PASS → Add ✅ "Trade Executed Successfully"
```

**With Chaos (Hallucination):**
```
User: "Buy 10 shares of NVDA"
   ↓
Chaos transposes → "01 shares at $045..."
   ↓
Is trade? YES
   ↓
Check context adherence
   ↓
Score: 35% (< 70%)
   ↓
BLOCK → 🛡️ "Trade Blocked: Low context adherence..."
```

## 🧪 Testing

### Test 1: PII Output

**Setup:**
1. Enable guardrails
2. Ask: **"Show me my account information"**

**Expected Result:**
```
🛡️ Guardrail Active: The response contains sensitive information 
and has been blocked for your protection.
```

**What Happened:**
1. Agent called `get_account_information()` tool
2. Tool returned PII (SSN, account number, etc.)
3. Output guardrail detected PII
4. Response blocked ✅

### Test 2: PII Input

**Setup:**
1. Enable guardrails
2. Ask: **"My SSN is 123-45-6789, can you help?"**

**Expected Result:**
```
🛡️ Guardrail Active: Your input contains personally identifiable 
information (PII). Please rephrase without including sensitive data.
```

**What Happened:**
1. User input scanned
2. Input guardrail detected SSN
3. Query blocked before processing ✅

### Test 3: Hallucinated Trade

**Setup:**
1. Enable guardrails
2. Enable chaos → Sloppiness
3. Ask: **"Buy 10 shares of NVDA"**
4. Chaos may transpose numbers

**Expected Result (if transposed):**
```
🛡️ Trade Blocked: Low context adherence detected (35%). The trade 
details may be inaccurate or hallucinated. Please verify and try again.

Attempted action: I've purchased 01 shares of NVDA at $045.00...
```

**What Happened:**
1. Agent generated response with transposed numbers
2. Trade detected
3. Context adherence calculated: 35% (< 70%)
4. Trade blocked ✅

### Test 4: Successful Trade

**Setup:**
1. Enable guardrails
2. Chaos OFF
3. Ask: **"Buy 10 shares of NVDA"**

**Expected Result:**
```
✅ Trade Executed Successfully

I've purchased 10 shares of NVDA at $450.00 for a total of $4,500.00.
Your order has been placed successfully.
```

**What Happened:**
1. Agent generated correct response
2. Trade detected
3. Context adherence: 95% (> 70%)
4. Trade passed, success message added ✅

## 📊 Statistics

### Available Metrics

```python
guardrails.get_stats()
```

**Returns:**
- `input_checks`: Total input checks
- `input_blocks`: Inputs blocked
- `output_checks`: Total output checks
- `output_blocks`: Outputs blocked
- `trade_checks`: Total trade checks
- `trade_blocks`: Trades blocked
- `enabled`: Boolean
- `block_rate`: Percentage

### View in UI

**Location:** Sidebar → Guardrails Details

**Shows:**
- Metrics per category
- Block rate progress bar
- Reset button

## 🔧 Configuration

### Enable/Disable

**Via UI:**
- Sidebar → Toggle "Enable Guardrails"

**Via Environment:**
```bash
export GUARDRAILS_ENABLED=true
```

**Via Code:**
```python
from guardrails_config import get_guardrails_manager
guardrails = get_guardrails_manager()
guardrails.enable()
```

### Adjust Thresholds

**File:** `guardrails_config.py`

```python
# Current settings
self.pii_threshold = 0.5              # 50%
self.sexism_threshold = 0.5           # 50%
self.toxicity_threshold = 0.5         # 50%
self.context_adherence_threshold = 0.70  # 70% for trades
```

**Adjust as needed:**
- Lower = More strict (more blocks)
- Higher = More lenient (fewer blocks)

## 📁 Files Created/Modified

### New Files
1. ✅ `guardrails_config.py` - Main guardrails module
2. ✅ `domains/finance/fake_database.py` - PII test data
3. ✅ `test_guardrails.py` - Test script
4. ✅ `GUARDRAILS_GUIDE.md` - Full documentation
5. ✅ `GUARDRAILS_SUMMARY.md` - This file

### Modified Files
1. ✅ `agent_frameworks/langgraph/agent.py` - Integrated guardrails
2. ✅ `domains/finance/tools/logic.py` - Added account info tool
3. ✅ `domains/finance/tools/schema.json` - Added tool schema
4. ✅ `domains/finance/config.yaml` - Added tool to config
5. ✅ `app.py` - Added UI controls
6. ✅ `requirements.txt` - Added galileo-protect
7. ✅ `README.md` - Added guardrails section

## 🎬 Demo Script

### Setup (1 minute)
```bash
pip install galileo-protect
streamlit run app.py
```

### Demo Part 1: PII Protection (2 minutes)

**Scenario:** "What if a user asks for sensitive account info?"

1. **Show the tool:** "We have a tool that returns account info"
2. **Ask:** "Show me my account information"
3. **See block:** 🛡️ message appears
4. **Explain:** "Guardrail detected PII and blocked it"
5. **Show stats:** Open Guardrails Details → 1 output block

### Demo Part 2: Trade Protection (3 minutes)

**Scenario:** "What if the agent hallucinates a trade amount?"

1. **Enable chaos:** Sidebar → Sloppiness ON
2. **Ask:** "Buy 10 shares of NVDA"
3. **Maybe blocked:** If chaos transposes, 🛡️ trade block
4. **Show attempted:** "Attempted action" shows wrong amount
5. **Explain:** "Context adherence < 70%, so blocked"
6. **Disable chaos**
7. **Ask again:** "Buy 10 shares of NVDA"
8. **See success:** ✅ Trade Executed Successfully
9. **Explain:** "High confidence, trade allowed"

### Demo Part 3: Input Protection (1 minute)

**Scenario:** "What if user includes PII in their query?"

1. **Ask:** "My SSN is 123-45-6789, help me"
2. **See block:** 🛡️ input block immediately
3. **Explain:** "Blocked before even processing"

### Demo Part 4: Stats & Monitoring (1 minute)

1. **Open Details:** Show stats (blocks, checks, rate)
2. **Explain:** "All logged to Galileo Console"
3. **Show benefits:**
   - Real-time protection
   - Production-ready
   - Comprehensive logging

## 🎯 Key Benefits

### For Production

1. **PII Protection**
   - Prevents data leaks
   - GDPR/HIPAA compliance
   - Customer trust

2. **Content Safety**
   - Blocks toxic/sexist content
   - Brand protection
   - User safety

3. **Hallucination Prevention**
   - Blocks suspicious trades
   - Reduces errors
   - Builds confidence

4. **Observability**
   - All logged to Galileo
   - Pattern detection
   - Continuous improvement

### For Demos

1. **Visual Impact**
   - 🛡️ Shield icon is clear
   - ✅ Success indicators
   - Real-time stats

2. **Easy to Show**
   - Simple toggle
   - Quick tests
   - Immediate feedback

3. **Compelling Story**
   - "This blocks PII leaks"
   - "This prevents wrong trades"
   - "This keeps users safe"

## 🚀 Quick Commands

### Install
```bash
pip install galileo-protect
```

### Run
```bash
streamlit run app.py
```

### Test
```bash
python test_guardrails.py
```

### Enable
```python
from guardrails_config import get_guardrails_manager
guardrails = get_guardrails_manager()
guardrails.enable()
```

## 📚 Documentation

- **Full Guide:** [GUARDRAILS_GUIDE.md](GUARDRAILS_GUIDE.md)
- **Main README:** [README.md](README.md) (Guardrails section)
- **Test Script:** [test_guardrails.py](test_guardrails.py)
- **This Summary:** [GUARDRAILS_SUMMARY.md](GUARDRAILS_SUMMARY.md)

## ✅ Summary

**What:** Real-time content filtering and safety for production AI agents

**Why:** Protect against PII leaks, inappropriate content, and hallucinated actions

**How:** Galileo Protect with input/output/trade guardrails

**Result:** Production-ready safety with comprehensive observability

**Test it:** `streamlit run app.py` → Enable Guardrails → Try examples! 🛡️

---

**Built for:** Galileo Golden Demo
**Created:** 2025
**Status:** ✅ Complete and ready for demos!

