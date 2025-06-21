"""Configuration management for the oncall agent."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Config(BaseSettings):
    """Application configuration."""
    
    # Anthropic/Claude settings
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-3-5-sonnet-20241022", env="CLAUDE_MODEL")
    
    # Agent settings
    agent_name: str = Field("oncall-agent", env="AGENT_NAME")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # MCP integration settings
    mcp_timeout: int = Field(30, env="MCP_TIMEOUT")  # seconds
    mcp_retry_attempts: int = Field(3, env="MCP_RETRY_ATTEMPTS")
    
    # Notion MCP settings
    notion_token: Optional[str] = Field(None, env="NOTION_TOKEN")
    notion_database_id: Optional[str] = Field(None, env="NOTION_DATABASE_ID")
    notion_version: str = Field("2022-06-28", env="NOTION_VERSION")
    
    # Grafana MCP settings
    grafana_url: Optional[str] = Field(None, env="GRAFANA_URL")
    grafana_api_key: Optional[str] = Field(None, env="GRAFANA_API_KEY")
    grafana_username: Optional[str] = Field(None, env="GRAFANA_USERNAME")
    grafana_password: Optional[str] = Field(None, env="GRAFANA_PASSWORD")
    grafana_mcp_server_path: str = Field("../../mcp-grafana/dist/mcp-grafana", env="GRAFANA_MCP_SERVER_PATH")
    grafana_mcp_host: str = Field("localhost", env="GRAFANA_MCP_HOST")
    grafana_mcp_port: int = Field(8081, env="GRAFANA_MCP_PORT")
    
    # Alert handling settings
    alert_auto_acknowledge: bool = Field(False, env="ALERT_AUTO_ACKNOWLEDGE")
    alert_priority_threshold: str = Field("high", env="ALERT_PRIORITY_THRESHOLD")
    
    # Kubernetes settings
    k8s_enabled: bool = Field(True, env="K8S_ENABLED")
    k8s_config_path: str = Field("~/.kube/config", env="K8S_CONFIG_PATH")
    k8s_context: str = Field("default", env="K8S_CONTEXT")
    k8s_namespace: str = Field("default", env="K8S_NAMESPACE")
    k8s_mcp_server_url: str = Field("http://localhost:8080", env="K8S_MCP_SERVER_URL")
    k8s_enable_destructive_operations: bool = Field(False, env="K8S_ENABLE_DESTRUCTIVE_OPERATIONS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def get(self, key: str, default=None):
        """Get config value by key (for backward compatibility)."""
        return getattr(self, key.lower(), default)


_config: Optional[Config] = None


def get_config() -> Config:
    """Get the application configuration singleton."""
    global _config
    if _config is None:
        # Load .env file if it exists
        load_dotenv()
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton (useful for testing)."""
    global _config
    _config = None