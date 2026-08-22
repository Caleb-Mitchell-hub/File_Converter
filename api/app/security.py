"""安全工具：密码哈希（PBKDF2-SHA256）+ JWT 签发/校验（HMAC-SHA256）。

全部基于标准库实现，不引入额外依赖：

- 密码存储格式：``pbkdf2_sha256${'$'}<iterations>${'$'}<salt_hex>${'$'}<hash_hex>``
- JWT：``header.payload.signature`` 三段式，HS256 签名，载荷含
  ``sub``（用户 id）、``iat``（签发时间）、``exp``（过期时间）
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional

#: PBKDF2 迭代次数（OWASP 建议 >= 60 万；本地项目 10 万保证速度与安全平衡）
_PBKDF2_ITERATIONS = 100_000


# ---------------------------------------------------------------------- #
# 密码哈希
# ---------------------------------------------------------------------- #
def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """对密码做 PBKDF2-SHA256 加盐哈希，返回可持久化的字符串。"""
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码是否匹配存储的哈希。任何解析失败都返回 False。"""
    try:
        algo, iterations_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations_s)
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------- #
# JWT（HMAC-SHA256）
# ---------------------------------------------------------------------- #
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_access_token(
    subject: str, secret: str, expires_seconds: int = 86400
) -> str:
    """签发 JWT。

    Args:
        subject: 用户唯一标识（这里用用户 id 的字符串形式）。
        secret: HMAC 签名密钥。
        expires_seconds: 有效期（秒），默认 24 小时。
    """
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "exp": now + expires_seconds}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_access_token(token: str, secret: str) -> Optional[dict[str, Any]]:
    """校验并解析 JWT。

    Returns:
        载荷 dict（含 ``sub``/``iat``/``exp``）；签名非法或已过期返回 None。
    """
    try:
        h, p, s = token.split(".")
        signing_input = f"{h}.{p}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(s)):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:  # noqa: BLE001 - 防御性：任何异常都视为无效 token
        return None
