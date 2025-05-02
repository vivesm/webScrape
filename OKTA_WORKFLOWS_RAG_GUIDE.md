# Testing Okta Workflows RAG with Ollama

This guide demonstrates how to use WebScrape Lite with Ollama to create a RAG-powered Q&A system for Okta Workflows documentation.

## Overview

We've scraped Okta Workflows documentation, processed it with RAG, and generated embeddings using Ollama to create a system that can:

1. Answer questions about Okta Workflows features and functionality
2. Retrieve relevant documentation chunks using semantic search
3. Generate context-aware responses using the qwen3:32b model

## Content We've Scraped

We've successfully scraped several key areas of the Okta Workflows documentation:

- **Overview and concepts** (learn-workflows.htm)
- **Building flows** (build-flows.htm, workflows-build-a-flow.htm)
- **Connections** (configure-connection.htm, view-connections-page.htm)
- **Flow options** (set-schedule-options.htm, set-error-handling.htm, set-monitor-options.htm)
- **Advanced functionality** (build-delegated-flow.htm, create-table.htm, customize-card.htm)

## Testing the RAG System

We've created a dedicated test script for the Okta Workflows documentation:

```bash
python test_okta_rag.py
```

This script:
- Connects to your local Ollama instance
- Uses the qwen3:32b model (or falls back to available models)
- Performs semantic search across the Okta documentation
- Generates RAG-enhanced responses using retrieved context

### Sample Questions to Test

The test script includes these sample questions:

1. "What is Okta Workflows?"
2. "How do I build flows in Okta Workflows?"
3. "What are the execution limits in Okta Workflows?"
4. "How do connections work in Okta Workflows?"
5. "What are helper flows in Okta Workflows?"

### Interactive Mode

You can also enter your own questions about Okta Workflows in interactive mode:

```
Enter a question about Okta Workflows (or 'exit' to quit): How do I test my flow?
```

## Scraping More Content

If you want to expand the knowledge base, you can run additional scrapes:

```bash
python main.py --base_url [OKTA_URL] --rag --same_domain_only --max_depth 2 --include ".*workflows.*" --chunk_size 800 --chunk_overlap 150
```

For example, to scrape more about Okta Workflow execution:

```bash
python main.py --base_url https://help.okta.com/wf/en-us/content/topics/workflows/execute/run-flows.htm --rag --same_domain_only --max_depth 2 --include ".*workflows.*|.*execute.*|.*run.*" --chunk_size 800 --chunk_overlap 150
```

## How It Works

1. **Scraping**: The documentation pages are scraped and saved as text files
2. **RAG Processing**: Text is split into overlapping chunks
3. **Embedding Generation**: Ollama generates vector embeddings for each chunk
4. **Semantic Search**: User queries are converted to embeddings and matched with similar chunks
5. **Response Generation**: The LLM generates answers using the retrieved chunks as context

## Troubleshooting

If the responses are not accurate:

1. Check if you've scraped the relevant documentation page
2. Try adjusting the chunk size and overlap parameters
3. Use more specific queries
4. Add more context by scraping additional pages
5. Verify Ollama is running and your models are available

## Next Steps

You can extend this system by:

1. Building a simple web UI to interact with the RAG system
2. Expanding content to include more Okta documentation
3. Fine-tuning the Ollama model on Okta-specific content
4. Creating a custom connector to access the latest documentation automatically
5. Implementing a feedback mechanism to improve responses over time
