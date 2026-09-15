# ADR-041: 텔레그램 봇 메뉴 명령어 관리 UI 및 실시간 모바일 미리보기·원터치 동기화

## 1. 배경 (Context)
- ADR-040을 통해 텔레그램 봇의 14종 핵심 명령어를 Telegram Bot API(`setMyCommands`)에 자동 등록하도록 구현하였다.
- 그러나 사용자가 특정 명령어를 끄거나(비활성화), 새로운 커스텀 명령어를 추가하거나, 설명 문구를 변경하고자 할 때 소스코드를 직접 수정해야 하는 한계가 있었다.
- 사용자는 웹 대시보드 콘솔에서 텔레그램 봇 메뉴 명령어를 시각적으로 확인하고, 체크박스로 켜고 끄며, 실시간으로 모바일 텔레그램 팝업 UI가 어떻게 보일지 미리보면서 터치 한 번으로 텔레그램 서버에 즉시 저장 및 동기화할 수 있는 전용 설정 화면을 요구하였다.

## 2. 의사결정 (Decision)
1. **명령어 영속화 설정 파일 체계 구축 (`config/telegram_commands.json`)**:
   - `config/telegram_commands.json` 및 `config/telegram_commands.json.example`을 제공하여 사용자 커스텀 명령어 목록 및 각 명령어별 활성화 여부(`enabled: true/false`)를 JSON으로 안전하게 영속화한다.
   - `TelegramService.get_configured_commands()`, `save_configured_commands()`, `reset_to_default_commands()`를 구현하여 소스코드 수정 없이 동적 관리가 가능하도록 한다.
2. **REST API 엔드포인트 확장 (`app/routers/telegram_router.py`)**:
   - `GET /api/telegram/commands`: 전체 및 활성 명령어 목록, 봇 연동 상태 반환.
   - `POST /api/telegram/commands`: 명령어 목록 수정/추가/삭제 저장 및 Telegram Bot API 실시간 동기화(`sync_to_telegram`).
   - `POST /api/telegram/commands/reset`: 기본 14종 표준 명령어로의 원터치 복원 및 동기화.
3. **웹 콘솔 전용 텔레그램 봇 메뉴 설정 모달 (`#telegram-menu-modal`)**:
   - 상단 헤더에 `[📱 메뉴: N개]` 배지(`#telegram-menu-badge`) 및 퀵 바에 `[📱 텔레그램 메뉴]` 칩을 배치하여 원클릭으로 모달을 호출할 수 있도록 구현.
   - **좌측(명령어 편집기)**: 각 명령어 행마다 On/Off 체크박스, 명령어 이름 수정란, 한글 설명 수정란, 삭제 버튼(`fa-trash-can`) 및 하단 `+ 새 명령어 추가` 폼 제공.
   - **우측(모바일 실시간 미리보기)**: 실제 스마트폰 텔레그램 다크 테마 UI를 시뮬레이션한 프레임(`mock-telegram-frame`)을 배치하여, 좌측에서 체크를 끄거나 켤 때마다 실시간으로 `[/]` 팝업 리스트가 반응하도록 구현.
   - **하단 액션**: `[기본값 복원]` 원터치 롤백 버튼 및 `[텔레그램에 즉시 반영]` 저장 버튼 제공.

## 3. 결과 및 효과 (Consequences)
- **GUI 기반 노코드 텔레그램 봇 관리**: 개발 지식이나 코드 수정 없이 웹 브라우저에서 체크박스 터치만으로 텔레그램 메뉴를 자유자재로 켜고 끌 수 있다.
- **실시간 피드백 및 제로-미스**: 스마트폰 화면을 본뜬 라이브 프리뷰를 보면서 편집하므로 오타나 누락 없이 직관적으로 메뉴를 구성할 수 있다.
- **안전한 복원력**: 잘못 설정하더라도 언제든 `[기본값 복원]` 버튼 하나로 공식 14종 표준 세트로 즉시 원상복구할 수 있다.
