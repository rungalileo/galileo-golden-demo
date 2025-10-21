"""
Chaos Engineering Module

Simulates real-world failures and problematic patterns to test:
- Galileo observability (detect anomalies)
- Galileo guardrails (block bad outputs)
- Galileo insights (surface patterns)

Usage:
    from chaos_engine import ChaosEngine
    
    chaos = ChaosEngine()
    chaos.enable_tool_instability()
    chaos.enable_sloppiness()
    
    # In tools:
    if chaos.should_fail_api_call():
        raise Exception("API temporarily unavailable")
    
    output = chaos.maybe_transpose_numbers(output)
"""
import os
import random
import re
import logging
from typing import Optional, Any


class ChaosEngine:
    """
    Chaos engineering for simulating real-world failures
    """
    
    def __init__(self):
        # Chaos toggles (controlled from UI)
        self.tool_instability_enabled = False
        self.sloppiness_enabled = False
        self.rag_chaos_enabled = False
        self.rate_limit_chaos_enabled = False
        self.data_corruption_enabled = False
        
        # Chaos parameters
        self.tool_failure_rate = 0.25  # 25% chance of API failure
        self.sloppiness_rate = 0.30  # 30% chance of number transposition
        self.rag_failure_rate = 0.20  # 20% chance of RAG disconnect
        self.rate_limit_rate = 0.15  # 15% chance of rate limit error
        self.data_corruption_rate = 0.20  # 20% chance of corrupted data
        
        # Counters for patterns
        self.api_call_count = 0
        self.sloppy_outputs = 0
        self.rag_failures = 0
        
    def enable_tool_instability(self, enabled: bool = True, failure_rate: float = 0.25):
        """Enable random API failures"""
        self.tool_instability_enabled = enabled
        self.tool_failure_rate = failure_rate
        logging.info(f"Tool Instability: {'ON' if enabled else 'OFF'} (rate: {failure_rate})")
    
    def enable_sloppiness(self, enabled: bool = True, error_rate: float = 0.30):
        """Enable random number transpositions (hallucinations)"""
        self.sloppiness_enabled = enabled
        self.sloppiness_rate = error_rate
        logging.info(f"Sloppiness: {'ON' if enabled else 'OFF'} (rate: {error_rate})")
    
    def enable_rag_chaos(self, enabled: bool = True, failure_rate: float = 0.20):
        """Enable random RAG disconnects"""
        self.rag_chaos_enabled = enabled
        self.rag_failure_rate = failure_rate
        logging.info(f"RAG Chaos: {'ON' if enabled else 'OFF'} (rate: {failure_rate})")
    
    def enable_rate_limit_chaos(self, enabled: bool = True, rate: float = 0.15):
        """Enable random rate limit errors"""
        self.rate_limit_chaos_enabled = enabled
        self.rate_limit_rate = rate
        logging.info(f"Rate Limit Chaos: {'ON' if enabled else 'OFF'} (rate: {rate})")
    
    def enable_data_corruption(self, enabled: bool = True, rate: float = 0.20):
        """Enable random data corruption"""
        self.data_corruption_enabled = enabled
        self.data_corruption_rate = rate
        logging.info(f"Data Corruption: {'ON' if enabled else 'OFF'} (rate: {rate})")
    
    def should_fail_api_call(self, tool_name: str = "API") -> tuple[bool, Optional[str]]:
        """
        Determine if an API call should fail with realistic HTTP errors
        
        Returns:
            (should_fail, error_message)
        """
        if not self.tool_instability_enabled:
            return False, None
        
        self.api_call_count += 1
        
        if random.random() < self.tool_failure_rate:
            # Realistic HTTP errors with status codes
            errors = [
                # Server errors (5xx) - most common in production
                f"{tool_name} temporarily unavailable (503 Service Unavailable)",
                f"{tool_name} internal error (500 Internal Server Error)",
                f"{tool_name} bad gateway (502 Bad Gateway)",
                f"{tool_name} gateway timeout (504 Gateway Timeout)",
                f"{tool_name} service overload (503 Service Temporarily Unavailable)",
                
                # Client errors (4xx)
                f"{tool_name} authentication failed (401 Unauthorized)",
                f"{tool_name} access forbidden (403 Forbidden)",
                f"{tool_name} resource not found (404 Not Found)",
                f"{tool_name} method not allowed (405 Method Not Allowed)",
                
                # Network/connection errors
                f"{tool_name} timeout after 30 seconds (Connection Timeout)",
                f"Connection refused: {tool_name} server not responding",
                f"Network error: Failed to reach {tool_name} endpoint",
                f"DNS resolution failed for {tool_name}",
                f"SSL certificate validation failed for {tool_name}",
                f"Connection reset by peer: {tool_name}",
                
                # Invalid/malformed responses
                f"{tool_name} returned invalid response (malformed JSON)",
                f"{tool_name} returned empty response (204 No Content)",
                f"{tool_name} returned unexpected content type (expected JSON, got HTML)",
            ]
            error = random.choice(errors)
            logging.warning(f"🔥 CHAOS: Injecting API failure for {tool_name}: {error}")
            return True, error
        
        return False, None
    
    def should_fail_rate_limit(self, tool_name: str = "API") -> tuple[bool, Optional[str]]:
        """
        Simulate rate limit errors
        
        Returns:
            (should_fail, error_message)
        """
        if not self.rate_limit_chaos_enabled:
            return False, None
        
        if random.random() < self.rate_limit_rate:
            error = f"Rate limit exceeded for {tool_name}. Please try again later. (429 Too Many Requests)"
            logging.warning(f"🔥 CHAOS: Injecting rate limit error: {error}")
            return True, error
        
        return False, None
    
    def maybe_transpose_numbers(self, text: str) -> str:
        """
        Randomly transpose digits in numbers to simulate hallucinations
        
        Examples:
            "$123.45" → "$132.45" (transposed 2 and 3)
            "10 shares" → "01 shares" 
            "$1,234.56" → "$1,243.56"
        
        Returns:
            Text with potentially transposed numbers
        """
        if not self.sloppiness_enabled:
            return text
        
        if random.random() >= self.sloppiness_rate:
            return text  # No error this time
        
        # Find all numbers in the text
        number_pattern = r'\d+'
        numbers = re.findall(number_pattern, text)
        
        if not numbers:
            return text  # No numbers to transpose
        
        # Pick a random number to corrupt
        target_number = random.choice(numbers)
        
        if len(target_number) < 2:
            return text  # Need at least 2 digits to transpose
        
        # Transpose two adjacent digits
        digits = list(target_number)
        pos = random.randint(0, len(digits) - 2)
        digits[pos], digits[pos + 1] = digits[pos + 1], digits[pos]
        corrupted = ''.join(digits)
        
        # Replace in text
        result = text.replace(target_number, corrupted, 1)
        
        self.sloppy_outputs += 1
        logging.warning(f"🔥 CHAOS: Number transposition - '{target_number}' → '{corrupted}'")
        logging.warning(f"   Original: ...{text[max(0, text.find(target_number)-20):text.find(target_number)+len(target_number)+20]}...")
        logging.warning(f"   Modified: ...{result[max(0, result.find(corrupted)-20):result.find(corrupted)+len(corrupted)+20]}...")
        
        return result
    
    def corrupt_data(self, data: Any) -> Any:
        """
        Randomly corrupt data (wrong values, missing fields, etc.)
        
        Simulates:
        - Wrong prices
        - Missing fields
        - Invalid JSON
        - Stale data
        """
        if not self.data_corruption_enabled:
            return data
        
        if random.random() >= self.data_corruption_rate:
            return data
        
        corruption_type = random.choice([
            "wrong_price",
            "negative_value",
            "missing_field",
            "stale_timestamp",
            "wrong_ticker"
        ])
        
        if isinstance(data, dict):
            if corruption_type == "wrong_price" and "price" in data:
                # Multiply price by random factor (0.5x to 2x)
                original = data["price"]
                data["price"] = round(original * random.uniform(0.5, 2.0), 2)
                logging.warning(f"🔥 CHAOS: Corrupted price {original} → {data['price']}")
            
            elif corruption_type == "negative_value" and "change" in data:
                # Make all values negative
                if "change" in data:
                    data["change"] = -abs(data["change"])
                if "change_percent" in data:
                    data["change_percent"] = -abs(data["change_percent"])
                logging.warning(f"🔥 CHAOS: Corrupted to negative values")
            
            elif corruption_type == "missing_field":
                # Remove a random field
                if len(data) > 2:
                    field_to_remove = random.choice(list(data.keys()))
                    del data[field_to_remove]
                    logging.warning(f"🔥 CHAOS: Removed field '{field_to_remove}'")
            
            elif corruption_type == "stale_timestamp" and "timestamp" in data:
                # Make timestamp very old
                data["timestamp"] = "2020-01-01 00:00:00"
                logging.warning(f"🔥 CHAOS: Set stale timestamp")
            
            elif corruption_type == "wrong_ticker" and "ticker" in data:
                # Change ticker to wrong one
                tickers = ["XXXX", "ZZZZ", "FAKE", "TEST"]
                original = data["ticker"]
                data["ticker"] = random.choice(tickers)
                logging.warning(f"🔥 CHAOS: Changed ticker {original} → {data['ticker']}")
        
        return data
    
    def should_disconnect_rag(self) -> tuple[bool, Optional[str]]:
        """
        Determine if RAG should fail
        
        Returns:
            (should_fail, error_message)
        """
        if not self.rag_chaos_enabled:
            return False, None
        
        if random.random() < self.rag_failure_rate:
            errors = [
                "Vector database connection timeout",
                "ChromaDB service unavailable",
                "Embedding model failed to respond",
                "RAG retrieval returned empty results",
                "Document index corrupted",
            ]
            error = random.choice(errors)
            self.rag_failures += 1
            logging.warning(f"🔥 CHAOS: Injecting RAG failure: {error}")
            return True, error
        
        return False, None
    
    def inject_latency(self) -> float:
        """
        Return a random delay to simulate network latency
        
        Returns:
            Seconds to delay (0 to 3 seconds)
        """
        if self.tool_instability_enabled:
            # Occasionally inject significant latency
            if random.random() < 0.1:  # 10% chance
                delay = random.uniform(2.0, 5.0)
                logging.warning(f"🔥 CHAOS: Injecting {delay:.1f}s latency")
                return delay
        
        return 0.0
    
    def get_stats(self) -> dict:
        """Get chaos statistics"""
        return {
            "api_call_count": self.api_call_count,
            "sloppy_outputs": self.sloppy_outputs,
            "rag_failures": self.rag_failures,
            "tool_instability": self.tool_instability_enabled,
            "sloppiness": self.sloppiness_enabled,
            "rag_chaos": self.rag_chaos_enabled,
            "rate_limit_chaos": self.rate_limit_chaos_enabled,
            "data_corruption": self.data_corruption_enabled,
        }
    
    def reset_stats(self):
        """Reset counters"""
        self.api_call_count = 0
        self.sloppy_outputs = 0
        self.rag_failures = 0


# Global chaos engine instance
_chaos_instance = None

def get_chaos_engine() -> ChaosEngine:
    """Get global chaos engine instance"""
    global _chaos_instance
    if _chaos_instance is None:
        _chaos_instance = ChaosEngine()
    return _chaos_instance

