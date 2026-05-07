"""
Genera sql/todo_aritmetrica.sql desde app/data/artist_ids.py.

Modelo actual:
  - spotify_artists y youtube_artist_channels separadas (sin conciliación cruzada).
  - youtube: varias filas por artista permitidas; IDs de canal repetidos se omiten (primera aparición).
  - spotify: IDs repetidos se omiten igual.
  - pending_artist_submissions: cola manual (vacía en seed).
  - endpoint_counter: contadores por ruta (vacía en seed).

Uso (desde la raíz del repo):
    python scripts/generate_aritmetrica_sql.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS_PATH = ROOT / "app" / "data" / "artist_ids.py"
OUT_PATH = ROOT / "sql" / "todo_aritmetrica.sql"


def sql_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def batched(values: list[str], size: int):
    for i in range(0, len(values), size):
        yield values[i : i + size]


def load_lists():
    ns: dict = {}
    exec(IDS_PATH.read_text(encoding="utf-8"), ns)
    return ns["spotify_ids"], ns["youtube_ids"]


def dedupe_spotify_by_id(rows: list[dict]) -> tuple[list[dict], list[tuple[str, str, str]]]:
    """Mantiene la primera fila por spotify id; devuelve (lista, omitidos)."""
    seen: dict[str, dict] = {}
    skipped: list[tuple[str, str, str]] = []  # id, nombre_omitido, nombre_conservado
    for r in rows:
        sid = r["id"]
        if sid not in seen:
            seen[sid] = r
        else:
            skipped.append((sid, r["name"], seen[sid]["name"]))
    return list(seen.values()), skipped


def dedupe_youtube_by_id(rows: list[dict]) -> tuple[list[dict], list[tuple[str, str, str]]]:
    seen: dict[str, dict] = {}
    skipped: list[tuple[str, str, str]] = []
    for r in rows:
        yid = r["id"]
        if yid not in seen:
            seen[yid] = r
        else:
            skipped.append((yid, r["name"], seen[yid]["name"]))
    return list(seen.values()), skipped


def main() -> None:
    spotify_rows, youtube_rows = load_lists()

    spotify_kept, spotify_skipped = dedupe_spotify_by_id(spotify_rows)
    youtube_kept, youtube_skipped = dedupe_youtube_by_id(youtube_rows)

    spotify_values = []
    for r in spotify_kept:
        sid = r["id"]
        url = f"https://open.spotify.com/artist/{sid}"
        spotify_values.append(
            f"({sql_str(r['name'])}, {sql_str(sid)}, {sql_str(url)})"
        )

    youtube_values = []
    for r in youtube_kept:
        yid = r["id"]
        url = f"https://www.youtube.com/channel/{yid}"
        youtube_values.append(
            f"({sql_str(r['name'])}, {sql_str(yid)}, {sql_str(url)})"
        )

    lines: list[str] = [
        "-- Aritmetrica: esquema + seed desde artist_ids.py",
        "-- Sin tabla única de artista: spotify y youtube son independientes.",
        "-- YouTube permite varios canales por nombre de artista; channel_id es único global.",
        "-- Ejecutar en el VPS, por ejemplo:",
        "--   mysql -h 127.0.0.1 -u USUARIO -p < sql/todo_aritmetrica.sql",
        "-- Este script hace DROP de tablas al inicio.",
        "",
        "SET NAMES utf8mb4;",
        "SET time_zone = '+00:00';",
        "",
        "CREATE DATABASE IF NOT EXISTS `aritmetrica-stats`",
        "  CHARACTER SET utf8mb4",
        "  COLLATE utf8mb4_unicode_ci;",
        "",
        "USE `aritmetrica-stats`;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "DROP TABLE IF EXISTS pending_artist_submissions;",
        "DROP TABLE IF EXISTS endpoint_counter;",
        "DROP TABLE IF EXISTS youtube_artist_channels;",
        "DROP TABLE IF EXISTS spotify_artists;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "CREATE TABLE spotify_artists (",
        "  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,",
        "  artist_name VARCHAR(255) NOT NULL,",
        "  spotify_artist_id VARCHAR(32) NOT NULL,",
        "  profile_url VARCHAR(512) DEFAULT NULL,",
        "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,",
        "  PRIMARY KEY (id),",
        "  UNIQUE KEY uq_spotify_artist_id (spotify_artist_id)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "CREATE TABLE youtube_artist_channels (",
        "  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,",
        "  artist_name VARCHAR(255) NOT NULL,",
        "  youtube_channel_id VARCHAR(64) NOT NULL,",
        "  channel_url VARCHAR(512) DEFAULT NULL,",
        "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,",
        "  PRIMARY KEY (id),",
        "  UNIQUE KEY uq_youtube_channel_id (youtube_channel_id),",
        "  KEY idx_youtube_artist_name (artist_name)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "CREATE TABLE pending_artist_submissions (",
        "  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,",
        "  artist_name VARCHAR(255) NOT NULL,",
        "  source_url VARCHAR(2048) NOT NULL,",
        "  status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',",
        "  corrected_url VARCHAR(2048) DEFAULT NULL,",
        "  platform ENUM('spotify', 'youtube') DEFAULT NULL,",
        "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,",
        "  reviewed_at TIMESTAMP NULL DEFAULT NULL,",
        "  PRIMARY KEY (id),",
        "  KEY idx_pending_status (status)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "-- Contador: respuestas HTTP exitosas (< 400), excluir /admin en la app",
        "CREATE TABLE endpoint_counter (",
        "  endpoint_path VARCHAR(255) NOT NULL,",
        "  success_count BIGINT UNSIGNED NOT NULL DEFAULT 0,",
        "  last_success_at TIMESTAMP NULL DEFAULT NULL,",
        "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,",
        "  PRIMARY KEY (endpoint_path)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
    ]

    lines.append("-- Registros omitidos en seed por ID duplicado (primera aparición en artist_ids.py gana)")
    for sid, skip_n, keep_n in spotify_skipped:
        lines.append(
            f"-- spotify id {sid}: omitido '{skip_n}', conservado '{keep_n}'"
        )
    for yid, skip_n, keep_n in youtube_skipped:
        lines.append(
            f"-- youtube id {yid}: omitido '{skip_n}', conservado '{keep_n}'"
        )
    lines.append("")

    for chunk in batched(spotify_values, 120):
        lines.append(
            "INSERT INTO spotify_artists (artist_name, spotify_artist_id, profile_url) VALUES\n"
            + ",\n".join(chunk)
            + ";"
        )
        lines.append("")

    for chunk in batched(youtube_values, 120):
        lines.append(
            "INSERT INTO youtube_artist_channels (artist_name, youtube_channel_id, channel_url) VALUES\n"
            + ",\n".join(chunk)
            + ";"
        )
        lines.append("")

    lines.append(
        "-- Incremento sugerido desde la API (fuera de /admin, status < 400):\n"
        "-- INSERT INTO endpoint_counter (endpoint_path, success_count, last_success_at)\n"
        "-- VALUES (:path, 1, UTC_TIMESTAMP())\n"
        "-- ON DUPLICATE KEY UPDATE success_count = success_count + 1, last_success_at = UTC_TIMESTAMP();"
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    print(
        f"Spotify: {len(spotify_rows)} filas -> {len(spotify_kept)} insertadas, "
        f"omitidas {len(spotify_skipped)}"
    )
    print(
        f"YouTube: {len(youtube_rows)} filas -> {len(youtube_kept)} insertadas, "
        f"omitidas {len(youtube_skipped)}"
    )


if __name__ == "__main__":
    main()
