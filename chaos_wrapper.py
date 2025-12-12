"""
Chaos Wrapper - Automatic chaos injection for domain tools

Simplified version: One function wraps all tools with chaos.
No complex pattern matching - just apply chaos to everything!

Usage:
    from chaos_wrapper import wrap_tools_with_chaos
    
    # In agent framework:
    raw_tools = [get_stock_price, get_patient_vitals, ...]
    wrapped_tools = wrap_tools_with_chaos(raw_tools)
    # Tools now have chaos automatically!
"""
import json
import time
import functools
from chaos_engine import get_chaos_engine


class APIError(Exception):
    """Custom exception for API errors with searchable metadata."""
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


def _extract_status_code(error_msg: str) -> str:
    """Extract HTTP status code from error message."""
    status_codes = ["503", "502", "504", "500", "401", "403", "404", "405", "429"]
    for code in status_codes:
        if code in error_msg:
            return code
    
    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        return "timeout"
    elif "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
        return "ssl_error"
    
    return "500"


def wrap_tools_with_chaos(tools: list) -> list:
    """ Wrap all tools with chaos injection.
    
    Args:
        tools: List of tool functions
        
    Returns:
        List of wrapped tool functions
    """
    chaos = get_chaos_engine()
    wrapped = []
    
    for tool in tools:
        if not hasattr(tool, '__name__'):
            wrapped.append(tool)
            continue
        
        func_name = tool.__name__
        display_name = func_name.replace("_", " ").title()
        
        @functools.wraps(tool)
        def wrapper(*args, __original_func=tool, __display_name=display_name, __func_name=func_name, **kwargs):
            # 1. API Failures - Return error as JSON instead of raising
            if chaos.tool_instability_enabled:
                should_fail, error_msg = chaos.should_fail_api_call(__display_name)
                if should_fail:
                    status_code = _extract_status_code(error_msg)
                    identifier = args[0] if args else 'unknown'
                    # Return error as structured response so Galileo logs it
                    error_response = {
                        "error": error_msg,
                        "status_code": status_code,
                        "error_type": "network_failure",
                        "tool": __func_name,
                        "identifier": str(identifier),
                        "chaos_injected": True
                    }
                    return json.dumps(error_response)
            
            # 2. Rate Limits - Return error as JSON instead of raising
            if chaos.rate_limit_chaos_enabled:
                should_rate_limit, error_msg = chaos.should_fail_rate_limit(__display_name)
                if should_rate_limit:
                    identifier = args[0] if args else 'unknown'
                    # Return error as structured response so Galileo logs it
                    error_response = {
                        "error": error_msg,
                        "status_code": "429",
                        "error_type": "rate_limit",
                        "tool": __func_name,
                        "identifier": str(identifier),
                        "chaos_injected": True
                    }
                    return json.dumps(error_response)
            
            # 3. Latency
            if chaos.tool_instability_enabled:
                delay = chaos.inject_latency()
                if delay > 0:
                    time.sleep(delay)
            
            # 4. Execute the tool and return result
            # NOTE: Data Corruption chaos is now handled at LLM level via system prompt injection
            # (see agent.py invoke_chatbot function)
            result = __original_func(*args, **kwargs)
            
            return result
        
        wrapped.append(wrapper)
    
    return wrapped


def wrap_rag_tool_with_chaos(rag_tool):
    """
    Wrap RAG tool to check for disconnection per-query.
    
    This allows intermittent RAG failures instead of session-level.
    Returns error as structured response so Galileo logs it.
    """
    from langchain_core.tools import BaseTool
    
    chaos = get_chaos_engine()
    
    # Check if it's a LangChain BaseTool (like StructuredTool)
    if isinstance(rag_tool, BaseTool):
        # Get the original function
        original_func = rag_tool.func
        
        @functools.wraps(original_func)
        def wrapper(*args, **kwargs):
            # Check if RAG should fail THIS query (runtime check)
            if chaos.rag_chaos_enabled:
                should_fail, error_msg = chaos.should_disconnect_rag()
                if should_fail:
                    # Return error as structured response so Galileo logs it
                    error_response = {
                        "error": error_msg,
                        "error_type": "rag_failure",
                        "chaos_injected": True,
                        "retrieved_documents": []  # Empty results
                    }
                    return json.dumps(error_response)
            
            # Normal RAG execution
            return original_func(*args, **kwargs)
        
        # Create a new BaseTool instance with the wrapped function
        wrapped_tool = type(rag_tool)(
            name=rag_tool.name,
            description=rag_tool.description,
            func=wrapper,
            args_schema=rag_tool.args_schema
        )
        return wrapped_tool
    else:
        # It's a plain function - wrap it directly
        @functools.wraps(rag_tool)
        def wrapper(*args, **kwargs):
            if chaos.rag_chaos_enabled:
                should_fail, error_msg = chaos.should_disconnect_rag()
                if should_fail:
                    error_response = {
                        "error": error_msg,
                        "error_type": "rag_failure",
                        "chaos_injected": True,
                        "retrieved_documents": []
                    }
                    return json.dumps(error_response)
            return rag_tool(*args, **kwargs)
        
        return wrapper


# Backwards compatibility aliases
wrap_tools_automatically = wrap_tools_with_chaos
wrap_tool_with_chaos = lambda func, **kwargs: wrap_tools_with_chaos([func])[0]

