# Policy Document Scraper and RAG Integration

A comprehensive system for scraping policy documents, cleaning content, and integrating with the RAG (Retrieval-Augmented Generation) knowledge base.

## Overview

This system handles the complete pipeline for policy management:

1. **Scraping**: Downloads policy pages from given URLs
2. **Cleaning**: Extracts and cleans HTML content, removing noise
3. **Storage**: Saves raw HTML and cleaned text to disk
4. **Processing**: Chunks documents for RAG retrieval
5. **Integration**: Prepares chunks for embedding and semantic search

## Architecture

### Components

#### PolicyScraper (`policy_scraper.py`)
- **Fetches** HTML from URLs using requests with proper headers
- **Cleans** content using BeautifulSoup and optional html2text
- **Validates** content length and quality
- **Persists** raw HTML, cleaned text, and metadata to disk
- **Loads** previously saved policies without re-scraping

#### ContentCleaner (Strategy Pattern)
- **BeautifulSoupCleaner**: Structured HTML-to-text extraction
  - Removes scripts, styles, navigation, headers, footers
  - Preserves document structure with newlines
  - Optimized for policy documents
  
- **HTML2TextCleaner**: Markdown-like conversion
  - Better for link preservation
  - Cleaner output with markdown formatting

#### PolicyProcessor
- **Chunks** documents using overlapping sliding window
- **Preserves** context between chunks (configurable overlap)
- **Validates** chunk quality and completeness
- **Exports** chunks in JSON/JSONL format for RAG

#### RAGPolicyIntegration
- **Orchestrates** the complete pipeline
- **Manages** policy lifecycle (scrape → process → validate)
- **Provides** helper functions for RAG service integration
- **Tracks** statistics and validation results

### Data Flow

```
URLs
  ↓
PolicyScraper (fetch & clean)
  ↓
PolicyDocument (raw + cleaned)
  ↓
Saved to Disk (raw/, cleaned/, metadata/)
  ↓
PolicyProcessor (chunk)
  ↓
DocumentChunk[]
  ↓
chunks.json (ready for RAG)
  ↓
RAG Retrieval & Embeddings
```

## File Structure

```
backend/app/agents/policy/
├── app/
│   ├── rag/
│   │   ├── policy_scraper.py      # Core scraping logic
│   │   ├── policy_cli.py           # Command-line interface
│   │   ├── rag_integration.py      # RAG pipeline integration
│   │   └── ...
│   ├── core/
│   │   ├── config.py               # Settings and directories
│   │   ├── models.py               # Pydantic models
│   │   └── ...
│   └── ...
├── data/
│   ├── chunks/
│   │   └── chunks.json             # Processed chunks for RAG
│   └── embeddings/
│       └── (embeddings go here)
└── ...
```

## Usage

### Option 1: Command-Line Interface (Recommended)

The CLI provides simple commands for all operations:

```bash
# Initialize RAG with complete pipeline (one command!)
python -m app.agents.policy.app.rag.policy_cli init-rag

# Force rescrape all policies
python -m app.agents.policy.app.rag.policy_cli init-rag --force

# Scrape policies from URLs
python -m app.agents.policy.app.rag.policy_cli scrape

# Load previously saved policies
python -m app.agents.policy.app.rag.policy_cli load

# Process policies into chunks
python -m app.agents.policy.app.rag.policy_cli process

# Validate chunks for RAG
python -m app.agents.policy.app.rag.policy_cli validate

# Show statistics
python -m app.agents.policy.app.rag.policy_cli stats

# Export chunks for RAG service
python -m app.agents.policy.app.rag.policy_cli export --format json
python -m app.agents.policy.app.rag.policy_cli export --format jsonl

# Show help
python -m app.agents.policy.app.rag.policy_cli help
```

### Option 2: Python API

