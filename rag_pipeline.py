#!/usr/bin/env python3
"""
Complete RAG Pipeline Script

This script provides a complete pipeline for:
1. Scraping a website
2. Processing it into RAG chunks
3. Generating embeddings using Ollama
4. Creating a combined knowledge document for upload to LLMs

Usage:
    python rag_pipeline.py --url "https://example.com" --output_name "my_knowledge"
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from pathlib import Path
import time
import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def execute_command(cmd, show_output=True):
    """Execute a shell command and return its output"""
    logging.info(f"Executing: {' '.join(cmd)}")
    
    try:
        if show_output:
            # Show output in real-time
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Print output in real-time
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            return process.returncode == 0
        else:
            # Capture output and return success/failure
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
    
    except Exception as e:
        logging.error(f"Error executing command: {e}")
        return False

def run_pipeline(url, output_name, depth=2, rag_dir=None, ollama_model="qwen3:32b", 
                 chunk_size=800, chunk_overlap=150, embed_model="nomic-embed-text",
                 format="markdown"):
    """Run the complete RAG pipeline"""
    
    # Set up directory names
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = f"output_{output_name}_{timestamp}"
    
    if rag_dir is None:
        rag_dir = f"rag_data_{output_name}_{timestamp}"
    
    # Create directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(rag_dir, exist_ok=True)
    
    try:
        # Step 1: Scrape the website
        logging.info(f"Step 1: Scraping {url} (depth: {depth})...")
        scrape_success = execute_command([
            "python", "main.py",
            "--base_url", url,
            "--max_depth", str(depth),
            "--output_dir", output_dir,
            "--rag",
            "--rag_dir", rag_dir,
            "--chunk_size", str(chunk_size),
            "--chunk_overlap", str(chunk_overlap),
            "--ollama",
            "--embedding_model", embed_model,
            "--model", ollama_model
        ])
        
        if not scrape_success:
            logging.error("Scraping failed")
            return False
        
        # Step 2: Check if RAG data was generated
        chunk_files = list(glob.glob(f"{rag_dir}/*_chunk_*.json"))
        if not chunk_files:
            logging.error(f"No chunk files found in {rag_dir}")
            return False
        
        logging.info(f"Generated {len(chunk_files)} RAG chunks")
        
        # Step 3: Create combined knowledge document
        combined_file = f"{output_name}_combined.md"
        logging.info(f"Step 3: Creating combined knowledge document {combined_file}...")
        
        knowledge_success = execute_command([
            "python", "create_combined_knowledge.py",
            "--rag_dir", rag_dir,
            "--output", combined_file,
            "--format", format
        ])
        
        if not knowledge_success:
            logging.error("Failed to create combined knowledge document")
            return False
        
        # Step 4: Generate sample queries for testing
        logging.info(f"Pipeline completed successfully!")
        logging.info(f"\nOutputs:")
        logging.info(f"  - Scraped content: {output_dir}/")
        logging.info(f"  - RAG chunks: {rag_dir}/")
        logging.info(f"  - Combined document: {combined_file}")
        
        # Provide usage instructions
        logging.info(f"\nNext steps:")
        logging.info(f"1. Upload {combined_file} to ChatGPT or Claude")
        logging.info(f"2. Ask questions about the content")
        logging.info(f"3. For local testing with Ollama:")
        logging.info(f"   python test_rag_stream.py --rag_dir {rag_dir} --query \"your question here\"")
        
        return True
        
    except Exception as e:
        logging.error(f"Pipeline error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run complete RAG pipeline")
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument("--output_name", required=True, help="Base name for output files")
    parser.add_argument("--depth", type=int, default=2, help="Scraping depth")
    parser.add_argument("--rag_dir", help="RAG data directory (default: auto-generated)")
    parser.add_argument("--ollama_model", default="qwen3:32b", help="Ollama model for generation")
    parser.add_argument("--embed_model", default="nomic-embed-text", help="Embedding model")
    parser.add_argument("--chunk_size", type=int, default=800, help="Chunk size for RAG")
    parser.add_argument("--chunk_overlap", type=int, default=150, help="Chunk overlap for RAG")
    parser.add_argument("--format", choices=["markdown", "text"], default="markdown", 
                        help="Output format for combined document")
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print(f"Starting RAG Pipeline for {args.url}")
    print("="*80 + "\n")
    
    success = run_pipeline(
        args.url, 
        args.output_name,
        depth=args.depth,
        rag_dir=args.rag_dir,
        ollama_model=args.ollama_model,
        embed_model=args.embed_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        format=args.format
    )
    
    if success:
        print("\n" + "="*80)
        print(f"RAG Pipeline Completed Successfully!")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print(f"RAG Pipeline Failed")
        print("="*80 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
