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
import inspect
import asyncio
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


def _build_chaos_wrappers(tool, display_name, func_name):
    """Return sync and async wrappers that inject chaos before calling the tool."""
    chaos = get_chaos_engine()

    def _maybe_fail(*args):
        if chaos.tool_instability_enabled:
            should_fail, error_msg = chaos.should_fail_api_call(display_name)
            if should_fail:
                status_code = _extract_status_code(error_msg)
                identifier = args[0] if args else "unknown"
                return json.dumps(
                    {
                        "error": error_msg,
                        "status_code": status_code,
                        "error_type": "network_failure",
                        "tool": func_name,
                        "identifier": str(identifier),
                        "chaos_injected": True,
                    }
                )

        if chaos.rate_limit_chaos_enabled:
            should_rate_limit, error_msg = chaos.should_fail_rate_limit(display_name)
            if should_rate_limit:
                identifier = args[0] if args else "unknown"
                return json.dumps(
                    {
                        "error": error_msg,
                        "status_code": "429",
                        "error_type": "rate_limit",
                        "tool": func_name,
                        "identifier": str(identifier),
                        "chaos_injected": True,
                    }
                )
        return None

    @functools.wraps(tool)
    async def async_wrapper(*args, __original_func=tool, **kwargs):
        failure = _maybe_fail(*args)
        if failure is not None:
            return failure

        if chaos.tool_instability_enabled:
            delay = chaos.inject_latency()
            if delay > 0:
                await asyncio.sleep(delay)

        return await __original_func(*args, **kwargs)

    @functools.wraps(tool)
    def sync_wrapper(*args, __original_func=tool, **kwargs):
        failure = _maybe_fail(*args)
        if failure is not None:
            return failure

        if chaos.tool_instability_enabled:
            delay = chaos.inject_latency()
            if delay > 0:
                time.sleep(delay)

        return __original_func(*args, **kwargs)

    return async_wrapper, sync_wrapper


def wrap_tools_with_chaos(tools: list) -> list:
    """ Wrap all tools with chaos injection.
    
    Args:
        tools: List of tool functions
        
    Returns:
        List of wrapped tool functions
    """
    wrapped = []
    
    for tool in tools:
        if not hasattr(tool, '__name__'):
            wrapped.append(tool)
            continue
        
        func_name = tool.__name__
        display_name = func_name.replace("_", " ").title()
        async_wrapper, sync_wrapper = _build_chaos_wrappers(tool, display_name, func_name)

        if inspect.iscoroutinefunction(tool):
            wrapped.append(async_wrapper)
        else:
            wrapped.append(sync_wrapper)
    
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
        original_func = rag_tool.coroutine or rag_tool.func
        is_async = inspect.iscoroutinefunction(original_func)

        if is_async:
            @functools.wraps(original_func)
            async def async_wrapper(*args, **kwargs):
                if chaos.rag_chaos_enabled:
                    should_fail, error_msg = chaos.should_disconnect_rag()
                    if should_fail:
                        return json.dumps(
                            {
                                "error": error_msg,
                                "error_type": "rag_failure",
                                "chaos_injected": True,
                                "retrieved_documents": [],
                            }
                        )
                return await original_func(*args, **kwargs)

            wrapped_tool = type(rag_tool)(
                name=rag_tool.name,
                description=rag_tool.description,
                coroutine=async_wrapper,
                args_schema=rag_tool.args_schema,
            )
            return wrapped_tool

        @functools.wraps(original_func)
        def sync_wrapper(*args, **kwargs):
            if chaos.rag_chaos_enabled:
                should_fail, error_msg = chaos.should_disconnect_rag()
                if should_fail:
                    return json.dumps(
                        {
                            "error": error_msg,
                            "error_type": "rag_failure",
                            "chaos_injected": True,
                            "retrieved_documents": [],
                        }
                    )
            return original_func(*args, **kwargs)

        wrapped_tool = type(rag_tool)(
            name=rag_tool.name,
            description=rag_tool.description,
            func=sync_wrapper,
            args_schema=rag_tool.args_schema,
        )
        return wrapped_tool
    else:
        is_async = inspect.iscoroutinefunction(rag_tool)
        if is_async:
            @functools.wraps(rag_tool)
            async def async_wrapper(*args, **kwargs):
                if chaos.rag_chaos_enabled:
                    should_fail, error_msg = chaos.should_disconnect_rag()
                    if should_fail:
                        return json.dumps(
                            {
                                "error": error_msg,
                                "error_type": "rag_failure",
                                "chaos_injected": True,
                                "retrieved_documents": [],
                            }
                        )
                return await rag_tool(*args, **kwargs)

            return async_wrapper

        @functools.wraps(rag_tool)
        def sync_wrapper(*args, **kwargs):
            if chaos.rag_chaos_enabled:
                should_fail, error_msg = chaos.should_disconnect_rag()
                if should_fail:
                    return json.dumps(
                        {
                            "error": error_msg,
                            "error_type": "rag_failure",
                            "chaos_injected": True,
                            "retrieved_documents": [],
                        }
                    )
            return rag_tool(*args, **kwargs)

        return sync_wrapper


# Backwards compatibility aliases
wrap_tools_automatically = wrap_tools_with_chaos
wrap_tool_with_chaos = lambda func, **kwargs: wrap_tools_with_chaos([func])[0]

