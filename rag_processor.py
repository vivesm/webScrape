import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from bs4 import BeautifulSoup
import hashlib
import re
from datetime import datetime

class RAGProcessor:
    """
    Processes scraped content into formats suitable for RAG (Retrieval Augmented Generation).
    
    This class converts HTML/PDF content into structured text chunks with metadata
    that can be used to train or augment large language models.
    """
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str = "rag_data",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata_fields: List[str] = None
    ):
        """
        Initialize the RAG processor.
        
        Args:
            input_dir: Directory containing scraped content
            output_dir: Directory to save processed RAG data
            chunk_size: Target size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
            metadata_fields: List of metadata fields to extract
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.metadata_fields = metadata_fields or ["title", "url", "date", "source"]
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize counters
        self.total_files = 0
        self.processed_files = 0
        self.total_chunks = 0
        
    async def process_directory(self) -> Dict[str, Any]:
        """
        Process all files in the input directory.
        
        Returns:
            Dictionary with processing statistics
        """
        logging.info(f"Processing files in {self.input_dir} for RAG data...")
        
        # List files in input directory
        input_files = list(Path(self.input_dir).glob("*.*"))
        self.total_files = len(input_files)
        
        # Process each file
        tasks = []
        for file_path in input_files:
            if file_path.suffix.lower() == ".pdf":
                # PDF files need special handling
                tasks.append(self._process_pdf_file(str(file_path)))
            elif file_path.suffix.lower() in [".txt", ".html"]:
                # Text and HTML files
                tasks.append(self._process_text_file(str(file_path)))
                
        # Wait for all processing tasks to complete
        await asyncio.gather(*tasks)
        
        # Generate index file
        self._generate_index_file()
        
        # Return statistics
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_chunks": self.total_chunks,
            "output_dir": self.output_dir
        }
        
    async def _process_text_file(self, file_path: str) -> None:
        """
        Process a text file for RAG.
        
        Args:
            file_path: Path to the text file
        """
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract filename for later use
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            
            # Extract metadata from content
            metadata = self._extract_metadata(content, file_path)
            
            # Handle HTML content
            if file_path.endswith(".html"):
                soup = BeautifulSoup(content, "html.parser")
                
                # Extract title if not already in metadata
                if "title" not in metadata and soup.title:
                    metadata["title"] = soup.title.get_text(strip=True)
                    
                # Extract main content (remove scripts, styles, etc.)
                for tag in soup(["script", "style", "meta", "link", "noscript"]):
                    tag.decompose()
                    
                content = soup.get_text(separator="\n")
                
            # Clean up the text
            content = self._clean_text(content)
            
            # Create chunks
            chunks = self._chunk_text(content)
            
            # Save chunks as individual JSON files
            doc_id = self._generate_doc_id(file_path)
            chunk_files = []
            
            for i, chunk in enumerate(chunks):
                # Create chunk metadata
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_name": file_name,
                    "processing_date": datetime.now().isoformat()
                })
                
                # Create chunk data
                chunk_data = {
                    "text": chunk,
                    "metadata": chunk_metadata
                }
                
                # Save chunk
                chunk_file = os.path.join(self.output_dir, f"{file_base}_chunk_{i}.json")
                with open(chunk_file, "w", encoding="utf-8") as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                    
                chunk_files.append(chunk_file)
                self.total_chunks += 1
                
            self.processed_files += 1
            logging.info(f"Processed {file_path} into {len(chunks)} chunks")
            
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            
    async def _process_pdf_file(self, file_path: str) -> None:
        """
        Process a PDF file for RAG.
        
        This extracts text from PDF using the PDFExtractor class.
        
        Args:
            file_path: Path to the PDF file
        """
        try:
            # Import PDF extractor here to keep it optional
            from pdf_extractor import PDFExtractor
            
            # Check for an already extracted text file first
            text_file = file_path.replace(".pdf", ".txt")
            if os.path.exists(text_file):
                await self._process_text_file(text_file)
                return
                
            # Extract text from PDF
            extractor = PDFExtractor()
            if not extractor.is_available():
                logging.warning(f"PyPDF2 not installed. Cannot extract text from PDF: {file_path}")
                logging.info("Install PyPDF2 with: pip install PyPDF2")
                return
                
            # Extract the text and metadata
            text, metadata = await extractor.extract_text_from_pdf(file_path)
            
            if not text:
                logging.warning(f"No text could be extracted from PDF: {file_path}")
                return
                
            # Extract filename for later use
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            
            # Combine extracted metadata with what we can determine
            pdf_metadata = self._extract_metadata(text, file_path)
            
            # Add PDF-specific metadata from extractor
            for key, value in metadata.items():
                if key not in pdf_metadata and value:
                    pdf_metadata[key] = value
                    
            # Clean up the text
            text = self._clean_text(text)
            
            # Create chunks
            chunks = self._chunk_text(text)
            
            # Save chunks as individual JSON files
            doc_id = self._generate_doc_id(file_path)
            chunk_files = []
            
            for i, chunk in enumerate(chunks):
                # Create chunk metadata
                chunk_metadata = pdf_metadata.copy()
                chunk_metadata.update({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_name": file_name,
                    "file_type": "pdf",
                    "processing_date": datetime.now().isoformat()
                })
                
                # Create chunk data
                chunk_data = {
                    "text": chunk,
                    "metadata": chunk_metadata
                }
                
                # Save chunk
                chunk_file = os.path.join(self.output_dir, f"{file_base}_chunk_{i}.json")
                with open(chunk_file, "w", encoding="utf-8") as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                    
                chunk_files.append(chunk_file)
                self.total_chunks += 1
                
            self.processed_files += 1
            logging.info(f"Processed PDF {file_path} into {len(chunks)} chunks")
            
        except ImportError:
            logging.warning(f"PyPDF2 not installed. Cannot extract text from PDF: {file_path}")
            logging.info("Install PyPDF2 with: pip install PyPDF2")
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            
    def _extract_metadata(self, content: str, file_path: str) -> Dict[str, str]:
        """
        Extract metadata from content and filename.
        
        Args:
            content: Text content
            file_path: Path to the file
            
        Returns:
            Dictionary of metadata fields
        """
        metadata = {}
        
        # Extract filename-based metadata
        file_name = os.path.basename(file_path)
        file_base = os.path.splitext(file_name)[0]
        
        # Set basic metadata
        metadata["source"] = file_name
        metadata["file_path"] = file_path
        
        # Try to extract a title from the first non-empty line
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:  # Reasonable title length
                metadata["title"] = line
                break
                
        # If we couldn't find a title, use the filename
        if "title" not in metadata:
            metadata["title"] = file_base.replace("_", " ").title()
            
        # Extract date - first try from content
        date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
            r"(\d{2}/\d{2}/\d{4})",  # MM/DD/YYYY
            r"([A-Z][a-z]+ \d{1,2},? \d{4})"  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content[:1000])  # Look only in the first 1000 chars
            if match:
                metadata["date"] = match.group(1)
                break
                
        # If no date found, use file modification time
        if "date" not in metadata:
            mod_time = os.path.getmtime(file_path)
            metadata["date"] = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d")
            
        # Try to extract a URL if it exists in the content
        url_pattern = r"https?://[^\s]+"
        url_match = re.search(url_pattern, content[:2000])
        if url_match:
            metadata["url"] = url_match.group(0)
            
        return metadata
        
    def _clean_text(self, text: str) -> str:
        """
        Clean text content for processing.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text
        """
        # Replace multiple newlines with a single newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        
        # Remove excessive whitespace
        text = re.sub(r" {2,}", " ", text)
        
        return text
        
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # If text is shorter than chunk size, return it as a single chunk
        if len(text) <= self.chunk_size:
            return [text]
            
        # Split text into chunks
        start = 0
        while start < len(text):
            # Get a chunk of text
            end = start + self.chunk_size
            
            # If we're at the end of the text, just add the last chunk
            if end >= len(text):
                chunks.append(text[start:])
                break
                
            # Find a good breaking point - prefer sentence end
            # Look backwards from the end to find a good breaking point
            break_point = end
            
            # Try to find a sentence end (., !, ?) followed by whitespace
            for i in range(end, max(start, end - self.chunk_overlap), -1):
                if i < len(text) and text[i-1] in ".!?" and (i >= len(text) or text[i].isspace()):
                    break_point = i
                    break
                    
            # If we couldn't find a sentence break, try a paragraph break
            if break_point == end:
                for i in range(end, max(start, end - self.chunk_overlap), -1):
                    if i < len(text) and text[i-1] == "\n" and (i >= len(text) or text[i] == "\n"):
                        break_point = i
                        break
                        
            # If we still don't have a good break, just break at a space
            if break_point == end:
                for i in range(end, max(start, end - self.chunk_overlap), -1):
                    if i < len(text) and text[i].isspace():
                        break_point = i
                        break
                        
            # Add the chunk
            chunks.append(text[start:break_point])
            
            # Move start position, ensuring overlap
            start = max(start + 1, break_point - self.chunk_overlap)
            
        return chunks
        
    def _generate_doc_id(self, file_path: str) -> str:
        """
        Generate a unique document ID based on the file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Unique document ID
        """
        # Create a hash of the file path
        hasher = hashlib.md5()
        hasher.update(file_path.encode("utf-8"))
        
        # Use first 8 characters of the hash
        return hasher.hexdigest()[:8]
        
    def _generate_index_file(self) -> None:
        """
        Generate an index file of all processed documents.
        """
        # Gather information about all JSON files
        index = []
        json_files = list(Path(self.output_dir).glob("*.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # Extract key information for the index
                metadata = data.get("metadata", {})
                index.append({
                    "file": str(json_file),
                    "doc_id": metadata.get("doc_id", ""),
                    "chunk_id": metadata.get("chunk_id", ""),
                    "title": metadata.get("title", ""),
                    "date": metadata.get("date", ""),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "total_chunks": metadata.get("total_chunks", 0)
                })
            except Exception as e:
                logging.error(f"Error processing index for {json_file}: {e}")
                
        # Save the index
        index_file = os.path.join(self.output_dir, "index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Generated index file with {len(index)} entries")