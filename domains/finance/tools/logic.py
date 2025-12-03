"""
Finance domain tools implementation with live data integration

Supports multiple data sources with automatic fallback:
1. Yahoo Finance (yfinance) - Free, no API key needed
2. Alpha Vantage - Free tier with API key  
3. Mock data - Fallback when live APIs fail
"""
import json
import time
import os
import logging
import random
from typing import Optional, Dict, Any, Tuple
from galileo import GalileoLogger
import streamlit as st

# =============================================================================
# Live Data Library Imports (graceful handling if not installed)
# =============================================================================

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.debug("yfinance not installed - will use mock data for stock prices")

try:
    from alpha_vantage.timeseries import TimeSeries
    ALPHA_VANTAGE_AVAILABLE = True
except ImportError:
    ALPHA_VANTAGE_AVAILABLE = False
    logging.debug("alpha-vantage not installed - Alpha Vantage source unavailable")


# =============================================================================
# Mock Database (Fallback Data)
# =============================================================================

MOCK_PRICE_DB = {
    "AVGO": {  # Broadcom
        "price": 184.72,
        "change": -2.68,
        "change_percent": -1.43,
        "volume": 502,
        "high": 186.34,
        "low": 184.52,
        "open": 186.24,
        "company_name": "Broadcom Inc.",
        "currency": "USD"
    },
    "GPS": {  # Gap
        "price": 19.85,
        "change": 0.15,
        "change_percent": 0.76,
        "volume": 4567890,
        "high": 20.00,
        "low": 19.50,
        "open": 19.70,
        "company_name": "Gap Inc.",
        "currency": "USD"
    },
    "AAPL": {  # Apple
        "price": 178.72,
        "change": 1.23,
        "change_percent": 0.69,
        "volume": 52345678,
        "high": 179.50,
        "low": 177.80,
        "open": 178.00,
        "company_name": "Apple Inc.",
        "currency": "USD"
    },
    "MSFT": {  # Microsoft
        "price": 415.32,
        "change": 2.45,
        "change_percent": 0.59,
        "volume": 23456789,
        "high": 416.00,
        "low": 413.50,
        "open": 414.00,
        "company_name": "Microsoft Corporation",
        "currency": "USD"
    },
    "GOOGL": {  # Google
        "price": 147.68,
        "change": -0.82,
        "change_percent": -0.55,
        "volume": 34567890,
        "high": 148.50,
        "low": 147.20,
        "open": 147.90,
        "company_name": "Alphabet Inc.",
        "currency": "USD"
    },
    "AMZN": {  # Amazon
        "price": 178.75,
        "change": 1.25,
        "change_percent": 0.70,
        "volume": 45678901,
        "high": 179.00,
        "low": 177.50,
        "open": 178.00,
        "company_name": "Amazon.com Inc.",
        "currency": "USD"
    },
    "META": {  # Meta
        "price": 485.58,
        "change": 3.42,
        "change_percent": 0.71,
        "volume": 56789012,
        "high": 486.00,
        "low": 482.00,
        "open": 483.00,
        "company_name": "Meta Platforms Inc.",
        "currency": "USD"
    },
    "TSLA": {  # Tesla
        "price": 177.77,
        "change": -2.33,
        "change_percent": -1.29,
        "volume": 67890123,
        "high": 180.00,
        "low": 177.00,
        "open": 179.00,
        "company_name": "Tesla Inc.",
        "currency": "USD"
    },
    "NVDA": {  # NVIDIA
        "price": 950.02,
        "change": 15.98,
        "change_percent": 1.71,
        "volume": 78901234,
        "high": 952.00,
        "low": 945.00,
        "open": 946.00,
        "company_name": "NVIDIA Corporation",
        "currency": "USD"
    }
}


# =============================================================================
# Live Data Sources
# =============================================================================

def _get_stock_price_yfinance(ticker: str) -> Dict[str, Any]:
    """
    Get real-time stock data from Yahoo Finance using yfinance.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary with stock data
    """
    if not YFINANCE_AVAILABLE:
        raise ImportError("yfinance not installed")
    
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Get current price and daily data
    current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
    previous_close = info.get('previousClose', current_price)
    
    if not current_price:
        raise ValueError(f"No price data available for {ticker}")
    
    # Calculate change
    change = current_price - previous_close
    change_percent = (change / previous_close * 100) if previous_close else 0
    
    return {
        "ticker": ticker.upper(),
        "price": round(current_price, 2),
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
        "volume": info.get('volume', 0),
        "high": round(info.get('dayHigh', 0) or 0, 2),
        "low": round(info.get('dayLow', 0) or 0, 2),
        "open": round(info.get('open', 0) or 0, 2),
        "market_cap": info.get('marketCap', 0),
        "pe_ratio": round(info.get('trailingPE', 0) or 0, 2),
        "company_name": info.get('shortName', ticker),
        "currency": info.get('currency', 'USD'),
        "source": "Yahoo Finance (live)"
    }


