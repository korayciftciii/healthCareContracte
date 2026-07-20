#!/bin/sh
set -e

echo "Bekleniyor: Postgres..."
python - <<'EOF'
import os, sys, time
import psycopg2
from urllib.parse import urlparse

url = urlparse(os.environ["DATABASE_URL"])
for i in range(30):
    try:
        psycopg2.connect(
            dbname=url.path.lstrip("/"),
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port or 5432,
        ).close()
        print("Postgres hazir.")
        sys.exit(0)
    except Exception:
        time.sleep(1)
print("Postgres'e baglanilamadi.", file=sys.stderr)
sys.exit(1)
EOF

echo "Migrasyonlar uygulaniyor..."
python manage.py migrate --noinput

echo "Statik dosyalar toplaniyor..."
python manage.py collectstatic --noinput

echo "Baslatiliyor: gunicorn (port ${GUNICORN_PORT:-8000})..."
exec gunicorn config.wsgi:application --bind "0.0.0.0:${GUNICORN_PORT:-8000}" --workers 3
