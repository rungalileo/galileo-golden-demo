"""
Dynamic Vector Database Setup Script
Supports any domain by reading configuration from domain config files.
Uses PostgreSQL with pgvector for vector storage.

Usage:
    python setup_vectordb.py <domain_name> <environment>

Example:
    python setup_vectordb.py finance local
    python setup_vectordb.py finance hosted
"""
import argparse
import sys
import os
from pathlib import Path
from typing import List

# Add parent directory to path to import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup_env import setup_environment
from domain_manager import DomainManager
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from helpers.pgvector_utils import create_pgvector_store, get_collection_name
from helpers.sql_utils import load_domain_relational_csvs
import getpass
import uuid
import pandas as pd


def setup_vectordb_for_domain(domain_name: str, environment: str):
    """
    Set up vector database for a specific domain using its configuration.

    Args:
        domain_name: Name of the domain (e.g., 'finance')
        environment: Environment to use ('local' or 'hosted')
    """
    print(f"Setting up vector database for domain: {domain_name} in {environment} environment")

    # Load domain configuration first
    domain_manager = DomainManager()

    try:
        domain_config = domain_manager.load_domain_config(domain_name)
        print(f"✓ Loaded configuration for domain: {domain_config.description}")
    except ValueError as e:
        print(f"❌ Error loading domain '{domain_name}': {e}")
        print(f"Available domains: {', '.join(domain_manager.list_domains())}")
        return False

    # Initialize environment with domain-specific settings
    setup_environment(domain_name, domain_config.config)

    if environment not in ("local", "hosted"):
        print(f"❌ Invalid environment: {environment}. Must be 'local' or 'hosted'")
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

    if domain_name == "mgm_marketing":
        # Custom path below uses explicit CSV + markdown read (avoids Unstructured on .md)
        non_csv_docs = []
        csv_docs = []
        all_docs = []
        print("✓ mgm_marketing: skipping generic DirectoryLoader (custom ingestion)")
    else:
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

    if not os.environ.get("POSTGRES_PASSWORD"):
        os.environ["POSTGRES_PASSWORD"] = getpass.getpass("Enter PostgreSQL password: ")

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model=embedding_model)

    collection_name = get_collection_name(domain_name, environment)
    print(f"Creating PostgreSQL/pgvector collection: {collection_name}")
    vector_store, collection_name = create_pgvector_store(
        embeddings,
        domain_name,
        environment,
        pre_delete_collection=True,
    )

    # Add documents to vector store with UUIDs
    print("Adding documents to vector store...")
    embedded_count = 0

    if domain_name == "bank":
        # Wifi QA Docs
        csv_path = os.path.join(docs_dir, "qa.csv")
        df = pd.read_csv(csv_path)
        doc_list: List[Document] = []
        uuid_list = []
        for _, row in df.iterrows():
            question = str(row.get("question", "") or "").strip()
            answer = str(row.get("answer", "") or "")
            body = (
                f"[FAQ] Online Bank FAQ. "
                f"Question: {question}. "
                f"Answer: {answer}. "
            )
            meta = {
                "doc_family": "bank",
                "question": question,
                "answer": answer
            }
            doc_list.append(Document(page_content=body, metadata=meta))
            uuid_list.append(uuid.uuid4())
        
        vector_store.add_documents(documents=doc_list, ids=uuid_list)
        embedded_count = len(doc_list)

        print("Loading relational tables for bank...")
        load_domain_relational_csvs(docs_dir, domain_name)

    elif domain_name == "healthcare":
        # QA Docs
        csv_path = os.path.join(docs_dir, "qa.csv")
        df = pd.read_csv(csv_path)
        doc_list: List[Document] = []
        uuid_list = []
        for _, row in df.iterrows():
            question = str(row.get("question", "") or "").strip()
            answer = str(row.get("answer", "") or "")
            body = (
                f"[FAQ] Healthcare FAQ. "
                f"Medication: {question}. "
                f"Information: {answer}. "
            )
            meta = {
                "doc_family": "healthcare",
                "question": question,
                "answer": answer
            }
            doc_list.append(Document(page_content=body, metadata=meta))
            uuid_list.append(uuid.uuid4())
        
        vector_store.add_documents(documents=doc_list, ids=uuid_list)
        embedded_count = len(doc_list)

        print("Loading relational tables for healthcare...")
        load_domain_relational_csvs(docs_dir, domain_name)

    elif domain_name == "restaurant":
        # QA Docs
        csv_path = os.path.join(docs_dir, "qa.csv")
        df = pd.read_csv(csv_path)
        doc_list: List[Document] = []
        uuid_list = []
        for _, row in df.iterrows():
            question = str(row.get("question", "") or "").strip()
            answer = str(row.get("answer", "") or "")
            body = (
                f"[FAQ] Restaurant FAQ. "
                f"Question: {question}. "
                f"Answer: {answer}. "
            )
            meta = {
                "doc_family": "restaurant",
                "question": question,
                "answer": answer
            }
            doc_list.append(Document(page_content=body, metadata=meta))
            uuid_list.append(uuid.uuid4())
        
        vector_store.add_documents(documents=doc_list, ids=uuid_list)
        embedded_count = len(doc_list)

        print("Loading relational tables for healthcare...")
        load_domain_relational_csvs(docs_dir, domain_name)

    else:
        uuid_list = [uuid.uuid4() for _ in all_docs]
        vector_store.add_documents(documents=all_docs, ids=uuid_list)
        embedded_count = len(all_docs)



    print(f"✅ Successfully created vector database for {domain_name}")
    print(f"📊 Total documents embedded: {embedded_count}")
    print(f"🔗 PostgreSQL collection: {collection_name}")

    return True


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="Set up vector database for a specific domain using PostgreSQL/pgvector"
    )
    parser.add_argument(
        "domain",
        help="Domain name (e.g., 'finance')"
    )
    parser.add_argument(
        "environment",
        choices=["local", "hosted"],
        help="Environment to use ('local' or 'hosted')"
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
