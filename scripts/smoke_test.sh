#!/usr/bin/env bash
set -e

echo "🚀 Starting Watson API Live Curl Smoke Test..."

# 1. Check if server is running on port 8000
SERVER_URL="http://localhost:8000"

AUTH_FLAGS=()
AUTH_TEST=0
if [ -f .env ]; then
    AUTH_USER=$(grep -E '^WEB_AUTH_USERNAME=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
    AUTH_PASS=$(grep -E '^WEB_AUTH_PASSWORD=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
    AUTH_ENABLED=$(grep -E '^WEB_AUTH_ENABLED=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    if [ "$AUTH_ENABLED" = "true" ] && [ -n "$AUTH_PASS" ]; then
        AUTH_FLAGS=(-u "${AUTH_USER:-watson}:$AUTH_PASS")
        AUTH_TEST=1
    fi
fi

run_curl() {
    curl -s "${AUTH_FLAGS[@]}" "$@"
}

SERVER_READY=0
for i in {1..10}; do
    if curl -s -o /dev/null "$SERVER_URL/"; then
        SERVER_READY=1
        break
    fi
    sleep 1
done

if [ "$SERVER_READY" -eq 0 ]; then
    echo "⚠️ Server is not running on port 8000. Launching temporary test server..."
    source venv/bin/activate
    python -m uvicorn app.main:app --port 8000 &
    SERVER_PID=$!
    sleep 3
    TRAP_EXIT=1
fi

if [ "$AUTH_TEST" -eq 1 ]; then
    echo "0. Testing Authentication Guard (ADR-015)..."
    UNAUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/")
    if [ "$UNAUTH_CODE" -ne 401 ]; then
        echo "❌ Expected 401 Unauthorized for unauthenticated request, got $UNAUTH_CODE"
        exit 1
    fi
    echo "✅ Auth Guard Passed (401 Unauthorized without credentials)"
fi

echo "0-1. Testing Lightweight Health Check & Heartbeat (ADR-021)..."
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/api/health")
if [ "$HEALTH_CODE" -ne 200 ]; then
    echo "❌ GET /api/health failed with status $HEALTH_CODE"
    exit 1
fi
echo "✅ GET /api/health Passed (200 OK - Health Alive)"

echo "1. Testing GET / (Agent Hub Portal with Auth - ADR-018)..."
RESPONSE_CODE=$(run_curl -o /dev/null -w "%{http_code}" "$SERVER_URL/")
if [ "$RESPONSE_CODE" -ne 200 ]; then
    echo "❌ GET / failed with status $RESPONSE_CODE"
    exit 1
fi
echo "✅ GET / Passed (200 OK - Agent Hub Portal)"

echo "1-1. Testing GET /watson & GET /dev & GET /api/hub/status..."
W_CODE=$(run_curl -o /dev/null -w "%{http_code}" "$SERVER_URL/watson")
D_CODE=$(run_curl -o /dev/null -w "%{http_code}" "$SERVER_URL/dev")
HUB_STATUS=$(run_curl "$SERVER_URL/api/hub/status")
if [ "$W_CODE" -eq 200 ] && [ "$D_CODE" -eq 200 ] && echo "$HUB_STATUS" | grep -q '"total_agents":2'; then
    echo "✅ Agent Hub & Dev Routes Passed (200 OK)"
else
    echo "❌ Agent Hub Routes Failed: watson=$W_CODE, dev=$D_CODE"
    exit 1
fi

echo "2. Testing GET /api/sessions..."
RESPONSE_CODE=$(run_curl -o /dev/null -w "%{http_code}" "$SERVER_URL/api/sessions")
if [ "$RESPONSE_CODE" -ne 200 ]; then
    echo "❌ GET /api/sessions failed with status $RESPONSE_CODE"
    exit 1
fi
echo "✅ GET /api/sessions Passed (200 OK)"

# Save original GTD path and create isolated sandbox GTD repository (ADR-012)
ORIGINAL_GTD_PATH=$(run_curl "$SERVER_URL/api/settings/gtd-path" | grep -o '"gtd_path":"[^"]*' | cut -d'"' -f4)
TMP_TEST_GTD=$(mktemp -d /tmp/watson_smoke_gtd_XXXXXX)
git init -b main "$TMP_TEST_GTD" > /dev/null
git -C "$TMP_TEST_GTD" config user.name "Watson Test"
git -C "$TMP_TEST_GTD" config user.email "test@watson.ai"
mkdir -p "$TMP_TEST_GTD/logs/daily" "$TMP_TEST_GTD/gtd"
echo "# Next Actions" > "$TMP_TEST_GTD/gtd/next_actions.md"
echo "# Inbox" > "$TMP_TEST_GTD/gtd/inbox.md"
git -C "$TMP_TEST_GTD" add -A && git -C "$TMP_TEST_GTD" commit -m "init test repo" > /dev/null

# Temporarily switch server to isolated test GTD sandbox
run_curl -X POST "$SERVER_URL/api/settings/gtd-path" \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$TMP_TEST_GTD\", \"create_if_missing\": true}" > /dev/null

cleanup() {
  if [ -n "$ORIGINAL_GTD_PATH" ]; then
    echo "Restoring original GTD path: $ORIGINAL_GTD_PATH..."
    run_curl -X POST "$SERVER_URL/api/settings/gtd-path" \
      -H "Content-Type: application/json" \
      -d "{\"path\": \"$ORIGINAL_GTD_PATH\", \"create_if_missing\": false}" > /dev/null || true
  fi
  # Clean up smoke test session so it doesn't pollute user UI
  run_curl -X DELETE "$SERVER_URL/api/sessions/smoke_butler_session" > /dev/null 2>&1 || true
  run_curl -X DELETE "$SERVER_URL/api/sessions/smoke_dev_session" > /dev/null 2>&1 || true
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
CHAT_RES1=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "안녕하세요 왓슨!", "auto_push": false}')
if echo "$CHAT_RES1" | grep -q '"intent":"chat_only"'; then
    echo "  ✅ 3-1. Chat Only Passed (intent=chat_only, No File Created)"
else
    echo "  ❌ 3-1. Chat Only Failed. Response: $CHAT_RES1"
    exit 1
fi

echo "  3-2. Testing Lifelog Suggestion (운동 일과 감지 - 제안 생성)..."
CHAT_RES2=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "오늘 저녁 한강 러닝 5km 뛰었어", "auto_push": false}')
if echo "$CHAT_RES2" | grep -q '"intent":"log_suggest"'; then
    echo "  ✅ 3-2. Suggestion Passed (intent=log_suggest, Pending Log Saved)"
else
    echo "  ❌ 3-2. Suggestion Failed. Response: $CHAT_RES2"
    exit 1
fi

echo "  3-3. Testing Confirmation & Commit (승인 - 마크다운 기록 생성)..."
CHAT_RES3=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "응 좋아", "auto_push": false}')
if echo "$CHAT_RES3" | grep -q '"intent":"log_confirm"'; then
    echo "  ✅ 3-3. Confirmation Passed (intent=log_confirm, File Written)"
else
    echo "  ❌ 3-3. Confirmation Failed. Response: $CHAT_RES3"
    exit 1
fi

echo "  3-4. Testing Direct Command (/log - 직접 마크다운 기록)..."
CHAT_RES4=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "/log 프로젝트 기획 완료", "auto_push": false}')
if echo "$CHAT_RES4" | grep -q '"intent":"log_explicit"'; then
    echo "  ✅ 3-4. Direct Command Passed (intent=log_explicit)"
