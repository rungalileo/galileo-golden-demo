"""
Hallucination Demo Helpers

This module provides functions to log intentional hallucinations to Galileo
for demonstration purposes. Each domain can define hallucination examples
in their config.yaml under the `demo_hallucinations` key.
"""
import os
import uuid
import logging
from typing import Optional, List, Dict, Any, Union
from galileo import GalileoLogger

logger = logging.getLogger(__name__)


def log_hallucination(
    project_name: str,
    log_stream: str,
    question: str,
    context_docs: List[str],
    hallucinated_answer: str,
    model: str = "gpt-4o",
    session_name: str = "Agent Session",
    trace_name: str = "RAG Pipeline",
    existing_logger: Optional[Union[GalileoLogger, Any]] = None,
) -> bool:
    """
    Log a hallucination trace to Galileo for demonstration purposes.
    
    This creates a complete trace with:
    - A retriever span showing the retrieved context
    - An LLM span showing the question and hallucinated (wrong) answer
    
    Args:
        project_name: The Galileo project name to log to
        log_stream: The Galileo log stream to log to  
        question: The user's question
        context_docs: List of retrieved context documents (real content)
        hallucinated_answer: The intentionally wrong answer that contradicts the context
        model: The model name to log (default: gpt-4o)
        session_name: Name for the Galileo session (default: "Hallucination Demo")
        existing_logger: Optional existing logger or context to reuse (if session already started)
        
    Returns:
        bool: True if logging succeeded, False otherwise
    """
    try:
        logger.info(f"Logging hallucination to project: {project_name}, log stream: {log_stream}")
        
        # Use existing logger if provided, otherwise create a new one
        if existing_logger:
            logger.info("Using existing Galileo session for hallucification demo")
            # If it's a GalileoDecorator (galileo_context), get the logger instance
            if hasattr(existing_logger, 'get_logger_instance'):
                galileo_logger = existing_logger.get_logger_instance()
                logger.info("Extracted logger instance from GalileoDecorator")
            else:
                galileo_logger = existing_logger
            created_new_session = False
        else:
            logger.info("Creating new Galileo session for hallucination demo")
            # Initialize Galileo logger
            galileo_logger = GalileoLogger(project=project_name, log_stream=log_stream)
            
            # Start a named session for easy identification
            session_id = str(uuid.uuid4())[:10]
            galileo_logger.start_session(name=session_name, external_id=session_id)
            created_new_session = True
        
        # Start a workflow trace. Names are intentionally generic
        # ("RAG Pipeline" rather than "Hallucination Demo") so the trace
        # blends in with real production traces during demos.
        galileo_logger.start_trace(
            input=question,
            name=trace_name,
        )
        
        # Add retriever span with the real context
        galileo_logger.add_retriever_span(
            input=question,
            output=context_docs,
            name="RAG Retrieval",
            duration_ns=int(1.3e8),
            status_code=200
        )
        
        # Build the LLM input with context
        context_text = "\n\n".join(context_docs)
        llm_input = f"""Human: You are a helpful assistant. Given the context below, please answer the following question:

{context_text}

Question: {question}"""
        
        # Add LLM span with the hallucinated answer
        galileo_logger.add_llm_span(
            input=llm_input,
            output=hallucinated_answer,
            model=model,
            name="LLM Response",
            num_input_tokens=len(llm_input.split()) * 2,  # Rough estimate
            num_output_tokens=len(hallucinated_answer.split()) * 2,
            total_tokens=len(llm_input.split()) * 2 + len(hallucinated_answer.split()) * 2,
            duration_ns=int(1.2e8),
            metadata={"temperature": "0.1", "demo_type": "hallucination"},
            temperature=0.1,
            status_code=200,
            time_to_first_token_ns=500000,
        )
        
        # Conclude the trace
        galileo_logger.conclude(
            output=hallucinated_answer,
            duration_ns=int(2.5e8),
            status_code=200
        )
        
        # Only flush if we created a new session
        # if created_new_session:
        galileo_logger.flush()
        
        logger.info(f"Successfully logged hallucination to project: {project_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log hallucination: {e}")
        return False


