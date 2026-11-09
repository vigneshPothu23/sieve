"""Sieve authentication package."""
from .auth import (
    ROLE_DESCRIPTIONS, ROLE_LABELS, ROLE_MODULES, authenticate, change_password,
    create_user, get_audit_events, has_module_access, list_users, record_audit,
    seed_users_from_secrets, set_user_active,
)
from .database import init_db

__all__ = [
    "ROLE_DESCRIPTIONS", "ROLE_LABELS", "ROLE_MODULES", "authenticate",
    "change_password", "create_user", "get_audit_events", "has_module_access",
    "init_db", "list_users", "record_audit", "seed_users_from_secrets",
    "set_user_active",
]
