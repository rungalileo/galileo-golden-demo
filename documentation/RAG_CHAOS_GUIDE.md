# RAG Chaos Engineering Guide

## Overview

RAG (Retrieval-Augmented Generation) Chaos simulates vector database failures and disconnections. **Works with both Pinecone and ChromaDB** (or any vector database).

## ✅ How It Works

### Implementation Level

RAG chaos works at the **tool registration level**, not the vector DB level:

1. When creating an agent, it checks if RAG should be disconnected
2. If chaos triggers (20% chance), the RAG tool is **never added** to the agent
3. Agent attempts to use RAG → tool doesn't exist → simulates database down
4. **Database-agnostic**: Works regardless of which vector DB you use

### Code Flow

```python
# In agent.py (lines 132-141)
if rag_config.get("enabled", False):
    # Check if RAG should be disconnected (chaos)
    if CHAOS_AVAILABLE:
        chaos = get_chaos_engine()
        should_fail, error_msg = chaos.should_disconnect_rag()
        if should_fail:
            print(f"🔥 CHAOS: RAG disconnected - {error_msg}")
            return  # Skip adding RAG tool
    
    # Normal path: Add RAG tool
    rag_tool = create_domain_rag_tool(domain_name, top_k)
    self.tools.append(rag_tool)
```

## 🔥 Error Types

### Generic Vector DB Errors
- ✅ "Vector database connection timeout"
- ✅ "Vector database service unavailable"
- ✅ "Embedding model failed to respond"
- ✅ "RAG retrieval returned empty results"
- ✅ "Document index corrupted"

### Pinecone-Specific Errors
- ✅ "Pinecone index unavailable (503 Service Unavailable)"
- ✅ "Pinecone API rate limit exceeded (429 Too Many Requests)"
- ✅ "Pinecone connection timeout after 30 seconds"
- ✅ "Pinecone index not found (404 Not Found)"

### ChromaDB-Specific Errors
- ✅ "ChromaDB service unavailable"
- ✅ "ChromaDB connection refused"

### Embedding Errors
- ✅ "OpenAI Embeddings API timeout"
- ✅ "Embedding dimension mismatch error"
- ✅ "Failed to generate embeddings for query"

## 📊 Configuration

### Default Settings
- **Failure Rate**: 20%
- **When Enabled**: RAG tool randomly unavailable
- **Impact**: Agent can't access knowledge base

### Enable RAG Chaos

**Via UI:**
```
Sidebar → Chaos Engineering → Chaos Controls
✅ RAG Disconnects (20% chance)
```

**Via Code:**
```python
from chaos_engine import get_chaos_engine

chaos = get_chaos_engine()
chaos.enable_rag_chaos(True)  # 20% failure rate
```

**Via CLI:**
```bash
python build_chaos_logs.py --rag-chaos
```

## 🎯 What This Demonstrates

### 1. Database Unavailability
Simulates when vector database goes down:
- Pinecone service outage
- ChromaDB container crashed
- Network partition

### 2. API Rate Limits
Pinecone free tier limits:
- 100 requests/minute
- Rate limiting during high traffic

### 3. Configuration Issues
Common production problems:
- Wrong index name
- Missing API keys
- Environment mismatch

### 4. Embedding Failures
OpenAI Embeddings issues:
- API timeouts
- Rate limits
- Service degradation

## 📝 Example Scenarios

### Scenario 1: RAG Unavailable During Agent Creation

```python
# Enable RAG chaos
chaos.enable_rag_chaos(True)

# Create agent
agent = LangGraphAgent("finance")
# 20% chance RAG tool won't be added

# Try to use RAG
response = agent.chat("What does the 10-Q say about revenue?")
# If RAG chaos triggered:
# - Agent doesn't have RAG tool
# - Can't access knowledge base
# - Falls back to general knowledge or says it can't answer
```

**In Logs:**
```
🔥 CHAOS: RAG disconnected - Pinecone index unavailable (503 Service Unavailable)
⚠️  Skipping RAG tool addition due to chaos injection
RAG disabled for domain 'finance' (chaos mode)
```

### Scenario 2: Comparing With and Without RAG

```python
# Run 10 queries with RAG chaos enabled
results = []
for query in test_queries:
    try:
        response = agent.chat(query)
        results.append({"query": query, "success": True})
    except Exception as e:
        results.append({"query": query, "success": False, "error": str(e)})

# Analyze results:
# - ~20% won't have RAG access
# - Answers will be generic without RAG
# - Shows importance of RAG for domain knowledge
```

### Scenario 3: Observing Agent Behavior

```python
# Question that requires RAG
query = "What were Q3 revenue figures from the 10-Q?"

# With RAG: Gets specific answer from document
# Without RAG (chaos): "I don't have access to that document"
```

## 🔍 Debugging in Galileo

