#!/usr/bin/env bash
# ==============================================================================
# Watson 24/7 AI Agent Service Controller (scripts/service.sh)
# ADR-056: Asynchronous Service Control Script & Daemonized Execution Standard
# ==============================================================================
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# 기본 포트 추출 (.env 지원)
PORT="8000"
if [ -f .env ]; then
    ENV_PORT=$(grep -E '^[[:space:]]*PORT=' .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]' || true)
    if [ -n "$ENV_PORT" ]; then
        PORT="$ENV_PORT"
    fi
fi

PID_FILE="$DIR/.watson.pid"
LOG_FILE="$DIR/watson.log"
TUNNEL_URL_FILE="$DIR/tunnel_url.txt"
SYSTEMD_SERVICE="watson.service"
TUNNEL_SERVICE="watson-tunnel.service"
VENV_PYTHON="$DIR/venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$(which python3 || echo "python3")"
fi

# 콘솔 색상
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

has_systemd() {
    if command -v systemctl >/dev/null 2>&1 && [ -f "/etc/systemd/system/$SYSTEMD_SERVICE" ]; then
        return 0
    fi
    return 1
}

is_systemd_active() {
    if has_systemd; then
        if sudo -n systemctl is-active --quiet "$SYSTEMD_SERVICE" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_daemon_active() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    # 포트 8000 리스닝 검사
    local port_pid
    port_pid=$(lsof -ti :"$PORT" 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        return 0
    fi
    return 1
}

is_running() {
    if is_systemd_active || is_daemon_active; then
        return 0
    fi
    return 1
}

wait_for_health() {
    local max_retries="${1:-60}" # 기본 최대 30초 (0.5s x 60)
    local interval="0.5"
    local count=0
    echo -ne "  ⏳ 비동기 서비스 헬스체크 대기 중 (http://127.0.0.1:$PORT/api/health)..."
    while [ "$count" -lt "$max_retries" ]; do
        local res
        res=$(curl -s -m 2 "http://127.0.0.1:$PORT/api/health" 2>/dev/null || true)
        if echo "$res" | grep -q '"status":"ok"'; then
            echo -e " ${GREEN}정상 가동 확인! (OK)${RESET}"
            return 0
        fi
        sleep "$interval"
        count=$((count + 1))
        echo -ne "."
    done
    echo -e " ${RED}타임아웃 (헬스체크 실패)${RESET}"
    return 1
}

start_service() {
    local mode="systemd"
    if [ "$1" == "--daemon" ] || ! has_systemd; then
        mode="daemon"
    fi

    echo -e "${BOLD}🚀 Watson 24/7 AI Agent 비동기 서비스 시작 (${mode})${RESET}"

    if is_running; then
        echo -e "${YELLOW}⚠️ Watson 서비스가 이미 가동 중입니다.${RESET}"
        status_service
        return 0
    fi

    if [ "$mode" == "systemd" ]; then
        echo -e "  ⚙️ systemd 서비스($SYSTEMD_SERVICE) 시작 요청..."
        if sudo -n systemctl start "$SYSTEMD_SERVICE"; then
            if [ -f "/etc/systemd/system/$TUNNEL_SERVICE" ]; then
                sudo -n systemctl start "$TUNNEL_SERVICE" 2>/dev/null || true
            fi
            if wait_for_health 30; then
                echo -e "${GREEN}✅ Watson systemd 서비스가 백그라운드에서 성공적으로 시작되었습니다.${RESET}"
                status_service
                return 0
            else
                echo -e "${RED}❌ Watson 서비스 시작 후 헬스체크 응답이 없습니다. 최근 로그 확인:${RESET}"
                sudo -n journalctl -u "$SYSTEMD_SERVICE" -n 20 --no-pager || true
                return 1
            fi
        else
            echo -e "${YELLOW}⚠️ systemd 시작 실패. 독립 데몬 모드로 폴백합니다...${RESET}"
            mode="daemon"
        fi
    fi

    if [ "$mode" == "daemon" ]; then
        echo -e "  ⚙️ 백그라운드 데몬(nohup) 비동기 실행..."
        mkdir -p "$(dirname "$LOG_FILE")"
        nohup "$VENV_PYTHON" -m uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "$PORT" \
            --timeout-keep-alive 75 \
            --limit-concurrency 100 >> "$LOG_FILE" 2>&1 &
        local new_pid=$!
        echo "$new_pid" > "$PID_FILE"
        echo -e "  📌 백그라운드 PID: ${CYAN}$new_pid${RESET}"

        if wait_for_health 30; then
            echo -e "${GREEN}✅ Watson 데몬 서비스가 백그라운드에서 성공적으로 시작되었습니다.${RESET}"
            status_service
            return 0
        else
            echo -e "${RED}❌ Watson 데몬 시작 후 헬스체크 실패. 로그 확인 ($LOG_FILE):${RESET}"
            tail -n 20 "$LOG_FILE" || true
            return 1
        fi
    fi
}

stop_service() {
    echo -e "${BOLD}🛑 Watson 24/7 AI Agent 서비스 중지${RESET}"
    local stopped=0

    # 1. systemd 중지
    if has_systemd && is_systemd_active; then
        echo -e "  ⚙️ systemd 서비스($SYSTEMD_SERVICE) 중지 중..."
        sudo -n systemctl stop "$SYSTEMD_SERVICE" 2>/dev/null || true
        if [ -f "/etc/systemd/system/$TUNNEL_SERVICE" ]; then
            sudo -n systemctl stop "$TUNNEL_SERVICE" 2>/dev/null || true
        fi
        stopped=1
    fi

    # 2. 데몬 PID 파일 프로세스 종료
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "  ⚙️ 백그라운드 데몬 PID($pid) 종료 중..."
            kill -TERM "$pid" 2>/dev/null || true
            for _ in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then break; fi
                sleep 0.5
            done
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
        stopped=1
    fi

    # 3. 포트 잔여 프로세스 점검 및 정리
    local port_pids
    port_pids=$(lsof -ti :"$PORT" 2>/dev/null || true)
    if [ -n "$port_pids" ]; then
        echo -e "  🧹 포트 $PORT 점유 프로세스 정리 ($port_pids)..."
        kill -TERM $port_pids 2>/dev/null || true
        sleep 1
        kill -9 $port_pids 2>/dev/null || true
        stopped=1
    fi

    if [ "$stopped" -eq 1 ]; then
        echo -e "${GREEN}✅ Watson 서비스가 안전하게 중지되었습니다.${RESET}"
    else
        echo -e "${YELLOW}ℹ️ 실행 중인 Watson 서비스가 없습니다.${RESET}"
    fi
}

restart_service() {
    echo -e "${BOLD}🔄 Watson 24/7 AI Agent 서비스 비동기 재시작${RESET}"
    stop_service
    sleep 1
    start_service "$@"
}

status_service() {
    echo -e "------------------------------------------------------------------"
    echo -e "${BOLD}📊 Watson 서비스 상태 점검 (Status)${RESET}"
    echo -e "------------------------------------------------------------------"

    local running=0
    local mode="None"
    local pid=""

    if is_systemd_active; then
        running=1
        mode="systemd ($SYSTEMD_SERVICE)"
        pid=$(sudo -n systemctl show -p MainPID --value "$SYSTEMD_SERVICE" 2>/dev/null || echo "")
    elif is_daemon_active; then
        running=1
        mode="daemon (PID file / standalone)"
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        else
            pid=$(lsof -ti :"$PORT" 2>/dev/null | head -n 1 || echo "")
        fi
    fi

    if [ "$running" -eq 1 ]; then
        echo -e "• 서비스 상태 : ${GREEN}🟢 ACTIVE (실행 중)${RESET}"
        echo -e "• 실행 모드   : ${CYAN}$mode${RESET}"
        echo -e "• 프로세스 PID: ${BOLD}$pid${RESET}"
        echo -e "• 서비스 포트 : ${CYAN}http://127.0.0.1:$PORT${RESET}"

        # 헬스체크 정보
        local health_json
        health_json=$(curl -s -m 2 "http://127.0.0.1:$PORT/api/health" 2>/dev/null || true)
        if [ -n "$health_json" ]; then
            echo -e "• 헬스체크    : ${GREEN}OK${RESET} $health_json"
        else
            echo -e "• 헬스체크    : ${YELLOW}응답 지연 또는 인증 필요${RESET}"
        fi

        # 터널 상태
        if [ -f "$TUNNEL_URL_FILE" ]; then
            local tunnel_url
            tunnel_url=$(cat "$TUNNEL_URL_FILE" 2>/dev/null || true)
            if [ -n "$tunnel_url" ]; then
                echo -e "• 공용 URL    : ${GREEN}$tunnel_url${RESET}"
            fi
        fi
        if command -v systemctl >/dev/null 2>&1 && [ -f "/etc/systemd/system/$TUNNEL_SERVICE" ]; then
            local tunnel_stat
            tunnel_stat=$(sudo -n systemctl is-active "$TUNNEL_SERVICE" 2>/dev/null || echo "inactive")
            echo -e "• 터널 서비스 : $TUNNEL_SERVICE ($tunnel_stat)"
        fi
    else
        echo -e "• 서비스 상태 : ${RED}🔴 INACTIVE (중지됨)${RESET}"
        echo -e "• 서비스 포트 : http://127.0.0.1:$PORT (미사용)"
    fi

    # Git 저장소 상태
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local commit
    commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo -e "• Git 브랜치  : ${CYAN}$branch${RESET} (${DIM}$commit${RESET})"
    echo -e "------------------------------------------------------------------"

    if [ "$running" -eq 1 ]; then
        return 0
    else
        return 1
    fi
}

logs_service() {
    local lines="${2:-50}"
    if is_systemd_active; then
        echo -e "${BOLD}📄 systemd 최근 로그 ($SYSTEMD_SERVICE, 최근 $lines줄)${RESET}"
        SYSTEMD_PAGER=cat sudo -n journalctl -u "$SYSTEMD_SERVICE" -n "$lines" --no-pager
    elif [ -f "$LOG_FILE" ]; then
        echo -e "${BOLD}📄 데몬 파일 최근 로그 ($LOG_FILE, 최근 $lines줄)${RESET}"
        tail -n "$lines" "$LOG_FILE"
    else
        echo -e "${YELLOW}ℹ️ 로그 파일 또는 활성 systemd 저널이 없습니다.${RESET}"
    fi
}

install_systemd() {
    echo -e "${BOLD}⚙️ systemd 서비스 등록 및 갱신${RESET}"
    local target="/etc/systemd/system/$SYSTEMD_SERVICE"
    local temp_file="/tmp/$SYSTEMD_SERVICE"

    sed -e "s|/home/ubuntu/watson/venv/bin/uvicorn|$DIR/venv/bin/uvicorn|g" \
        -e "s|/home/ubuntu/watson|$DIR|g" \
        -e "s|User=ubuntu|User=$USER|g" \
        -e "s|--port 8000|--port $PORT|g" \
        "$DIR/systemd/watson.service" > "$temp_file"

    echo -e "  📋 $temp_file -> $target 복사..."
    sudo -n cp "$temp_file" "$target"
    sudo -n systemctl daemon-reload
    sudo -n systemctl enable "$SYSTEMD_SERVICE"
    echo -e "${GREEN}✅ $SYSTEMD_SERVICE 등록 및 데몬 리로드 완료!${RESET}"
    echo -e "  실행 명령: ${CYAN}./scripts/service.sh start${RESET}"
}

print_help() {
    echo -e "${BOLD}Watson 24/7 AI Agent 비동기 서비스 제어 스크립트${RESET}"
    echo -e "사용법: $0 {start|stop|restart|status|logs|install-systemd}"
    echo ""
    echo "명령어 목록:"
    echo "  start           : Watson 서비스를 비동기(Background)로 가동 (systemd 또는 daemon)"
    echo "  stop            : 가동 중인 Watson 서비스를 안전하게 중지"
    echo "  restart         : Watson 서비스를 비동기로 재시작"
    echo "  status          : 서비스 실행 여부, PID, 헬스체크 및 터널 URL 점검"
    echo "  logs [N]        : 최근 로그 N줄 조회 (기본값: 50줄, 포그라운드 블로킹 없음)"
    echo "  install-systemd : systemd에 watson.service 등록/갱신"
    echo ""
    echo "단축 스크립트:"
    echo "  ./scripts/start.sh   (= ./scripts/service.sh start)"
    echo "  ./scripts/stop.sh    (= ./scripts/service.sh stop)"
    echo "  ./scripts/restart.sh (= ./scripts/service.sh restart)"
    echo "  ./scripts/status.sh  (= ./scripts/service.sh status)"
}

case "${1:-}" in
    start)
        start_service "${2:-}"
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service "${2:-}"
        ;;
    status)
        status_service
        ;;
    logs)
        logs_service "$@"
        ;;
    install-systemd)
        install_systemd
        ;;
    -h|--help|help)
        print_help
        ;;
    *)
        print_help
        exit 1
        ;;
esac
