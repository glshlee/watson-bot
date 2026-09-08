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

# Save original GTD path and create isolated sandbox GTD repository (ADR-012)
ORIGINAL_GTD_PATH=$(curl -s "$SERVER_URL/api/settings/gtd-path" | grep -o '"gtd_path":"[^"]*' | cut -d'"' -f4)
TMP_TEST_GTD=$(mktemp -d /tmp/watson_smoke_gtd_XXXXXX)
git init -b main "$TMP_TEST_GTD" > /dev/null
git -C "$TMP_TEST_GTD" config user.name "Watson Test"
git -C "$TMP_TEST_GTD" config user.email "test@watson.ai"
mkdir -p "$TMP_TEST_GTD/logs/daily" "$TMP_TEST_GTD/gtd"
echo "# Next Actions" > "$TMP_TEST_GTD/gtd/next_actions.md"
echo "# Inbox" > "$TMP_TEST_GTD/gtd/inbox.md"
git -C "$TMP_TEST_GTD" add -A && git -C "$TMP_TEST_GTD" commit -m "init test repo" > /dev/null

# Temporarily switch server to isolated test GTD sandbox
curl -s -X POST "$SERVER_URL/api/settings/gtd-path" \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$TMP_TEST_GTD\", \"create_if_missing\": true}" > /dev/null

cleanup() {
  if [ -n "$ORIGINAL_GTD_PATH" ]; then
    echo "Restoring original GTD path: $ORIGINAL_GTD_PATH..."
    curl -s -X POST "$SERVER_URL/api/settings/gtd-path" \
      -H "Content-Type: application/json" \
      -d "{\"path\": \"$ORIGINAL_GTD_PATH\", \"create_if_missing\": false}" > /dev/null || true
  fi
  if [ -n "$TMP_TEST_GTD" ] && [ -d "$TMP_TEST_GTD" ]; then
    rm -rf "$TMP_TEST_GTD" || true
  fi
  if [ "$TRAP_EXIT" = "1" ] && [ -n "$SERVER_PID" ]; then
    echo "Cleaning up temporary test server (PID: $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

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

echo "  3-5. Testing Task Briefing (오늘 해야할 일 정리해줘 - ADR-008)..."
CHAT_RES5=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "오늘 해야할 일 정리해줘", "auto_push": false}')
if echo "$CHAT_RES5" | grep -q '"intent":"task_briefing"'; then
    echo "  ✅ 3-5. Task Briefing Passed (intent=task_briefing, Summary Returned)"
else
    echo "  ❌ 3-5. Task Briefing Failed. Response: $CHAT_RES5"
    exit 1
fi

echo "  3-6. Testing Repo Sync & Briefing (gtd 레포 최신화하고 다시 알려줘 - ADR-009)..."
CHAT_RES6=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "gtd 레포 최신화하고 다시 알려줘", "auto_push": false}')
if echo "$CHAT_RES6" | grep -q '"intent":"repo_sync_and_briefing"'; then
    echo "  ✅ 3-6. Repo Sync & Briefing Passed (intent=repo_sync_and_briefing)"
else
    echo "  ❌ 3-6. Repo Sync & Briefing Failed. Response: $CHAT_RES6"
    exit 1
fi

echo "  3-7. Testing Repo Push (푸시해줘 - ADR-011)..."
CHAT_RES7=$(curl -s -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "푸시해줘", "auto_push": false}')
if echo "$CHAT_RES7" | grep -q '"intent":"repo_push"'; then
    echo "  ✅ 3-7. Repo Push Passed (intent=repo_push)"
else
    echo "  ❌ 3-7. Repo Push Failed. Response: $CHAT_RES7"
    exit 1
fi


echo "4. Testing GET /api/telegram/status (ADR-006 Telegram Router)..."
TG_STATUS=$(curl -s "$SERVER_URL/api/telegram/status")
if echo "$TG_STATUS" | grep -q '"configured"'; then
    echo "✅ GET /api/telegram/status Passed (Telegram Router Active)"
else
    echo "❌ GET /api/telegram/status Failed. Response: $TG_STATUS"
    exit 1
fi

echo "5. Testing /api/settings/gtd-path (ADR-007 GTD Directory Isolation)..."
GTD_STATUS=$(curl -s "$SERVER_URL/api/settings/gtd-path")
if echo "$GTD_STATUS" | grep -q '"gtd_path"'; then
    echo "  ✅ 5-1. GET /api/settings/gtd-path Passed"
else
    echo "  ❌ 5-1. GET /api/settings/gtd-path Failed. Response: $GTD_STATUS"
    exit 1
fi

# Test updating GTD path to test sandbox
POST_GTD_RES=$(curl -s -X POST "$SERVER_URL/api/settings/gtd-path" \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$TMP_TEST_GTD\", \"create_if_missing\": false}")
if echo "$POST_GTD_RES" | grep -q '"success":true'; then
    echo "  ✅ 5-2. POST /api/settings/gtd-path Passed (Connected to test sandbox)"
else
    echo "  ❌ 5-2. POST /api/settings/gtd-path Failed. Response: $POST_GTD_RES"
    exit 1
fi

echo "🎉 All Curl Smoke Tests Passed Successfully!"
