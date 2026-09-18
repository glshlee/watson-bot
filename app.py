#!/usr/bin/env python3
"""
Watson 24/7 AI Agent Service Guardrail Entrypoint (ADR-056)
- 직접 포그라운드 실행을 방지하고 비동기(Background Daemon/systemd) 서비스 스크립트로 안전하게 위임합니다.
- 에이전트 및 CLI 환경에서 대화 세션 블로킹 및 고아 프로세스 생성을 원천 차단합니다.
"""
import os
import subprocess
import sys


def main() -> None:
    project_root = os.path.dirname(os.path.abspath(__file__))
    service_script = os.path.join(project_root, "scripts", "service.sh")

    if not os.path.exists(service_script):
        print(f"❌ 서비스 제어 스크립트를 찾을 수 없습니다: {service_script}", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]

    # 개발자가 명시적으로 포그라운드 디버깅을 요청한 경우만 예외 처리 (--foreground)
    if "--foreground" in args:
        print("⚠️ [Watson] 개발용 포그라운드 모드로 Uvicorn을 직접 실행합니다...")
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
        return

    # 기본 동작: 비동기(Background) 서비스 실행/제어로 위임
    subcommand = "start"
    extra_args = []
    if args:
        first = args[0]
        if first in ["start", "stop", "restart", "status", "logs", "install-systemd", "--help", "-h"]:
            subcommand = first
            extra_args = args[1:]
        else:
            extra_args = args

    print("=" * 65)
    print("🤖 [Watson] 비동기 서비스 실행 가드레일 (ADR-056)")
    print("포그라운드 직접 실행 대신 안전한 비동기 백그라운드 서비스로 위임합니다.")
    print(f"실행 명령: ./scripts/service.sh {subcommand} {' '.join(extra_args)}")
    print("=" * 65)

    cmd = [service_script, subcommand] + extra_args
    proc = subprocess.run(cmd, check=False)
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
