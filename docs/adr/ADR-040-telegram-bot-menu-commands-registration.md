# ADR-040: 텔레그램 네이티브 봇 메뉴 명령어(Bot Commands Menu) 등록 및 자동 동기화

## 1. 배경 (Context)
- 왓슨(Watson) 에이전트는 `/today`, `/briefing`, `/bus`, `/log`, `/done`, `/gtd`, `/schedule`, `/commute`, `/sync`, `/push`, `/url`, `/status`, `/help`, `/start` 등 다양하고 강력한 슬래시 명령어를 제공하고 있다.
- 그러나 텔레그램 메신저 대화창 좌측 하단의 네이티브 메뉴 버튼(`[/]`)을 눌렀을 때 등록된 명령어가 없어 사용자가 명령어의 이름이나 문법을 외워서 직접 입력해야 하는 불편이 있었다.
- 사용자는 텔레그램 메뉴 버튼(`[/]`)을 탭했을 때 모든 주요 기능이 설명과 함께 팝업 리스트로 표시되어, 타이핑 없이도 원터치로 명령을 실행할 수 있도록 정식 봇 메뉴 등록을 요청하였다.

## 2. 의사결정 (Decision)
1. **표준 봇 명령어 14종 사전 정의 (`TelegramService.DEFAULT_COMMANDS`)**:
   - `today` (오늘 일일 로그 확인)
   - `briefing` (GTD 아침/저녁 맞춤 브리핑)
   - `bus` (실시간 출근 버스 도착 현황 및 갱신)
   - `log` (오늘 라이프로그에 즉시 기록)
   - `done` (1순위 GTD 태스크 완료 및 푸시)
   - `gtd` (GTD 인박스 및 실행 대기 작업 확인)
   - `schedule` (브리핑 스케줄 및 당일 타임라인 확인)
   - `commute` (출근길 날씨·미세먼지·버스 설정 확인)
   - `sync` (GTD 원격 저장소 최신화 git pull)
   - `push` (로컬 커밋 원격 GitHub 푸시 git push)
   - `url` (웹 대시보드 Cloudflare 접속 주소)
   - `status` (왓슨 에이전트 시스템 상태 확인)
   - `help` (사용법 및 명령어 도움말)
   - `start` (왓슨 봇 시작 및 안내)
2. **Telegram Bot API 연동 및 자동 등록 루틴 (`set_my_commands`, `get_my_commands`)**:
   - `TelegramService.set_my_commands(commands=None)`: Telegram API `setMyCommands` 및 `setChatMenuButton(menu_button={"type": "commands"})`를 호출하여 봇 메뉴 버튼을 정식 활성화한다.
   - `TelegramService.get_my_commands()`: 현재 Telegram 서버에 등록된 명령어 목록을 조회한다.
   - `TelegramService.start_polling()`: 봇 폴링 루프 시작 시 자동으로 `set_my_commands()`를 실행하여 서버 기동 즉시 메뉴가 최신 상태로 동기화되도록 보장한다.
3. **REST API 엔드포인트 제공 (`telegram_router.py`)**:
   - `POST /api/telegram/setup-commands`: 텔레그램 봇 메뉴 명령어를 수동/외부 트리거로 즉시 등록 및 갱신.
   - `GET /api/telegram/commands`: 현재 Telegram 서버에 등록된 봇 명령어 목록 및 상태 조회.
4. **GTD 메뉴 실행 라우팅 개선 (`process_update`)**:
   - 메뉴에서 `/gtd` 선택 시 기존 단순 저장소 메타데이터 대신 실제 수집함(`inbox.md`) 및 다음 행동(`next_actions.md`) 목록을 지능형 브리핑으로 반환하도록 비서 파이프라인 연계. (단순 상태 질의는 `/gtd status`, `/repo`로 분리)

## 3. 결과 및 효과 (Consequences)
- **모바일 원터치 UX 극대화**: 텔레그램 채팅창 좌측의 `[/]` 버튼만 누르면 모든 명령어가 한글 설명과 함께 펼쳐지며 터치 한 번으로 즉시 실행된다.
- **배포 및 서버 재시작 시 자동 무중단 동기화**: 서버 시작 시 백그라운드 폴링 태스크가 `setMyCommands`를 자동 호출하므로 별도 수동 설정 없이 상시 최신 명령어가 유지된다.
- **외부 검증 및 관리 투명성**: REST API 엔드포인트와 스모크 테스트를 통해 CI/CD 및 라이브 환경에서 명령어 등록 상태를 언제든 확인하고 재등록할 수 있다.
