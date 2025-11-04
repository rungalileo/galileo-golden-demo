"""
Deliberately confusing tools for demonstrating Galileo's observability value

This module contains tools that look similar but have subtle differences:
- Some return minimal or different data formats
- Some have hidden latency
- Some return different formats
- Some have subtle bugs
- Some are redundant but less robust

Note: All tools still log to Galileo for proper observability!

Use these to show how Galileo helps identify:
1. Suboptimal tool choices by agents
2. Performance bottlenecks (latency, inefficiency)
3. Subtle data corruption and bugs
4. Error-prone paths (no fallback, brittle integrations)
5. Format inconsistencies and parsing issues

Usage:
    Set USE_CHAOS_TOOLS=true to expose these confusing alternatives
    alongside the normal tools.
"""
import json
import time
import os
import logging
import random
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
# GalileoLogger import removed - all logging handled by GalileoCallback


# =============================================================================
# Pydantic Input Schemas (to avoid JsonSchema errors with GalileoLogger)
# =============================================================================

class StockTickerInput(BaseModel):
    """Input schema for tools that take a single ticker parameter."""
    ticker: str = Field(..., description="The stock ticker symbol (e.g., AAPL, GOOGL, MSFT)")

class StockTickersInput(BaseModel):
    """Input schema for tools that take multiple tickers."""
    tickers: str = Field(..., description="Comma-separated list of stock ticker symbols (e.g., AAPL,GOOGL,MSFT)")


# Lazy import helpers to avoid circular dependency
_base_funcs = {}

def _get_base_function(name: str):
    """Lazy import of base functions to avoid circular dependency."""
    if not _base_funcs:
        import sys
        from pathlib import Path
        tools_dir = Path(__file__).parent
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import logic
        _base_funcs['get_stock_price'] = logic.get_stock_price
        _base_funcs['get_market_news'] = logic.get_market_news
        _base_funcs['MOCK_PRICE_DB'] = logic.MOCK_PRICE_DB
    return _base_funcs[name]

# Wrapper functions that lazy-load the base functions
def _base_get_stock_price(ticker: str) -> str:
    """Wrapper for base get_stock_price with lazy import."""
    return _get_base_function('get_stock_price')(ticker)

def _base_get_market_news(ticker: str, limit: int = 5) -> str:
    """Wrapper for base get_market_news with lazy import."""
    return _get_base_function('get_market_news')(ticker, limit)

def _get_mock_price_db():
    """Get the MOCK_PRICE_DB with lazy import."""
    return _get_base_function('MOCK_PRICE_DB')

# Try to import live data functions
try:
    from .live_data import get_live_stock_price, get_stock_price_yfinance, get_stock_price_alpha_vantage
    LIVE_DATA_AVAILABLE = True
except ImportError:
    try:
        from live_data import get_live_stock_price, get_stock_price_yfinance, get_stock_price_alpha_vantage
        LIVE_DATA_AVAILABLE = True
    except ImportError:
        LIVE_DATA_AVAILABLE = False
        logging.warning("Live data not available for chaos tools")


# =============================================================================
# CHAOS PATTERN 1: Tools without fallback handling
# =============================================================================

def get_stock_price_fast(ticker: str, ) -> str:
    """
    Get stock price quickly without overhead.
    
    ⚠️ CHAOS: Returns minimal data structure (just price info, no metadata)!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing minimal stock price data
    """
    logging.info(f"[CHAOS] get_stock_price_fast called (minimal data)")
    result = json.loads(_base_get_stock_price(ticker))
    
    # Return only essential fields - loses metadata
    minimal = {
        "ticker": ticker,
        "price": result.get("price", 0),
        "change": result.get("change", 0)
    }
    return json.dumps(minimal)


def fetch_stock_price(ticker: str, ) -> str:
    """
    Fetch the current stock price for a ticker.
    
    ⚠️ CHAOS: Similar to get_stock_price but without fallback handling!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price
    """
    logging.info(f"[CHAOS] fetch_stock_price called (no fallback)")
    
    # Check if user wants live data (respects USE_LIVE_DATA toggle)
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    
    # Only tries live data, no fallback to mock
    if use_live_data and LIVE_DATA_AVAILABLE:
        try:
            return get_live_stock_price(ticker)
        except Exception as e:
            raise Exception(f"Failed to fetch live data for {ticker}: {e}")
    else:
        if use_live_data:
            raise Exception("Live data requested but not available (install yfinance/alpha-vantage)")
        else:
            raise Exception("Live data disabled - enable USE_LIVE_DATA to use this tool")


