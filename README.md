# AristStats API

API REST con FastAPI para consultar estadísticas de artistas de rap/hip-hop latinoamericano en Spotify y YouTube.

## Estructura del proyecto

```
aritstats/
├── app/
│   ├── main.py              # Entrada de la aplicación FastAPI
│   ├── config.py            # Configuración y variables de entorno
│   ├── data/
│   │   └── artist_ids.py    # IDs de artistas en Spotify y YouTube
│   ├── routers/
│   │   ├── spotify.py       # Endpoints de Spotify
│   │   ├── youtube.py       # Endpoints de YouTube
│   │   └── admin.py         # Cola de aprobación y rutas administrativas
│   └── services/
│       ├── scraper.py       # Scraping de oyentes mensuales en Spotify
│       └── platform_urls.py
├── scripts/
│   └── generate_aritmetrica_sql.py  # Regenera sql/todo_aritmetrica.sql desde artist_ids.py
├── sql/
│   └── todo_aritmetrica.sql          # Esquema + datos iniciales (ejecutar en MySQL)
├── .env.example
├── requirements.txt
└── README.md
```

## Cómo levantarlo manualmente

### 1. Requisitos previos

- Python 3.9 o superior
- pip

### 2. Clonar o descargar el proyecto

```bash
git clone <url-del-repo>
cd aritstats
```

### 3. Crear un entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar variables de entorno

Copia el archivo de ejemplo y rellena tus credenciales de Spotify:

```bash
cp .env.example .env
```

Edita `.env`:

```env
SPOTIFY_CLIENT_ID=tu_client_id_aqui
SPOTIFY_CLIENT_SECRET=tu_client_secret_aqui

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=tu_usuario_mysql
MYSQL_PASSWORD=tu_password_mysql
MYSQL_DATABASE=aritmetrica-stats
```

