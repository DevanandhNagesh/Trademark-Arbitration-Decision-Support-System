"""auth.py - Authentication utilities, password hashing, JWT token issuance, and FastAPI dependencies."""

from __future__ import annotations

import os
import hashlib
import hmac
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from db import User, get_db
from logging_config import logger

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "trademark-dss-jwt-secret-key-2026-arbitration-system")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

VALID_ROLES = {"lawyer", "company", "admin"}
PUBLIC_SIGNUP_ROLES = {"lawyer", "company"}

PHOTO_SIG_EXPIRY_SECONDS = 600  # 10 minutes
PHOTO_REF_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Issue a signed JWT access token containing subject (email) and role."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to extract and validate the authenticated user from JWT token."""
    # If OAuth2PasswordBearer didn't extract token, check Authorization header directly
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: subject missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(allowed_roles: List[str]):
    """Factory dependency for role-based authorization."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {allowed_roles}, but user has role '{current_user.role}'.",
            )
        return current_user

    return role_checker


# Convenient preset for admin-only endpoints
require_admin = require_role(["admin"])


def validate_photo_reference(photo_reference: str) -> bool:
    """Validate photo_reference string format and length."""
    if not photo_reference or not isinstance(photo_reference, str):
        return False
    if len(photo_reference) > 1000:
        return False
    return bool(PHOTO_REF_PATTERN.match(photo_reference))


def generate_signed_photo_url(
    photo_reference: str, maxwidth: int = 400, expires_in_sec: int = PHOTO_SIG_EXPIRY_SECONDS
) -> str:
    """Generate an HMAC-signed photo proxy URL with expiry timestamp."""
    expires_at = int(time.time()) + expires_in_sec
    clamped_width = max(100, min(800, int(maxwidth)))
    msg = f"{photo_reference}:{expires_at}:{clamped_width}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"/places/photo?photo_reference={photo_reference}&maxwidth={clamped_width}&expires={expires_at}&sig={sig}"


def verify_photo_signature(photo_reference: str, maxwidth: int, expires: int, sig: str) -> bool:
    """Verify HMAC signature and expiration timestamp for photo proxy requests."""
    if not sig or not expires or not photo_reference:
        return False
    try:
        expires_int = int(expires)
        maxwidth_int = int(maxwidth)
    except (ValueError, TypeError):
        return False

    if int(time.time()) > expires_int:
        return False

    clamped_width = max(100, min(800, maxwidth_int))
    msg = f"{photo_reference}:{expires_int}:{clamped_width}".encode("utf-8")
    expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)
