"""Pydantic models for urlinsta data structures."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    """User model representing an Instagram Business account."""

    id: Optional[int] = None
    instagram_id: str
    instagram_username: str
    facebook_page_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Token(BaseModel):
    """Token model for OAuth tokens."""

    id: Optional[int] = None
    user_id: int
    token_type: str  # 'user'
    access_token: str
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Insight(BaseModel):
    """Instagram insight metric."""

    id: Optional[int] = None
    user_id: int
    metric_name: str
    metric_value: float
    period: str  # 'day', 'week', 'days_28', 'lifetime'
    collected_at: Optional[datetime] = None


class AudienceData(BaseModel):
    """Audience demographic data."""

    id: Optional[int] = None
    user_id: int
    data_type: str  # 'city', 'country', 'age_gender'
    data_json: str  # JSON string of demographic breakdown
    collected_at: Optional[datetime] = None


class CollectionLog(BaseModel):
    """Log entry for data collection runs."""

    id: Optional[int] = None
    user_id: int
    collection_type: str  # 'insights' or 'audience'
    status: str  # 'success', 'error', 'rate_limited'
    error_message: Optional[str] = None
    collected_at: Optional[datetime] = None


class InstagramAccount(BaseModel):
    """Instagram Business Account info from API."""

    id: str
    username: str
    name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    followers_count: Optional[int] = None
    media_count: Optional[int] = None
