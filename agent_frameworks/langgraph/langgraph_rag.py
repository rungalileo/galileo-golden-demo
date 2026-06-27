"""
LangGraph RAG Integration
Handles RAG retrieval logic for LangGraph agents using LangChain's retrieval chain pattern.
Uses PostgreSQL with pgvector for vector storage.
"""
import asyncio
import os
from typing import Optional

from langchain_classic import hub
from langchain_core.tools import tool
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from helpers.llm_utils import (
    get_chat_model,
    get_default_chat_model,
    get_domain_embedding_model,
    get_embeddings,
)
from helpers.pgvector_utils import VECTOR_INDEX_ENV, collection_exists, create_pgvector_store
from domain_manager import DomainManager
from helpers.agent_control_helpers import domain_controlled_tool
from setup_env import setup_environment


# Global cache for RAG instances
_rag_cache = {}


class DomainRAGSystem:
    """RAG system for a specific domain with eager initialization"""
<<<<<<< Updated upstream
    
    def __init__(self, domain_name: str, top_k: int = 5):
        self.domain_name = domain_name
        self.top_k = top_k
=======

    def __init__(self, domain_name: str, top_k: int = 5, model_name: Optional[str] = None):
        self.domain_name = domain_name
        self.top_k = top_k
        self.model_name = model_name
>>>>>>> Stashed changes
        self.retrieval_chain = None
        self._initialized = False

        self.initialize()

    def initialize(self):
        """Initialize the RAG system with eager loading"""
        if self._initialized:
            return

        try:
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(self.domain_name)

            rag_config = domain_config.config.get("rag", {})
            vectorstore_config = domain_config.config.get("vectorstore", {})
            model_config = domain_config.config.get("model", {})
<<<<<<< Updated upstream
            
            embedding_model = vectorstore_config.get("embedding_model", "text-embedding-3-large")
            llm_model = model_config.get("model_name", "gpt-4o")
            
            # Initialize environment
            setup_environment()
            
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

            embedding_model = get_domain_embedding_model(vectorstore_config)
            llm_model = (
                self.model_name
                or model_config.get("hosted_default_model")
                or model_config.get("default_model")
                or model_config.get("model_name", get_default_chat_model())
            )

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

            embeddings = get_embeddings(embedding_model)
            vector_store, _ = create_pgvector_store(
                embeddings, self.domain_name, environment
>>>>>>> Stashed changes
            )

            retriever = vector_store.as_retriever(search_kwargs={"k": self.top_k})

            llm = get_chat_model(
                llm_model,
                temperature=0.1,
                name=f"{self.domain_name.title()} RAG Assistant",
            )

            retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
            combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
            self.retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)

            self._initialized = True
<<<<<<< Updated upstream
            print(f"✅ RAG system initialized for domain '{self.domain_name}'")
            
=======
            print(
                f"✅ RAG system initialized for domain '{self.domain_name}' (model: {llm_model})"
            )

>>>>>>> Stashed changes
        except Exception as e:
            print(f"❌ Error initializing RAG system for domain '{self.domain_name}': {e}")
            import traceback

            traceback.print_exc()
            self._initialized = False

    async def search(self, query: str) -> str:
        """Search the domain's knowledge base (no @control — applied at tool boundary)."""
        if not self.retrieval_chain:
            return (
                f"❌ RAG system not initialized for domain '{self.domain_name}'. "
                "Please check your vector database setup."
            )

        try:
            # PGVector is created in sync mode; use invoke (not ainvoke) in a thread
            # so we don't block the event loop or require async_mode on the store.
            result = await asyncio.to_thread(
                self.retrieval_chain.invoke, {"input": query}
            )
            # print(f" --> RAG search result: {result}")
            return result["answer"]
        except Exception as e:
            from helpers.pgvector_utils import format_embedding_dimension_error

            dimension_error = format_embedding_dimension_error(
                e, self.domain_name, embedding_model
            )
            if dimension_error:
                return f"❌ {dimension_error}"
            return f"❌ Error during RAG search for domain '{self.domain_name}': {str(e)}"


<<<<<<< Updated upstream
def get_domain_rag_system(domain_name: str, top_k: int = None) -> DomainRAGSystem:
    """Get or create a RAG system instance with caching"""
    # Get top_k from domain config if not specified
=======
def get_domain_rag_system(
    domain_name: str,
    top_k: int = None,
    model_name: Optional[str] = None,
) -> DomainRAGSystem:
    """Get or create a RAG system instance with caching (per domain, top_k, and model)."""
>>>>>>> Stashed changes
    if top_k is None:
        try:
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(domain_name)
            rag_config = domain_config.config.get("rag", {})
            top_k = rag_config.get("top_k", 5)
        except:
            top_k = 5
    
    cache_key = f"{domain_name}_{top_k}"
    if cache_key not in _rag_cache:
        _rag_cache[cache_key] = DomainRAGSystem(domain_name, top_k)
    return _rag_cache[cache_key]


def create_domain_rag_tool(domain_name: str, top_k: int = None):
    """
    Create a LangChain retrieval chain tool that works with GalileoCallback automatically.
<<<<<<< Updated upstream
    
    This uses LangChain's built-in retrieval chain with lazy initialization and caching,
    which should automatically work with the GalileoCallback for logging retrieval steps.
    
    Args:
        domain_name: Name of the domain
        top_k: Default number of documents to retrieve
        
    Returns:
        LangChain tool that uses retrieval chain
    """
    # Get the RAG system instance (cached and lazy-loaded)
    rag_system = get_domain_rag_system(domain_name, top_k)
    
    # Create the tool using LangChain's @tool decorator
=======

    Args:
        domain_name: Name of the domain
        top_k: Default number of documents to retrieve
        model_name: Optional model override (e.g. from sidebar)

    Returns:
        LangChain tool that uses retrieval chain
    """
    rag_system = get_domain_rag_system(domain_name, top_k, model_name=model_name)

    def _resolve_galileo_logger(*_args, **_kwargs):
        try:
            import streamlit as st

            return st.session_state.get(f"galileo_logger_{domain_name}") or st.session_state.get(
                "galileo_logger"
            )
        except Exception:
            return None

>>>>>>> Stashed changes
    @tool
    @domain_controlled_tool(step_name="retrieval_step", resolve_logger=_resolve_galileo_logger)
    async def retrieve_documents_chain(query: str) -> str:
        """Retrieve information related to a query from the knowledge base using LangChain retrieval chain."""
        return await rag_system.search(query)

    retrieve_documents_chain.name = f"retrieve_{domain_name}_documents"
<<<<<<< Updated upstream
    retrieve_documents_chain.description = f"Retrieve information from the {domain_name} knowledge base"
    
    return retrieve_documents_chain
=======
    retrieve_documents_chain.description = (
        f"Retrieve information from the {domain_name} knowledge base"
    )

    return retrieve_documents_chain
>>>>>>> Stashed changes
