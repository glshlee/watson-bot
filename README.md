# Watson Bot 🚀

Watson Bot은 개인 생산성(Todo, Memo, Schedule)을 효율적으로 관리할 수 있는 가벼운 비동기 봇 서비스입니다.

## 🏗️ Architecture & Key Features

- **Layered Architecture (레이어 분리 설계)**:
  - `interfaces/`: 챗봇 및 UI 입출력 레이어 (현재 텔레그램 `aiogram 3.x`, 추후 Discord/Slack 등 확장 가능)
  - `services/`: 도메인 및 생산성 비즈니스 로직
  - `storage/`: 저장소 레이어 (Markdown 직렬화 및 Git Sync)
  - `domain/`: 핵심 데이터 엔티티

- **Markdown & Git Persistence**:
  - 생성된 모든 할 일, 메모, 일정은 상위 저장소 `life_log` (`02_personal/watson/user_{user_id}.md`) 내의 표준 GFM 마크다운 문서로 자동 저장됩니다.
  - 변경 시 Git commit 및 push가 트리거되어 **GitHub 웹 UI** 상에서도 관리가 가능합니다.

## 🚀 Quick Start

1. **의존성 패키지 설치**:
   ```bash
   pip install -r requirements.txt
   ```

2. **환경변수 설정 (`.env`)**:
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   LIFE_LOG_PATH=/path/to/life_log
   ```

3. **실행**:
   ```bash
   python main.py
   ```