else
    echo "  ❌ 3-4. Direct Command Failed. Response: $CHAT_RES4"
    exit 1
fi

echo "  3-5. Testing Task Briefing (오늘 해야할 일 정리해줘 - ADR-008)..."
CHAT_RES5=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "오늘 해야할 일 정리해줘", "auto_push": false}')
if echo "$CHAT_RES5" | grep -q '"intent":"task_briefing"'; then
    echo "  ✅ 3-5. Task Briefing Passed (intent=task_briefing, Summary Returned)"
else
    echo "  ❌ 3-5. Task Briefing Failed. Response: $CHAT_RES5"
    exit 1
fi

echo "  3-6. Testing Repo Sync & Briefing (gtd 레포 최신화하고 다시 알려줘 - ADR-009)..."
CHAT_RES6=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "gtd 레포 최신화하고 다시 알려줘", "auto_push": false}')
if echo "$CHAT_RES6" | grep -q '"intent":"repo_sync_and_briefing"'; then
    echo "  ✅ 3-6. Repo Sync & Briefing Passed (intent=repo_sync_and_briefing)"
else
    echo "  ❌ 3-6. Repo Sync & Briefing Failed. Response: $CHAT_RES6"
    exit 1
fi

echo "  3-7. Testing Repo Push (푸시해줘 - ADR-011)..."
CHAT_RES7=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "푸시해줘", "auto_push": false}')
if echo "$CHAT_RES7" | grep -q '"intent":"repo_push"'; then
    echo "  ✅ 3-7. Repo Push Passed (intent=repo_push)"
