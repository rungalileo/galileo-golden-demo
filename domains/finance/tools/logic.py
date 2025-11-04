# note from yash that it wouldn't be bad to hook up to alphavantage like we do in other demo
"""
Finance domain tools implementation

Supports both mock data (for demos) and live data (via APIs):
- Set USE_LIVE_DATA=true to enable live stock prices
- Set USE_LIVE_DATA=false or leave unset for mock data

Also supports chaos engineering for testing:
- Simulates API failures, data corruption, hallucinations
"""
import json
import time
import os
import requests
import logging
import random
from typing import Optional
# GalileoLogger import removed - all logging handled by GalileoCallback
import streamlit as st


class APIError(Exception):
    """
    Custom exception for API errors with searchable metadata.
    
    The error message will include the status code and metadata in a format
    that Galileo can index and search.
    """
    def __init__(self, message: str, status_code: str = "500", error_type: str = "network_failure", **kwargs):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.metadata = kwargs
        self.metadata['status_code'] = status_code
        self.metadata['error_type'] = error_type
    
    def __str__(self):
        # Format: [STATUS_CODE] message | metadata as key=value
        metadata_str = " | ".join([f"{k}={v}" for k, v in self.metadata.items()])
        return f"[{self.status_code}] {super().__str__()} | {metadata_str}"

# Import chaos engine
try:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from chaos_engine import get_chaos_engine
    CHAOS_AVAILABLE = True
except ImportError as e:
    CHAOS_AVAILABLE = False
    logging.warning(f"Chaos engine not available: {e}")

# Try to import live data module (check if libraries are available)
# We don't cache USE_LIVE_DATA - it will be checked dynamically at runtime
try:
    # Try relative import first (when loaded as module)
    try:
        from .live_data import get_live_stock_price, get_live_market_news
    except ImportError:
        # Fall back to absolute import (when run directly)
        import sys
        from pathlib import Path
        # Add domains/finance/tools to path
        tools_dir = Path(__file__).parent
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        from live_data import get_live_stock_price, get_live_market_news
    
    LIVE_DATA_AVAILABLE = True
    logging.info("✓ Live data libraries available (yfinance/alpha-vantage)")
except ImportError as e:
    LIVE_DATA_AVAILABLE = False
    logging.info("✓ Live data libraries not installed - using mock data only")
    logging.info("   To enable live data: pip install yfinance alpha-vantage")

# Mock database for testing
MOCK_PRICE_DB = {
    "AVGO": {  # Broadcom
        "price": 184.72,
        "change": -2.68,
        "change_percent": -1.43,
        "volume": 502,
        "high": 186.34,
        "low": 184.52,
        "open": 186.24
    },
    "GPS": {  # Gap
        "price": 19.85,
        "change": 0.15,
        "change_percent": 0.76,
        "volume": 4567890,
        "high": 20.00,
        "low": 19.50,
        "open": 19.70
    },
    "AAPL": {  # Apple
        "price": 178.72,
        "change": 1.23,
        "change_percent": 0.69,
        "volume": 52345678,
        "high": 179.50,
        "low": 177.80,
        "open": 178.00
    },
    "MSFT": {  # Microsoft
        "price": 415.32,
        "change": 2.45,
        "change_percent": 0.59,
        "volume": 23456789,
        "high": 416.00,
        "low": 413.50,
        "open": 414.00
    },
    "GOOGL": {  # Google
        "price": 147.68,
        "change": -0.82,
        "change_percent": -0.55,
        "volume": 34567890,
        "high": 148.50,
        "low": 147.20,
        "open": 147.90
    },
    "AMZN": {  # Amazon
        "price": 178.75,
        "change": 1.25,
        "change_percent": 0.70,
        "volume": 45678901,
        "high": 179.00,
        "low": 177.50,
        "open": 178.00
    },
    "META": {  # Meta
        "price": 485.58,
        "change": 3.42,
        "change_percent": 0.71,
        "volume": 56789012,
        "high": 486.00,
        "low": 482.00,
        "open": 483.00
    },
    "TSLA": {  # Tesla
        "price": 177.77,
        "change": -2.33,
        "change_percent": -1.29,
        "volume": 67890123,
        "high": 180.00,
        "low": 177.00,
        "open": 179.00
    },
    "NVDA": {  # NVIDIA
        "price": 950.02,
        "change": 15.98,
        "change_percent": 1.71,
        "volume": 78901234,
        "high": 952.00,
        "low": 945.00,
        "open": 946.00
    }
}

