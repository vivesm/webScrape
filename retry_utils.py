import asyncio
import logging
import random
from typing import Callable, TypeVar, Any, Optional, Dict, List
import time
import requests
from functools import wraps

T = TypeVar('T')

class RetryException(Exception):
    """Exception raised when maximum retries are exhausted."""
    pass

def calculate_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: float = 0.1) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current retry attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Random jitter factor (0-1)
    
    Returns:
        Delay time in seconds
    """
    # Calculate exponential backoff
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # Add jitter (randomness) to prevent thundering herd problem
    jitter_amount = delay * jitter
    delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)  # Ensure non-negative delay

async def async_retry(
    func: Callable[..., Any],
    *args: Any,
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on_exceptions: tuple = (Exception,),
    retry_on_status_codes: List[int] = None,
    **kwargs: Any
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to call
        *args: Positional arguments to pass to the function
        retries: Maximum number of retries
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retry_on_exceptions: Tuple of exceptions that trigger a retry
        retry_on_status_codes: List of HTTP status codes that trigger a retry
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Result of the function call
    
    Raises:
        RetryException: If maximum retries are exhausted
    """
    retry_on_status_codes = retry_on_status_codes or [429, 503, 500]
    last_exception = None
    
    for attempt in range(retries + 1):  # +1 because first attempt is not a retry
        try:
            result = await func(*args, **kwargs)
            
            # Check for HTTP status code if result is a response
            if hasattr(result, 'status_code') and result.status_code in retry_on_status_codes:
                delay = calculate_backoff(attempt, base_delay, max_delay)
                logging.warning(
                    f"Received status code {result.status_code}, "
                    f"retrying in {delay:.2f}s (attempt {attempt+1}/{retries})"
                )
                await asyncio.sleep(delay)
                continue
                
            return result
            
        except retry_on_exceptions as e:
            if attempt == retries:
                if last_exception:
                    raise RetryException(f"Maximum retries ({retries}) exceeded") from last_exception
                raise RetryException(f"Maximum retries ({retries}) exceeded") from e
            
            last_exception = e
            delay = calculate_backoff(attempt, base_delay, max_delay)
            
            # Log different messages for different types of exceptions
            if isinstance(e, requests.exceptions.Timeout):
                logging.warning(f"Request timed out, retrying in {delay:.2f}s (attempt {attempt+1}/{retries})")
            elif isinstance(e, requests.exceptions.ConnectionError):
                logging.warning(f"Connection error, retrying in {delay:.2f}s (attempt {attempt+1}/{retries})")
            elif isinstance(e, requests.exceptions.HTTPError):
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                logging.warning(f"HTTP error {status_code}, retrying in {delay:.2f}s (attempt {attempt+1}/{retries})")
            else:
                logging.warning(f"Error: {e}, retrying in {delay:.2f}s (attempt {attempt+1}/{retries})")
            
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    raise RetryException(f"Maximum retries ({retries}) exceeded")

def async_retry_decorator(
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on_exceptions: tuple = (Exception,),
    retry_on_status_codes: List[int] = None
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        retries: Maximum number of retries
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retry_on_exceptions: Tuple of exceptions that trigger a retry
        retry_on_status_codes: List of HTTP status codes that trigger a retry
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await async_retry(
                func, *args,
                retries=retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retry_on_exceptions=retry_on_exceptions,
                retry_on_status_codes=retry_on_status_codes,
                **kwargs
            )
        return wrapper
    return decorator