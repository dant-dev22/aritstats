from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from app.data.artist_ids import spotify_ids
from app.services.scraper import get_monthly_listeners
from app.services.spotify_api import get_artists_info

router = APIRouter(prefix="/spotify", tags=["spotify"])


@router.get("/credentials")
def get_credentials():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Spotify credentials not configured")
    return {
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }


@router.get("/artists")
def get_artists():
    return {"total": len(spotify_ids), "artists": spotify_ids}


@router.get("/artists/info")
def get_artists_info_endpoint(ids: str = Query(..., description="Comma-separated Spotify artist IDs")):
    """
    Fetches name, image and profile URL from the official Spotify API.
    Accepts up to 50 IDs per call (Spotify limit).
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Spotify credentials not configured")
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="No IDs provided")
    if len(id_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 IDs per request")
    try:
        artists = get_artists_info(id_list)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {e}")
    return {"artists": artists}


@router.get("/artist/{artist_id}/listeners")
def get_monthly_listeners_endpoint(artist_id: str):
    listeners = get_monthly_listeners(artist_id)
    return {"artist_id": artist_id, "monthly_listeners": listeners}