# =============================================================================
# CHAOS PATTERN 2: Tools with different return formats
# =============================================================================

def lookup_stock_price(ticker: str, ) -> str:
    """
    Look up the current price for a stock ticker.
    
    ⚠️ CHAOS: Returns only the price as a plain string, losing all context!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        Plain string with just the price (e.g., "178.72")
    """
    logging.info(f"[CHAOS] lookup_stock_price called (returns string only)")
    data = json.loads(_base_get_stock_price(ticker))
    return str(data.get('price', 0))  # Just returns price, loses all other data


def get_stock_data(ticker: str, ) -> str:
    """
    Get comprehensive stock market data for a ticker.
    
    ⚠️ CHAOS: Returns different JSON structure than other tools!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with different field names (camelCase instead of snake_case)
    """
    logging.info(f"[CHAOS] get_stock_data called (different format)")
    data = json.loads(_base_get_stock_price(ticker))
    
    # Transform to different format - breaks downstream parsing
    return json.dumps({
        "tickerSymbol": data.get("ticker", ticker),
        "currentPrice": data.get("price", 0),
        "priceChange": data.get("change", 0),
        "percentChange": data.get("change_percent", 0),
        "tradingVolume": data.get("volume", 0),
        "dayHigh": data.get("high", 0),
        "dayLow": data.get("low", 0),
        "openPrice": data.get("open", 0)
    })


# =============================================================================
# CHAOS PATTERN 3: Tools with artificial latency
# =============================================================================

def get_current_stock_price(ticker: str, ) -> str:
    """
    Get the current stock price with real-time accuracy.
    
    ⚠️ CHAOS: Adds artificial 2-second delay for "accuracy"!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price
    """
    logging.info(f"[CHAOS] get_current_stock_price called (2s delay)")
    time.sleep(2)  # Unnecessary delay that hurts performance
    return _base_get_stock_price(ticker)


def get_stock_price_accurate(ticker: str, ) -> str:
    """
    Get highly accurate stock price with multiple validation checks.
    
    ⚠️ CHAOS: Adds random latency between 1-5 seconds!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price
    """
    delay = random.uniform(1.0, 5.0)
    logging.info(f"[CHAOS] get_stock_price_accurate called ({delay:.1f}s delay)")
    time.sleep(delay)  # Random delay makes performance unpredictable
    return _base_get_stock_price(ticker)


# =============================================================================
# CHAOS PATTERN 4: Tools with subtle bugs
# =============================================================================

def retrieve_stock_price(ticker: str, ) -> str:
    """
    Retrieve the stock price for a given ticker symbol.
    
    ⚠️ CHAOS: 10% chance of returning data for wrong ticker!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price (might be wrong ticker!)
    """
    actual_ticker = ticker.upper()
    
    # Subtle bug: Sometimes returns data for random ticker
    if random.random() < 0.1:  # 10% chance
        wrong_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        actual_ticker = random.choice(wrong_tickers)
        logging.warning(f"[CHAOS] retrieve_stock_price returning wrong ticker: {actual_ticker} instead of {ticker}")
    
    return _base_get_stock_price(actual_ticker)


def query_stock_price(ticker: str, ) -> str:
    """
    Query the stock price from market data sources.
    
    ⚠️ CHAOS: Corrupts price data 5% of the time!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price (might be corrupted!)
    """
    result = json.loads(_base_get_stock_price(ticker))
    
    # Subtle data corruption
    if random.random() < 0.05:  # 5% chance
        corruption_type = random.choice(['price', 'change', 'volume'])
        if corruption_type == 'price':
            result['price'] = result['price'] * random.uniform(0.5, 1.5)
            logging.warning(f"[CHAOS] query_stock_price corrupted price for {ticker}")
        elif corruption_type == 'change':
            result['change'] = result['change'] * -1  # Flip sign
            logging.warning(f"[CHAOS] query_stock_price corrupted change for {ticker}")
        else:
            result['volume'] = int(result['volume'] * 0.01)  # Wrong scale
            logging.warning(f"[CHAOS] query_stock_price corrupted volume for {ticker}")
    
    return json.dumps(result)


# =============================================================================
# CHAOS PATTERN 5: Inefficient but working tools
# =============================================================================

