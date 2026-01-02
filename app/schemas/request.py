"""
Request schemas for the regulatory extraction pipeline.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from app.config import USState
from app.schemas.response import ProcessedRule


class ExtractionRequest(BaseModel):
    """
    Request model for the rule extraction endpoint.
    """
    state: USState = Field(
        ...,
        description="US state to extract labeling requirements from"
    )
    product_type: Literal["flower", "concentrates", "edibles", "all"] = Field(
        ...,
        description="Type of marijuana product to extract labeling rules for"
    )
    existing_rules: Optional[List[ProcessedRule]] = Field(
        None,
        description="Pre-existing processed rules to compare against newly extracted rules"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "state": "montana",
                "product_type": "concentrates",
                "existing_rules": [
                    {
                        "rule_name": "THC Content Labeling",
                        "rule_description": "All marijuana concentrates must display THC content in milligrams...",
                        "rule_text_citation": "ARM 42.39.301(1)",
                        "status": "unchanged",
                        "change_reason": None
                    }
                ]
            }
        }
