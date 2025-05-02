#!/usr/bin/env python3
"""
Test Ollama RAG Integration

This script demonstrates how to use the OllamaProcessor class to:
1. Connect to a local Ollama instance
2. Perform semantic search on existing RAG data
3. Generate responses using RAG data

Requirements:
- Ollama running locally with the specified models
- Existing RAG data in the rag_data/ directory
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any
from ollama_processor import OllamaProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Sample queries to test semantic search
SAMPLE_QUERIES = [
    "What is recipe design?",
    "How do I handle errors in recipes?",
    "What are the key considerations for automation workflows?",
    "Tell me about data flow in recipes"
]

async def test_semantic_search(processor: OllamaProcessor, query: str, top_k: int = 3) -> None:
    """
    Test semantic search functionality
    
    Args:
        processor: The OllamaProcessor instance
        query: The search query
        top_k: Number of top results to display
    """
    print(f"\n\n{'=' * 60}")
    print(f"SEMANTIC SEARCH: {query}")
    print(f"{'=' * 60}")
    
    results = await processor.semantic_search(query, top_k=top_k)
    
    if not results:
        print("No search results found.")
        return
        
    print(f"Found {len(results)} relevant chunks\n")
    
    for i, result in enumerate(results):
        similarity = result["similarity"]
        text = result["text"]
        metadata = result["metadata"]
        
        print(f"\nRESULT {i+1} - Similarity: {similarity:.4f}")
        print(f"Source: {metadata.get('file_name', 'Unknown')}")
        print(f"Chunk: {metadata.get('chunk_id', 'Unknown')}")
        print(f"{'-' * 60}")
        print(text[:300] + "..." if len(text) > 300 else text)
    
async def test_rag_response(processor: OllamaProcessor, query: str, top_k: int = 3) -> None:
    """
    Test RAG-based response generation
    
    Args:
        processor: The OllamaProcessor instance
        query: The user query
        top_k: Number of top chunks to use for context
    """
    print(f"\n\n{'=' * 60}")
    print(f"RAG RESPONSE: {query}")
    print(f"{'=' * 60}")
    
    # First, get the relevant chunks using semantic search
    results = await processor.semantic_search(query, top_k=top_k)
    
    if not results:
        print("No relevant context found.")
        direct_response = await processor.generate_response(query)
        print("\nDIRECT RESPONSE (without RAG):")
        print(f"{'-' * 60}")
        print(direct_response)
        return
    
    # Build the context from the top results
    context = ""
    for i, result in enumerate(results):
        context += f"Context {i+1}:\n{result['text']}\n\n"
    
    # Build a prompt with the context and query
    rag_prompt = f"""I'll provide you with some context information, then ask a question.
Please answer the question based on the provided context.

{context}

Question: {query}

Answer:"""
    
    # Generate the response
    response = await processor.generate_response(rag_prompt)
    
    # Display the response
    print("\nRAG-ENHANCED RESPONSE:")
    print(f"{'-' * 60}")
    print(response)

async def main():
    """
    Main function to run the Ollama RAG tests
    """
    # Initialize the Ollama processor
    # We're using the same model configuration found in the existing data
    processor = OllamaProcessor(
        rag_dir="rag_data",
        ollama_url="http://localhost:11434",
        model="qwen3:32b",  # Match existing model in embeddings_index.json
        embedding_model="nomic-embed-text"
    )
    
    # Check Ollama connection
    print(f"Checking connection to Ollama at {processor.ollama_url}...")
    connection_ok = await processor._check_ollama_connection()
    
    if not connection_ok:
        print("Failed to connect to Ollama. Please make sure Ollama is running.")
        print(f"Expected URL: {processor.ollama_url}")
        print(f"Expected model: {processor.model}")
        print(f"Expected embedding model: {processor.embedding_model}")
        return
    
    print(f"Successfully connected to Ollama!")
    print(f"Using model: {processor.model}")
    print(f"Using embedding model: {processor.embedding_model}")
    
    # Check if embeddings index exists
    index_file = os.path.join(processor.rag_dir, "embeddings_index.json")
    if not os.path.exists(index_file):
        print(f"Embeddings index not found at {index_file}")
        print("Please run the main.py script with --rag --ollama options first")
        return
        
    # Print index info
    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)
        print(f"Found embeddings index with {len(index)} entries")
    
    # Get user query or use sample queries
    use_samples = input("Use sample queries? (y/n): ").lower().startswith('y')
    
    if use_samples:
        # Test semantic search with sample queries
        for query in SAMPLE_QUERIES:
            await test_semantic_search(processor, query)
            await test_rag_response(processor, query)
    else:
        # Ask for custom query
        while True:
            query = input("\nEnter a query (or 'exit' to quit): ")
            if query.lower() in ('exit', 'quit', 'q'):
                break
                
            await test_semantic_search(processor, query)
            await test_rag_response(processor, query)
    
    print("\nTest completed!")

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
