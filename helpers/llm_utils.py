"""
LLM and embedding helpers for local (Ollama or MLX), hosted (OpenAI), and
AWS Bedrock inference.
"""
import json
import os
import importlib.util
import urllib.error
import urllib.request
import uuid
from contextvars import ContextVar, Token
from functools import lru_cache
from typing import Any, List, Literal, Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI

LLMProvider = Literal["local", "hosted", "bedrock"]
LocalLLMBackend = Literal["ollama", "mlx"]

DEFAULT_LOCAL_CHAT_MODEL = "gemma4"
DEFAULT_MLX_CHAT_MODEL = "mlx-community/gemma-4-26b-a4b-it-4bit"
DEFAULT_MLX_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_MLX_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_HOSTED_CHAT_MODEL = "gpt-4o"
DEFAULT_BEDROCK_CHAT_MODEL = "mistral.ministral-3-14b-instruct"
DEFAULT_LOCAL_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_HOSTED_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_BEDROCK_REGION = "us-east-1"
# nomic-embed-text (Ollama) produces 768-dim vectors; OpenAI must match for pgvector.
DEFAULT_EMBEDDING_DIMENSIONS = 768

_llm_provider_ctx: ContextVar[LLMProvider] = ContextVar("llm_provider", default="local")


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str):
    """Load and cache the local embedding model lazily."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class LocalSentenceTransformerEmbeddings(Embeddings):
    """LangChain embeddings backed by a local sentence-transformers model."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = _load_sentence_transformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        vector = self._model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vector.tolist()


def _parse_mlx_tool_calls(content: Any) -> List[dict]:
    """Normalize common JSON tool-call output emitted as plain message text.

    Some MLX models describe a requested tool as
    ``{"name": "...", "parameters": {...}}`` even when tools were supplied
    through the OpenAI-compatible request. LangGraph expects those calls in the
    structured ``AIMessage.tool_calls`` field.
    """
    if not isinstance(content, str):
        return []

    text = content.strip()
    if text.startswith("```") and text.endswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 : -3].strip()

    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []

    if isinstance(payload, dict) and isinstance(payload.get("tool_calls"), list):
        candidates = payload["tool_calls"]
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = [payload]

    tool_calls: List[dict] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return []
        function = candidate.get("function", candidate)
        if not isinstance(function, dict):
            return []

        name = function.get("name")
        arguments = function.get("parameters", function.get("arguments"))
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return []
        if not isinstance(name, str) or not name or not isinstance(arguments, dict):
            return []

        tool_calls.append(
            {
                "name": name,
                "args": arguments,
                "id": candidate.get("id") or f"call_{uuid.uuid4().hex}",
                "type": "tool_call",
            }
        )
    return tool_calls


class MLXChatOpenAI(ChatOpenAI):
    """ChatOpenAI adapter with a narrow fallback for MLX JSON tool calls."""

    @staticmethod
    def _normalize_tool_calls(result: ChatResult) -> ChatResult:
        for generation in result.generations:
            message = generation.message
            if not isinstance(message, AIMessage) or message.tool_calls:
                continue

            parsed_calls = _parse_mlx_tool_calls(message.content)
            if not parsed_calls:
                continue

            message.tool_calls = parsed_calls
            message.additional_kwargs["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["args"]),
                    },
                }
                for call in parsed_calls
            ]
            message.content = ""
        return result

    def _generate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        result = super()._generate(messages, stop, run_manager, **kwargs)
        return self._normalize_tool_calls(result) if kwargs.get("tools") else result

    async def _agenerate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        result = await super()._agenerate(messages, stop, run_manager, **kwargs)
        return self._normalize_tool_calls(result) if kwargs.get("tools") else result


def set_llm_provider(provider: LLMProvider) -> Token:
    """Set the active LLM provider for the current async/task context."""
    return _llm_provider_ctx.set(provider)


def reset_llm_provider(token: Token) -> None:
    """Restore the previous LLM provider context."""
    _llm_provider_ctx.reset(token)


