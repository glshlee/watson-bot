#!/usr/bin/env bash
# ==============================================================================
# Watson AI Butler - 1-Click Self-Hosting Setup Wizard (ADR-046)
# 24/7 GitHub LifeLog & GTD Personal Assistant Setup Automation
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ANSI Color Codes
BOLD="\033[1m"
GREEN="\033[1;32m"
BLUE="\033[1;34m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

NON_INTERACTIVE=false
DRY_RUN=false
RUN_CHECK=false

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║   🤖 Watson AI Butler - 1-Click Self-Hosting Setup Wizard (ADR-046)       ║"
    echo "║   24/7 개인용 GitHub LifeLog & GTD 지능형 비서 올인원 배포 스크립트       ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
}

usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  -y, --non-interactive  사용자 입력 없이 기본값/환경변수로 자동 설치 진행"
    echo "  -d, --dry-run          파일 수정이나 패키지 설치 없이 모의 테스트 실행"
    echo "  -c, --check            현재 설치된 Watson 시스템 설정 및 준비 상태 점검"
    echo "  -h, --help             본 도움말 메시지 출력"
    echo ""
    exit 0
}

# Parse Command Line Arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--non-interactive|--unattended)
            NON_INTERACTIVE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -c|--check)
            RUN_CHECK=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}알 수 없는 옵션: $1${RESET}"
            usage
            ;;
    esac
done

print_banner

# Step 0: Check Mode
if [ "$RUN_CHECK" = true ]; then
    echo -e "${BLUE}🔍 시스템 설정 및 준비 상태를 점검합니다...${RESET}"
    if [ -f ".env" ]; then
        echo -e "  ✅ .env 파일 존재"
    else
        echo -e "  ❌ .env 파일이 없습니다. 셋업 위저드를 실행하세요."
    fi

    if [ -d "venv" ]; then
        echo -e "  ✅ venv 가상환경 디렉토리 존재"
        if [ -f "venv/bin/python" ]; then
            PY_VER=$(venv/bin/python --version 2>&1 || echo "Unknown")
            echo -e "  ✅ Python 런타임: $PY_VER"
        fi
    else
        echo -e "  ⚠️ venv 가상환경이 생성되지 않았습니다."
    fi

    if [ -d "config" ]; then
        echo -e "  ✅ config 디렉토리 존재"
        [ -f "config/gtd_config.json" ] && echo -e "  ✅ config/gtd_config.json 설정됨"
        [ -f "config/commute_config.json" ] && echo -e "  ✅ config/commute_config.json 설정됨"
        [ -f "config/telegram_commands.json" ] && echo -e "  ✅ config/telegram_commands.json 설정됨"
    fi
    exit 0
fi

echo -e "${BLUE}💡 Watson 비서를 서버에 10분 만에 배포할 수 있도록 안내합니다.${RESET}"
echo -e "${YELLOW}[Enter]를 누르면 대괄호 [기본값]이 적용됩니다.${RESET}\n"

# Step 1: Check Prerequisite Tools
echo -e "${BOLD}[1/7] 🛠️ 필수 시스템 도구 확인${RESET}"
for cmd in python3 git curl; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "  ✅ $cmd 설치 확인: $(command -v "$cmd")"
    else
        echo -e "  ❌ $cmd 가 설치되어 있지 않습니다. sudo apt-get install $cmd 명령으로 설치해주세요."
        exit 1
    fi
done

# Step 2: Read current .env if exists for smart defaults
DEFAULT_PORT="8000"
DEFAULT_TZ="Asia/Seoul"
DEFAULT_TG_TOKEN=""
DEFAULT_TG_CHAT_ID=""
DEFAULT_GEMINI_KEY=""
DEFAULT_GTD_PATH="$HOME/lifelog"
DEFAULT_LOCATION="성동구 금호동"
DEFAULT_WEB_AUTH="false"
DEFAULT_WEB_USER="watson"
DEFAULT_WEB_PW="watson_secret_1234"

