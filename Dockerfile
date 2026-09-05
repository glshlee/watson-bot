# ==============================================================================
# Watson 24/7 AI Agent - Dockerfile (Multi-Arch: AMD64 & ARM64)
# ==============================================================================

FROM python:3.11-slim

# 파이썬 표준 출력 버퍼링 비활성화 및 바이트코드 생성 방지
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Git 자동 커밋 및 푸시를 위한 git, curl 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스코드 복사
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# 라이프로그 디렉토리 생성
RUN mkdir -p /app/lifelogs

# 웹 대시보드 및 API 포트 노출
EXPOSE 8000

# 서버 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
