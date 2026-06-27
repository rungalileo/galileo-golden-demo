"""
LLM and embedding helpers for OpenAI inference.
"""
import os
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

DEFAULT_CHAT_MODEL = "gpt-4o"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"


def get_default_chat_model() -> str:
    """Return the default OpenAI chat model."""
    return os.environ.get("OPENAI_DEFAULT_CHAT_MODEL", DEFAULT_CHAT_MODEL)


def get_default_embedding_model() -> str:
    """Return the default OpenAI embedding model."""
    return os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def get_domain_embedding_model(vectorstore_config: dict) -> str:
    """Return the embedding model used for pgvector retrieval."""
    return vectorstore_config.get("embedding_model") or get_default_embedding_model()


def ensure_openai_api_key() -> str:
    """Return OPENAI_API_KEY or raise with setup instructions."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add openai_api_key to .streamlit/secrets.toml."
        )
    return api_key


def get_domain_chat_model(domain_config: dict, *, override: Optional[str] = None) -> str:
    """Resolve the chat model for a domain."""
    if override:
        return override
    model_cfg = domain_config.get("model", {})
    return (
        model_cfg.get("hosted_default_model")
        or model_cfg.get("default_model")
        or model_cfg.get("model_name")
        or get_default_chat_model()
    )


def get_chat_model(
    model: str,
    *,
    temperature: float = 0.1,
    name: Optional[str] = None,
) -> BaseChatModel:
    """Create an OpenAI chat model."""
    from langchain_openai import ChatOpenAI

    ensure_openai_api_key()
    kwargs = {
        "model": model,
        "temperature": temperature,
    }
    if name:
        kwargs["name"] = name
    return ChatOpenAI(**kwargs)


def get_embeddings(model: Optional[str] = None) -> Embeddings:
    """Create OpenAI embeddings."""
    from langchain_openai import OpenAIEmbeddings

    ensure_openai_api_key()
    embedding_model = model or get_default_embedding_model()
    return OpenAIEmbeddings(model=embedding_model)
