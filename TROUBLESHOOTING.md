# Troubleshooting WebScrape Lite + Ollama RAG Integration

This guide addresses common errors you might encounter when using WebScrape Lite with Ollama for RAG processing.

## Common Errors

### 1. "Error generating response" in test_okta_rag.py

**Problem**: When running test_okta_rag.py, some queries fail with "Error generating response"

**Causes**:
- Timeout issues with Ollama API
- Context window limitations
- Malformed prompt or response format

**Solutions**:
```python
# Add timeout handling and retries
try:
    response = await processor.generate_response(prompt, timeout=60)
except Exception as e:
    print(f"Error generating response: {e}")
    response = "Failed to generate response. The model might be overloaded or the context too large."
```

### 2. "No RAG chunks found" when processing new directories

**Problem**: When running RAG on a new output directory, you get "No RAG chunks found"

**Causes**:
- PDF extraction failing silently
- HTML parsing issues with certain page formats
- Text content might be too small to chunk effectively

**Solutions**:
```bash
# Check if files were saved and have content
ls -la output_oie/
cat output_oie/example.txt | wc -c

# Force text extraction with explicit format
python main.py --base_url URL --rag --extract_text_only --output_format text
```

### 3. Browser cleanup errors

**Problem**: "RuntimeWarning: coroutine 'Launcher.killChrome' was never awaited"

**Cause**: Asyncio event loop closed before all cleanup tasks completed

**Solution**: This is a minor issue with Pyppeteer's cleanup. It doesn't affect functionality but can be addressed with:
```python
# Add in browser_pool.py
async def close_all(self):
    close_tasks = []
    for browser in self.browsers:
        if browser and not browser.process.returncode:
            close_tasks.append(asyncio.create_task(browser.close()))
    if close_tasks:
        await asyncio.gather(*close_tasks, return_exceptions=True)
```

### 4. RAG data not generating for specific content types

**Problem**: Some files don't get processed into RAG chunks

**Causes**:
- File size limitations
- Text encoding issues
- Format incompatibility

**Solution**: Check that files have valid content with:
```bash
# Validate output files have usable content
find output/ -type f -name "*.text" -size -100c
```

## Improving Error Handling

Add these improvements to ollama_processor.py:

```python
async def generate_response(self, prompt, max_retries=3, timeout=60):
    """Generate a response with built-in retry logic."""
    retries = 0
    while retries < max_retries:
        try:
            async with asyncio.timeout(timeout):
                response = await self.ollama_client.generate(
                    model=self.model,
                    prompt=prompt
                )
                return response.get('response', 'No response generated')
        except asyncio.TimeoutError:
            retries += 1
            logging.warning(f"Timeout generating response (attempt {retries}/{max_retries})")
            await asyncio.sleep(2)  # Short delay before retry
        except Exception as e:
            retries += 1
            logging.error(f"Error generating response: {e}")
            await asyncio.sleep(2)
    
    return "Failed to generate response after multiple attempts."
```

## Processing Large Documentation Sets

For large documentation sites, break up scraping into sections:

```bash
# Scrape main areas separately
python main.py --base_url "URL1" --rag --output_dir output_part1 --rag_dir rag_part1
python main.py --base_url "URL2" --rag --output_dir output_part2 --rag_dir rag_part2

# Then process separately
python test_okta_rag.py --rag_dir rag_part1
python test_okta_rag.py --rag_dir rag_part2
