# Finance Domain 💰

A stock market analyst and trading assistant with RAG capabilities for financial document analysis.

## Available Tools

The finance domain includes 4 tools (3 domain-specific + 1 RAG retrieval tool):

### 1. `get_stock_price`
Get current stock price and market data for any ticker symbol.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)

**Example queries:**
- "What's the current price of AAPL?"
- "Get me the stock price for Tesla"
- "How much is Microsoft stock trading at?"

### 2. `purchase_stocks`
Execute a stock purchase order.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol to purchase
- `quantity` (integer, required): Number of shares to purchase
- `price` (number, required): Price per share

**Example queries:**
- "Buy 10 shares of TSLA at 180 dollars per share"
- "Purchase 50 shares of AAPL at 178 per share"
- "I want to buy 100 shares of MSFT at 415 dollars each"

### 3. `sell_stocks`
Execute a stock sale order.

**Parameters:**
- `ticker` (string, required): Stock ticker symbol to sell
- `quantity` (integer, required): Number of shares to sell
- `price` (number, required): Price per share

**Example queries:**
- "Sell 5 shares of AMZN at 175 per share"
- "I want to sell 20 shares of GOOGL at 148 dollars each"
- "Sell 15 shares of META at 485 per share"

### 4. `retrieve_finance_documents` (RAG Tool)
Automatically added when RAG is enabled. Retrieves information from the finance knowledge base.

**What it searches:**
- Company financial reports and earnings transcripts
- Quarterly performance data
- Revenue analysis and comparisons

This tool is invoked automatically by the agent when you ask questions about financial information in the documents.
**Example queries that trigger the RAG tool:**
- "What was Costco's revenue in Q1 and how did it compare to the previous quarter?"
- "What was Adobe's revenue in Q4?"
- "How did Broadcom perform in their most recent quarter?"
- "What was Walmart's Q4 revenue compared to Q3?"

## Mock Data

The domain includes realistic mock stock prices for:
- AVGO (Broadcom)
- GPS (Gap)
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Google)
- AMZN (Amazon)
- META (Meta)
- TSLA (Tesla)
- NVDA (NVIDIA)

## Galileo Project

Logs to: `galileo-demo-finance` unless custom project is configured

## Try It Out!

Start the app and navigate to: `http://localhost:8501/finance`

**Quick test queries:**
1. "What's the price of AAPL stock?"
2. "Buy 10 shares of TSLA at 180 per share"
3. "What was Costco's Q1 revenue?"

> **Note:** This is a demo application designed to showcase Galileo's observability capabilities. It is not intended for real financial trading or investment decisions. All stock data is simulated for demonstration purposes.

