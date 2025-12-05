"""
Chaos Engineering Engine

Domain-agnostic chaos logic that simulates real-world failures:
- API failures (503, 504, timeouts, etc.)
- Rate limiting (429 errors)
- Data corruption (wrong values, missing fields)
- RAG disconnects (vector DB failures)
- Number transposition (LLM hallucinations)

This module provides the DECISION LOGIC for when/how chaos should occur.
The actual APPLICATION of chaos is handled by chaos_wrapper.py.
"""
import random
import re
import logging
from typing import Optional, Any, Tuple


class ChaosEngine:
    """
    Chaos engineering engine for simulating real-world failures.
    
    This is the "brain" that decides when chaos should happen.
    It's domain-agnostic and works with any tools from any domain.
    """
    
    def __init__(self):
        # Chaos toggles (controlled from UI)
        self.tool_instability_enabled = False
        self.sloppiness_enabled = False
        self.rag_chaos_enabled = False
        self.rate_limit_chaos_enabled = False
        self.data_corruption_enabled = False
        
        # Chaos parameters (failure rates - defaults)
        self.tool_failure_rate = 1  # 25% chance of API failure
        self.sloppiness_rate = 1  # 30% chance of number transposition
        self.rag_failure_rate = 1  # 20% chance of RAG disconnect
        self.rate_limit_rate = 1  # 15% chance of rate limit error
        self.data_corruption_rate = 1  # 20% chance of corrupted data
        
        # Counters for statistics
        self.api_call_count = 0
        self.sloppy_outputs = 0
        self.rag_failures = 0
    
    def enable_tool_instability(self, enabled: bool = True, failure_rate: Optional[float] = None):
        """Enable random API failures"""
        self.tool_instability_enabled = enabled
        if failure_rate is not None:
            self.tool_failure_rate = failure_rate
        logging.info(f"Tool Instability: {'ON' if enabled else 'OFF'} (rate: {self.tool_failure_rate})")
    
    def enable_sloppiness(self, enabled: bool = True, error_rate: Optional[float] = None):
        """Enable random number transpositions (hallucinations)"""
        self.sloppiness_enabled = enabled
        if error_rate is not None:
            self.sloppiness_rate = error_rate
        logging.info(f"Sloppiness: {'ON' if enabled else 'OFF'} (rate: {self.sloppiness_rate})")
    
    def enable_rag_chaos(self, enabled: bool = True, failure_rate: Optional[float] = None):
        """Enable random RAG disconnects"""
        self.rag_chaos_enabled = enabled
        if failure_rate is not None:
            self.rag_failure_rate = failure_rate
        logging.info(f"RAG Chaos: {'ON' if enabled else 'OFF'} (rate: {self.rag_failure_rate})")
    
    def enable_rate_limit_chaos(self, enabled: bool = True, rate: Optional[float] = None):
        """Enable random rate limit errors"""
        self.rate_limit_chaos_enabled = enabled
        if rate is not None:
            self.rate_limit_rate = rate
        logging.info(f"Rate Limit Chaos: {'ON' if enabled else 'OFF'} (rate: {self.rate_limit_rate})")
    
    def enable_data_corruption(self, enabled: bool = True, rate: Optional[float] = None):
        """Enable random data corruption"""
        self.data_corruption_enabled = enabled
        if rate is not None:
            self.data_corruption_rate = rate
        logging.info(f"Data Corruption: {'ON' if enabled else 'OFF'} (rate: {self.data_corruption_rate})")
    
    def should_fail_api_call(self, tool_name: str = "API") -> Tuple[bool, Optional[str]]:
        """
        Determine if an API call should fail with realistic HTTP errors.
        
        Args:
            tool_name: Name of the tool/API being called
            
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
                
                # Client errors (4xx)
                f"{tool_name} authentication failed (401 Unauthorized)",
                f"{tool_name} access forbidden (403 Forbidden)",
                f"{tool_name} resource not found (404 Not Found)",
                
                # Network/connection errors
                f"{tool_name} timeout after 30 seconds (Connection Timeout)",
                f"Connection refused: {tool_name} server not responding",
                f"Network error: Failed to reach {tool_name} endpoint",
                f"SSL certificate validation failed for {tool_name}",
            ]
            error = random.choice(errors)
            logging.warning(f"🔥 CHAOS: Injecting API failure for {tool_name}: {error}")
            return True, error
        
        return False, None
    
    def should_fail_rate_limit(self, tool_name: str = "API") -> Tuple[bool, Optional[str]]:
        """
        Simulate rate limit errors.
        
        Args:
            tool_name: Name of the tool/API being called
            
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
    
    def transpose_numbers(self, text: str) -> str:
        """
        Replace numbers with obviously wrong random numbers to simulate hallucinations.
        
        Examples:
            "$178.45" → "$423.89" (completely different)
            "Price $178.45, up 2.5%" → "Price $892.31, up 7.8%" (multiple numbers wrong)
        
        Args:
            text: Text containing numbers
            
        Returns:
            Text with randomly corrupted numbers
        """
        if not self.sloppiness_enabled:
            return text
        
        if random.random() >= self.sloppiness_rate:
            return text  # No error this time
        
        # Find all numbers with decimals (e.g., "178.45") and integers (e.g., "178")
        # Match numbers with optional decimals and commas
        number_pattern = r'\d+(?:,\d+)*(?:\.\d+)?'
        
        def replace_number(match):
            """Replace a number with a random wrong number of similar magnitude"""
            original = match.group(0)
            
            # Remove commas for processing
            clean_num = original.replace(',', '')
            
            try:
                # Check if it has decimals
                if '.' in clean_num:
                    # Float number
                    val = float(clean_num)
                    # Generate random number in similar range (0.5x to 3x)
                    new_val = val * random.uniform(0.5, 3.0)
                    # Keep same decimal places
                    decimal_places = len(clean_num.split('.')[1])
                    corrupted = f"{new_val:.{decimal_places}f}"
                else:
                    # Integer
                    val = int(clean_num)
                    # Generate random number in similar range
                    if val < 10:
                        # Small numbers: just scramble or change
                        corrupted = str(random.randint(0, 20))
                    else:
                        # Larger numbers: multiply by 0.5x to 3x
                        new_val = int(val * random.uniform(0.5, 3.0))
                        corrupted = str(new_val)
                        
                        # Add commas back if original had them
                        if ',' in original:
                            corrupted = f"{int(corrupted):,}"
                
                logging.warning(f"🔥 CHAOS: Number hallucination - '{original}' → '{corrupted}'")
                return corrupted
                
            except (ValueError, ZeroDivisionError):
                # If parsing fails, return original
                return original
        
        # Replace all numbers in the text
        result = re.sub(number_pattern, replace_number, text)
        
        if result != text:
            self.sloppy_outputs += 1
        
        return result
    
    def corrupt_data(self, data: Any) -> Any:
        """
        Randomly corrupt data (wrong values, missing fields, etc.)
        
        DOMAIN-AGNOSTIC: Works with ANY data structure from ANY domain.
        
        Simulates:
        - Wrong numeric values (prices, counts, measurements, etc.)
        - Negative values (for positive-only fields)
        - Missing fields
        - Stale timestamps
        - Wrong identifiers
        
        Args:
            data: Data to potentially corrupt (dict or other type)
            
        Returns:
            Potentially corrupted data
        """
        if not self.data_corruption_enabled:
            return data
        
        if random.random() >= self.data_corruption_rate:
            return data
        
        if not isinstance(data, dict):
            return data  # Can only corrupt dict structures
        
        corruption_type = random.choice([
            "wrong_numeric_value",
            "negative_value",
            "missing_field",
            "stale_timestamp",
            "wrong_identifier"
        ])
        
        if corruption_type == "wrong_numeric_value":
            # Find ANY numeric field and corrupt it (domain-agnostic!)
            numeric_fields = [k for k, v in data.items() 
                            if isinstance(v, (int, float)) and k not in ["status_code", "success"]]
            if numeric_fields:
                field = random.choice(numeric_fields)
                original = data[field]
                # Multiply by random factor (0.5x to 2x)
                if isinstance(original, int):
                    data[field] = int(original * random.uniform(0.5, 2.0))
                else:
                    data[field] = round(original * random.uniform(0.5, 2.0), 2)
                logging.warning(f"🔥 CHAOS: Corrupted {field} {original} → {data[field]}")
        
        elif corruption_type == "negative_value":
            # Make ANY numeric value negative (works for any domain)
            numeric_fields = [k for k, v in data.items() 
                            if isinstance(v, (int, float)) and v > 0 
                            and k not in ["status_code", "success"]]
            if numeric_fields:
                field = random.choice(numeric_fields)
                data[field] = -abs(data[field])
                logging.warning(f"🔥 CHAOS: Made {field} negative")
        
        elif corruption_type == "missing_field" and len(data) > 2:
            # Remove a random field (domain-agnostic)
            fields_to_skip = ["_metadata", "status_code", "success", "error"]
            removable_fields = [k for k in data.keys() if k not in fields_to_skip]
            if removable_fields:
                field_to_remove = random.choice(removable_fields)
                del data[field_to_remove]
                logging.warning(f"🔥 CHAOS: Removed field '{field_to_remove}'")
        
        elif corruption_type == "stale_timestamp":
            # Look for ANY timestamp-like field (domain-agnostic)
            timestamp_fields = [k for k in data.keys() 
                              if any(t in k.lower() for t in ["time", "date", "timestamp", "created", "updated"])]
            if timestamp_fields:
                field = random.choice(timestamp_fields)
                data[field] = "2020-01-01 00:00:00"
                logging.warning(f"🔥 CHAOS: Set stale {field}")
        
        elif corruption_type == "wrong_identifier":
            # Look for ANY identifier field (domain-agnostic)
            id_fields = [k for k in data.keys() 
                        if any(i in k.lower() for i in ["id", "ticker", "symbol", "code", "reference"])]
            if id_fields:
                field = random.choice(id_fields)
                original = data[field]
                data[field] = "XXXX_CORRUPTED"
                logging.warning(f"🔥 CHAOS: Changed {field} '{original}' → '{data[field]}'")
        
        return data
    
    def should_disconnect_rag(self) -> Tuple[bool, Optional[str]]:
        """
        Determine if RAG should fail (works for any vector DB).
        
        Returns:
            (should_fail, error_message)
        """
        if not self.rag_chaos_enabled:
            return False, None
        
        if random.random() < self.rag_failure_rate:
            errors = [
                # Generic vector DB errors
                "Vector database connection timeout",
                "Vector database service unavailable",
                "Embedding model failed to respond",
                "RAG retrieval returned empty results",
                "Document index corrupted",
                
                # Specific vector DB errors
                "ChromaDB service unavailable",
                "Pinecone index unavailable (503 Service Unavailable)",
                "Embedding dimension mismatch error",
            ]
            error = random.choice(errors)
            self.rag_failures += 1
            logging.warning(f"🔥 CHAOS: Injecting RAG failure: {error}")
            return True, error
        
        return False, None
    
    def inject_latency(self) -> float:
        """
        Return a random delay to simulate network latency.
        
        Returns:
            Seconds to delay (0 to 5 seconds)
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

