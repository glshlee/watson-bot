# Telegram Bot Advanced Project 🚀

고도화된 비동기 텔레그램 봇 프로젝트입니다. `aiogram 3.x` 프레임워크 기반으로 확장 가능하고 깔끔한 모듈화 구조를 제공합니다.

## 주요 특징
- **비동기 기반**: Python `asyncio` & `aiogram 3.x` 적용
- **모듈화 핸들러**: 기능별 핸들러(Handlers) 분리 구조
- **환경 변수 관리**: `.env` 파일 기반 안전한 토큰 및 구성 관리

## 시작하기

### 1. 가상환경 구축 및 패키지 설치
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일에 Telegram Bot Token 입력
```

### 3. 봇 실행
```bash
python main.py
```
