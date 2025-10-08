# Live Stock Data & News Setup

## Overview

The finance agent can now use **real-time stock prices and market news** from live APIs instead of mock data!

## 🎛️ Easiest Way: UI Controls (New!)

The Streamlit app now has **built-in controls** in the sidebar - no configuration files needed!

### Quick Start with UI

1. **Start the app**: `streamlit run app.py`
2. **Open sidebar** → Find "⚙️ Live Data Settings"
3. **Toggle ON** "Use Live Stock Data"
4. **Select source** (or leave as "Auto")
5. **Try it!** Ask: "What's the price of AAPL?"

**That's it!** No editing files, no command line. Just click and go!

See **[UI_CONTROLS_GUIDE.md](UI_CONTROLS_GUIDE.md)** for full details.

---

## Alternative: Manual Configuration

If you prefer to set it up via configuration files (or for permanent settings):

## Supported APIs

### Stock Prices

| API | Cost | API Key Required | Rate Limit | Best For |
|-----|------|------------------|------------|----------|
| **Yahoo Finance** (yfinance) | Free | ❌ No | Unlimited | Quick start, demos |
| **Alpha Vantage** | Free tier | ✅ Yes | 25 calls/day (free) | Demos, news included |
| **Finnhub** | Free tier | ✅ Yes | 60 calls/min (free) | Higher rate limits |

### Market News

| API | Cost | API Key Required | Rate Limit | Best For |
|-----|------|------------------|------------|----------|
| **Alpha Vantage News** | Free tier | ✅ Yes | 25 calls/day (free) | Stock-specific news |
| **NewsAPI** | Free tier | ✅ Yes | 100 calls/day (free) | General + financial news |

## Quick Start (No API Key Needed!)

The easiest option is Yahoo Finance via `yfinance` - it works out of the box!

### Step 1: Install Dependencies

```bash
pip install yfinance alpha-vantage requests
```

Or update all requirements:
```bash
pip install -r requirements.txt
```

### Step 2: Enable Live Data

Add to your `.env` file or `.streamlit/secrets.toml`:

```bash
USE_LIVE_DATA=true
```

### Step 3: Run the App

```bash
streamlit run app.py
```

That's it! The agent will now use real-time stock prices from Yahoo Finance.

## Advanced Setup (With API Keys)

For better reliability and news data, set up API keys:

### Option 1: Alpha Vantage (Recommended)

**Pros**: Stock prices + news in one API, free tier available

1. **Get API Key**: https://www.alphavantage.co/support/#api-key
2. **Add to secrets**:
   ```toml
   # .streamlit/secrets.toml
   ALPHA_VANTAGE_API_KEY = "your_key_here"
   USE_LIVE_DATA = "true"
   ```
3. **Free tier**: 25 API calls per day

### Option 2: NewsAPI (For Additional News)

1. **Get API Key**: https://newsapi.org/register
2. **Add to secrets**:
   ```toml
   # .streamlit/secrets.toml
   NEWSAPI_KEY = "your_key_here"
   ```
3. **Free tier**: 100 requests/day (with 1-day delay on some content)

### Option 3: Finnhub (Alternative)

1. **Get API Key**: https://finnhub.io/register
2. **Add to secrets**:
   ```toml
   FINNHUB_API_KEY = "your_key_here"
   ```
3. **Free tier**: 60 calls/minute

## Configuration File

### Using .env File

Create `.env` in project root:

```bash
# Enable live data
USE_LIVE_DATA=true

# API Keys (optional - yfinance works without them)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
NEWSAPI_KEY=your_newsapi_key_here
FINNHUB_API_KEY=your_finnhub_key_here

# Galileo settings (keep existing)
GALILEO_API_KEY=your_galileo_key
GALILEO_PROJECT=your_project
```

### Using Streamlit Secrets

Add to `.streamlit/secrets.toml`:

```toml
# Live data toggle
USE_LIVE_DATA = "true"

# API Keys
ALPHA_VANTAGE_API_KEY = "your_key_here"
NEWSAPI_KEY = "your_key_here"

# Galileo (keep existing)
openai_api_key = "your_key"
galileo_api_key = "your_key"
galileo_project = "your_project"
```

## How It Works

### Automatic Fallback System

The system tries sources in this order:

**For Stock Prices:**
1. **Yahoo Finance** (yfinance) - No API key, unlimited
2. **Alpha Vantage** - If API key set
3. **Mock Data** - If all else fails

**For News:**
1. **Alpha Vantage News** - If API key set
2. **NewsAPI** - If API key set
3. **Error** - If no keys configured

### Environment Variable: `USE_LIVE_DATA`

- `USE_LIVE_DATA=true` → Use live APIs
- `USE_LIVE_DATA=false` or not set → Use mock data (default)

## Testing

### Quick Test - Stock Price

```python
# In Python or Streamlit app
from domains.finance.tools.logic import get_stock_price

# Will use live data if enabled
result = get_stock_price("AAPL")
print(result)
```

### In Streamlit UI

1. Start app: `streamlit run app.py`
2. Go to Chat tab
3. Ask: "What's the current price of AAPL?"
4. Should return real-time data!

### Check What's Being Used

