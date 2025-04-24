#!/usr/bin/env python3

import asyncio
import logging
import argparse
import os
import json
from pathlib import Path

from rag_processor import RAGProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def main():
    """
    Example script to demonstrate RAG processing on existing files.
    
    This script processes text or HTML files in a given directory and converts them
    into RAG-friendly chunks with metadata, ready for use with LLMs.
    """
    parser = argparse.ArgumentParser(description="Process files for RAG (Retrieval Augmented Generation)")
    
    parser.add_argument("--input_dir", 
                      default="output",
                      help="Directory containing files to process")
    parser.add_argument("--output_dir", 
                      default="rag_data",
                      help="Directory to store RAG-processed data")
    parser.add_argument("--chunk_size",
                      type=int,
                      default=1000,
                      help="Size of text chunks (in characters)")
    parser.add_argument("--chunk_overlap",
                      type=int,
                      default=200,
                      help="Overlap between text chunks (in characters)")
    parser.add_argument("--sample",
                      action="store_true",
                      help="Display a sample of generated chunks")
                      
    args = parser.parse_args()
    
    # Check if input directory exists and has files
    input_path = Path(args.input_dir)
    if not input_path.exists():
        logging.error(f"Input directory '{args.input_dir}' does not exist.")
        return
        
    files = list(input_path.glob("*.*"))
    if not files:
        logging.error(f"No files found in '{args.input_dir}'.")
        return
        
    logging.info(f"Found {len(files)} files to process in '{args.input_dir}'.")
    
    # Create and run the RAG processor
    processor = RAGProcessor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    stats = await processor.process_directory()
    
    # Output summary
    logging.info(f"RAG processing completed: {stats['processed_files']} files, {stats['total_chunks']} chunks")
    logging.info(f"Data saved to {args.output_dir}/")
    
    # Display a sample chunk if requested
    if args.sample and stats['total_chunks'] > 0:
        # Find a sample chunk file
        sample_files = list(Path(args.output_dir).glob("*.json"))
        if sample_files and len(sample_files) > 0:
            # Skip index.json
            sample_files = [f for f in sample_files if f.name != "index.json"]
            if sample_files:
                sample_file = sample_files[0]
                
                with open(sample_file, "r", encoding="utf-8") as f:
                    sample_data = json.load(f)
                
                logging.info("\n" + "="*50)
                logging.info("SAMPLE CHUNK:")
                logging.info("="*50)
                logging.info(f"File: {sample_file}")
                logging.info("Metadata:")
                for key, value in sample_data.get("metadata", {}).items():
                    logging.info(f"  {key}: {value}")
                
                # Show a preview of the text
                text = sample_data.get("text", "")
                preview = text[:500] + "..." if len(text) > 500 else text
                logging.info("\nText Preview:")
                logging.info(preview)
                logging.info("="*50)

if __name__ == "__main__":
    asyncio.run(main())