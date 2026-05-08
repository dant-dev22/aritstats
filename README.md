# AristStats API

API REST construida con FastAPI para consultar estadísticas de artistas de rap/hip-hop latinoamericano en Spotify y YouTube.

## Actualizar en VPS con script

Este proyecto incluye `scripts/deploy.sh` para actualizar código en el VPS y reiniciar el servicio gestionado por `systemd`.

### Flujo del script

1. Descarga cambios del repositorio (`git fetch` + `git pull`).
2. Actualiza dependencias del entorno virtual.
3. Reinicia el servicio en `systemd`.
4. Muestra estado y logs recientes del servicio.

### Uso

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Opciones útiles

```bash
./scripts/deploy.sh --branch main
./scripts/deploy.sh --service aritstats
./scripts/deploy.sh --app-dir .
```

### Nota sobre base de datos y seed

El deploy normal **no** reaplica seed de base de datos.

Si algún día quieres hacerlo manualmente, puedes usar:

```bash
./scripts/deploy.sh --with-seed
```

`sql/todo_aritmetrica.sql` recrea tablas del proyecto (`DROP` + `CREATE`), así que úsalo solo cuando realmente quieras resetear/reaplicar esos datos.
