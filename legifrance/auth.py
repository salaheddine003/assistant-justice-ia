import requests

from .config import API_KEY, CLIENT_ID, CLIENT_SECRET, OAUTH_URL


def get_token() -> str:
    """Obtient un token OAuth2 PISTE."""
    r = requests.post(
        OAUTH_URL,
        data={
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope":         "openid",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def hdrs(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "KeyId":         API_KEY,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
