# WebScrape Technical Context

## Technologies Used

### Core Technologies

1. **Python 3.9+**
   - Primary programming language
   - Chosen for its strong ecosystem in web scraping and data processing
   - Extensive library support for async operations and ML/AI integration

2. **Pyppeteer**
   - Python port of Puppeteer for browser automation
   - Provides headless Chrome/Chromium control
   - Enables JavaScript-rendered content scraping
   - Handles complex modern web elements (cookie banners, lazy loading)

3. **Beautiful Soup 4**
   - HTML/XML parsing library
   - Used for content extraction from HTML
   - Enhanced with specialized extraction scripts for complex documentation
   - Supports noise removal and intelligent parsing

4. **Asyncio**
   - Asynchronous I/O framework for Python
   - Powers the concurrency model
   - Enables efficient handling of multiple browser instances
   - Used for non-blocking network operations
   - Applied in streaming response processing with wait_for for timeout management

5. **Aiohttp**
   - Asynchronous HTTP client/server
   - Used for API communication with Ollama
   - Handles async requests for embeddings and LLM operations
   - Supports streaming response consumption

6. **SQLite**
   - Lightweight embedded database
   - Stores URL history and download information
   - Enables duplicate prevention and content tracking
   - Supports metadata for multilingual content

### Supporting Technologies

1. **JSON**
   - Primary data interchange format
   - Used for RAG chunk storage
   - Stores metadata and configuration
   - Maintains language information and source tracking

2. **PyPDF2**
   - PDF processing library
   - Extracts text and metadata from PDF files
   - Used in the PDF extraction pipeline

3. **TQDM**
   - Progress bar library
   - Provides visual feedback during operations
   - Enhances user experience for long-running tasks

4. **Logging**
   - Python's built-in logging module
   - Comprehensive logging throughout the application
   - Configurable log levels and outputs
   - Enhanced error logging for timeout detection

5. **Flask** (Full version only)
   - Web framework for the dashboard
   - Lightweight server for monitoring and control
   - Provides RESTful API for interfacing with the scraper

6. **Ollama**
   - Local LLM server for embeddings and text generation
   - Supports various models (llama3, nomic-embed-text, etc.)
   - Provides both batch and streaming APIs
   - Used for RAG query processing

7. **Subprocess**
   - Python's built-in process management module
   - Used for pipeline orchestration
   - Enables command execution with real-time output monitoring
   - Supports error handling and process management

## Development Setup

### Environment Requirements

1. **Python Environment**
   - Python 3.9 or higher (3.9+ for asyncio compatibility)
   - Virtual environment recommended (venv or conda)
   - Pip for package management

2. **Browser Requirements**
   - Chrome or Chromium installed
   - Suitable for headless operation
   - Compatible with Pyppeteer

3. **System Requirements**
   - Memory: Minimum 4GB RAM (8GB+ recommended for large sites)
   - Storage: Sufficient for output files and browser cache
   - Processor: Multi-core recommended for concurrent operations
   - GPU (optional): Accelerates Ollama processing for large models

### Installation Steps

