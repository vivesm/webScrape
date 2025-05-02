#!/usr/bin/env python3
"""
Simplified Ollama tester that uses lighter models and shorter prompts
"""

import os
import sys
import json
import asyncio
import aiohttp
import argparse

async def test_model(model, prompt, max_tokens=100, 
                    ollama_url="http://localhost:11434"):
    """Test a specific model with streaming enabled"""
    print(f"Testing model: {model}")
    print(f"Prompt: {prompt}")
    print(f"Max tokens: {max_tokens}")
    print("Streaming response...")
    
    try:
        # Setup payload with streaming
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens
            }
        }
        
        # Connect with short timeout
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ollama_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status} - {error_text}")
                    return
                
                # Process streaming response
                full_response = ""
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
                            print(chunk, end="", flush=True)
                            chunks_received += 1
                            
                            # Early return after some chunks to avoid timeouts
                            if chunks_received >= 10 or len(full_response) > 150:
                                print("\n\n[Early exit for testing]")
                                break
                                
                            # Check for done
                            if data.get("done", False):
                                break
                                
                    except json.JSONDecodeError:
                        pass
                    
                    # Simple timeout
                    if asyncio.get_event_loop().time() - start_time > 10:
                        print("\n\n[Timeout after 10 seconds]")
                        break
                        
                print(f"\n\nReceived {chunks_received} chunks ({len(full_response)} chars)")
                print(f"Time taken: {asyncio.get_event_loop().time() - start_time:.1f}s")
    except Exception as e:
        print(f"Error: {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description="Test Ollama with simple prompts")
    parser.add_argument("--model", default="", help="Specific model to test")
    args = parser.parse_args()

    # Get available models
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                if response.status == 200:
                    models_data = await response.json()
                    models = [model["name"] for model in models_data.get("models", [])]
                    print(f"Available models: {', '.join(models)}")
                else:
                    print(f"Failed to connect to Ollama: {response.status}")
                    return
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return

    # Test the models
    if args.model:
        # Test only the specified model
        if args.model not in models:
            print(f"Model '{args.model}' not found in available models")
            return
        await test_model(args.model, "Hello, how are you?")
    else:
        # Try with a few different models (prefer smaller ones)
        test_models = []
        
        # Try to find smaller/faster models first
        for candidate in ["llama3.2:3b", "gemma3:4b", "mistral:latest", "llama2:latest"]:
            if candidate in models:
                test_models.append(candidate)
                
        # Add the first model if we don't have any matches
        if not test_models and models:
            test_models.append(models[0])
            
        # Test each model
        for model in test_models:
            print("\n" + "="*40)
            await test_model(model, "Hello, how are you?")
            print("="*40 + "\n")
            await asyncio.sleep(1)  # Short pause between models

if __name__ == "__main__":
    asyncio.run(main())
