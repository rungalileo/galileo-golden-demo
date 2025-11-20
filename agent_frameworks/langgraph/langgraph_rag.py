"""
LangGraph RAG Integration
Handles RAG retrieval logic for LangGraph agents using LangChain's retrieval chain pattern.
Uses Pinecone for vector storage with environment-based configuration.
"""
import os
from pathlib import Path
from typing import Optional
try:
    from langchainhub import pull as hub_pull
except ImportError:
    # Fallback for older versions
    try:
        from langchain import hub
        hub_pull = hub.pull
    except ImportError:
        # If all else fails, we'll create a simple prompt template
        from langchain_core.prompts import ChatPromptTemplate
        def hub_pull(prompt_name):
            # Fallback: create a simple prompt template
            return ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that answers questions based on retrieved context."),
                ("human", "{input}\n\nContext:\n{context}")
            ])

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Try to import retrieval chain functions from newer locations
try:
    from langchain.chains.retrieval import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    try:
        from langchain.chains import create_retrieval_chain, create_stuff_documents_chain
    except ImportError:
        # Fallback: create these functions manually using LCEL
        from langchain_core.runnables import RunnablePassthrough, RunnableParallel
        from langchain_core.output_parsers import StrOutputParser
        
        def create_stuff_documents_chain(llm, prompt):
            """Create a chain that combines documents using LCEL"""
            def format_docs(input_dict):
                docs = input_dict.get("context", [])
                if not docs:
                    return ""
                # Handle both list of strings and list of Document objects
                if isinstance(docs, list):
                    if docs and hasattr(docs[0], 'page_content'):
                        return "\n\n".join(doc.page_content for doc in docs)
                    else:
                        return "\n\n".join(str(doc) for doc in docs)
                return str(docs)
            
            chain = (
                RunnableParallel(
                    context=format_docs,
                    input=lambda x: x.get("input", "")
                )
                | prompt
                | llm
                | StrOutputParser()
            )
            return chain
        
        def create_retrieval_chain(retriever, combine_docs_chain):
            """Create a retrieval chain using LCEL"""
            def invoke_with_input(input_dict):
                # Get the input query
                query = input_dict.get("input", "")
                # Retrieve documents
                docs = retriever.invoke(query)
                # Combine with input
                result = combine_docs_chain.invoke({"context": docs, "input": query})
                # Return in expected format
                return {"answer": result}
            
            # Create a simple callable that matches the expected interface
            class RetrievalChainWrapper:
                def invoke(self, input_dict):
                    return invoke_with_input(input_dict)
            
            return RetrievalChainWrapper()
from pinecone import Pinecone
from domain_manager import DomainManager
from setup_env import setup_environment


# Global cache for RAG instances
_rag_cache = {}


class DomainRAGSystem:
    """RAG system for a specific domain with eager initialization"""
    
    def __init__(self, domain_name: str, top_k: int = 5):
        self.domain_name = domain_name
        self.top_k = top_k
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
            )
            
            # Create prompt for the chain
            retrieval_qa_chat_prompt = hub_pull("langchain-ai/retrieval-qa-chat")
            
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
        # System should already be initialized at startup
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
