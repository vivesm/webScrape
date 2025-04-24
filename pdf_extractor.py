"""
PDF Extractor Module
=================

This module provides functionality for extracting text and metadata from PDF files,
making them accessible for RAG processing and other text analysis tasks. It uses
PyPDF2 under the hood but wraps it in an async interface for better integration
with the rest of the application.

Key Features:
- Extract text content from PDF files
- Extract metadata (title, author, etc.) from PDF files
- Clean and normalize extracted text
- Process PDF files in parallel
- Optional dependency (PyPDF2 can be absent)
- Support for batch processing entire directories

Usage Example:
------------
```python
# Create an extractor
extractor = PDFExtractor()

# Check if PDF extraction is available (PyPDF2 is installed)
if extractor.is_available():
    # Extract text and metadata from a PDF
    text, metadata = await extractor.extract_text_from_pdf("document.pdf")
    
    # Process all PDFs in a directory
    stats = await extractor.bulk_extract_directory(
        input_dir="pdfs/",
        output_dir="extracted_text/"
    )
    print(f"Processed {stats['processed']} of {stats['total']} PDFs")
```

Dependencies:
- PyPDF2 (optional but required for actual extraction)
- asyncio for async/await functionality
"""

import os
import logging
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import asyncio
import re

class PDFExtractor:
    """
    Extracts text content and metadata from PDF files.
    
    This class provides methods to extract text and metadata from PDF files
    using PyPDF2. It handles the complexities of PDF parsing, text extraction,
    and cleanup to produce clean, usable text for further processing.
    
    The class imports PyPDF2 dynamically, so it can still be instantiated even
    if PyPDF2 is not installed, though extraction functions will return empty
    results in that case.
    """
    
    def __init__(self):
        """
        Initialize the PDF extractor.
        
        This constructor attempts to import PyPDF2 dynamically. If the import
        succeeds, the extractor will be fully functional. If it fails, the
        extractor will still work but will return empty results.
        
        The dynamic import allows the application to run without PyPDF2 if
        PDF extraction is not needed.
        """
        # Import PyPDF2 dynamically to avoid requiring it unless needed
        try:
            import PyPDF2
            self.PyPDF2 = PyPDF2
            self.available = True
        except ImportError:
            self.available = False
            logging.warning("PyPDF2 not installed. PDF extraction will be limited.")
            logging.info("Install with: pip install PyPDF2")
    
    def is_available(self) -> bool:
        """
        Check if PDF extraction functionality is available.
        
        This method checks if PyPDF2 is installed and available for use.
        It's recommended to call this before attempting extraction.
        
        Returns:
            True if PyPDF2 is installed and available, False otherwise
        """
        return self.available
    
    async def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text and metadata from a PDF file.
        
        This is the main public method for extracting content from a PDF.
        It extracts both the text content (with page markers) and metadata
        such as title, author, and creation date.
        
        Args:
            pdf_path: Path to the PDF file to extract from
            
        Returns:
            Tuple containing:
              - The extracted text as a string (empty string if extraction fails)
              - A dictionary of metadata (keys are lowercase, values are strings)
              
        Note:
            The extraction happens in a thread pool to avoid blocking the event loop,
            since PDF parsing can be CPU-intensive.
        """
        # Return early if PyPDF2 is not available
        if not self.available:
            return "", {"error": "PyPDF2 not installed"}
            
        # Run the CPU-intensive extraction in a separate thread to avoid blocking the event loop
        return await asyncio.to_thread(self._extract_text_from_pdf_sync, pdf_path)
    
    def _extract_text_from_pdf_sync(self, pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Synchronous implementation of PDF text extraction.
        
        This internal method does the actual work of extracting text and metadata
        from a PDF file. It's called from extract_text_from_pdf via asyncio.to_thread
        to avoid blocking the event loop.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, metadata_dict)
            
        Note:
            - Adds page markers ("--- Page X ---") to help with context
            - Cleans the extracted text to remove common PDF extraction artifacts
            - Normalizes metadata keys by removing leading slashes and converting to lowercase
        """
        try:
            text_content = []
            metadata = {}
            
            with open(pdf_path, 'rb') as file:
                # Create PDF reader object
                reader = self.PyPDF2.PdfReader(file)
                
                # Extract metadata from document information
                if reader.metadata:
                    for key, value in reader.metadata.items():
                        if value and isinstance(value, str):
                            # Remove the leading slash from keys like '/Title'
                            clean_key = key.lstrip('/').lower()
                            metadata[clean_key] = value
                
                # Extract text from each page
                for page_num, page in enumerate(reader.pages):
                    # Extract text from this page
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Add page number information to help with context
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    
                # Join all text with double newlines for separation
                full_text = "\n\n".join(text_content)
                
                # Clean the text to remove common PDF extraction artifacts
                full_text = self._clean_pdf_text(full_text)
                
                return full_text, metadata
                
        except Exception as e:
            # Log the error and return empty results
            logging.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return "", {"error": str(e)}
    
    def _clean_pdf_text(self, text: str) -> str:
        """
        Clean text extracted from PDF.
        
        This method applies various transformations to improve the quality of
        extracted PDF text, which often contains artifacts from the PDF format.
        
        Args:
            text: Raw text extracted from PDF
            
        Returns:
            Cleaned text with normalized whitespace and formatting
            
        Note:
            PDF text extraction often produces inconsistent spacing and
            line breaks. This method attempts to normalize these issues.
        """
        # Replace multiple spaces with a single space (common PDF artifact)
        text = re.sub(r' {2,}', ' ', text)
        
        # Replace excessive newlines with double newlines (for paragraph separation)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing spaces from each line
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    async def bulk_extract_directory(self, input_dir: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process all PDF files in a directory and extract their text content.
        
        This method provides batch processing capability for PDF extraction.
        It can either:
        1. Just extract text/metadata from PDFs (if output_dir is None)
        2. Extract and save the text/metadata to output files (if output_dir is provided)
        
        Args:
            input_dir: Directory containing PDF files to process
            output_dir: Optional directory to save extracted text files
                        If None, text is extracted but not saved
            
        Returns:
            Statistics dictionary with the following keys:
            - total: Total number of PDF files found
            - processed: Number of PDFs successfully processed
            - output_dir: Directory where outputs were saved (if applicable)
            - error: Error message (if PyPDF2 is not available)
            
        Note:
            This method processes PDFs concurrently for better performance.
            The directory structure is preserved if output_dir is specified.
        """
        # Return early if PyPDF2 is not available
        if not self.available:
            return {"error": "PyPDF2 not installed", "processed": 0}
            
        # Find all PDF files (including in subdirectories)
        input_path = Path(input_dir)
        pdf_files = list(input_path.glob("**/*.pdf"))
        
        # Create output directory if specified
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        processed = 0
        tasks = []
        
        # Create tasks for each PDF file
        for pdf_file in pdf_files:
            if output_dir:
                # Preserve directory structure
                rel_path = pdf_file.relative_to(input_path)
                output_file = Path(output_dir) / f"{rel_path.stem}.txt"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Create extraction and save task
                tasks.append(self._extract_and_save(str(pdf_file), str(output_file)))
            else:
                # Just extract without saving
                tasks.append(self.extract_text_from_pdf(str(pdf_file)))
        
        # Process all PDFs concurrently
        results = await asyncio.gather(*tasks)
        
        # Count successful extractions
        for result in results:
            if isinstance(result, tuple):
                text, metadata = result
                if text:  # Non-empty text means success
                    processed += 1
            elif isinstance(result, bool) and result:  # Boolean True from _extract_and_save
                processed += 1
        
        # Return statistics
        return {
            "total": len(pdf_files),
            "processed": processed,
            "output_dir": output_dir
        }
    
    async def _extract_and_save(self, pdf_path: str, output_path: str) -> bool:
        """
        Extract text from PDF and save to a file.
        
        This internal method combines extraction and saving into a single operation.
        It also saves metadata to a separate file if available.
        
        Args:
            pdf_path: Path to PDF file to process
            output_path: Path to save the extracted text
            
        Returns:
            True if successful, False otherwise
            
        Note:
            If metadata is available, it's saved to a separate file with
            the same name as the output file but with "_metadata.txt" appended.
        """
        try:
            # Extract text and metadata
            text, metadata = await self.extract_text_from_pdf(pdf_path)
            
            if text:
                # Save extracted text
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                    
                # Save metadata if it exists (to a separate file)
                if metadata:
                    metadata_path = f"{os.path.splitext(output_path)[0]}_metadata.txt"
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        for key, value in metadata.items():
                            f.write(f"{key}: {value}\n")
                
                logging.info(f"Extracted text from {pdf_path} to {output_path}")
                return True
            else:
                logging.warning(f"No text extracted from {pdf_path}")
                return False
                
        except Exception as e:
            logging.error(f"Error processing {pdf_path}: {e}")
            return False