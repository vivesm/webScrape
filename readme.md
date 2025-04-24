# webScrape

WebScrape is a Python-based web scraping tool that dynamically fetches web page links, downloads content as PDFs or text files, and handles cookie banners. The script uses Pyppeteer for headless browser automation and supports concurrency and delay configurations.

## Features

- Extracts links dynamically from a given URL
- Saves content in **PDF** or **text** format (text is now the default)
- Handles cookie banners automatically
- Efficient browser resource pooling
- Smart content comparison to avoid re-downloading identical content
- URL filtering with regex patterns
- Configurable concurrency and delays
- Progress reporting with tqdm
- Exponential backoff retry mechanism
- Rotating user agents
- **RAG Processing** - Convert scraped content into chunks for LLM training and retrieval
- **Web Dashboard** - Monitor and control scraping jobs via web interface
- **Streaming Processing** - Process content as it downloads for better performance (2.2x faster)
- **Crawl Depth Control** - Limit how many levels deep to follow links
- **Test Mode** - Configurable test mode to process a specific number of pages
- **History Tracking** - Track and manage downloaded URLs with persistent storage
- **Duplicate Prevention** - Prevent re-downloading the same URLs
- **Settings Memory** - Remember previous settings across sessions

## Requirements

- Python 3.7+
- Virtual environment recommended

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

Run the script with the desired options:

```bash
python main.py --base_url <URL> [options]
```

### Command-Line Arguments

| Argument           | Description                                      | Default                                       |
|--------------------|--------------------------------------------------|-----------------------------------------------|
| `--base_url`       | The URL to scrape links from                     | `https://docs.workato.com/projects.html`     |
| `--output_format`  | Output format for files (`pdf` or `text`)        | `text`                                       |
| `--test`           | Enable test mode                                 | Disabled                                     |
| `--test_count`     | Number of pages to process in test mode          | `2`                                          |
| `--delay`          | Delay (in seconds) between processing links      | `1.0`                                        |
| `--concurrency`    | Number of concurrent browsers to use             | `2`                                          |
| `--output_dir`     | Directory to save scraped content                | `output`                                     |
| `--same_domain_only`| Only follow links from the same domain          | Disabled                                     |
| `--include`        | Regex pattern to include URLs                    | None (include all)                           |
| `--exclude`        | Regex pattern to exclude URLs                    | None (exclude none)                          |
| `--timeout`        | Navigation timeout in seconds                    | `30`                                         |
| `--max_depth`      | Maximum link depth to crawl                      | `1` (only links on the start page)           |
| `--rag`            | Process scraped content for RAG                  | Disabled                                     |
| `--rag_dir`        | Directory to store RAG-processed data            | `rag_data`                                   |
| `--chunk_size`     | Size of text chunks for RAG (in characters)      | `1000`                                       |
| `--chunk_overlap`  | Overlap between text chunks for RAG              | `200`                                        |
| `--streaming`      | Enable streaming processing for better performance | Disabled                                   |
| `--stream_buffer`  | Size of streaming buffer in KB                   | `1024` (1MB)                                 |
| `--language`       | Filter content by language code                    | None (process all languages)                 |

### Example Usage

1. Scrape all links from a specific URL and save as PDFs:
   ```bash
   python main.py --base_url https://docs.workato.com/getting-started/what-is-workato.html --output_format pdf
   ```

2. Test mode (process a limited number of pages):
   ```bash
   python main.py --test --test_count 3 --base_url https://example.com
   ```

3. Only scrape URLs from the same domain:
   ```bash
   python main.py --base_url https://example.com --same_domain_only
   ```

4. Use regex patterns to filter URLs:
   ```bash
   python main.py --base_url https://example.com --include ".*docs.*" --exclude ".*login.*"
   ```

5. Increase concurrency for faster scraping:
   ```bash
   python main.py --base_url https://example.com --concurrency 4
   ```

6. Deep crawl up to 3 levels from the starting URL:
   ```bash
   python main.py --base_url https://example.com --max_depth 3 --same_domain_only
   ```

7. Single-page scrape without following any links:
   ```bash
   python main.py --base_url https://example.com --max_depth 0
   ```

8. Process content for RAG (Retrieval Augmented Generation):
   ```bash
   python main.py --base_url https://example.com --output_format text --rag
   ```

9. Customize RAG processing with different chunk sizes:
   ```bash
   python main.py --base_url https://example.com --output_format text --rag --chunk_size 500 --chunk_overlap 100
   ```

10. Start the web dashboard for monitoring:
   ```bash
   python dashboard_server.py --port 5000
   ```

11. Run with streaming processing for better performance:
   ```bash
   python main.py --base_url https://example.com --streaming
   ```

12. Filter content by language (only download English pages):
   ```bash
   python main.py --base_url https://example.com --language en
   ```

13. Filter content by language (only download Japanese pages):
   ```bash
   python main.py --base_url https://example.com --language ja
   ```

## RAG Processing

The RAG (Retrieval Augmented Generation) processing feature converts scraped content into a format suitable for training or augmenting large language models:

- Divides text into semantically meaningful chunks with configurable size and overlap
- Extracts metadata from content (title, source URL, dates, etc.)
- Stores each chunk as a JSON file with its metadata
- Creates an index file for easy retrieval
- Automatically handles text, HTML, and PDF input formats
- Extracts text and metadata from PDF files
- Cleans and normalizes text for better quality training data

### RAG Output Format

Each processed chunk is saved as a JSON file with the following structure:

```json
{
  "text": "The actual text content of the chunk...",
  "metadata": {
    "title": "Document Title",
    "url": "https://source-url.com/page",
    "date": "2023-05-15",
    "source": "original_file.txt",
    "doc_id": "a1b2c3d4",
    "chunk_id": "a1b2c3d4_0",
    "chunk_index": 0,
    "total_chunks": 5,
    "file_name": "original_file.txt",
    "file_type": "pdf",
    "processing_date": "2023-05-16T14:22:33.123456"
  }
}
```

