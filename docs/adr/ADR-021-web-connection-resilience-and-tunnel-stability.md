# ADR-021: 웹 연결 복원력(Connection Resilience), Cloudflare HTTP/2 터널 안정화 및 화면 복귀 자동 동기화

## 1. Context (배경 및 문제점)
사용자가 모바일 또는 웹 브라우저에서 Watson 비서(`/watson`)나 DevBot 콘솔(`/dev`)을 사용할 때 다음과 같은 커넥션 끊김 및 통신 불안정 문제가 보고되었다:
1. **Cloudflare Quick Tunnel의 QUIC UDP 유휴 타임아웃 드롭**:
   - `cloudflared`의 기본 통신 프로토콜인 QUIC(UDP 7844)은 클라우드 가상머신(NAT 게이트웨이) 및 모바일 이동통신망에서 수십 초의 무입력 상태 시 방화벽 NAT 매핑이 만료된다.
   - 이로 인해 터널 로그에 `failed to accept QUIC stream: timeout: no recent network activity` 오류가 지속 발생하며 터널 세션이 재연결되고, 이 과정에서 클라이언트의 인바운드 요청이 `Incoming request ended abruptly: context canceled`로 끊어지는 현상이 발생했다.
2. **Uvicorn Reverse Proxy Keep-Alive 불일치**:
   - Uvicorn의 기본 `timeout_keep_alive`가 5초로 매우 짧아, Cloudflare Tunnel과의 로컬 프록시 연결 풀링 시 소켓 재사용 타이밍 경합(TCP RST)으로 인한 502/504 Bad Gateway가 유발되었다.
3. **스마트폰 백그라운드/화면 꺼짐 시 프론트엔드 통신 단절 및 응답 유실**:
   - 모바일 Safari/Chrome에서 사용자가 질문을 보낸 뒤 화면이 꺼지거나 다른 앱으로 전환하면 백그라운드 fetch가 일시 중단되거나 네트워크 소켓이 끊어졌다.
   - 서버는 정상적으로 답변 생성을 마치고 SQLite에 저장했으나, 사용자가 화면을 다시 켰을 때 프론트엔드에는 `⚠️ 서버 연결 오류가 발생했습니다`라는 에러만 노출되고 이미 완료된 AI 응답이 복원되지 않았다.
4. **실시간 연결 상태 가시성 및 지능형 재시도 부재**:
   - 일시적인 네트워크 순단 시에도 즉각적인 에러 메시지를 띄우고 재시도나 복구 루프가 없었으며, 사용자는 현재 서버/터널이 연결 상태인지 오프라인 상태인지 직관적으로 확인할 수 없었다.

## 2. Decision (결정 사항)

### 2.1 네트워크 계층: Cloudflare HTTP/2 프로토콜 강제 및 Uvicorn Keep-Alive 최적화
- **Cloudflare Tunnel (`scripts/run_tunnel.sh`)**:
  - `cloudflared tunnel` 실행 시 `--protocol http2` 및 `--retries 10`을 명시하여 UDP 기반 QUIC 대신 신뢰성 높은 TCP TLS HTTP/2 전송을 강제한다.
  - 이를 통해 클라우드 방화벽/NAT 환경에서의 UDP 비활성 포트 드롭을 원천 차단하고 영구적인 TCP Keep-alive 프로브를 보장한다.
- **Uvicorn Keep-Alive 조정 (`watson.service`)**:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75 --limit-concurrency 100`으로 튜닝하여 Cloudflare 에지 프록시 타임아웃(60초)보다 긴 75초 Keep-alive 소켓을 유지, 프록시-오리진 간 소켓 닫힘 경합을 완전히 제거한다.
- **SQLite Concurrency 락 방지 (`app/db/database.py`)**:
  - `connect_args={"check_same_thread": False, "timeout": 30.0}`으로 설정하여 웹 요청과 텔레그램 폴링 간 동시성 충돌 시 락 에러를 차단한다.

### 2.2 백엔드 계층: 초경량 헬스체크 & 하트비트 엔드포인트 (`app/main.py`)
- `GET /api/health` 및 `GET /healthz` 엔드포인트를 라우팅 최상단에 제공한다.
- 무거운 LLM 추론이나 Git/DB 오버헤드 없이 `< 1ms` 내에 `{"status": "ok", "timestamp": "...", "service": "watson", "version": "1.0.0"}`을 반환하여 터널 헬스체크 및 브라우저 하트비트 핑에 대응한다.

### 2.3 프론트엔드 계층: 탄력적 재시도 (`fetchWithRetry`) & 화면 복귀 자동 동기화 (`main.js`, `dev.js`)
- **지능형 재시도 엔진 (`fetchWithRetry`)**:
  - 네트워크 단절 또는 502/503/504 에러 수신 시 지수 백오프(1.2초, 2.4초)로 최대 2회 자동 재시도하며, 65초 타임아웃 신호를 주입한다.
- **화면 복귀/잠금 해제 자동 복구 (`visibilitychange`, `online`/`offline`)**:
  - 모바일 브라우저 화면이 켜지거나 탭으로 복귀(`document.addEventListener("visibilitychange")`)할 때 즉시 헬스체크 및 세션 히스토리(`/api/sessions/{id}/history`) 동기화를 자동 수행한다.
  - 요청 중 연결이 끊겼더라도 서버가 이미 생성한 최신 응답을 감지하여 채팅창에 즉시 렌더링하고 실패 에러를 자동 정화한다.
- **실시간 연결 상태 배너 & 하트비트 핑**:
  - 매 25초 주기로 `/api/health` 하트비트를 전송하여 `.status-indicator` 및 `.system-status`를 3단계(`online`, `warning`, `offline`)로 실시간 전환한다.
  - 연결 이상 발생 시 최상단에 부드러운 경고 배너(`#connection-banner`)와 `[🔄 재시도]` 원클릭 수동 복구 버튼을 제공한다.

## 3. Consequences (영향 및 효과)

### 장점 (Positive)
- **모바일 환경 접속 안정성 획기적 향상**: 지하철, 엘리베이터 등 음영지역 통과나 Wi-Fi/LTE 망 전환 시에도 자동 재시도 및 세션 히스토리 역추적으로 사용자의 발화나 AI의 응답이 유실되지 않음.
- **터널 QUIC 유휴 드롭 종결**: TCP HTTP/2 고정으로 유휴 상태에서도 터널 세션이 끊김 없이 24/7 영구 유지됨.
- **직관적 네트워크 상태 인지**: 배너와 펄스 인디케이터로 연결 이상 여부를 사용자가 즉시 파악하고 원클릭 복구 가능.

### 관리 사항 (Maintenance)
- `scripts/smoke_test.sh`의 스모크 테스트 루프에 `0-1. Testing Lightweight Health Check & Heartbeat` 검증 단계를 영구 포함하여 CI/배포 시 회귀를 방지함.