def get_multiple_stock_prices(tickers: str, ) -> str:
    """
    Get prices for multiple tickers at once.
    
    ⚠️ CHAOS: Works but adds 500ms delay per ticker!
    Agent might use this even for single ticker.
    
    Args:
        tickers: Comma-separated ticker symbols (e.g., "AAPL,MSFT,GOOGL")
        
    Returns:
        JSON string with array of stock prices
    """
    logging.info(f"[CHAOS] get_multiple_stock_prices called with: {tickers}")
    ticker_list = [t.strip() for t in tickers.split(',')]
    results = []
    
    for ticker in ticker_list:
        time.sleep(0.5)  # Adds latency per ticker
        try:
            data = json.loads(_base_get_stock_price(ticker))
            results.append(data)
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    
    return json.dumps({"stocks": results, "count": len(results)})


def get_stock_with_news(ticker: str, ) -> str:
    """
    Get stock price along with latest news.
    
    ⚠️ CHAOS: Makes two separate calls instead of using efficient approach!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with both price and news (inefficiently fetched)
    """
    logging.info(f"[CHAOS] get_stock_with_news called (inefficient)")
    
    # Inefficiently makes two separate calls
    price_data = json.loads(_base_get_stock_price(ticker))
    time.sleep(1)  # Artificial delay between calls
    news_data = json.loads(_base_get_market_news(ticker, limit=3))
    
    return json.dumps({
        "stock": price_data,
        "news": news_data,
        "warning": "This tool makes inefficient separate calls"
    })


# =============================================================================
# CHAOS PATTERN 6: API Schema Evolution (realistic API changes)
# =============================================================================

def get_stock_price_v2(ticker: str, ) -> str:
    """
    Get stock price using v2 API format.
    
    ⚠️ CHAOS: Returns "v2" API format - wraps response in extra metadata layer!
    Simulates API versioning where structure changes between versions.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with v2 wrapper structure
    """
    logging.info(f"[CHAOS] get_stock_price_v2 called (wrapped format)")
    result = json.loads(_base_get_stock_price(ticker))
    
    # V2 wraps everything in a "data" object with metadata
    v2_response = {
        "data": result,
        "api_version": "2.0",
        "timestamp": time.time(),
        "success": True,
        "meta": {
            "request_id": f"req_{random.randint(10000, 99999)}",
            "server": "api-v2.example.com"
        }
    }
    return json.dumps(v2_response)


def get_stock_price_unstable_schema(ticker: str, ) -> str:
    """
    Get stock price from API with unstable schema.
    
    ⚠️ CHAOS: Randomly switches between v1 and v2 schemas (30% chance of v2)!
    Simulates API that hasn't fully migrated - some calls return old format, some new.
    This is VERY realistic - happens during rolling deployments.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string in either v1 or v2 format (unpredictable!)
    """
    logging.info(f"[CHAOS] get_stock_price_unstable_schema called")
    result = json.loads(_base_get_stock_price(ticker))
    
    if random.random() < 0.3:  # 30% chance of v2 format
        # V2: Nested structure with extra metadata
        logging.warning(f"[CHAOS] Returning v2 schema for {ticker}")
        return json.dumps({
            "status": "success",
            "data": {
                "symbol": result.get("ticker"),
                "quote": {
                    "price": result.get("price"),
                    "change": result.get("change"),
                    "change_percent": result.get("change_percent")
                },
                "metrics": {
                    "volume": result.get("volume"),
                    "high": result.get("high"),
                    "low": result.get("low"),
                    "open": result.get("open")
                }
            },
            "version": "2.0"
        })
    else:
        # V1: Original flat structure
        logging.info(f"[CHAOS] Returning v1 schema for {ticker}")
        return json.dumps(result)


def get_stock_price_evolving(ticker: str, ) -> str:
    """
    Get stock price from evolving API.
    
    ⚠️ CHAOS: Randomly adds new undocumented fields (20% chance)!
    Simulates API evolution where new fields appear without warning.
    Can break parsers that don't handle unexpected fields gracefully.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with occasional surprise fields
    """
    logging.info(f"[CHAOS] get_stock_price_evolving called")
    result = json.loads(_base_get_stock_price(ticker))
    
    if random.random() < 0.2:  # 20% chance of new fields
        # Add "beta" fields that weren't in original API
        result["beta_features"] = {
            "sentiment_score": round(random.uniform(-1, 1), 2),
            "analyst_rating": random.choice(["buy", "hold", "sell"]),
            "risk_level": random.choice(["low", "medium", "high"]),
            "ai_prediction": round(result.get("price", 0) * random.uniform(0.95, 1.05), 2)
        }
        result["experimental"] = True
        result["feature_flags"] = ["sentiment", "ai_predict"]
        logging.warning(f"[CHAOS] Added undocumented beta fields to {ticker}")
    
    return json.dumps(result)


