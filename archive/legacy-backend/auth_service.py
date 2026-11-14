"""
SiteIQ CQMS — Enterprise Security & Multi-Tenant Authentication Engine
Provides:
1. Password hashing (bcrypt with salted rounds) & verification
2. JWT generation, signature verification, and expiration validation
3. Current authenticated user & organization extraction dependency
4. Multi-tenant access controls
"""

import os
import time
import json
import base64
import hmac
import hashlib
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends, status
import bcrypt

JWT_SECRET = os.environ.get("SITEIQ_JWT_SECRET", "siteiq-super-secure-production-qc-secret-key-2026-v1")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400 * 7  # 7 days

def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64_url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)

def create_access_token(user_id: str, org_id: str, role: str, email: str, full_name: str, employee_id: Optional[str] = None) -> str:
    """Create a signed JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "email": email,
        "name": full_name,
        "emp_id": employee_id or "",
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS
    }
    
    hdr_b64 = _b64_url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    pay_b64 = _b64_url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    msg = f"{hdr_b64}.{pay_b64}".encode('utf-8')
    sig = hmac.new(JWT_SECRET.encode('utf-8'), msg, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(sig)
    return f"{hdr_b64}.{pay_b64}.{sig_b64}"

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Validate JWT token signature and expiration, returning decoded payload."""
    parts = token.strip().split('.')
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token"
        )
    
    hdr_b64, pay_b64, sig_b64 = parts
    msg = f"{hdr_b64}.{pay_b64}".encode('utf-8')
    expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), msg, hashlib.sha256).digest()
    
    try:
        actual_sig = _b64_url_decode(sig_b64)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
    
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
    
    try:
        payload = json.loads(_b64_url_decode(pay_b64).decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token has expired")
        
    return payload

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Extract authenticated user payload if header is provided."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    try:
        return verify_jwt_token(token)
    except HTTPException:
        return None

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Enforce authentication and extract user payload."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credential required. Please sign in."
        )
    token = authorization.replace("Bearer ", "").strip()
    return verify_jwt_token(token)