def _get_stock_price_alpha_vantage(ticker: str, api_key: str) -> Dict[str, Any]:
    """
    Get stock data from Alpha Vantage.
    
    Args:
        ticker: Stock ticker symbol
        api_key: Alpha Vantage API key
        
    Returns:
        Dictionary with stock data
    """
    if not ALPHA_VANTAGE_AVAILABLE:
        raise ImportError("alpha-vantage not installed")
    
    ts = TimeSeries(key=api_key, output_format='json')
    data, meta_data = ts.get_quote_endpoint(symbol=ticker)
    
    current_price = float(data['05. price'])
    previous_close = float(data['08. previous close'])
    change = float(data['09. change'])
    change_percent = float(data['10. change percent'].rstrip('%'))
    
    return {
        "ticker": ticker.upper(),
        "price": round(current_price, 2),
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
        "volume": int(data['06. volume']),
        "high": round(float(data['03. high']), 2),
        "low": round(float(data['04. low']), 2),
        "open": round(float(data['02. open']), 2),
        "currency": "USD",
        "source": "Alpha Vantage (live)"
    }


def _get_mock_stock_price(ticker: str) -> Dict[str, Any]:
    """
    Get stock price from mock database.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with mock stock data
    """
    ticker_upper = ticker.upper()
    
    if ticker_upper in MOCK_PRICE_DB:
        result = MOCK_PRICE_DB[ticker_upper].copy()
        result["ticker"] = ticker_upper
        result["source"] = "Mock Data"
        return result
    
    # Generate reasonable mock data for unknown tickers
    return {
        "ticker": ticker_upper,
        "price": 100.00,
        "change": round(random.uniform(-3, 3), 2),
        "change_percent": round(random.uniform(-2, 2), 2),
        "volume": random.randint(100000, 10000000),
        "high": 102.00,
        "low": 98.00,
        "open": 100.00,
        "company_name": ticker_upper,
        "currency": "USD",
        "source": "Mock Data (ticker not in database)"
    }


# =============================================================================
# API Key Helper
# =============================================================================

def _get_alpha_vantage_key() -> Optional[str]:
    """Get Alpha Vantage API key from environment or Streamlit secrets."""
    # Try environment variable first
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if key:
        return key
    
    # Try Streamlit secrets
    try:
        key = st.secrets.get("alpha_vantage_api_key")
        if key:
            return key
    except Exception:
        pass
    
    return None


# =============================================================================
# Galileo Logging Helpers
# =============================================================================

def _log_to_galileo(galileo_logger: GalileoLogger, ticker: str, result: dict, 
                    start_time: float, source: str = "unknown") -> None:
    """
    Helper function to log stock price lookup to Galileo.
    """
    galileo_logger.add_tool_span(
        input=json.dumps({"ticker": ticker}),
        output=json.dumps(result),
        name="Get Stock Price",
        duration_ns=int((time.time() - start_time) * 1_000_000),
        metadata={
            "ticker": ticker,
            "price": str(result.get("price", "N/A")),
            "source": source,
            "found": "true"
        },
        tags=["stocks", "price", "lookup", source.replace(" ", "_").lower()]
    )


def _log_purchase_to_galileo(galileo_logger: GalileoLogger, ticker: str, quantity: int, 
                             price: float, order_id: str, start_time: float) -> None:
    """
    Helper function to log stock purchase to Galileo.
    """
    galileo_logger.add_tool_span(
        input=json.dumps({
            "ticker": ticker,
            "quantity": quantity,
            "price": price
        }),
        output=json.dumps({
            "order_id": order_id,
            "total_cost": quantity * price,
            "fees": 10.00
        }),
        name="Purchase Stocks",
        duration_ns=int((time.time() - start_time) * 1_000_000),
        metadata={
            "ticker": ticker,
            "quantity": str(quantity),
            "price": str(price),
            "order_id": order_id
        },
        tags=["stocks", "purchase", "trade"]
    )