def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider ('local', 'hosted', or 'bedrock')."""
    return _llm_provider_ctx.get()


def get_local_llm_backend() -> LocalLLMBackend:
    """Return the configured local chat backend.

    Ollama remains the default for backward compatibility. Setting
    ``local_llm_backend = "mlx"`` in secrets.toml opts into the
    OpenAI-compatible MLX-LM server.
    """
    backend = os.environ.get("LOCAL_LLM_BACKEND", "ollama").strip().lower()
    return "mlx" if backend == "mlx" else "ollama"


def get_local_provider_label() -> str:
    """Return the user-facing label for the active local chat backend."""
    return "Local (MLX)" if get_local_llm_backend() == "mlx" else "Local (Ollama)"


def get_ollama_base_url() -> str:
    """Return the Ollama server URL (default: http://localhost:11434)."""
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def get_mlx_base_url() -> str:
    """Return the OpenAI-compatible MLX-LM base URL."""
    return os.environ.get("MLX_BASE_URL", DEFAULT_MLX_BASE_URL).rstrip("/")


def get_mlx_api_key() -> str:
    """Return the placeholder API key accepted by the local MLX-LM server."""
    return os.environ.get("MLX_API_KEY", "local")


def get_bedrock_region() -> str:
    """Return the AWS region for Bedrock calls (default: us-east-1)."""
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("BEDROCK_REGION")
        or DEFAULT_BEDROCK_REGION
    )


def message_content_to_text(content) -> str:
    """Flatten a LangChain message's ``.content`` to plain text.

    ChatOpenAI / ChatOllama return ``.content`` as a ``str``, but
    ChatBedrockConverse (and other Bedrock Converse / Anthropic-style models)
    return a list of content blocks, e.g. ``[{"type": "text", "text": "..."}]``.
    Callers that expect a string (UI rendering, tracing, history) must normalize
    through this so Bedrock responses don't break ``str`` operations like
    ``.replace()``.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def get_default_chat_model(*, provider: Optional[LLMProvider] = None) -> str:
    """Return the default chat model for the given or active provider."""
    resolved = provider or get_llm_provider()
    if resolved == "hosted":
        return os.environ.get("OPENAI_DEFAULT_CHAT_MODEL", DEFAULT_HOSTED_CHAT_MODEL)
    if resolved == "bedrock":
        return os.environ.get("BEDROCK_DEFAULT_CHAT_MODEL", DEFAULT_BEDROCK_CHAT_MODEL)
    if get_local_llm_backend() == "mlx":
        return os.environ.get("MLX_DEFAULT_CHAT_MODEL", DEFAULT_MLX_CHAT_MODEL)
    return os.environ.get("OLLAMA_DEFAULT_CHAT_MODEL", DEFAULT_LOCAL_CHAT_MODEL)


def get_embedding_dimensions() -> int:
    """Return embedding vector size for the single pgvector index."""
    raw = os.environ.get(
        "OPENAI_EMBEDDING_DIMENSIONS",
        os.environ.get("EMBEDDING_DIMENSIONS", str(DEFAULT_EMBEDDING_DIMENSIONS)),
    )
    return int(raw)


def is_ollama_available(*, timeout: float = 3) -> bool:
    """Return True if the Ollama server responds at the configured base URL."""
    url = f"{get_ollama_base_url().rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _mlx_request(path: str, *, timeout: float = 3):
    """Open an authenticated request against the local MLX-LM API."""
    request = urllib.request.Request(
        f"{get_mlx_base_url()}/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {get_mlx_api_key()}"},
    )
    return urllib.request.urlopen(request, timeout=timeout)


def is_mlx_available(*, timeout: float = 3) -> bool:
    """Return True if the configured MLX-LM server exposes its model list."""
    try:
        with _mlx_request("models", timeout=timeout) as response:
            response.read()
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def get_configured_embedding_provider() -> Optional[LLMProvider]:
    """Optional embedding-provider override from config (EMBEDDING_PROVIDER).

    Returns None when unset, in which case the embedding provider follows the
    chat provider selected in the UI. Set it only to pin RAG to one backend
    regardless of the chat toggle.
    """
    raw = os.environ.get("EMBEDDING_PROVIDER", "").strip().lower()
    if raw in ("hosted", "openai"):
        return "hosted"
    if raw in ("bedrock", "aws"):
        return "bedrock"
    if raw in ("local", "ollama"):
        return "local"
    return None


# Placeholder values shipped in secrets.toml.template — treated as "not set".
_OPENAI_KEY_PLACEHOLDERS = {
    "",
    "...",
    "sk-...",
    "your_openai_api_key_here",
    "your-openai-api-key",
    "your-openai-api-key-here",
}


def openai_api_key_configured() -> bool:
    """True only if a real OpenAI key is set (not empty and not a template placeholder)."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key in _OPENAI_KEY_PLACEHOLDERS:
        return False
    if "..." in key:  # any leftover ellipsis from the template
        return False
    return bool(key)


