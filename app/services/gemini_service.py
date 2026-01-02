"""
Gemini AI service for rule extraction and comparison using the google-genai SDK.
Uses structured outputs with Pydantic models for type-safe responses.
"""

from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from google import genai

from app.config import get_settings
from app.schemas.response import Rule, ProcessedRule, ChangeStatus
from app.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Structured Output Schemas for Gemini
# ============================================================================

class ExtractedRule(BaseModel):
    """A single rule extracted from rule_text by Gemini."""
    rule_name: str = Field(
        description="Short descriptive title for the rule (e.g., 'THC Content Labeling', 'Warning Statement Requirement')"
    )
    rule_description: str = Field(
        description="Plain language explanation of the rule with specific details including any numerical limits, required text, or specific requirements"
    )


class RuleExtractionResult(BaseModel):
    """Structured output schema for rule extraction from text."""
    rules: List[ExtractedRule] = Field(
        description="List of individual rules extracted from the source text"
    )


class RuleComparisonResult(BaseModel):
    """Structured output schema for comparing two processed rules."""
    are_equivalent: bool = Field(
        description="Whether the two rules are semantically equivalent (same requirements, possibly different wording)"
    )
    change_reason: Optional[str] = Field(
        default=None,
        description="If not equivalent, explain what changed (e.g., 'THC limit increased from 10mg to 15mg')"
    )