if [ -f ".env" ]; then
    echo -e "\n  ℹ️ 기존 .env 파일의 설정값을 불러왔습니다."
    # shellcheck disable=SC1091
    source <(grep -E '^(PORT|TIMEZONE|TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_CHAT_IDS|GEMINI_API_KEY|LLM_API_KEY|GTD_PATH|WEB_AUTH_ENABLED|WEB_AUTH_USERNAME|WEB_AUTH_PASSWORD)=' .env 2>/dev/null || true)
    [ -n "$PORT" ] && DEFAULT_PORT="$PORT"
    [ -n "$TIMEZONE" ] && DEFAULT_TZ="$TIMEZONE"
    [ -n "$TELEGRAM_BOT_TOKEN" ] && DEFAULT_TG_TOKEN="$TELEGRAM_BOT_TOKEN"
    [ -n "$TELEGRAM_ALLOWED_CHAT_IDS" ] && DEFAULT_TG_CHAT_ID="$TELEGRAM_ALLOWED_CHAT_IDS"
    [ -n "$GEMINI_API_KEY" ] && DEFAULT_GEMINI_KEY="$GEMINI_API_KEY"
    [ -z "$DEFAULT_GEMINI_KEY" ] && [ -n "$LLM_API_KEY" ] && DEFAULT_GEMINI_KEY="$LLM_API_KEY"
    [ -n "$GTD_PATH" ] && DEFAULT_GTD_PATH="$GTD_PATH"
    [ -n "$WEB_AUTH_ENABLED" ] && DEFAULT_WEB_AUTH="$WEB_AUTH_ENABLED"
    [ -n "$WEB_AUTH_USERNAME" ] && DEFAULT_WEB_USER="$WEB_AUTH_USERNAME"
    [ -n "$WEB_AUTH_PASSWORD" ] && DEFAULT_WEB_PW="$WEB_AUTH_PASSWORD"
fi

# Step 3: Interactive Questions
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"

    if [ "$NON_INTERACTIVE" = true ] || [ "$DRY_RUN" = true ] || [ ! -t 0 ]; then
        eval "$var_name=\"$default\""
        return
    fi

    if [ "$is_secret" = true ] && [ -n "$default" ]; then
        masked_default="${default:0:4}...${default: -4}"
        echo -ne "${CYAN}$prompt [현재: $masked_default]: ${RESET}"
    else
        echo -ne "${CYAN}$prompt [$default]: ${RESET}"
    fi

    read -r input_val
    if [ -z "$input_val" ]; then
        eval "$var_name=\"$default\""
    else
        eval "$var_name=\"$input_val\""
    fi
}

echo -e "\n${BOLD}[2/7] 🌐 서버 기본 설정${RESET}"
prompt_input "1. HTTP 서비스 포트 번호" "$DEFAULT_PORT" INPUT_PORT
prompt_input "2. 기본 타임존 (KST)" "$DEFAULT_TZ" INPUT_TZ

echo -e "\n${BOLD}[3/7] 📱 텔레그램 봇 연동 (필수)${RESET}"
echo -e "   ℹ️ 텔레그램에서 @BotFather를 찾아 /newbot 으로 새 봇을 만들고 토큰을 받으세요."
prompt_input "3. 텔레그램 봇 토큰 (HTTP API Token)" "$DEFAULT_TG_TOKEN" INPUT_TG_TOKEN true

echo -e "   ℹ️ 텔레그램 @userinfobot 으로 본인의 숫자 ID를 확인하세요 (예: 123456789)."
prompt_input "4. 관리자 텔레그램 Chat ID (쉼표 구분 복수 가능)" "$DEFAULT_TG_CHAT_ID" INPUT_TG_CHAT_ID

echo -e "\n${BOLD}[4/7] 🧠 AI 엔진 설정 (Gemini API)${RESET}"
echo -e "   ℹ️ Google AI Studio (https://aistudio.google.com/)에서 무료 API 키를 발급받으세요."
prompt_input "5. Gemini API Key (무료 키 가능)" "$DEFAULT_GEMINI_KEY" INPUT_GEMINI_KEY true

