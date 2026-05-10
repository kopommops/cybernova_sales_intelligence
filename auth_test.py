import requests

BASE = "http://localhost:8000"
PASS = "PASS"
FAIL = "FAIL"


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status}  {label}" + (f"  [{detail}]" if detail else ""))
    return condition


def post(path, json=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BASE}{path}", json=json, headers=headers)


def get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BASE}{path}", headers=headers)


def patch(path, json=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.patch(f"{BASE}{path}", json=json, headers=headers)

def safe_json(r):
    """Return response JSON dict, or empty dict if body is empty/invalid."""
    try:
        return r.json()
    except Exception:
        return {}

print("\n----------------------------------------------------")
print("  CyberNova Auth Validation")
print("-------------------------------------------------------\n")

# i am seeding a systems manager directly (bootstrap only)
# in production the first systems_manager is seeded via a one-time script.
# here it is inserted directly so i can test approval flows.
print("PRE-STEP — seed systems manager")
import os, duckdb
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from dashboard.api.auth.hashing import hash_password


db_path = Path(__file__).resolve().parent / "data" / "cybernova_analytics.duckdb"
db_path = str(db_path)

con = duckdb.connect(db_path)
con.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username VARCHAR UNIQUE NOT NULL,
        hashed_pw VARCHAR NOT NULL, role VARCHAR NOT NULL,
        is_approved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
# remove leftover test users from previous runs
con.execute("DELETE FROM users WHERE username IN ('sysadmin','alice','bob')")
con.execute(
    "INSERT INTO users (id, username, hashed_pw, role, is_approved) VALUES (?,?,?,?,?)",
    [999, "sysadmin", hash_password("Admin1234!"), "systems_manager", True]
)
con.close()
print("  Seeded: sysadmin / Admin1234! (systems_manager, approved)\n")

print("STEP 1 — Health check")
r = requests.get(f"{BASE}/")
check("API is reachable", r.status_code == 200, safe_json(r).get("status"))

print("\nSTEP 2 — Register new accounts (REQ-03)")
r = post("/auth/register", {"username": "alice", "password": "Password1!"})
check("Register alice → 201", r.status_code == 201, safe_json(r).get("message", r.text))

r = post("/auth/register", {"username": "bob", "password": "Password2!"})
check("Register bob → 201", r.status_code == 201, safe_json(r).get("message", r.text))

r = post("/auth/register", {"username": "alice", "password": "Password1!"})
check("Duplicate username → 409", r.status_code == 409, safe_json(r).get("detail"))

r = post("/auth/register", {"username": "ab", "password": "Password1!"})
check("Short username → 422", r.status_code == 422)

r = post("/auth/register", {"username": "weakpw", "password": "short"})
check("Weak password → 422", r.status_code == 422)

print("\nSTEP 3 — Login before approval (REQ-04)")
r = post("/auth/login", {"username": "alice", "password": "Password1!"})
try:
    detail = safe_json(r).get("detail", "")
except Exception:
    detail = r.text or "(empty body)"
check("Unapproved login → 403", r.status_code == 403, detail)
r = post("/auth/login", {"username": "alice", "password": "Password1!"})
print(f"[DEBUG] status={r.status_code} body={r.text[:120]}")

print("\nSTEP 4 — Systems manager login")
r = post("/auth/login", {"username": "sysadmin", "password": "Admin1234!"})
check("sysadmin login → 200", r.status_code == 200)
sys_token = safe_json(r).get("access_token", "")
check("Token received", bool(sys_token))
check("Role is systems_manager", safe_json(r).get("role") == "systems_manager")

print("\nSTEP 5 — List pending users (REQ-19)")
r = get("/auth/pending", token=sys_token)
check("Pending list → 200", r.status_code == 200)
pending = r.json()
check("alice and bob are pending", len(pending) >= 2,
      f"{[u['username'] for u in pending]}")

alice_id = next((u["id"] for u in pending if u["username"] == "alice"), None)
bob_id   = next((u["id"] for u in pending if u["username"] == "bob"),   None)

print("\nSTEP 6 — Approve users (REQ-19) and assign roles (REQ-20)")
r = post(f"/auth/approve/{alice_id}", {"role": "salesperson"}, token=sys_token)
check("Approve alice as salesperson → 200", r.status_code == 200,
      safe_json(r).get("message"))

r = post(f"/auth/approve/{bob_id}", {"role": "sales_manager"}, token=sys_token)
check("Approve bob as sales_manager → 200", r.status_code == 200,
      safe_json(r).get("message"))

print("\nSTEP 7 — Login after approval (REQ-04)")
r = post("/auth/login", {"username": "alice", "password": "Password1!"})
check("alice login → 200", r.status_code == 200)
alice_token = safe_json(r).get("access_token", "")
check("alice role is salesperson", safe_json(r).get("role") == "salesperson")

r = post("/auth/login", {"username": "bob", "password": "Password2!"})
check("bob login → 200", r.status_code == 200)
bob_token = safe_json(r).get("access_token", "")
check("bob role is sales_manager", safe_json(r).get("role") == "sales_manager")

r = post("/auth/login", {"username": "alice", "password": "WrongPassword!"})
check("Wrong password → 401", r.status_code == 401, safe_json(r).get("detail"))

print("\nSTEP 8 — RBAC enforcement (REQ-02)")
# alice (salesperson) cannot access systems_manager endpoints
r = get("/auth/pending", token=alice_token)
check("salesperson cannot list pending users → 403", r.status_code == 403,
      safe_json(r).get("detail"))

r = post(f"/auth/approve/{bob_id}", {"role": "salesperson"}, token=alice_token)
check("salesperson cannot approve users → 403", r.status_code == 403)

# bob (sales_manager) cannot access systems_manager endpoints
r = get("/auth/pending", token=bob_token)
check("sales_manager cannot list pending users → 403", r.status_code == 403)

# no token at all
r = get("/auth/pending")
check("No token → 401", r.status_code == 401)

print("\nSTEP 9 — Change role (REQ-20)")
r = patch(f"/auth/users/{alice_id}/role", {"role": "sales_manager"}, token=sys_token)
check("Promote alice to sales_manager → 200", r.status_code == 200,
      safe_json(r).get("message"))

print("\nSTEP 10 — List all users")
r = get("/auth/users", token=sys_token)
check("All users list → 200", r.status_code == 200)
users = r.json()
check("At least 3 users present", len(users) >= 3,
      f"{[u['username'] for u in users]}")

print("\n-----------------------------------------------------")
print("  Auth validation complete.")
print("  If all checks pass → Phase 4 (API Routers) is unblocked.")
print("--------------------------------------------------------------\n")