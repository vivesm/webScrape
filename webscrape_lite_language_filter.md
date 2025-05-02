# Language Filtering in WebScrape Lite

WebScrape Lite now supports language filtering to help you target specific language content during web scraping operations.

## Overview

Many websites offer content in multiple languages, typically organized with language codes in the URL path (e.g., `/en/`, `/fr/`, `/de/`). With the language filtering feature, you can:

- Focus scraping on content in a specific language
- Avoid duplicative content across multiple languages
- Build language-specific RAG datasets

## Using Language Filtering

### Command Line Option

```bash
python main.py --base_url https://example.com --language en
```

The `--language` parameter accepts a language code (typically a two-letter ISO code):

- `en` - English (default)
- `fr` - French
- `de` - German
- `es` - Spanish
- `ja` - Japanese
- etc.

You can also specify `all` to disable language filtering:

```bash
python main.py --base_url https://example.com --language all
```

### How It Works

When you specify a language:

1. The scraper looks for URLs containing the language pattern (e.g., `/en/` for English)
2. URLs that don't contain the specified language pattern are filtered out
3. This filtering is implemented by adding the language pattern to the URL include patterns

### Example Scenarios

#### Scraping English Documentation

```bash
python main.py --base_url https://docs.example.com --language en --rag
```

#### Creating Multilingual Training Data

To scrape content in multiple languages separately:

```bash
# Scrape English content
python main.py --base_url https://docs.example.com --language en --output_dir output_en --rag_dir rag_data_en

# Scrape Spanish content
python main.py --base_url https://docs.example.com --language es --output_dir output_es --rag_dir rag_data_es
```

#### Scraping All Languages

```bash
python main.py --base_url https://docs.example.com --language all
```

## Combining with Other Filters

The language filter can be combined with other URL filtering options:

```bash
python main.py --base_url https://docs.example.com --language en --include ".*docs.*" --exclude ".*archive.*"
```

## Limitations

- The language filter assumes the website uses language codes in URL paths
- Some websites might use different patterns for language identification
- The filter looks for the exact pattern (e.g., `/en/`), so non-standard formats might not work

## Advanced Use Cases

### Scraping Multiple Language Variants

For sites with regional language variants (e.g., English US vs. English UK):

```bash
# For English US
python main.py --base_url https://docs.example.com --include "/en-us/"

# For English UK
python main.py --base_url https://docs.example.com --include "/en-gb/"
```

### Custom Language Pattern

If a site uses non-standard language indicators:

```bash
python main.py --base_url https://docs.example.com --include "language=en"
