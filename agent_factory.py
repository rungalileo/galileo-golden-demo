"""
Agent Factory - Creates domain-specific agents for different frameworks

Supports both single agents and multi-agent systems (Investment Committee).
"""
import os
from typing import Optional, List, Any
from domain_manager import DomainManager, DomainConfig
from agent_frameworks.langgraph.agent import LangGraphAgent
from base_agent import BaseAgent


class AgentFactory:
    """
    Factory for creating domain-specific agents with different frameworks.
    
    Also supports creating multi-agent systems like the Investment Committee.
    """
    
    def __init__(self):
        self.domain_manager = DomainManager()
        self._committee_cache = {}  # Cache for committee orchestrators
    
    def get_available_domains(self) -> list[str]:
        """Get list of available domains"""
        return self.domain_manager.list_domains()
    
    def get_available_frameworks(self) -> list[str]:
        """Get list of available frameworks"""
        return ["LangGraph"]  # Add more frameworks as we implement them
    
    def create_agent(self, domain: str, framework: str, session_id: Optional[str] = None) -> BaseAgent:
        """
        Create an agent for the specified domain and framework.
        
        Args:
            domain: The domain name (e.g., "finance", "healthcare")
            framework: The framework name (e.g., "LangGraph", "CrewAI")
            session_id: Optional session ID for conversation tracking
            
        Returns:
            Configured agent instance
            
        Raises:
            ValueError: If domain or framework is not supported
        """
        # Validate domain exists
        available_domains = self.get_available_domains()
        if domain not in available_domains:
            raise ValueError(f"Domain '{domain}' not found. Available domains: {available_domains}")
        
        # Validate framework is supported
        available_frameworks = self.get_available_frameworks()
        if framework not in available_frameworks:
            raise ValueError(f"Framework '{framework}' not supported. Available frameworks: {available_frameworks}")
        
        # Load domain configuration
        domain_config = self.domain_manager.load_domain_config(domain)
        
        # Create the appropriate agent based on framework
        if framework == "LangGraph":
            return LangGraphAgent(domain_config, session_id)
        # elif framework == "CrewAI":
        #     return CrewAIAgent(domain_config, session_id)
        # elif framework == "AutoGen":
        #     return AutoGenAgent(domain_config, session_id)
        else:
            raise ValueError(f"Framework '{framework}' not implemented yet")
    
    def get_domain_info(self, domain: str) -> dict:
        """Get information about a domain for UI display"""
        return self.domain_manager.get_domain_info(domain)
    
    def has_investment_committee(self, domain: str) -> bool:
        """
        Check if a domain has an investment committee configured.
        
        Args:
            domain: The domain name to check
            
        Returns:
            True if investment_committee folder exists with valid config
        """
        try:
            domain_config = self.domain_manager.load_domain_config(domain)
            committee_path = os.path.join(
                os.path.dirname(domain_config.docs_dir),
                "investment_committee"
            )
            config_path = os.path.join(committee_path, "config.yaml")
            return os.path.exists(config_path)
        except Exception:
            return False
    
    def create_debate_orchestrator(
        self,
        domain: str,
        callbacks: List[Any] = None,
        session_id: Optional[str] = None
    ):
        """
        Create a debate orchestrator for the Investment Committee.
        
        Args:
            domain: The domain name (must have investment_committee configured)
            callbacks: LangChain callbacks for observability (e.g., GalileoCallback)
            session_id: Optional session ID for caching
            
        Returns:
            DebateOrchestrator instance
            
        Raises:
            ValueError: If domain doesn't have investment committee configured
        """
        # Check if committee exists
        if not self.has_investment_committee(domain):
            raise ValueError(
                f"Domain '{domain}' does not have an investment committee configured. "
                f"Please create the investment_committee folder with config.yaml."
            )
        
        # Use cached orchestrator if available (per session)
        cache_key = f"{domain}_{session_id}"
        if cache_key in self._committee_cache:
            return self._committee_cache[cache_key]
        
        # Import here to avoid circular imports
        from agent_frameworks.langgraph.multi_agent import DebateOrchestrator
        
        # Get domain config and committee path
        domain_config = self.domain_manager.load_domain_config(domain)
        committee_path = os.path.join(
            os.path.dirname(domain_config.docs_dir),
            "investment_committee"
        )
        
        # Create orchestrator
        orchestrator = DebateOrchestrator(
            domain_config=domain_config,
            committee_path=committee_path,
            callbacks=callbacks
        )
        
        # Cache it
        if session_id:
            self._committee_cache[cache_key] = orchestrator
        
        return orchestrator
    
    def get_committee_info(self, domain: str) -> Optional[dict]:
        """
        Get information about a domain's investment committee for UI display.
        
        Args:
            domain: The domain name
            
        Returns:
            Dict with committee info, or None if not configured
        """
        if not self.has_investment_committee(domain):
            return None
        
        try:
            import yaml
            domain_config = self.domain_manager.load_domain_config(domain)
            committee_path = os.path.join(
                os.path.dirname(domain_config.docs_dir),
                "investment_committee"
            )
            config_path = os.path.join(committee_path, "config.yaml")
            
            with open(config_path, 'r') as f:
                committee_config = yaml.safe_load(f)
            
            return {
                "name": committee_config.get("committee", {}).get("name", "Investment Committee"),
                "description": committee_config.get("committee", {}).get("description", ""),
                "max_rounds": committee_config.get("debate", {}).get("max_rounds", 2),
                "agents": [
                    {
                        "name": agent.get("display_name", agent.get("name")),
                        "icon": agent.get("icon", "🤖"),
                        "color": agent.get("color", "#666666")
                    }
                    for agent in committee_config.get("agents", [])
                ]
            }
        except Exception as e:
            print(f"Error loading committee info: {e}")
            return None


# Example usage
if __name__ == "__main__":
    factory = AgentFactory()
    
    print("Available domains:", factory.get_available_domains())
    print("Available frameworks:", factory.get_available_frameworks())
    
    # Create a finance agent with LangGraph
    try:
        agent = factory.create_agent("finance", "LangGraph", session_id="test-session")
        print(f"Created agent: {agent.__class__.__name__}")
        print(f"Domain: {agent.domain_config.name}")
        print(f"Tools: {[tool.name for tool in agent.tools]}")
    except Exception as e:
        print(f"Error creating agent: {e}")
