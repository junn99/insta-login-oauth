"""Insights collection logic."""

from .database import (
    get_all_users,
    get_user_token,
    save_insights,
    save_audience_data,
    log_collection,
)
from .instagram_api import InstagramAPI, InstagramAPIError
from .rate_limiter import RateLimitError


def collect_insights_for_user(user_id: int, instagram_id: str, access_token: str) -> dict:
    """
    Collect insights for a single user.

    Returns:
        dict with 'success', 'insights_count', 'error' keys
    """
    api = InstagramAPI(access_token, instagram_id)

    try:
        # Collect daily insights
        insights = api.get_insights(period="day")

        if insights:
            save_insights(user_id, insights)
            log_collection(user_id, "insights", "success")
            return {"success": True, "insights_count": len(insights), "error": None}
        else:
            log_collection(user_id, "insights", "success", "No insights data available")
            return {"success": True, "insights_count": 0, "error": None}

    except RateLimitError as e:
        log_collection(user_id, "insights", "rate_limited", str(e))
        return {"success": False, "insights_count": 0, "error": f"Rate limited: {e}"}

    except InstagramAPIError as e:
        log_collection(user_id, "insights", "error", str(e))
        return {"success": False, "insights_count": 0, "error": f"API error: {e}"}

    except Exception as e:
        log_collection(user_id, "insights", "error", str(e))
        return {"success": False, "insights_count": 0, "error": f"Unexpected error: {e}"}


def collect_audience_for_user(user_id: int, instagram_id: str, access_token: str) -> dict:
    """
    Collect audience data for a single user.

    Returns:
        dict with 'success', 'data_types', 'error' keys
    """
    api = InstagramAPI(access_token, instagram_id)

    try:
        audience_data = api.get_audience_data()

        if audience_data:
            for data_type, data in audience_data.items():
                save_audience_data(user_id, data_type, data)

            log_collection(user_id, "audience", "success")
            return {"success": True, "data_types": list(audience_data.keys()), "error": None}
        else:
            log_collection(user_id, "audience", "success", "No audience data available")
            return {"success": True, "data_types": [], "error": None}

    except RateLimitError as e:
        log_collection(user_id, "audience", "rate_limited", str(e))
        return {"success": False, "data_types": [], "error": f"Rate limited: {e}"}

    except InstagramAPIError as e:
        log_collection(user_id, "audience", "error", str(e))
        return {"success": False, "data_types": [], "error": f"API error: {e}"}

    except Exception as e:
        log_collection(user_id, "audience", "error", str(e))
        return {"success": False, "data_types": [], "error": f"Unexpected error: {e}"}


def collect_all_users() -> dict:
    """
    Collect insights and audience data for all users.

    Returns:
        Summary dict with counts of successful/failed collections
    """
    users = get_all_users()
    results = {
        "total_users": len(users),
        "insights_success": 0,
        "insights_failed": 0,
        "audience_success": 0,
        "audience_failed": 0,
        "errors": [],
    }

    for user in users:
        # Get user token for API calls
        token = get_user_token(user.id, "user")
        if not token:
            results["errors"].append(f"No user token for user {user.instagram_username}")
            results["insights_failed"] += 1
            results["audience_failed"] += 1
            continue

        # Collect insights
        insights_result = collect_insights_for_user(user.id, user.instagram_id, token.access_token)
        if insights_result["success"]:
            results["insights_success"] += 1
        else:
            results["insights_failed"] += 1
            results["errors"].append(f"Insights error for {user.instagram_username}: {insights_result['error']}")

        # Collect audience data
        audience_result = collect_audience_for_user(user.id, user.instagram_id, token.access_token)
        if audience_result["success"]:
            results["audience_success"] += 1
        else:
            results["audience_failed"] += 1
            results["errors"].append(f"Audience error for {user.instagram_username}: {audience_result['error']}")

    return results
