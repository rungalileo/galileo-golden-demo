"""LangGraph RAG Integration

Domain-scoped RAG retrieval for LangGraph agents.

This implementation uses PostgreSQL + pgvector via langchain-postgres (PGVector)
for vector storage, and supports both local (Ollama) and hosted (OpenAI) chat
providers.
"""

from __future__ import annotations

import os
from typing import Optional

from langsmith import Client as LangSmithClient

from langchain_core.tools import tool
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from domain_manager import DomainManager
from setup_env import setup_environment

from helpers.llm_utils import (
    get_chat_model,
    get_default_chat_model,
    get_domain_embedding_model,
    get_embeddings,
    get_llm_provider,
)
from helpers.pgvector_utils import VECTOR_INDEX_ENV, collection_exists, create_pgvector_store

# Global cache for RAG instances
_rag_cache: dict[str, "DomainRAGSystem"] = {}


class DomainRAGSystem:
    """RAG system for a specific domain with eager initialization."""

    def __init__(self, domain_name: str, top_k: int = 5, model_name: Optional[str] = None):
        self.domain_name = domain_name
        self.top_k = top_k
        self.model_name = model_name
        self.retrieval_chain = None
        self._initialized = False

        # Initialize immediately when created
        self.initialize()

    def initialize(self) -> None:
        if self._initialized:
            return

        try:
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(self.domain_name)

            rag_config = domain_config.config.get("rag", {})
            vectorstore_config = domain_config.config.get("vectorstore", {})
            model_config = domain_config.config.get("model", {})

            provider = get_llm_provider()
            embedding_model = get_domain_embedding_model(vectorstore_config)

            llm_model = (
                self.model_name
                or (
                    model_config.get("hosted_default_model")
                    if provider == "hosted"
                    else model_config.get("default_model")
                )
                or model_config.get("default_model")
                or model_config.get("model_name", get_default_chat_model(provider=provider))
            )

            # Ensure env vars (POSTGRES_*, GALILEO_PROJECT, etc.) are loaded.
            setup_environment(self.domain_name, domain_config.config)

            environment = VECTOR_INDEX_ENV

            if not os.environ.get("POSTGRES_PASSWORD"):
                raise ValueError(
                    "POSTGRES_PASSWORD not found. Please add it to .streamlit/secrets.toml"
                )

            if not collection_exists(self.domain_name, environment):
                collection_name = f"{self.domain_name}_{environment}_index"
                raise ValueError(
                    f"PostgreSQL collection not found: {collection_name}. "
                    f"Please run: python helpers/setup_vectordb.py {self.domain_name} local"
                )

            embeddings = get_embeddings(embedding_model, provider="local")
            vector_store, _ = create_pgvector_store(embeddings, self.domain_name, environment)
            retriever = vector_store.as_retriever(search_kwargs={"k": self.top_k})

            llm = get_chat_model(
                llm_model,
                temperature=0.1,
                name=f"{self.domain_name.title()} RAG Assistant",
                provider=provider,
            )

            # Pull prompt from LangSmith.
            retrieval_qa_chat_prompt = LangSmithClient().pull_prompt(
                "langchain-ai/retrieval-qa-chat",
                dangerously_pull_public_prompt=True,
            )

            combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
            self.retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)

            self._initialized = True
            print(
                f"✅ RAG system initialized for domain '{self.domain_name}' (model: {llm_model}, top_k: {self.top_k})"
            )

        except Exception as exc:
            print(f"❌ Error initializing RAG system for domain '{self.domain_name}': {exc}")
            import traceback

            traceback.print_exc()
            self._initialized = False

    def search(self, query: str) -> str:
        if not self.retrieval_chain:
            return (
                f"❌ RAG system not initialized for domain '{self.domain_name}'. "
                "Please check your vector database setup."
            )

        try:
            result = self.retrieval_chain.invoke({"input": query})
            return result.get("answer", "")
        except Exception as exc:
            return f"❌ Error during RAG search for domain '{self.domain_name}': {exc}"


def get_domain_rag_system(
    domain_name: str,
    top_k: int | None = None,
    model_name: Optional[str] = None,
) -> DomainRAGSystem:
    """Get or create a cached RAG system instance."""

    if top_k is None:
        try:
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(domain_name)
            rag_config = domain_config.config.get("rag", {})
            top_k = rag_config.get("top_k", 5)
        except Exception:
            top_k = 5

    cache_key = f"{domain_name}_{top_k}_{model_name or 'default'}_{get_llm_provider()}"
    if cache_key not in _rag_cache:
        _rag_cache[cache_key] = DomainRAGSystem(domain_name, top_k, model_name=model_name)
    return _rag_cache[cache_key]


def create_domain_rag_tool(
    domain_name: str,
    top_k: int | None = None,
    model_name: Optional[str] = None,
):
    """Create a LangChain @tool wrapper around the domain's retrieval chain."""

    rag_system = get_domain_rag_system(domain_name, top_k, model_name=model_name)

    @tool
    def retrieve_documents_chain(query: str) -> str:
        """Retrieve information related to a query from the knowledge base."""
        return rag_system.search(query)

    retrieve_documents_chain.name = f"retrieve_{domain_name}_documents"
    retrieve_documents_chain.description = f"Retrieve information from the {domain_name} knowledge base"

    return retrieve_documents_chain
