# Testing WebScrape Lite with Ollama RAG

This guide explains how to test the WebScrape Lite tool with Ollama RAG (Retrieval Augmented Generation) capabilities.

## Overview

WebScrape Lite integrates with Ollama to provide powerful RAG capabilities:
- Generate embeddings for scraped content
- Perform semantic search across scraped documents
- Generate context-aware responses using both the LLM and retrieved content

## Prerequisites

1. **Ollama installed and running locally**
   - Download Ollama from [ollama.ai](https://ollama.ai)
   - Install the models needed for processing:
     - A language model (e.g., `qwen3:32b`, `llama3`, etc.)
     - An embedding model (e.g., `nomic-embed-text`)

2. **WebScrape Lite with RAG data**
   - Ensure you've already run the scraper with RAG processing enabled
   - Check that the `rag_data/` directory contains chunk files and an `embeddings_index.json` file

## Testing Options

### Option 1: Run the Test Script

We've created a dedicated test script to verify the Ollama RAG integration:

```bash
python test_ollama_rag.py
```

This script:
- Connects to your local Ollama instance
- Performs semantic search on existing RAG data
- Generates RAG-enhanced responses
- Provides both sample queries and an interactive mode

### Option 2: Test via Main Script

Run the main WebScrape tool with Ollama processing enabled:

```bash
python main.py --base_url https://example.com --rag --ollama --ollama_model qwen3:32b --embedding_model nomic-embed-text
```

This will:
1. Scrape content from the specified URL
2. Process it into RAG chunks 
3. Generate embeddings using Ollama
4. Create an embeddings index for retrieval

## Key Features Being Tested

1. **Connection to Ollama**
   - The script verifies it can connect to the Ollama API
   - It checks if the required models are available

2. **Semantic Search**
   - Converting queries to embeddings
   - Finding semantically similar content chunks
   - Ranking results by relevance

3. **RAG Response Generation**
   - Using retrieved content as context
   - Generating coherent answers based on the retrieved information
   - Providing citations or references to source material

## Customizing the Test

The test script allows for two modes:
- **Sample queries mode**: Tests with pre-defined questions
- **Interactive mode**: Enter your own queries to test

You can also modify the script to:
- Change the number of results returned (`top_k` parameter)
- Adjust the prompt formatting for response generation
- Test with different Ollama models

## Troubleshooting

If you encounter issues:

1. **Ollama Connection Problems**
   - Ensure Ollama is running (`ps aux | grep ollama`)
   - Verify the API endpoint (default: http://localhost:11434)
   - Check available models (`ollama list`)

2. **Missing Models**
   - Install required models: `ollama pull qwen3:32b` and `ollama pull nomic-embed-text`

3. **No Embeddings Found**
   - Ensure you've processed content with the `--rag --ollama` flags
   - Check that the embeddings index exists in `rag_data/embeddings_index.json`

4. **Slow Response Times**
   - Larger models like `qwen3:32b` require more resources
   - Consider using a smaller model if performance is an issue

## Real-World Applications

This integration enables powerful applications:
- Create searchable knowledge bases from documentation
- Build domain-specific Q&A systems
- Develop context-aware chatbots with grounding in specific content
- Implement semantic search across large document collections

## Next Steps

After testing this integration, you might want to:
1. Integrate the RAG capabilities into your own applications
2. Experiment with different chunking strategies for better retrieval
3. Try different Ollama models to balance performance and quality
4. Expand the system to include other document types or sources
