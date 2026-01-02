# Marijuana Labeling Requirements Extraction Pipeline

A LangGraph-based pipeline for extracting and managing marijuana **labeling requirements** using Firecrawl and Gemini AI.

## Features

- **Web Scraping**: Uses Firecrawl Agent API to autonomously extract labeling requirement rules from URLs
- **AI-Powered Comparison**: Uses Gemini 2.5 Flash (via google-genai SDK) to semantically compare rules
- **Hybrid Matching**: Matches rules by rule number first, then uses AI for content comparison
- **Product-Specific Filtering**: Filter labeling rules by product type (flower, concentrates, edibles)
- **FastAPI Backend**: Production-ready REST API

## Labeling Requirements Extracted

The pipeline focuses exclusively on labeling requirements:
- THC/CBD potency and cannabinoid content labeling
- Required warning statements and labels
- Manufacturer/producer identification
- Product name and strain information
- Net weight/volume labeling
- Serving size and dosage information
- Ingredient lists and allergen labeling
- Batch/lot number requirements
- Expiration or use-by date labeling
- Universal symbol requirements
- Font size and visibility requirements

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Endpoint                           │
│                   POST /api/v1/extract-rules                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Workflow                          │
│  ┌──────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐  │
│  │  Scrape  │───▶│  Compare  │───▶│  Merge  │───▶│  Format  │  │
│  │   Node   │    │   Node    │    │   Node  │    │   Node   │  │
│  └──────────┘    └───────────┘    └─────────┘    └──────────┘  │
│       │               │                                         │
│       ▼               ▼                                         │
│  ┌──────────┐    ┌───────────┐                                 │
│  │Firecrawl │    │  Gemini   │                                 │
│  │  Agent   │    │    AI     │                                 │
│  └──────────┘    └───────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

1. Clone the repository:
```bash
cd "Langraph Pipeline"
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Add your API keys to `.env`:
```
FIRECRAWL_API_KEY=your-firecrawl-api-key
GOOGLE_API_KEY=your-google-api-key
```

## Usage

### Start the Server

```bash
python -m app.main
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

#### Extract Rules (No Existing Rules)
```bash
curl -X POST http://localhost:8000/api/v1/extract-rules \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://rules.mt.gov/gateway/RuleNo.asp?RN=42.39",
    "product_type": "concentrates"
  }'
```

#### Extract Rules (With Existing Rules for Comparison)
```bash
curl -X POST http://localhost:8000/api/v1/extract-rules \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://rules.mt.gov/gateway/RuleNo.asp?RN=42.39",
    "product_type": "flower",
    "existing_rules": [
      {
        "rule_number": "42.39.301",
        "rule_number_citation": "ARM Chapter 42.39",
        "effective_date": "2023-01-01",
        "effective_date_citation": "Montana Administrative Register",
        "rule_text": "All marijuana products must display THC content...",
        "rule_text_citation": "ARM 42.39.301(1)",
        "rule_type": "labeling",
        "rule_type_citation": "ARM 42.39.301 Header"
      }
    ]
  }'
```

### API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Rule Matching Logic

The pipeline uses a **hybrid matching approach**:

1. **Rule Number Match**: First, rules are matched by their `rule_number` field
2. **Semantic Comparison**: For matched rules, Gemini AI compares the content semantically
3. **Decision Logic**:
   - If semantically equivalent → Keep existing rule
   - If content differs → Replace with new scraped rule
   - If rule number not found → Mark existing as deprecated
   - If new rule number → Add as new rule

## Product Types

| Type | Description |
|------|-------------|
| `flower` | Marijuana flower, dried cannabis, cannabis buds |
| `concentrates` | Marijuana concentrates, extracts, oils, waxes, dabs |
| `edibles` | Cannabis-infused food products, consumables |
| `all` | All marijuana products |

## Response Schema

```json
{
  "success": true,
  "product_type": "concentrates",
  "source_url": "https://example.com/regulations",
  "total_rules_found": 5,
  "rules": [
    {
      "rule_number": "42.39.301",
      "effective_date": "2023-01-01",
      "rule_text": "All marijuana concentrates must display THC content in milligrams...",
      "rule_text_citation": "ARM 42.39.301(1)"
    }
  ],
  "error": null
}
```

## Project Structure

```
langraph-pipeline/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Environment configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── request.py          # Request Pydantic models
│   │   └── response.py         # Response Pydantic models
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py            # LangGraph state definition
│   │   ├── nodes.py            # Graph node functions
│   │   └── workflow.py         # Graph assembly
│   └── services/
│       ├── __init__.py
│       ├── firecrawl_service.py  # Firecrawl agent wrapper
│       └── gemini_service.py     # Gemini API wrapper
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FIRECRAWL_API_KEY` | Firecrawl API key | Yes |
| `GOOGLE_API_KEY` | Google AI/Gemini API key | Yes |
| `APP_ENV` | Environment (development/production) | No |
| `DEBUG` | Enable debug mode | No |

## License

MIT

