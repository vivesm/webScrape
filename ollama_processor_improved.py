import os
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from pathlib import Path

class OllamaProcessor:
    """
    Process RAG data using a local Ollama instance.
    
    This class sends processed text chunks to a local Ollama instance
    to generate embeddings or perform other LLM-related operations.
    """
    
    def __init__(
        self,
        rag_dir: str = "rag_data",
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3",
        batch_size: int = 10,
        embedding_model: str = "nomic-embed-text"
    ):
        """
        Initialize the Ollama processor.
        
        Args:
            rag_dir: Directory containing RAG data chunks
            ollama_url: URL of the Ollama API
            model: Ollama model to use
            batch_size: Number of chunks to process in a batch
            embedding_model: Model to use for embeddings
        """
        self.rag_dir = rag_dir
        self.ollama_url = ollama_url
        self.model = model
        self.batch_size = batch_size
        self.embedding_model = embedding_model
        
        # Create output directory if it doesn't exist
        Path(rag_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize counters
        self.processed_chunks = 0
        self.total_chunks = 0
        
    async def process_rag_data(self) -> Dict[str, Any]:
        """
        Process all RAG data chunks using Ollama.
        
        Returns:
            Dictionary with processing statistics
        """
        logging.info(f"Processing RAG data with Ollama model {self.model}...")
        
        # Verify Ollama is running
        if not await self._check_ollama_connection():
            logging.error(f"Could not connect to Ollama at {self.ollama_url}")
            return {
                "success": False,
                "processed_chunks": 0,
                "total_chunks": 0,
                "error": "Could not connect to Ollama"
            }
        
        # List RAG chunks
        chunk_files = list(Path(self.rag_dir).glob("*_chunk_*.json"))
        if not chunk_files:
            logging.warning(f"No RAG chunks found in {self.rag_dir}")
            return {
                "success": False,
                "processed_chunks": 0,
                "total_chunks": 0,
                "error": "No RAG chunks found"
            }
            
        self.total_chunks = len(chunk_files)
        logging.info(f"Found {self.total_chunks} RAG chunks to process")
        
        # Process chunks in batches
        batches = [chunk_files[i:i + self.batch_size] for i in range(0, len(chunk_files), self.batch_size)]
        
        for i, batch in enumerate(batches):
            logging.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} chunks)")
            await self._process_batch(batch)
            
        # Generate embeddings index
        await self._generate_embeddings_index()
        
        # Return statistics
        return {
            "success": True,
            "processed_chunks": self.processed_chunks,
            "total_chunks": self.total_chunks,
            "model": self.model,
            "embedding_model": self.embedding_model
        }
        
    async def _check_ollama_connection(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        # Log available models
                        models = [model["name"] for model in models_data.get("models", [])]
                        logging.info(f"Connected to Ollama. Available models: {', '.join(models)}")
                        
                        # Verify our model is available
                        if self.model not in models:
                            logging.warning(f"Model {self.model} not found in Ollama. Available models: {', '.join(models)}")
                            if models:
                                logging.info(f"Using {models[0]} instead")
                                self.model = models[0]
                            else:
                                logging.error("No models available in Ollama")
                                return False
                        return True
                    else:
                        logging.error(f"Failed to connect to Ollama: {response.status} {response.reason}")
                        return False
        except Exception as e:
            logging.error(f"Error connecting to Ollama: {e}")
            return False
            
    async def _process_batch(self, chunk_files: List[Path]) -> None:
        """
        Process a batch of RAG chunks.
        
        Args:
            chunk_files: List of chunk file paths to process
        """
        tasks = []
        for chunk_file in chunk_files:
            tasks.append(self._process_chunk(chunk_file))
            
        # Wait for all processing tasks to complete
        await asyncio.gather(*tasks)
        
    async def _process_chunk(self, chunk_file: Path) -> None:
        """
        Process a single RAG chunk with Ollama.
        
        Args:
            chunk_file: Path to the chunk file
        """
        try:
            # Read chunk data
            with open(chunk_file, "r", encoding="utf-8") as f:
                chunk_data = json.load(f)
                
            # Extract text
            text = chunk_data.get("text", "")
            if not text:
                logging.warning(f"No text found in chunk {chunk_file}")
                return
                
            # Generate embeddings for the chunk
            embedding = await self._generate_embedding(text)
            if embedding:
                # Add embedding to chunk data
                chunk_data["embedding"] = embedding
                
                # Add Ollama processing info to metadata
                if "metadata" not in chunk_data:
                    chunk_data["metadata"] = {}
                    
                chunk_data["metadata"]["ollama_model"] = self.model
                chunk_data["metadata"]["embedding_model"] = self.embedding_model
                chunk_data["metadata"]["ollama_processed"] = True
                
                # Save updated chunk data
                with open(chunk_file, "w", encoding="utf-8") as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                    
                self.processed_chunks += 1
                logging.debug(f"Processed chunk {chunk_file.name}")
                
        except Exception as e:
            logging.error(f"Error processing chunk {chunk_file}: {e}")
            
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding for the given text using Ollama.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            # Use the embeddings API endpoint
            endpoint = f"{self.ollama_url}/api/embeddings"
            
            # Prepare the request payload
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Return the embedding vector
                        return result.get("embedding", [])
                    else:
                        response_text = await response.text()
                        logging.error(f"Failed to generate embedding: {response.status} {response.reason} - {response_text}")
                        return None
                        
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            return None
            
    async def generate_response(self, prompt, max_retries=3, timeout=60):
        """
        Generate a response with built-in retry logic.
        
        Args:
            prompt: The prompt to generate a response for
            max_retries: Maximum number of retry attempts
            timeout: Timeout in seconds for the request
            
        Returns:
            The generated response or error message
        """
        retries = 0
        while retries < max_retries:
            try:
                async with asyncio.timeout(timeout):
                    # Use the generation API endpoint
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self.ollama_url}/api/generate",
                            json={"model": self.model, "prompt": prompt, "stream": False}
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                return result.get('response', 'No response generated')
                            else:
                                response_text = await response.text()
                                logging.error(f"Failed to generate response: {response.status} {response.reason} - {response_text}")
                                
            except asyncio.TimeoutError:
                retries += 1
                logging.warning(f"Timeout generating response (attempt {retries}/{max_retries})")
                await asyncio.sleep(2)  # Short delay before retry
                
            except Exception as e:
                retries += 1
                logging.error(f"Error generating response: {e}")
                await asyncio.sleep(2)  # Short delay before retry
                
            # If we have more retries, continue
            if retries < max_retries:
                logging.info(f"Retrying response generation (attempt {retries+1}/{max_retries})")
                
        return "Failed to generate response after multiple attempts."
            
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Query text
            top_k: Number of top results to return
            
        Returns:
            List of top matching chunks
        """
        try:
            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []
                
            # Load all chunks
            chunk_files = list(Path(self.rag_dir).glob("*_chunk_*.json"))
            results = []
            
            for chunk_file in chunk_files:
                try:
                    with open(chunk_file, "r", encoding="utf-8") as f:
                        chunk_data = json.load(f)
                        
                    # Skip chunks without embeddings
                    if "embedding" not in chunk_data:
                        continue
                        
                    # Calculate similarity score (cosine similarity)
                    chunk_embedding = chunk_data["embedding"]
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    
                    # Add to results
                    results.append({
                        "chunk_file": str(chunk_file),
                        "text": chunk_data.get("text", ""),
                        "metadata": chunk_data.get("metadata", {}),
                        "similarity": similarity
                    })
                    
                except Exception as e:
                    logging.error(f"Error processing chunk {chunk_file} for search: {e}")
                    
            # Sort results by similarity and return top_k
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logging.error(f"Error performing semantic search: {e}")
            return []
            
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (between -1 and 1)
        """
        if len(vec1) != len(vec2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
        
    async def _generate_embeddings_index(self) -> None:
        """
        Generate an index file for embeddings.
        """
        # Gather information about all processed chunks
        index = []
        chunk_files = list(Path(self.rag_dir).glob("*_chunk_*.json"))
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Only include chunks with embeddings
                if "embedding" not in data:
                    continue
                    
                # Extract key information for the index
                metadata = data.get("metadata", {})
                index.append({
                    "file": str(chunk_file),
                    "doc_id": metadata.get("doc_id", ""),
                    "chunk_id": metadata.get("chunk_id", ""),
                    "title": metadata.get("title", ""),
                    "has_embedding": True,
                    "embedding_model": metadata.get("embedding_model", self.embedding_model),
                    "ollama_model": metadata.get("ollama_model", self.model)
                })
            except Exception as e:
                logging.error(f"Error processing embeddings index for {chunk_file}: {e}")
                
        # Save the embeddings index
        index_file = os.path.join(self.rag_dir, "embeddings_index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Generated embeddings index with {len(index)} entries")