Look for log messages:
- `"✓ Live data mode enabled"` → Live APIs active
- `"Using mock data mode"` → Mock data active
- `"Fetching live data for AAPL"` → API call being made

## API Response Formats

### Stock Price Response

```json
{
  "ticker": "AAPL",
  "price": 178.72,
  "change": 1.23,
  "change_percent": 0.69,
  "volume": 52345678,
  "high": 179.50,
  "low": 177.80,
  "open": 178.00,
  "market_cap": 2750000000000,
  "pe_ratio": 29.5,
  "company_name": "Apple Inc.",
  "currency": "USD",
  "source": "Yahoo Finance (yfinance)"
}
```

### News Response

```json
{
  "articles": [
    {
      "title": "Apple announces new product...",
      "summary": "Apple Inc. today announced...",
      "url": "https://...",
      "source": "Reuters",
      "published": "2024-10-08T10:30:00Z",
      "sentiment": "positive",
      "sentiment_score": 0.75,
      "tickers": ["AAPL"]
    }
  ],
  "count": 5,
  "source": "Alpha Vantage News"
}
```

## Rate Limits & Best Practices

### Free Tier Limits

| Service | Daily Limit | Notes |
|---------|-------------|-------|
| Yahoo Finance | Unlimited | No API key needed, but unofficial |
| Alpha Vantage | 25 calls/day | 5 calls/minute |
| NewsAPI | 100 calls/day | 1-day delay on some content (free tier) |

### Tips for Staying Within Limits

1. **Use Mock Data for Development**: Set `USE_LIVE_DATA=false` while coding
2. **Cache Responses**: The app naturally caches within a session
3. **Test with Specific Stocks**: Use a small set of tickers for testing
4. **Monitor Usage**: Check API dashboard for your usage stats

### Upgrading for Production

If you need more calls:

- **Alpha Vantage Pro**: $50/month → 75 calls/minute
- **NewsAPI Pro**: $449/month → 10,000 calls/day
- **Finnhub Pro**: $60/month → 300 calls/minute

## Troubleshooting

### "yfinance not installed"

```bash
pip install yfinance
```

### "All live data sources failed"

1. Check internet connection
2. Verify API keys are correct
3. Check if you've hit rate limits
4. Try with mock data: `USE_LIVE_DATA=false`

### "API key not found"

Make sure keys are in `.streamlit/secrets.toml` or `.env`:
```toml
ALPHA_VANTAGE_API_KEY = "your_actual_key"
```

### Rate Limit Errors

You've hit the daily/minute limit. Either:
- Wait for limit to reset
- Use mock data temporarily
- Upgrade to paid tier

## Comparison: Mock vs Live Data

| Feature | Mock Data | Live Data (yfinance) | Live Data (Alpha Vantage) |
|---------|-----------|---------------------|---------------------------|
| Setup | ✅ None | ✅ pip install | ⚠️ API key needed |
| Cost | ✅ Free | ✅ Free | ✅ Free tier available |
| Real-time | ❌ No | ✅ Yes | ✅ Yes |
| News | ❌ No | ❌ No | ✅ Yes |
| Rate Limits | ✅ None | ✅ Unlimited | ⚠️ 25/day (free) |
| Reliability | ✅ 100% | ⚠️ Unofficial API | ✅ Official API |
| Best For | Demos, dev | Quick start, testing | Production, news |

## Example: Full Setup

```bash
# 1. Install dependencies
pip install yfinance alpha-vantage requests

# 2. Get Alpha Vantage key (optional but recommended)
# Visit: https://www.alphavantage.co/support/#api-key

# 3. Configure secrets
cat >> .streamlit/secrets.toml << EOF
USE_LIVE_DATA = "true"
ALPHA_VANTAGE_API_KEY = "your_key_here"
EOF

# 4. Run the app
streamlit run app.py

# 5. Test it
# Ask: "What's the current price of TSLA?"
# Should return real-time data!
```

## What's Next

### Adding More Features

The live_data.py module supports:
- ✅ Real-time stock prices
- ✅ Market news
- 🔄 Company fundamentals (can add)
- 🔄 Historical data (can add)
- 🔄 Market indicators (can add)

### Adding as Tools

You can expose news as a tool:

```python
# In tools/schema.json, add:
{
  "name": "get_market_news",
  "description": "Get latest market news for a stock or general market news",
  "parameters": {
    "type": "object",
    "properties": {
      "ticker": {
        "type": "string",
        "description": "Stock ticker to get news for (optional)"
      }
    }
  }
}
```

Then add to TOOLS in logic.py.

## Summary

✅ **Easiest**: Yahoo Finance (yfinance) - Works immediately, no API key  
✅ **Recommended**: Alpha Vantage - Free tier, official API, includes news  
✅ **Alternative**: NewsAPI - Great for additional news sources  

🎯 **Quick Start**: `pip install yfinance` + `USE_LIVE_DATA=true` → Done!  
📈 **With News**: Get Alpha Vantage key → Full stock data + sentiment analysis  
🔄 **Fallback**: Automatically falls back to mock data if APIs fail  

---

**Ready to try live data?** Set `USE_LIVE_DATA=true` and run the app! 🚀

