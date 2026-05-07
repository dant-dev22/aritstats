from fastapi import APIRouter
from app.data.artist_ids import youtube_ids

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/artists")
def get_artists():
    return {"total": len(youtube_ids), "artists": youtube_ids}