1. **Basic Setup**
   ```bash
   # Clone repository or download source
   git clone <repository-url>
   cd webscrape
   
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Chromium Installation**
   - Automatic installation via Pyppeteer
   - Manual installation supported via `install_chromium.py`
   - Custom browser path configuration available

3. **Ollama Setup** (Required for RAG)
   - Install Ollama locally: https://ollama.ai/
   - Pull required models:
     ```bash
     ollama pull llama3
     ollama pull nomic-embed-text
     ```
   - Configure connection in WebScrape settings
   - Test connection with `python test_ollama_rag.py`

## Technical Constraints

1. **Browser Automation Limitations**
   - Headless browsers consume significant resources
   - Concurrent instances limited by system memory
   - Some websites actively block headless browsers

2. **Network Constraints**
   - Rate limiting by websites may affect scraping speed
   - IP blocking possible when scraping aggressively
   - Network bandwidth can become a bottleneck

3. **Processing Overheads**
   - PDF processing is memory-intensive
   - Large sites require significant storage
   - Embedding generation requires computational resources
   - LLM inference can be resource-intensive and timeout-prone

4. **JavaScript Handling**
   - Complex JavaScript frameworks may not render fully
   - Single-page applications require special handling
   - JavaScript execution timeouts need configuration

5. **Ollama Integration Limits**
   - Depends on local Ollama installation
   - Performance tied to local hardware capabilities
   - Model size affects embedding generation speed
   - Response generation can timeout with large contexts
   - Streaming API mitigates timeout issues but adds complexity

6. **Multilingual Support Challenges**
   - Language detection requires additional processing
   - Different languages may need different chunking strategies
   - Cross-lingual search requires specialized embeddings
   - URL patterns for language identification can vary by site

7. **External LLM Integration Limits**
   - File upload size limitations vary by platform
   - Context window restrictions on external LLMs
   - Markdown formatting may be rendered differently across platforms
   - Limited control over external LLM processing once content is uploaded

## Dependencies

### Core Dependencies

| Dependency | Purpose | Version |
|------------|---------|---------|
| pyppeteer | Browser automation | >=1.0.2 |
| beautifulsoup4 | HTML parsing | >=4.9.3 |
| requests | HTTP requests | >=2.25.1 |
| aiohttp | Async HTTP client | >=3.7.4 |
| PyPDF2 | PDF processing | >=2.10.0 |
| tqdm | Progress bars | >=4.61.2 |
| asyncio | Async framework | Built-in |
| langdetect | Language detection | >=1.0.9 |

### Optional Dependencies

| Dependency | Purpose | Version | Required For |
|------------|---------|---------|-------------|
| flask | Web dashboard | >=2.0.1 | Full version |
| sqlite3 | Database | Built-in | URL history |
| numpy | Vector operations | >=1.20.0 | Ollama embeddings |
| pillow | Image processing | >=8.2.0 | Screenshots |
| pydantic | Data validation | >=1.9.0 | Configuration management |

## Tool Usage Patterns

### End-to-End Pipeline

The simplest way to use WebScrape is through the integrated pipeline:

```bash
./rag_pipeline.py --url "https://example.com" --output_name "my_knowledge"
```

Pipeline options:
- `--url` - Target website URL (required)
- `--output_name` - Base name for output files (required)
- `--depth` - Crawling depth (default: 2)
- `--ollama_model` - Model for generation (default: qwen3:32b)
- `--embed_model` - Embedding model (default: nomic-embed-text)
- `--chunk_size` - RAG chunk size (default: 800)
- `--chunk_overlap` - Chunk overlap (default: 150)
- `--format` - Output format (default: markdown)

### Command-Line Interface

For more granular control, use the individual components:

```bash
# Scraping and RAG processing
python main.py --base_url <URL> [options]
```

Common option patterns:

1. **Basic Scraping**
   ```bash
   python main.py --base_url <URL> --output_format text
   ```

2. **Depth Control**
   ```bash
   python main.py --base_url <URL> --max_depth <N> --same_domain_only
   ```

3. **RAG Processing**
   ```bash
   python main.py --base_url <URL> --rag --chunk_size <N> --chunk_overlap <M>
   ```

4. **Full Pipeline with Ollama**
   ```bash
   python main.py --base_url <URL> --rag --ollama --embedding_model <MODEL>
   ```

5. **Multilingual Support**
   ```bash
   python main.py --base_url <URL> --rag --language fr,en --detect_language
   ```

6. **Testing Pattern**
   ```bash
   python main.py --base_url <URL> --test --test_count <N>
   ```

### External LLM Export

For creating documents to upload to external LLMs:

```bash
python create_combined_knowledge.py --rag_dir <RAG_DIR> --output <OUTPUT_FILE>
```

Options:
- `--rag_dir` - Directory with RAG data (default: rag_data)
- `--output` - Output filename (default: combined_knowledge.md)
- `--format` - Output format (default: markdown, options: markdown, text)

### Streaming RAG Patterns

For streaming response generation with Ollama:

```bash
python test_rag_stream.py --query "Your question here" --rag_dir rag_data
```

Options for streaming mode:

1. **Basic Streaming**
   ```bash
   python test_rag_stream.py --query "Your query" --stream
   ```

2. **Model Selection**
   ```bash
   python test_rag_stream.py --query "Your query" --model llama3 --stream
   ```

3. **Context Control**
   ```bash
   python test_rag_stream.py --query "Your query" --num_chunks 5 --stream
   ```

4. **Product-Specific Testing**
   ```bash
   python test_okta_rag.py --query "What is device fingerprinting?"
   ```

### Web Dashboard (Full Version)

Dashboard is started separately from scraping:

```bash
python dashboard_server.py --port <PORT> --host <HOST>
```

Dashboard interaction patterns:
- Configuration via web form
- Job monitoring through status page
- History management via table interface
- Resource monitoring through charts

### Integration Patterns

1. **RAG Pipeline Integration**
   ```python
   from rag_processor import RAGProcessor
   
   processor = RAGProcessor(input_dir="output", output_dir="rag_data")
   processor.process_all_files()
   ```

2. **Ollama Batch Integration**
   ```python
   from ollama_processor import OllamaProcessor
   
   ollama = OllamaProcessor(rag_dir="rag_data", ollama_url="http://localhost:11434")
   asyncio.run(ollama.process_rag_data())
   ```

3. **Ollama Streaming Integration**
   ```python
   from ollama_processor_stream import OllamaStreamProcessor
   
   stream_processor = OllamaStreamProcessor(
       rag_dir="rag_data", 
       ollama_url="http://localhost:11434",
       timeout=60
   )
   
   async def process_stream():
       async for chunk in stream_processor.generate_response_stream(
           query="Your query",
           contexts=contexts,
           system_prompt="Your system prompt"
       ):
           print(chunk, end="", flush=True)
   
   asyncio.run(process_stream())
   ```

4. **External LLM Export Integration**
   ```python
   from create_combined_knowledge import create_combined_document
   
   success = create_combined_document(
       rag_dir="rag_data",
       output_file="knowledge_export.md",
       format="markdown"
   )
   ```

5. **Complete Pipeline Integration**
   ```python
   from rag_pipeline import run_pipeline
   
   success = run_pipeline(
       url="https://example.com",
       output_name="my_knowledge",
       depth=2,
       ollama_model="llama3",
       embed_model="nomic-embed-text"
   )
   ```

6. **Custom Link Processing**
   ```python
   from web_scraper import WebScraper
   
   def custom_link_handler(url):
       # Custom logic here
       return modified_url
   
   scraper = WebScraper(base_url="https://example.com")
   scraper.set_link_handler(custom_link_handler)
   scraper.start()
   ```

7. **Language-Aware Processing**
   ```python
   from web_scraper import WebScraper
   
   scraper = WebScraper(
       base_url="https://example.com",
       language_filter=["en", "fr"],
       detect_language=True
   )
   scraper.start()
   
   # In RAG processor
   from rag_processor import RAGProcessor
   
   processor = RAGProcessor(
       input_dir="output", 
       output_dir="rag_data",
       maintain_language_metadata=True
   )
   processor.process_all_files()