```python
from app.agents.policy.app.rag.rag_integration import (
    RAGPolicyIntegration,
    initialize_rag_with_policies
)

# Quick initialization (recommended)
result = initialize_rag_with_policies(force_rescrape=False)
print(result['status'])  # "success" or "error"

# Manual pipeline
integration = RAGPolicyIntegration()

# Scrape and process
result = integration.scrape_and_process(force_rescrape=False)
print(f"Policies scraped: {result['policies_scraped']}")
print(f"Chunks created: {result['chunks_created']}")

# Validate
validation = integration.validate_chunks()
if validation['valid']:
    print("All chunks valid!")

# Get statistics
stats = integration.get_policy_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Chunks by domain: {stats['chunks_by_domain']}")

# Load chunks
chunks = integration.load_chunks()
domain_chunks = integration.get_chunks_by_domain('refund')

# Export for RAG
export_file = integration.export_chunks_for_rag(output_format='json')
```

### Option 3: Direct Scraper Usage

```python
from app.agents.policy.app.rag.policy_scraper import (
    PolicyScraper,
    PolicyProcessor,
    POLICY_URLS
)

# Scrape specific policy
scraper = PolicyScraper()
policy_doc = scraper.scrape_policy('refund', POLICY_URLS['refund'])

# Process into chunks
processor = PolicyProcessor()
chunks = processor.chunk_policy(policy_doc)

# Save chunks
processor.save_chunks_to_json(
    {'refund': chunks},
    output_file=Path('chunks.json')
)
```

## Configuration

Settings are in `app/agents/policy/app/core/config.py`:

```python
# Chunk settings
CHUNK_SIZE = 800              # Characters per chunk
CHUNK_OVERLAP = 200           # Overlap between chunks

# Scraping settings
SCRAPE_TIMEOUT = 30           # Seconds
SCRAPE_DELAY = 1.0            # Delay between requests

# Directories
RAW_POLICIES_DIR = policies/raw
CLEANED_POLICIES_DIR = policies/cleaned
CHUNKS_DIR = data/chunks
EMBEDDINGS_DIR = data/embeddings

# LLM settings (for generation)
GENERATION_MODEL = mistral:instruct
EMBEDDING_MODEL = mxbai-embed-large
```

## Policies Included

The system scrapes 7 policy domains:

| Domain | URL | Content |
|--------|-----|---------|
| Returns | https://stories.flipkart.com/flipkart-product-returns-2/ | Returns eligibility, process, timeframes |
| Refund | https://stories.flipkart.com/flipkart-product-returns-2/ | Refund policies, methods, timeline |
| Terms | https://stories.flipkart.com/terms-of-use | Terms of service, legal agreements |
| Privacy | https://stories.flipkart.com/privacy-policy | Privacy policy, data handling |
| Help | https://www.flipkart.com/helpcentre | General help and FAQs |
| Cancellation | https://healthplus.flipkart.com/pages/view/return-cancellation-and-refund-policy | Cancellation policies and procedures |
| Shipping | https://stories.flipkart.com/flipkart-product-returns-2/ | Shipping policies, delivery times |

## Output Structure

### Raw Policy Storage

```
policies/raw/
├── returns_20260223_120000.html
├── refund_20260223_120001.html
├── terms_20260223_120002.html
└── ...
```

### Cleaned Policy Storage

```
policies/cleaned/
├── returns_20260223_120000.txt
├── returns_20260223_120000_metadata.json
├── refund_20260223_120001.txt
├── refund_20260223_120001_metadata.json
└── ...
```

### Metadata JSON

```json
{
  "policy_id": "returns_20260223_120000",
  "policy_domain": "returns",
  "title": "Flipkart Returns Policy",
  "source_url": "https://stories.flipkart.com/flipkart-product-returns-2/",
  "scrape_timestamp": "2026-02-23T12:00:00",
  "metadata": {
    "policy_key": "returns",
    "scrape_date": "2026-02-23T12:00:00",
    "content_length": 5432,
    "html_length": 45632
  },
  "raw_file": "/.../policies/raw/returns_20260223_120000.html",
  "cleaned_file": "/.../policies/cleaned/returns_20260223_120000.txt"
}
```

### Chunks Output (chunks.json)

```json
[
  {
    "chunk_id": "chunk_returns_20260223_120000_0",
    "policy_id": "returns_20260223_120000",
    "policy_domain": "returns",
    "content": "Flipkart returns policy - eligible items... (truncated)",
    "chunk_index": 0,
    "source_url": "https://stories.flipkart.com/...",
    "metadata": {
      "title": "Flipkart Returns Policy",
      "policy_key": "returns"
    },
    "created_at": "2026-02-23T12:00:00"
  },
  { ... more chunks ... }
]
```

