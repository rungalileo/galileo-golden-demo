"""
Galileo API Helper Functions
"""
import requests
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import setup_env
sys.path.append(str(Path(__file__).parent.parent))
from setup_env import setup_environment

# Call setup_environment to load secrets into environment variables
setup_environment()


def get_galileo_app_url() -> str:
    """
    Get the Galileo web console URL from environment variables.
    
    Returns:
        str: The Galileo web console URL without trailing slash
        
    Raises:
        ValueError: If GALILEO_CONSOLE_URL is not set
    """
    galileo_url = os.environ.get("GALILEO_CONSOLE_URL")
    if not galileo_url:
        raise ValueError("GALILEO_CONSOLE_URL environment variable is not set")
    
    # Remove trailing slash if present
    return galileo_url.rstrip('/')


def get_galileo_api_url() -> str:
    """
    Get the Galileo API URL from environment variables.
    
    Returns:
        str: The Galileo API URL
        
    Raises:
        ValueError: If GALILEO_CONSOLE_URL is not set
    """
    galileo_url = get_galileo_app_url()
    
    # Extract domain without protocol
    if galileo_url.startswith("https://"):
        domain = galileo_url[8:]  # Remove https://
    elif galileo_url.startswith("http://"):
        domain = galileo_url[7:]  # Remove http://
    else:
        domain = galileo_url
    
    # Remove app. prefix if exists and any path components
    if domain.startswith("app."):
        domain = domain[4:]
    domain = domain.split('/')[0]  # Get just the domain part
    
    return f"https://api.{domain}"


def get_galileo_api_key() -> str:
    """
    Get the Galileo API key from environment variables.
    
    Returns:
        str: The Galileo API key
        
    Raises:
        ValueError: If GALILEO_API_KEY is not set
    """
    api_key = os.environ.get("GALILEO_API_KEY")
    if not api_key:
        raise ValueError("GALILEO_API_KEY environment variable is not set")
    return api_key


def get_galileo_project_id(project_name: str, starting_token: int = 0, limit: int = 10) -> str:
    """
    Fetches the Galileo project ID for a given project name.

    Args:
        project_name (str): The name of the project to search for.
        starting_token (int): The starting token for pagination.
        limit (int): The number of projects to fetch.

    Returns:
        str: The project ID if found, else None.
        
    Raises:
        ValueError: If required environment variables are not set
        requests.RequestException: If API request fails
    """
    api_key = get_galileo_api_key()
    galileo_url = get_galileo_app_url()
    
    url = f"{galileo_url}/api/galileo/public/v2/projects/paginated?starting_token={starting_token}&limit={limit}"
    headers = {
        "accept": "*/*",
        "galileo-api-key": api_key,
        "content-type": "application/json",
        "origin": galileo_url,
        "referer": f"{galileo_url}/",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    }
    data = {
        "sort": {
            "name": "updated_at",
            "ascending": False
        },
        "filters": []
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    for project in result.get("projects", []):
        if project.get("name") == project_name:
            return project.get("id")
    return None


def get_galileo_log_stream_id(project_id: str, log_stream_name: str) -> str:
    """
    Fetches the Galileo log stream ID for a given project ID and log stream name.

    Args:
        project_id (str): The ID of the project.
        log_stream_name (str): The name of the log stream to search for.

    Returns:
        str: The log stream ID if found, else None.
        
    Raises:
        ValueError: If required environment variables are not set
        requests.RequestException: If API request fails
    """
    api_key = get_galileo_api_key()
    galileo_url = get_galileo_app_url()
    
    url = f"{galileo_url}/api/galileo/v2/projects/{project_id}/log_streams"
    headers = {
        "accept": "*/*",
        "galileo-api-key": api_key,
        "content-type": "application/json",
        "origin": galileo_url,
        "referer": f"{galileo_url}/",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    log_streams = response.json()  # This is now a list of log streams
    
    for stream in log_streams:  # Iterate directly over the list
        if stream.get("name") == log_stream_name:
            return stream.get("id")
    return None
