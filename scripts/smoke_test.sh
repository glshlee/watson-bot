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

echo "3. Testing POST /api/chat (ADR-004 Smart Butler Workflow)..."

echo "  3-1. Testing Chat Only (인사/잡담 - 마크다운 기록 X)..."
CHAT_RES1=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "안녕하세요 왓슨!", "auto_push": false}')
if echo "$CHAT_RES1" | grep -q '"intent":"chat_only"'; then
    echo "  ✅ 3-1. Chat Only Passed (intent=chat_only, No File Created)"
else
    echo "  ❌ 3-1. Chat Only Failed. Response: $CHAT_RES1"
    exit 1
fi

echo "  3-2. Testing Lifelog Suggestion (운동 일과 감지 - 제안 생성)..."
CHAT_RES2=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "오늘 저녁 한강 러닝 5km 뛰었어", "auto_push": false}')
if echo "$CHAT_RES2" | grep -q '"intent":"log_suggest"'; then
    echo "  ✅ 3-2. Suggestion Passed (intent=log_suggest, Pending Log Saved)"
else
    echo "  ❌ 3-2. Suggestion Failed. Response: $CHAT_RES2"
    exit 1
fi

echo "  3-3. Testing Confirmation & Commit (승인 - 마크다운 기록 생성)..."
CHAT_RES3=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "응 좋아", "auto_push": false}')
if echo "$CHAT_RES3" | grep -q '"intent":"log_confirm"'; then
    echo "  ✅ 3-3. Confirmation Passed (intent=log_confirm, File Written)"
else
    echo "  ❌ 3-3. Confirmation Failed. Response: $CHAT_RES3"
    exit 1
fi

echo "  3-4. Testing Direct Command (/log - 직접 마크다운 기록)..."
CHAT_RES4=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "/log 프로젝트 기획 완료", "auto_push": false}')
if echo "$CHAT_RES4" | grep -q '"intent":"log_explicit"'; then
    echo "  ✅ 3-4. Direct Command Passed (intent=log_explicit)"
else
    echo "  ❌ 3-4. Direct Command Failed. Response: $CHAT_RES4"
    exit 1
fi

if [ "$TRAP_EXIT" = "1" ] && [ -n "$SERVER_PID" ]; then
    echo "Cleaning up temporary test server (PID: $SERVER_PID)..."
    kill "$SERVER_PID" || true
fi

echo "🎉 All Curl Smoke Tests Passed Successfully!"