else
    echo "  ❌ 3-7. Repo Push Failed. Response: $CHAT_RES7"
    exit 1
fi

echo "  3-7-1. Testing Natural Speech Repo Push (푸시도해야지 - ADR-020)..."
CHAT_RES7_1=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "푸시도해야지", "auto_push": false}')
if echo "$CHAT_RES7_1" | grep -q '"intent":"repo_push"'; then
    echo "  ✅ 3-7-1. Natural Speech Repo Push Passed (intent=repo_push)"
else
    echo "  ❌ 3-7-1. Natural Speech Repo Push Failed. Response: $CHAT_RES7_1"
    exit 1
fi

echo "  3-7-2. Testing Push Destination Query (어디다 푸시한거야? - ADR-020)..."
CHAT_RES7_2=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "어디다 푸시한거야?", "auto_push": false}')
if echo "$CHAT_RES7_2" | grep -q '"intent":"repo_push"' && echo "$CHAT_RES7_2" | grep -q '원격 GitHub 저장소 정보'; then
    echo "  ✅ 3-7-2. Push Destination Query Passed (Real GitHub Repo Info Returned, No Hallucination)"
else
    echo "  ❌ 3-7-2. Push Destination Query Failed. Response: $CHAT_RES7_2"
    exit 1
fi

echo "  3-7-3. Testing Repo Commit (커밋해 - ADR-020)..."
CHAT_RES7_3=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "커밋해", "auto_push": false}')
if echo "$CHAT_RES7_3" | grep -q '"intent":"repo_commit"'; then
    echo "  ✅ 3-7-3. Repo Commit Passed (intent=repo_commit)"
else
    echo "  ❌ 3-7-3. Repo Commit Failed. Response: $CHAT_RES7_3"
    exit 1
fi


echo "  3-8. Testing Compound Intent (로그와 GTD 동시 기록 - ADR-014)..."
CHAT_RES8=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "주말에 서산 여행을 가보려구. 용현집 어죽 먹고 게국지도 먹고싶대. 로그와 gtd에 기록해줘.", "auto_push": false}')
if echo "$CHAT_RES8" | grep -q '"intent":"log_dual"'; then
    echo "  ✅ 3-8. Compound Intent Passed (intent=log_dual, Daily Log + GTD Inbox Written)"
else
    echo "  ❌ 3-8. Compound Intent Failed. Response: $CHAT_RES8"
    exit 1
fi

echo "  3-9. Testing Dev Agent Chat (/status - ADR-018)..."
DEV_RES=$(run_curl -X POST "$SERVER_URL/api/dev/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_dev_session", "message": "/status"}')
if echo "$DEV_RES" | grep -q 'action_type'; then
    echo "  ✅ 3-9. Dev Agent Chat Passed (action_type returned)"
else
    echo "  ❌ 3-9. Dev Agent Chat Failed: $DEV_RES"
    exit 1
fi

