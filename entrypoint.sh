#!/bin/sh
set -e

# Wait for MySQL to be ready
echo "Waiting for MySQL at ${MYSQL_HOST:-mysql}:${MYSQL_PORT:-3306}..."
until python -c "
import pymysql, os, sys
try:
    pymysql.connect(
        host=os.getenv('MYSQL_HOST','mysql'),
        port=int(os.getenv('MYSQL_PORT','3306')),
        user=os.getenv('MYSQL_USER','opd_user'),
        password=os.getenv('MYSQL_PASSWORD','opd_password'),
        database=os.getenv('MYSQL_DB','opd_vertex'),
    ).close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    echo "MySQL not ready yet, retrying in 2s..."
    sleep 2
done
echo "MySQL is ready."

# Run Alembic migrations
alembic upgrade head

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
