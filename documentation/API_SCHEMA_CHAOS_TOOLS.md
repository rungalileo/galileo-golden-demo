# API Schema Evolution Chaos Tools

## 🔥 NEW Feature: Realistic API Change Simulation

We've added **5 new chaos tools** that simulate real-world API evolution problems. These are some of the sneakiest and most realistic chaos scenarios!

## The 5 New Tools

### 1. `get_stock_price_v2()` - API Version Wrapper

**What it does:** Wraps the response in a v2 metadata layer

**Example:**
```json
// Normal:
{"ticker": "AAPL", "price": 178.72, ...}

// V2:
{
  "data": {"ticker": "AAPL", "price": 178.72, ...},
  "api_version": "2.0",
  "timestamp": 1234567890,
  "success": true,
  "meta": {
    "request_id": "req_12345",
    "server": "api-v2.example.com"
  }
}
```

**Demonstrates:** API versioning where structure changes between versions

---

### 2. `get_stock_price_unstable_schema()` - Version Drift

**What it does:** 30% chance returns v2 format, 70% returns v1

**Why it's sneaky:** This is EXACTLY what happens during rolling deployments!

**Real-world scenario:**
```
Request 1 → Server A (v1) → Flat structure ✅
Request 2 → Server B (v2) → Nested structure ❌
Request 3 → Server A (v1) → Flat structure ✅
```

**Demonstrates:** 
- Rolling deployments with mixed versions
- Load balancer routing to different server versions
- Canary deployments gone wrong

---

### 3. `get_stock_price_evolving()` - Surprise Fields

**What it does:** 20% chance adds undocumented beta fields

**Example:**
```json
{
  "ticker": "AAPL",
  "price": 178.72,
  // Surprise! New fields appear:
  "beta_features": {
    "sentiment_score": 0.75,
    "analyst_rating": "buy",
    "risk_level": "low",
    "ai_prediction": 182.50
  },
  "experimental": true,
  "feature_flags": ["sentiment", "ai_predict"]
}
```

**Demonstrates:**
- Beta features rolling out to production
- A/B testing with new fields
- Feature flags changing response structure
- New fields appearing without documentation

---

### 4. `get_stock_price_deprecated()` - Field Removal

**What it does:** 15% chance removes deprecated fields

**Example:**
```json
{
  "ticker": "AAPL",
  "price": 178.72,
  // Missing: "open" and "volume" fields!
  "_deprecated_fields_removed": ["open", "volume"],
  "_migration_notice": "Some fields have been deprecated. See API v2 docs."
}
```

**Demonstrates:**
- Deprecation periods where fields randomly disappear
- Gradual migration breaking old code
- Warnings about deprecated fields
- Transition period chaos

---

### 5. `get_stock_price_breaking_change()` - Type Changes

**What it does:** 10% chance changes field types (the nightmare scenario!)

**Three types of breaking changes:**

**A) Numbers → Strings**
```json
{
  "price": "178.72",      // Was: 178.72
  "change": "1.23",       // Was: 1.23
  "volume": "52345678"    // Was: 52345678
}
```

**B) Truncate Floats → Integers**
```json
{
  "price": 178,           // Lost precision! Was: 178.72
  "change": 1,            // Was: 1.23
  "change_percent": 0     // Was: 0.69
}
```

**C) Rename Fields**
```json
{
  "current_price": 178.72,    // Was: "price"
  "price_change": 1.23,       // Was: "change"
  "pct_change": 0.69         // Was: "change_percent"
}
```

**Demonstrates:**
- Type changes that break parsers
- Precision loss in numeric fields
- Field renames without proper versioning
- Breaking changes that slip through

---

## Why These Are Sneaky

These scenarios are **extremely realistic** and happen in production all the time:

1. **During Rolling Deployments**
   - Some servers on v1, some on v2
   - Same request, different response structure
   - Hard to reproduce, intermittent failures

2. **During API Migrations**
   - Old and new formats coexist
   - Gradual deprecation of fields
   - Type changes for "optimization"

3. **During A/B Testing**
   - Different users get different schemas
   - Beta features leak to production
   - Feature flags change responses

4. **After Breaking Changes**
   - Someone pushes a "minor" change
   - Field types change unexpectedly
   - Old clients break silently

## What Galileo Catches

With these chaos tools, Galileo will show:

✅ **Schema inconsistencies** - Compare response structures across requests
✅ **Type mismatches** - See when numbers become strings
✅ **Missing fields** - Track which fields disappear
✅ **New fields** - Identify undocumented additions
✅ **Version drift** - Spot rolling deployment issues
✅ **Breaking changes** - Catch field renames and type changes

## Demo Script

```python
# Enable chaos tools with schema evolution
os.environ["USE_CHAOS_TOOLS"] = "true"

# Ask for the same stock multiple times
for i in range(5):
    response = agent.chat("What's the price of AAPL?")
    # Some calls work, some fail due to schema changes!
    # Galileo shows exactly which schema was returned each time
```

**Expected results:**
- Call 1: Works fine (v1 schema)
- Call 2: Fails parsing (v2 nested schema)
- Call 3: Works but has extra fields (beta features)
- Call 4: Fails due to missing field (deprecated)
- Call 5: Type error (number became string)

**In Galileo traces:**
- See exact response structure for each call
- Compare schemas side-by-side
- Identify which tool was used
- Track success/failure rates
- Pinpoint where parsing broke

## Total Chaos Tools Now

| Category | Count |
|----------|-------|
| **Standard Tools** | 5 |
| **Pattern 1: Minimal/No Fallback** | 2 |
| **Pattern 2: Different Formats** | 2 |
| **Pattern 3: Artificial Latency** | 2 |
| **Pattern 4: Subtle Bugs** | 2 |
| **Pattern 5: Inefficiency** | 2 |
| **Pattern 6: Schema Evolution** | 5 ⬅️ NEW! |
| **Pattern 7: Direct API Access** | 2 |
| **TOTAL** | **22 tools** |

## Key Talking Points

1. **"This is what happens during rolling deployments..."**
   - Show `unstable_schema` returning different formats
   - Point out 30% failure rate in Galileo

2. **"This is what beta testing looks like..."**
   - Show `evolving` adding surprise fields
   - Demonstrate how agents handle unexpected data

3. **"This is the nightmare scenario - breaking changes..."**
   - Show `breaking_change` changing types
   - Watch agent fail when "178.72" (string) != 178.72 (number)

4. **"Even with full observability, these are hard to catch..."**
   - All tools log to Galileo
   - But intermittent schema changes are subtle
   - Galileo makes them visible and debuggable

## Usage

```bash
# Enable via environment
export USE_CHAOS_TOOLS=true

# Or via UI
Sidebar → Chaos Engineering → Confusing Tools ✅
```

**Result:** Agent now has 22 tools (5 standard + 17 chaos)

---

## The Sneaky Factor 🔥

These tools simulate the **exact problems** that engineers face with:
- Microservices with version drift
- Third-party APIs that change without notice  
- Legacy systems being migrated
- A/B tests leaking to production
- "Minor" updates that break everything

Perfect for demonstrating how Galileo helps you:
1. Spot schema inconsistencies
2. Track API evolution over time
3. Debug intermittent failures
4. Validate type contracts
5. Monitor breaking changes

🎯 **This is the most realistic chaos testing yet!**