def _extract_status_code(error_msg: str) -> str:
    """
    Extract HTTP status code from error message.
    
    Args:
        error_msg: Error message that may contain a status code
        
    Returns:
        Status code as string (defaults to "500" if not found)
    """
    # Check for specific status codes in order of specificity
    status_codes = ["503", "502", "504", "500", "401", "403", "404", "405", "429"]
    for code in status_codes:
        if code in error_msg:
            return code
    
    # Check for error types
    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        return "timeout"
    elif "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
        return "ssl_error"
    elif "dns" in error_msg.lower():
        return "dns_error"
    elif "malformed" in error_msg.lower() or "invalid" in error_msg.lower():
        return "invalid_response"
    
    return "500"  # Default to internal server error


def _add_success_metadata(result: dict, ticker: str, data_source: str = "mock") -> dict:
    """
    Add success metadata to result for Galileo visibility.
    
    Args:
        result: The stock price data
        ticker: The ticker symbol
        data_source: Source of data (live, mock, etc.)
        
    Returns:
        Enhanced result with metadata
    """
    # Add metadata that will be visible in Galileo traces
    result_with_metadata = {
        **result,
        "_metadata": {
            "status_code": "200",
            "success": True,
            "ticker": ticker,
            "data_source": data_source
        }
    }
    return result_with_metadata

def get_stock_price(ticker: str) -> str:
    """
    Get the current stock price and other market data for a given ticker symbol.
    Uses live data if USE_LIVE_DATA=true, otherwise uses mock database.
    
    Args:
        ticker: The ticker symbol to look up
        
    Returns:
        JSON string containing the stock price and market data
    """
    start_time = time.time()
    
    # Chaos: Check for API failure injection
    if CHAOS_AVAILABLE:
        chaos = get_chaos_engine()
        should_fail, error_msg = chaos.should_fail_api_call("Stock Price API")
        if should_fail:
            # Extract status code and raise structured exception
            status_code = _extract_status_code(error_msg)
            raise APIError(
                error_msg,
                status_code=status_code,
                error_type="network_failure",
                ticker=ticker,
                chaos_injected=True
            )
        
        # Chaos: Check for rate limit
        should_rate_limit, error_msg = chaos.should_fail_rate_limit("Stock Price API")
        if should_rate_limit:
            raise APIError(
                error_msg,
                status_code="429",
                error_type="rate_limit",
                ticker=ticker,
                chaos_injected=True
            )
        
        # Chaos: Inject latency
        delay = chaos.inject_latency()
        if delay > 0:
            time.sleep(delay)
    
    # Try live data first if enabled (check dynamically to respect UI toggle)
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    
    if use_live_data and LIVE_DATA_AVAILABLE:
        try:
            logging.info(f"Fetching live data for {ticker}")
            result_json = get_live_stock_price(ticker)
            result_dict = json.loads(result_json)
            
            # Chaos: Maybe corrupt the data
            if CHAOS_AVAILABLE:
                chaos = get_chaos_engine()
                result_dict = chaos.corrupt_data(result_dict)
            
            # Add success metadata
            result_dict = _add_success_metadata(result_dict, ticker, "live")
            return json.dumps(result_dict)
        except Exception as e:
            logging.warning(f"Live data failed, falling back to mock: {e}")
            # Fall through to mock data
    
    # Use mock database
    try:
        if ticker in MOCK_PRICE_DB:
            logging.info(f"Found {ticker} in mock database")
            result = MOCK_PRICE_DB[ticker]
            result = _add_success_metadata(result, ticker, "mock")
            return json.dumps(result)
            
        # If not found, return a default mock price
        logging.info(f"Ticker {ticker} not found, using default mock price")
        result = {
            "price": 100.00,
            "change": 0.00,
            "change_percent": 0.00,
            "volume": 1000,
            "high": 101.00,
            "low": 99.00,
            "open": 100.00
        }
        result = _add_success_metadata(result, ticker, "mock_default")
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error getting stock price: {str(e)}")
        
        # On any error, try the mock database
        if ticker in MOCK_PRICE_DB:
            logging.info(f"Found {ticker} in mock database after error")
            result = MOCK_PRICE_DB[ticker]
            result = _add_success_metadata(result, ticker, "mock")
            return json.dumps(result)
            
        # If not found in mock database, return a default mock price
        logging.info(f"Ticker {ticker} not found in mock database, using default mock price")
        result = {
            "price": 100.00,
            "change": 0.00,
            "change_percent": 0.00,
            "volume": 1000,
            "high": 101.00,
            "low": 99.00,
            "open": 100.00
        }
        result = _add_success_metadata(result, ticker, "mock_default")
        return json.dumps(result)


