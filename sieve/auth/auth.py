"""Authentication, fixed-role access control, account seeding and audit helpers."""
from __future__ import annotations
import base64
import hashlib
import hmac
import re
import secrets
from .database import connect, init_db

ROLE_LABELS = {
    "admin": "Nexus",
    "inspect": "Prism",
    "firewall": "Aegis",
    "evaluation": "Vantage",
}
ROLE_DESCRIPTIONS = {
    "admin": "User and account management",
    "inspect": "Inspect Content",
    "firewall": "Agent Firewall",
    "evaluation": "Evaluation",
}
ROLE_MODULES = {
    "admin": frozenset({"user_management"}),
    "inspect": frozenset({"inspect"}),
    "firewall": frozenset({"firewall"}),
    "evaluation": frozenset({"evaluation"}),
}
PBKDF2_ITERATIONS = 310_000
MIN_PASSWORD_LENGTH = 12
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")

def validate_username(username: str) -> str:
    value = str(username).strip()
    if not USERNAME_RE.fullmatch(value):
        raise ValueError("Username must be 3–40 characters using letters, numbers, dot, underscore or hyphen.")
    return value

def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > 256:
        raise ValueError("Password is too long.")

def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False

def _safe_user(row) -> dict:
    result = dict(row)
    result.pop("password_hash", None)
    result["must_change_password"] = bool(result["must_change_password"])
    result["is_active"] = bool(result["is_active"])
    return result

def record_audit(username: str | None, event: str, details: str = "") -> None:
    with connect() as db:
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   (username, event[:80], details[:1000]))

def seed_users_from_secrets(seed_users) -> int:
    """Seed once from st.secrets['SIEVE_USERS']; entries need username, role, password."""
    entries = list(seed_users or [])
    if not entries:
        return 0
    prepared, seen, admins = [], set(), 0
    for entry in entries:
        username = validate_username(str(entry["username"]))
        if username.casefold() in seen:
            raise ValueError(f"Duplicate seed username: {username}")
        seen.add(username.casefold())
        role = str(entry["role"]).strip().lower()
        if role not in ROLE_LABELS:
            raise ValueError(f"Unsupported role '{role}' for {username}.")
        password = str(entry["password"])
        validate_password(password)
        display_name = str(entry.get("display_name") or username).strip()[:100]
        admins += int(role == "admin")
        prepared.append((username, display_name, role, hash_password(password)))
    if admins != 1:
        raise ValueError("Secrets must define exactly one initial admin account.")
    init_db()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return 0
        db.executemany(
            """INSERT INTO users(username,display_name,role,password_hash,must_change_password,is_active)
               VALUES (?,?,?,?,1,1)""", prepared)
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   ("system", "initial_accounts_seeded", f"{len(prepared)} account(s) seeded"))
        return len(prepared)

def authenticate(username: str, password: str) -> dict | None:
    init_db()
    username = str(username).strip()
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if row is None or not row["is_active"] or not verify_password(password, row["password_hash"]):
            db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                       (username[:40] or None, "login_failed", "Invalid credentials or inactive account"))
            return None
        db.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   (row["username"], "login_success", ""))
        updated = db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
        return _safe_user(updated)

def change_password(username: str, new_password: str) -> None:
    validate_password(new_password)
    with connect() as db:
        row = db.execute("SELECT id FROM users WHERE username=? COLLATE NOCASE AND is_active=1",
                         (username,)).fetchone()
        if row is None:
            raise ValueError("User account not found or inactive.")
        db.execute("UPDATE users SET password_hash=?,must_change_password=0,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (hash_password(new_password), row["id"]))
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   (username, "password_changed", "Password updated"))

def create_user(username: str, display_name: str, role: str, temporary_password: str) -> None:
    username = validate_username(username)
    role = str(role).strip().lower()
    if role not in ROLE_LABELS:
        raise ValueError("Choose one of the four supported roles.")
    validate_password(temporary_password)
    display_name = str(display_name).strip()[:100] or username
    with connect() as db:
        db.execute("""INSERT INTO users(username,display_name,role,password_hash,must_change_password)
                      VALUES (?,?,?,?,1)""",
                   (username, display_name, role, hash_password(temporary_password)))
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   (username, "account_created", f"Role: {role}"))

def list_users() -> list[dict]:
    init_db()
    with connect() as db:
        rows = db.execute("""SELECT id,username,display_name,role,must_change_password,
                                    is_active,created_at,updated_at,last_login
                             FROM users ORDER BY created_at,username""").fetchall()
        return [_safe_user(row) for row in rows]

def set_user_active(username: str, active: bool) -> None:
    with connect() as db:
        cursor = db.execute("UPDATE users SET is_active=?,updated_at=CURRENT_TIMESTAMP WHERE username=? COLLATE NOCASE",
                            (int(bool(active)), username))
        if cursor.rowcount != 1:
            raise ValueError("User account not found.")
        db.execute("INSERT INTO audit_events(username,event,details) VALUES (?,?,?)",
                   (username, "account_activated" if active else "account_deactivated", ""))

def has_module_access(role: str, module: str) -> bool:
    return module in ROLE_MODULES.get(str(role).lower(), frozenset())

def get_audit_events(limit: int = 200) -> list[dict]:
    limit = max(1, min(int(limit), 1000))
    init_db()
    with connect() as db:
        rows = db.execute("SELECT username,event,details,created_at FROM audit_events ORDER BY id DESC LIMIT ?",
                          (limit,)).fetchall()
        return [dict(row) for row in rows]