def _log_sale_to_galileo(galileo_logger: GalileoLogger, ticker: str, quantity: int, 
                         price: float, order_id: str, start_time: float) -> None:
    """
    Helper function to log stock sale to Galileo.
    """
    galileo_logger.add_tool_span(
        input=json.dumps({
            "ticker": ticker,
            "quantity": quantity,
            "price": price
        }),
        output=json.dumps({
            "order_id": order_id,
            "total_sale": quantity * price,
            "fees": 14.99
        }),
        name="Sell Stocks",
        duration_ns=int((time.time() - start_time) * 1_000_000),
        metadata={
            "ticker": ticker,
            "quantity": str(quantity),
            "sale": str(price),
            "order_id": order_id
        },
        tags=["stocks", "sale", "trade"]
    )


# =============================================================================
# Public Tool Functions
# =============================================================================

def get_stock_price(ticker: str, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Get the current stock price and market data for a given ticker symbol.
    
    Automatically tries live data sources in order:
    1. Yahoo Finance (free, no API key)
    2. Alpha Vantage (if API key configured)
    3. Mock data (fallback)
    
    Args:
        ticker: The stock ticker symbol to look up (e.g., "AAPL", "TSLA")
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing the stock price and market data
    """
    start_time = time.time()
    ticker = ticker.upper().strip()
    
    result = None
    source_used = "mock"
    
    # Try Yahoo Finance first (free, no API key needed)
    if YFINANCE_AVAILABLE:
        try:
            logging.info(f"Fetching {ticker} from Yahoo Finance...")
            result = _get_stock_price_yfinance(ticker)
            source_used = "yfinance"
        except Exception as e:
            logging.debug(f"Yahoo Finance failed for {ticker}: {e}")
    
    # Try Alpha Vantage if yfinance failed
    if result is None:
        api_key = _get_alpha_vantage_key()
        if api_key and ALPHA_VANTAGE_AVAILABLE:
            try:
                logging.info(f"Fetching {ticker} from Alpha Vantage...")
                result = _get_stock_price_alpha_vantage(ticker, api_key)
                source_used = "alpha_vantage"
            except Exception as e:
                logging.debug(f"Alpha Vantage failed for {ticker}: {e}")
    
    # Fall back to mock data
    if result is None:
        logging.info(f"Using mock data for {ticker}")
        result = _get_mock_stock_price(ticker)
        source_used = "mock"
    
    # Log to Galileo if logger provided
    if galileo_logger:
        _log_to_galileo(galileo_logger, ticker, result, start_time, source_used)
    
    return json.dumps(result)


def purchase_stocks(ticker: str, quantity: int, price: float, 
                    galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Execute a stock purchase order (simulated).
    
    Args:
        ticker: The stock ticker symbol to purchase
        quantity: The number of shares to purchase
        price: The price per share
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing the order confirmation
    """
    start_time = time.time()
    ticker = ticker.upper().strip()
    
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
            "total_cost": round(total_cost, 2),
            "fees": fees,
            "total_with_fees": round(total_with_fees, 2),
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Successfully purchased {quantity} shares of {ticker} at ${price:.2f} per share"
        }
        
        if galileo_logger:
            _log_purchase_to_galileo(galileo_logger, ticker, quantity, price, order_id, start_time)
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error purchasing stocks: {str(e)}")
        raise


def sell_stocks(ticker: str, quantity: int, price: float, 
                galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Execute a stock sale order (simulated).
    
    Args:
        ticker: The stock ticker symbol to sell
        quantity: The number of shares to sell
        price: The price per share
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing the order confirmation
    """
    start_time = time.time()
    ticker = ticker.upper().strip()
    
    try:
        # Generate a random order ID
        order_id = f"ORD-{random.randint(100000, 999999)}"
        
        # Calculate total proceeds minus fees
        total_sale = quantity * price
        fees = 14.99  # Fixed fee for simplicity
        total_with_fees = total_sale - fees
        
        # Create order confirmation
        result = {
            "order_id": order_id,
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "total_sale": round(total_sale, 2),
            "fees": fees,
            "total_with_fees": round(total_with_fees, 2),
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Successfully sold {quantity} shares of {ticker} at ${price:.2f} per share"
        }
        
        if galileo_logger:
            _log_sale_to_galileo(galileo_logger, ticker, quantity, price, order_id, start_time)
        
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error selling stocks: {str(e)}")
        raise


# =============================================================================
# Tool Exports
# =============================================================================

TOOLS = [
    get_stock_price,
    purchase_stocks,
    sell_stocks
]
