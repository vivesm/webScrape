#!/usr/bin/env python3
"""
Fix RAG data extraction for Okta Identity Engine documentation.

This script processes HTML files in the output directory and ensures they're
properly converted to text chunks for RAG processing.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def extract_text_from_html(file_path):
    """Extract clean text from HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove scripts, styles, etc.
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up text (remove excessive newlines, etc.)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n\n'.join(lines)
        
        return text
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
        return None

async def create_chunks(text, chunk_size=800, chunk_overlap=150, metadata=None):
    """Split text into overlapping chunks."""
    if not text or len(text) < chunk_size / 2:
        # Text too small to chunk effectively
        logging.warning(f"Text too small to chunk effectively ({len(text)} chars)")
        return []
        
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        # Calculate end position with overlap
        end = min(start + chunk_size, len(text))
        
        # If not the first chunk, include overlap
        if start > 0:
            start = max(0, start - chunk_overlap)
            
        # Extract chunk text
        chunk_text = text[start:end]
        
        # Create chunk data
        chunk_data = {
            "text": chunk_text,
            "metadata": metadata or {},
            "chunk_id": str(chunk_id)
        }
        
        # Add chunk info to metadata
        chunk_data["metadata"]["char_start"] = start
        chunk_data["metadata"]["char_end"] = end
        chunk_data["metadata"]["chunk_size"] = len(chunk_text)
        
        chunks.append(chunk_data)
        
        # Move to next chunk
        start = end
        chunk_id += 1
        
    return chunks

async def process_file(input_file, output_dir, chunk_size=800, chunk_overlap=150):
    """Process a single file into RAG chunks."""
    try:
        # Extract filename and create base metadata
        filename = os.path.basename(input_file)
        doc_id = os.path.splitext(filename)[0]
        
        # Create metadata for this file
        metadata = {
            "source": str(input_file),
            "doc_id": doc_id,
            "title": doc_id.replace("-", " ").title()
        }
        
        # Extract text content from HTML
        text = await extract_text_from_html(input_file)
        if not text:
            logging.warning(f"No text extracted from {input_file}")
            return False
            
        # Create chunks from text
        chunks = await create_chunks(text, chunk_size, chunk_overlap, metadata)
        if not chunks:
            logging.warning(f"No chunks created for {input_file}")
            return False
            
        # Save chunks to output directory
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(output_dir, f"{doc_id}_chunk_{i}.json")
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
                
        logging.info(f"Created {len(chunks)} chunks for {input_file}")
        return True
        
    except Exception as e:
        logging.error(f"Error processing {input_file}: {e}")
        return False

async def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Fix RAG data extraction for OIE docs")
    parser.add_argument("--input_dir", default="output_oie", help="Input directory with HTML files")
    parser.add_argument("--output_dir", default="rag_data_oie", help="Output directory for RAG chunks")
    parser.add_argument("--chunk_size", type=int, default=800, help="Chunk size in characters")
    parser.add_argument("--chunk_overlap", type=int, default=150, help="Overlap between chunks")
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get all HTML files
    html_files = []
    for ext in [".html", ".htm", ".text"]:
        html_files.extend(list(Path(args.input_dir).glob(f"*{ext}")))
        
    if not html_files:
        logging.error(f"No HTML files found in {args.input_dir}")
        return 1
        
    logging.info(f"Found {len(html_files)} HTML files to process")
    
    # Process files
    results = []
    for file in html_files:
        result = await process_file(
            file, 
            args.output_dir, 
            args.chunk_size, 
            args.chunk_overlap
        )
        results.append(result)
        
    # Create index file
    chunk_files = list(Path(args.output_dir).glob("*_chunk_*.json"))
    index = []
    
    for chunk_file in chunk_files:
        try:
            with open(chunk_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Extract key information for the index
            metadata = data.get("metadata", {})
            index.append({
                "file": str(chunk_file),
                "doc_id": metadata.get("doc_id", ""),
                "chunk_id": metadata.get("chunk_id", ""),
                "title": metadata.get("title", ""),
                "has_embedding": False
            })
        except Exception as e:
            logging.error(f"Error processing index for {chunk_file}: {e}")
            
    # Save the index
    index_file = os.path.join(args.output_dir, "index.json")
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        
    # Print summary
    success_count = sum(results)
    logging.info(f"Processing complete: {success_count}/{len(html_files)} files processed")
    logging.info(f"Created {len(chunk_files)} chunks in {args.output_dir}")
    
    if len(chunk_files) > 0:
        logging.info("SUCCESS: RAG chunks were created successfully")
        return 0
    else:
        logging.error("ERROR: No RAG chunks were created")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