def purchase_stocks(ticker: str, quantity: int, price: float) -> str:
    """
    Simulate purchasing stocks with a given ticker symbol, quantity, and price.
    
    Args:
        ticker: The ticker symbol to purchase
        quantity: The number of shares to purchase
        price: The price per share
        
    Returns:
        JSON string containing the order confirmation
    """
    start_time = time.time()
    try:
        # Generate a random order ID
        order_id = f"ORD-{random.randint(100000, 999999)}"
        
        # Calculate total cost including fees
        total_cost = quantity * price
        fees = 10.00  # Fixed fee for simplicity
        total_with_fees = total_cost + fees
        
        # Create order confirmation
        result = {
            "order_id": order_id,
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "total_cost": total_cost,
            "fees": fees,
            "total_with_fees": total_with_fees,
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Purchase of stocks completed successfully",
            "_metadata": {
                "status_code": "201",  # 201 Created for successful purchase
                "success": True,
                "operation": "purchase"
            }
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error purchasing stocks: {str(e)}")
        raise


def sell_stocks(ticker: str, quantity: int, price: float) -> str:
    """
    Simulate selling stocks with a given ticker symbol, quantity, and price.
    
    Args:
        ticker: The ticker symbol to sell
        quantity: The number of shares to sell
        price: The price per share
        
    Returns:
        JSON string containing the order confirmation
    """
    start_time = time.time()
    try:
        # Generate a random order ID
        order_id = f"ORD-{random.randint(100000, 999999)}"
        
        # Calculate total cost including fees
        total_sale = quantity * price
        fees = 14.99  # Fixed fee for simplicity
        total_with_fees = total_sale - fees
        
        # Create order confirmation
        result = {
            "order_id": order_id,
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "total_sale": total_sale,
            "fees": fees,
            "total_with_fees": total_with_fees,
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Sale of stocks completed successfully",
            "_metadata": {
                "status_code": "201",  # 201 Created for successful sale
                "success": True,
                "operation": "sell"
            }
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error selling stocks: {str(e)}")
        raise


def get_market_news(ticker: Optional[str] = None, limit: int = 5) -> str:
    """
    Get the latest market news for a specific stock or general market news.
    Uses live news APIs if enabled, otherwise returns a message.
    
    Args:
        ticker: Optional stock ticker to get news for (e.g., 'AAPL', 'TSLA')
        limit: Number of news articles to return (default: 5)
        
    Returns:
        JSON string containing news articles with titles, summaries, and sentiment
    """
    start_time = time.time()
    
    # Try live news if enabled (check dynamically to respect UI toggle)
    use_live_data = os.getenv("USE_LIVE_DATA", "false").lower() == "true"
    
    if use_live_data and LIVE_DATA_AVAILABLE:
        try:
            logging.info(f"Fetching live news for {ticker or 'market'}")
            return get_live_market_news(ticker, limit)
        except Exception as e:
            logging.warning(f"Live news failed: {e}")
            # Fall through to mock response
    
    # Mock news response
    result = {
        "articles": [
            {
                "title": "Market Update: Tech Stocks Rally",
                "summary": "Technology stocks showed strong gains today with major tech companies leading the market higher.",
                "source": "Mock News",
                "published": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sentiment": "positive"
            }
        ],
        "count": 1,
        "source": "Mock News (Enable live data for real news)",
        "note": "This is mock data. Enable USE_LIVE_DATA=true and configure ALPHA_VANTAGE_API_KEY or NEWSAPI_KEY for real news.",
        "_metadata": {
            "status_code": "200",
            "success": True,
            "data_source": "mock"
        }
    }
    
    return json.dumps(result)


def get_account_information() -> str:
    """
    Get brokerage account information and portfolio holdings.
    
    ⚠️ GUARDRAIL TEST: This returns PII that should be caught by guardrails!
    
    Returns:
        JSON string containing account information
    """
    try:
        # Import fake database
        import sys
        from pathlib import Path
        finance_dir = Path(__file__).parent.parent
        if str(finance_dir) not in sys.path:
            sys.path.insert(0, str(finance_dir))
        from fake_database import get_account_info, format_account_info
        
        # Get account info WITH PII (will trigger guardrails!)
        info = get_account_info("default")
        
        # Return formatted with PII - this should trigger output guardrails
        result = format_account_info(info, include_pii=True)
        
        return result
        
    except Exception as e:
        error_msg = f"Error retrieving account information: {str(e)}"
        logging.error(error_msg)
        
        return json.dumps({"error": error_msg})


# Export tools for easy loading by frameworks
BASE_TOOLS = [
    get_stock_price,
    get_market_news,
    get_account_information,
    purchase_stocks,
    sell_stocks
]

# Helper function to get chaos tools (lazy import to avoid circular dependency)
def _get_chaos_tools():
    """Lazy import of chaos tools to avoid circular dependency at module load time."""
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    import chaos_tools
    return chaos_tools.CHAOS_TOOLS


# Optionally REPLACE with chaos tools for demonstrating observability value
use_chaos = os.getenv("USE_CHAOS_TOOLS", "false").lower() == "true"
logging.info(f"🔍 USE_CHAOS_TOOLS environment variable: {os.getenv('USE_CHAOS_TOOLS', 'not set')} -> {use_chaos}")

if use_chaos:
    try:
        # Lazy import to avoid circular dependency
        CHAOS_TOOLS = _get_chaos_tools()
        logging.warning("🔥 CHAOS MODE ENABLED: Replacing standard tools with confusing alternatives!")
        logging.warning("⚠️  Base get_stock_price tool is now OFF-LIMITS")
        
        # Combine chaos stock price tools with the other necessary tools
        # The agent needs purchase, sell, news, and account info to function
        # But we provide 17 confusing options for stock price lookups
        TOOLS = CHAOS_TOOLS + [
            get_market_news,
            get_account_information,
            purchase_stocks,
            sell_stocks
        ]
        logging.info(f"🔧 {len(TOOLS)} total tools: {len(CHAOS_TOOLS)} chaos stock price tools + 4 standard tools")
        logging.info(f"📋 Chaos tool names: {[t.__name__ for t in CHAOS_TOOLS[:5]]}...")
        logging.info(f"📋 Standard tool names: get_market_news, get_account_information, purchase_stocks, sell_stocks")
    except ImportError as e:
        TOOLS = BASE_TOOLS  # Fallback to base tools if chaos_tools not available
        logging.warning(f"⚠️  Failed to import chaos_tools: {e}")
        logging.info(f"✅ {len(TOOLS)} standard tools available (using fallback)")
else:
    TOOLS = BASE_TOOLS
    logging.info(f"✅ {len(TOOLS)} standard tools available")
    logging.info(f"📋 Standard tool names: {[t.__name__ for t in TOOLS]}")
