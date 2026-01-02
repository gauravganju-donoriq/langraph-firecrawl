"""
Response schemas for the regulatory extraction pipeline.
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ChangeStatus(str, Enum):
    """Status of rule after comparison."""
    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class Rule(BaseModel):
    """
    Represents a raw rule extracted by Firecrawl.
    Used internally before Gemini processing.
    """
    rule_number: str = Field(
        ...,
        description="The official rule number/identifier"
    )
    effective_date: str = Field(
        ...,
        description="The date when the rule became effective"
    )
    rule_text: str = Field(
        ...,
        description="The full text content of the labeling rule"
    )
    rule_text_citation: str = Field(
        ...,
        description="Citation source for the rule text"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "rule_number": "42.39.301",
                "effective_date": "2023-01-01",
                "rule_text": "All marijuana products must display THC content in milligrams...",
                "rule_text_citation": "ARM 42.39.301(1)"
            }
        }


class ProcessedRule(BaseModel):
    """
    Represents an individual processed rule extracted by Gemini.
    Contains a summarized, structured rule with change status.
    """
    rule_name: str = Field(
        ...,
        description="Short descriptive title for the rule (e.g., 'THC Content Labeling')"
    )
    rule_description: str = Field(
        ...,
        description="Plain language explanation with specific details of the rule requirements"
    )
    rule_text_citation: str = Field(
        ...,
        description="Citation source for the rule text (from Firecrawl)"
    )
    status: ChangeStatus = Field(
        default=ChangeStatus.NEW,
        description="Change status: new, updated, or unchanged"
    )
    change_reason: Optional[str] = Field(
        default=None,
        description="Explanation of why the rule was updated (only if status is 'updated')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "rule_name": "THC Content Labeling",
                "rule_description": "All marijuana products must display THC content in milligrams per serving and per package. The label must show both delta-9 THC and total THC content.",
                "rule_text_citation": "ARM 42.39.301(1)",
                "status": "new",
                "change_reason": None
            }
        }


class ExtractionResponse(BaseModel):
    """
    Response model for the rule extraction endpoint.
    """
    success: bool = Field(..., description="Whether the extraction was successful")
    state: str = Field(..., description="The US state that was queried")
    product_type: str = Field(..., description="The product type that was queried")
    source_url: str = Field(..., description="The regulatory URL that was scraped")
    total_rules_extracted: int = Field(
        ...,
        description="Total number of individual rules extracted and processed"
    )
    rules: List[ProcessedRule] = Field(
        ...,
        description="The processed rules with change status flags"
    )
    error: Optional[str] = Field(None, description="Error message if extraction failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "state": "montana",
                "product_type": "flower",
                "source_url": "https://rules.mt.gov/gateway/RuleNo.asp?RN=42.39",
                "total_rules_extracted": 5,
                "rules": [
                    {
                        "rule_name": "THC Content Labeling",
                        "rule_description": "All marijuana products must display THC content in milligrams...",
                        "rule_text_citation": "ARM 42.39.301(1)",
                        "status": "new",
                        "change_reason": None
                    }
                ],
                "error": None
            }
        }
