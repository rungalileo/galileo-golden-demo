"""
LangGraph RAG Integration
Handles RAG retrieval logic for LangGraph agents using LangChain's retrieval chain pattern.
Uses Pinecone for vector storage with environment-based configuration.
"""
import os
from pathlib import Path
from typing import Optional
<<<<<<< Updated upstream
from langsmith import Client as LangSmithClient
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.tools import tool
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from pinecone import Pinecone
from domain_manager import DomainManager
=======

from langchain_classic import hub
from langchain_core.tools import tool
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from helpers.llm_utils import (
    get_chat_model,
    get_default_chat_model,
    get_domain_embedding_model,
    get_embeddings,
    get_llm_provider,
)
from helpers.pgvector_utils import VECTOR_INDEX_ENV, collection_exists, create_pgvector_store
from domain_manager import DomainManager
from helpers.agent_control_helpers import domain_controlled_tool
>>>>>>> Stashed changes
from setup_env import setup_environment


# Global cache for RAG instances
_rag_cache = {}


class DomainRAGSystem:
    """RAG system for a specific domain with eager initialization"""
    
    def __init__(self, domain_name: str, top_k: int = 5, model_name: Optional[str] = None):
        self.domain_name = domain_name
        self.top_k = top_k
        self.model_name = model_name  # Use same model as main agent when provided
        self.retrieval_chain = None
        self._initialized = False
        self._pinecone_client = None
        
        # Initialize immediately when created
        self.initialize()
        
    def initialize(self):
        """Initialize the RAG system with eager loading"""
        if self._initialized:
            return
            
        try:
            # Get domain config
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(self.domain_name)
            
            # Get config values
            rag_config = domain_config.config.get("rag", {})
            vectorstore_config = domain_config.config.get("vectorstore", {})
            model_config = domain_config.config.get("model", {})
<<<<<<< Updated upstream
            
            embedding_model = vectorstore_config.get("embedding_model", "text-embedding-3-large")
            # Use passed model (from main agent selection) or domain default so RAG matches main assistant
=======

            provider = get_llm_provider()
            embedding_model = get_domain_embedding_model(vectorstore_config)
>>>>>>> Stashed changes
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
            
            # Initialize environment with domain-specific settings
            setup_environment(self.domain_name, domain_config.config)
<<<<<<< Updated upstream
            
            # Get environment and API key
            environment = os.environ.get("ENVIRONMENT", "local")
            
            if environment == "local":
                api_key = os.environ.get("PINECONE_API_KEY_LOCAL")
            elif environment == "hosted":
                api_key = os.environ.get("PINECONE_API_KEY_HOSTED")
            else:
                raise ValueError(f"Invalid environment: {environment}. Must be 'local' or 'hosted'")
            
            if not api_key:
                raise ValueError(f"Pinecone API key not found for environment '{environment}'. Please add it to .streamlit/secrets.toml")
            
            # Initialize Pinecone client
            if self._pinecone_client is None:
                self._pinecone_client = Pinecone(api_key=api_key)
            
            # Create index name based on domain and environment
            index_name = f"{self.domain_name}-{environment}-index"
            
            # Check if index exists
            if not self._pinecone_client.has_index(index_name):
                raise ValueError(f"Pinecone index not found: {index_name}. Please run: python helpers/setup_vectordb.py {self.domain_name} {environment}")
            
            # Get the index
            index = self._pinecone_client.Index(index_name)
            
            # Initialize embeddings and vector store
            embeddings = OpenAIEmbeddings(model=embedding_model)
            
            vector_store = PineconeVectorStore(index=index, embedding=embeddings)
            
            # Create retriever
            retriever = vector_store.as_retriever(search_kwargs={"k": self.top_k})
            
            # Create LLM for the chain
            llm = ChatOpenAI(
                model=llm_model,
                temperature=0.1,
                name=f"{self.domain_name.title()} RAG Assistant"
=======

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
            vector_store, _ = create_pgvector_store(
                embeddings, self.domain_name, environment
            )

            retriever = vector_store.as_retriever(search_kwargs={"k": self.top_k})

            llm = get_chat_model(
                llm_model,
                temperature=0.1,
                name=f"{self.domain_name.title()} RAG Assistant",
                provider=provider,
>>>>>>> Stashed changes
            )
            
            # Create prompt for the chain
            # Pull via langsmith directly: the langchain_classic.hub wrapper is
            # deprecated and doesn't forward `dangerously_pull_public_prompt`,
            # which newer langsmith requires for public prompts. We trust this
            # one (official langchain-ai org).
            retrieval_qa_chat_prompt = LangSmithClient().pull_prompt(
                "langchain-ai/retrieval-qa-chat",
                dangerously_pull_public_prompt=True,
            )
            
            # Create the retrieval chain
            combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
            self.retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
            
            self._initialized = True
            print(f"✅ RAG system initialized for domain '{self.domain_name}' (model: {llm_model})")
            
        except Exception as e:
            print(f"❌ Error initializing RAG system for domain '{self.domain_name}': {e}")
            import traceback
            traceback.print_exc()
            self._initialized = False
            
    def search(self, query: str) -> str:
        """Search the domain's knowledge base"""
        # System should already be initialized at startup
        if not self.retrieval_chain:
            return f"❌ RAG system not initialized for domain '{self.domain_name}'. Please check your vector database setup."
            
        try:
            result = self.retrieval_chain.invoke({"input": query})
            return result["answer"]
        except Exception as e:
            return f"❌ Error during RAG search for domain '{self.domain_name}': {str(e)}"


def get_domain_rag_system(
    domain_name: str,
    top_k: int = None,
    model_name: Optional[str] = None,
) -> DomainRAGSystem:
    """Get or create a RAG system instance with caching (per domain, top_k, and model)."""
    # Get top_k from domain config if not specified
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
    top_k: int = None,
    model_name: Optional[str] = None,
):
    """
    Create a LangChain retrieval chain tool that works with GalileoCallback automatically.
    Uses the same LLM as the main agent when model_name is provided so nested RAG steps
    show the selected model in traces.

    Args:
        domain_name: Name of the domain
        top_k: Default number of documents to retrieve
        model_name: Optional model override (e.g. from sidebar); must match main agent for consistent traces.

    Returns:
        LangChain tool that uses retrieval chain
    """
    # Get the RAG system instance (cached per domain, top_k, and model)
    rag_system = get_domain_rag_system(domain_name, top_k, model_name=model_name)
    
    # Create the tool using LangChain's @tool decorator
    @tool
    def retrieve_documents_chain(query: str) -> str:
        """Retrieve information related to a query from the knowledge base using LangChain retrieval chain."""
        return rag_system.search(query)
    
    # Set the tool name and description
    retrieve_documents_chain.name = f"retrieve_{domain_name}_documents"
    retrieve_documents_chain.description = f"Retrieve information from the {domain_name} knowledge base"
    
    return retrieve_documents_chain
