# note from yash that it wouldn't be bad to hook up to alphavantage like we do in other demo
"""
Finance domain tools implementation
"""
import json
import time
import os
import requests
import logging
import random
from typing import Optional
from galileo import GalileoLogger
import streamlit as st

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

def _log_to_galileo(galileo_logger: GalileoLogger, ticker: str, result: dict, start_time: float) -> None:
    """
    Helper function to log stock price lookup to Galileo.
    
    Args:
        galileo_logger: Galileo logger for observability
        ticker: The ticker symbol that was looked up
        result: The price data found
        start_time: The start time of the lookup operation
    """
    galileo_logger.add_tool_span(
        input=json.dumps({"ticker": ticker}),
        output=json.dumps(result),
        name="Get Stock Price",
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata={
            "ticker": ticker,
            "price": str(result["price"]),
            "found": "true"
        },
        tags=["stocks", "price", "lookup"]
    )

def get_stock_price(ticker: str, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Get the current stock price and other market data for a given ticker symbol.
    Falls back to mock database if API call fails.
    
    Args:
        ticker: The ticker symbol to look up
        galileo_logger: Galileo logger for observability (optional)
        
    Returns:
        JSON string containing the stock price and market data
    """
    start_time = time.time()
    try:
        # Use mock database for demo purposes
        if ticker in MOCK_PRICE_DB:
            logging.info(f"Found {ticker} in mock database")
            result = MOCK_PRICE_DB[ticker]
            if galileo_logger:
                _log_to_galileo(galileo_logger, ticker, result, start_time)
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
        if galileo_logger:
            _log_to_galileo(galileo_logger, ticker, result, start_time)
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error getting stock price: {str(e)}")
        
        # On any error, try the mock database
        if ticker in MOCK_PRICE_DB:
            logging.info(f"Found {ticker} in mock database after error")
            result = MOCK_PRICE_DB[ticker]
            if galileo_logger:
                _log_to_galileo(galileo_logger, ticker, result, start_time)
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
        if galileo_logger:
            _log_to_galileo(galileo_logger, ticker, result, start_time)
        return json.dumps(result)


def _log_purchase_to_galileo(galileo_logger: GalileoLogger, ticker: str, quantity: int, price: float, order_id: str, start_time: float) -> None:
    """
    Helper function to log stock purchase to Galileo.
    
    Args:
        galileo_logger: Galileo logger for observability
        ticker: The ticker symbol being purchased
        quantity: Number of shares being purchased
        price: Price per share
        order_id: The generated order ID
        start_time: The start time of the purchase operation
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
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata={
            "ticker": ticker,
            "quantity": str(quantity),
            "price": str(price),
            "order_id": order_id
        },
        tags=["stocks", "purchase", "trade"]
    )

def purchase_stocks(ticker: str, quantity: int, price: float, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Simulate purchasing stocks with a given ticker symbol, quantity, and price.
    
    Args:
        ticker: The ticker symbol to purchase
        quantity: The number of shares to purchase
        price: The price per share
        galileo_logger: Galileo logger for observability (optional)
        
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
            "description": "Purchase of stocks completed successfully"
        }
        
        if galileo_logger:
            _log_purchase_to_galileo(galileo_logger, ticker, quantity, price, order_id, start_time)
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error purchasing stocks: {str(e)}")
        raise


def _log_sale_to_galileo(galileo_logger: GalileoLogger, ticker: str, quantity: int, price: float, order_id: str, start_time: float) -> None:
    """
    Helper function to log stock sale to Galileo.
    
    Args:
        galileo_logger: Galileo logger for observability
        ticker: The ticker symbol being sold
        quantity: Number of shares being sold
        price: Price per share
        order_id: The generated order ID
        start_time: The start time of the sale operation
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
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata={
            "ticker": ticker,
            "quantity": str(quantity),
            "sale": str(price),
            "order_id": order_id
        },
        tags=["stocks", "sale", "trade"]
    )

def sell_stocks(ticker: str, quantity: int, price: float, galileo_logger: Optional[GalileoLogger] = None) -> str:
    """
    Simulate selling stocks with a given ticker symbol, quantity, and price.
    
    Args:
        ticker: The ticker symbol to sell
        quantity: The number of shares to sell
        price: The price per share
        galileo_logger: Galileo logger for observability (optional)
        
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
            "description": "Sale of stocks completed successfully"
        }
        
        if galileo_logger:
            _log_sale_to_galileo(galileo_logger, ticker, quantity, price, order_id, start_time)
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error selling stocks: {str(e)}")
        raise


# Export tools for easy loading by frameworks
TOOLS = [
    get_stock_price,
    purchase_stocks,
    sell_stocks
]
