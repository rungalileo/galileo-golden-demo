"""
Domain Manager - Discovers and loads domain configurations
"""
import os
import yaml
import json
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class DomainConfig:
    """Container for domain configuration data"""
    name: str
    description: str
    config: Dict
    system_prompt: Dict
    tools_dir: str
    docs_dir: str
    dataset_file: str


class DomainManager:
    """Manages domain discovery and configuration loading"""
    
    def __init__(self, domains_dir: str = "domains"):
        self.domains_dir = domains_dir
    
    def list_domains(self) -> List[str]:
        """Scan domains directory and return available domains"""
        if not os.path.exists(self.domains_dir):
            return []
        
        domains = []
        for item in os.listdir(self.domains_dir):
            domain_path = os.path.join(self.domains_dir, item)
            if os.path.isdir(domain_path):
                # Check if it has required files
                if self._is_valid_domain(domain_path):
                    domains.append(item)
        
        return sorted(domains)
    
    def _is_valid_domain(self, domain_path: str) -> bool:
        """Check if a directory contains a valid domain structure"""
        required_files = [
            "config.yaml",
            "system_prompt.json",
            "tools/schema.json",
            "tools/logic.py"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(domain_path, file_path)
            if not os.path.exists(full_path):
                return False
        
        return True
    
    def load_domain_config(self, domain_name: str) -> DomainConfig:
        """Load and validate domain configuration"""
        domain_path = os.path.join(self.domains_dir, domain_name)
        
        if not os.path.exists(domain_path):
            raise ValueError(f"Domain '{domain_name}' not found")
        
        if not self._is_valid_domain(domain_path):
            raise ValueError(f"Domain '{domain_name}' has invalid structure")
        
        # Load config.yaml
        config_path = os.path.join(domain_path, "config.yaml")
        config = self._load_yaml(config_path)
        
        # Load system_prompt.json
        system_prompt_path = os.path.join(domain_path, "system_prompt.json")
        system_prompt = self._load_json(system_prompt_path)
        
        # Get directory paths
        tools_dir = os.path.join(domain_path, "tools")
        docs_dir = os.path.join(domain_path, "docs")
        dataset_file = os.path.join(domain_path, "dataset.csv")
        
        return DomainConfig(
            name=domain_name,
            description=config.get("domain", {}).get("description", ""),
            config=config,
            system_prompt=system_prompt,
            tools_dir=tools_dir,
            docs_dir=docs_dir,
            dataset_file=dataset_file
        )
    
    def get_domain_info(self, domain_name: str) -> Dict:
        """Get domain metadata for UI display"""
        domain_config = self.load_domain_config(domain_name)
        
        # Validate required config structure
        if "tools" not in domain_config.config:
            raise ValueError(f"Domain '{domain_name}' missing 'tools' in config.yaml")
        if "rag" not in domain_config.config:
            raise ValueError(f"Domain '{domain_name}' missing 'rag' in config.yaml")
        if "model" not in domain_config.config:
            raise ValueError(f"Domain '{domain_name}' missing 'model' in config.yaml")
        if "model_name" not in domain_config.config["model"]:
            raise ValueError(f"Domain '{domain_name}' missing 'model_name' in model config")
        
        return {
            "name": domain_config.name,
            "description": domain_config.description,
            "tools": domain_config.config["tools"],
            "rag_enabled": domain_config.config["rag"]["enabled"],
            "model": domain_config.config["model"]["model_name"],
            "ui": domain_config.config.get("ui", {})  # Include UI configuration
        }
    
    def _load_yaml(self, file_path: str) -> Dict:
        """Load YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            if data is None:
                raise ValueError(f"Empty or invalid YAML file: {file_path}")
            return data
    
    def _load_json(self, file_path: str) -> Dict:
        """Load JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            if data is None:
                raise ValueError(f"Empty or invalid JSON file: {file_path}")
            return data


# Example usage and testing
if __name__ == "__main__":
    dm = DomainManager()
    
    print("Available domains:")
    domains = dm.list_domains()
    for domain in domains:
        print(f"  - {domain}")
    
    if domains:
        print(f"\nDomain info for '{domains[0]}':")
        info = dm.get_domain_info(domains[0])
        print(json.dumps(info, indent=2))