def bedrock_configured() -> bool:
    """True if a Bedrock API key (bearer token) is set (a region always resolves)."""
    return bool(os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip())


def ensure_bedrock_credentials() -> None:
    """Raise with setup instructions if the Bedrock bearer token is not configured."""
    if not bedrock_configured():
        raise ValueError(
            "AWS_BEARER_TOKEN_BEDROCK is not set. Add a real bedrock_api_key to "
            ".streamlit/secrets.toml (and optionally aws_region, default us-east-1) "
            "to use the Bedrock (AWS) provider."
        )


def ollama_configured() -> bool:
    """True if an Ollama base URL is configured (ollama_base_url in secrets.toml)."""
    return bool(os.environ.get("OLLAMA_BASE_URL", "").strip())


def mlx_configured() -> bool:
    """True if an MLX-LM base URL is configured in secrets.toml."""
    return bool(os.environ.get("MLX_BASE_URL", "").strip())


# Provider ordering for the UI. Display order is how options appear in the
# radio; priority order decides which configured provider is preselected.
_PROVIDER_DISPLAY_ORDER: tuple = ("local", "hosted", "bedrock")
_PROVIDER_PRIORITY: tuple = ("local", "bedrock", "hosted")


def provider_configured(provider: LLMProvider) -> bool:
    """True if the given provider's credential is set in secrets.toml.

    "Configured" means the credential is present — it does NOT check live
    reachability (e.g. whether the Ollama server is actually running).
    """
    if provider == "hosted":
        return openai_api_key_configured()
    if provider == "bedrock":
        return bedrock_configured()
    if get_local_llm_backend() == "mlx":
        return mlx_configured()
    return ollama_configured()


def configured_providers() -> List[LLMProvider]:
    """Return providers whose credential is set, in UI display order."""
    return [p for p in _PROVIDER_DISPLAY_ORDER if provider_configured(p)]


def default_provider() -> Optional[LLMProvider]:
    """Return the provider to preselect: first configured in priority order.

    Priority is local > bedrock > hosted. Returns None if none are configured.
    """
    for provider in _PROVIDER_PRIORITY:
        if provider_configured(provider):
            return provider
    return None


def embedding_backend_available(provider: LLMProvider) -> bool:
    """Return True if the given embedding backend can actually be used right now.

    Checks live availability at call time. MLX-LM does not expose embeddings,
    so the MLX local backend uses an in-process sentence-transformers model.
    Ollama configurations keep using Ollama embeddings unchanged.
    """
    if provider == "hosted":
        return openai_api_key_configured()
    if provider == "bedrock":
        return bedrock_configured()
    if get_local_llm_backend() == "mlx":
        return importlib.util.find_spec("sentence_transformers") is not None
    return is_ollama_available()


# Order in which to try other backends when the desired one is unavailable.
_EMBEDDING_FALLBACK_ORDER: tuple[LLMProvider, ...] = ("local", "hosted", "bedrock")


def resolve_embedding_provider(
    provider: Optional[LLMProvider] = None,
) -> LLMProvider:
    """
    Resolve the *desired* embedding backend for RAG.

    Follows the chat provider selected in the UI (get_llm_provider()) so RAG
    embeds queries with the same provider as chat. This is safe because the
    setup script builds a separate pgvector index per provider
    ({domain}_local_index for Ollama, {domain}_hosted_index for OpenAI,
    {domain}_bedrock_index for Bedrock) and each index is only ever queried
    with the backend that built it — so flipping the UI toggle just switches
    which prebuilt index is searched, never compares vectors across
    incompatible embedding spaces.

    Precedence: explicit `provider` arg > EMBEDDING_PROVIDER override > chat
    radio (get_llm_provider()). If the desired backend's service is
    unreachable, falls back to the first other reachable backend so RAG keeps
    working.
    """
    requested: LLMProvider = provider or get_configured_embedding_provider() or get_llm_provider()

    if embedding_backend_available(requested):
        return requested

    for fallback in _EMBEDDING_FALLBACK_ORDER:
        if fallback == requested:
            continue
        if embedding_backend_available(fallback):
            print(
                f"ℹ️  '{requested}' embedding backend unavailable; "
                f"falling back to '{fallback}'."
            )
            return fallback

    raise ConnectionError(
        "No embedding backend available. For MLX, install sentence-transformers; "
        f"for Ollama, start it at {get_ollama_base_url()}; otherwise set "
        "openai_api_key or bedrock_api_key in .streamlit/secrets.toml."
    )


