"""
LangGraph workflow assembly for the regulatory extraction pipeline.
"""

from langgraph.graph import StateGraph, START, END

from app.config import USState
from app.graph.state import PipelineState, create_initial_state
from app.graph.nodes import (
    scrape_node,
    extract_rules_node,
    compare_node,
    format_response_node,
    should_compare
)
from app.schemas.response import ProcessedRule, ExtractionResponse
from app.logging_config import get_logger
from typing import List, Optional

logger = get_logger(__name__)


def create_extraction_workflow():
    """
    Create and compile the LangGraph extraction workflow.
    
    Flow:
        START -> scrape -> extract_rules -> (compare | format) -> format -> END
    """
    logger.info("Creating LangGraph extraction workflow...")
    
    # Create the graph with our state schema
    workflow = StateGraph(PipelineState)  # type: ignore[arg-type]
    
    # Add nodes
    workflow.add_node("scrape", scrape_node)
    workflow.add_node("extract_rules", extract_rules_node)
    workflow.add_node("compare", compare_node)
    workflow.add_node("format", format_response_node)
    
    logger.debug("Added nodes: scrape, extract_rules, compare, format")
    
    # Define edges
    # START -> scrape -> extract_rules
    workflow.add_edge(START, "scrape")
    workflow.add_edge("scrape", "extract_rules")
    
    # extract_rules -> (compare | format) based on whether existing rules exist
    workflow.add_conditional_edges(
        "extract_rules",
        should_compare,
        {
            "compare": "compare",
            "format": "format"
        }
    )
    
    # compare -> format -> END
    workflow.add_edge("compare", "format")
    workflow.add_edge("format", END)
    
    logger.debug("Added edges: START->scrape->extract_rules->(compare|format)->format->END")
    
    # Compile the graph
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compiled successfully")
    
    return compiled_workflow


async def run_extraction_workflow(
    state: USState,
    product_type: str,
    existing_rules: Optional[List[ProcessedRule]] = None
) -> ExtractionResponse:
    """
    Run the extraction workflow and return the response.
    
    Args:
        state: The US state to extract regulations from
        product_type: Type of marijuana product (flower, concentrates, edibles, all)
        existing_rules: Optional list of previously processed rules for comparison
        
    Returns:
        ExtractionResponse with processed rules and status flags
    """
    logger.info("")
    logger.info("#" * 70)
    logger.info("EXTRACTION WORKFLOW STARTED")
    logger.info("#" * 70)
    logger.info(f"State: {state.value}")
    logger.info(f"Product Type: {product_type}")
    logger.info(f"Existing Rules: {len(existing_rules) if existing_rules else 0}")
    
    # Create the workflow
    workflow = create_extraction_workflow()
    
    # Create initial state
    initial_state = create_initial_state(
        state=state,
        product_type=product_type,
        existing_rules=existing_rules
    )
    
    logger.info("Initial state created, invoking workflow...")
    
    # Run the workflow
    final_state = await workflow.ainvoke(initial_state)
    
    logger.info("")
    logger.info("#" * 70)
    logger.info("EXTRACTION WORKFLOW COMPLETED")
    logger.info("#" * 70)
    
    # Get the resolved source URL from state
    source_url = final_state.get("source_url", "")
    
    # Check for errors
    if final_state.get("error"):
        logger.error(f"Workflow completed with error: {final_state['error']}")
        return ExtractionResponse(
            success=False,
            state=state.value,
            product_type=product_type,
            source_url=source_url,
            total_rules_extracted=0,
            rules=[],
            error=final_state["error"]
        )
    
    # Build response
    final_rules = final_state.get("final_rules", [])
    processed_rules = final_state.get("processed_rules", [])
    
    # If no comparison was done, use processed rules directly
    if not final_rules and processed_rules:
        final_rules = processed_rules
    
    logger.info("Final Response:")
    logger.info("  Success: True")
    logger.info(f"  State: {state.value}")
    logger.info(f"  Source URL: {source_url}")
    logger.info(f"  Total Rules Extracted: {len(final_rules)}")
    
    for i, rule in enumerate(final_rules):
        logger.info(f"    [{i+1}] {rule.rule_name} ({rule.status.value})")
    
    return ExtractionResponse(
        success=True,
        state=state.value,
        product_type=product_type,
        source_url=source_url,
        total_rules_extracted=len(final_rules),
        rules=final_rules,
        error=None
    )
