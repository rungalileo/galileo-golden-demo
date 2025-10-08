"""
Live stock data and news integration using real APIs

Supports multiple data sources:
1. Yahoo Finance (yfinance) - Free, no API key needed
2. Alpha Vantage - Free tier with API key
3. Finnhub - Free tier with API key (optional)
"""
import os
import json
import time
import logging
from typing import Optional, Dict, Any
from galileo import GalileoLogger

# Import libraries (will work if installed)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not installed. Run: pip install yfinance")

try:
    from alpha_vantage.timeseries import TimeSeries
    from alpha_vantage.sectorperformance import SectorPerformances
    ALPHA_VANTAGE_AVAILABLE = True
except ImportError:
    ALPHA_VANTAGE_AVAILABLE = False
    logging.warning("alpha-vantage not installed. Run: pip install alpha-vantage")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# =============================================================================
# YAHOO FINANCE (yfinance) - Free, No API Key
# =============================================================================

def get_stock_price_yfinance(ticker: str) -> Dict[str, Any]:
    """
    Get real-time stock data from Yahoo Finance using yfinance
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary with stock data
    """
    if not YFINANCE_AVAILABLE:
        raise ImportError("yfinance not installed")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get current price and daily data
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        previous_close = info.get('previousClose', current_price)
        
        # Calculate change
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close else 0
        
        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": info.get('volume', 0),
            "high": info.get('dayHigh', 0),
            "low": info.get('dayLow', 0),
            "open": info.get('open', 0),
            "market_cap": info.get('marketCap', 0),
            "pe_ratio": info.get('trailingPE', 0),
            "company_name": info.get('shortName', ticker),
            "currency": info.get('currency', 'USD'),
            "source": "Yahoo Finance (yfinance)"
        }
    except Exception as e:
        logging.error(f"Error fetching from yfinance: {e}")
        raise


# =============================================================================
# ALPHA VANTAGE - Free Tier with API Key
# =============================================================================

def get_stock_price_alpha_vantage(ticker: str, api_key: str) -> Dict[str, Any]:
    """
    Get stock data from Alpha Vantage
    
    Args:
        ticker: Stock ticker symbol
        api_key: Alpha Vantage API key
        
    Returns:
        Dictionary with stock data
    """
    if not ALPHA_VANTAGE_AVAILABLE:
        raise ImportError("alpha-vantage not installed")
    
    try:
        ts = TimeSeries(key=api_key, output_format='json')
        data, meta_data = ts.get_quote_endpoint(symbol=ticker)
        
        current_price = float(data['05. price'])
        previous_close = float(data['08. previous close'])
        change = float(data['09. change'])
        change_percent = float(data['10. change percent'].rstrip('%'))
        
        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": int(data['06. volume']),
            "high": float(data['03. high']),
            "low": float(data['04. low']),
            "open": float(data['02. open']),
            "source": "Alpha Vantage"
        }
    except Exception as e:
        logging.error(f"Error fetching from Alpha Vantage: {e}")
        raise


def get_market_news_alpha_vantage(api_key: str, tickers: Optional[str] = None, 
                                    topics: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Get market news from Alpha Vantage News API
    
    Args:
        api_key: Alpha Vantage API key
        tickers: Optional comma-separated ticker symbols (e.g., "AAPL,TSLA")
        topics: Optional topics (e.g., "technology", "finance")
        limit: Number of articles to return
        
    Returns:
        Dictionary with news articles
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not installed")
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": api_key,
            "limit": limit
        }
        
        if tickers:
            params["tickers"] = tickers
        if topics:
            params["topics"] = topics
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get('feed', [])[:limit]:
            articles.append({
                "title": item.get('title', ''),
                "summary": item.get('summary', ''),
                "url": item.get('url', ''),
                "source": item.get('source', ''),
                "published": item.get('time_published', ''),
                "sentiment": item.get('overall_sentiment_label', 'neutral'),
                "sentiment_score": item.get('overall_sentiment_score', 0),
                "tickers": [t['ticker'] for t in item.get('ticker_sentiment', [])]
            })
        
        return {
            "articles": articles,
            "count": len(articles),
            "source": "Alpha Vantage News"
        }
    except Exception as e:
        logging.error(f"Error fetching news from Alpha Vantage: {e}")
        raise


# =============================================================================
# NEWS API - General and Financial News
# =============================================================================

