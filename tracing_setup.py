"""
Shared OTLP Tracing Setup for Observability Platforms

This module provides centralized initialization for OpenTelemetry-based
tracing platforms (Phoenix and Arize AX).

ARCHITECTURE:
- OpenTelemetry instrumentation is set up ONCE at module load time
- A "switchable" span processor routes spans to the active platform
- Platform can be changed at runtime WITHOUT server restart
- Project name is read from GALILEO_PROJECT env var (set by setup_env.py)
"""
import os
from typing import Optional



# Global state
_instrumentation_initialized = False
_active_platform: str = "none"  # "phoenix", "arize", or "none"
_switchable_processor: Optional["SwitchableSpanProcessor"] = None
_phoenix_available = False
_arize_available = False


class SwitchableSpanProcessor:
    """
    A span processor that routes spans to the active platform at runtime.
    Adds platform-specific project attributes to spans.
    """
    
    def __init__(self):
        self._phoenix_processor = None
        self._arize_processor = None
        self._active = "none"
        self._phoenix_project = None
        self._arize_project = None
    
    def set_phoenix_processor(self, processor, project_name: str = None):
        """Set the Phoenix span processor"""
        if self._phoenix_processor:
            try:
                self._phoenix_processor.shutdown()
            except Exception:
                pass
        self._phoenix_processor = processor
        self._phoenix_project = project_name
    
    def set_arize_processor(self, processor, project_name: str = None):
        """Set the Arize span processor"""
        if self._arize_processor:
            try:
                self._arize_processor.shutdown()
            except Exception:
                pass
        self._arize_processor = processor
        self._arize_project = project_name
    
    def switch_to(self, platform: str):
        """Switch which platform receives spans"""
        self._active = platform.lower()
    
    def get_active(self) -> str:
        return self._active
    
    def on_start(self, span, parent_context=None):
        # Add platform-specific project attributes
        if self._active == "phoenix" and self._phoenix_project:
            span.set_attribute("openinference.project.name", self._phoenix_project)
        elif self._active == "arize" and self._arize_project:
            span.set_attribute("arize.project.name", self._arize_project)
        
        if self._active == "phoenix" and self._phoenix_processor:
            self._phoenix_processor.on_start(span, parent_context)
        elif self._active == "arize" and self._arize_processor:
            self._arize_processor.on_start(span, parent_context)
    
    def on_end(self, span):
        if self._active == "phoenix" and self._phoenix_processor:
            self._phoenix_processor.on_end(span)
        elif self._active == "arize" and self._arize_processor:
            self._arize_processor.on_end(span)
    
    def shutdown(self):
        if self._phoenix_processor:
            self._phoenix_processor.shutdown()
        if self._arize_processor:
            self._arize_processor.shutdown()
    
    def force_flush(self, timeout_millis: int = 30000):
        if self._active == "phoenix" and self._phoenix_processor:
            self._phoenix_processor.force_flush(timeout_millis)
        elif self._active == "arize" and self._arize_processor:
            self._arize_processor.force_flush(timeout_millis)


def _create_phoenix_processor():
    """Create a Phoenix processor. Returns (processor, project_name) tuple.
    
    Note: Phoenix reads project from TracerProvider resource attributes,
    which are set at initialization time. The project shown here is for logging only.
    """
    phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT")
    phoenix_api_key = os.getenv("PHOENIX_API_KEY")
    project = os.getenv("GALILEO_PROJECT", "galileo-demo")
    print(f"[OTLP] Creating Phoenix processor (resource project set at init time)")
    
    if not phoenix_endpoint or not phoenix_api_key:
        return None, None
    
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        exporter = OTLPSpanExporter(
            endpoint=phoenix_endpoint,
            headers={"authorization": f"Bearer {phoenix_api_key}"}
        )
        
        print(f"[OTLP] Phoenix processor created")
        return BatchSpanProcessor(exporter), project
    except Exception as e:
        print(f"[OTLP] Failed to create Phoenix processor: {e}")
        return None, None


