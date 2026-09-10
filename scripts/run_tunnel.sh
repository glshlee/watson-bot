#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

LOG_FILE="$DIR/tunnel.log"
URL_FILE="$DIR/tunnel_url.txt"

# Read .env if present
TOKEN=""
if [ -f .env ]; then
    TOKEN=$(grep -E '^CLOUDFLARE_TUNNEL_TOKEN=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]' || true)
fi

if [ -n "$TOKEN" ]; then
    echo "Starting Cloudflare Tunnel with dedicated token (HTTP/2)..."
    exec /usr/local/bin/cloudflared tunnel run --protocol http2 --retries 10 --token "$TOKEN"
else
    echo "Starting Cloudflare Quick Tunnel on port 8000 (HTTP/2)..."
    > "$LOG_FILE"
    /usr/local/bin/cloudflared tunnel --url http://localhost:8000 --protocol http2 --retries 10 --logfile "$LOG_FILE" &
    PID=$!

    # Extract assigned trycloudflare.com URL and write to file
    (
        for i in {1..20}; do
            if [ -f "$LOG_FILE" ]; then
                ASSIGNED_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$LOG_FILE" | head -n 1 || true)
                if [ -n "$ASSIGNED_URL" ]; then
                    echo "$ASSIGNED_URL" > "$URL_FILE"
                    echo "🚀 Cloudflare Quick Tunnel Online: $ASSIGNED_URL"
                    break
                fi
            fi
            sleep 1
        done
    ) &

    wait $PID
fi