def get_market_news_newsapi(api_key: str, query: str = "stock market", limit: int = 5) -> Dict[str, Any]:
    """
    Get financial news from NewsAPI
    
    Args:
        api_key: NewsAPI key
        query: Search query
        limit: Number of articles
        
    Returns:
        Dictionary with news articles
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library not installed")
    
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": limit
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get('articles', []):
            articles.append({
                "title": item.get('title', ''),
                "description": item.get('description', ''),
                "url": item.get('url', ''),
                "source": item.get('source', {}).get('name', ''),
                "published": item.get('publishedAt', ''),
                "author": item.get('author', ''),
            })
        
        return {
            "articles": articles,
            "count": len(articles),
            "source": "NewsAPI"
        }
    except Exception as e:
        logging.error(f"Error fetching news from NewsAPI: {e}")
        raise


# =============================================================================
# Unified Interface with Fallback
# =============================================================================

def get_live_stock_price(ticker: str, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Get live stock price with automatic fallback or specific source
    
    Respects STOCK_DATA_SOURCE environment variable:
    - "auto" (default): Try all sources in order
    - "yfinance": Use Yahoo Finance only
    - "alpha_vantage": Use Alpha Vantage only
    - "finnhub": Use Finnhub only (if implemented)
    
    Args:
        ticker: Stock ticker symbol
        galileo_logger: Galileo logger for observability
        
    Returns:
        JSON string with stock data
    """
    start_time = time.time()
    errors = []
    
    # Get preferred source from environment
    preferred_source = os.getenv("STOCK_DATA_SOURCE", "auto").lower()
    
    # Helper function to try a specific source
    def try_yfinance():
        if not YFINANCE_AVAILABLE:
            return None, "yfinance not installed"
        try:
            logging.info(f"Fetching {ticker} from Yahoo Finance...")
            result = get_stock_price_yfinance(ticker)
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"ticker": ticker}),
                    output=json.dumps(result),
                    name="Get Stock Price (Yahoo Finance)",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    metadata={
                        "ticker": ticker,
                        "price": str(result["price"]),
                        "source": "yfinance"
                    },
                    tags=["stocks", "price", "live", "yfinance"]
                )
            return json.dumps(result), None
        except Exception as e:
            return None, f"Yahoo Finance: {str(e)}"
    
    def try_alpha_vantage():
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_vantage_key:
            return None, "Alpha Vantage API key not set"
        if not ALPHA_VANTAGE_AVAILABLE:
            return None, "alpha-vantage not installed"
        try:
            logging.info(f"Fetching {ticker} from Alpha Vantage...")
            result = get_stock_price_alpha_vantage(ticker, alpha_vantage_key)
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"ticker": ticker}),
                    output=json.dumps(result),
                    name="Get Stock Price (Alpha Vantage)",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    metadata={
                        "ticker": ticker,
                        "price": str(result["price"]),
                        "source": "alpha_vantage"
                    },
                    tags=["stocks", "price", "live", "alpha_vantage"]
                )
            return json.dumps(result), None
        except Exception as e:
            return None, f"Alpha Vantage: {str(e)}"
    
    # If specific source requested, try only that one
    if preferred_source == "yfinance":
        result, error = try_yfinance()
        if result:
            return result
        errors.append(error)
        
    elif preferred_source == "alpha_vantage":
        result, error = try_alpha_vantage()
        if result:
            return result
        errors.append(error)
        
    # Auto mode: try all sources in order
    elif preferred_source == "auto":
        # Try Yahoo Finance first
        result, error = try_yfinance()
        if result:
            return result
        if error:
            errors.append(error)
            logging.warning(error)
        
        # Try Alpha Vantage
        result, error = try_alpha_vantage()
        if result:
            return result
        if error:
            errors.append(error)
            logging.warning(error)
    
    # If all sources failed, raise error with details
    error_msg = f"Failed to get live data for {ticker}. Source: {preferred_source}. Errors: {'; '.join(errors)}"
    logging.error(error_msg)
    raise Exception(error_msg)


def get_live_market_news(ticker: Optional[str] = None, limit: int = 5, 
                          galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Get live market news with automatic fallback
    
    Args:
        ticker: Optional ticker to get news for
        limit: Number of articles
        galileo_logger: Galileo logger
        
    Returns:
        JSON string with news articles
    """
    start_time = time.time()
    
    # Try Alpha Vantage News first
    alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_key:
        try:
            logging.info("Fetching news from Alpha Vantage...")
            result = get_market_news_alpha_vantage(alpha_vantage_key, tickers=ticker, limit=limit)
            
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"ticker": ticker, "limit": limit}),
                    output=json.dumps(result),
                    name="Get Market News",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    tags=["news", "market", "alpha_vantage"]
                )
            
            return json.dumps(result)
        except Exception as e:
            logging.warning(f"Alpha Vantage News failed: {e}")
    
    # Try NewsAPI as fallback
    newsapi_key = os.getenv("NEWSAPI_KEY")
    if newsapi_key:
        try:
            query = f"{ticker} stock" if ticker else "stock market"
            logging.info(f"Fetching news from NewsAPI with query: {query}")
            result = get_market_news_newsapi(newsapi_key, query=query, limit=limit)
            
            if galileo_logger:
                galileo_logger.add_tool_span(
                    input=json.dumps({"query": query, "limit": limit}),
                    output=json.dumps(result),
                    name="Get Market News",
                    duration_ns=int((time.time() - start_time) * 1000000),
                    tags=["news", "market", "newsapi"]
                )
            
            return json.dumps(result)
        except Exception as e:
            logging.warning(f"NewsAPI failed: {e}")
    
    raise Exception("No news API keys configured. Set ALPHA_VANTAGE_API_KEY or NEWSAPI_KEY")

