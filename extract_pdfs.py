#!/usr/bin/env python3

import asyncio
import logging
import argparse
import os
from pathlib import Path

from pdf_extractor import PDFExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def main():
    """
    Script to extract text from PDF files in a directory.
    
    This utility extracts text content from PDF files and saves it to text files,
    making it useful for preparing PDFs for RAG processing or other text analysis.
    """
    parser = argparse.ArgumentParser(description="Extract text from PDF files")
    
    parser.add_argument("--input_dir", 
                      required=True,
                      help="Directory containing PDF files")
    parser.add_argument("--output_dir", 
                      default=None,
                      help="Directory to save extracted text (defaults to input_dir/extracted)")
    parser.add_argument("--recursive", 
                      action="store_true",
                      help="Process subdirectories recursively")
                      
    args = parser.parse_args()
    
    # Set default output directory if not specified
    if not args.output_dir:
        args.output_dir = os.path.join(args.input_dir, "extracted")
    
    # Check if PyPDF2 is installed
    try:
        import PyPDF2
    except ImportError:
        logging.error("PyPDF2 is required but not installed.")
        logging.info("Install with: pip install PyPDF2")
        return 1
    
    # Check if input directory exists
    input_path = Path(args.input_dir)
    if not input_path.exists():
        logging.error(f"Input directory '{args.input_dir}' does not exist.")
        return 1
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find PDF files
    pattern = "**/*.pdf" if args.recursive else "*.pdf"
    pdf_files = list(input_path.glob(pattern))
    
    if not pdf_files:
        logging.error(f"No PDF files found in '{args.input_dir}'.")
        return 1
    
    logging.info(f"Found {len(pdf_files)} PDF files to process.")
    
    # Initialize PDF extractor
    extractor = PDFExtractor()
    if not extractor.is_available():
        logging.error("PDF extraction not available. Please install PyPDF2.")
        return 1
    
    # Process all PDFs
    stats = await extractor.bulk_extract_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir
    )
    
    # Output summary
    logging.info(f"PDF extraction completed:")
    logging.info(f"  - Total PDFs: {stats['total']}")
    logging.info(f"  - Successfully processed: {stats['processed']}")
    logging.info(f"  - Output directory: {stats['output_dir']}")
    
    if stats['processed'] == 0:
        logging.warning("No PDFs were successfully processed.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)