### What to Look For

1. **Missing RAG Tool Calls**
   - Filter spans by tool name
   - Look for absence of `retrieve_finance_documents` calls
   - Compare to runs without chaos

2. **Agent Response Quality**
   - Responses without RAG are more generic
   - May hallucinate without knowledge base access
   - Lower accuracy on domain-specific questions

3. **Error Patterns**
   - Track which error messages appear most
   - Correlate with user complaints
   - Identify which scenarios cause issues

### Galileo Queries

**Find runs without RAG:**
```
# Look for absence of RAG tool spans
# Or check agent metadata for "rag_available: false"
```

**Compare RAG vs No-RAG:**
```
# Group by presence of RAG spans
# Compare response quality metrics
```

## 🎬 Demo Talking Points

### 1. "RAG is critical infrastructure..."
- Show query with RAG working
- Enable chaos, show same query failing
- Demonstrate impact of database unavailability

### 2. "This simulates real outages..."
- Pinecone service outages
- API rate limits
- Network issues
- Configuration problems

### 3. "Different error types..."
- Show variety: 503, 429, timeout, not found
- Each represents different failure mode
- Realistic production scenarios

### 4. "Galileo shows the impact..."
- Compare traces with/without RAG
- See response quality difference
- Track availability metrics

## 💡 Production Insights

### What This Simulates

**Pinecone Issues:**
- Service outages (happens occasionally)
- API rate limits (free tier: 100 req/min)
- Index not found (configuration error)
- Connection timeouts (network issues)

**ChromaDB Issues:**
- Container crashed (deployment issue)
- Service unavailable (resource constraints)
- Connection refused (wrong port/host)

**Embedding Issues:**
- OpenAI API down
- Rate limits exceeded
- Timeout during high load
- Dimension mismatches (config error)

### Real-World Frequency

These failures **do happen** in production:
- Pinecone outages: ~99.9% uptime (few hours/year)
- API rate limits: Common with free tier
- Configuration errors: Common during deployments
- Embedding API issues: OpenAI outages happen

## 🚀 Best Practices

### 1. Monitor RAG Availability
```python
# Track RAG tool availability
if "retrieve_documents" in agent.tools:
    rag_available = True
else:
    rag_available = False
    
# Log to Galileo metadata
metadata = {"rag_available": rag_available}
```

### 2. Graceful Degradation
```python
# Handle RAG unavailability
try:
    response = agent.chat(query)
except Exception as e:
    if "RAG" in str(e):
        # Fall back to general knowledge
        response = agent.chat_without_rag(query)
```

### 3. Retry Logic
```python
# Retry RAG initialization
max_retries = 3
for attempt in range(max_retries):
    try:
        agent = create_agent_with_rag()
        break
    except RAGUnavailableError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
```

## 📈 Metrics to Track

In Galileo, monitor:

1. **RAG Availability Rate**
   - % of sessions with RAG tool available
   - Track over time

2. **Response Quality by RAG Status**
   - Compare metrics with/without RAG
   - Shows RAG's impact on accuracy

3. **Error Distribution**
   - Which RAG errors occur most
   - Pinecone vs ChromaDB vs Embeddings

4. **Recovery Time**
   - How long until RAG available again
   - Track retry success rates

## 🔧 Technical Details

### Why Tool-Level Chaos?

We disconnect at **tool registration** rather than runtime because:

1. **More Realistic**: Database down = tool unavailable
2. **Clean Failure**: Agent knows RAG isn't available
3. **Database Agnostic**: Works for any vector DB
4. **Easy to Implement**: Single check during agent init

### Alternative: Runtime Failures

Could also fail at runtime:
```python
def search(self, query: str) -> str:
    # Check chaos at runtime
    if should_fail:
        raise VectorDBError("Pinecone unavailable")
    
    # Normal retrieval
    return self.retrieval_chain.invoke(query)
```

**Pros**: More granular, can fail mid-session
**Cons**: More complex, DB-specific code

### Current Implementation

Current approach (tool-level) is **simpler and more realistic**:
- Database down = entire tool unavailable
- Works for Pinecone, ChromaDB, or any DB
- Clean separation of concerns

## ✅ Summary

**RAG Chaos is database-agnostic and works for:**
- ✅ Pinecone (current setup)
- ✅ ChromaDB (legacy support)
- ✅ Any other vector database

**Simulates realistic failures:**
- ✅ Service outages (503)
- ✅ Rate limits (429)
- ✅ Timeouts
- ✅ Configuration errors (404)
- ✅ Embedding API issues

**Demonstrates observability value:**
- ✅ Impact of RAG unavailability
- ✅ Response quality without knowledge base
- ✅ Error tracking and analysis
- ✅ Availability monitoring

Ready for demos showing RAG infrastructure resilience! 🚀