def _create_arize_processor():
    """Create an Arize processor. Returns (processor, project_name) tuple."""
    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")
    # Use GALILEO_PROJECT (set by setup_env.py) for consistency across all platforms
    project = os.getenv("GALILEO_PROJECT", "galileo-demo")
    print(f"[OTLP] Creating Arize processor with project_name: {project}")
    
    if not space_id or not api_key:
        return None, None
    
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        exporter = OTLPSpanExporter(
            endpoint="https://otlp.arize.com/v1/traces",
            headers={
                "authorization": api_key,
                "space_id": space_id,
            }
        )
        
        print(f"[OTLP] Arize processor created (project_name: {project})")
        return BatchSpanProcessor(exporter), project
    except Exception as e:
        print(f"[OTLP] Failed to create Arize processor: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def initialize_otlp_tracing():
    """
    Initialize OTLP tracing infrastructure. Call ONCE before LangChain imports.
    
    Note: For Phoenix, the project name is read from GALILEO_PROJECT env var
    at initialization time. If not set, uses "default".
    """
    global _instrumentation_initialized, _switchable_processor
    global _phoenix_available, _arize_available, _active_platform
    
    if _instrumentation_initialized:
        return "already_initialized"
    
    print(f"\n🔭 Initializing OTLP tracing infrastructure...")
    
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        
        _switchable_processor = SwitchableSpanProcessor()
        
        # Check credentials availability
        _phoenix_available = bool(os.getenv("PHOENIX_ENDPOINT") and os.getenv("PHOENIX_API_KEY"))
        _arize_available = bool(os.getenv("ARIZE_SPACE_ID") and os.getenv("ARIZE_API_KEY"))
        
        # Get project name for Phoenix (baked into resource, can't change at runtime)
        # Priority: PHOENIX_PROJECT_NAME > GALILEO_PROJECT > "galileo-demo"
        project = os.getenv("PHOENIX_PROJECT_NAME") or os.getenv("GALILEO_PROJECT", "galileo-demo")
        
        # Set up tracer provider with switchable processor
        # Include openinference.project.name for Phoenix compatibility
        resource = Resource.create({
            "service.name": "galileo-demo",
            "openinference.project.name": project,
        })
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        tracer_provider.add_span_processor(_switchable_processor)
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument LangChain
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider, skip_dep_check=True)
        
        _instrumentation_initialized = True
        _active_platform = "none"
        
        print(f"   ✅ OTLP infrastructure ready")
        print(f"   Phoenix project (fixed): {project}")
        print(f"   Phoenix: {'available' if _phoenix_available else 'no credentials'}")
        print(f"   Arize: {'available' if _arize_available else 'no credentials'}")
        
        return "initialized"
        
    except Exception as e:
        print(f"   ⚠️ OTLP initialization failed: {e}")
        _instrumentation_initialized = True
        return "failed"


def switch_otlp_platform(platform: str) -> bool:
    """
    Switch the active OTLP platform. Creates processor on first use.
    Project name is read from GALILEO_PROJECT env var.
    """
    global _active_platform
    
    if not _instrumentation_initialized or not _switchable_processor:
        print(f"[OTLP] Cannot switch - not initialized")
        return False
    
    platform = platform.lower().strip()
    if platform in ["arize", "arize-ax", "arize_ax", "arize ax"]:
        platform = "arize"
    
    # Handle "none"
    if platform == "none":
        _switchable_processor.switch_to("none")
        _active_platform = "none"
        return True
    
    # Validate credentials
    if platform == "phoenix" and not _phoenix_available:
        print(f"[OTLP] Phoenix not available (no credentials)")
        return False
    if platform == "arize" and not _arize_available:
        print(f"[OTLP] Arize not available (no credentials)")
        return False
    
    # Create processor (reads GALILEO_PROJECT at creation time)
    if platform == "phoenix":
        processor, project_name = _create_phoenix_processor()
        if processor:
            _switchable_processor.set_phoenix_processor(processor, project_name)
    elif platform == "arize":
        processor, project_name = _create_arize_processor()
        if processor:
            _switchable_processor.set_arize_processor(processor, project_name)
    
    _switchable_processor.switch_to(platform)
    _active_platform = platform
    return True


def get_active_platform() -> str:
    """Get the currently active OTLP platform."""
    return _active_platform


def is_phoenix_available() -> bool:
    """Check if Phoenix credentials are configured."""
    return _phoenix_available


def is_arize_available() -> bool:
    """Check if Arize credentials are configured."""
    return _arize_available