def get_stock_price_deprecated(ticker: str, ) -> str:
    """
    Get stock price from API that's deprecating fields.
    
    ⚠️ CHAOS: Randomly removes "deprecated" fields (15% chance)!
    Simulates API that's removing old fields - sometimes they're there, sometimes not.
    Super realistic for APIs in transition periods.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with randomly missing fields
    """
    logging.info(f"[CHAOS] get_stock_price_deprecated called")
    result = json.loads(_base_get_stock_price(ticker))
    
    if random.random() < 0.15:  # 15% chance of field removal
        # Remove fields that are "deprecated"
        deprecated_fields = ["open", "volume"]
        removed = []
        for field in deprecated_fields:
            if field in result:
                del result[field]
                removed.append(field)
        if removed:
            result["_deprecated_fields_removed"] = removed
            result["_migration_notice"] = "Some fields have been deprecated. See API v2 docs."
            logging.warning(f"[CHAOS] Removed deprecated fields {removed} from {ticker}")
    
    return json.dumps(result)


def get_stock_price_breaking_change(ticker: str, ) -> str:
    """
    Get stock price from API with breaking changes.
    
    ⚠️ CHAOS: Changes field types randomly (10% chance)!
    - Numbers become strings: 178.72 → "178.72"
    - Strings become numbers: "AAPL" → null (invalid)
    - Floats become integers: 178.72 → 178
    
    Simulates the nightmare scenario of breaking API changes.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string with type-changed fields
    """
    logging.info(f"[CHAOS] get_stock_price_breaking_change called")
    result = json.loads(_base_get_stock_price(ticker))
    
    if random.random() < 0.1:  # 10% chance of type changes
        breaking_change = random.choice(["numbers_to_strings", "truncate_floats", "rename_fields"])
        
        if breaking_change == "numbers_to_strings":
            # Convert numbers to strings
            for key in ["price", "change", "change_percent", "volume", "high", "low", "open"]:
                if key in result and isinstance(result[key], (int, float)):
                    result[key] = str(result[key])
            logging.warning(f"[CHAOS] Converted numbers to strings for {ticker}")
            
        elif breaking_change == "truncate_floats":
            # Truncate floats to integers (loses precision)
            for key in ["price", "change", "change_percent", "high", "low", "open"]:
                if key in result and isinstance(result[key], float):
                    result[key] = int(result[key])
            logging.warning(f"[CHAOS] Truncated floats to integers for {ticker}")
            
        elif breaking_change == "rename_fields":
            # Rename fields without notice (breaking change)
            renames = {
                "price": "current_price",
                "change": "price_change",
                "change_percent": "pct_change"
            }
            for old_key, new_key in renames.items():
                if old_key in result:
                    result[new_key] = result[old_key]
                    del result[old_key]
            logging.warning(f"[CHAOS] Renamed fields for {ticker}")
    
    return json.dumps(result)


# =============================================================================
# CHAOS PATTERN 7: Direct API access (bypasses wrappers)
# =============================================================================

def get_stock_price_yfinance_direct(ticker: str, ) -> str:
    """
    Get stock price directly from Yahoo Finance.
    
    ⚠️ CHAOS: Bypasses wrapper, no fallback if yfinance fails!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price
    """
    # Check if user wants live data (respects USE_LIVE_DATA toggle)
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    
    if not use_live_data:
        raise Exception("Live data disabled - enable USE_LIVE_DATA to use this tool")
    
    if not LIVE_DATA_AVAILABLE:
        raise ImportError("yfinance not available")
    
    logging.info(f"[CHAOS] get_stock_price_yfinance_direct called (no fallback)")
    
    try:
        return get_stock_price_yfinance(ticker)
    except Exception as e:
        raise Exception(f"yfinance API failed: {e}")


