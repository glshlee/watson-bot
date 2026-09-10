# 🤖 Watson (왓슨) - 24/7 GitHub LifeLog & GTD AI Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0.svg)](https://core.telegram.org/bots)
[![GitHub Actions & Git](https://img.shields.io/badge/Git-Automation-F05032.svg)](https://git-scm.com/)
[![AI Engine](https://img.shields.io/badge/AI-Antigravity%20%2F%20Gemini-8E44AD.svg)](https://github.com/glshlee/watson-bot)

> **"대화는 가볍게, 기록은 단단하게."**  
> 왓슨(Watson)은 24시간 상시 가동되며 모바일(텔레그램) 및 웹 대시보드를 통해 사용자의 일상과 업무를 기록하고, 외부 개인 GTD/라이프로그 저장소에 표준화된 마크다운으로 자동 커밋해 주는 **지능형 LifeLog & GTD AI 비서(Butler)**입니다.

---

## 📑 목차 (Table of Contents)

1. [🌟 핵심 특징 (Key Features)](#-핵심-특징-key-features)
2. [🏗️ 시스템 아키텍처](#️-시스템-아키텍처)
3. [📋 사전 준비 사항](#-사전-준비-사항-prerequisites)
4. [🚀 24/7 배포 및 실행 가이드](#-247-배포-및-실행-가이드)
   - [방법 1: Linux systemd 서비스 상시 구동 (권장)](#방법-1-linux-systemd-서비스-상시-구동-권장)
   - [방법 2: Docker Compose 기반 배포](#방법-2-docker-compose-기반-배포)
   - [방법 3: 로컬 파이썬 가상환경 직접 실행](#방법-3-로컬-파이썬-가상환경-직접-실행)
5. [📱 실전 사용 매뉴얼 (User Manual)](#-실전-사용-매뉴얼-user-manual)
   - [텔레그램 봇 실전 활용](#1-모바일-텔레그램-봇-활용)
   - [웹 대시보드 및 GTD 설정 UI](#2-웹-대시보드-및-gtd-환경설정)
6. [📁 GTD 및 라이프로그 저장 구조](#-gtd-및-라이프로그-저장-구조)
7. [🧪 테스트 및 품질 검증](#-테스트-및-품질-검증)
8. [🛠️ 프로젝트 디렉토리 구조 & 에이전트 하네스](#️-프로젝트-디렉토리-구조--에이전트-하네스)
9. [📄 라이선스](#-라이선스-license)

---

## 🌟 핵심 특징 (Key Features)

- 🧠 **지능형 비서 & 능동 제안 (Smart Butler - ADR-004)**
  - 단순 잡담/질문은 세션 메모리에만 보관하고 Git 저장소를 어지럽히지 않습니다.
  - 운동, 업무, 생각 등 기록할 가치가 있는 일과를 감지하면 비서가 먼저 **"라이프로그에 기록할까요?"**라고 인라인 버튼으로 제안합니다.
- 📋 **GTD 지능형 브리핑 & Antigravity AI 브릿지 (Task Briefing - ADR-008)**
  - *"오늘 해야할 일 정리해줘"*, *"오늘 일정 어때?"* 요청 시 연동된 GTD 저장소의 금일 데일리 로그(`logs/daily/`), 다음 행동(`gtd/next_actions.md`), 수집함(`gtd/inbox.md`)을 실시간 분석하여 맞춤형 일정/할 일 브리핑을 제공합니다.
  - Linux/macOS 환경에서 Antigravity CLI(`agy`) 바이너리를 동적으로 자동 탐색하여 생생한 자연어 맥락을 유지합니다.
- 🔄 **GTD 저장소 원격 동기화 & 온디맨드 최신화 (Repo Sync - ADR-009)**
  - *"gtd 레포 최신화하고 다시 알려줘"*, *"레포 최신화"*, `/sync` 요청 시 원격 GitHub로부터 최신 커밋을 `git pull --rebase --autostash`로 안전하게 동기화한 뒤 브리핑을 제공합니다.
  - 모바일(옵시디언)이나 다른 환경에서 작업한 변경사항도 왓슨이 즉시 인식합니다.
- 🧠 **세션 대화 맥락 참조 기록 & 고탄력 AI (Context-Aware Logging - ADR-010)**
  - 대화 후 *"오늘 로그에 내가 아까 말한 내용도 기록해줘. 내 감정이니까"*, *"방금 이야기 일기에 적어줘"* 요청 시 직전 대화 맥락을 역추적하여 마크다운에 즉시 영구 보존합니다.
  - 프롬프트 경량화와 50초 탄력적 타임아웃으로 맥락 단절(Amnesia) 없는 빠르고 신뢰성 높은 대화를 보장합니다.
- 🚀 **결정론적 Git 푸시 & AGY Headless 무중단 실행 (Repo Push - ADR-011)**
  - *"푸시해줘"*, *"푸시도 해줘"*, *"깃 푸시"*, `/push`, *"푸시가 안됐는데 다시 확인해줘"* 요청 시 LLM의 환각 응답을 원천 차단하고 백엔드 `GitService.push()`를 즉시 실행하여 실시간 상태를 정직하게 보고합니다.
  - 언스테이징된 파일이 있더라도 `autostash` 안전 병합을 적용하여 원격 GitHub 푸시를 누락 없이 완수합니다.
  - 비대화형 CLI 환경에서 `--dangerously-skip-permissions` 플래그를 적용하여 도구 권한 거부로 인한 침묵 및 엉뚱한 감성 폴백 노출을 원천 방지합니다.
- 🛡️ **테스트 샌드박스 격리 & 대화형 지시어 문맥 역추적 (Test Sandbox & Directive - ADR-012)**
  - 스모크 테스트 실행 시 완전히 격리된 임시 Git 저장소 샌드박스를 사용하여 실제 사용자 라이프로그 저장소에 테스트 더미 데이터가 유입되는 것을 원천 차단합니다.
  - 사연 공유 후 *"응 오늘 로그에 기록해줘"*, *"오늘 일기에 적어줘"*, *"응 기록해줘"* 등 구어체 지시어 수신 시 지시어 텍스트가 본문으로 오인되는 것을 방지하고, 이전 대화 사연을 역추적하여 마크다운에 정확히 보존합니다.
- ⏱️ **한국 표준시(KST) 타임존 로컬라이제이션 (Timezone Localization - ADR-013)**
  - 서버의 기본 시스템 시간대(UTC)와 무관하게 모든 일일 로그 파일 경로(`YYYY-MM-DD.md`), 타임스탬프(`[HH:MM]`), 커밋 메시지 일자, 텔레그램 동기화 시간을 한국 표준시(`Asia/Seoul`, UTC+9)로 정규화합니다.
  - 자정 넘은 새벽 시간대(00:00~09:00 KST) 기록 시 UTC의 전날 날짜 파일로 분기되는 결함을 완전히 해결하여 항상 정확한 한국 날짜 파일에 기록합니다.
- 🧭 **복합 의도 감지 & GTD 태스크 정제 (Compound Intent & Task Formulation - ADR-014)**
  - *"로그와 gtd에 기록해줘"*, *"일기랑 할일에 적어줘"* 요청 시, 서사적 일기는 데일리 로그(`logs/daily/YYYY-MM-DD.md`)에, 실행 가능한 할 일은 GTD 인박스(`gtd/inbox.md`)에 단일 트랜잭션으로 누락 없이 동시 기록합니다.
  - 문장 끝의 지시어 수식구("로그와 gtd에 기록해줘") 및 불필요한 구두점을 완벽히 절삭하여 깔끔한 일기 본문을 보존합니다.
  - 비정형 사연에서 여행/맛집/업무 등의 핵심 요소를 추출하여 행동 지향적 태스크(`- [ ] 서산 여행 계획 및 맛집 방문 (용현집 어죽, 또간집 게국지) 🚗🍲`)로 합성하고, 인박스의 대주제 섹션(`## 🧘 개인 생활 & 건강`)에 자동 정렬합니다.
- 🔐 **웹 콘솔 보안 인증 & Cloudflare Tunnel 외부 연동 (Web Auth & Tunnel - ADR-015)**
  - 클라우드 방화벽 인바운드 포트(8000 등)를 외부에 열지 않고, **Cloudflare Tunnel (`cloudflared`)**을 통해 어디서나 무료 HTTPS 암호화 접속을 지원합니다.
  - 웹 대시보드(`/`) 및 모든 관리 API에 **HTTP Basic 보안 인증**을 적용하여 브라우저 로그인 창(ID/PW)을 강제하며, 비인가자의 개인 일기 및 GTD 열람/조작을 원천 차단합니다.
  - `watson-tunnel.service` 데몬을 통해 24/7 무중단 백그라운드 구동되며, 전용 도메인 토큰 연동까지 완벽 지원합니다.
- 📱 **모바일 퍼스트 반응형 웹 콘솔 & 터치 UX 최적화 (Mobile Responsive UX - ADR-016)**
  - 스마트폰(<= 768px) 환경에서 사이드바를 **오프캔버스 슬라이드 드로어**로 자동 전환하여 모바일 화면 전체를 채팅창으로 활용합니다.
  - 세션 선택 및 새 세션 시작 시 드로어가 자동으로 닫혀 즉각적인 타이핑 경험을 제공합니다.
  - `100dvh` 동적 뷰포트, iOS Safe Area 및 16px 폰트(사파리 자동 줌 인 방지) 적용으로 스마트폰 브라우저에서도 네이티브 앱 수준의 쾌적한 사용성을 보장합니다.
- 🗂️ **웹 콘솔 세션 관리 고도화 (Advanced Session Management UI - ADR-017)**
  - **실시간 검색 & 채널 필터**: 키워드 입력 즉시 세션 목록이 필터링되며, `전체` / `🌐 웹` / `📱 텔레그램` 탭으로 채널별 세션을 분리 조회합니다.
  - **세션 CRUD 완비**: 세션 이름 변경(모달 UI), 대화 내용 비우기(Clear Messages), 세션 영구 삭제 및 인접 세션 자동 전환 폴백을 지원합니다.
  - **스마트 자동 네이밍**: 첫 대화 입력 시 사용자의 질문/메모 핵심을 추출하여 의미 있는 세션 제목을 자동 생성합니다.
  - **풍부한 세션 카드 & 헤더 동기화**: 세션별 메시지 개수, 상대 시간("방금", "10분 전"), 채널 뱃지를 카드에 표시하고 헤더 영역과 실시간 동기화합니다.
- 🚀 **에이전트 허브 대시보드 포털 & 개발 에이전트 분리 (Agent Hub & Dev Agent - ADR-018)**
  - **에이전트 허브 포털 (`/`)**: 왓슨 비서, DevBot 개발자 및 확장 에이전트의 가동 상태와 메트릭을 한눈에 조망하는 상위 런처 대시보드 제공.
  - **엔지니어 DevBot (`/dev`)**: 소스코드 분석, Git 단축 명령(`/status`, `/diff`, `/log`, `/branch`) 즉시 실행 및 기술 질문 답변을 전담하는 엔지니어링 콘솔.
  - **비서 Watson 분리 (`/watson`)**: 일상 메모 및 GTD 일정 브리핑 전용 콘솔을 독립 제공하며, 상단 `[🏠 에이전트 허브]` 버튼으로 포털과 상호 이동.
  - **세션 데이터 격리 (`agent_type`)**: 비서의 일기/GTD 데이터와 개발자의 소스코드/Git 로그가 서로 간섭하지 않도록 SQLite 세션 테이블 격리.
  - **모바일/데스크톱 세로 스크롤 & 원클릭 카드 터치 UX**: 모바일과 저해상도 환경에서도 카드와 버튼이 시원하게 스크롤되며, 카드 본문 어디를 탭해도 즉시 해당 콘솔로 진입.
- 🛠️ **DevBot 대화형 엔지니어링 툴체인 (Interactive Dev Toolchain - ADR-019)**
  - **대화형 툴체인 실행**: 터미널 없이도 웹 콘솔(`/dev`)에서 `/test [경로]`(단위 테스트 실행), `/lint`(Ruff & Mypy 정적 분석/타입 검사 뱃지 보고), `/commit [메시지]`(Conventional Commits 3종 자동 추천 및 커밋 실행), `/help`를 즉각 실행.
  - **살아있는 엔지니어링 추론**: 최신 `docs/roadmap.md` 마일스톤 및 워크스페이스 상태를 실시간 주입하고 AGY 비대화형 표준 규격(`-p`, `--dangerously-skip-permissions`)으로 Antigravity 수준의 시니어 페어 프로그래밍 대화 지원.
  - **모바일/웹 퀵 툴 칩**: `/dev` 입력창 상단 원터치 버튼으로 복잡한 명령어 타이핑 없이도 테스트와 린트, 커밋 제안을 즉시 트리거.
- 🎯 **결정론적 GTD 태스크 제거 & 원격 투명성 (Deterministic GTD Task Removal & Repo Transparency - ADR-020)**
  - *"tiara_ad는 제거해"*, *"주간보고 아젠다도 제거"* 등 태스크 삭제 요청 시 LLM의 가짜 완료 답변을 차단하고, `inbox.md` 및 `next_actions.md` 파일에서 해당 마크다운 항목(`- [ ] ...`)을 물리적으로 완벽히 탐색·삭제합니다.
  - 삭제 후 즉시 로컬 Git 커밋 및 원격 GitHub 자동 푸시를 집행하여 실제 파일 및 리포지토리 상태를 100% 동기화합니다.
  - *"커밋해"*, `repo_commit` 명령을 결정론적으로 파싱하여 변경사항을 즉시 커밋하고, *"푸시도해야지"*, *"어디다 푸시한거야?"* 등 자연어 어미 변화(`~해야지`, `~하자`) 및 원격 리포지토리 확인 질의에 실제 Git 원격 URL, 브랜치, 최신 커밋 해시를 정직하게 투명 보고합니다.
- 🌐 **웹 연결 복원력 & Cloudflare HTTP/2 터널 안정화 (Web Connection Resilience - ADR-021)**
  - Cloudflare Tunnel 통신 프로토콜을 UDP QUIC에서 TCP TLS 기반 **HTTP/2 (`--protocol http2`, `--retries 10`)**로 고정하여 클라우드 NAT 환경의 유휴 연결 만료 및 터널 끊김을 원천 방지합니다.
  - Uvicorn Keep-Alive를 **75초(`--timeout-keep-alive 75`, 동시성 100)**로 최적화하여 Cloudflare 프록시와의 소켓 닫힘 경합 및 502/504 에러를 제거합니다.
  - 초경량 헬스체크(`GET /api/health`, `< 1ms`) 및 25초 주기 브라우저 하트비트를 통해 실시간 연결 상태를 추적합니다.
  - 웹 콘솔(`main.js`, `dev.js`)에 **지능형 재시도 엔진(`fetchWithRetry`)**을 도입하고, 모바일 화면 꺼짐 후 복귀나 백그라운드 탭 전환 시(`visibilitychange`, `online`) 세션 히스토리를 자동 동기화하여 이미 생성된 AI 응답을 누락 없이 복원합니다.
  - 3단계 연결 펄스 인디케이터(`online`/`warning`/`offline`) 및 최상단 연결 알림 배너와 원클릭 수동 재시도 버튼을 제공합니다.
- 📋 **GTD 및 데일리 로그 파일 즉시 열람 숏컷 & DevBot 대기시간 최적화 (Inspection Shortcuts - ADR-022)**
  - *"오늘자 로그 보여줘"*, `/today`, `/daily` 명령 시 오늘자 마크다운 파일(`logs/daily/YYYY-MM-DD.md`)의 원본, 줄 수, 최종 수정 시각을 0.01초 내에 즉각 열람합니다.
  - *"gtd 파일 보여줘"*, `/gtd`, `/inbox` 명령 시 수집함(`inbox.md`)과 다음 행동(`next_actions.md`) 마크다운을 직접 읽고 미완료 태스크(`- [ ]`) 개수를 자동 집계하여 보고합니다.
  - Watson 콘솔(`.watson-quick-bar`)과 DevBot 콘솔(`.dev-quick-bar`)에 원터치 실행 칩을 제공하여 번거로운 타이핑 없이 원클릭 조회를 지원합니다.
  - DevBot의 대화 맥락을 200자로 축약하고 AGY CLI 타임아웃을 35초로 튜닝하여 50초 대기 지연 및 폴백 문제를 해결했습니다.

- 📁 **GTD 저장소 격리 및 외부 체계 오케스트레이션 (GTD Repo Isolation - ADR-007)**
  - 왓슨 봇 소스코드 저장소와 개인 데이터(GTD/라이프로그) 저장소를 물리적으로 완벽히 분리합니다.
  - 웹 환경설정 UI(`/settings`) 및 API를 통해 작업 GTD 디렉토리를 자유롭게 지정하고, 해당 저장소의 독립 Git 환경으로 안전하게 1기록 1커밋을 집행합니다.
- 📝 **1기록 1커밋 & 마크다운 영속화 (Git-Backed LifeLog)**
  - 사용자가 승인(`[✅ 응, 기록해줘]`)하거나 직접 명령(`/log`)한 확정된 기록만 마크다운 파일에 즉시 영속화하고 Git 커밋/푸시합니다.
- 📱 **모바일 텔레그램 봇 연동 (Zero-Config Mobile Bot)**
  - 복잡한 도메인/SSL 설정 없이 봇 토큰만으로 구동되는 **비동기 롱 폴링(Long Polling)** 지원.
  - 비인가 접근 차단 **화이트리스트 보안** 및 사진+캡션 자동 첨부 다운로드/마크다운 연동.
- 🖥️ **올인원 웹 대시보드 & 실시간 뷰어 (Web Dashboard)**
  - 실시간 웹 채팅, 날짜/채널별 세션 기록 탐색, 오늘 작성된 마크다운 라이프로그 실시간 렌더링 뷰어 및 GTD 디렉토리 설정 패널 제공.

---

## 🏗️ 시스템 아키텍처

```mermaid
flowchart TB
    subgraph Clients["📱 사용자 인터페이스"]
        TG["텔레그램 모바일 앱"]
        WEB["웹 대시보드 & 설정창 (/settings)"]
    end

    subgraph Core["🤖 Watson Agent Engine (FastAPI / 24/7)"]
        Router["Router & Dispatcher"]
        Supervisor["Supervisor (오케스트레이터)"]
        LLM["AI Provider (Antigravity CLI / Gemini API)"]
        SessionDB[("SQLite 세션 DB")]
        GitWorker["Git & Markdown Service"]
    end

    subgraph GTDStorage["📦 격리된 개인 GTD 저장소 (독립 Git Repo)"]
        Inbox["gtd/inbox.md (수집함)"]
        DailyMD["logs/daily/YYYY-MM-DD.md (일일 로그)"]
        NextActions["gtd/next_actions.md (다음 행동)"]
        RemoteGit["개인 원격 GitHub (Remote Push)"]
    end

    TG <-->|Long Polling| Router
    WEB <-->|HTTP / REST (포트 8000)| Router
    Router --> Supervisor
    Supervisor <--> LLM
    Supervisor <--> SessionDB
    Supervisor -->|할 일 브리핑 요청 시| GTDStorage
    Supervisor -->|승인된 기록 반영 시| GitWorker
    GitWorker --> Inbox
    GitWorker --> DailyMD
    GitWorker --> NextActions
    GitWorker -->|독립 Git 커밋/푸시| RemoteGit
```

---

## 📋 사전 준비 사항 (Prerequisites)

1. **AI 엔진 (택일 또는 혼용)**:
   - **Antigravity CLI (`agy`)**: Linux/macOS 로컬 CLI 환경 지원.
   - **Google Gemini API Key (무료)**: [Google AI Studio](https://aistudio.google.com/)에서 발급 가능.
2. **텔레그램 봇 토큰 및 Chat ID (모바일 연동 시)**:
   - 텔레그램 [@BotFather](https://t.me/botfather)에서 봇 생성 후 `HTTP API Token` 복사.
   - 본인의 Chat ID 확인: [@userinfobot](https://t.me/userinfobot)에게 메시지를 전송하여 `Id` 번호 확인.
3. **GitHub SSH 배포 키(Deploy Key)**:
   - 개인 GTD/라이프로그 저장소에 자동 `git push`를 수행하기 위한 SSH 쓰기 권한 키.

---

## 🚀 24/7 배포 및 실행 가이드

### 방법 1: Linux systemd 서비스 상시 구동 (권장)

Linux 서버(Ubuntu/Debian 등)에서 OS 데몬으로 백그라운드 24/7 상시 무중단 구동하는 표준 방식입니다.

```bash
# 1. 저장소 클론 및 가상환경 생성
git clone https://github.com/glshlee/watson-bot.git
cd watson-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
nano .env  # 텔레그램 토큰, 허용 Chat ID, GEMINI_API_KEY 등 입력

# 3. systemd 서비스 등록 및 활성화
sudo cp systemd/watson.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now watson.service

# 4. 서비스 상태 및 실시간 로그 확인
sudo systemctl status watson.service
sudo journalctl -u watson.service -f
```

---

### 방법 2: Docker Compose 기반 배포

Docker를 선호하는 환경에서 컨테이너로 격리하여 실행합니다:

```bash
# 1. 환경변수 설정
cp .env.example .env

# 2. 도커 컨테이너 빌드 및 백그라운드 실행
docker compose up -d --build

# 3. 로그 확인
docker compose logs -f
```

---

### 방법 3: 로컬 파이썬 가상환경 직접 실행

개발 및 기능 테스트용으로 포그라운드에서 직접 실행합니다:

```bash
source venv/bin/activate
python app.py
# 또는
uvicorn app.main:app --reload --port 8000
```

---

## 📱 실전 사용 매뉴얼 (User Manual)

### 1. 모바일 텔레그램 봇 활용

스마트폰 텔레그램 앱에서 왓슨에게 일상 언어로 말을 걸어보세요:

| 상황 / 의도 | 사용자 입력 예시 | 왓슨 AI 반응 및 동작 |
| :--- | :--- | :--- |
| **봇 시작** | `/start` | 왓슨 비서의 환영 인사 및 사용 매뉴얼 안내 |
| **할 일 / 일정 브리핑** | *"오늘 해야할 일 정리해줘"*, *"오늘 일정 어때?"* | 📋 **GTD 저장소 분석** ➔ 금일 스케줄, Next Actions, Inbox 항목을 종합 브리핑 |
| **GTD 레포 최신화 / 동기화** | *"gtd 레포 최신화하고 다시 알려줘"*, *"레포 최신화"*, `/sync` | 🔄 원격 GitHub로부터 최신 커밋을 `pull` 동기화하고 즉시 최신 상태로 재브리핑 |
| **GitHub 원격 푸시** | *"푸시해줘"*, *"푸시도 해줘"*, *"깃 푸시"*, `/push`, *"푸시 확인해줘"* | 🚀 **결정론적 Git Push** ➔ 로컬 커밋 개수 및 원격 반영 결과를 백엔드에서 정직하게 실행 후 보고 |
| **맥락 참조 / 구어체 기록** | *"응 오늘 로그에 기록해줘"*, *"오늘 로그에 내가 아까 말한 내용도 기록해줘"* | 🧠 직전 대화의 긴 사연과 감정을 역추적하여 오늘 마크다운 일기에 즉시 영속화 및 Git 커밋 |
| **복합 기록 (일기+GTD 동시)** | *"서산 여행 가려구. 용현집 가보고싶대. 로그와 gtd에 기록해줘."* | 🧭 **동시 기록 & 태스크 정제** ➔ 일기엔 깔끔한 본문만 남기고, GTD 인박스엔 정제된 실행 태스크(`- [ ] 서산 여행 계획 및 맛집 방문...`) 동시 등록 |
| **일과 보고** | *"오늘 헬스장에서 하체 운동 50분 완료!"* | 💡 **일과 감지** ➔ `[✅ 응, 기록해줘]` / `[❌ 아니야]` 인라인 버튼 표시 |
| **기록 승인** | 버튼 클릭 또는 *"응"*, *"기록해줘"* | 📝 즉시 GTD 마크다운에 반영 ➔ 독립 Git 커밋 & 푸시 완료 메시지 반환 |
| **직접 기록 명령** | `/log 저녁 개발 회의 및 아키텍처 리뷰 완료` | 제안 단계 없이 즉시 마크다운 기록 및 Git 커밋 |
| **일반 대화 / 질의** | *"고마워"*, *"오늘 날씨 좋네"* | 다정하게 대화를 나누며 세션에만 보관 (Git 커밋 X) |
| **사진 첨부** | 운동/식단 사진 + 캡션 전송 | 이미지 자동 다운로드 후 마크다운에 연동 |

---

### 2. 웹 대시보드 및 GTD 환경설정

브라우저(로컬 `http://localhost:8000` 또는 Cloudflare Tunnel HTTPS 외부 주소)에 접속하여 시각적으로 일과를 확인하고 관리합니다:

1. **모바일 퍼스트 실시간 웹 대화 콘솔 (`/`)**:
   - 데스크톱뿐만 아니라 스마트폰(iOS Safari, Android Chrome)에서도 오프캔버스 드로어 메뉴를 통해 세션을 자유롭게 전환하며 왓슨과 실시간 소통.
   - 뷰포트 높이(`100dvh`) 및 16px 폰트(사파리 자동 줌 방지), iOS Safe Area 패딩을 적용하여 모바일 키보드가 올라와도 깨짐 없는 채팅 화면 제공.
2. **라이프로그 실시간 뷰어**: 오늘 날짜의 마크다운 렌더링 화면을 실시간 확인.
3. **GTD 환경설정 모달 / 페이지 (`/settings`)**:
   - 왓슨이 바라볼 **GTD 작업 디렉토리 경로**를 웹에서 동적으로 변경 및 즉시 적용.
   - 연결된 디렉토리의 Git 상태(브랜치, 커밋 여부) 및 디렉토리 구조 검증.

---

## 📁 GTD 및 라이프로그 저장 구조

왓슨은 사용자가 지정한 외부 GTD 디렉토리의 표준 마크다운 파일 구조를 존중하여 기록합니다:

```text
/home/ubuntu/workspace/life_log/ (지정된 GTD 디렉토리)
├── gtd/
│   ├── inbox.md          # 미분류 퀵 캡처 항목
│   └── next_actions.md   # 다음 행동 및 긴급 태스크
└── logs/
    └── daily/
        ├── 2026-09-07.md
        └── 2026-09-08.md # 일일 시간대별 타임라인 및 일과 로그
```

**일일 마크다운 로그 예시 (`logs/daily/YYYY-MM-DD.md`):**

```markdown
# 📅 2026-09-08 Daily Log

## ⏰ Schedule & Routine
- [09:00] 팀 스탠드업 및 주간 스프린트 점검
- [14:00] GTD 외부 레포 연동 아키텍처 구현

## 📝 Completed Tasks
- [x] Antigravity CLI Linux 브릿지 연동 및 타임아웃 최적화

## 💡 Notes & Thoughts
- 비서형 상호작용과 GTD 브리핑 연동이 매끄럽게 동작함.
```

---

## 🧪 테스트 및 품질 검증

본 프로젝트는 견고한 품질 유지를 위해 자동화 테스트와 린트 파이프라인을 갖추고 있습니다:

```bash
# 1. pytest 전체 단위 및 통합 테스트 (20개 항목)
pytest

# 2. cURL 기반 라이브 API 엔드투엔드 스모크 테스트 (GTD 브리핑 포함)
./scripts/smoke_test.sh

# 3. 코드 스타일 및 린트 검사
ruff check .

# 4. 정적 타입 검사
mypy app tests
```

---

## 🛠️ 프로젝트 디렉토리 구조 & 에이전트 하네스

```text
watson-bot/
├── .agents/                 # 범용 에이전트 하네스 표준 (supervisor, lifelog_generator, git_worker 등)
│   ├── agents/              # 서브 에이전트 역할 정의
│   ├── skills/              # 모듈형 스킬 (git-automation, session-memory, markdown-lifelog)
│   └── rules/               # 자가진화(evolution.md) 및 정합성(spec_alignment.md) 규칙
├── app/
│   ├── db/                  # SQLAlchemy SQLite 모델 및 세션 관리
│   ├── models/              # Pydantic 스키마 정의
│   ├── routers/             # FastAPI 라우터 (web, chat, telegram, settings)
│   ├── services/            # 핵심 비즈니스 로직 (Supervisor, LLMProvider, GitWorker 등)
│   ├── static/              # 대시보드 CSS/JS/스타일
│   ├── templates/           # Jinja2 HTML 대시보드 및 설정 템플릿
│   └── main.py              # FastAPI 진입점 및 Lifespan 관리
├── docs/
│   ├── adr/                 # 아키텍처 결정 기록 (ADR-001 ~ ADR-022)
│   ├── PRD.md               # 제품 기획서
│   ├── requirements.md      # 기능 명세서
│   └── roadmap.md           # 개발 로드맵
├── systemd/
│   ├── watson.service       # 24/7 Linux OS 서비스 유닛 파일
│   └── watson-tunnel.service # 24/7 Cloudflare Tunnel 서비스 유닛 파일
├── scripts/                 # 스모크 테스트 및 유틸리티
├── tests/                   # pytest 테스트 스위트
├── docker-compose.yml       # 컨테이너 배포 명세
├── requirements.txt         # 파이썬 패키지 의존성
└── README.md                # 본 문서
```

---

## 📄 라이선스 (License)

본 프로젝트는 **MIT License**를 따릅니다.
