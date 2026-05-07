from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, model_validator
from pymysql.err import IntegrityError

from app.db import get_connection, mysql_configured
from app.services.platform_urls import extract_spotify_artist_id, extract_youtube_channel_id

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_db():
    if not mysql_configured():
        raise HTTPException(
            status_code=503,
            detail="MySQL no configurado (variables MYSQL_USER y MYSQL_DATABASE)",
        )


@router.get("/visits")
def admin_health():
    return {"status": "ok", "message": "admin endpoint activo temporalmente"}


class NewPendingSubmissionBody(BaseModel):
    artist_name: str
    source_url: str


@router.post("/pending-submissions", status_code=201)
def create_pending_submission(body: NewPendingSubmissionBody):
    _require_db()
    name = body.artist_name.strip()
    url = body.source_url.strip()
    if not name or not url:
        raise HTTPException(
            status_code=400,
            detail="artist_name y source_url son obligatorios y no pueden ir vacíos",
        )
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pending_artist_submissions (artist_name, source_url)
                VALUES (%s, %s)
                """,
                (name, url),
            )
            new_id = cur.lastrowid
        conn.commit()
        return {
            "id": new_id,
            "artist_name": name,
            "source_url": url,
            "status": "pending",
        }
    finally:
        conn.close()


@router.get("/pending-submissions")
def list_pending_submissions(
    status: str | None = Query(
        "pending",
        description="Filtrar por estado: pending, approved, rejected o 'all'",
    ),
) -> list[dict[str, Any]]:
    _require_db()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if status and status.lower() == "all":
                cur.execute(
                    """
                    SELECT id, artist_name, source_url, status, corrected_url,
                           platform, created_at, updated_at, reviewed_at
                    FROM pending_artist_submissions
                    ORDER BY id DESC
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT id, artist_name, source_url, status, corrected_url,
                           platform, created_at, updated_at, reviewed_at
                    FROM pending_artist_submissions
                    WHERE status = %s
                    ORDER BY id DESC
                    """,
                    (status,),
                )
            rows = cur.fetchall()
        return rows
    finally:
        conn.close()


class ReviewSubmissionBody(BaseModel):
    approved: bool
    corrected_url: str = ""
    platform: Literal["spotify", "youtube"] | None = None

    @model_validator(mode="after")
    def validate_approved(self):
        if self.approved:
            if not (self.corrected_url or "").strip():
                raise ValueError("corrected_url es obligatorio cuando approved es true")
            if self.platform is None:
                raise ValueError("platform es obligatorio cuando approved es true")
        return self


@router.post("/pending-submissions/{submission_id}/review")
def review_pending_submission(submission_id: int, body: ReviewSubmissionBody):
    _require_db()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, artist_name, source_url, status
                FROM pending_artist_submissions
                WHERE id = %s
                FOR UPDATE
                """,
                (submission_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            if row["status"] != "pending":
                raise HTTPException(
                    status_code=409,
                    detail="Solo se pueden revisar registros en estado pending",
                )

            if not body.approved:
                cur.execute(
                    """
                    UPDATE pending_artist_submissions
                    SET status = 'rejected',
                        corrected_url = %s,
                        platform = %s,
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        body.corrected_url.strip() or None,
                        body.platform,
                        submission_id,
                    ),
                )
                conn.commit()
                return {
                    "submission_id": submission_id,
                    "approved": False,
                    "status": "rejected",
                    "platform_row": None,
                }

            corrected = body.corrected_url.strip()
            plat = body.platform
            artist_name = row["artist_name"]
            platform_payload: dict[str, str]

            if plat == "spotify":
                sid = extract_spotify_artist_id(corrected)
                if not sid:
                    raise HTTPException(
                        status_code=400,
                        detail="No se pudo obtener el Spotify artist ID desde corrected_url",
                    )
                profile_url = f"https://open.spotify.com/artist/{sid}"
                try:
                    cur.execute(
                        """
                        INSERT INTO spotify_artists (artist_name, spotify_artist_id, profile_url)
                        VALUES (%s, %s, %s)
                        """,
                        (artist_name, sid, profile_url),
                    )
                except IntegrityError:
                    conn.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Ese spotify_artist_id ya existe en spotify_artists",
                    ) from None
                platform_payload = {"spotify_artist_id": sid}
            else:
                yid = extract_youtube_channel_id(corrected)
                if not yid:
                    raise HTTPException(
                        status_code=400,
                        detail="No se pudo obtener el YouTube channel ID (UC…) desde corrected_url",
                    )
                channel_url = f"https://www.youtube.com/channel/{yid}"
                try:
                    cur.execute(
                        """
                        INSERT INTO youtube_artist_channels
                        (artist_name, youtube_channel_id, channel_url)
                        VALUES (%s, %s, %s)
                        """,
                        (artist_name, yid, channel_url),
                    )
                except IntegrityError:
                    conn.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Ese youtube_channel_id ya existe en youtube_artist_channels",
                    ) from None
                platform_payload = {"youtube_channel_id": yid}

            cur.execute(
                """
                UPDATE pending_artist_submissions
                SET status = 'approved',
                    corrected_url = %s,
                    platform = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (corrected, plat, submission_id),
            )
            conn.commit()

            return {
                "submission_id": submission_id,
                "approved": True,
                "status": "approved",
                "platform": plat,
                "platform_row": platform_payload,
            }
    except HTTPException:
        conn.rollback()
        raise
    finally:
        conn.close()
