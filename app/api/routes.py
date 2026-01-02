"""
FastAPI routes for the regulatory extraction pipeline.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas.request import ExtractionRequest
from app.schemas.response import ExtractionResponse
from app.graph.workflow import run_extraction_workflow
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["extraction"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@router.post(
    "/extract-rules",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract labeling requirement rules for a US state",
    description="""
    Extract marijuana **labeling requirements** for a specified US state.
    
    The endpoint will:
    1. Resolve the regulatory URL for the selected state
    2. Scrape the URL for raw regulatory text using Firecrawl
    3. Use Gemini AI to extract individual labeling rules from the text
    4. If existing rules are provided, compare and set status flags
    5. Return the final set of processed rules with change indicators
    
    **Supported States:**
    - `montana`: Administrative Rules of Montana (ARM) Chapter 42.39
    
    **Product Types:**
    - `flower`: Marijuana flower, dried cannabis, and cannabis buds
    - `concentrates`: Marijuana concentrates, extracts, oils, waxes, and dabs
    - `edibles`: Marijuana edibles, cannabis-infused food products
    - `all`: All marijuana products
    
    **Rule Status Flags:**
    - `new`: Rule not found in existing set
    - `updated`: Rule content has changed (includes change_reason)
    - `unchanged`: Rule is semantically equivalent to existing
    
    **Rule Matching:**
    - Rules are matched by `rule_text_citation` (consistent identifier from source)
    - Matched rules are compared semantically using Gemini AI
    - Status and change_reason are set based on comparison
    """
)
async def extract_rules(request: ExtractionRequest) -> ExtractionResponse:
    """Extract regulatory rules for a US state."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("API REQUEST: POST /api/v1/extract-rules")
    logger.info("=" * 70)
    logger.info(f"Request state: {request.state.value}")
    logger.info(f"Request product_type: {request.product_type}")
    logger.info(f"Request existing_rules: {len(request.existing_rules) if request.existing_rules else 0}")
    
    if request.existing_rules:
        for i, rule in enumerate(request.existing_rules):
            logger.debug(f"  Existing rule [{i+1}]: {rule.rule_name}")
    
    try:
        # Convert existing rules to list if provided
        existing_rules = request.existing_rules if request.existing_rules else None
        
        # Run the extraction workflow
        response = await run_extraction_workflow(
            state=request.state,
            product_type=request.product_type,
            existing_rules=existing_rules
        )
        
        # Check if the workflow reported an error
        if not response.success:
            logger.error(f"Workflow returned error: {response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error or "Extraction failed"
            )
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("API RESPONSE: SUCCESS")
        logger.info("=" * 70)
        logger.info(f"State: {response.state}")
        logger.info(f"Source URL: {response.source_url}")
        logger.info(f"Total rules extracted: {response.total_rules_extracted}")
        logger.info(f"Rules returned: {len(response.rules)}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during extraction: {str(e)}"
        )
