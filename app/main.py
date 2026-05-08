from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers import spotify, youtube, admin

app = FastAPI(
    title="AristStats API",
    description="Estadísticas de artistas de rap/hip-hop latinoamericano en Spotify y YouTube.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(spotify.router, prefix="/api")
app.include_router(youtube.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/", tags=["root"])
def root():
    return {"status": "ok", "message": "AristStats API corriendo"}
