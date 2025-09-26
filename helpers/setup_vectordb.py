"""
Dynamic Vector Database Setup Script
Supports any domain by reading configuration from domain config files.

Usage:
    python setup_vectordb.py <domain_name>
    
Example:
    python setup_vectordb.py finance
"""
import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path to import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup_env import setup_environment
from domain_manager import DomainManager
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import getpass


def setup_vectordb_for_domain(domain_name: str):
    """
    Set up vector database for a specific domain using its configuration.
    
    Args:
        domain_name: Name of the domain (e.g., 'finance')
    """
    print(f"Setting up vector database for domain: {domain_name}")
    
    # Initialize environment
    setup_environment()
    
    # Load domain configuration
    domain_manager = DomainManager()
    
    try:
        domain_config = domain_manager.load_domain_config(domain_name)
        print(f"✓ Loaded configuration for domain: {domain_config.description}")
    except ValueError as e:
        print(f"❌ Error loading domain '{domain_name}': {e}")
        print(f"Available domains: {', '.join(domain_manager.list_domains())}")
        return False
    
    # Get configuration settings
    rag_config = domain_config.config.get("rag", {})
    vectorstore_config = domain_config.config.get("vectorstore", {})
    
    chunk_size = rag_config.get("chunk_size", 1000)
    chunk_overlap = rag_config.get("chunk_overlap", 200)
    embedding_model = vectorstore_config.get("embedding_model", "text-embedding-3-large")
    
    print(f"Using chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    print(f"Using embedding model: {embedding_model}")
    
    # Check if docs directory exists
    docs_dir = domain_config.docs_dir
    if not os.path.exists(docs_dir):
        print(f"❌ Docs directory not found: {docs_dir}")
        return False
    
    print(f"Loading documents from: {docs_dir}")
    
    # Load non-CSV documents
    non_csv_loader = DirectoryLoader(docs_dir, exclude=["**/*.csv"])
    non_csv_docs = non_csv_loader.load()
    print(f"✓ Loaded {len(non_csv_docs)} non-CSV documents")
    
    # Load CSV documents
    csv_loader = DirectoryLoader(docs_dir, glob="**/*.csv", loader_cls=CSVLoader)
    csv_docs = csv_loader.load()
    print(f"✓ Loaded {len(csv_docs)} CSV documents")
    
    if len(non_csv_docs) == 0 and len(csv_docs) == 0:
        print(f"⚠️  No documents found in {docs_dir}")
        return False
    
    # Split documents using domain configuration
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True
    )
    split_docs = text_splitter.split_documents(non_csv_docs)
    
    # Combine all documents
    all_docs = split_docs + csv_docs
    print(f"✓ Total document chunks: {len(all_docs)}")
    
    # Preview first few documents
    print("\nDocument preview:")
    for i, doc in enumerate(all_docs[:3]):
        print(f"Doc {i+1}: {doc.page_content[:100]}...")
        print(f"Metadata: {doc.metadata}")
        print("-" * 50)
    
    # Set up OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model=embedding_model)
    
    # Set up domain-specific vector store directory
    domain_path = Path("domains") / domain_name
    vector_db_dir = domain_path / "chroma_db"
    
    # Create directory if it doesn't exist
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    
    collection_name = f"{domain_name}_collection"
    
    print(f"Creating vector store at: {vector_db_dir}")
    print(f"Collection name: {collection_name}")
    
    # Can also intitialize from client directly, but this abstraction seems fine
    # https://python.langchain.com/docs/integrations/vectorstores/chroma/#initialization-from-client
    # Create vector store
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(vector_db_dir),
    )
    
    # Add documents to vector store
    print("Adding documents to vector store...")
    vector_store.add_documents(all_docs)
    
    print(f"✅ Successfully created vector database for {domain_name}")
    print(f"📁 Vector DB saved to: {vector_db_dir}")
    print(f"📊 Total documents embedded: {len(all_docs)}")
    
    return True


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="Set up vector database for a specific domain"
    )
    parser.add_argument(
        "domain", 
        help="Domain name (e.g., 'finance')"
    )
    parser.add_argument(
        "--list-domains", 
        action="store_true",
        help="List available domains"
    )
    
    args = parser.parse_args()
    
    if args.list_domains:
        domain_manager = DomainManager()
        domains = domain_manager.list_domains()
        print("Available domains:")
        for domain in domains:
            print(f"  - {domain}")
        return
    
    success = setup_vectordb_for_domain(args.domain)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
