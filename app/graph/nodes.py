"""
LangGraph node functions for the regulatory extraction pipeline.
"""

from typing import Dict, Any

from app.graph.state import PipelineState
from app.services.firecrawl_service import FirecrawlService
from app.services.gemini_service import GeminiService
from app.schemas.response import ProcessedRule, ChangeStatus
from app.logging_config import get_logger

logger = get_logger(__name__)


# Initialize services lazily to avoid import-time errors
_firecrawl_service = None
_gemini_service = None


def get_firecrawl_service() -> FirecrawlService:
    """Get or create the Firecrawl service instance."""
    global _firecrawl_service
    if _firecrawl_service is None:
        logger.debug("Creating new FirecrawlService instance")
        _firecrawl_service = FirecrawlService()
    return _firecrawl_service


def get_gemini_service() -> GeminiService:
    """Get or create the Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        logger.debug("Creating new GeminiService instance")
        _gemini_service = GeminiService()
    return _gemini_service


async def scrape_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node that scrapes regulatory information using Firecrawl.
    Resolves the URL from state configuration and outputs raw rules.
    """
    logger.info("")
    logger.info("*" * 60)
    logger.info("NODE: scrape_node")
    logger.info("*" * 60)
    
    try:
        us_state = state["state"]
        product_type = state["product_type"]
        
        logger.info(f"Input state: {us_state.value}")
        logger.info(f"Input product_type: {product_type}")
        
        firecrawl_service = get_firecrawl_service()
        
        # Extract rules using Firecrawl agent (URL is resolved from state config)
        scraped_rules, source_url = await firecrawl_service.extract_rules(us_state, product_type)
        
        logger.info(f"Source URL: {source_url}")
        logger.info(f"scrape_node OUTPUT: {len(scraped_rules)} raw rules extracted")
        
        return {
            "scraped_rules": scraped_rules,
            "source_url": source_url,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"scrape_node FAILED: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "scraped_rules": [],
            "source_url": "",
            "error": f"Scraping failed: {str(e)}"
        }


async def extract_rules_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node that uses Gemini to extract individual rules from scraped rule_text.
    Converts raw rules into structured ProcessedRule objects.
    """
    logger.info("")
    logger.info("*" * 60)
    logger.info("NODE: extract_rules_node")
    logger.info("*" * 60)
    
    try:
        scraped_rules = state.get("scraped_rules", [])
        
        logger.info(f"Input scraped_rules: {len(scraped_rules)}")
        
        if not scraped_rules:
            logger.warning("No scraped rules to process")
            return {
                "processed_rules": [],
                "error": None
            }
        
        gemini_service = get_gemini_service()
        
        # Extract individual rules from each scraped rule's text
        processed_rules = await gemini_service.extract_rules_from_scraped_data(scraped_rules)
        
        logger.info(f"extract_rules_node OUTPUT: {len(processed_rules)} individual rules extracted")
        
        for i, rule in enumerate(processed_rules):
            logger.debug(f"  [{i+1}] {rule.rule_name}")
        
        return {
            "processed_rules": processed_rules,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"extract_rules_node FAILED: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "processed_rules": [],
            "error": f"Rule extraction failed: {str(e)}"
        }


async def compare_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node that compares existing processed rules with newly extracted rules.
    Sets status flags (NEW, UPDATED, UNCHANGED) and change_reason on each rule.
    """
    logger.info("")
    logger.info("*" * 60)
    logger.info("NODE: compare_node")
    logger.info("*" * 60)
    
    try:
        existing_rules = state.get("existing_rules", [])
        processed_rules = state.get("processed_rules", [])
        
        logger.info(f"Input existing_rules: {len(existing_rules)}")
        logger.info(f"Input processed_rules: {len(processed_rules)}")
        
        if not existing_rules:
            # No existing rules - all processed rules are NEW
            logger.info("No existing rules - marking all as NEW")
            final_rules = [
                ProcessedRule(
                    rule_name=rule.rule_name,
                    rule_description=rule.rule_description,
                    rule_text_citation=rule.rule_text_citation,
                    status=ChangeStatus.NEW,
                    change_reason=None
                )
                for rule in processed_rules
            ]
            return {
                "final_rules": final_rules,
                "error": None
            }
        
        gemini_service = get_gemini_service()
        
        # Compare the rule sets and get back rules with status flags
        final_rules = await gemini_service.compare_rule_sets(existing_rules, processed_rules)
        
        # Log summary
        new_count = sum(1 for r in final_rules if r.status == ChangeStatus.NEW)
        updated_count = sum(1 for r in final_rules if r.status == ChangeStatus.UPDATED)
        unchanged_count = sum(1 for r in final_rules if r.status == ChangeStatus.UNCHANGED)
        
        logger.info(f"compare_node OUTPUT: {len(final_rules)} final rules")
        logger.info(f"  NEW: {new_count}, UPDATED: {updated_count}, UNCHANGED: {unchanged_count}")
        
        return {
            "final_rules": final_rules,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"compare_node FAILED: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "final_rules": [],
            "error": f"Comparison failed: {str(e)}"
    }


async def format_response_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node that formats the final response.
    Ensures all rules have proper status flags set.
    """
    logger.info("")
    logger.info("*" * 60)
    logger.info("NODE: format_response_node")
    logger.info("*" * 60)
    
    try:
        existing_rules = state.get("existing_rules", [])
        processed_rules = state.get("processed_rules", [])
        final_rules = state.get("final_rules", [])
        
        logger.info(f"State - existing_rules: {len(existing_rules)}")
        logger.info(f"State - processed_rules: {len(processed_rules)}")
        logger.info(f"State - final_rules: {len(final_rules)}")
        
        # If no comparison was done (no existing rules), use processed_rules as final
        if not existing_rules and not final_rules and processed_rules:
            logger.info("No existing rules provided - using processed rules as final (all NEW)")
            final_rules = [
                ProcessedRule(
                    rule_name=rule.rule_name,
                    rule_description=rule.rule_description,
                    rule_text_citation=rule.rule_text_citation,
                    status=ChangeStatus.NEW,
                    change_reason=None
                )
                for rule in processed_rules
            ]
            return {
                "final_rules": final_rules,
                "error": None
            }
        
        logger.info(f"format_response_node OUTPUT: {len(final_rules)} rules")
        
        return {
            "error": None
        }
        
    except Exception as e:
        logger.error(f"format_response_node FAILED: {str(e)}")
        return {
            "error": f"Format failed: {str(e)}"
        }


def should_compare(state: PipelineState) -> str:
    """
    Conditional edge function to determine if comparison is needed.
    Routes to 'compare' if existing rules are provided, otherwise 'format'.
    """
    logger.info("")
    logger.info("*" * 60)
    logger.info("CONDITIONAL: should_compare")
    logger.info("*" * 60)
    
    # Check for errors first
    if state.get("error"):
        logger.warning(f"Error in state, routing to 'format': {state.get('error')}")
        return "format"
    
    existing_rules = state.get("existing_rules", [])
    
    if existing_rules and len(existing_rules) > 0:
        logger.info(f"Existing rules found ({len(existing_rules)}) - routing to 'compare'")
        return "compare"
    else:
        logger.info("No existing rules - routing to 'format'")
        return "format"
