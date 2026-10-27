#!/usr/bin/env bash
# ==============================================================================
# Watson Production Deployment Script (scripts/deploy.sh)
# ADR-062: Remote Production Server Pull & Safe Zero-Downtime Restart
# ==============================================================================
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

RUN_GATE=0
SKIP_PULL=0
for arg in "$@"; do
    case "$arg" in
        --with-gate)
            RUN_GATE=1
            ;;
        --no-pull)
            SKIP_PULL=1
            ;;
    esac
done

echo "=================================================================="
echo "🚢 Watson 24/7 운영계(Production) 배포 시작 (ADR-062)"
echo "=================================================================="

if [ "$SKIP_PULL" -eq 0 ]; then
    echo "🔄 [1/3] 원격 저장소 최신 코드 동기화 (git pull --rebase --autostash)..."
    git pull --rebase --autostash
else
    echo "⏭️  [1/3] --no-pull 옵션: 원격 풀(Pull) 단계를 건너뜁니다."
fi

if [ "$RUN_GATE" -eq 1 ]; then
    echo "🚦 [2/3] 통합 품질 게이트 실행 (./scripts/gate.sh)..."
    ./scripts/gate.sh
else
    echo "✅ [2/3] 로컬 Pre-Push 게이트 검증 완료 코드 반영 (서버 내 게이트 생략, 필요 시 --with-gate)"
fi

echo "🚀 [3/3] 운영 서비스(포트 8000) 비동기 재시작 및 헬스체크..."
./scripts/service.sh restart

echo "=================================================================="
echo "🎉 Watson 운영계 배포 및 헬스체크가 완료되었습니다!"
echo "=================================================================="
