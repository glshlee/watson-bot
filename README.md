# 🤖 Watson (왓슨) - 24/7 GitHub LifeLog AI Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0.svg)](https://core.telegram.org/bots)
[![GitHub Actions & Git](https://img.shields.io/badge/Git-Automation-F05032.svg)](https://git-scm.com/)

> **"대화는 가볍게, 기록은 단단하게."**  
> 왓슨(Watson)은 24시간 상시 가동되며 모바일(텔레그램) 및 웹 대시보드를 통해 사용자의 일상을 기록하고, 표준화된 마크다운 라이프로그로 변환하여 GitHub 저장소에 자동 커밋해 주는 **지능형 LifeLog AI 비서(Butler)**입니다.

---

## 📑 목차 (Table of Contents)

1. [🌟 핵심 특징](#-핵심-특징-key-features)
2. [🏗️ 시스템 아키텍처](#️-시스템-아키텍처)
3. [📋 사전 준비 사항](#-사전-준비-사항-prerequisites)
4. [🐳 Docker 기반 완전 설치 & 24/7 배포 가이드 (메인 매뉴얼)](#-docker-기반-완전-설치--247-배포-가이드-메인-매뉴얼)
5. [💻 방법 2: 파이썬 가상환경 직접 실행 (개발/로컬용)](#-방법-2-파이썬-가상환경-직접-실행-개발로컬용)
6. [📱 실전 사용 매뉴얼 (User Manual)](#-실전-사용-매뉴얼-user-manual)
7. [📁 마크다운 라이프로그 저장 구조](#-마크다운-라이프로그-저장-구조)
8. [🧪 테스트 및 품질 검증](#-테스트-및-품질-검증)
9. [🛠️ 프로젝트 디렉토리 구조](#️-프로젝트-디렉토리-구조)
10. [📄 라이선스](#-라이선스-license)

---

## 🌟 핵심 특징 (Key Features)

- 🧠 **지능형 비서 & 능동 제안 (Smart Butler)**
  - 단순 잡담/인사는 세션에만 보관하고 Git을 어지럽히지 않습니다.
  - 운동, 업무, 생각 등 기록할 가치가 있는 일과를 감지하면 비서가 먼저 **"라이프로그에 기록할까요?"**라고 인라인 버튼으로 제안합니다.
- 📝 **1기록 1커밋 & 마크다운 영속화 (Git-Backed LifeLog)**
  - 사용자가 승인(`[✅ 응, 기록해줘]`)하거나 직접 명령(`/log`)한 확정된 기록만 `lifelogs/YYYY/MM/YYYY-MM-DD.md`에 카테고리별로 정돈되어 즉시 Git 커밋/푸시됩니다.
- 📱 **모바일 텔레그램 봇 연동 (Zero-Config Mobile Bot)**
  - 도메인/SSL 설정 없이 봇 토큰만으로 즉시 구동되는 **비동기 롱 폴링(Long Polling)** 모드 지원.
  - 비인가 접근을 차단하는 **화이트리스트 보안** 및 원클릭 기록 확정 **인라인 키보드** 지원.
  - 사진과 일과 메모를 함께 전송하면 자동으로 첨부파일을 다운로드하고 마크다운에 연동.
- 🖥️ **올인원 웹 대시보드 (Web Dashboard)**
  - 실시간 웹 채팅, 날짜/채널별 세션 기록 조회, 오늘 작성된 마크다운 라이프로그 실시간 렌더링 뷰어 제공.
- 🐳 **24/7 원클릭 Docker 컨테이너 패키징**
  - Oracle Cloud, AWS, GCP, 개인 서버 등에서 도커로 데이터 유실 없이 24시간 365일 안전하게 무중단 구동.

---

## 🏗️ 시스템 아키텍처

```mermaid
flowchart LR
    subgraph Clients["📱 사용자 인터페이스"]
        TG["텔레그램 모바일 앱"]
        WEB["웹 대시보드 (브라우저)"]
    end

    subgraph Docker["🐳 Docker Container (watson-agent)"]
        Router["Telegram & Web Router"]
        Supervisor["Supervisor (오케스트레이터)"]
        LLM["AI Engine (Gemini 1.5 Flash / AGY)"]
        SessionDB[("SQLite 세션 DB (Volume)")]
        GitWorker["Git & Markdown Service"]
    end

    subgraph Storage["📦 영속화 및 버전 관리"]
        LocalMD["lifelogs/*.md 마크다운 (Volume)"]
        HostSSH["~/.ssh & ~/.gitconfig (Volume)"]
        GitHub["GitHub 원격 저장소 (Remote Repo)"]
    end

    TG <-->|Long Polling| Router
    WEB <-->|HTTP / REST (포트 8000)| Router
    Router --> Supervisor
    Supervisor <--> LLM
    Supervisor <--> SessionDB
    Supervisor -->|승인 시 1기록 1커밋| GitWorker
    GitWorker --> LocalMD
    GitWorker -.->|인증 참조| HostSSH
    GitWorker -->|git push| GitHub
```

---

## 📋 사전 준비 사항 (Prerequisites)

1. **Google Gemini API Key (무료)**:
   - [Google AI Studio](https://aistudio.google.com/)에서 무료로 즉시 발급받을 수 있습니다.
2. **텔레그램 봇 토큰 및 본인 Chat ID (모바일 연동 시)**:
   - 텔레그램 앱에서 [@BotFather](https://t.me/botfather) 검색 ➔ `/newbot` 입력하여 봇 생성 후 **HTTP API Token** 복사.
   - 본인의 Chat ID 확인: [@userinfobot](https://t.me/userinfobot)에게 아무 메시지를 보내 `Id` 번호 확인.
3. **GitHub SSH 배포 키(Deploy Key)**:
   - 원격 서버 컨테이너가 라이프로그를 자동으로 커밋하고 푸시할 수 있도록 저장소 쓰기 권한이 필요합니다.

---

## 🐳 Docker 기반 완전 설치 & 24/7 배포 가이드 (메인 매뉴얼)

본 서비스는 **Docker Compose를 통한 24/7 상시 가동**을 기본 표준으로 설계되었습니다.  
새로운 원격 서버(Oracle Cloud, Ubuntu, Debian 등)에 처음 설치할 때 아래 순서대로 진행하시면 5분 안에 배포가 완료됩니다.

### Step 1. 서버에 Docker 및 Docker Compose 설치

이미 서버에 도커가 설치되어 있다면 **Step 2**로 넘어가세요.  
설치되어 있지 않다면 공식 원클릭 스크립트로 즉시 설치합니다:

```bash
# 1. 도커 공식 자동 설치 스크립트 실행
curl -fsSL https://get.docker.com | sh

# 2. 현재 로그인 계정에 도커 실행 권한 부여 (sudo 없이 실행하기 위함)
sudo usermod -aG docker $USER

# 3. 변경된 그룹 권한 적용을 위해 재로그인 (또는 터미널 재접속)
newgrp docker

# 4. 설치 확인 (Docker 및 Docker Compose 버전 출력 확인)
docker --version
docker compose version
```

---

### Step 2. Watson 저장소 클론

```bash
# 왓슨 프로젝트 복제 및 디렉토리 이동
git clone https://github.com/glshlee/watson-bot.git
cd watson-bot
```

---

### Step 3. 환경 변수 설정 (`.env`)

템플릿(`.env.example`)을 복사하여 `.env` 파일을 생성하고 본인의 키 값을 입력합니다:

```bash
cp .env.example .env
nano .env  # 또는 vim .env
```

**.env 파일 필수 설정 내용:**

```ini
# ==============================================================================
# Watson 24/7 AI Agent Environment Configuration
# ==============================================================================

# [필수] Google Gemini API 키
GEMINI_API_KEY=AIzaSy...실제_발급받은_키_입력...
LLM_MODEL=gemini-1.5-flash

# [선택] 텔레그램 봇 연동 (모바일에서 사용하려면 반드시 입력)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
# 본인의 텔레그램 Chat ID (인가된 사용자만 봇을 사용할 수 있도록 제한, 쉼표로 다중 등록 가능)
TELEGRAM_ALLOWED_CHAT_IDS=123456789

# [서버 및 Git 기본 설정]
PORT=8000
ENV=production
DATABASE_URL=sqlite:///./app.db
REPO_PATH=.
GIT_REMOTE_NAME=origin
GIT_BRANCH=main
```

---

### Step 4. 원격 서버 GitHub SSH 배포 키(Deploy Key) 설정 (필수 ⭐)

왓슨 도커 컨테이너는 호스트 서버의 `~/.ssh` 키를 안전하게 마운트하여 마크다운 기록 발생 시 GitHub로 자동 `git push`합니다.  
서버에서 SSH 키를 1회 생성하고 GitHub에 등록해야 합니다:

```bash
# 1. 서버 호스트에서 SSH 키 생성 (엔터 3번 입력)
ssh-keygen -t ed25519 -C "watson-agent" -f ~/.ssh/id_ed25519 -N ""

# 2. 생성된 공개키 내용 복사
cat ~/.ssh/id_ed25519.pub
```

1. 웹 브라우저에서 본인의 GitHub 저장소 (`https://github.com/glshlee/watson-bot`) 접속
2. **Settings** ➔ **Deploy keys** ➔ **Add deploy key** 클릭
3. **Title**: `Watson Server Key` 입력
4. **Key**: 터미널에서 복사한 `ssh-ed25519 AAAA...` 공개키 붙여넣기
5. ⚠️ **"Allow write access" (쓰기 권한 허용) 체크박스를 반드시 체크**한 후 **Add key** 클릭
6. 서버 터미널로 돌아와 저장소 원격 주소를 SSH 주소로 변경:
   ```bash
   git remote set-url origin git@github.com:glshlee/watson-bot.git

   # SSH 연결 및 인증 확인 (성공 시 Hi glshlee/watson-bot! 안내 메시지 출력)
   ssh -T git@github.com
   ```

---

### Step 5. Docker Compose로 24/7 무중단 백그라운드 구동

이제 모든 준비가 끝났습니다! 도커 컨테이너를 빌드하고 실행합니다:

```bash
# 컨테이너 빌드 및 백그라운드 구동
docker compose up -d --build
```

**실행 상태 및 로그 확인:**

```bash
# 1. 실행 중인 컨테이너 상태 확인 (STATUS가 Up인지 확인)
docker compose ps

# 2. 실시간 로그 스트리밍 확인 (Ctrl + C 로 빠져나올 수 있음)
docker compose logs -f
```

로그에 다음과 같이 출력되면 정상 가동 중입니다:
```text
watson-agent | INFO:watson.main:🚀 Starting Watson Telegram Bot Polling task in background...
watson-agent | INFO: Application startup complete.
watson-agent | INFO: Uvicorn running on http://0.0.0.0:8000
```

> **💾 데이터 보존 안내 (Docker Volumes):**  
> `docker-compose.yml` 설정에 의해 세션 DB(`app.db`)와 마크다운 파일(`lifelogs/`)이 호스트 디렉토리에 실시간 영속화됩니다. 컨테이너를 종료하거나 재빌드해도 데이터가 절대 유실되지 않습니다.

---

### Step 6. 오라클 클라우드(OCI) 등 외부 방화벽 포트(8000) 개방

웹 대시보드(`http://[서버IP]:8000`)에 외부에서 접속하려면 서버 인스턴스의 8000번 포트를 열어주어야 합니다:

1. **오라클 클라우드 웹 콘솔 설정**:
   - 인스턴스 ➔ 연결된 **Virtual Cloud Network (VCN)** 클릭 ➔ **Security Lists** 클릭
   - **Ingress Rules** ➔ **Add Ingress Rules**
   - Source CIDR: `0.0.0.0/0`, IP Protocol: `TCP`, Destination Port Range: `8000` 추가
2. **리눅스 OS 내부 방화벽(iptables) 허용**:
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save  # 설정 영구 저장
   ```

---

### Step 7. 유용한 Docker 관리 명령어

```bash
# 컨테이너 중지
docker compose down

# 컨테이너 재시작
docker compose restart

# 코드 업데이트 후 재배포 (Git 최신 코드 수신 및 무중단 재빌드)
git pull origin main
docker compose up -d --build
```

---

## 💻 방법 2: 파이썬 가상환경 직접 실행 (개발/로컬용)

Docker 없이 개발용 PC나 로컬 환경에서 테스트할 때 사용하는 방법입니다:

```bash
# 1. 가상환경 생성 및 활성화 (Python 3.10 이상)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 패키지 설치
pip install -r requirements.txt

# 3. 환경 변수 파일 생성 (.env)
cp .env.example .env
# .env 파일에 GEMINI_API_KEY, TELEGRAM_BOT_TOKEN 등 입력

# 4. 서버 실행
python app.py
# 또는 uvicorn app.main:app --reload --port 8000
```

---

## 📱 실전 사용 매뉴얼 (User Manual)

### 1. 모바일 텔레그램 봇으로 사용하기

스마트폰 텔레그램 앱에서 왓슨 봇에게 편안하게 말을 걸어보세요:

| 상황 | 사용자 입력 예시 | 왓슨 AI 반응 및 동작 |
| :--- | :--- | :--- |
| **봇 시작** | `/start` | 왓슨 비서의 환영 인사 및 사용 가이드 안내 |
| **일반 대화** | "오늘 날씨 어때?", "안녕!" | 다정하게 대화를 나누며 세션에만 보관 (Git 커밋 X) |
| **일과 보고** | "오늘 헬스장에서 스쿼트 100kg 완료!" | **일과 가치 감지** ➔ `[✅ 응, 기록해줘]` / `[❌ 아니야]` 인라인 버튼 표시 |
| **기록 승인** | 버튼 클릭 또는 "응", "기록해줘" | 즉시 마크다운 생성 ➔ Git 커밋 & 푸시 완료 메시지 반환 |
| **직접 기록** | `/log 저녁 개발 회의 및 코드 리뷰 완료` | 제안 단계 없이 즉시 마크다운 기록 및 Git 커밋 |
| **사진 첨부** | 음식/운동 사진 + 캡션 전송 | 이미지 자동 저장 (`lifelogs/attachments/`) 후 마크다운에 연동 |

---

### 2. 웹 대시보드 사용하기

브라우저(`http://localhost:8000` 또는 `http://[서버-공인-IP]:8000`)로 접속하여 시각적으로 라이프로그를 검토하고 대화할 수 있습니다:

1. **좌측 사이드바**: 날짜별/채널별(`web`, `telegram:xxxxx`) 대화 세션 히스토리 목록 탐색.
2. **중앙 채팅창**: 왓슨과 실시간 대화 및 라이프로그 제안 승인/반려.
3. **우측 뷰어**: 오늘 날짜의 마크다운 라이프로그 실시간 렌더링 확인.

---

## 📁 마크다운 라이프로그 저장 구조

기록된 모든 일과는 다음과 같이 표준화된 디렉토리와 마크다운 서식으로 영구 보존됩니다:

```text
lifelogs/
├── 2026/
│   └── 09/
│       ├── 2026-09-05.md
│       └── 2026-09-07.md
└── attachments/
    └── tg_1788591358_photo.jpg
```

**마크다운 파일 예시 (`lifelogs/2026/09/2026-09-05.md`):**

```markdown
# 📅 2026-09-05 LifeLog

## 📝 Daily Work & Tasks
- [15:30] Docker 배포 패키징 완료 및 문서화 작업

## 🏃 Workout & Health
- [18:00] 헬스장에서 스쿼트 100kg 완료!

## 📸 Media & Attachments
- ![운동 인증사진](../../attachments/tg_1788591358_photo.jpg)
```

---

## 🧪 테스트 및 품질 검증

프로젝트의 안정성을 위해 제공되는 자동화 테스트 스크립트입니다:

```bash
# 1. 전체 단위 테스트 (15개 항목)
pytest

# 2. cURL 기반 라이브 API 스모크 테스트 (서버 자동 기동/검증/종료)
./scripts/smoke_test.sh

# 3. 파이썬 코드 스타일 및 린트 검사
ruff check .
```

---

## 🛠️ 프로젝트 디렉토리 구조

```text
watson-bot/
├── .agents/                 # 범용 에이전트 하네스 표준 (역할, 스킬, 자가진화 규칙)
├── app/
│   ├── db/                  # SQLAlchemy SQLite 모델 및 세션
│   ├── models/              # Pydantic 스키마 정의
│   ├── routers/             # FastAPI 엔드포인트 (web, chat, telegram)
│   ├── services/            # 비즈니스 로직 (Supervisor, LLM, Git, Telegram 등)
│   ├── static/              # 대시보드 CSS/JS/첨부 이미지
│   ├── templates/           # Jinja2 HTML 대시보드
│   └── main.py              # FastAPI 진입점 & Lifespan 관리
├── docs/                    # PRD, 요구사항, 로드맵, 배포 가이드, ADR 목록
├── lifelogs/                # 자동 생성되는 마크다운 라이프로그 저장소
├── scripts/                 # 스모크 테스트 및 유틸리티 스크립트
├── tests/                   # pytest 테스트 스위트
├── docker-compose.yml       # 24/7 무중단 배포 구성 파일
├── Dockerfile               # 컨테이너 빌드 파일
├── requirements.txt         # 파이썬 의존성 목록
└── README.md                # 본 문서
```

---

## 📄 라이선스 (License)

본 프로젝트는 **MIT License**를 따릅니다.
