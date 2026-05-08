import time
import requests
from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

_token_cache = {"token": None, "expires_at": 0}


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"]
    return _token_cache["token"]


def get_artists_info(artist_ids: list[str]) -> list[dict]:
    """
    Calls Spotify Web API for up to 50 artist IDs per request.
    Returns list of dicts with id, name, images, external_urls.
    """
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    results = []

    # Spotify allows max 50 per request
    for i in range(0, len(artist_ids), 50):
        batch = artist_ids[i : i + 50]
        resp = requests.get(
            "https://api.spotify.com/v1/artists",
            headers=headers,
            params={"ids": ",".join(batch)},
            timeout=15,
        )
        resp.raise_for_status()
        artists = resp.json().get("artists", [])
        for a in artists:
            if a:
                results.append({
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "images": a.get("images", []),
                    "external_urls": a.get("external_urls", {}),
                    "followers": a.get("followers", {}).get("total", 0),
                    "genres": a.get("genres", []),
                })
    return results
