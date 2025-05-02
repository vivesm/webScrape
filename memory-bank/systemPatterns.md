# WebScrape System Patterns

## System Architecture

WebScrape employs a modular, component-based architecture that separates concerns and enables flexibility. The system is organized into these key components:

```
                                  ┌─────────────────┐
                                  │     main.py     │
                                  │  (Entry Point)  │
                                  └────────┬────────┘
                                           │
                 ┌─────────────────────────┼─────────────────────────┐
                 │                         │                         │
        ┌────────▼────────┐      ┌─────────▼─────────┐     ┌─────────▼─────────┐
        │  web_scraper.py │      │ link_extractor.py │     │ content_scraper.py │
        │(Orchestration)  │◄─────►│  (URL Discovery)  │     │ (Content Saving)  │
        └────────┬────────┘      └───────────────────┘     └─────────┬─────────┘
                 │                                                    │
        ┌────────▼────────┐                                  ┌────────▼────────┐
        │ browser_pool.py │                                  │ retry_utils.py  │
        │(Resource Mgmt)  │                                  │ (Error Handling)│
        └────────┬────────┘                                  └─────────────────┘
                 │
        ┌────────▼────────┐      ┌───────────────────┐     ┌─────────────────┐
        │ rag_processor.py│◄─────►│ streaming_proc.py │     │ pdf_extractor.py│
        │ (RAG Pipeline)  │      │(Memory Efficiency) │     │(PDF Processing) │
        └────────┬────────┘      └───────────────────┘     └─────────────────┘
                 │
                 ├─────────────────────────┐
                 │                         │
        ┌────────▼────────┐      ┌─────────▼─────────┐
        │ollama_processor │      │ollama_stream_proc │
        │  (Embeddings)   │◄─────►│ (Response Stream) │
        └─────────────────┘      └───────────────────┘
```

### Core Components

1. **Entry Point (main.py)**
   - Handles command-line argument parsing
   - Initializes the appropriate components
   - Configures the system based on user preferences
   - Manages language and product-specific options

2. **Web Scraper (web_scraper.py)**
   - Core orchestration engine
   - Manages the overall scraping workflow
   - Integrates with other components
   - Handles the primary control flow
   - Includes language detection and filtering

3. **Link Extractor (link_extractor.py)**
   - Discovers URLs from web pages
   - Implements depth control
   - Filters URLs based on patterns
   - Maintains the discovery queue
   - Recognizes language identifiers in URLs

4. **Content Scraper (content_scraper.py)**
   - Saves content from web pages
   - Handles different output formats
   - Processes HTML content
   - Manages file output
   - Preserves language metadata

5. **Browser Pool (browser_pool.py)**
   - Manages Pyppeteer browser instances
   - Implements concurrency control
   - Optimizes resource usage
   - Rotates user agents

6. **RAG Processor (rag_processor.py)**
   - Chunks text for RAG applications
   - Extracts and preserves metadata
   - Creates structured output
   - Prepares data for LLM consumption
   - Handles multilingual content with appropriate metadata

7. **Ollama Processor (ollama_processor.py)**
   - Interfaces with local Ollama instance
   - Generates embeddings for chunks
   - Provides semantic search capabilities
   - Facilitates LLM integration
   - Manages batch processing for embeddings

8. **Ollama Stream Processor (ollama_processor_stream.py)**
   - Implements streaming API for LLM responses
   - Handles timeout detection and recovery
   - Manages partial response accumulation
   - Provides graceful error handling
   - Enables cross-product documentation support

## Key Technical Decisions

1. **Headless Browser Approach**
   - Using Pyppeteer (Python port of Puppeteer) for browser automation
   - Enables handling of JavaScript-heavy sites and dynamic content
   - Provides capabilities to interact with page elements (like cookie banners)

2. **Modular Component Design**
   - Separation of concerns for maintainability
   - Components communicate through well-defined interfaces
   - Each module handles a specific aspect of the scraping process
   - New components can be added without disrupting existing functionality

3. **Concurrency Model**
   - Browser pool for parallel processing
   - Configurable concurrency level
   - Resource-aware design to prevent overloading
   - Asynchronous processing for network and LLM operations

4. **Content Processing Pipeline**
   - Multi-stage processing from raw HTML to RAG chunks
   - Streaming option for memory efficiency
   - Metadata preservation throughout the pipeline
   - Language-aware processing for multilingual content

5. **Error Resilience**
   - Exponential backoff retry mechanism
   - Graceful failure handling
   - Comprehensive logging system
   - Timeout detection and recovery for LLM operations

6. **Lite vs. Full Version**
   - Core functionality in both versions
   - Advanced features (dashboard, streaming) only in full version
   - Common codebase with feature toggles
   - Consistent APIs between versions

7. **Multilingual Support**
   - Language detection integration
   - URL pattern matching for language paths
   - Metadata preservation for language information
   - Language-specific processing options

