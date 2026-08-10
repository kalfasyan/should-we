from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

from .config import _label_to_key, data_dir, project_paths

_PBKDF2_ITERATIONS = 200_000


def users_path() -> Path:
    return data_dir() / ".users.json"


def load_users() -> dict[str, str]:
    path = users_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def save_users(users: dict[str, str]) -> None:
    path = users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(users, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS).hex()


def create_user(name: str) -> tuple[str, str | None]:
    """Create a test user; returns (password, error). Password is shown once, hash stored."""
    name = name.strip()
    if not name:
        return "", "Name required."
    users = load_users()
    if name in users:
        return "", f"User '{name}' already exists."
    key = _label_to_key(name)
    if not key:
        return "", "Name must contain at least one letter or digit."
    for other in users:
        if _label_to_key(other) == key:
            return "", f"Project key '{key}' is already used by user '{other}'."
    cfg_path, _ = project_paths(key)
    if cfg_path.exists():
        return "", f"Project key '{key}' already exists — pick a different name."
    password = secrets.token_urlsafe(12)
    salt = secrets.token_urlsafe(8)
    users[name] = f"{hash_password(password, salt)}:{salt}"
    save_users(users)
    return password, None


def verify_user(name: str, password: str | None) -> bool:
    stored = load_users().get(name.strip())
    if not stored or ":" not in stored:
        return False
    digest, salt = stored.split(":", 1)
    return secrets.compare_digest(digest, hash_password(password or "", salt))


def delete_user(name: str) -> None:
    users = load_users()
    users.pop(name, None)
    save_users(users)
