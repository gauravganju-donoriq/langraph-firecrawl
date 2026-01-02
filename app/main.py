"""
FastAPI application entry point for the regulatory extraction pipeline.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.routes import router
from app.logging_config import setup_logging, get_logger

# Setup logging before anything else
setup_logging(level="DEBUG")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("=" * 70)
    logger.info("STARTING APPLICATION")
    logger.info("=" * 70)
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Gemini model: {settings.gemini_model}")
    logger.info("=" * 70)
    
    yield
    
    logger.info("=" * 70)
    logger.info("SHUTTING DOWN APPLICATION")
    logger.info("=" * 70)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Marijuana Labeling Requirements Extraction Pipeline",
        description="""
        A LangGraph-based pipeline for extracting and managing marijuana **labeling requirements**
        using Firecrawl and Gemini AI.
        
        ## Features
        
        - **Multi-State Support**: Select a US state to extract regulations from configured sources
        - **Web Scraping**: Uses Firecrawl Agent to extract raw regulatory text from URLs
        - **AI-Powered Extraction**: Uses Gemini AI to parse and structure individual rules
        - **Smart Comparison**: Matches rules by citation and compares semantically
        - **Change Tracking**: Returns rules with status flags (new, updated, unchanged)
        - **Product-Specific**: Filter labeling rules by product type (flower, concentrates, edibles)
        
        ## Supported States
        
        - **Montana**: Administrative Rules of Montana (ARM) Chapter 42.39
        
        ## Labeling Requirements Extracted
        
        - THC/CBD potency and cannabinoid content labeling
        - Required warning statements and labels
        - Manufacturer/producer identification
        - Serving size and dosage information
        - Ingredient lists and allergen labeling
        - Batch/lot number and expiration date requirements
        
        ## Workflow
        
        1. Select a US state and product type
        2. URL is automatically resolved from state configuration
        3. Firecrawl extracts raw regulatory text from the page
        4. Gemini AI parses the text into individual structured rules
        5. If existing rules are provided, they are compared semantically
        6. Rules are returned with status flags indicating changes
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router)
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    logger.info("Starting uvicorn server on 0.0.0.0:8000")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"  # Reduce uvicorn noise
    )
