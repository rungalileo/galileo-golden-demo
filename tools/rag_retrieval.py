"""
Global RAG Retrieval Functions
Designt to work across all domains by loading domain-specific vector databases.

This is a general retrieval tool that hits Chroma using LangChain's vectorstore abstraction.
Currently, logging for retrieval spans is missing and needs to be resolved in future iterations.

For now, since we primarily use the LangGraph agent, all retrieval logic with proper
Galileo logging happens in agent_frameworks/langgraph/langgraph_rag.py which uses
LangChain's retrieval chain pattern that should work with GalileoCallback.

"""
import os
from pathlib import Path
from typing import List, Tuple, Optional
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from domain_manager import DomainManager
import json


class RAGRetriever:
    """
    Global RAG retriever that works with domain-specific vector databases.
    """
    
    def __init__(self):
        self.domain_manager = DomainManager()
        self._vector_stores = {}  # Cache loaded vector stores
        self._embeddings = {}     # Cache embedding models
    
    def _get_embeddings(self, embedding_model: str) -> OpenAIEmbeddings:
        """Get or create embeddings model (with caching)"""
        if embedding_model not in self._embeddings:
            self._embeddings[embedding_model] = OpenAIEmbeddings(model=embedding_model)
        return self._embeddings[embedding_model]
    
    def _get_vector_store(self, domain_name: str) -> Optional[Chroma]:
        """Get or load vector store for a domain (with caching)"""
        if domain_name in self._vector_stores:
            return self._vector_stores[domain_name]
        
        try:
            # Load domain configuration
            domain_config = self.domain_manager.load_domain_config(domain_name)
            vectorstore_config = domain_config.config.get("vectorstore", {})
            
            # Get embedding model from config
            embedding_model = vectorstore_config.get("embedding_model", "text-embedding-3-large")
            embeddings = self._get_embeddings(embedding_model)
            
            # Build path to domain's vector database
            domain_path = Path("domains") / domain_name
            vector_db_dir = domain_path / "chroma_db"
            
            if not vector_db_dir.exists():
                print(f"⚠️  Vector database not found for domain '{domain_name}' at {vector_db_dir}")
                print(f"Run: python helpers/setup_vectordb.py {domain_name}")
                return None
            
            # Load the vector store
            collection_name = f"{domain_name}_collection"
            vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(vector_db_dir),
            )
            
            # Cache it
            self._vector_stores[domain_name] = vector_store
            return vector_store
            
        except Exception as e:
            print(f"❌ Error loading vector store for domain '{domain_name}': {e}")
            return None
    
    def retrieve_documents(self, domain_name: str, query: str, top_k: int = 5) -> Tuple[str, List]:
        """
        Retrieve relevant documents from domain's vector database.
        
        Args:
            domain_name: Name of the domain (e.g., 'finance')
            query: Search query
            top_k: Number of documents to retrieve
            
        Returns:
            Tuple of (formatted_content, raw_documents)
        """
        vector_store = self._get_vector_store(domain_name)
        if not vector_store:
            return f"❌ Vector database not available for domain '{domain_name}'", []
        
        try:
            # Retrieve documents
            retrieved_docs = vector_store.similarity_search(query, k=top_k)
            
            if not retrieved_docs:
                return f"No relevant documents found for query: '{query}'", []
            print(retrieved_docs)
            # Format the results
            formatted_content = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}"
                for doc in retrieved_docs
            ])
            print(formatted_content)
            
            return formatted_content, retrieved_docs
            
        except Exception as e:
            return f"❌ Error retrieving documents: {str(e)}", []


# Global retriever instance
_global_retriever = RAGRetriever()


def create_domain_retrieval_function(domain_name: str, top_k: int = None):
    """
    Create a domain-specific retrieval function.
    
    This creates a function that's bound to a specific domain, so the agent
    doesn't need to specify the domain name each time.
    
    Args:
        domain_name: Name of the domain
        top_k: Default number of documents to retrieve
        
    Returns:
        Pure function for domain-specific retrieval
    """
    # Get top_k from domain config if not specified
    if top_k is None:
        try:
            domain_manager = DomainManager()
            domain_config = domain_manager.load_domain_config(domain_name)
            rag_config = domain_config.config.get("rag", {})
            top_k = rag_config.get("top_k", 5)
        except:
            top_k = 5
    
    def retrieve_domain_documents(query: str) -> str:
        f"""
        Retrieve information related to a query from the {domain_name} knowledge base.
        
        This function searches through {domain_name}-specific documents that have been
        embedded in the vector database.
        
        Args:
            query: The search query or question
            
        Returns:
            Formatted string containing retrieved document content and metadata
        """
        content, docs = _global_retriever.retrieve_documents(domain_name, query, top_k)
        return content
    
    # Set function metadata for tool creation
    retrieve_domain_documents.__name__ = f"retrieve_{domain_name}_documents"
    retrieve_domain_documents.__doc__ = f"Retrieve information from the {domain_name} knowledge base"
    
    return retrieve_domain_documents


# Export for easy importing
__all__ = ['create_domain_retrieval_function', 'RAGRetriever']
