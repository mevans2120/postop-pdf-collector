"""Rate limiting utilities for controlling request rates."""

import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional


class RateLimiter:
    """Simple rate limiter for controlling request rates to domains."""
    
    def __init__(self, max_requests: float = 2.0):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per second
        """
        self.max_requests = max_requests
        self.min_interval = 1.0 / max_requests if max_requests > 0 else 0
        self.last_request_time: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()
    
    async def acquire(self, domain: Optional[str] = None) -> None:
        """
        Wait if necessary to maintain rate limit.
        
        Args:
            domain: Domain to rate limit (None for global limit)
        """
        if self.min_interval <= 0:
            return
        
        domain = domain or "global"
        
        async with self._lock:
            current_time = time.time()
            last_time = self.last_request_time[domain]
            
            if last_time > 0:
                elapsed = current_time - last_time
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
            
            self.last_request_time[domain] = time.time()
    
    def reset(self, domain: Optional[str] = None) -> None:
        """
        Reset rate limiter for a domain.
        
        Args:
            domain: Domain to reset (None to reset all)
        """
        if domain:
            self.last_request_time.pop(domain, None)
        else:
            self.last_request_time.clear()


class TokenBucketRateLimiter:
    """Token bucket rate limiter for more sophisticated rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket rate limiter.
        
        Args:
            rate: Token refill rate per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            current_time = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = current_time - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = current_time
            
            # Try to acquire tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            
            # Update tokens after wait
            self.tokens = min(
                self.capacity,
                self.tokens + wait_time * self.rate
            )
            self.tokens -= tokens
            return True
    
    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        current_time = time.time()
        elapsed = current_time - self.last_update
        return min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )