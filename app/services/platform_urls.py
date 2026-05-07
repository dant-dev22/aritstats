import re
from urllib.parse import unquote, urlparse


def extract_spotify_artist_id(raw: str) -> str | None:
    s = raw.strip()
    if not s:
        return None
    if m := re.fullmatch(r"spotify:artist:([0-9A-Za-z]{22})", s):
        return m.group(1)
    if re.fullmatch(r"[0-9A-Za-z]{22}", s):
        return s
    try:
        u = urlparse(s)
    except ValueError:
        return None
    path = unquote(u.path or "")
    parts = [p for p in path.split("/") if p]
    if "artist" in parts:
        i = parts.index("artist")
        if i + 1 < len(parts):
            cand = parts[i + 1].split("?")[0]
            if re.fullmatch(r"[0-9A-Za-z]{22}", cand):
                return cand
    return None


def extract_youtube_channel_id(raw: str) -> str | None:
    s = raw.strip()
    if not s:
        return None
    # ID directo
    if m := re.fullmatch(r"(UC[0-9A-Za-z_-]{22})", s):
        return m.group(1)
    # youtu.be y youtube.com
    if m := re.search(r"(?i)youtube\.com/channel/(UC[0-9A-Za-z_-]{22})", s):
        return m.group(1)
    return None