def get_stock_price_alpha_vantage_direct(ticker: str, ) -> str:
    """
    Get stock price directly from Alpha Vantage.
    
    ⚠️ CHAOS: Requires API key, no fallback if it fails!
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price
    """
    # Check if user wants live data (respects USE_LIVE_DATA toggle)
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    
    if not use_live_data:
        raise Exception("Live data disabled - enable USE_LIVE_DATA to use this tool")
    
    if not LIVE_DATA_AVAILABLE:
        raise ImportError("Alpha Vantage not available")
    
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise Exception("ALPHA_VANTAGE_API_KEY not set")
    
    logging.info(f"[CHAOS] get_stock_price_alpha_vantage_direct called (no fallback)")
    
    try:
        return get_stock_price_alpha_vantage(ticker, api_key)
    except Exception as e:
        raise Exception(f"Alpha Vantage API failed: {e}")


# =============================================================================
# Export chaos tools
# =============================================================================

# Import the non-stock-price tools from logic module
# These are needed for the agent to function (purchase, sell, news, account info)
# We only create chaos variations for get_stock_price to demonstrate confusion
import sys
import os
from pathlib import Path

# Get the parent directory to import from logic
parent_dir = str(Path(__file__).parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the other necessary tools from logic.py
# We'll add these at the end since we can't import them here (circular dependency)
# Instead, we'll let logic.py add them when it assembles CHAOS_TOOLS


# All the confusing alternatives (all still log to Galileo)
CHAOS_TOOLS = [
    # Pattern 1: No fallback / minimal data
    get_stock_price_fast,
    fetch_stock_price,
    
    # Pattern 2: Different formats
    lookup_stock_price,
    get_stock_data,
    
    # Pattern 3: Artificial latency
    get_current_stock_price,
    get_stock_price_accurate,
    
    # Pattern 4: Subtle bugs
    retrieve_stock_price,
    query_stock_price,
    
    # Pattern 5: Inefficient
    get_multiple_stock_prices,
    get_stock_with_news,
    
    # Pattern 6: API Schema Evolution (NEW!)
    get_stock_price_v2,
    get_stock_price_unstable_schema,
    get_stock_price_evolving,
    get_stock_price_deprecated,
    get_stock_price_breaking_change,
]

# Add direct API tools if available
if LIVE_DATA_AVAILABLE:
    # Pattern 7: Direct API access
    CHAOS_TOOLS.extend([
        get_stock_price_yfinance_direct,
        get_stock_price_alpha_vantage_direct,
    ])


def get_all_chaos_tools():
    """
    Get all chaos tools for export.
    
    Returns:
        List of chaos tool functions
    """
    return CHAOS_TOOLS


def get_chaos_tool_descriptions():
    """
    Get descriptions of what each chaos tool does wrong.
    
    Returns:
        Dictionary mapping tool names to their chaos patterns
    """
    return {
        "get_stock_price_fast": "Returns minimal data - loses metadata",
        "fetch_stock_price": "No fallback to mock data - fails easily",
        "lookup_stock_price": "Returns only price string - loses context",
        "get_stock_data": "Different JSON format - breaks parsing",
        "get_current_stock_price": "2-second artificial delay",
        "get_stock_price_accurate": "1-5 second random delay",
        "retrieve_stock_price": "10% chance returns wrong ticker",
        "query_stock_price": "5% chance corrupts data",
        "get_multiple_stock_prices": "500ms per ticker - inefficient",
        "get_stock_with_news": "Makes separate calls inefficiently",
        "get_stock_price_v2": "Wraps response in v2 metadata layer",
        "get_stock_price_unstable_schema": "30% chance returns different schema",
        "get_stock_price_evolving": "20% chance adds surprise fields",
        "get_stock_price_deprecated": "15% chance removes deprecated fields",
        "get_stock_price_breaking_change": "10% chance changes field types",
        "get_stock_price_yfinance_direct": "Direct API, no fallback",
        "get_stock_price_alpha_vantage_direct": "Requires API key, no fallback",
    }


# =============================================================================
# Integration helper
# =============================================================================

def should_use_chaos_tools():
    """Check if chaos tools should be enabled."""
    return os.getenv("USE_CHAOS_TOOLS", "false").lower() == "true"


def get_combined_tools():
    """
    Get base tools combined with chaos tools if enabled.
    
    Returns:
        List of tool functions (base + chaos if enabled)
    """
    from .logic import TOOLS as BASE_TOOLS
    
    if should_use_chaos_tools():
        logging.warning("⚠️  CHAOS MODE: Adding confusing tools for agent confusion testing")
        return BASE_TOOLS + CHAOS_TOOLS
    
    return BASE_TOOLS

