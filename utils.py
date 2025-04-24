import os
import re
import logging
import hashlib
import random
from typing import Set, List, Optional, Dict, Any
from pathlib import Path
from urllib.parse import urlparse, urljoin

# List of common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

def get_random_user_agent() -> str:
    """Return a random user agent from the list of common user agents."""
    return random.choice(USER_AGENTS)

def create_headers(custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Create request headers with a random user agent.
    
    Args:
        custom_headers: Optional custom headers to include
        
    Returns:
        Dictionary of headers with random user agent
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",  # Do Not Track
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    if custom_headers:
        headers.update(custom_headers)
        
    return headers

def hash_file(file_path: str) -> Optional[str]:
    """
    Calculate the SHA256 hash of a file for comparison.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal digest of file hash or None if file doesn't exist
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return None

def hash_bytes(data_bytes: bytes) -> str:
    """
    Hash raw byte content.
    
    Args:
        data_bytes: Bytes to hash
        
    Returns:
        Hexadecimal digest of bytes hash
    """
    hasher = hashlib.sha256()
    hasher.update(data_bytes)
    return hasher.hexdigest()

def hash_text(text: str) -> str:
    """
    Hash text content.
    
    Args:
        text: Text to hash
        
    Returns:
        Hexadecimal digest of text hash
    """
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()

def sanitize_filename(url: str, index: int = 0) -> str:
    """
    Create a safe filename from a URL.
    
    Args:
        url: URL to convert to filename
        index: Optional numeric index to append for uniqueness
        
    Returns:
        Sanitized filename
    """
    # Get the path part of the URL
    parsed = urlparse(url)
    path = parsed.path
    
    # Use the last part of the path, or the domain if path is empty
    if path and path != '/':
        title_part = path.split("/")[-1][:50] or f"page-{index}"
    else:
        title_part = parsed.netloc.split(".")[-2][:50] or f"page-{index}"
    
    # Replace illegal filename characters
    title = re.sub(r'[\\/*?:"<>|]', "_", title_part)
    
    # Ensure we have something valid
    if not title:
        title = f"page-{index}"
        
    return title

def filter_links(links: Set[str], base_url: str = None, 
                 exclude_patterns: List[str] = None, 
                 include_patterns: List[str] = None,
                 same_domain_only: bool = False) -> Set[str]:
    """
    Filter links based on various criteria.
    
    Args:
        links: Set of links to filter
        base_url: Optional base URL to restrict to same domain
        exclude_patterns: List of regex patterns to exclude
        include_patterns: List of regex patterns to include
        same_domain_only: Whether to only include links from the same domain
        
    Returns:
        Filtered set of links
    """
    valid_links = set()
    skipped_links_count = 0
    skipped_external_domains = set()
    
    # Compile patterns if provided
    exclude_regex = [re.compile(pattern) for pattern in (exclude_patterns or [])]
    include_regex = [re.compile(pattern) for pattern in (include_patterns or [])]
    
    # Get base domain if needed
    base_domain = None
    if same_domain_only and base_url:
        base_domain = urlparse(base_url).netloc
        logging.info(f"Domain restriction enabled. Only following links in domain: {base_domain}")
    
    for link in links:
        # Skip if not an HTTP(S) URL
        if not link.startswith(("http://", "https://")):
            skipped_links_count += 1
            continue
            
        # Apply domain filter
        if same_domain_only and base_domain:
            link_domain = urlparse(link).netloc
            if link_domain != base_domain:
                skipped_external_domains.add(link_domain)
                continue
                
        # Apply exclusion patterns
        if exclude_regex and any(pattern.search(link) for pattern in exclude_regex):
            skipped_links_count += 1
            continue
            
        # Apply inclusion patterns
        if include_regex and not any(pattern.search(link) for pattern in include_regex):
            skipped_links_count += 1
            continue
            
        # Force HTTPS when possible
        if link.startswith("http://"):
            https_link = "https://" + link[7:]
            valid_links.add(https_link)
        else:
            valid_links.add(link)
    
    # Log filtering stats
    if same_domain_only and base_domain and skipped_external_domains:
        logging.info(f"Skipped {len(skipped_external_domains)} external domains: {', '.join(list(skipped_external_domains)[:5])}" + 
                    (f" and {len(skipped_external_domains) - 5} more..." if len(skipped_external_domains) > 5 else ""))
    
    logging.info(f"Link filtering: {len(links)} total, {len(valid_links)} valid, {skipped_links_count} skipped")
    
    return valid_links

def ensure_dir(dir_path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Directory path to ensure exists
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)