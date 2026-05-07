from fastapi import APIRouter, HTTPException
from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from app.data.artist_ids import spotify_ids
from app.services.scraper import get_monthly_listeners

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


@router.get("/artist/{artist_id}/listeners")
def get_monthly_listeners_endpoint(artist_id: str):
    listeners = get_monthly_listeners(artist_id)
    return {"artist_id": artist_id, "monthly_listeners": listeners}