echo -e "\n${BOLD}[5/7] 📁 개인 GTD 및 라이프로그 저장소 경로${RESET}"
echo -e "   ℹ️ 일상 일기와 GTD 마크다운이 보관될 전용 폴더입니다."
prompt_input "6. GTD 저장소 절대 경로" "$DEFAULT_GTD_PATH" INPUT_GTD_PATH

echo -e "\n${BOLD}[6/7] 🚌 출근길 & 동네 날씨 브리핑 기본값${RESET}"
prompt_input "7. 거주지 동네명 (기상청/대기질 자동 연동)" "$DEFAULT_LOCATION" INPUT_LOCATION

echo -e "\n${BOLD}[7/7] 🔒 웹 대시보드 보안 (HTTP Basic Auth)${RESET}"
prompt_input "8. 웹 대시보드 비밀번호 잠금 활성화 (true/false)" "$DEFAULT_WEB_AUTH" INPUT_WEB_AUTH
if [ "$INPUT_WEB_AUTH" = "true" ] || [ "$INPUT_WEB_AUTH" = "y" ] || [ "$INPUT_WEB_AUTH" = "yes" ]; then
    INPUT_WEB_AUTH="true"
    prompt_input "   - 웹 로그인 아이디" "$DEFAULT_WEB_USER" INPUT_WEB_USER
    prompt_input "   - 웹 로그인 비밀번호" "$DEFAULT_WEB_PW" INPUT_WEB_PW true
else
    INPUT_WEB_AUTH="false"
fi

# Step 4: Create Files & Directories
echo -e "\n${BOLD}📝 설정 파일 적용 및 디렉토리 생성 중...${RESET}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN 모드] 파일 쓰기를 건너뜁니다.${RESET}"
    echo "  - Port: $INPUT_PORT"
    echo "  - Timezone: $INPUT_TZ"
    echo "  - Telegram Token: ${INPUT_TG_TOKEN:0:6}..."
    echo "  - Allowed Chat IDs: $INPUT_TG_CHAT_ID"
    echo "  - GTD Path: $INPUT_GTD_PATH"
    echo "  - Location: $INPUT_LOCATION"
    echo "  - Web Auth: $INPUT_WEB_AUTH"
    echo -e "${GREEN}✅ Dry-run 모의 셋업 검증 완료!${RESET}"
    exit 0
fi

# 1. Ensure GTD Path Exists
mkdir -p "$INPUT_GTD_PATH/logs/daily"
mkdir -p "$INPUT_GTD_PATH/gtd"
mkdir -p "$INPUT_GTD_PATH/lifelogs"
if [ ! -d "$INPUT_GTD_PATH/.git" ]; then
    echo -e "  📦 GTD 저장소에 Git 초기화 수행 ($INPUT_GTD_PATH)"
    (cd "$INPUT_GTD_PATH" && git init -q && git config user.name "Watson Butler" && git config user.email "watson@local") || true
fi

# Create default inbox.md and next_actions.md if missing
if [ ! -f "$INPUT_GTD_PATH/gtd/inbox.md" ]; then
    cat << 'EOF' > "$INPUT_GTD_PATH/gtd/inbox.md"
# 📥 GTD Inbox (수집함)

## 📌 미분류 태스크
- [ ] Watson 비서 초기 설정 완료 및 텔레그램 테스트
EOF
fi

if [ ! -f "$INPUT_GTD_PATH/gtd/next_actions.md" ]; then
    cat << 'EOF' > "$INPUT_GTD_PATH/gtd/next_actions.md"
# ⚡ Next Actions (다음 행동)

## 🚀 최우선 실행 과제
- [ ] 텔레그램으로 Watson 비서에게 첫 인사 보내기 (/start)
EOF
fi

# 2. Write .env
if [ -f ".env" ]; then
    cp .env ".env.bak.$(date +%Y%m%d_%H%M%S)"
    echo -e "  💾 기존 .env 백업 완료"
fi

cat << EOF > .env
# Watson AI Agent Generated Environment Configuration
PORT=$INPUT_PORT
ENV=production
DATABASE_URL=sqlite:///./app.db
TIMEZONE=$INPUT_TZ

