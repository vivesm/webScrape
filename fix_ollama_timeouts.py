#!/usr/bin/env python3
"""
Fix Ollama Timeout Issues

This script modifies how we connect to Ollama to avoid timeout issues:
1. Uses stream mode instead of blocking response
2. Implements chunked processing of responses
3. Sets proper context length limits
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from pathlib import Path

# Set logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def test_ollama_connection(ollama_url="http://localhost:11434", model="qwen3:32b"):
    """Test connection to Ollama and return model information"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ollama_url}/api/tags") as response:
                if response.status == 200:
                    models_data = await response.json()
                    models = [model["name"] for model in models_data.get("models", [])]
                    print(f"Connected to Ollama. Available models: {', '.join(models)}")
                    return True, models
                else:
                    print(f"Failed to connect to Ollama: {response.status} {response.reason}")
                    return False, []
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return False, []

async def stream_ollama_response(prompt, model="qwen3:32b", ollama_url="http://localhost:11434", 
                                max_tokens=2000, timeout=30):
    """
    Stream response from Ollama to avoid timeout issues.
    
    This is much more reliable than waiting for the full response at once.
    """
    try:
        # Setup the request with streaming enabled
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        # Use a faster timeout for initial connection
        conn_timeout = aiohttp.ClientTimeout(total=10)  
        
        # Stream the response in chunks
        full_response = ""
        print("Streaming response...")
        
        async with aiohttp.ClientSession(timeout=conn_timeout) as session:
            async with session.post(f"{ollama_url}/api/generate", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return f"Error: HTTP {response.status} - {error_text}"
                
                # Process the stream
                start_time = asyncio.get_event_loop().time()
                chunks_received = 0
                
                async for line in response.content:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            chunk = data["response"]
                            full_response += chunk
                            chunks_received += 1
                            
                            # Print progress every 5 chunks
                            if chunks_received % 5 == 0:
                                elapsed = asyncio.get_event_loop().time() - start_time
                                print(f"Received {chunks_received} chunks ({len(full_response)} chars) in {elapsed:.1f}s")
                            
                            # Check for done flag
                            if data.get("done", False):
                                break
                                
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON: {line}")
                    
                    # Check for timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        print(f"Stream timeout after {timeout}s")
                        break
                
        return full_response
    except asyncio.TimeoutError:
        return "Error: Connection timeout"
    except Exception as e:
        return f"Error: {str(e)}"

async def generate_embeddings(text, model="nomic-embed-text", ollama_url="http://localhost:11434"):
    """Generate embeddings with better error handling"""
    try:
        # Use the embeddings API endpoint with shorter timeout
        conn_timeout = aiohttp.ClientTimeout(total=10)
        
        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": text
        }
        
        async with aiohttp.ClientSession(timeout=conn_timeout) as session:
            async with session.post(f"{ollama_url}/api/embeddings", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("embedding", [])
                else:
                    print(f"Failed to generate embedding: {response.status}")
                    return None
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

async def main():
    """Test improved Ollama interaction"""
    import argparse
    parser = argparse.ArgumentParser(description="Test Ollama with streaming responses")
    parser.add_argument("--model", default="qwen3:32b", help="Model to use")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    parser.add_argument("--max_tokens", type=int, default=1000, help="Max tokens to generate")
    parser.add_argument("--prompt", default="Explain quantum computing in simple terms", 
                        help="Prompt to send")
    args = parser.parse_args()
    
    # Test connection
    success, models = await test_ollama_connection()
    if not success:
        print("Failed to connect to Ollama. Please check if it's running.")
        return
    
    if args.model not in models:
        print(f"Warning: Model {args.model} not found. Available models: {', '.join(models)}")
        if models:
            print(f"Falling back to {models[0]}")
            args.model = models[0]
        else:
            print("No models available. Please check Ollama installation.")
            return
    
    # Test streaming response
    print(f"\nTesting streaming response with model {args.model}...")
    print(f"Prompt: {args.prompt}")
    print(f"Timeout: {args.timeout}s, Max tokens: {args.max_tokens}")
    
    response = await stream_ollama_response(
        prompt=args.prompt,
        model=args.model,
        max_tokens=args.max_tokens,
        timeout=args.timeout
    )
    
    print("\nFinal response:")
    print("="*60)
    print(response)
    print("="*60)
    
    # Test embedding generation
    print("\nTesting embedding generation...")
    embedding = await generate_embeddings("This is a test")
    if embedding:
        print(f"Successfully generated embedding of size {len(embedding)}")
    else:
        print("Failed to generate embedding")

if __name__ == "__main__":
    asyncio.run(main())