> Las credenciales de Spotify las obtienes en [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

En el VPS, con la API en el mismo equipo, `MYSQL_HOST=127.0.0.1` suele ser lo correcto. Los endpoints bajo `/admin` que usan la cola de aprobación requieren estas variables; el resto de la API puede funcionar solo con Spotify.

### 6. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

El servidor quedará corriendo en `http://127.0.0.1:8000`.

Para especificar host y puerto:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Documentación interactiva

Una vez levantado el servidor, accede a:

- Swagger UI: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
- ReDoc: [http://127.0.0.1:8000/api/redoc](http://127.0.0.1:8000/api/redoc)

> Todas las rutas viven bajo el prefijo `/api` porque en producción nginx proxea `aritmetrica.lat/api/*` hacia la app FastAPI (el resto del dominio queda libre para el frontend).

---

## Endpoints disponibles

### General

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/` | Health check de la API |

### Spotify

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/spotify/credentials` | Retorna `client_id` y `client_secret` configurados |
| GET | `/api/spotify/artists` | Lista todos los artistas con sus IDs de Spotify |
| GET | `/api/spotify/artist/{artist_id}/listeners` | Oyentes mensuales de un artista (scraping) |

### YouTube

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/youtube/artists` | Lista todos los artistas con sus IDs de canal de YouTube |

### CORS

La app configura CORS vía la variable `CORS_ORIGINS` (lista separada por comas en `.env`). Por defecto incluye `https://aritmetrica.lat`, `https://www.aritmetrica.lat`, `http://localhost:3000` y `http://127.0.0.1:3000`.

---

## Despliegue en producción (VPS)

En muchos VPS el mismo servidor MySQL ya aloja otras bases de datos. Eso no es problema: esta API usa **solo** la base `aritmetrica-stats` (nombre con guion: en SQL y en `MYSQL_DATABASE` va tal cual). Conviene crear un usuario MySQL dedicado con permisos únicamente sobre esa base (`GRANT … ON \`aritmetrica-stats\`.*`), para no mezclar privilegios con el resto de proyectos.

### Crear y poblar la base con el script SQL

1. Sube el repositorio al VPS (o al menos los archivos `sql/todo_aritmetrica.sql` y, si actualizas datos, `app/data/artist_ids.py` más `scripts/generate_aritmetrica_sql.py`).
2. El archivo `sql/todo_aritmetrica.sql` hace lo siguiente:
   - `CREATE DATABASE IF NOT EXISTS` + `USE` para `aritmetrica-stats`
   - Elimina y vuelve a crear las tablas del proyecto (`DROP` al inicio)
   - Inserta el seed de artistas Spotify/YouTube según `artist_ids.py` en el momento en que se generó el archivo

   **No lo ejecutes a ciegas sobre una base que ya tenga datos de producción** que quieras conservar: los `DROP TABLE` borran solo las tablas de este esquema dentro de esa base, pero al recrear se pierde lo que hubiera en ellas.

3. Desde el VPS, con el cliente `mysql` y un usuario con permiso para crear la base (o que ya tenga la base creada y permisos sobre ella):

   ```bash
   mysql -h 127.0.0.1 -u TU_USUARIO -p < sql/todo_aritmetrica.sql
   ```

   Si tu instancia MySQL escucha solo en socket o en otro puerto, ajusta `-h` y `-P`.

4. La API corriendo **en el mismo VPS** debe apuntar a ese MySQL local (por ejemplo `MYSQL_HOST=127.0.0.1` y el mismo `MYSQL_DATABASE`, usuario y contraseña que usaste para la importación).

### Regenerar el SQL después de cambiar `artist_ids.py`

En tu máquina de desarrollo (o en el VPS, con Python y el repo):

```bash
python scripts/generate_aritmetrica_sql.py
```

Eso sobrescribe `sql/todo_aritmetrica.sql`. Vuelve a subir el archivo y ejecútalo en el servidor solo cuando quieras **reaplicar** el seed completo (recordando que los `DROP` reinician esas tablas).

### Servidor FastAPI

En tu VPS, en lugar de `--reload` corre el servidor con varios workers:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Recomendado además:

- Servir detrás de un reverse proxy (nginx o Caddy) para HTTPS y compresión.
- Correr el proceso bajo `systemd` para reinicio automático.

### Dejar la API corriendo en segundo plano (recomendado: systemd)

`systemd` es la forma más segura de mantener la API viva en un VPS, reiniciarla si cae y arrancarla automáticamente al reiniciar el servidor.

1. Crea una carpeta de despliegue (ejemplo: `/opt/aritstats`) y deja ahí el proyecto:

```bash
sudo mkdir -p /opt/aritstats
sudo chown -R $USER:$USER /opt/aritstats
cd /opt/aritstats
git clone <url-del-repo> .
```

2. Crea el entorno virtual e instala dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

3. Configura `.env` con tus credenciales reales (Spotify/MySQL).

4. Crea el archivo del servicio:

```bash
sudo nano /etc/systemd/system/aritstats.service
```

Contenido (ajusta `User`, `Group` y rutas si corresponde):

```ini
[Unit]
Description=AristStats FastAPI service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/aritstats
EnvironmentFile=/opt/aritstats/.env
ExecStart=/opt/aritstats/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

5. Activa y levanta el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aritstats
sudo systemctl start aritstats
```

6. Verifica estado y logs:

```bash
sudo systemctl status aritstats
sudo journalctl -u aritstats -f
```

Comandos utiles:

```bash
sudo systemctl restart aritstats
sudo systemctl stop aritstats
sudo systemctl start aritstats
```

> Si usas nginx como proxy reverso, apunta `location /api/` a `http://127.0.0.1:8000`.

### Opción rápida (menos robusta): `nohup`

Si solo quieres dejarlo corriendo temporalmente en segundo plano:

```bash
nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 > aritstats.log 2>&1 &
```

Luego puedes validar con:

```bash
ps aux | rg uvicorn
```

Esta opción **no** reinicia el proceso automáticamente si el servidor se reinicia o si la app se cae, por eso `systemd` sigue siendo la recomendada.
