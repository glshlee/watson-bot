# 🚀 Watson 원격 서버 24/7 상시 배포 가이드

본 문서는 Watson AI Agent를 원격 리눅스 서버(Oracle Cloud, AWS, GCP, 홈 서버 등)에 설치하여 24시간 365일 무중단으로 구동하는 가이드입니다.

---

## 🐳 방법 1: Docker Compose 원클릭 배포 (가장 추천 ⭐)

Docker가 설치된 모든 리눅스 환경에서 명령어 3줄로 즉시 배포할 수 있습니다.

### 1. 저장소 클론 및 디렉토리 이동
```bash
git clone https://github.com/glshlee/watson-bot.git
cd watson-bot
```

### 2. 환경 변수 설정 (`.env`)
```bash
cp .env.example .env
nano .env
```
* `GEMINI_API_KEY`: Google AI Studio에서 무료 발급받은 API 키 입력
* `PORT`: 기본값 `8000`

### 3. 컨테이너 빌드 및 백그라운드 실행
```bash
docker compose up -d --build
```

### 4. 실행 상태 및 로그 확인
```bash
docker compose ps
docker compose logs -f
```

* **대시보드 접속**: 브라우저에서 `http://[서버-공인-IP]:8000`

---

## ⚙️ 방법 2: systemd 데몬 백그라운드 배포 (Non-Docker)

Docker 없이 일반 파이썬 가상환경으로 서버 부팅 시 자동 실행되도록 등록하는 방법입니다.

```bash
# 1. 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 서비스 유닛 파일 등록
sudo cp systemd/watson.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable watson
sudo systemctl start watson

# 3. 상태 확인
sudo systemctl status watson
```

---

## 🔑 필수: 원격 서버 Git Push 자동 인증 팁

왓슨이 작성한 라이프로그 마크다운을 GitHub 저장소(`glshlee/watson-bot`)로 자동 푸시할 수 있도록, 원격 서버에서 1회 인증을 설정해야 합니다:

### SSH 배포 키(Deploy Key) 등록 (가장 편리)
```bash
# 1. 서버에서 키 생성
ssh-keygen -t ed25519 -C "watson-agent" -f ~/.ssh/id_ed25519 -N ""

# 2. 공개키 복사
cat ~/.ssh/id_ed25519.pub
```
3. GitHub 저장소(`glshlee/watson-bot`) ➔ **Settings** ➔ **Deploy keys** ➔ **Add deploy key**
4. 키 붙여넣기 후 **"Allow write access"** 반드시 체크!
5. 저장소 원격을 SSH 주소로 변경:
   ```bash
   git remote set-url origin git@github.com:glshlee/watson-bot.git
   ```

---

## 🛡️ 오라클 클라우드 네트워크 방화벽(포트 8000) 허용 팁
오라클 클라우드 인스턴스는 기본적으로 외부 포트가 닫혀 있으므로 두 가지를 열어주어야 합니다:
1. **오라클 클라우드 웹 콘솔**: Virtual Cloud Networks (VCN) ➔ Security Lists ➔ Ingress Rules ➔ `0.0.0.0/0`, TCP 포트 `8000` 추가
2. **서버 내부 방화벽(iptables) 해제**:
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
   sudo netfilter-persistent save  # 또는 sudo iptables-save
   ```
