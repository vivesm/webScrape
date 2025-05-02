#!/usr/bin/env python3
"""
Lightweight test script for Okta Identity Engine RAG with Ollama

This script tests the RAG capabilities using simplified prompts and shorter timeouts.
"""

import asyncio
import logging
from ollama_processor import OllamaProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Sample queries about Okta Identity Engine
SAMPLE_QUERIES = [
    "What is Okta Identity Engine?",
    "How do I configure passwordless authentication?",
    "What features does PAM provide?",
    "What is Identity Governance?",
    "What is device fingerprinting in Okta?"
]

async def test_rag_response(processor, query, top_k=3, timeout=25):
    """
    Generate a RAG-enhanced response for a query with shorter timeout
    
    Args:
        processor: The OllamaProcessor instance
        query: The query to answer
        top_k: Number of chunks to retrieve
        timeout: Shorter timeout in seconds
    """
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")
    
    # Get relevant chunks
    results = await processor.semantic_search(query, top_k=top_k)
    
    if not results:
        print("No relevant context found for this query.")
        return
    
    print(f"Found {len(results)} relevant chunks")
    
    # Extract just the text from the top chunk for a simpler prompt
    context = results[0]['text'] if results else ""
    
    # Create a very simple prompt with minimal context
    prompt = f"Answer about Okta Identity Engine based on this context: {context}\n\nQuestion: {query}"
    
    # Generate the response with shorter timeout
    print("Generating response...")
    try:
        response = await processor.generate_response(prompt, timeout=timeout)
        print("\nRAG RESPONSE:")
        print(f"{'-'*60}")
        print(response)
    except Exception as e:
        print(f"Error generating response: {e}")

async def display_chunks(rag_dir="rag_data_oie"):
    """
    Display chunk statistics to verify extraction worked
    """
    from pathlib import Path
    import json
    
    chunks = list(Path(rag_dir).glob("*_chunk_*.json"))
    print(f"Found {len(chunks)} chunks in {rag_dir}")
    
    # Show sample of chunk content
    if chunks:
        with open(chunks[0], 'r') as f:
            sample = json.load(f)
        
        print("\nSample chunk metadata:")
        metadata = sample.get('metadata', {})
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        text = sample.get('text', '')
        print(f"\nSample text ({len(text)} chars):")
        print(f"{text[:200]}...")

async def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Lightweight Test for Okta Identity Engine RAG")
    parser.add_argument("--rag_dir", default="rag_data_oie", help="Directory containing RAG data")
    parser.add_argument("--show_chunks", action="store_true", help="Display chunk statistics only")
    parser.add_argument("--query", help="Run a single specific query")
    args = parser.parse_args()
    
    # Show chunk stats if requested
    if args.show_chunks:
        await display_chunks(args.rag_dir)
        return
    
    # Initialize the Ollama processor with existing data
    processor = OllamaProcessor(
        rag_dir=args.rag_dir,
        ollama_url="http://localhost:11434",
        model="qwen3:32b",
        embedding_model="nomic-embed-text"
    )
    
    # Check connection
    if not await processor._check_ollama_connection():
        print("Failed to connect to Ollama. Make sure it's running.")
        return
    
    print(f"Connected to Ollama using model: {processor.model}")
    
    # Just show the single specified query if provided
    if args.query:
        await test_rag_response(processor, args.query)
        return
        
    # Process first sample query only to verify everything works
    await test_rag_response(processor, SAMPLE_QUERIES[0])
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(main())