8. **Streaming Response Generation**
   - Token-by-token streaming from LLM
   - Buffer management for partial responses
   - Timeout handling with retry logic
   - Cross-compatibility with Python 3.9+ environments

## Design Patterns in Use

1. **Factory Pattern**
   - Used for creating browser instances
   - Provides a consistent interface for browser creation
   - Encapsulates browser setup complexity
   - Also applied to processor creation based on content type

2. **Strategy Pattern**
   - Different strategies for content processing (batch vs. streaming)
   - Interchangeable components for different output formats
   - Pluggable RAG processors
   - Alternative LLM response generation approaches

3. **Observer Pattern**
   - Progress reporting with callbacks
   - Event-based notifications for process milestones
   - Dashboard updates in the full version
   - Streaming response observation

4. **Builder Pattern**
   - Construction of complex scraper configurations
   - Step-by-step setup of parameters
   - Default values with selective overrides
   - Language and product-specific builder options

5. **Singleton Pattern**
   - Applied to the browser pool for resource management
   - Ensures consistent state across the application
   - Controls system-wide resources
   - Also used for Ollama client connections

6. **Command Pattern**
   - Command-line arguments encapsulating operations
   - Decouples command execution from implementation
   - Supports extensibility of command options
   - Product-specific command sets

7. **Adapter Pattern**
   - Used to normalize different API responses
   - Provides consistent interface for embedding models
   - Adapts between streaming and non-streaming interfaces
   - Simplifies integration of different LLM providers

8. **Decorator Pattern**
   - Applied to processors to add features like timeout handling
   - Enhances components with additional capabilities
   - Allows for composition of processing steps
   - Used for adding language detection to standard processors

## Component Relationships

1. **Web Scraper and Link Extractor**
   - Web scraper requests URLs from link extractor
   - Link extractor feeds discovered URLs back to web scraper
   - Depth control is coordinated between these components
   - Language pattern recognition integrated into extraction

2. **Web Scraper and Content Scraper**
   - Web scraper passes page content to content scraper
   - Content scraper handles saving and processing
   - Format-specific logic is encapsulated in content scraper
   - Language metadata is preserved from source to output

3. **Browser Pool and Other Components**
   - Centralized management of browser resources
   - Components request browser instances as needed
   - Pool handles lifecycle management and cleanup
   - Provides connection abstraction for headless operations

4. **RAG Processor and Ollama Processor**
   - RAG processor prepares chunks for Ollama processing
   - Ollama processor enriches chunks with embeddings
   - Both collaborate for semantic search capabilities
   - Metadata including language is maintained throughout

5. **Ollama Processor and Ollama Stream Processor**
   - Ollama processor handles batch embedding generation
   - Stream processor manages response generation
   - Both interface with the Ollama API but in different modes
   - Stream processor implements timeout detection and retry logic

6. **Content Scraper and Language Detection**
   - Content extraction considers language patterns
   - Language information is extracted from URLs and content
   - Metadata tagging includes language identification
   - Content can be filtered by language requirements

## Critical Implementation Paths

1. **URL Discovery and Processing**
   ```
   Link Extractor → Web Scraper → Content Scraper → File Output
   ```
   - Critical for basic scraping functionality
   - Core workflow for content acquisition
   - Includes language detection and filtering

2. **RAG Processing Pipeline**
   ```
   Content Scraper → RAG Processor → Ollama Processor → Structured Output
   ```
   - Essential for AI/ML applications
   - Transforms raw content into LLM-ready format
   - Preserves metadata including language information

3. **Browser Resource Management**
   ```
   Web Scraper → Browser Pool → Browser Instances → Content Access
   ```
   - Critical for performance and stability
   - Manages the most resource-intensive component
   - Handles concurrent browser operations

4. **Error Handling and Retry Flow**
   ```
   Component Error → Retry Utility → Exponential Backoff → Resolution
   ```
   - Essential for reliability in production
   - Prevents failures due to transient issues
   - Applies to network operations and LLM interactions

5. **Streaming Processing Path**
   ```
   Content Access → Streaming Buffer → Incremental Processing → Output
   ```
   - Important for memory efficiency
   - Enables processing of large websites
   - Provides progress feedback during long operations

6. **Streaming Response Generation**
   ```
   Query → Context Selection → Ollama Stream Processor → Buffer Management → Response Assembly
   ```
   - Critical for reliable LLM response generation
   - Prevents timeouts with large context windows
   - Provides graceful error handling and partial results
   - Supports cross-product documentation queries

7. **Cross-Product Documentation Flow**
   ```
   Query Analysis → RAG Directory Selection → Semantic Search → Context Retrieval → Streaming Response
   ```
   - Enables knowledge retrieval across multiple product domains
   - Organizes documentation into separate RAG directories
   - Maintains product-specific context boundaries
   - Facilitates specialized testing and evaluation
