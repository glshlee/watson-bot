# ADR-056: 비동기 서비스 제어 스크립트 및 데몬 구동 표준화 (Asynchronous Service Control Script & Daemonized Execution Standard)

## 1. 개요 (Context)
* **배경**:
  * Watson 애플리케이션은 24/7 가동되는 GitHub LifeLog AI 비서이자 FastAPI 백엔드 서비스이다.
  * 기존 문서(`AGENTS.md`, `README.md`, `setup_wizard.sh`)에는 서버 구동 방식으로 `python app.py` 또는 `uvicorn app.main:app` 등 포그라운드 실행 방식이 안내되어 있었다.
  * 이로 인해 AI 에이전트(개발 보조 에이전트)나 사용자가 터미널 대화 세션에서 포그라운드로 서버를 직접 구동하다가 세션이 블로킹(무한 대기)되거나, 백그라운드에 이미 활성화된 systemd 서비스(`watson.service`)와 포트(8000) 충돌을 일으키거나 고아 프로세스를 남기는 문제가 발생했다.
* **사용자 요구사항**:
  * 포그라운드 직접 실행을 엄격히 금지하고, 비동기 백그라운드(systemd 또는 백그라운드 데몬)로만 제어·실행할 수 있는 전용 서비스 스크립트 체계를 구축할 것.

---

## 2. 의사결정 (Decision)

### 2.1 통합 비동기 서비스 제어 스크립트 (`scripts/service.sh`) 구축
Watson 서비스의 전체 생명주기를 비동기 논블로킹(Non-blocking) 방식으로 제어하는 표준 스크립트를 구현한다:
1. **`start`**:
   - 이미 가동 중인지 확인 후 중복 실행 방지.
   - systemd(`watson.service`)가 등록되어 있으면 `sudo systemctl start watson.service`를 실행하고, 없거나 `--daemon` 모드인 경우 `nohup uvicorn ... > watson.log 2>&1 &` 및 `.watson.pid` 파일 생성.
   - 최대 30초 동안 `http://127.0.0.1:PORT/api/health` 헬스체크를 비동기 폴링하여 정상 가동(`"status":"ok"`)을 확인한 즉시 PID 및 상태를 출력하고 반환 (포그라운드 블로킹 없음).
2. **`stop`**:
   - systemd 서비스 중지 및 `.watson.pid` 프로세스에 SIGTERM/SIGKILL 안전 전송.
   - 포트 점유 잔여 프로세스까지 안전하게 정리.
3. **`restart`**:
   - `stop` 실행 후 포트 해제를 대기하고, `start`를 비동기로 호출하여 헬스체크 검증 완료 후 즉시 종료.
4. **`status`**:
   - systemd 활성 여부, 데몬 PID, 점유 포트, `/api/health` 응답 본문, Cloudflare Tunnel URL(`tunnel_url.txt`), Tunnel 서비스 상태, Git 브랜치/커밋 정보를 한눈에 브리핑.
5. **`logs [N]`**:
   - systemd 저널(`SYSTEMD_PAGER=cat journalctl -u watson.service -n N --no-pager`) 또는 로그 파일(`watson.log`)의 최근 N개 라인을 비동기 즉시 출력.
6. **`install-systemd`**:
   - 현재 작업 디렉토리 경로, 사용자명, 포트를 동적 바인딩하여 `/etc/systemd/system/watson.service` 등록 및 `daemon-reload`.

### 2.2 원터치 단축 스크립트 제공
터미널 및 스크립트에서 편리하게 호출할 수 있도록 단축 진입점을 제공:
* `scripts/start.sh` ➔ `./scripts/service.sh start`
* `scripts/stop.sh` ➔ `./scripts/service.sh stop`
* `scripts/restart.sh` ➔ `./scripts/service.sh restart`
* `scripts/status.sh` ➔ `./scripts/service.sh status`

### 2.3 포그라운드 직접 실행 방지 가드레일 (`app.py`)
* AI 에이전트나 사용자가 관성적으로 `python app.py`를 실행하더라도 터미널이 블로킹되지 않도록 루트 디렉토리에 방어 가드레일 스크립트 `app.py`를 배치.
* `python app.py` 호출 시 가드레일 배너를 출력하고 즉시 `./scripts/service.sh start`로 위임하여 비동기 백그라운드 구동을 수행.

### 2.4 하네스 마스터 가이드 (`AGENTS.md`) 및 문서 동기화
* `AGENTS.md`의 `Essential Commands` 및 `Hard Constraints`를 수정하여 에이전트의 포그라운드 직접 실행(`python app.py`, foreground `uvicorn`)을 원천 금지하고, 반드시 `./scripts/service.sh` 또는 단축 스크립트를 통한 비동기 제어만을 허용.

---

## 3. 구현 세부사항 (Implementation)

| 파일 | 역할 및 변경 내용 |
| :--- | :--- |
| `scripts/service.sh` | 비동기 서비스 제어기 (`start`, `stop`, `restart`, `status`, `logs`, `install-systemd`) |
| `scripts/start.sh` | 원터치 비동기 시작 단축 스크립트 |
| `scripts/stop.sh` | 원터치 서비스 정지 단축 스크립트 |
| `scripts/restart.sh` | 원터치 비동기 재시작 단축 스크립트 |
| `scripts/status.sh` | 원터치 상태 점검 단축 스크립트 |
| `app.py` | 직접 포그라운드 실행 방지 및 비동기 서비스 자동 위임 가드레일 |
| `systemd/watson.service` | 작업 디렉토리 및 가상환경 경로 표준화 |
| `scripts/setup_wizard.sh` | 로컬 실행 안내를 `./scripts/start.sh` 비동기 방식으로 개편 |
| `AGENTS.md` | 비동기 서비스 제어 및 포그라운드 직접 실행 금지 규칙 명시 |

---

## 4. 파급 효과 (Consequences)
* **긍정적 효과**:
  * **에이전트 세션 보호**: 에이전트가 서버를 띄우다 세션이 멈추거나 타임아웃되는 치명적인 개발 장애 원천 해소.
  * **일관된 24/7 데몬 운영**: 개발자/운영자 누구나 `./scripts/service.sh {start|stop|restart|status}` 명령어로 손쉽게 서비스와 헬스 상태를 비동기로 제어 가능.
  * **프로세스 충돌 방지**: 중복 실행, 포트 경합, 고아 프로세스 발생 방지.
* **유의 사항**:
  * systemd 등록 환경에서는 `sudo systemctl` 권한이 활용되며, 권한이 없거나 컨테이너 환경에서는 자동으로 `nohup` 데몬 모드로 안전하게 폴백된다.
