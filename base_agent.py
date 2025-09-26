"""
Base Agent Interface - Abstract base class for all agent frameworks
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain_manager import DomainConfig


class BaseAgent(ABC):
    """
    Abstract base class that all agent frameworks must implement.
    This standardizes how new frameworks are added to prevent drift.
    """
    
    def __init__(self, domain_config: DomainConfig, session_id: Optional[str] = None):
        self.domain_config = domain_config
        self.session_id = session_id or f"{domain_config.name}-session"
        self.tools = []
        self.system_prompt = domain_config.system_prompt["system_prompt"]
    
    @abstractmethod
    def load_tools(self) -> None:
        """
        Load tools from the domain's tools directory.
        Must be implemented by each framework.
        """
        pass
    
    @abstractmethod
    def process_query(self, messages: List[Dict[str, str]]) -> str:
        """
        Process a user query and return a response.
        
        Args:
            messages: List of conversation messages in format [{"role": "user", "content": "..."}]
            
        Returns:
            String response from the agent
        """
        pass
