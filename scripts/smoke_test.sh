#!/usr/bin/env bash
set -e

echo "🚀 Starting Watson API Live Curl Smoke Test..."

# 1. Check if server is running on port 8000
SERVER_URL="http://localhost:8000"

if ! curl -s "$SERVER_URL/" > /dev/null; then
    echo "⚠️ Server is not running on port 8000. Launching temporary test server..."
    source venv/bin/activate
    python -m uvicorn app.main:app --port 8000 &
    SERVER_PID=$!
    sleep 2
    TRAP_EXIT=1
fi

echo "1. Testing GET / (HTML Dashboard)..."
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/")
if [ "$RESPONSE_CODE" -ne 200 ]; then
    echo "❌ GET / failed with status $RESPONSE_CODE"
    exit 1
fi
echo "✅ GET / Passed (200 OK)"

echo "2. Testing GET /api/sessions..."
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/api/sessions")
if [ "$RESPONSE_CODE" -ne 200 ]; then
    echo "❌ GET /api/sessions failed with status $RESPONSE_CODE"
    exit 1
fi
echo "✅ GET /api/sessions Passed (200 OK)"

echo "3. Testing POST /api/chat (Interactive AI Chat & Lifelog)..."
CHAT_RESPONSE=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "curl_smoke_session", "message": "Curl smoke test log", "category": "Daily Notes & Diary", "auto_push": false}')

if echo "$CHAT_RESPONSE" | grep -q "ai_response"; then
    echo "✅ POST /api/chat Passed (AI Response Received)"
else
    echo "❌ POST /api/chat Failed. Response: $CHAT_RESPONSE"
    exit 1
fi

if [ "$TRAP_EXIT" = "1" ] && [ -n "$SERVER_PID" ]; then
    echo "Cleaning up temporary test server (PID: $SERVER_PID)..."
    kill "$SERVER_PID" || true
fi

echo "🎉 All Curl Smoke Tests Passed Successfully!"
