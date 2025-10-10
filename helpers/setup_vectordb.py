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
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import getpass
import uuid


def setup_vectordb_for_domain(domain_name: str, environment: str):
    """
    Set up vector database for a specific domain using its configuration.
    
    Args:
        domain_name: Name of the domain (e.g., 'finance')
        environment: Environment to use ('local' or 'hosted')
    """
    print(f"Setting up vector database for domain: {domain_name} in {environment} environment")
    
    # Initialize environment
    setup_environment()
    
    # Set up Pinecone project based on environment
    if environment == "local":
        pinecone_project = "galileo-demo-local"
    elif environment == "hosted":
        pinecone_project = "galileo-demo-hosted"
    else:
        print(f"❌ Invalid environment: {environment}. Must be 'local' or 'hosted'")
        return False
    
    print(f"Using Pinecone project: {pinecone_project}")
    
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
    
    # Get the appropriate Pinecone API key based on environment
    if environment == "local":
        pinecone_key = os.environ.get("PINECONE_API_KEY_LOCAL")
        if not pinecone_key:
            pinecone_key = getpass.getpass("Enter API key for Pinecone (galileo-demo-local project): ")
    elif environment == "hosted":
        pinecone_key = os.environ.get("PINECONE_API_KEY_HOSTED")
        if not pinecone_key:
            pinecone_key = getpass.getpass("Enter API key for Pinecone (galileo-demo-hosted project): ")
    
    # Set the Pinecone API key for this session
    os.environ["PINECONE_API_KEY"] = pinecone_key
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model=embedding_model)
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=pinecone_key)
    
    # Create index name based on domain and environment
    index_name = f"{domain_name}-{environment}-index"
    
    print(f"Creating Pinecone index: {index_name}")
    
    # Check if index exists and has correct dimension
    if pc.has_index(index_name):
        # Check if existing index has correct dimension
        index_info = pc.describe_index(index_name)
        existing_dimension = index_info.dimension
        expected_dimension = 3072 if embedding_model == "text-embedding-3-large" else 1536
        
        if existing_dimension != expected_dimension:
            print(f"⚠️  Existing index has wrong dimension: {existing_dimension}, expected: {expected_dimension}")
            print(f"Deleting existing index: {index_name}")
            pc.delete_index(index_name)
            # Wait for deletion to complete
            import time
            time.sleep(5)
            print(f"Creating new Pinecone index: {index_name}")
        else:
            print(f"Using existing Pinecone index: {index_name}")
            print(f"Index dimension: {existing_dimension}")
    
    if not pc.has_index(index_name):
        print(f"Creating new Pinecone index: {index_name}")
        # Use correct dimension for text-embedding-3-large (3072)
        dimension = 3072 if embedding_model == "text-embedding-3-large" else 1536
        print(f"Using dimension: {dimension} for embedding model: {embedding_model}")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    
    # Get the index
    index = pc.Index(index_name)
    
    # Create vector store
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    
    # Add documents to vector store with UUIDs
    print("Adding documents to vector store...")
    uuids = [str(uuid.uuid4()) for _ in range(len(all_docs))]
    vector_store.add_documents(documents=all_docs, ids=uuids)
    
    print(f"✅ Successfully created vector database for {domain_name}")
    print(f"📊 Total documents embedded: {len(all_docs)}")
    print(f"🔗 Pinecone index: {index_name}")
    
    return True


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="Set up vector database for a specific domain using Pinecone"
    )
    parser.add_argument(
        "domain", 
        help="Domain name (e.g., 'finance')"
    )
    parser.add_argument(
        "environment",
        choices=["local", "hosted"],
        help="Environment to use ('local' for galileo-demo-local, 'hosted' for galileo-demo-hosted)"
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
    
    success = setup_vectordb_for_domain(args.domain, args.environment)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
