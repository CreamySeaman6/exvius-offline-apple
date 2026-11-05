# Exvius Offline game server for the iPhone app. Build from the repository root:
#   docker compose -f ios-server/docker-compose.yml build
FROM python:3.12-slim

RUN pip install --no-cache-dir "cryptography>=42" "pyyaml>=6" tzdata

WORKDIR /app
COPY source/server /app/server
COPY data/latest.json /app/latest.json
COPY ios-server/serve.py ios-server/certs.py ios-server/fetch_data.py ios-server/ffbe.py /app/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FFBE_ENGINE=/app/server \
    FFBE_DATA_DIR=/srv/ffbe/data \
    FFBE_SERVER_ROOT=/srv/ffbe/server-root

VOLUME ["/srv/ffbe/data", "/srv/ffbe/server-root"]
ENTRYPOINT ["python3", "/app/ffbe.py"]
CMD ["serve"]