### PDF Extraction Tool

The project includes a standalone PDF extraction tool for converting PDF files to text format:

```bash
python extract_pdfs.py --input_dir /path/to/pdf/files --output_dir /path/to/output
```

Options:
- `--input_dir`: Directory containing PDF files (required)
- `--output_dir`: Directory to save extracted text (defaults to input_dir/extracted)
- `--recursive`: Process subdirectories recursively

The tool extracts both text content and metadata from PDFs, which can then be used directly or processed further with the RAG processor.

## Architecture

The codebase is organized into separate modules:

- `main.py` - Entry point with argument parsing
- `web_scraper.py` - Main class coordinating the scraping process
- `link_extractor.py` - Handles extracting links from webpages
- `content_scraper.py` - Handles saving content as PDF or text
- `browser_pool.py` - Manages a pool of browser instances
- `retry_utils.py` - Provides retry functionality with exponential backoff
- `utils.py` - Common utility functions
- `rag_processor.py` - Processes content for RAG applications
- `pdf_extractor.py` - Extracts text and metadata from PDF files
- `extract_pdfs.py` - Standalone script for PDF text extraction
- `dashboard_server.py` - Web dashboard for monitoring and control
- `streaming_processor.py` - Streaming-based content processing

## Output

All scraped files are saved in the `output/` directory by default. Files are named based on the last part of the URL, sanitized for safe filenames.

RAG processed data is saved in the `rag_data/` directory by default, with each chunk as a separate JSON file and an index.json file for easy navigation.

## Web Dashboard

The web dashboard provides a graphical interface for monitoring and controlling scraping operations:

- Real-time status monitoring for current scraping jobs
- Resource usage statistics (CPU, memory, network)
- Job history and logs
- Easy job configuration and launching
- Performance metrics and visualizations

To start the dashboard:

```bash
python dashboard_server.py --port 5000 --host 127.0.0.1
```

Then open a web browser and navigate to `http://127.0.0.1:5000`.

### Dashboard Features

- **Scraper Status**: View the current state of scraping jobs
- **Resource Usage**: Monitor system resource consumption
- **Start New Job**: Configure and start scraping operations with saved settings
- **Test Mode**: Configure and run quick tests with a limited number of pages
- **Recent Jobs**: View history of completed jobs
- **Logs**: See real-time logs from scraping operations (with copy functionality)
- **Performance**: Track URLs processed per minute
- **Downloaded Links**: Manage downloaded URLs with multi-select and bulk deletion
- **File Progress**: View filenames being processed in real-time
- **Content Comparison**: See which files are skipped due to identical content
- **Force Stop**: Emergency stop functionality for stuck jobs

## Streaming Processing

The streaming processor provides memory-efficient content processing:

- Processes content as it downloads, rather than waiting for complete files
- Reduces memory usage for large files
- Improves overall performance by parallelizing download and processing
- Handles HTML and PDF content differently for optimal results
- **Offers 2.2x+ faster performance** in benchmark tests

The streaming processor is particularly useful for:
- Scraping large websites with many pages
- Extracting text from HTML pages efficiently
- Handling direct PDF downloads
- Reducing overall scraping time for large-scale operations

To enable streaming processing, use the `--streaming` flag:

```bash
python main.py --base_url https://example.com --streaming
```

You can also configure the streaming buffer size:

```bash
python main.py --base_url https://example.com --streaming --stream_buffer 2048
```

### Performance Testing

The streaming processor has been extensively tested and shows significant performance improvements:

| Metric                 | Regular Scraper | Streaming Processor | Improvement |
|------------------------|-----------------|---------------------|-------------|
| Average processing time| 0.293 sec/URL   | 0.130 sec/URL       | 2.26x faster|
| Content consistency    | Baseline        | 98.06% match        | Excellent   |
| Memory efficiency      | Higher          | Lower               | Better      |

The streaming processor maintains excellent content quality while processing URLs more than twice as fast as the regular scraper. These improvements are particularly noticeable when scraping large websites with many pages.

## URL History and Content Management

WebScrape includes a robust system for managing downloaded URLs and avoiding duplicates:

### Download History

- **SQLite Database**: Tracks all downloaded URLs in a persistent database
- **Domain Grouping**: URLs are organized by domain for easy navigation
- **File Metadata**: Stores file paths, sizes, and download timestamps
- **Bulk Management**: Select and delete multiple URLs at once
- **Domain Deletion**: Remove all URLs from a specific domain with one click
- **Duplicate Prevention**: Blocks re-downloading of already processed URLs (unless in test mode)

### Content Comparison

WebScrape uses smart content comparison to determine if a file needs to be redownloaded:

1. **Hash Comparison**: Both new and existing files are hashed using SHA-256
2. **Identical Content Detection**: Files are only saved if content has actually changed
3. **Informative Logging**: System logs whether content is identical or differs from existing
4. **Memory Efficiency**: Comparison is performed on streaming chunks for better performance
5. **Format-Specific Handling**: Different comparison methods for PDF and text files

This content comparison helps to:
- Avoid unnecessary downloads when content hasn't changed
- Prevent duplicate files with the same content
- Improve overall scraping efficiency
- Maintain a cleaner output directory

### Settings Memory

The dashboard remembers your previous settings, including:

- Base URL
- Output format
- Depth settings
- Test mode configuration
- Streaming options
- RAG processing settings

This makes it easier to run multiple jobs with similar configurations.

## Contributing

Contributions are welcome! Please fork the repository, make changes, and submit a pull request.

## License

This project is licensed under the MIT License.