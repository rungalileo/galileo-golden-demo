# ✅ Live Stock Data Integration Complete!

## What's Been Added

Your finance agent can now use **real-time stock prices and market news** from live APIs!

## Quick Start (30 Seconds!)

```bash
# 1. Install (no API key needed!)
pip install yfinance

# 2. Enable live data
echo 'USE_LIVE_DATA = "true"' >> .streamlit/secrets.toml

# 3. Run
streamlit run app.py

# 4. Try it
# Ask: "What's the current price of AAPL?"
# → Gets REAL stock price!
```

## Supported APIs

### Stock Prices

✅ **Yahoo Finance (yfinance)** - Recommended for quick start
  - Free, no API key needed
  - Unlimited calls
  - Real-time data
  - Works immediately!

✅ **Alpha Vantage** - Recommended for production
  - Free tier: 25 calls/day
  - Official API
  - Includes news
  - Get key: https://www.alphavantage.co/support/#api-key

✅ **Finnhub** - Alternative
  - Free tier: 60 calls/minute
  - Get key: https://finnhub.io/

### Market News

✅ **Alpha Vantage News** - Included with stock API
  - Financial news with sentiment
  - Stock-specific news

✅ **NewsAPI** - Additional news source
  - Free tier: 100 calls/day
  - Get key: https://newsapi.org/

## Files Created

1. **`domains/finance/tools/live_data.py`** - Live API integrations
   - Yahoo Finance integration
   - Alpha Vantage integration
   - NewsAPI integration
   - Automatic fallback system

2. **`LIVE_DATA_SETUP.md`** - Complete documentation
   - API comparison
   - Setup instructions
   - Configuration options
   - Troubleshooting

3. **`setup_live_data.sh`** - Automated setup script
   - Interactive installation
   - API key configuration
   - Quick start or full setup

## Files Modified

1. **`requirements.txt`** - Added:
   ```
   yfinance
   requests
   alpha-vantage
   ```

2. **`domains/finance/tools/logic.py`** - Updated:
   - Checks `USE_LIVE_DATA` environment variable
   - Tries live APIs first
   - Falls back to mock data if needed
   - No breaking changes!

3. **`README.md`** - Added live data section

## How It Works

### Smart Fallback System

```
User asks for stock price
        ↓
USE_LIVE_DATA=true?
        ↓
    Yes → Try live APIs:
           1. Yahoo Finance (yfinance)
           2. Alpha Vantage (if key set)
           3. Mock data (if all fail)
        ↓
    No → Use mock data
```

### Environment Variable Control

**Enable live data:**
```bash
USE_LIVE_DATA=true
```

**Disable (use mock data):**
```bash
USE_LIVE_DATA=false
# or leave unset (default)
```

## API Keys (Optional)

### In `.streamlit/secrets.toml`:

```toml
# Required: Enable live data
USE_LIVE_DATA = "true"

# Optional: For more features
ALPHA_VANTAGE_API_KEY = "your_key_here"
NEWSAPI_KEY = "your_key_here"
FINNHUB_API_KEY = "your_key_here"
```

### In `.env`:

```bash
USE_LIVE_DATA=true
ALPHA_VANTAGE_API_KEY=your_key_here
NEWSAPI_KEY=your_key_here
```

## Examples

### Real-Time Stock Price

**Ask:** "What's the current price of TSLA?"

**Response:**
```json
{
  "ticker": "TSLA",
  "price": 177.77,
  "change": -2.33,
  "change_percent": -1.29,
  "volume": 67890123,
  "high": 180.00,
  "low": 177.00,
  "open": 179.00,
  "market_cap": 562000000000,
  "pe_ratio": 71.2,
  "company_name": "Tesla, Inc.",
  "source": "Yahoo Finance (yfinance)"
}
```

### Market News (With Alpha Vantage)

**Ask:** "What's the latest news about NVDA?"

**Response:**
```json
{
  "articles": [
    {
      "title": "NVIDIA announces new AI chip...",
      "summary": "NVIDIA Corporation today...",
      "sentiment": "positive",
      "sentiment_score": 0.82,
      "published": "2024-10-08T10:30:00Z"
    }
  ],
  "source": "Alpha Vantage News"
}
```

## Testing

### Test Live Data

```bash
python -c "
from domains.finance.tools.logic import get_stock_price
import os
os.environ['USE_LIVE_DATA'] = 'true'
print(get_stock_price('AAPL'))
"
```

### Test in UI

1. `streamlit run app.py`
2. Chat tab
3. "What's the price of GOOGL?"
4. Should show real-time data!

## Rate Limits

| Service | Free Tier | Paid |
|---------|-----------|------|
| Yahoo Finance | Unlimited | N/A |
| Alpha Vantage | 25/day | $50/mo → 75/min |
| NewsAPI | 100/day | $449/mo → 10k/day |
| Finnhub | 60/min | $60/mo → 300/min |

## Troubleshooting

**"yfinance not installed"**
```bash
pip install yfinance
```

**"API key not found"**
- Check `.streamlit/secrets.toml` or `.env`
- Make sure key is spelled correctly

**"Rate limit exceeded"**
- You've hit daily limit
- Wait for reset or use mock data
- Consider upgrading to paid tier

**Still using mock data?**
- Verify `USE_LIVE_DATA = "true"` (not "True" or "TRUE")
- Check logs for errors
- Make sure dependencies installed

## When to Use Live vs Mock Data

### Use Live Data When:
✅ Demoing with real-time prices  
✅ Testing agent with current market  
✅ Showing realistic scenarios  
✅ Production deployment  

### Use Mock Data When:
✅ Development/testing  
✅ Consistent test results needed  
✅ No internet connection  
✅ Avoiding API rate limits  
✅ Running many experiments  

## What's Next

### Future Enhancements

You can easily add:
- Historical price data
- Company fundamentals (P/E, market cap trends)
- Technical indicators (RSI, MACD, etc.)
- Earnings reports
- Analyst ratings
- Options data
- Crypto prices

All use the same pattern in `live_data.py`!

## Summary

🎯 **Easiest**: Yahoo Finance - Works immediately, no setup  
📈 **Best**: Alpha Vantage - Free tier, official, includes news  
🔄 **Smart**: Automatic fallback to mock data if APIs fail  
⚡ **Fast**: Install in 30 seconds, working in 1 minute  

---

**Files:**
- 📄 `domains/finance/tools/live_data.py` - API integrations
- 📘 `LIVE_DATA_SETUP.md` - Full documentation
- 🔧 `setup_live_data.sh` - Automated setup
- 📝 `LIVE_DATA_SUMMARY.md` - This file

**Quick Start:** `pip install yfinance` + `USE_LIVE_DATA=true` → Done!

**Try it now:** Ask the agent for a real stock price! 🚀

