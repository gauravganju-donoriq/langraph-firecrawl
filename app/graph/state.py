"""
LangGraph state definition for the regulatory extraction pipeline.
"""

from typing import TypedDict, List, Optional

from app.config import USState
from app.schemas.response import Rule, ProcessedRule


class PipelineState(TypedDict, total=False):
    """
    State schema for the LangGraph extraction workflow.
    
    Attributes:
        state: The US state to extract regulations from.
        product_type: Type of marijuana product (flower, concentrates, edibles, all).
        existing_rules: Pre-existing processed rules provided by the user for comparison.
        source_url: The resolved URL used for extraction (set by scrape_node).
        scraped_rules: Raw rules extracted from the source URL by Firecrawl.
        processed_rules: Individual rules extracted by Gemini from scraped rule_text.
        final_rules: The final set of processed rules with status flags.
        error: Error message if any step fails.
    """
    # Input fields
    state: USState
    product_type: str
    existing_rules: List[ProcessedRule]
    
    # Processing fields
    source_url: str
    scraped_rules: List[Rule]
    processed_rules: List[ProcessedRule]
    
    # Output fields
    final_rules: List[ProcessedRule]
    error: Optional[str]


def create_initial_state(
    state: USState,
    product_type: str,
    existing_rules: Optional[List[ProcessedRule]] = None
) -> PipelineState:
    """
    Create the initial state for the extraction workflow.
    
    Args:
        state: The US state to extract regulations from.
        product_type: Type of marijuana product.
        existing_rules: Optional list of existing processed rules to compare against.
        
    Returns:
        Initialized PipelineState dictionary.
    """
    return PipelineState(
        state=state,
        product_type=product_type,
        existing_rules=existing_rules or [],
        source_url="",
        scraped_rules=[],
        processed_rules=[],
        final_rules=[],
        error=None
    )
