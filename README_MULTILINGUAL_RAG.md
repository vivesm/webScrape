# Multilingual RAG with WebScrape Lite

This guide demonstrates how to use WebScrape Lite to create RAG systems that work across multiple languages or target specific language documentation.

## Overview

Many documentation sites offer content in multiple languages. WebScrape Lite now includes language filtering to help you:

1. Target content in specific languages
2. Create separate RAG datasets for different languages
3. Process multilingual content effectively

## Key Features

- **Language Filtering**: Target content by language code in URLs (e.g., `/en/`, `/fr/`, `/de/`)
- **Separate Output Directories**: Store different language content in dedicated directories
- **Targeted Scraping**: Focus only on relevant documentation sections
- **Cross-Product Documentation**: Scrape content across different product lines

## Examples

### Scraping Okta Workflows Documentation (English)

```bash
python main.py --base_url "https://help.okta.com/wf/en-us/content/topics/workflows/" \
  --rag --same_domain_only --max_depth 3 \
  --include ".*build.*|.*function.*|.*execute.*|.*workflows.*" \
  --chunk_size 800 --chunk_overlap 150
```

### Scraping Okta Identity Engine Documentation (English)

```bash
python main.py --base_url "https://help.okta.com/oie/en-us/content/topics/identity-engine/oie-index.htm" \
  --rag --same_domain_only --max_depth 2 \
  --chunk_size 800 --chunk_overlap 150 \
  --output_dir output_oie --rag_dir rag_data_oie
```

### Creating Separate Spanish Documentation RAG

```bash
python main.py --base_url "https://help.okta.com/wf/es-us/content/topics/workflows/" \
  --rag --same_domain_only --max_depth 3 \
  --language es \
  --output_dir output_es --rag_dir rag_data_es
```

## Testing Multilingual RAG

Once you've created RAG datasets for different languages, you can test them with our test script:

```bash
# Test English Okta Workflows RAG
python test_okta_rag.py

# Test Spanish Okta Workflows RAG (with custom directory)
python test_okta_rag.py --rag_dir rag_data_es
```

## Integrating Multiple Knowledge Bases

You can create a combined knowledge base by:

1. Scraping different product documentation into separate directories
2. Processing each directory for RAG independently
3. Creating a meta-index that maps queries to the appropriate knowledge base

## Benefits of Multilingual RAG

- **Language-Specific Knowledge**: Better answers in the user's preferred language
- **Reduced Confusion**: Avoid mixing terms/concepts that differ between languages
- **Improved Relevance**: More precise semantic search within language context
- **Product-Specific Insights**: Separate knowledge bases for different product lines

## Next Steps

Consider enhancing your multilingual RAG capabilities by:

1. Creating language detection for queries
2. Implementing cross-lingual search (searching Spanish docs with English queries)
3. Building a frontend that allows switching between language datasets
4. Fine-tuning embeddings models on domain-specific multilingual content
