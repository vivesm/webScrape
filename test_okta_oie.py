#!/usr/bin/env python3
"""
Test Okta Identity Engine RAG with Ollama

This script tests the RAG capabilities using the Okta Identity Engine documentation
that's been scraped and processed with Ollama.
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

async def test_rag_response(processor, query, top_k=3):
    """
    Generate a RAG-enhanced response for a query
    
    Args:
        processor: The OllamaProcessor instance
        query: The query to answer
        top_k: Number of chunks to retrieve
    """
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}")
    
    # Get relevant chunks
    results = await processor.semantic_search(query, top_k=top_k)
    
    if not results:
        print("No relevant context found for this query.")
        return
    
    print(f"Found {len(results)} relevant chunks:")
    for i, result in enumerate(results):
        similarity = result["similarity"]
        source = result.get("chunk_file", "Unknown")
        print(f"  {i+1}. {source} (similarity: {similarity:.4f})")
    
    # Build context from chunks
    context = "\n\n".join([
        f"Context {i+1}:\n{result['text']}"
        for i, result in enumerate(results)
    ])
    
    # Create a prompt with the retrieved context
    prompt = f"""You are a helpful assistant answering questions about Okta Identity Engine (OIE).
Use ONLY the following context to answer the question. If you can't answer
from the context, say you don't have enough information.

{context}

Question: {query}

Answer:"""
    
    # Generate the response
    print("\nGenerating response...")
    response = await processor.generate_response(prompt)
    
    print("\nRAG RESPONSE:")
    print(f"{'-'*80}")
    print(response)

async def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test Okta Identity Engine RAG with Ollama")
    parser.add_argument("--rag_dir", default="rag_data_oie", help="Directory containing RAG data")
    parser.add_argument("--ollama_url", default="http://localhost:11434", help="Ollama API URL")
    parser.add_argument("--model", default="qwen3:32b", help="Ollama model for generation")
    parser.add_argument("--embedding_model", default="nomic-embed-text", help="Model for embeddings")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    args = parser.parse_args()
    
    # Initialize the Ollama processor with existing data
    processor = OllamaProcessor(
        rag_dir=args.rag_dir,
        ollama_url=args.ollama_url,
        model=args.model,
        embedding_model=args.embedding_model
    )
    
    # Check connection
    if not await processor._check_ollama_connection():
        print("Failed to connect to Ollama. Make sure it's running.")
        return
    
    print(f"Connected to Ollama using model: {processor.model}")
    print(f"Using embedding model: {processor.embedding_model}")
    
    # Process sample queries (auto mode by default, can be overridden with --interactive flag)
    if not args.interactive:
        print("Auto-running sample queries. Use --interactive flag for manual input.")
        await processor.process_rag_data()  # Generate embeddings for existing chunks
        for query in SAMPLE_QUERIES:
            await test_rag_response(processor, query)
    else:
        use_samples = input("Use sample queries? (y/n): ").lower().startswith('y')
        # Process RAG data to ensure embeddings exist
        await processor.process_rag_data()
        
        if use_samples:
            for query in SAMPLE_QUERIES:
                await test_rag_response(processor, query)
        else:
            while True:
                query = input("\nEnter a question about Okta Identity Engine (or 'exit' to quit): ")
                if query.lower() in ('exit', 'quit', 'q'):
                    break
                    
                await test_rag_response(processor, query)
    
    print("\nTesting complete!")

if __name__ == "__main__":
    asyncio.run(main())
