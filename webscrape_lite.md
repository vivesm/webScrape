# WebScrape Lite

A simplified version of the WebScrape tool that focuses on essential web scraping functionality and RAG (Retrieval Augmented Generation) processing.

## Overview

WebScrape Lite allows you to:
- Scrape web pages and save content as text files
- Extract links from web pages with basic depth control
- Process scraped content for LLM training using RAG
- Generate structured text chunks with metadata

This lite version strips away the complexity of the full WebScrape project while maintaining the core functionality needed for most web scraping and RAG processing tasks.

## Installation

1. Clone the repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

Only the following core dependencies are needed:
- beautifulsoup4
- pyppeteer
- requests
- tqdm
- PyPDF2 (for RAG processing)

## Core Components

WebScrape Lite consists of these essential modules:

1. **main.py**: Entry point with simplified command-line options
2. **web_scraper.py**: Core scraping functionality
3. **link_extractor.py**: Extracts links from web pages
4. **content_scraper.py**: Saves web content as text
5. **rag_processor.py**: Processes text for LLM training

## Basic Usage

### Simple Web Scraping

The most basic usage is to scrape a single web page:

```bash
python main.py --base_url https://example.com
```

This will:
- Visit the specified URL
- Save its content as text
- Store the output in the `output/` directory

### Scraping with Link Following

To scrape a page and follow links one level deep:

```bash
python main.py --base_url https://example.com --max_depth 1 --same_domain_only
```

This will:
- Visit the base URL
- Extract all links on that page
- Visit each link and save its content
- Only follow links to the same domain

### Basic RAG Processing

To scrape web content and process it for RAG:

```bash
python main.py --base_url https://example.com --output_format text --rag
```

This will:
- Scrape content as text
- Process the text into chunks suitable for LLM training
- Store the chunked data in the `rag_data/` directory

### Customizing RAG Parameters

You can customize the RAG processing parameters:

```bash
python main.py --base_url https://example.com --rag --chunk_size 500 --chunk_overlap 100
```

This will:
- Create smaller chunks (500 characters each)
- With more overlap between chunks (100 characters)
- Resulting in more chunks with better context continuity

### Using Ollama for RAG Processing

If you have Ollama running locally, you can process RAG data with it:

```bash
python main.py --base_url https://example.com --rag --ollama
```

This will:
- Scrape content and process it into RAG chunks
- Connect to your local Ollama instance
- Generate embeddings for each chunk
- Enable semantic search capabilities

### Customizing Ollama Integration

You can customize the Ollama integration:

```bash
python main.py --base_url https://example.com --rag --ollama --ollama_model llama3 --embedding_model nomic-embed-text
```

This allows you to:
- Specify which Ollama model to use
- Choose a specific embedding model
- Connect to Ollama instances on different hosts

## Command-Line Options

### Essential Options

| Option | Description | Default |
|--------|-------------|---------|
| `--base_url` | URL to scrape | None |
| `--output_format` | Output format (`text` only in Lite) | `text` |
| `--output_dir` | Where to save scraped content | `output/` |
| `--max_depth` | How many levels deep to follow links | `1` |
| `--same_domain_only` | Only follow links on the same domain | `False` |
| `--delay` | Seconds to wait between requests | `1.0` |
| `--concurrency` | Number of concurrent browsers | `2` |

### RAG Options

| Option | Description | Default |
|--------|-------------|---------|
| `--rag` | Enable RAG processing | `False` |
| `--rag_dir` | Directory for RAG output | `rag_data/` |
| `--chunk_size` | Size of text chunks in characters | `1000` |
| `--chunk_overlap` | Overlap between chunks in characters | `200` |

### Ollama Options

| Option | Description | Default |
|--------|-------------|---------|
| `--ollama` | Process RAG data with local Ollama | `False` |
| `--ollama_url` | URL of Ollama API endpoint | `http://localhost:11434` |
| `--ollama_model` | Ollama model to use for processing | `llama3` |
| `--embedding_model` | Model to use for generating embeddings | `nomic-embed-text` |

## Common Use Cases

### 1. Scraping Documentation for a Knowledge Base

```bash
python main.py --base_url https://docs.example.com/start --max_depth 2 --same_domain_only --rag
```

Perfect for creating training data from documentation sites.

### 2. Creating LLM Fine-Tuning Data

```bash
python main.py --base_url https://example.com/blog --max_depth 1 --rag --chunk_size 750 --chunk_overlap 150
```

Ideal for processing blog content for LLM fine-tuning.

### 3. Single Page with Detailed RAG Processing

```bash
python main.py --base_url https://example.com/article --max_depth 0 --rag --chunk_size 300 --chunk_overlap 100
```

Great for processing a single detailed article with fine-grained chunks.

### 4. Creating Embeddings for Semantic Search

```bash
python main.py --base_url https://docs.example.com/products --max_depth 1 --same_domain_only --rag --ollama
```

Perfect for generating embeddings that can be used for semantic search in AI applications.

## Understanding RAG Output

RAG processing creates a structured format for LLM training and retrieval:

1. Each chunk is saved as a separate JSON file with:
   - The text content
   - Metadata about its source
   - Positional information

2. Example RAG chunk:

```json
{
  "text": "The actual text content of the chunk...",
  "metadata": {
    "title": "Document Title",
    "url": "https://source-url.com/page",
    "source": "original_file.txt",
    "chunk_id": "a1b2c3d4_0",
    "chunk_index": 0,
    "total_chunks": 5
  }
}
```

3. With Ollama processing, chunks also include embeddings:

```json
{
  "text": "The actual text content of the chunk...",
  "embedding": [0.02, -0.14, 0.33, ...],
  "metadata": {
    "title": "Document Title",
    "url": "https://source-url.com/page",
    "source": "original_file.txt",
    "chunk_id": "a1b2c3d4_0",
    "chunk_index": 0,
    "total_chunks": 5,
    "ollama_model": "llama3",
    "embedding_model": "nomic-embed-text",
    "ollama_processed": true
  }
}
```

4. The chunks can be used for:
   - Training LLMs on domain-specific content
   - Building retrieval systems for RAG applications
   - Creating knowledge bases with source tracking
   - Semantic search using the generated embeddings

## Limitations of the Lite Version

WebScrape Lite intentionally omits certain advanced features:

- No PDF output format (text only)
- No streaming processing for improved performance
- No web dashboard for monitoring
- No advanced domain restriction
- No proxy support or advanced browser features

These limitations help keep the tool simple and focused while still providing powerful core functionality. However, the Ollama integration provides advanced capabilities for those who need semantic search and embedding generation.

## Testing

To verify your installation is working correctly:

```bash
python test_scraper.py
```

This will run a simple test of the core functionality and RAG processing.

## Next Steps

Once you're comfortable with WebScrape Lite, you can explore:

1. Using RAG chunks in retrieval systems
2. Customizing the RAG processor for different chunk strategies
3. Exploring the full WebScrape project for advanced features
4. Creating your own processors for specialized content extraction
