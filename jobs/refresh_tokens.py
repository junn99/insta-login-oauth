"""Scheduled job for refreshing expiring tokens."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, get_expiring_tokens, save_token
from src.oauth import refresh_long_lived_token


def run_token_refresh(days_before_expiry: int = 7):
    """
    Refresh tokens that will expire within the specified days.

    Args:
        days_before_expiry: Refresh tokens expiring within this many days
    """
    print(f"Checking for tokens expiring within {days_before_expiry} days...")

    # Ensure database is initialized
    init_db()

    # Get expiring tokens
    expiring = get_expiring_tokens(days_before_expiry)

    if not expiring:
        print("No tokens need refreshing.")
        return {"refreshed": 0, "failed": 0, "errors": []}

    results = {"refreshed": 0, "failed": 0, "errors": []}

    for user, token in expiring:
        print(f"Refreshing token for {user.instagram_username}...")

        try:
            # Refresh the token
            new_token_data = refresh_long_lived_token(token.access_token)

            # Save the new token
            save_token(
                user_id=user.id,
                token_type="user",
                access_token=new_token_data["access_token"],
                expires_at=new_token_data["expires_at"],
            )

            print(f"  ✓ Token refreshed, expires: {new_token_data['expires_at']}")
            results["refreshed"] += 1

        except Exception as e:
            error_msg = f"Failed to refresh token for {user.instagram_username}: {e}"
            print(f"  ✗ {error_msg}")
            results["failed"] += 1
            results["errors"].append(error_msg)

    print(f"\n=== Refresh Summary ===")
    print(f"Refreshed: {results['refreshed']}")
    print(f"Failed: {results['failed']}")

    return results


if __name__ == "__main__":
    run_token_refresh()
