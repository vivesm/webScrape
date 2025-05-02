# Ollama RAG Cheatsheet for WebScrape Lite

## Quick Start Commands

### Test Ollama RAG Integration
```bash
python test_ollama_rag.py
```

### Scrape and Process with Ollama
```bash
python main.py --base_url https://example.com --rag --ollama
```

### Check Ollama Status
```bash
ps aux | grep ollama | grep -v grep
ollama list
```

## Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--ollama_url` | Ollama API endpoint | `http://localhost:11434` |
| `--ollama_model` | LLM model to use | `llama3` |
| `--embedding_model` | Model for embeddings | `nomic-embed-text` |
| `--chunk_size` | Size of text chunks | `1000` |
| `--chunk_overlap` | Overlap between chunks | `200` |

## Common Troubleshooting

1. **Is Ollama running?**
   ```bash
   ps aux | grep ollama | grep -v grep
   ```

2. **Which models are available?**
   ```bash
   ollama list
   ```

3. **Pull missing models:**
   ```bash
   ollama pull llama3
   ollama pull nomic-embed-text
   ```

4. **Check embeddings index:**
   ```bash
   cat rag_data/embeddings_index.json | head
   ```

## Sample Queries for Testing

- "What is recipe design?"
- "How do I handle errors in recipes?"
- "Explain data flow in automation workflows"
- "What are the key considerations for recipes?"

## Structure of RAG Data

- Each chunk is stored as a JSON file
- Embeddings are included in each chunk
- Metadata contains source info, chunk ID, etc.
- `embeddings_index.json` provides quick access to all chunks

## Testing Flow

1. Start Ollama service
2. Run test script or main script with --ollama flag
3. Verify semantic search results
4. Check RAG-enhanced responses
