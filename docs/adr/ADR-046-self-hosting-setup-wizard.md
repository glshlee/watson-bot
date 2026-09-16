# ADR-046: 1-Click 셀프호스팅 배포 패키지 & 대화형 셋업 위저드 (Self-Hosting Setup Wizard & Packaging)

## 1. 배경 (Context)
Watson은 개인용 GitHub 라이프로그 및 GTD 관리 AI 비서로서, 고도화된 브리핑, 기상/출근길 연동, 비전 멀티모달 분석, 연간 잔디 및 인플레이스 에디터 등 풍부한 기능을 갖추었습니다.
하지만 본인 외에 지인, 동료, 또는 일반 사용자가 Watson을 자신의 개인 서버(오라클 클라우드 평생 무료 VM, AWS EC2, 라즈베리 파이, 로컬 홈 서버)에 직접 띄워 사용하려면, 수많은 환경변수(`.env`), 텔레그램 봇 토큰 및 Chat ID, GTD 디렉토리 초기화, Python 가상환경 구축, systemd 서비스 등록 등을 수작업으로 진행해야 하는 진입 장벽이 존재했습니다.
사용자의 민감한 일기와 일정 데이터가 중앙 서버를 거치지 않고 **오직 사용자의 개인 기기와 개인 GitHub 저장소에만 보존**되는 강력한 프라이버시 원칙을 지키면서도, 초보자도 10분 만에 배포할 수 있는 **1-Click 대화형 셋업 위저드**와 **올인원 컨테이너 패키징**이 요구되었습니다.

## 2. 결정 사항 (Decision)

### 1) 대화형 셋업 위저드 스크립트 (`./scripts/setup_wizard.sh`)
* **친절한 단계별 대화형 질문 및 스마트 기본값**:
  1. 필수 도구(Python 3.10+, git, curl) 자동 확인.
  2. 서버 포트(기본 `8000`), 타임존(기본 `Asia/Seoul`).
  3. 텔레그램 봇 토큰(`TELEGRAM_BOT_TOKEN`) 및 관리자 Chat ID(`TELEGRAM_ALLOWED_CHAT_IDS`).
  4. 무료 Gemini API Key (`GEMINI_API_KEY`).
  5. GTD 저장소 경로(`GTD_PATH`, 기본 `$HOME/lifelog`): 미존재 시 디렉토리 생성 및 `git init`, 기본 수집함(`inbox.md`) 및 다음행동(`next_actions.md`) 자동 생성.
  6. 거주지 동네명(`config/commute_config.json` 생성).
  7. 웹 콘솔 보안 인증(HTTP Basic Auth) 활성화 및 계정 생성.
* **무인 자동화 및 모의 테스트 옵션**:
  * `-y`, `--non-interactive`: 기본값 및 환경변수로 입력 대기 없이 즉시 세팅 (CI/CD용).
  * `-d`, `--dry-run`: 파일 변경 없이 입력값 검증 및 모의 테스트.
  * `-c`, `--check`: 현재 `.env`, `venv`, `config` 디렉토리 설정 상태 점검.
* **동적 systemd 서비스 자동 적응**:
  * 호스트 환경의 현재 경로(`$PWD`)와 사용자 계정(`$USER`), 포트를 감지하여 `/tmp/watson.service`를 자동 합성하고 복사 명령어 제시.

### 2) 시스템 배포 진단 서비스 & REST API (`SetupService`, `web_router.py`)
* `SetupService` (`app/services/setup_service.py`):
  * 텔레그램 봇, 관리자 ID, LLM 엔진, GTD 저장소 및 Git 연동 여부, 웹 보안, 출근길 설정, 런타임 환경 등 8개 영역 진단.
  * 비밀값 마스킹(`_mask_secret`), 준비율 백분율(`readiness_percentage`), 즉시 조치 항목 및 추천 가이드 생성.
* `GET /api/system/setup-status`:
  * 진단 데이터 JSON 및 마크다운 리포트 반환.
* DevBot 콘솔 연동:
  * `/setup`, `/설정점검` 명령어 및 원터치 칩(`[⚙️ 배포점검]`)을 통해 터미널 없이도 현재 시스템 준비 상태를 언제든 확인 가능.

### 3) 올인원 Docker Compose 및 환경 템플릿 최적화
* `Dockerfile`: `python:3.12-slim`, `safe.directory '*'` 설정, 초경량 헬스체크(`GET /api/health`) 탑재.
* `docker-compose.yml`: `./config`, SQLite DB, GTD 볼륨 마운트 및 자동 재시작(`restart: always`) 완비.
* `.env.example`: 초보자 친화적 상세 주석 및 발급 링크 명시.

### 4) 초보자용 10분 완성 퀵스타트 가이드 (`docs/quickstart_guide.md`)
* 사전 준비물 3종(BotFather 토큰, userinfobot Chat ID, Gemini 무료 키) 발급 방법, 셋업 위저드 실행, systemd/Docker 가동, FAQ 트러블슈팅을 완벽히 정리.

## 3. 결과 및 영향 (Consequences)
* **긍정적 효과**:
  * 지인이나 타 사용자도 `./scripts/setup_wizard.sh` 1회 실행만으로 10분 만에 자신만의 Watson 24/7 비서를 완벽히 구축할 수 있음.
  * 개인정보(일기, 일정)가 제3자에게 노출되지 않는 셀프호스팅의 보안상 이점과 극도로 간편한 사용자 경험(UX)을 동시 달성.
  * `/setup` 및 `GET /api/system/setup-status`를 통해 설치 후 운영 중에도 시스템 건전성을 실시간 진단 가능.
* **부정적 효과 및 완화책**:
  * 사용자의 서버 환경(포트 충돌, 방화벽)에 따라 접근 문제가 발생할 수 있으나, 퀵스타트 가이드의 FAQ 및 Cloudflare Tunnel 연동 가이드를 통해 완화함.