def get_domain_embedding_model(
    vectorstore_config: dict,
    *,
    provider: Optional[LLMProvider] = None,
) -> str:
    """Return the embedding model for the active or specified provider."""
    resolved = resolve_embedding_provider(provider)
    if resolved == "hosted":
        return (
            vectorstore_config.get("hosted_embedding_model")
            or os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_HOSTED_EMBEDDING_MODEL)
        )
    if resolved == "bedrock":
        return (
            vectorstore_config.get("bedrock_embedding_model")
            or os.environ.get("BEDROCK_EMBEDDING_MODEL", DEFAULT_BEDROCK_EMBEDDING_MODEL)
        )
    if get_local_llm_backend() == "mlx":
        return (
            vectorstore_config.get("mlx_embedding_model")
            or os.environ.get("MLX_EMBEDDING_MODEL", DEFAULT_MLX_EMBEDDING_MODEL)
        )
    return (
        vectorstore_config.get("embedding_model")
        or os.environ.get("OLLAMA_EMBEDDING_MODEL", DEFAULT_LOCAL_EMBEDDING_MODEL)
    )


def ensure_openai_api_key() -> str:
    """Return OPENAI_API_KEY or raise with setup instructions."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_api_key_configured():
        raise ValueError(
            "OPENAI_API_KEY is not set (or still a placeholder). Add a real "
            "openai_api_key to .streamlit/secrets.toml to use the Hosted (OpenAI) provider."
        )
    return api_key


def list_ollama_models() -> List[str]:
    """Return model base names available in the local Ollama instance."""
    url = f"{get_ollama_base_url().rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        raise ConnectionError(
            f"Cannot reach Ollama at {get_ollama_base_url()}. "
            "Make sure Ollama is running."
        ) from exc

    return [
        model.get("name", "").split(":")[0]
        for model in payload.get("models", [])
        if model.get("name")
    ]


def list_mlx_models() -> List[str]:
    """Return model IDs exposed by the configured MLX-LM server."""
    try:
        with _mlx_request("models", timeout=10) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectionError(
            f"Cannot reach MLX-LM at {get_mlx_base_url()}. "
            "Make sure the MLX-LM server is running."
        ) from exc

    return [
        model.get("id", "")
        for model in payload.get("data", [])
        if model.get("id")
    ]


def list_local_models() -> List[str]:
    """Return models from the configured local chat backend."""
    if get_local_llm_backend() == "mlx":
        return list_mlx_models()
    return list_ollama_models()


def ensure_ollama_model_available(model: str, *, model_kind: str = "model") -> None:
    """Raise a clear error if the requested Ollama model is not installed locally."""
    installed_models = set(list_ollama_models())
    if model not in installed_models:
        raise ValueError(
            f'Ollama {model_kind} "{model}" is not installed. '
            f"Pull it with:\n\n  ollama pull {model}\n\n"
            f"Installed models: {', '.join(sorted(installed_models)) or '(none)'}"
        )


def get_domain_chat_model(domain_config: dict, *, override: Optional[str] = None) -> str:
    """Resolve the chat model for a domain using the active provider."""
    if override:
        return override
    provider = get_llm_provider()
    model_cfg = domain_config.get("model", {})
    if provider == "hosted":
        return (
            model_cfg.get("hosted_default_model")
            or get_default_chat_model(provider="hosted")
        )
    if provider == "bedrock":
        return (
            model_cfg.get("bedrock_default_model")
            or get_default_chat_model(provider="bedrock")
        )
    if get_local_llm_backend() == "mlx":
        return (
            model_cfg.get("mlx_default_model")
            or get_default_chat_model(provider="local")
        )
    return model_cfg.get("default_model") or get_default_chat_model(provider="local")


def get_chat_model(
    model: str,
    *,
    temperature: float = 0.1,
    name: Optional[str] = None,
    num_ctx: int = 8192,
    provider: Optional[LLMProvider] = None,
) -> BaseChatModel:
    """Create a chat model for the active or specified provider."""
    resolved_provider = provider or get_llm_provider()
    if resolved_provider == "hosted":
        ensure_openai_api_key()
        kwargs = {
            "model": model,
            "temperature": temperature,
        }
        if name:
            kwargs["name"] = name
        return ChatOpenAI(**kwargs)

    if resolved_provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        ensure_bedrock_credentials()
        kwargs = {
            "model": model,
            "temperature": temperature,
            "region_name": get_bedrock_region(),
        }
        if name:
            kwargs["name"] = name
        return ChatBedrockConverse(**kwargs)

    if get_local_llm_backend() == "mlx":
        if not is_mlx_available():
            raise ConnectionError(
                f"Cannot reach MLX-LM at {get_mlx_base_url()}. "
                "Make sure the MLX-LM server is running."
            )
        kwargs = {
            "model": model,
            "temperature": temperature,
            "base_url": get_mlx_base_url(),
            "api_key": get_mlx_api_key(),
        }
        # Gemma 4 reasons in a separate hidden channel by default. Disable that
        # channel for the demo so short response budgets are spent on visible
        # answers. Keep every other MLX model's request shape unchanged.
        if "gemma-4" in model.casefold():
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False}
            }
        if name:
            kwargs["name"] = name
        return MLXChatOpenAI(**kwargs)

    ensure_ollama_model_available(model, model_kind="chat model")
    kwargs = {
        "model": model,
        "temperature": temperature,
        "base_url": get_ollama_base_url(),
        "num_ctx": num_ctx,
    }
    if name:
        kwargs["name"] = name
    return ChatOllama(**kwargs)


def get_embeddings(
    model: Optional[str] = None,
    *,
    provider: Optional[LLMProvider] = None,
) -> Embeddings:
    """Create embeddings for the UI-selected provider (with Ollama→OpenAI fallback)."""
    resolved_provider = resolve_embedding_provider(provider)
    config: dict = {}
    embedding_model = model or get_domain_embedding_model(config, provider=resolved_provider)

    if resolved_provider == "hosted":
        from langchain_openai import OpenAIEmbeddings

        ensure_openai_api_key()
        kwargs = {"model": embedding_model}
        if embedding_model.startswith("text-embedding-3"):
            kwargs["dimensions"] = get_embedding_dimensions()
        return OpenAIEmbeddings(**kwargs)

    if resolved_provider == "bedrock":
        from langchain_aws import BedrockEmbeddings

        ensure_bedrock_credentials()
        # Bedrock embedding models emit their own native dimensionality (e.g.
        # Titan v2 = 1024); this index is a separate collection, so we do NOT
        # apply the OpenAI-only get_embedding_dimensions() (768) here.
        return BedrockEmbeddings(
            model_id=embedding_model,
            region_name=get_bedrock_region(),
        )

    if get_local_llm_backend() == "mlx":
        return LocalSentenceTransformerEmbeddings(embedding_model)

    ensure_ollama_model_available(embedding_model, model_kind="embedding model")
    return OllamaEmbeddings(model=embedding_model, base_url=get_ollama_base_url())


def get_index_embeddings(
    vectorstore_config: Optional[dict] = None,
    *,
    provider: Optional[LLMProvider] = None,
) -> Embeddings:
    """Embeddings for pgvector. Pass `provider` to pin the backend (e.g. the
    index the caller has already selected); otherwise follows the UI selection.
    """
    config = vectorstore_config or {}
    resolved = resolve_embedding_provider(provider)
    model = get_domain_embedding_model(config, provider=resolved)
    return get_embeddings(model, provider=resolved)


# Backward-compatible aliases
get_index_embedding_provider = get_llm_provider
get_vector_embeddings = get_index_embeddings
get_vector_embedding_provider = get_llm_provider


def get_index_embedding_model(vectorstore_config: Optional[dict] = None) -> str:
    """Return the embedding model for the UI-selected provider."""
    return get_domain_embedding_model(vectorstore_config or {})
