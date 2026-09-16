# 🚀 Watson 10분 완성 1-Click 셀프호스팅 퀵스타트 가이드 (Quickstart Guide)

본 문서는 누구나 자신의 개인 서버(오라클 클라우드 평생 무료 VM, AWS EC2, 라즈베리 파이, 로컬 홈 서버)에 **Watson 24/7 LifeLog & GTD 지능형 AI 비서**를 10분 만에 구축하고 사용할 수 있도록 안내하는 초보자용 배포 매뉴얼입니다 (ADR-046).

---

## 📋 0. 사전 준비물 (딱 3가지만 준비하세요!)

Watson은 사용자의 데이터를 중앙 서버로 전송하지 않고 **오직 사용자의 기기와 개인 GitHub 저장소에만 보관**하는 완벽한 프라이버시 우선 구조입니다.

| 준비물 | 소요 시간 | 비용 | 발급/확인 방법 |
| :--- | :--- | :--- | :--- |
| **1. 텔레그램 봇 토큰** | 1분 | 무료 | 텔레그램에서 [@BotFather](https://t.me/BotFather) 검색 ➔ `/newbot` 입력 후 토큰 획득 |
| **2. 본인 텔레그램 Chat ID** | 30초 | 무료 | 텔레그램에서 [@userinfobot](https://t.me/userinfobot) 검색 ➔ 대화창에 표시된 본인의 **숫자 Id** 복사 |
| **3. Google Gemini API Key** | 1분 | 무료 | [Google AI Studio](https://aistudio.google.com/) 접속 ➔ `Get API Key` 클릭 후 키 복사 |

---

## 🛠️ 1. 설치 및 배포 단계 (Step-by-Step)

### Step 1: 저장소 복제 (Clone Repository)

터미널을 열고 서버에 Watson 소스코드를 복제합니다:

```bash
git clone https://github.com/glshlee/watson-bot.git
cd watson-bot
```

---

### Step 2: 1-Click 셋업 위저드 실행 (Setup Wizard)

복잡한 `.env` 편집 없이 대화형 마법사가 모든 것을 자동으로 구성해 줍니다:

```bash
./scripts/setup_wizard.sh
```

화면의 안내에 따라 차례대로 입력합니다:
1. **포트 번호**: 기본값 `8000` (Enter)
2. **타임존**: 기본값 `Asia/Seoul` (Enter)
3. **텔레그램 봇 토큰**: 준비물 1에서 복사한 토큰 붙여넣기
4. **텔레그램 Chat ID**: 준비물 2에서 확인한 본인 숫자 ID 붙여넣기
5. **Gemini API Key**: 준비물 3에서 발급받은 키 붙여넣기
6. **GTD 저장소 경로**: 일기가 저장될 폴더 (기본값 `$HOME/lifelog`, Enter 시 자동 디렉토리 및 Git 생성)
7. **거주지 동네명**: 기상청 날씨/미세먼지 연동용 동네명 (예: `성동구 금호동`, `분당구 정자동`)
8. **웹 대시보드 보안**: 외부 접속 시 비밀번호 잠금 여부 (`true`/`false`)

> 💡 **Tip (무인 자동 설치)**: CI/CD나 자동화 환경에서는 `./scripts/setup_wizard.sh -y` 옵션을 사용하면 기본값으로 즉시 세팅됩니다.

---

### Step 3: 서비스 가동 (2가지 방식 중 선택)

#### 방법 A: systemd 백그라운드 상시 가동 (가장 추천 ⭐️)

서버가 재부팅되어도 Watson이 자동으로 시작되도록 등록합니다:

```bash
# 위저드가 생성한 맞춤형 서비스 파일 등록
sudo cp /tmp/watson.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now watson.service

# 가동 상태 확인
sudo systemctl status watson.service
```

#### 방법 B: Docker Compose 기반 격리 가동

도커 컨테이너 환경을 선호하는 경우:

```bash
docker compose up -d --build

# 로그 확인
docker compose logs -f
```

---

## 📱 2. 첫 대화 시작하기 (First Conversation)

1. 스마트폰 텔레그램 앱을 열고 본인이 생성한 봇 대화창으로 들어갑니다.
2. 대화창에 **`/start`**를 전송합니다.
3. 왓슨이 환영 인사와 함께 20종 네이티브 메뉴 및 사용법을 안내합니다!
4. 이제 일상 언어로 말을 걸어보세요:
   - *"오늘 해야할 일 정리해줘"* ➔ GTD 아침 집중 과제 브리핑
   - *"오늘 퇴근길에 헬스장에서 스쿼트 80kg 성공했어"* ➔ 일기 작성 사전 제안 및 승인 시 자동 커밋
   - 운동/음식 사진 전송 ➔ Vision AI 멀티모달 시각 분석 및 정갈한 표 포맷팅
   - 좌측 하단 `[/]` 버튼 클릭 ➔ 20종 원터치 명령어 팝업

---

## 🖥️ 3. 웹 대시보드 접속 및 연간 잔디 확인

1. 브라우저를 열고 `http://서버IP:8000` (로컬의 경우 `http://localhost:8000`)에 접속합니다.
2. 상단 헤더의 **연간 잔디 뱃지**(`🌿 2026: N일 기록`)를 클릭하거나 퀵 바의 **`[✏️ 잔디 & 로그 편집]`**을 클릭합니다.
3. 52주 연간 기여도 히트맵과 좌우 분할 실시간 마크다운 에디터에서 일일 로그를 조회·편집할 수 있습니다.

---

## 🌐 4. 포트포워딩 없는 무료 보안 접속 (Cloudflare Tunnel)

집이나 개인 NAS, 클라우드 사설망에서 공인 IP 포트 개방 없이 안전한 HTTPS 도메인을 연결하고 싶다면:

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)에서 무료 Tunnel을 생성합니다.
2. 발급받은 Tunnel Token을 `.env`의 `CLOUDFLARE_TUNNEL_TOKEN`에 입력합니다.
3. 서비스 재시작 후 텔레그램에서 `/url`을 입력하면 실시간 HTTPS 주소를 즉시 안내받을 수 있습니다.

---

## ❓ 5. 자주 묻는 질문 (FAQ & Troubleshooting)

### Q1. 텔레그램 메시지를 보냈는데 왓슨이 답장이 없어요.
* **원인 1**: `.env` 파일의 `TELEGRAM_ALLOWED_CHAT_IDS`에 본인의 Chat ID가 일치하지 않으면 보안상 응답하지 않습니다.
* **원인 2**: `sudo journalctl -u watson.service -e` 명령으로 로그를 확인하여 봇 토큰 오탈자 여부를 확인하세요.

### Q2. 일기나 GTD 파일이 어디에 저장되나요?
* 셋업 위저드에서 입력한 `GTD_PATH`(기본: `$HOME/lifelog`)에 마크다운 파일로 저장됩니다.
  - 일일 로그: `$HOME/lifelog/logs/daily/YYYY-MM-DD.md`
  - GTD 인박스: `$HOME/lifelog/gtd/inbox.md`
  - GTD 다음행동: `$HOME/lifelog/gtd/next_actions.md`
* 해당 폴더에 개인 GitHub 원격 레포(`git remote add origin ...`)를 연결해두면 자동으로 안전하게 원격 백업됩니다.

### Q3. 시스템 준비 상태를 언제든 다시 확인하고 싶어요.
* 터미널: `./scripts/setup_wizard.sh --check`
* 웹 API: `curl http://localhost:8000/api/system/setup-status`
* DevBot 콘솔: `/dev` 접속 후 `/setup` 명령어 입력
