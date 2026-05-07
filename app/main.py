from fastapi import FastAPI

from app.routers import spotify, youtube, admin

app = FastAPI(
    title="AristStats API",
    description="Estadísticas de artistas de rap/hip-hop latinoamericano en Spotify y YouTube.",
    version="1.0.0",
)


app.include_router(spotify.router)
app.include_router(youtube.router)
app.include_router(admin.router)


@app.get("/", tags=["root"])
def root():
    return {"status": "ok", "message": "AristStats API corriendo"}
