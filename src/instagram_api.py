"""Instagram Graph API client with retry logic."""

from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random, retry_if_exception

from .config import config
from .rate_limiter import rate_limiter, RateLimitError


class InstagramAPIError(Exception):
    """Instagram API error."""

    def __init__(self, message: str, code: Optional[int] = None, subcode: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


def _is_retryable(exception: BaseException) -> bool:
    """Only retry on transient errors, not permanent client errors (400, 403, etc.)."""
    if isinstance(exception, requests.RequestException):
        return True
    if isinstance(exception, InstagramAPIError):
        # Retry on rate-limit, server errors, and known transient API error codes
        return exception.code in (None, 1, 2, 4, 17, 32, 341) or (
            exception.code is not None and exception.code >= 500
        )
    return False


class InstagramAPI:
    """Instagram Graph API client."""

    # Available insight metrics for Instagram Business accounts
    # Updated per Graph API v22 changelog — removed deprecated:
    #   impressions (use views), profile_views, follower_count
    INSIGHT_METRICS = [
        "views",
        "reach",
        "accounts_engaged",
        "total_interactions",
        "likes",
        "comments",
        "shares",
        "saves",
        "replies",
        "follows_and_unfollows",
        "reposts",
        "profile_links_taps",
    ]

    AUDIENCE_METRICS = [
        "engaged_audience_demographics",
        "reached_audience_demographics",
        "follower_demographics",
    ]

    def __init__(self, access_token: str, instagram_id: str):
        self.access_token = access_token
        self.instagram_id = instagram_id
        self.base_url = config.INSTAGRAM_API_BASE_URL

    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make an API request with rate limiting."""
        # Check rate limit
        if not rate_limiter.can_make_request():
            wait_time = rate_limiter.wait_if_needed()
            if wait_time > 60:  # If wait is too long, raise error
                raise RateLimitError(f"Rate limit exceeded. Retry after {wait_time:.0f}s", wait_time)

        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token

        response = requests.get(url, params=params)
        rate_limiter.record_request()

        # Handle API errors
        if response.status_code != 200:
            try:
                error_data = response.json().get("error", {})
            except (ValueError, KeyError):
                error_data = {}
            raise InstagramAPIError(
                error_data.get("message", "Unknown error"),
                error_data.get("code"),
                error_data.get("error_subcode"),
            )

        return response.json()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60) + wait_random(0, 1),
        retry=retry_if_exception(_is_retryable),
    )
    def _request_with_retry(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make request with exponential backoff retry."""
        return self._make_request(endpoint, params)

    def get_insights(self, metrics: Optional[list[str]] = None, period: str = "day") -> list[dict]:
        """
        Fetch Instagram insights.

        Args:
            metrics: List of metric names. Defaults to common metrics.
            period: Time period - 'day', 'week', 'days_28', or 'lifetime'

        Returns:
            List of insight dictionaries with metric_name, metric_value, period
        """
        if metrics is None:
            # Use a subset of commonly available metrics
            metrics = ["views", "reach", "accounts_engaged", "total_interactions"]

        # Filter to valid metrics only
        valid_metrics = [m for m in metrics if m in self.INSIGHT_METRICS]
        if not valid_metrics:
            return []

        params = {
            "metric": ",".join(valid_metrics),
            "period": period,
            "metric_type": "total_value",
        }

        try:
            data = self._request_with_retry(f"{self.instagram_id}/insights", params)
            results = []

            for item in data.get("data", []):
                metric_name = item.get("name")
                values = item.get("total_value", {})
                value = values.get("value", 0)

                results.append({
                    "metric_name": metric_name,
                    "metric_value": float(value),
                    "period": period,
                })

            return results

        except InstagramAPIError as e:
            # Handle specific errors
            if e.code == 100 and "not compatible" in str(e).lower():
                # Metric not available for this period, try with lifetime
                return []
            raise

    def get_audience_data(self) -> dict[str, dict]:
        """
        Fetch audience demographic data.

        Returns:
            Dictionary with demographic breakdowns (city, country, age_gender)
        """
        results = {}

        # Try each audience metric
        for metric in self.AUDIENCE_METRICS:
            try:
                params = {
                    "metric": metric,
                    "period": "lifetime",
                    "metric_type": "total_value",
                }
                data = self._request_with_retry(f"{self.instagram_id}/insights", params)

                for item in data.get("data", []):
                    breakdown = item.get("total_value", {}).get("breakdowns", [])
                    if breakdown:
                        # Extract the demographic data
                        for bd in breakdown:
                            dimension = bd.get("dimension_keys", ["unknown"])[0]
                            values = {}
                            for result in bd.get("results", []):
                                key = result.get("dimension_values", ["unknown"])[0]
                                val = result.get("value", 0)
                                values[key] = val
                            results[f"{metric}_{dimension}"] = values

            except InstagramAPIError:
                # Skip if metric not available
                continue

        return results

    def get_account_info(self) -> dict:
        """Get basic account information."""
        params = {
            "fields": "id,username,name,profile_picture_url,followers_count,follows_count,media_count,biography"
        }
        return self._request_with_retry(self.instagram_id, params)
