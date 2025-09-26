"""
LangGraph RAG Integration
Handles RAG retrieval logic for LangGraph agents using LangChain's retrieval chain pattern.
"""
import os
from pathlib import Path
from typing import Optional
from langchain import hub
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.tools import tool
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from domain_manager import DomainManager


# Global cache for RAG instances
_rag_cache = {}


class DomainRAGSystem:
    """RAG system for a specific domain with lazy initialization"""
    
    def __init__(self, domain_name: str, top_k: int = 5):
        self.domain_name = domain_name
        self.top_k = top_k
        self.retrieval_chain = None
        self._initialized = False
        
    def initialize(self):
        """Initialize the RAG system with lazy loading"""
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
            
            embedding_model = vectorstore_config.get("embedding_model", "text-embedding-3-large")
            llm_model = model_config.get("model_name", "gpt-4o")
            
            # Check if vector database exists
            domain_path = Path("domains") / self.domain_name
            vector_db_dir = domain_path / "chroma_db"
            
            if not vector_db_dir.exists():
                raise ValueError(f"Vector database not found for domain '{self.domain_name}' at {vector_db_dir}. Please run: python helpers/setup_vectordb.py {self.domain_name}")
            
            # Initialize embeddings and vector store
            embeddings = OpenAIEmbeddings(model=embedding_model)
            collection_name = f"{self.domain_name}_collection"
            
            vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(vector_db_dir),
            )
            
            # Create retriever
            retriever = vector_store.as_retriever(search_kwargs={"k": self.top_k})
            
            # Create LLM for the chain
            llm = ChatOpenAI(
                model=llm_model,
                temperature=0.1,
                name=f"{self.domain_name.title()} RAG Assistant"
            )
            
            # Create prompt for the chain
            retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
            
            # Create the retrieval chain
            combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
            self.retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
            
            self._initialized = True
            print(f"✅ RAG system initialized for domain '{self.domain_name}'")
            
        except Exception as e:
            print(f"❌ Error initializing RAG system for domain '{self.domain_name}': {e}")
            import traceback
            traceback.print_exc()
            self._initialized = False
            
    def search(self, query: str) -> str:
        """Search the domain's knowledge base"""
        # Lazy initialization - only initialize when first used
        if not self._initialized:
            self.initialize()
            
        if not self.retrieval_chain:
            return f"❌ RAG system not initialized for domain '{self.domain_name}'. Please check your vector database setup."
            
        try:
            result = self.retrieval_chain.invoke({"input": query})
            return result["answer"]
        except Exception as e:
            return f"❌ Error during RAG search for domain '{self.domain_name}': {str(e)}"


def get_domain_rag_system(domain_name: str, top_k: int = None) -> DomainRAGSystem:
    """Get or create a RAG system instance with caching"""
    # Get top_k from domain config if not specified
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
    @tool
    def retrieve_documents_chain(query: str) -> str:
        """Retrieve information related to a query from the knowledge base using LangChain retrieval chain."""
        return rag_system.search(query)
    
    # Set the tool name and description
    retrieve_documents_chain.name = f"retrieve_{domain_name}_documents"
    retrieve_documents_chain.description = f"Retrieve information from the {domain_name} knowledge base"
    
    return retrieve_documents_chain
