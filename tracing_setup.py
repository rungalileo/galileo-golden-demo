"""
Shared OTLP Tracing Setup for Observability Platforms

This module provides centralized initialization for OpenTelemetry-based
tracing platforms (Phoenix and Arize AX). It can be imported by both
the Streamlit app and experiment runners to ensure consistent tracing.
"""
import os


# Global flags to prevent re-initialization
_phoenix_initialized = False
_arize_ax_initialized = False


def _get_otlp_preference():
    """Read the OTLP platform preference from file"""
    pref_file = os.path.join(os.path.dirname(__file__), ".otlp_preference")
    try:
        if os.path.exists(pref_file):
            with open(pref_file, "r") as f:
                return f.read().strip().lower()
    except:
        pass
    return "phoenix"  # Default to Phoenix


def _initialize_phoenix_otlp():
    """Initialize Phoenix OTLP tracing (must be called before LangChain imports)"""
    global _phoenix_initialized
    
    if _phoenix_initialized:
        return True  # Silent return if already initialized
    
    phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT")
    phoenix_api_key = os.getenv("PHOENIX_API_KEY")
    phoenix_project = os.getenv("PHOENIX_PROJECT", "galileo-demo")
    
    if not phoenix_endpoint or not phoenix_api_key:
        print("   ⚠️  Phoenix credentials not set, skipping initialization")
        return False
    
    print(f"\n🔭 Initializing Phoenix OTLP tracing...")
    
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        
        # Create OTLP exporter with Bearer token auth and project headers
        exporter = OTLPSpanExporter(
            endpoint=phoenix_endpoint,
            headers={
                "authorization": f"Bearer {phoenix_api_key}",
                "project": phoenix_project,
                "x-project": phoenix_project,
                "x-project-name": phoenix_project,
            }
        )
        
        # Create resource with project attributes
        resource = Resource.create({
            "service.name": phoenix_project,
            "project.name": phoenix_project,
            "openinference.project.name": phoenix_project,
        })
        
        # Create tracer provider with resource and BatchSpanProcessor
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument LangChain with OpenInference semantic conventions
        LangChainInstrumentor().instrument(
            tracer_provider=tracer_provider,
            skip_dep_check=True
        )
        
        _phoenix_initialized = True
        os.environ['_PHOENIX_INITIALIZED'] = 'true'
        
        print(f"   ✅ Phoenix initialized with BatchSpanProcessor")
        print(f"   Project: {phoenix_project}")
        print(f"   Endpoint: {phoenix_endpoint}")
        return True
    except Exception as e:
        print(f"   ⚠️  Phoenix pre-init failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _initialize_arize_ax_otlp():
    """Initialize Arize AX OTLP tracing (must be called before LangChain imports)"""
    global _arize_ax_initialized
    
    if _arize_ax_initialized:
        return True  # Silent return if already initialized
    
    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")
    project = os.getenv("ARIZE_PROJECT", "galileo-demo")
    
    if not space_id or not api_key:
        print("   ⚠️  Arize AX credentials not set, skipping initialization")
        return False
    
    print(f"\n🔭 Initializing Arize AX OTLP tracing...")
    
    try:
        # Use manual OTLP setup (same as Phoenix) which we know sends traces successfully
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        
        # Arize OTLP endpoint (HTTP)
        arize_endpoint = "https://otlp.arize.com/v1/traces"
        
        # Create OTLP exporter with Arize-specific headers
        exporter = OTLPSpanExporter(
            endpoint=arize_endpoint,
            headers={
                "authorization": api_key,
                "space_id": space_id,
                "model_id": project,
                "model_version": "production",
            }
        )
        
        # Create resource with OpenInference-specific attributes
        resource = Resource.create({
            "service.name": project,
            "model_id": project,
            "model_version": "production",
            "openinference.project.name": project,
        })
        
        # Create tracer provider with resource and BatchSpanProcessor
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument LangChain with OpenInference semantic conventions
        LangChainInstrumentor().instrument(
            tracer_provider=tracer_provider,
            skip_dep_check=True
        )
        
        _arize_ax_initialized = True
        os.environ['_ARIZE_AX_INITIALIZED'] = 'true'
        
        print(f"   ✅ Arize AX initialized with BatchSpanProcessor + OpenInference")
        print(f"   Model ID: {project}")
        print(f"   Endpoint: {arize_endpoint}")
        return True
    except Exception as e:
        print(f"   ⚠️  Arize AX pre-init failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def initialize_otlp_tracing():
    """
    Initialize OTLP tracing based on user preference.
    
    This should be called BEFORE any LangChain imports to ensure
    OpenTelemetry instrumentation is set up correctly.
    
    Returns:
        str: The platform that was initialized ("phoenix", "arize_ax", or "none")
    """
    # Only initialize once
    if os.getenv('_OTLP_INITIALIZED'):
        # Already initialized, return what's active
        if _phoenix_initialized:
            return "phoenix"
        elif _arize_ax_initialized:
            return "arize_ax"
        return "none"
    
    # Get preference
    preference = _get_otlp_preference()
    
    # Initialize based on preference
    if preference == "phoenix":
        if _initialize_phoenix_otlp():
            os.environ['_OTLP_INITIALIZED'] = 'true'
            return "phoenix"
    elif preference == "arize ax":
        if _initialize_arize_ax_otlp():
            os.environ['_OTLP_INITIALIZED'] = 'true'
            return "arize_ax"
    
    os.environ['_OTLP_INITIALIZED'] = 'true'
    return "none"


# Auto-initialize if this module is imported
# This ensures OTLP tracing is set up before LangChain imports
if __name__ != "__main__":
    # Only auto-initialize if environment is loaded
    if os.getenv("GALILEO_API_KEY"):
        initialized_platform = initialize_otlp_tracing()
        if initialized_platform != "none":
            print(f"   ℹ️  OTLP tracing auto-initialized: {initialized_platform}")


