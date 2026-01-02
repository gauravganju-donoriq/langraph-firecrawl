"""
Configuration management for the regulatory extraction pipeline.
"""

from enum import Enum
from functools import lru_cache
from typing import Dict
from pydantic import BaseModel
from pydantic_settings import BaseSettings


# =============================================================================
# US State Configuration
# =============================================================================

class USState(str, Enum):
    """Supported US states for regulatory extraction."""
    MONTANA = "montana"
    # Add more states here as needed:
    # COLORADO = "colorado"
    # CALIFORNIA = "california"


class StateConfig(BaseModel):
    """Configuration for a specific state's regulatory source."""
    url: str
    prompt: str


# State-specific configurations with URLs and extraction prompts
STATE_CONFIGS: Dict[USState, StateConfig] = {
    USState.MONTANA: StateConfig(
        url="https://rules.mt.gov/browse/collections/aec52c46-128e-4279-9068-8af5d5432d74/sections/e99998bd-fc2a-4eed-9405-9cfd464de88e",
        prompt="""Extract the complete, verbatim text content from the PDF versions of the Administrative Rules of Montana (ARM) Chapter 42.39 specifically for 'General labeling requirements' and 'Labeling requirements for {product_description}'. For each rule, include the rule number, the effective date, and the full body text. You MUST include all subsections, legal citations, history and authority sections found at the bottom of the rule. Do not summarize or omit any parts of the document. NOTE the PDF is being rendered by Chrome's built-in PDF viewer which uses an embed plugin(USE THE scrape_raw TOOL). Maintain the extraction within the target URL:{url}"""
    ),
    # Add more states with their specific URLs and prompts:
    # USState.COLORADO: StateConfig(
    #     url="https://colorado.gov/...",
    #     prompt="Extract regulations from Colorado Code..."
    # ),
}


def get_state_config(state: USState) -> StateConfig:
    """Get the configuration for a specific state."""
    if state not in STATE_CONFIGS:
        raise ValueError(f"State '{state}' is not configured. Available states: {list(STATE_CONFIGS.keys())}")
    return STATE_CONFIGS[state]


# =============================================================================
# Application Settings
# =============================================================================

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    firecrawl_api_key: str
    google_api_key: str
    
    # Application Settings
    app_env: str = "development"
    debug: bool = True
    
    # Gemini Model Configuration (using new google-genai SDK)
    # Available models: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash-001, etc.
    gemini_model: str = "gemini-2.5-flash"
    
    # API Settings
    api_v1_prefix: str = "/api/v1"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]

