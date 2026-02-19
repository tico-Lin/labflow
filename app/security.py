"""
身份驗證與授權模組 (Security & Authorization Module)

【功能】
- JWT 令牌管理（生成、驗證）
- 密碼加密與驗證
- 角色控制（RBAC）
- 依賴注入：current_user, current_admin

【技術棧】
- PyJWT: JWT 令牌
- passlib + bcrypt: 密碼加密
- datetime: 過期時間管理

【版本】v1.0
【最後更新】2026-01-07
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt as jwt_module

# 離線模式標誌（支持離線無 token 存取）
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "true").strip().lower() in {"1", "true", "yes"}
try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        """雜湊密碼"""
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return pwd_context.verify(plain_password, hashed_password)

except ImportError:
    import base64
    import hashlib
    import os

    # 提供備用的密碼雜湊實現
    def hash_password(password: str) -> str:
        """雜湊密碼 (備用實現，僅用於測試)"""
        salt = base64.b64encode(os.urandom(16)).decode("utf-8")
        h = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return f"$sha256${salt}${h}"

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """驗證密碼 (備用實現，僅用於測試)"""
        if not hashed_password.startswith("$sha256$"):
            return False
        _, salt, hash_value = hashed_password.split("$", 3)[1:]
        calculated_hash = hashlib.sha256(
            (plain_password + salt).encode("utf-8")
        ).hexdigest()
        return calculated_hash == hash_value


from fastapi import Header, HTTPException, status
from pydantic import BaseModel

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345678")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# JWT 錯誤
class JWTError(Exception):
    """JWT 相關錯誤"""

    pass


# ================== Token Schemas ==================


class TokenRequest(BaseModel):
    """令牌請求（用於刷新）"""

    refresh_token: str


class TokenResponse(BaseModel):
    """令牌回應"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    """用戶登錄請求"""

    username: str
    password: str


class UserRegister(BaseModel):
    """用戶註冊請求"""

    username: str
    password: str
    email: Optional[str] = None


class UserResponse(BaseModel):
    """用戶回應"""

    id: int
    username: str
    email: Optional[str]
    role: str

    model_config = {"from_attributes": True}


class TokenData(BaseModel):
    """JWT Payload 數據"""

    sub: int  # user_id
    username: str
    role: str
    exp: datetime


# ================== JWT 令牌管理 ==================
def create_access_token(data: Dict[str, Any]) -> str:
    """
    建立 Access Token

    Args:
        data: 要編碼的資料（必須包含 'sub' 與 'role'）
    Returns:
        JWT 令牌字串
    """
    to_encode = data.copy()
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt_module.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise JWTError(f"無法建立 token: {str(e)}")


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    建立 Refresh Token
    Args:
        data: 要編碼的資料
    Returns:
        JWT 令牌字串
    """
    to_encode = data.copy()
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt_module.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise JWTError(f"無法建立 refresh token: {str(e)}")


def verify_token(token: str) -> Dict[str, Any]:
    """
    驗證令牌

    Args:
        token: JWT 令牌字串

    Returns:
        解碼後的 payload

    Raises:
        JWTError: 令牌無效或過期
    """
    try:
        payload = jwt_module.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt_module.ExpiredSignatureError:
        raise JWTError("令牌已過期")
    except jwt_module.InvalidTokenError as e:
        raise JWTError(f"無效的令牌: {str(e)}")
    except Exception as e:
        raise JWTError(f"驗證令牌失敗: {str(e)}")


# ================== 依賴注入函式 ==================


def get_bearer_token(authorization: Optional[str] = None) -> str:
    """從 Authorization 請求頭提取 Bearer token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少認證令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證方案",
        )

    return credentials


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    依賴注入：取得當前用戶

    用法：
        @app.get("/users/me")
        def get_me(current_user = Depends(get_current_user)):
            return current_user
    """
    token = get_bearer_token(authorization)

    try:
        payload = verify_token(token)
        user_id: Optional[Any] = payload.get("sub")
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        role: Optional[str] = payload.get("role")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"id": user_id, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_admin(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    依賴注入：確認當前用戶是管理員

    用法：
        @app.delete("/users/{user_id}")
        def delete_user(user_id: int, admin = Depends(get_current_admin)):
            ...
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限",
        )
    return current_user


# ================== 離線模式支持 ==================


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    依賴注入：取得當前用戶（支持離線模式）

    行為：
    - 若 OFFLINE_MODE=true 且無 token → 返回虛擬用戶（id=0, role="offline"）
    - 若有 token → 驗證並返回用戶信息
    - 若 OFFLINE_MODE=false 且無 token → 返回 401 Unauthorized

    用法：
        @app.get("/files/")
        def read_files(current_user = Depends(get_current_user_optional)):
            return {"user": current_user}
    """
    # 若沒有 authorization header
    if not authorization:
        if OFFLINE_MODE:
            # 離線模式下允許訪問，返回虛擬用戶
            return {
                "id": 0,
                "role": "offline",
                "username": "offline_user",
                "is_offline": True,
            }
        else:
            # 非離線模式下，仍然要求認證
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少認證令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 有 token 則驗證
    try:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的認證方案",
            )

        payload = verify_token(credentials)
        user_id: Optional[Any] = payload.get("sub")
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        role: Optional[str] = payload.get("role")
        username: Optional[str] = payload.get("username")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"id": user_id, "role": role, "username": username, "is_offline": False}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


def is_offline_user(current_user: Dict[str, Any]) -> bool:
    """檢查是否為離線用戶"""
    return current_user.get("is_offline", False)
