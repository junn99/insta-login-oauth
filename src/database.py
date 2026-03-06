"""Database operations for Supabase."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from supabase import create_client, Client

from .config import config
from .models import User, Token, Insight


_client: Optional[Client] = None


def _parse_datetime(value) -> Optional[datetime]:
    """Parse datetime from string or return as-is if already datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Handle ISO format with or without timezone
        try:
            # Try with timezone
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
        try:
            # Try without timezone
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return None


def _normalize_data_json(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def get_client() -> Client:
    """Get or create Supabase client."""
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def init_db():
    """Initialize database tables. Run this SQL in Supabase SQL Editor first."""
    # Tables should be created via Supabase Dashboard or SQL Editor
    # This function just verifies connection
    client = get_client()
    # Test connection by checking if users table exists
    try:
        client.table("users").select("id").limit(1).execute()
    except Exception:
        pass  # Table might not exist yet


# User operations
def get_user_by_instagram_id(instagram_id: str) -> Optional[User]:
    """Get user by Instagram ID."""
    client = get_client()
    result = (
        client.table("users").select("*").eq("instagram_id", instagram_id).execute()
    )
    if result.data:
        row = result.data[0]
        return User(
            id=row["id"],
            instagram_id=row["instagram_id"],
            instagram_username=row["instagram_username"],
            facebook_page_id=row["facebook_page_id"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by internal ID."""
    client = get_client()
    result = client.table("users").select("*").eq("id", user_id).execute()
    if result.data:
        row = result.data[0]
        return User(
            id=row["id"],
            instagram_id=row["instagram_id"],
            instagram_username=row["instagram_username"],
            facebook_page_id=row["facebook_page_id"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    return None


def get_all_users() -> list[User]:
    """Get all users."""
    client = get_client()
    result = client.table("users").select("*").execute()
    return [
        User(
            id=r["id"],
            instagram_id=r["instagram_id"],
            instagram_username=r["instagram_username"],
            facebook_page_id=r["facebook_page_id"],
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
        )
        for r in result.data
    ]


def create_or_update_user(
    instagram_id: str, instagram_username: str, facebook_page_id: Optional[str] = None
) -> User:
    """Create or update a user."""
    client = get_client()
    existing = get_user_by_instagram_id(instagram_id)

    if existing:
        update_data = {
            "instagram_username": instagram_username,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if facebook_page_id is not None:
            update_data["facebook_page_id"] = facebook_page_id
        client.table("users").update(update_data).eq("instagram_id", instagram_id).execute()
        return get_user_by_instagram_id(instagram_id)
    else:
        insert_data = {
            "instagram_id": instagram_id,
            "instagram_username": instagram_username,
        }
        if facebook_page_id is not None:
            insert_data["facebook_page_id"] = facebook_page_id
        client.table("users").insert(insert_data).execute()
        return get_user_by_instagram_id(instagram_id)


# Token operations
def save_token(
    user_id: int,
    token_type: str,
    access_token: str,
    expires_at: Optional[datetime] = None,
):
    """Save or update a token."""
    client = get_client()
    # Delete existing token of same type
    client.table("tokens").delete().eq("user_id", user_id).eq(
        "token_type", token_type
    ).execute()
    # Insert new token
    client.table("tokens").insert(
        {
            "user_id": user_id,
            "token_type": token_type,
            "access_token": access_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
    ).execute()


def get_user_token(user_id: int, token_type: str) -> Optional[Token]:
    """Get token for a user."""
    client = get_client()
    result = (
        client.table("tokens")
        .select("*")
        .eq("user_id", user_id)
        .eq("token_type", token_type)
        .execute()
    )
    if result.data:
        row = result.data[0]
        return Token(
            id=row["id"],
            user_id=row["user_id"],
            token_type=row["token_type"],
            access_token=row["access_token"],
            expires_at=_parse_datetime(row.get("expires_at")),
            created_at=_parse_datetime(row.get("created_at")),
        )
    return None


def get_expiring_tokens(days: int = 7) -> list[tuple[User, Token]]:
    """Get tokens expiring within specified days."""
    client = get_client()
    threshold = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    result = (
        client.table("tokens")
        .select("*, users(*)")
        .eq("token_type", "user")
        .lt("expires_at", threshold)
        .execute()
    )

    return [
        (
            User(
                id=r["users"]["id"],
                instagram_id=r["users"]["instagram_id"],
                instagram_username=r["users"]["instagram_username"],
                facebook_page_id=r["users"]["facebook_page_id"],
            ),
            Token(
                id=r["id"],
                user_id=r["user_id"],
                token_type=r["token_type"],
                access_token=r["access_token"],
                expires_at=_parse_datetime(r.get("expires_at")),
            ),
        )
        for r in result.data
    ]


# Insights operations
def save_insights(user_id: int, insights: list[dict]):
    """Save multiple insight records."""
    client = get_client()
    rows = [
        {
            "user_id": user_id,
            "metric_name": insight["metric_name"],
            "metric_value": insight["metric_value"],
            "period": insight["period"],
        }
        for insight in insights
    ]
    if rows:
        client.table("insights").insert(rows).execute()


def get_insights(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metric_name: Optional[str] = None,
) -> list[Insight]:
    """Get insights with optional filters."""
    client = get_client()
    query = client.table("insights").select("*").eq("user_id", user_id)

    if start_date:
        query = query.gte("collected_at", start_date.isoformat())
    if end_date:
        query = query.lte("collected_at", end_date.isoformat())
    if metric_name:
        query = query.eq("metric_name", metric_name)

    result = query.order("collected_at", desc=True).execute()

    return [
        Insight(
            id=r["id"],
            user_id=r["user_id"],
            metric_name=r["metric_name"],
            metric_value=r["metric_value"],
            period=r["period"],
            collected_at=r.get("collected_at"),
        )
        for r in result.data
    ]


def get_latest_insights(user_id: int) -> dict[str, Insight]:
    """Get the latest value for each metric."""
    client = get_client()
    # Get all insights and group by metric_name, taking the latest
    result = (
        client.table("insights")
        .select("*")
        .eq("user_id", user_id)
        .order("collected_at", desc=True)
        .execute()
    )

    latest = {}
    for r in result.data:
        metric = r["metric_name"]
        if metric not in latest:
            latest[metric] = Insight(
                id=r["id"],
                user_id=r["user_id"],
                metric_name=r["metric_name"],
                metric_value=r["metric_value"],
                period=r["period"],
                collected_at=r.get("collected_at"),
            )
    return latest


# Audience data operations
def save_audience_data(user_id: int, data_type: str, data: dict):
    """Save audience data."""
    client = get_client()
    client.table("audience_data").insert(
        {"user_id": user_id, "data_type": data_type, "data_json": json.dumps(data)}
    ).execute()


def get_latest_audience_data(user_id: int) -> dict[str, dict]:
    """Get latest audience data by type."""
    client = get_client()
    result = (
        client.table("audience_data")
        .select("*")
        .eq("user_id", user_id)
        .order("collected_at", desc=True)
        .execute()
    )

    latest = {}
    for r in result.data:
        data_type = r["data_type"]
        if data_type not in latest:
            latest[data_type] = _normalize_data_json(r.get("data_json"))
    return latest


# Collection log operations
def log_collection(
    user_id: int, collection_type: str, status: str, error_message: Optional[str] = None
):
    """Log a collection attempt."""
    client = get_client()
    client.table("collection_log").insert(
        {
            "user_id": user_id,
            "collection_type": collection_type,
            "status": status,
            "error_message": error_message,
        }
    ).execute()
