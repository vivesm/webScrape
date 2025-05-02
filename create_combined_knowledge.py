#!/usr/bin/env python3
"""
Create a combined knowledge document from RAG chunks

This script combines multiple RAG chunks into a single markdown file
that can be uploaded to Claude, ChatGPT, or other LLMs.
"""

import os
import glob
import json
import argparse
from pathlib import Path

def create_combined_document(rag_dir, output_file, format="markdown"):
    """Create a combined document from RAG chunks"""
    print(f"Creating combined document from {rag_dir}...")
    
    # Ensure rag_dir exists
    if not os.path.exists(rag_dir):
        print(f"Error: Directory {rag_dir} does not exist")
        return False
    
    # Get all chunk files
    chunk_files = sorted(glob.glob(f"{rag_dir}/*_chunk_*.json"))
    if not chunk_files:
        print(f"Error: No chunk files found in {rag_dir}")
        return False
    
    print(f"Found {len(chunk_files)} chunk files")
    
    # Create output file with appropriate format
    with open(output_file, 'w') as out:
        # Write header
        if format == "markdown":
            out.write(f"# Combined Knowledge Document\n\n")
            out.write(f"Generated from {len(chunk_files)} chunks in {rag_dir}\n\n")
            out.write("---\n\n")
        else:  # Plain text
            out.write(f"COMBINED KNOWLEDGE DOCUMENT\n\n")
            out.write(f"Generated from {len(chunk_files)} chunks in {rag_dir}\n\n")
            out.write(f"{'=' * 50}\n\n")
        
        # Process each chunk
        for i, chunk_file in enumerate(chunk_files):
            try:
                with open(chunk_file, 'r') as f:
                    data = json.load(f)
                
                # Extract information
                text = data.get('text', '')
                source = data.get('source', os.path.basename(chunk_file))
                chunk_id = os.path.basename(chunk_file).replace('.json', '')
                
                if not text:
                    print(f"Warning: No text found in {chunk_file}, skipping")
                    continue
                
                # Write chunk information
                if format == "markdown":
                    out.write(f"## Chunk {i+1}: {chunk_id}\n\n")
                    out.write(f"**Source**: {source}\n\n")
                    out.write(f"{text}\n\n")
                    out.write("---\n\n")
                else:  # Plain text
                    out.write(f"CHUNK {i+1}: {chunk_id}\n\n")
                    out.write(f"Source: {source}\n\n")
                    out.write(f"{text}\n\n")
                    out.write(f"{'=' * 50}\n\n")
                
            except Exception as e:
                print(f"Error processing {chunk_file}: {e}")
    
    print(f"Successfully created combined document: {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Create a combined knowledge document from RAG chunks")
    parser.add_argument("--rag_dir", default="rag_data", help="Directory containing RAG chunks")
    parser.add_argument("--output", default="combined_knowledge.md", help="Output filename")
    parser.add_argument("--format", choices=["markdown", "text"], default="markdown", 
                        help="Output format (markdown or plain text)")
    args = parser.parse_args()
    
    # Determine output extension based on format
    output_path = Path(args.output)
    if args.format == "markdown" and output_path.suffix.lower() not in ['.md', '.markdown']:
        output_path = output_path.with_suffix('.md')
    elif args.format == "text" and output_path.suffix.lower() not in ['.txt', '.text']:
        output_path = output_path.with_suffix('.txt')
    
    success = create_combined_document(args.rag_dir, str(output_path), args.format)
    
    if success:
        print(f"\nNext steps:")
        print(f"1. Review the combined document: {output_path}")
        print(f"2. Upload the file to ChatGPT, Claude, or other LLM")
        print(f"3. Use the content for queries about the documentation")

if __name__ == "__main__":
    main()