def match_hallucination_in_input(
    user_input: str,
    hallucinations: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Find a demo hallucination whose trigger keywords all appear in the user's input.

    Matching is case-insensitive and substring-based, so a user typing
    "what's the lisinopril dosage?" matches trigger_keywords ["lisinopril", "dosage"].

    If a hallucination entry has no `trigger_keywords`, it falls back to a loose
    match against the configured `question` (any 2+ "significant" words shared).

    Args:
        user_input: The raw user chat input.
        hallucinations: The `demo_hallucinations` list from a domain config.

    Returns:
        The matching hallucination dict, or None if nothing matches.
    """
    if not user_input or not hallucinations:
        return None

    text = user_input.lower()

    for hallucination in hallucinations:
        keywords = hallucination.get("trigger_keywords") or []
        if keywords:
            if all(str(kw).lower() in text for kw in keywords):
                return hallucination
            continue

        # Fallback: derive keywords from the question itself.
        question = (hallucination.get("question") or "").lower()
        stopwords = {
            "what", "is", "the", "are", "a", "an", "and", "or", "of", "for",
            "to", "in", "on", "with", "how", "do", "does", "did", "be", "by",
            "its", "it", "this", "that", "from", "at", "as", "you", "i",
        }
        significant = [
            w.strip(".,?!:;\"'()[]")
            for w in question.split()
            if w.strip(".,?!:;\"'()[]") and w.strip(".,?!:;\"'()[]") not in stopwords
        ]
        hits = sum(1 for w in significant if w in text)
        if significant and hits >= max(2, len(significant) // 2):
            return hallucination

    return None


def log_hallucination_for_domain(
    domain_name: str,
    domain_config: Dict[str, Any],
    rag_retriever_func: Optional[callable] = None,
    hallucination_index: int = 0,
    existing_logger: Optional[Union[GalileoLogger, Any]] = None,
) -> bool:
    """
    Log a hallucination for a specific domain using its config.
    
    This reads the hallucination examples from the domain's config.yaml
    and logs them to Galileo. If a RAG retriever function is provided,
    it will fetch real context; otherwise uses the pre-defined context.
    
    Args:
        domain_name: Name of the domain (e.g., "finance", "healthcare")
        domain_config: The domain's configuration dictionary
        rag_retriever_func: Optional function to retrieve real context from RAG
        hallucination_index: Which hallucination example to use (default: 0)
        existing_logger: Optional existing logger or context to reuse (if session already started)
        
    Returns:
        bool: True if logging succeeded, False otherwise
    """
    # Get Galileo settings
    galileo_config = domain_config.get("galileo", {})
    project_name = galileo_config.get("project", f"galileo-demo-{domain_name}")
    log_stream = galileo_config.get("log_stream", "default")
    
    # Get hallucination examples
    hallucinations = domain_config.get("demo_hallucinations", [])
    
    if not hallucinations:
        logger.warning(f"No hallucination examples defined for domain: {domain_name}")
        return False
    
    if hallucination_index >= len(hallucinations):
        hallucination_index = 0
        
    hallucination = hallucinations[hallucination_index]
    question = hallucination.get("question", "")
    hallucinated_answer = hallucination.get("hallucinated_answer", "")
    context_docs = hallucination.get("context", [])
    
    if not question or not hallucinated_answer:
        logger.error(f"Invalid hallucination config for domain: {domain_name}")
        return False
    
    # If RAG retriever is provided and no pre-defined context, fetch real context
    if rag_retriever_func and not context_docs:
        try:
            context_docs = rag_retriever_func(question)
        except Exception as e:
            logger.warning(f"Failed to retrieve context from RAG: {e}")
            context_docs = ["[Context retrieval failed]"]
    
    # Use pre-defined context if available
    if not context_docs:
        context_docs = ["[No context available]"]
    
    # Neutral session/trace naming so the trace looks like any other
    # production query, not a flagged demo artifact.
    session_name = f"{domain_name.title()} Agent Session"

    return log_hallucination(
        project_name=project_name,
        log_stream=log_stream,
        question=question,
        context_docs=context_docs,
        hallucinated_answer=hallucinated_answer,
        session_name=session_name,
        trace_name="Agent",
        existing_logger=existing_logger,
    )


def log_specific_hallucination(
    domain_name: str,
    domain_config: Dict[str, Any],
    hallucination: Dict[str, Any],
    user_question: Optional[str] = None,
    existing_logger: Optional[Union[GalileoLogger, Any]] = None,
) -> bool:
    """
    Log a specific hallucination dict (as opposed to one looked up by index).

    Used by the chat handler when a user's message matches a configured
    hallucination's trigger_keywords. The actual user wording is preserved
    as the trace input so the Galileo trace reflects what the user typed.
    """
    galileo_config = domain_config.get("galileo", {})
    project_name = galileo_config.get("project", f"galileo-demo-{domain_name}")
    log_stream = galileo_config.get("log_stream", "default")

    question = user_question or hallucination.get("question", "")
    hallucinated_answer = hallucination.get("hallucinated_answer", "")
    context_docs = hallucination.get("context") or ["[No context available]"]

    if not question or not hallucinated_answer:
        logger.error(f"Invalid hallucination config for domain: {domain_name}")
        return False

    # Neutral session/trace naming so the chat-triggered trace blends in
    # with the agent's normal traces (no "Hallucination Demo" branding).
    session_name = f"{domain_name.title()} Agent Demo"

    return log_hallucination(
        project_name=project_name,
        log_stream=log_stream,
        question=question,
        context_docs=context_docs,
        hallucinated_answer=hallucinated_answer,
        session_name=session_name,
        trace_name="Agent",
        existing_logger=existing_logger,
    )