## Features

### Smart Content Extraction

- **Removes** noise: scripts, styles, navigation, ads
- **Preserves** structure: headings, lists, paragraphs
- **Extracts** main content: identifies and focuses on primary text
- **Handles** malformed HTML gracefully with fallback strategies

### Intelligent Chunking

- **Respects** sentence boundaries (doesn't break mid-sentence)
- **Maintains** context with overlapping windows
- **Configurable** chunk size for different use cases
- **Validates** chunk quality and completeness

### Persistence & Recovery

- **Saves** raw HTML for archival and re-processing
- **Stores** cleaned text for direct use
- **Caches** metadata for quick lookups
- **Reloads** without re-scraping on restart

### RAG Integration

- **Validates** chunks before ingestion
- **Tracks** statistics and quality metrics
- **Exports** in multiple formats (JSON, JSONL)
- **Provides** domain-based filtering for targeted retrieval

## Dependencies

Required packages (add to requirements.txt):

```
requests>=2.31.0
beautifulsoup4>=4.12.0
html2text>=2024.2.26
lxml>=4.9.0
```

Install them:
```bash
pip install requests beautifulsoup4 html2text lxml
```

## Workflow Examples

### Example 1: One-Time Setup

```bash
# Initialize everything with one command
python -m app.agents.policy.app.rag.policy_cli init-rag

# Check results
python -m app.agents.policy.app.rag.policy_cli stats
```

### Example 2: Update Policies

```bash
# Force rescrape to get latest content
python -m app.agents.policy.app.rag.policy_cli init-rag --force

# Validate new chunks
python -m app.agents.policy.app.rag.policy_cli validate

# Export for RAG
python -m app.agents.policy.app.rag.policy_cli export
```

### Example 3: Python Integration

```python
from app.agents.policy.app.rag.rag_integration import initialize_rag_with_policies

# On app startup
result = initialize_rag_with_policies()
if result['status'] == 'success':
    print(f"✅ Loaded {result['statistics']['total_chunks']} policy chunks")
else:
    print(f"❌ Failed to initialize policies: {result['errors']}")
```

## Troubleshooting

### Issue: "Chunks file not found"
**Solution**: Run `python -m app.agents.policy.app.rag.policy_cli init-rag`

### Issue: "Failed to fetch URL"
**Solution**: Check internet connection, verify URL is accessible, check firewall/proxy

### Issue: "Validation errors"
**Solution**: Run `python -m app.agents.policy.app.rag.policy_cli validate` to see details

### Issue: "Empty chunks"
**Solution**: Adjust `CHUNK_SIZE` in config, website HTML structure may have changed

## Extensions

### Adding New Policies

Add to `POLICY_URLS` in `policy_scraper.py`:

```python
POLICY_URLS = {
    "exchange": {
        "url": "https://example.com/exchange-policy",
        "domain": "exchange",
        "title": "Exchange Policy",
    }
}
```

### Custom HTML Cleaning

Implement custom `ContentCleaner`:

```python
class CustomCleaner(ContentCleaner):
    def clean(self, html: str) -> str:
        # Your custom logic
        return cleaned_text
```

### Custom Chunking Strategy

Subclass `PolicyProcessor`:

```python
class CustomProcessor(PolicyProcessor):
    def chunk_policy(self, policy_doc):
        # Your custom chunking logic
        return chunks
```

## Performance

- **Scraping**: ~2-5 seconds per page (depends on page size)
- **Cleaning**: ~100ms per page
- **Chunking**: ~50ms per 1000 characters
- **Validation**: ~10ms for 100 chunks

For 7 policies:
- Total time: ~30-60 seconds
- Total output: ~5000-10000 chunks
- File size: ~2-5 MB

## Security

- **No credentials** stored or transmitted
- **Standard User-Agent** for web requests
- **No cookies** or session persistence
- **Local-only** file operations
- **No external** data transmission (except scraping)

## License

Same as parent project

## Support

For issues or questions, check the logs:
```bash
tail -f logs/policy_scraper.log
```

Or run validation:
```bash
python -m app.agents.policy.app.rag.policy_cli validate
```
