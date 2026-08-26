"""Database operations for Supabase."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from supabase import create_client, Client

from .config import config
from .consent import (
    CONSENT_SCHEMA_VERSION,
    INSTAGRAM_PERMISSIONS_VERSION,
    PRIVACY_VERSION,
    TERMS_VERSION,
)
from .models import User, Token, Insight


logger = logging.getLogger(__name__)

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
    """Verify the Supabase connection. Tables come from ``supabase_schema.sql``.

    Deliberately non-fatal: this runs on every page load, so a transient
    Supabase outage or missing preview config must not take the whole page
    down. It logs instead of raising -- without the log line a bad key, a
    missing table or an RLS policy that denies our role all look identical to a
    healthy connection, and the failure only surfaces later inside the OAuth
    callback.
    """
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.warning(
            "Supabase connectivity check skipped because SUPABASE_URL or "
            "SUPABASE_KEY is unset."
        )
        return

    try:
        client = get_client()
        client.table("users").select("id").limit(1).execute()
    except Exception:
        logger.warning(
            "Supabase connectivity check failed against %s -- the app will keep "
            "serving pages but reads/writes are likely broken. Check that "
            "SUPABASE_KEY is valid and that supabase_schema.sql has been run.",
            config.SUPABASE_URL or "<unset SUPABASE_URL>",
            exc_info=True,
        )


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


def complete_instagram_onboarding(
    *,
    instagram_id: str,
    instagram_username: str,
    access_token: str,
    consent: Any,
    expires_at: Optional[datetime] = None,
) -> int:
    """Atomically save user, consent audit row and token via Supabase RPC."""
    instagram_id = _require_value("instagram_id", instagram_id)
    instagram_username = _require_value("instagram_username", instagram_username)
    access_token = _require_value("access_token", access_token)
    state_nonce = _require_non_empty_string(consent, "nonce")
    consent_accepted_at = _require_datetime(consent, "accepted_at")
    consent_bundle_hash = _require_bundle_hash(consent, "bundle_hash")
    consent_schema_version = _require_exact_attr(
        consent,
        "consent_schema_version",
        CONSENT_SCHEMA_VERSION,
    )
    terms_version = _require_exact_attr(consent, "terms_version", TERMS_VERSION)
    privacy_version = _require_exact_attr(consent, "privacy_version", PRIVACY_VERSION)
    instagram_permissions_version = _require_exact_attr(
        consent,
        "instagram_permissions_version",
        INSTAGRAM_PERMISSIONS_VERSION,
    )
    consent_age = _require_true_attr(consent, "age_confirmed")
    consent_terms = _require_true_attr(consent, "terms_accepted")
    consent_privacy = _require_true_attr(consent, "privacy_accepted")
    consent_instagram = _require_true_attr(consent, "instagram_permissions_accepted")

    client = get_client()
    result = client.rpc(
        "complete_instagram_onboarding",
        {
            "p_instagram_id": instagram_id,
            "p_instagram_username": instagram_username,
            "p_access_token": access_token,
            "p_expires_at": expires_at.isoformat() if expires_at else None,
            "p_state_nonce": state_nonce,
            "p_consent_schema_version": consent_schema_version,
            "p_terms_version": terms_version,
            "p_privacy_version": privacy_version,
            "p_instagram_permissions_version": instagram_permissions_version,
            "p_consent_age": consent_age,
            "p_consent_terms": consent_terms,
            "p_consent_privacy": consent_privacy,
            "p_consent_instagram": consent_instagram,
            "p_accepted_at": consent_accepted_at.isoformat(),
            "p_bundle_hash": consent_bundle_hash,
        },
    ).execute()

    data = result.data
    if isinstance(data, list):
        if not data:
            raise ValueError("complete_instagram_onboarding returned no user_id")
        data = data[0]
    if isinstance(data, dict):
        if "complete_instagram_onboarding" in data:
            data = data["complete_instagram_onboarding"]
        else:
            raise ValueError("complete_instagram_onboarding returned invalid user_id")
    if isinstance(data, bool) or not isinstance(data, int) or data <= 0:
        raise ValueError("complete_instagram_onboarding returned invalid user_id")
    return data


def _require_value(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"complete_instagram_onboarding requires {name}")
    return value


def _require_non_empty_string(obj: Any, attr: str) -> str:
    value = getattr(obj, attr, None)
    if not isinstance(value, str) or not value:
        raise ValueError(f"complete_instagram_onboarding requires {attr}")
    return value


def _require_bundle_hash(obj: Any, attr: str) -> str:
    value = _require_non_empty_string(obj, attr)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"complete_instagram_onboarding requires valid {attr}")
    return value


def _require_datetime(obj: Any, attr: str) -> datetime:
    value = getattr(obj, attr, None)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"complete_instagram_onboarding requires {attr}")
    return value


def _require_exact_attr(obj: Any, attr: str, expected: Any) -> Any:
    value = getattr(obj, attr, None)
    if value != expected:
        raise ValueError(f"complete_instagram_onboarding requires {attr}={expected}")
    return value


def _require_true_attr(obj: Any, attr: str) -> bool:
    value = getattr(obj, attr, None)
    if value is not True:
        raise ValueError(f"complete_instagram_onboarding requires {attr}=true")
    return True


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
        .limit(200)
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
