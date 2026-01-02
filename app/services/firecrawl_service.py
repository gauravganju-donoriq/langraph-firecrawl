"""
Firecrawl service for web scraping marijuana labeling regulatory information.
"""

from typing import List, Dict, Any, Tuple
from firecrawl import FirecrawlApp  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from app.config import get_settings, get_state_config, USState
from app.schemas.response import Rule
from app.logging_config import get_logger

logger = get_logger(__name__)


class FirecrawlExtractSchema(BaseModel):
    """Schema for Firecrawl agent extraction."""
    rules: List[Dict[str, str]] = Field(
        ...,
        description="List of extracted labeling requirement rules"
    )


class FirecrawlService:
    """
    Service for interacting with Firecrawl Agent API.
    Extracts marijuana labeling requirements based on state and product type.
    """
    
    PRODUCT_TYPE_DESCRIPTIONS = {
        "flower": "marijuana flower, dried cannabis, and cannabis buds",
        "concentrates": "marijuana concentrates, extracts",
        "edibles": "marijuana edibles, cannabis-infused food products, and consumables",
        "all": "all marijuana and cannabis products including flower, concentrates, and edibles"
    }
    
    def __init__(self):
        logger.info("Initializing FirecrawlService...")
        settings = get_settings()
        self.app = FirecrawlApp(api_key=settings.firecrawl_api_key)
        logger.info("FirecrawlService initialized successfully")
    
    def _build_extraction_prompt(self, state: USState, product_type: str) -> Tuple[str, str]:
        """
        Build a dynamic prompt for the Firecrawl agent based on state and product type.
        Returns the prompt and URL from the state config.
        """
        # Get state-specific config
        state_config = get_state_config(state)
        
        # Get product description
        product_description = self.PRODUCT_TYPE_DESCRIPTIONS.get(
            product_type, 
            self.PRODUCT_TYPE_DESCRIPTIONS["all"]
        )
        
        # Format the state-specific prompt with product description and URL
        prompt = state_config.prompt.format(
            product_description=product_description,
            url=state_config.url
        )
        
        logger.debug(f"Built extraction prompt for state='{state.value}', product_type='{product_type}'")
        return prompt, state_config.url

    def _get_schema_dict(self) -> Dict[str, Any]:
        """Get the JSON schema for extraction."""
        return {
        "type": "object",
        "properties": {
        "rules": {
            "type": "array",
            "items": {
            "type": "object",
            "properties": {
                "rule_number": {
                "type": "string"
                },
                "effective_date": {
                "type": "string"
                },
                "rule_text": {
                "type": "string"
                },
                "rule_text_citation": {
                "type": "string",
                "description": "Source URL for rule_text_citation"
                },
                "rule_type": {
                "type": "string"
                },
            },
            "required": [
                "rule_number",
                "effective_date",
                "rule_text",
                "rule_text_citation",
                "rule_type",
                "rule_type_citation"
            ]
            }
        }
        },
        "required": [
        "rules"
        ]
    }

    async def extract_rules(self, state: USState, product_type: str) -> Tuple[List[Rule], str]:
        """
        Extract labeling requirement rules for a given state using Firecrawl agent.
        
        Args:
            state: The US state to extract rules from
            product_type: Type of marijuana product
            
        Returns:
            Tuple of (list of Rule objects, source URL used)
        """
        logger.info("=" * 60)
        logger.info("FIRECRAWL EXTRACTION STARTED")
        logger.info("=" * 60)
        logger.info(f"State: {state.value}")
        logger.info(f"Product Type: {product_type}")
        
        prompt, url = self._build_extraction_prompt(state, product_type)
        schema = self._get_schema_dict()
        
        logger.info(f"URL: {url}")
        
        logger.debug("Calling Firecrawl agent...")
        logger.debug(f"Prompt: {prompt[:200]}...")
        
        try:
            # Call Firecrawl agent with the URL
            result = self.app.agent(
                urls=[url],
                prompt=prompt,
                schema=schema
            )
            
            logger.debug(f"Firecrawl agent returned result type: {type(result)}")
            
            # Parse the result
            if result and hasattr(result, 'data') and result.data:
                rules_data = result.data.get('rules', [])
                logger.info(f"Extracted {len(rules_data)} rules from result.data")
            elif isinstance(result, dict):
                rules_data = result.get('rules', [])
                logger.info(f"Extracted {len(rules_data)} rules from dict result")
            else:
                rules_data = []
                logger.warning("No rules found in Firecrawl response")
            
            # Convert to Rule objects
            rules = []
            for i, rule_data in enumerate(rules_data):
                try:
                    rule = Rule(**rule_data)
                    rules.append(rule)
                    logger.debug(f"  Rule {i+1}: {rule.rule_number} - parsed successfully")
                except Exception as e:
                    logger.warning(f"  Rule {i+1}: Failed to parse - {e}")
                    logger.debug(f"  Rule data: {rule_data}")
                    continue
            
            logger.info("-" * 60)
            logger.info(f"FIRECRAWL EXTRACTION COMPLETE: {len(rules)} valid rules extracted")
            logger.info("-" * 60)
            
            for i, rule in enumerate(rules):
                logger.info(f"  [{i+1}] {rule.rule_number} (effective: {rule.effective_date})")
            
            return rules, url
            
        except Exception as e:
            logger.error(f"FIRECRAWL EXTRACTION FAILED: {str(e)}")
            logger.exception("Full traceback:")
            raise Exception(f"Firecrawl extraction failed: {str(e)}")