class GeminiService:
    """
    Service for interacting with Google Gemini API using the google-genai SDK.
    Handles rule extraction from text and semantic comparison with structured outputs.
    """
    
    def __init__(self):
        logger.info("Initializing GeminiService...")
        settings = get_settings()
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.gemini_model
        logger.info(f"GeminiService initialized with model: {self.model}")
    
    # ========================================================================
    # Rule Extraction
    # ========================================================================
    
    def _build_extraction_prompt(self, rule_text: str) -> str:
        """Build a prompt for extracting individual rules from rule_text."""
        return f"""You are a legal regulatory expert analyzing marijuana labeling requirements.

Extract all individual labeling requirements from the following regulatory text. Each requirement should be a separate rule with:
1. A short, descriptive rule_name (e.g., "THC Content Labeling", "Warning Statement Requirement", "Font Size Requirement")
2. A clear rule_description that explains the requirement in plain language AND includes specific details like numerical limits, required text, or exact specifications

REGULATORY TEXT:
{rule_text}

Guidelines:
- Extract EACH distinct requirement as a separate rule
- Include specific numerical values, percentages, or measurements when present
- Include any required warning text verbatim
- Be comprehensive - don't skip any requirements
- Use clear, professional language in descriptions

Extract all rules from this text."""

    async def extract_rules_from_text(
        self, 
        rule_text: str, 
        rule_text_citation: str
    ) -> List[ProcessedRule]:
        """
        Extract individual rules from a raw rule_text using Gemini.
        
        Args:
            rule_text: The raw regulatory text to parse
            rule_text_citation: The citation source (passed through to each rule)
            
        Returns:
            List of ProcessedRule objects with status set to NEW
        """
        logger.info("-" * 40)
        logger.info("GEMINI RULE EXTRACTION")
        logger.info("-" * 40)
        logger.debug(f"Rule text length: {len(rule_text)} chars")
        logger.debug(f"Citation: {rule_text_citation}")
        
        prompt = self._build_extraction_prompt(rule_text)
        
        try:
            logger.debug(f"Calling Gemini model: {self.model}")
            
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_json_schema": RuleExtractionResult.model_json_schema(),
                },
            )
            
            logger.debug("Gemini response received, parsing...")
            
            if not response.text:
                raise Exception("Gemini returned empty response")
            
            result = RuleExtractionResult.model_validate_json(response.text)
            
            # Convert to ProcessedRule objects with citation and NEW status
            processed_rules = []
            for extracted in result.rules:
                processed_rule = ProcessedRule(
                    rule_name=extracted.rule_name,
                    rule_description=extracted.rule_description,
                    rule_text_citation=rule_text_citation,
                    status=ChangeStatus.NEW,
                    change_reason=None
                )
                processed_rules.append(processed_rule)
                logger.debug(f"  Extracted: {extracted.rule_name}")
            
            logger.info(f"Extracted {len(processed_rules)} individual rules")
            
            return processed_rules
            
        except Exception as e:
            logger.error(f"GEMINI EXTRACTION FAILED: {str(e)}")
            logger.exception("Full traceback:")
            raise Exception(f"Rule extraction failed: {str(e)}")
    
    async def extract_rules_from_scraped_data(
        self, 
        scraped_rules: List[Rule]
    ) -> List[ProcessedRule]:
        """
        Process all scraped rules and extract individual requirements.
        
        Args:
            scraped_rules: List of raw Rule objects from Firecrawl
            
        Returns:
            Flattened list of all ProcessedRule objects
        """
        logger.info("=" * 60)
        logger.info("GEMINI BATCH EXTRACTION STARTED")
        logger.info("=" * 60)
        logger.info(f"Processing {len(scraped_rules)} scraped rules")
        
        all_processed_rules: List[ProcessedRule] = []
        
        for i, scraped_rule in enumerate(scraped_rules):
            logger.info(f"\nProcessing scraped rule {i+1}/{len(scraped_rules)}: {scraped_rule.rule_number}")
            
            try:
                extracted_rules = await self.extract_rules_from_text(
                    rule_text=scraped_rule.rule_text,
                    rule_text_citation=scraped_rule.rule_text_citation
                )
                all_processed_rules.extend(extracted_rules)
                logger.info(f"  -> Extracted {len(extracted_rules)} individual rules")
            except Exception as e:
                logger.error(f"  Failed to extract from rule {scraped_rule.rule_number}: {e}")
                continue
        
        logger.info("=" * 60)
        logger.info(f"BATCH EXTRACTION COMPLETE: {len(all_processed_rules)} total rules")
        logger.info("=" * 60)
        
        return all_processed_rules
    
    # ========================================================================
    # Rule Comparison
    # ========================================================================
    
    def _build_comparison_prompt(
        self, 
        existing_rule: ProcessedRule, 
        new_rule: ProcessedRule
    ) -> str:
        """Build a prompt for comparing two processed rules."""
        return f"""You are a legal regulatory expert comparing two versions of marijuana labeling requirements.

Compare these two rules and determine if they are semantically equivalent (same requirements, possibly different wording) or if there are substantive differences.

EXISTING RULE:
- Name: {existing_rule.rule_name}
- Description: {existing_rule.rule_description}

NEW RULE:
- Name: {new_rule.rule_name}
- Description: {new_rule.rule_description}

Consider the following when comparing:
1. Core requirements and restrictions
2. Numerical thresholds or limits
3. Required disclosures or warnings
4. Scope of application

Minor wording changes that don't affect the legal meaning should be considered equivalent.
If there are differences, explain specifically what changed."""

    async def compare_rules(
        self, 
        existing_rule: ProcessedRule, 
        new_rule: ProcessedRule
    ) -> Tuple[ChangeStatus, Optional[str]]:
        """
        Compare an existing processed rule with a new one using Gemini.
        
        Args:
            existing_rule: The previously stored rule
            new_rule: The newly extracted rule
            
        Returns:
            Tuple of (ChangeStatus, change_reason)
        """
        logger.info("-" * 40)
        logger.info("GEMINI RULE COMPARISON")
        logger.info("-" * 40)
        logger.info(f"Comparing rule: {existing_rule.rule_name}")
        
        prompt = self._build_comparison_prompt(existing_rule, new_rule)
        
        try:
            logger.debug(f"Calling Gemini model: {self.model}")
            
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_json_schema": RuleComparisonResult.model_json_schema(),
                },
            )
            
            logger.debug("Gemini response received, parsing...")
            
            if not response.text:
                raise Exception("Gemini returned empty response")
            
            result = RuleComparisonResult.model_validate_json(response.text)
            
            logger.info(f"  Are equivalent: {result.are_equivalent}")
            
            if result.are_equivalent:
                logger.info("  Result: UNCHANGED")
                return ChangeStatus.UNCHANGED, None
            else:
                logger.info(f"  Result: UPDATED - {result.change_reason}")
                return ChangeStatus.UPDATED, result.change_reason
                    
        except Exception as e:
            logger.error(f"GEMINI COMPARISON FAILED: {str(e)}")
            logger.exception("Full traceback:")
            # Default to UPDATED on error so we don't lose potential changes
            return ChangeStatus.UPDATED, f"Comparison error: {str(e)}"
    
    async def compare_rule_sets(
        self,
        existing_rules: List[ProcessedRule],
        new_rules: List[ProcessedRule]
    ) -> List[ProcessedRule]:
        """
        Compare existing rules with newly extracted rules and set status flags.
        Matches rules by rule_text_citation (from Firecrawl) to ensure consistent matching.
        
        Args:
            existing_rules: Previously stored processed rules
            new_rules: Newly extracted processed rules
            
        Returns:
            List of ProcessedRule with status and change_reason set appropriately
        """
        logger.info("=" * 60)
        logger.info("RULE SET COMPARISON STARTED")
        logger.info("=" * 60)
        logger.info(f"Existing rules: {len(existing_rules)}")
        logger.info(f"New rules: {len(new_rules)}")
        
        # Create lookup map for existing rules by rule_text_citation
        # Citation is consistent across extractions (comes from Firecrawl)
        existing_map = {rule.rule_text_citation: rule for rule in existing_rules}
        
        final_rules: List[ProcessedRule] = []
        
        for new_rule in new_rules:
            citation = new_rule.rule_text_citation
            
            if citation in existing_map:
                existing_rule = existing_map[citation]
                logger.info(f"\nMatched rule by citation: {citation}")
                
                # Compare the rules semantically
                status, change_reason = await self.compare_rules(existing_rule, new_rule)
                
                # Create the final rule with appropriate status
                final_rule = ProcessedRule(
                    rule_name=new_rule.rule_name,
                    rule_description=new_rule.rule_description,
                    rule_text_citation=new_rule.rule_text_citation,
                    status=status,
                    change_reason=change_reason
                )
                final_rules.append(final_rule)
            else:
                # New rule that doesn't exist in the previous set (citation not found)
                logger.info(f"\nNew rule (citation: {citation}): {new_rule.rule_name}")
                final_rule = ProcessedRule(
                    rule_name=new_rule.rule_name,
                    rule_description=new_rule.rule_description,
                    rule_text_citation=new_rule.rule_text_citation,
                    status=ChangeStatus.NEW,
                    change_reason=None
                )
                final_rules.append(final_rule)
        
        # Log summary
        new_count = sum(1 for r in final_rules if r.status == ChangeStatus.NEW)
        updated_count = sum(1 for r in final_rules if r.status == ChangeStatus.UPDATED)
        unchanged_count = sum(1 for r in final_rules if r.status == ChangeStatus.UNCHANGED)
        
        logger.info("=" * 60)
        logger.info("RULE SET COMPARISON COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  NEW: {new_count}")
        logger.info(f"  UPDATED: {updated_count}")
        logger.info(f"  UNCHANGED: {unchanged_count}")
        
        return final_rules
    
    def close(self):
        """Close the client to release resources."""
        logger.debug("Closing Gemini client")
        self.client.close()
