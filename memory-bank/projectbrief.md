# WebScrape Project Brief

## Project Purpose
WebScrape is a Python-based web scraping tool designed to dynamically fetch web page content, extract links, and process the gathered information for use in Large Language Models (LLMs) via Retrieval Augmented Generation (RAG).

## Core Requirements

1. **Web Scraping Functionality**
   - Dynamically extract links from specified URLs
   - Save content in text format (PDF support in full version)
   - Handle cookie banners automatically
   - Support configurable concurrency and delays
   - Provide link filtering with regex patterns
   - Detect and process language-specific content

2. **Content Processing**
   - Convert scraped content into chunks suitable for LLM training
   - Extract metadata from content including language information
   - Process content in streaming or batch mode
   - Support for PDF extraction and processing
   - Intelligently handle complex HTML structures
   - Maintain cross-product documentation organization

3. **Ollama Integration**
   - Connect to locally running Ollama instances
   - Generate embeddings for semantic search
   - Process content with LLM models
   - Provide a simple API for embeddings and generation
   - Support streaming response generation to avoid timeouts
   - Implement retry mechanisms with fallback options

4. **Multilingual Support**
   - Detect content language automatically
   - Filter content based on language preferences
   - Extract language information from URL patterns
   - Preserve language metadata throughout processing
   - Support language-specific RAG directories

5. **External LLM Integration**
   - Format RAG content for cloud-based LLMs (ChatGPT, Claude)
   - Preserve source and metadata in LLM-friendly formats
   - Support different output formats (markdown, plain text)
   - Create combined knowledge documents from multiple chunks

6. **End-to-End Pipeline**
   - Provide single-command workflow from scraping to LLM consumption
   - Support timestamped outputs for content versioning
   - Implement automated process orchestration
   - Create organized output artifacts with consistent naming

7. **User Interface & Control**
   - Command-line interface with extensive options
   - Web dashboard for monitoring (full version)
   - Progress reporting and logging
   - Job history and management
   - Enhanced error reporting with troubleshooting guidance

8. **Efficiency & Resource Management**
   - Browser resource pooling
   - Duplicate prevention
   - Smart content comparison
   - Exponential backoff retry mechanism
   - Token-aware processing for optimal context utilization
   - Memory-efficient streaming for large documents

## Project Versions

1. **WebScrape (Full)**: Complete toolkit with all features
2. **WebScrape Lite**: Simplified version focusing on essential functionality

Both versions support the core Ollama integration, multilingual content processing, streaming response generation, and external LLM export capabilities.

## Success Criteria

- Efficient scraping of web content with minimal errors
- Proper structuring of content for LLM consumption
- Seamless integration with Ollama for embeddings generation
- Reliable response generation even with large context windows
- Effective handling of multilingual content
- Organized cross-product documentation support
- Simple export to external LLMs like ChatGPT and Claude
- End-to-end pipeline with minimal user intervention
- User-friendly interfaces for both technical and non-technical users
- Resource-efficient operation with proper error handling
