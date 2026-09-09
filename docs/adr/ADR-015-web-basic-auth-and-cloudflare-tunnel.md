# ADR-015: 웹 콘솔 HTTP Basic 인증 및 Cloudflare Tunnel 보안 연동

## 1. 배경 (Context)
왓슨의 웹 대시보드(인터랙티브 대화 콘솔, 세션 내역 조회, GTD 설정)를 외부 모바일 기기 및 외부 PC에서 접속하여 활용하고자 하는 요구가 제기되었다.
그러나 다음과 같은 보안 및 네트워크 제약사항이 존재하였다:
1. **인증 부재 및 사생활 노출 위험**: 기존 웹 콘솔(`/`, `/api/*`)은 인증 없이 열려 있어, 공인 IP나 외부 인터넷에 노출될 경우 무단 사용자가 개인 GTD 인박스, 일기(라이프로그) 및 대화 내역을 열람하거나 임의로 Git 커밋/푸시를 유발할 수 있음.
2. **클라우드 인바운드 방화벽 제약**: 오라클 클라우드(OCI) 등 클라우드 가상 사설망(VCN)은 기본적으로 22번 포트만 개방되어 있어 8000번 포트 직접 접근이 차단됨.
3. **HTTP 평문 전송 위험**: 공인 IP로 8000번 포트를 직접 개방하더라도 HTTPS(SSL)가 적용되지 않아 공공 Wi-Fi 등에서 데이터 및 인증 정보 도청 위험이 존재함.

## 2. 결정 사항 (Decision)
1. **애플리케이션 계층 HTTP Basic 인증 (`app/auth.py`)**:
   - FastAPI의 `HTTPBasic`과 `secrets.compare_digest` 타이밍 공격 방어 함수를 적용하여 `verify_web_auth` 의존성 구현.
   - `web_router` 및 `settings_router` 전체 라우터에 기본 의존성으로 부착하여 웹 콘솔 접근 및 관리 API 호출 시 브라우저 네이티브 로그인 팝업(ID/PW) 강제.
   - `WEB_AUTH_ENABLED` 플래그 및 환경 변수(`WEB_AUTH_USERNAME`, `WEB_AUTH_PASSWORD`)를 통해 유연하게 활성화/비활성화 제어.
2. **네트워크 계층 Cloudflare Tunnel (`cloudflared`) 무개방 암호화 터널링**:
   - 외부 클라우드 인바운드 포트를 전혀 개방하지 않고, 아웃바운드 터널 방식으로 Cloudflare 엣지 네트워크와 로컬 8000 포트를 연결.
   - 무료 자동 HTTPS(SSL 인증서)가 제공되어 브라우저와 왓슨 서버 간의 모든 트래픽을 완벽 암호화.
   - 영구 백그라운드 구동을 위한 `systemd/watson-tunnel.service` 및 러너 스크립트(`scripts/run_tunnel.sh`) 구현 (Quick Tunnel 및 Token 기반 Named Tunnel 동시 지원).
3. **테스트 및 검증 자동화 동기화**:
   - `tests/test_auth.py` 신설: 인증 비활성화 시 정상 접근, 인증 활성화 시 401(WWW-Authenticate) 및 정상 인증(200 OK) 단위 검증.
   - `scripts/smoke_test.sh`: `.env`의 인증 설정을 감지하여 `0. Testing Authentication Guard` (비인가 401 차단 검증) 및 인증 플래그(`-u`) 기반 200 OK 테스트 자동 집행.

## 3. 결과 및 영향 (Consequences)
- **장점**:
  - 클라우드 방화벽을 복잡하게 설정하거나 포트를 열지 않고도 어디서나 안전한 HTTPS URL로 웹 대시보드 접근 가능.
  - 브라우저 네이티브 ID/PW 인증을 통해 외부인의 무단 접근 및 일기/GTD 유출을 원천 차단.
  - 전용 도메인이 있는 경우 `CLOUDFLARE_TUNNEL_TOKEN` 설정만으로 손쉽게 개인 도메인 연결 확장 가능.
- **테스트 및 검증**:
  - `pytest tests/test_auth.py`: 2개 테스트 통과.
  - `pytest tests/test_web_router.py tests/test_settings_service.py`: 7개 테스트 통과.
  - `scripts/smoke_test.sh`: 0번 Auth Guard 포함 전체 스모크 테스트 통과.
  - 라이브 Cloudflare Tunnel URL HTTPS cURL 검증 (비인가 시 401, 인가 시 200 OK) 완료.