# LLM Configuration
GEMINI_API_KEY=$INPUT_GEMINI_KEY
LLM_API_KEY=$INPUT_GEMINI_KEY
LLM_MODEL=gemini-1.5-flash

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=$INPUT_TG_TOKEN
TELEGRAM_ALLOWED_CHAT_IDS=$INPUT_TG_CHAT_ID

# GTD Storage Configuration
GTD_PATH=$INPUT_GTD_PATH
REPO_PATH=.
GIT_REMOTE_NAME=origin
GIT_BRANCH=main

# Web Authentication
WEB_AUTH_ENABLED=$INPUT_WEB_AUTH
WEB_AUTH_USERNAME=$INPUT_WEB_USER
WEB_AUTH_PASSWORD=$INPUT_WEB_PW
CLOUDFLARE_TUNNEL_TOKEN=
EOF
echo -e "  ✅ .env 파일 저장 완료"

# 3. Create config files
mkdir -p config
cat << EOF > config/gtd_config.json
{
  "gtd_path": "$INPUT_GTD_PATH"
}
EOF

if [ ! -f "config/commute_config.json" ]; then
    cat << EOF > config/commute_config.json
{
  "location_name": "$INPUT_LOCATION",
  "bus_stop_name": "탑승 정류소",
  "bus_stop_id": "",
  "bus_route_no": "",
  "dispatch_time": "07:30",
  "weekdays_only": true
}
EOF
fi

if [ ! -f "config/telegram_commands.json" ] && [ -f "config/telegram_commands.json.example" ]; then
    cp config/telegram_commands.json.example config/telegram_commands.json
    echo -e "  ✅ config/telegram_commands.json 20종 명령어 기본값 생성"
fi

# Step 5: Python Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo -e "\n${BOLD}🐍 Python 가상환경(venv) 생성 및 패키지 설치 중...${RESET}"
    python3 -m venv venv
    venv/bin/pip install --upgrade pip -q
    venv/bin/pip install -r requirements.txt -q
    echo -e "  ✅ 가상환경 및 패키지 설치 완료"
else
    echo -e "  ✅ 기존 venv 가상환경 확인됨"
fi

# Step 6: Systemd Service Auto-Generation
SYSTEMD_TARGET="/etc/systemd/system/watson.service"
TEMP_SERVICE="/tmp/watson.service"

sed -e "s|/home/ubuntu/watson/venv/bin/uvicorn|$PROJECT_ROOT/venv/bin/uvicorn|g" \
    -e "s|/home/ubuntu/watson|$PROJECT_ROOT|g" \
    -e "s|User=ubuntu|User=$USER|g" \
    -e "s|--port 8000|--port $INPUT_PORT|g" \
    systemd/watson.service > "$TEMP_SERVICE"

echo -e "\n${BOLD}🚀 서비스 가동 방식 안내${RESET}"
echo "------------------------------------------------------------------"
echo -e "1) ${GREEN}systemd 백그라운드 서비스 등록 (추천 ⭐️):${RESET}"
echo "   sudo cp $TEMP_SERVICE $SYSTEMD_TARGET"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable --now watson.service"
echo ""
echo -e "2) ${BLUE}Docker Compose 컨테이너 가동:${RESET}"
echo "   docker compose up -d --build"
echo ""
echo -e "3) ${YELLOW}로컬 포그라운드 직접 실행:${RESET}"
echo "   source venv/bin/activate && python app.py"
echo "------------------------------------------------------------------"

echo -e "\n${GREEN}🎉 Watson 1-Click 셀프호스팅 설정이 성공적으로 완료되었습니다!${RESET}"
echo -e "• 웹 대시보드 주소: ${CYAN}http://localhost:$INPUT_PORT${RESET}"
echo -e "• 시스템 설정 진단: ${CYAN}http://localhost:$INPUT_PORT/api/system/setup-status${RESET}"
echo -e "• 상세 매뉴얼 문서: ${CYAN}docs/quickstart_guide.md${RESET}\n"