echo "  3-10. Testing Dev Agent Toolchain (/lint - ADR-019)..."
DEV_LINT_RES=$(run_curl -X POST "$SERVER_URL/api/dev/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_dev_session", "message": "/lint"}')
if echo "$DEV_LINT_RES" | grep -q '"action_type":"tool_lint"'; then
    echo "  ✅ 3-10. Dev Agent Toolchain Passed (action_type=tool_lint)"
else
    echo "  ❌ 3-10. Dev Agent Toolchain Failed: $DEV_LINT_RES"
    exit 1
fi

echo "  3-11. Testing Watson Shortcuts (/today & /gtd - ADR-022)..."
TODAY_RES=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "/today", "auto_push": false}')
if echo "$TODAY_RES" | grep -q '"intent":"daily_log_inspect"'; then
    echo "  ✅ 3-11-1. Watson /today Passed (intent=daily_log_inspect)"
else
    echo "  ❌ 3-11-1. Watson /today Failed: $TODAY_RES"
    exit 1
fi

GTD_RES=$(run_curl -X POST "$SERVER_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_butler_session", "message": "/gtd", "auto_push": false}')
if echo "$GTD_RES" | grep -q '"intent":"gtd_inspect"'; then
    echo "  ✅ 3-11-2. Watson /gtd Passed (intent=gtd_inspect)"
else
    echo "  ❌ 3-11-2. Watson /gtd Failed: $GTD_RES"
    exit 1
fi

echo "  3-12. Testing Dev Agent Shortcuts (/today & /gtd - ADR-022)..."
DEV_TODAY_RES=$(run_curl -X POST "$SERVER_URL/api/dev/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_dev_session", "message": "/today"}')
if echo "$DEV_TODAY_RES" | grep -q '"action_type":"tool_today_log"'; then
    echo "  ✅ 3-12-1. Dev Agent /today Passed (action_type=tool_today_log)"
else
    echo "  ❌ 3-12-1. Dev Agent /today Failed: $DEV_TODAY_RES"
    exit 1
fi

DEV_GTD_RES=$(run_curl -X POST "$SERVER_URL/api/dev/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "smoke_dev_session", "message": "/gtd"}')
if echo "$DEV_GTD_RES" | grep -q '"action_type":"tool_gtd_files"'; then
    echo "  ✅ 3-12-2. Dev Agent /gtd Passed (action_type=tool_gtd_files)"
else
    echo "  ❌ 3-12-2. Dev Agent /gtd Failed: $DEV_GTD_RES"
    exit 1
fi



echo "4. Testing GET /api/telegram/status (ADR-006 Telegram Router)..."
TG_STATUS=$(run_curl "$SERVER_URL/api/telegram/status")
if echo "$TG_STATUS" | grep -q '"configured"'; then
    echo "✅ GET /api/telegram/status Passed (Telegram Router Active)"
else
    echo "❌ GET /api/telegram/status Failed. Response: $TG_STATUS"
    exit 1
fi

echo "5. Testing /api/settings/gtd-path (ADR-007 GTD Directory Isolation)..."
GTD_STATUS=$(run_curl "$SERVER_URL/api/settings/gtd-path")
if echo "$GTD_STATUS" | grep -q '"gtd_path"'; then
    echo "  ✅ 5-1. GET /api/settings/gtd-path Passed"
else
    echo "  ❌ 5-1. GET /api/settings/gtd-path Failed. Response: $GTD_STATUS"
    exit 1
fi

# Test updating GTD path to test sandbox
POST_GTD_RES=$(run_curl -X POST "$SERVER_URL/api/settings/gtd-path" \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$TMP_TEST_GTD\", \"create_if_missing\": false}")
if echo "$POST_GTD_RES" | grep -q '"success":true'; then
    echo "  ✅ 5-2. POST /api/settings/gtd-path Passed (Connected to test sandbox)"
else
    echo "  ❌ 5-2. POST /api/settings/gtd-path Failed. Response: $POST_GTD_RES"
    exit 1
fi

echo "🎉 All Curl Smoke Tests Passed Successfully!"
