"""
Agent Factory - Creates domain-specific agents for different frameworks
"""
from typing import Optional
from domain_manager import DomainManager, DomainConfig
from agent_frameworks.langgraph.agent import LangGraphAgent
from base_agent import BaseAgent


class AgentFactory:
    """
    Factory for creating domain-specific agents with different frameworks.
    """
    
    def __init__(self, domains_dir: Optional[str] = None):
        # If domains_dir is provided, use it; otherwise use default
        if domains_dir:
            self.domain_manager = DomainManager(domains_dir=domains_dir)
        else:
            # Try to find domains directory relative to common locations
            import os
            from pathlib import Path
            
            # Check if we're in a subdirectory and need to go up
            current_dir = Path.cwd()
            if current_dir.name in ["OpenTelemetry_notebooks", "experiments", "helpers"]:
                # We're in a subdirectory, look for domains in parent
                domains_path = current_dir.parent / "domains"
            else:
                # We're at project root
                domains_path = current_dir / "domains"
            
            if domains_path.exists():
                self.domain_manager = DomainManager(domains_dir=str(domains_path))
            else:
                # Fallback to default
                self.domain_manager = DomainManager()
    
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
