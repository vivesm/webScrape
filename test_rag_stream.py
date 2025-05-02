#!/usr/bin/env python3
"""
Test RAG with streaming response generation

This script uses the streaming version of OllamaProcessor to avoid timeout issues
"""

import os
import sys
import asyncio
import logging
import argparse
from ollama_processor_stream import OllamaProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Sample queries about Okta for testing
SAMPLE_QUERIES = {
    "okta_workflows": [
        "What is Okta Workflows?",
        "How do I build flows in Okta Workflows?"
    ],
    "okta_identity": [
        "What is Okta Identity Engine?",
        "What is device fingerprinting in Okta?"
    ]
}

async def test_streaming_response(processor, query, max_tokens=200, timeout=15):
    """Test streaming response generation with a query"""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")
    
    # Find relevant chunks
    results = await processor.semantic_search(query, top_k=2)
    
    if not results:
        print("No relevant chunks found")
        return
        
    print(f"Found {len(results)} relevant chunks. Top match: {results[0]['chunk_file']}")
    
    # Simplified prompt for faster responses
    context = results[0]['text']
    prompt = f"Answer briefly based on this context: {context}\n\nQ: {query}"
    
    # Generate streaming response
    print("\nGenerating response (streaming)...")
    response = await processor.generate_response(prompt, max_tokens=max_tokens, timeout=timeout)
    
    print("\nResponse:")
    print(f"{'-'*60}")
    print(response)
    print(f"{'-'*60}")

async def show_embeddings_info(rag_dir):
    """Show info about embeddings"""
    from pathlib import Path
    import json
    
    # Check if embeddings index exists
    index_path = os.path.join(rag_dir, "embeddings_index.json")
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            index = json.load(f)
        print(f"Found {len(index)} chunks with embeddings in {rag_dir}")
    else:
        print(f"No embeddings index found in {rag_dir}")
    
    # Check chunk files
    chunk_files = list(Path(rag_dir).glob("*_chunk_*.json"))
    print(f"Total chunks: {len(chunk_files)}")
    
    # Check if any chunk has embeddings
    has_embeddings = 0
    for chunk_file in chunk_files[:10]:  # Just check first 10
        with open(chunk_file, 'r') as f:
            data = json.load(f)
            if "embedding" in data:
                has_embeddings += 1
    
    print(f"Checked 10 chunks, {has_embeddings} have embeddings")

async def main():
    parser = argparse.ArgumentParser(description="Test RAG with streaming responses")
    parser.add_argument("--rag_dir", default="rag_data", help="Directory with RAG data")
    parser.add_argument("--query", help="Specific query to test")
    parser.add_argument("--model", default="llama2:latest", help="Model to use")
    parser.add_argument("--timeout", type=int, default=15, help="Response timeout")
    parser.add_argument("--product", default="okta_workflows", 
                       choices=["okta_workflows", "okta_identity"],
                       help="Product to query about")
    parser.add_argument("--info", action="store_true", help="Show embeddings info only")
    args = parser.parse_args()
    
    # Just show embeddings info if requested
    if args.info:
        await show_embeddings_info(args.rag_dir)
        return
    
    # Initialize the Ollama processor with streaming support
    processor = OllamaProcessor(
        rag_dir=args.rag_dir,
        model=args.model,
    )
    
    # Check connection
    if not await processor._check_ollama_connection():
        print("Failed to connect to Ollama. Make sure it's running.")
        return
    
    print(f"Connected to Ollama using model: {processor.model}")
    
    # Process RAG data to ensure embeddings exist
    print("Checking RAG data...")
    await processor.process_rag_data()
    
    # Test a specific query if provided
    if args.query:
        await test_streaming_response(processor, args.query, timeout=args.timeout)
        return
    
    # Otherwise run sample queries for the selected product
    queries = SAMPLE_QUERIES.get(args.product, [])
    for query in queries:
        await test_streaming_response(processor, query, timeout=args.timeout)
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(main())
