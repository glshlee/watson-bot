import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic(auto_error=False)


def verify_web_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),  # noqa: B008
) -> bool:
    """
    웹 콘솔 및 관리 API 접근 시 HTTP Basic 인증을 검증합니다 (ADR-015).
    - WEB_AUTH_ENABLED가 False이고 WEB_AUTH_PASSWORD가 비어있으면 인증 생략
    - 활성화된 경우 올바른 아이디/비밀번호가 아니면 401 Unauthorized 반환 (브라우저 로그인 팝업 표시)
    """
    if not settings.WEB_AUTH_ENABLED and not settings.WEB_AUTH_PASSWORD:
        return True

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic realm='Watson Agent Console'"},
        )

    is_user_correct = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.WEB_AUTH_USERNAME.encode("utf-8"),
    )
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.WEB_AUTH_PASSWORD.encode("utf-8"),
    )

    if not (is_user_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic realm='Watson Agent Console'"},
        )

    return True
