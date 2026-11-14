"""Password hashing, session tokens and a small in-process rate limiter."""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import TooManyRequests, Unauthorized

SESSION_COOKIE = "siteiq_session"
CSRF_HEADER = "X-SiteIQ-CSRF"
MIN_PASSWORD_LENGTH = 10


class Role(str, Enum):
    ADMIN = "admin"
    QC_LEAD = "qc_lead"
    ENGINEER = "engineer"

    @property
    def home(self) -> str:
        return {"admin": "/admin", "qc_lead": "/qc", "engineer": "/engineer"}[self.value]

    @property
    def label(self) -> str:
        return {"admin": "Organization Admin", "qc_lead": "QC Lead", "engineer": "Field Engineer"}[self.value]


@dataclass(frozen=True)
class Principal:
    """The authenticated caller. org_id and role come only from the signed token."""
    user_id: str
    org_id: str
    role: Role
    email: str
    name: str
    employee_id: str = ""

    @property
    def actor(self) -> str:
        """Display name written to audit trails (never taken from request bodies)."""
        return f"{self.name} ({self.role.label})"


# ---------- passwords ----------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


_DUMMY_HASH = hash_password(uuid.uuid4().hex)


def verify_password_constant_time(plain: str, hashed: str | None) -> bool:
    """Always runs bcrypt so response time doesn't reveal whether an email exists."""
    if not hashed:
        verify_password(plain, _DUMMY_HASH)
        return False
    return verify_password(plain, hashed)


# ---------- tokens ----------

def create_token(user: dict) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {
        "sub": user["id"], "org_id": user["org_id"], "role": user["role"], "email": user["email"],
        "name": user["full_name"], "emp_id": user.get("employee_id") or "",
        "iat": now, "exp": now + s.jwt_ttl_seconds, "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Principal:
    try:
        p = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"],
                       options={"require": ["sub", "org_id", "role", "exp"]})
        return Principal(user_id=p["sub"], org_id=p["org_id"], role=Role(p["role"]), email=p.get("email", ""),
                         name=p.get("name", ""), employee_id=p.get("emp_id", ""))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise Unauthorized("Session expired or invalid. Please sign in again.") from exc


# ---------- rate limiting ----------

class RateLimiter:
    """Sliding-window limiter. In-process only: use Redis when running >1 replica."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                raise TooManyRequests("Too many attempts. Please wait a minute and try again.")
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter(limit=10, window_seconds=60)
signup_limiter = RateLimiter(limit=5, window_seconds=600)
