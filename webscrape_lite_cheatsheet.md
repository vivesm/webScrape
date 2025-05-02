# WebScrape Lite - Quick Reference

## Installation

```bash
pip install -r requirements.txt
```

## Basic Commands

### Simple Scraping

```bash
# Scrape a single page
python main.py --base_url https://example.com

# Scrape with link following (same domain only)
python main.py --base_url https://example.com --same_domain_only

# Limit crawl depth
python main.py --base_url https://example.com --max_depth 1

# Adjust request delay
python main.py --base_url https://example.com --delay 2.0
```

### RAG Processing

```bash
# Scrape with basic RAG processing
python main.py --base_url https://example.com --rag

# Customize chunk size and overlap
python main.py --base_url https://example.com --rag --chunk_size 500 --chunk_overlap 100

# Change output directories
python main.py --base_url https://example.com --output_dir custom_output --rag --rag_dir custom_rag

# Use Ollama for processing RAG data
python main.py --base_url https://example.com --rag --ollama

# Customize Ollama models
python main.py --base_url https://example.com --rag --ollama --ollama_model llama3 --embedding_model nomic-embed-text
```

## Common Patterns

```bash
# Documentation site with RAG
python main.py --base_url https://docs.example.com --max_depth 2 --same_domain_only --rag

# Blog content for LLM fine-tuning
python main.py --base_url https://example.com/blog --max_depth 1 --rag --chunk_size 750

# Single detailed article
python main.py --base_url https://example.com/article --max_depth 0 --rag --chunk_size 300
```

## Testing

```bash
# Run basic test suite
python test_scraper.py
```

## RAG Output Format

### Basic RAG Chunk
```json
{
  "text": "Chunk content...",
  "metadata": {
    "url": "https://source-url.com/page",
    "chunk_id": "a1b2c3d4_0",
    "chunk_index": 0,
    "total_chunks": 5
  }
}
```

### Ollama-Processed Chunk
```json
{
  "text": "Chunk content...",
  "embedding": [0.02, -0.14, 0.33, ...],
  "metadata": {
    "url": "https://source-url.com/page",
    "chunk_id": "a1b2c3d4_0",
    "ollama_processed": true,
    "ollama_model": "llama3"
  }
}
```
