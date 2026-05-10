import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.auth.hashing      import hash_password, verify_password
from api.auth.jwt_handler  import create_access_token
from api.auth.rbac         import require_role
from api.deps.current_user import get_current_user
from api.schemas.user import (
    ApproveUserRequest, LoginRequest, MessageResponse,
    RegisterRequest, TokenResponse, UserResponse, DeleteUserRequest
)

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

_DB_PATH_RAW = os.getenv("DB_PATH", "data/cybernova_analytics.duckdb")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _resolve_db() -> Path:
    """
    Resolve DB_PATH to an absolute Path regardless of working directory.
    Anchors relative paths to the dashboard/ project root.
    """
    p = Path(_DB_PATH_RAW)
    if not p.is_absolute():
        # parents[2] = api/routers → api → dashboard  (the project root)
        p = Path(__file__).resolve().parents[2] / p
    if not p.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not found at '{p}'. "
                   "Ask the systems manager to upload log data first.",
        )
    return p


def _get_con(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Open a DuckDB connection.
    DDL (CREATE TABLE) only runs on writable connections.
    """
    path = _resolve_db()
    con  = duckdb.connect(str(path), read_only=read_only)

    # Only create table on writable connections — never on read_only
    if not read_only:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                username    VARCHAR UNIQUE NOT NULL,
                hashed_pw   VARCHAR        NOT NULL,
                role        VARCHAR        NOT NULL,
                is_approved BOOLEAN        DEFAULT FALSE,
                created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
            )
        """)
    return con


def _next_id(con) -> int:
    return con.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM users"
    ).fetchone()[0]


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(body: RegisterRequest):
    con = _get_con()   # writable — creates users table if missing

    existing = con.execute(
        "SELECT id FROM users WHERE username = ?", [body.username]
    ).fetchone()

    if existing:
        con.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' is already taken.",
        )

    new_id = _next_id(con)
    hashed = hash_password(body.password)

    con.execute(
        "INSERT INTO users (id, username, hashed_pw, role, is_approved) "
        "VALUES (?, ?, ?, 'salesperson', FALSE)",
        [new_id, body.username, hashed],
    )
    con.close()
    return MessageResponse(
        message=f"Account '{body.username}' created. "
                "Awaiting approval from the systems manager."
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    # read_only=True — no DDL, just SELECT
    con = duckdb.connect(str(_resolve_db()), read_only=True)

    row = con.execute(
        "SELECT id, hashed_pw, role, is_approved "
        "FROM users WHERE username = ?",
        [body.username],
    ).fetchone()
    con.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    _, hashed_pw, role, is_approved = row

    if not verify_password(body.password, hashed_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval by the systems manager. "
                   "Please contact your administrator.",
        )

    token = create_access_token({
        "sub":         body.username,
        "role":        role,
        "is_approved": is_approved,
    })

    return TokenResponse(access_token=token, role=role, username=body.username)


@router.get("/pending", response_model=list[UserResponse])
def list_pending(current_user: dict = Depends(get_current_user)):
    require_role(current_user["role"], "systems_manager")
    con  = duckdb.connect(str(_resolve_db()), read_only=True)
    rows = con.execute(
        "SELECT id, username, role, is_approved "
        "FROM users WHERE is_approved = FALSE"
    ).fetchall()
    con.close()
    return [UserResponse(id=r[0], username=r[1], role=r[2], is_approved=r[3])
            for r in rows]


@router.post("/approve/{user_id}", response_model=MessageResponse)
def approve_user(
    user_id: int,
    body: ApproveUserRequest,
    current_user: dict = Depends(get_current_user),
):
    require_role(current_user["role"], "systems_manager")
    con = _get_con()   # writable

    row = con.execute(
        "SELECT username FROM users WHERE id = ?", [user_id]
    ).fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}.")

    con.execute(
        "UPDATE users SET is_approved = TRUE, role = ? WHERE id = ?",
        [body.role, user_id],
    )
    con.close()
    return MessageResponse(
        message=f"User '{row[0]}' approved with role '{body.role}'."
    )

@router.patch("/users/{user_id}/role", response_model=MessageResponse)
def change_role(
    user_id: int,
    body: ApproveUserRequest,
    current_user: dict = Depends(get_current_user),
):
    require_role(current_user["role"], "systems_manager")
    con = _get_con()

    row = con.execute(
        "SELECT username FROM users WHERE id = ?", [user_id]
    ).fetchone()
    if not row:
        con.close()
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}.")

    con.execute(
        "UPDATE users SET role = ? WHERE id = ?", [body.role, user_id]
    )
    con.close()
    return MessageResponse(
        message=f"Role updated: '{row[0]}' is now '{body.role}'."
    )

@router.get("/users", response_model=list[UserResponse])
def list_all_users(current_user: dict = Depends(get_current_user)):
    require_role(current_user["role"], "systems_manager")
    con  = duckdb.connect(str(_resolve_db()), read_only=True)
    rows = con.execute(
        "SELECT id, username, role, is_approved FROM users ORDER BY id"
    ).fetchall()
    con.close()
    return [UserResponse(id=r[0], username=r[1], role=r[2], is_approved=r[3])
            for r in rows]

@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Form-based login for Swagger UI OAuth2 compatibility.
    Identical logic to /auth/login but accepts form fields.
    """
    con = duckdb.connect(str(_resolve_db()), read_only=True)
    row = con.execute(
        "SELECT id, hashed_pw, role, is_approved FROM users WHERE username = ?",
        [form_data.username],
    ).fetchone()
    con.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    _, hashed_pw, role, is_approved = row

    if not verify_password(form_data.password, hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not is_approved:
        raise HTTPException(status_code=403, detail="Account pending approval.")

    token = create_access_token({
        "sub": form_data.username,
        "role": role,
        "is_approved": is_approved,
    })
    return TokenResponse(access_token=token, role=role, username=form_data.username)

# ── Delete user ───────────────────────────────────────────────────────────────


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    body:    DeleteUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Systems manager deletes a user after re-entering their own password.
    Cannot delete themselves.
    """
    require_role(current_user["role"], "systems_manager")

    con = _get_con()

    # verify sysadmin password
    own = con.execute(
        "SELECT hashed_pw FROM users WHERE username = ?",
        [current_user["sub"]]
    ).fetchone()

    if not own or not verify_password(body.password, own[0]):
        con.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password confirmation failed."
        )

    # prevent self-deletion
    target = con.execute(
        "SELECT username FROM users WHERE id = ?", [user_id]
    ).fetchone()

    if not target:
        con.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user with id {user_id}."
        )

    if target[0] == current_user["sub"]:
        con.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    con.execute("DELETE FROM users WHERE id = ?", [user_id])
    con.close()

    return MessageResponse(message=f"User '{target[0]}' deleted.")

@router.post("/reject/{user_id}", response_model=MessageResponse)
def reject_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Reject and remove a pending (unapproved) registration."""
    require_role(current_user["role"], "systems_manager")

    con = _get_con()
    row = con.execute(
        "SELECT username, is_approved FROM users WHERE id = ?", [user_id]
    ).fetchone()

    if not row:
        con.close()
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}.")

    if row[1]:  # is_approved = True
        con.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot reject an already-approved user. Use delete instead."
        )

    con.execute("DELETE FROM users WHERE id = ?", [user_id])
    con.close()
    return MessageResponse(message=f"Registration for '{row[0]}' rejected and removed.")