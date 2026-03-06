"""Rate limiting for Instagram Graph API."""

import time
from collections import deque
from threading import Lock

from .config import config


class RateLimiter:
    """Rolling window rate limiter for API calls."""

    def __init__(self, max_requests: int = None, window_seconds: int = None):
        self.max_requests = max_requests or config.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or config.RATE_LIMIT_WINDOW
        self.requests: deque = deque()
        self._lock = Lock()

    def _cleanup_old_requests(self):
        """Remove requests outside the current window."""
        now = time.time()
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding the rate limit."""
        with self._lock:
            self._cleanup_old_requests()
            return len(self.requests) < self.max_requests

    def record_request(self):
        """Record that a request was made."""
        with self._lock:
            self.requests.append(time.time())

    def wait_if_needed(self) -> float:
        """Wait if necessary and return the wait time in seconds."""
        with self._lock:
            self._cleanup_old_requests()

            if len(self.requests) < self.max_requests:
                return 0.0

            # Calculate wait time until oldest request expires
            wait_time = (self.requests[0] + self.window_seconds) - time.time()

        # Sleep outside the lock to avoid blocking other threads
        if wait_time > 0:
            time.sleep(wait_time + 0.1)
            return wait_time

        return 0.0

    def get_remaining_requests(self) -> int:
        """Get the number of requests remaining in current window."""
        with self._lock:
            self._cleanup_old_requests()
            return max(0, self.max_requests - len(self.requests))

    def get_reset_time(self) -> float:
        """Get seconds until the rate limit resets (oldest request expires)."""
        with self._lock:
            self._cleanup_old_requests()
            if not self.requests:
                return 0.0
            return max(0.0, (self.requests[0] + self.window_seconds) - time.time())


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after


# Global rate limiter instance
rate_limiter = RateLimiter()
