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
    
    # Alert handling settings
    alert_auto_acknowledge: bool = Field(False, env="ALERT_AUTO_ACKNOWLEDGE")
    alert_priority_threshold: str = Field("high", env="ALERT_PRIORITY_THRESHOLD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


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