import httpx
from typing import Optional
import io
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT  = 60.0 
CAUSAL_TIMEOUT = 180.0


class APIError(Exception):
    """Raised when the API returns a non-2xx response."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail      = detail
        super().__init__(f"API {status_code}: {detail}")


class APIClient:
    """
    Stateless HTTP client. Instantiated per-request with the
    current user's JWT token from NiceGUI app.storage.user.
    """

    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict | list:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(f"{BASE_URL}{path}",
                           headers=self._headers, params=params or {})
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()

    def _post(self, path: str, body: dict = None) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{BASE_URL}{path}",
                            headers=self._headers, json=body or {})
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()

    def _patch(self, path: str, body: dict = None) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.patch(f"{BASE_URL}{path}",
                             headers=self._headers, json=body or {})
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()

    @staticmethod
    def login(username: str, password: str) -> dict:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                f"{BASE_URL}/auth/login",
                json={"username": username, "password": password},
            )
        if not r.is_success:
            detail = r.json().get("detail", "Login failed") if r.content else "Login failed"
            raise APIError(r.status_code, detail)
        return r.json()   # {access_token, role, username}

    @staticmethod
    def register(username: str, password: str) -> dict:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                f"{BASE_URL}/auth/register",
                json={"username": username, "password": password},
            )
        if not r.is_success:
            detail = r.json().get("detail", "Registration failed") if r.content else "Registration failed"
            raise APIError(r.status_code, detail)
        return r.json()

    def get_demand_trend(self, start: str, end: str) -> list:
        return self._get("/api/analytics/demand-trend",
                         {"start": start, "end": end})

    def get_conversion_kpi(self, start: str, end: str) -> list:
        return self._get("/api/analytics/conversion-kpi",
                         {"start": start, "end": end})

    def get_heatmap(self, start: str, end: str) -> list:
        return self._get("/api/analytics/heatmap",
                         {"start": start, "end": end})

    def get_funnel(self, start: str, end: str) -> list:
        return self._get("/api/analytics/funnel",
                         {"start": start, "end": end})

    def get_ai_engagement(self, start: str, end: str) -> list:
        return self._get("/api/analytics/ai-engagement",
                         {"start": start, "end": end})

    def get_summary_stats(self, start: str, end: str) -> list:
        return self._get("/api/analytics/summary-stats",
                         {"start": start, "end": end})

    def get_anomaly_alerts(self, start: str, end: str,
                       threshold: int = 184) -> list:
        return self._get("/api/analytics/anomaly-alerts",
                        {"start": start, "end": end,
                        "threshold": threshold})

    def get_causal(self, force: bool = False) -> dict:
        with httpx.Client(timeout=CAUSAL_TIMEOUT) as client:
            r = client.get(
                f"{BASE_URL}/api/analytics/causal",
                headers=self._headers,
                params={"force": str(force).lower()},
            )
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()

    def get_geo(self, start: str, end: str) -> list:
        return self._get("/api/analytics/geo",
                         {"start": start, "end": end})

    def get_action_plan(self, start: str, end: str) -> dict:
        return self._get("/api/manager/action-plan",
                         {"start": start, "end": end})

    def send_chat(self, history: list, message: str) -> str:
        result = self._post("/api/manager/chat", {
            "history": history,
            "message": message,
        })
        return result["response"]

    def send_email(self, recipient: str,
                   subject: str, body: str) -> dict:
        return self._post("/api/manager/send-email", {
            "recipient": recipient,
            "subject":   subject,
            "body":      body,
        })

    def get_pdf_url(self, start: str, end: str) -> str:
        """Returns the full URL for the PDF download — opened in browser."""
        token = self._headers["Authorization"].replace("Bearer ", "")
        return (f"{BASE_URL}/api/manager/export-pdf"
                f"?start={start}&end={end}&token={token}")

    def get_pending_users(self) -> list:
        return self._get("/api/auth/pending")

    def get_all_users(self) -> list:
        return self._get("/auth/users")

    def get_pending_users(self) -> list:
        return self._get("/auth/pending")

    def approve_user(self, user_id: int, role: str) -> dict:
        return self._post(f"/auth/approve/{user_id}", {"role": role})

    def change_role(self, user_id: int, role: str) -> dict:
        return self._patch(f"/auth/users/{user_id}/role", {"role": role})

    def upload_csv(self, file_path: str) -> dict:
        """Multipart file upload — uses raw httpx, not _post."""
        with open(file_path, "rb") as f:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{BASE_URL}/api/system/upload",
                    headers={"Authorization": self._headers["Authorization"]},
                    files={"file": (file_path, f, "text/csv")},
                )
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()
    
    def delete_user(self, user_id: int, password: str) -> dict:
        """Systems manager deletes a user after password confirmation."""
        import httpx
        with httpx.Client(timeout=10.0) as client:
            r = client.request(
                "DELETE",
                f"{BASE_URL}/auth/users/{user_id}",
                headers=self._headers,
                json={"password": password},
            )
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()

    def reject_user(self, user_id: int) -> dict:
        """
        Reject a pending user by deleting their account.
        Uses a blank password bypass for pending accounts that have no confirmed password.
        Systems manager provides own password via the UI.
        """
        # rejection is just deletion — reuse delete_user in the UI
        return self._post(f"/auth/reject/{user_id}", {})
    
    def process_and_upload_to_duckdb(self, df: pd.DataFrame) -> dict:
        import httpx
        # Use a BytesIO buffer to stay in RAM
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{BASE_URL}/api/system/upload",
                headers={"Authorization": self._headers["Authorization"]},
                # Pass the buffer directly as the 'file'
                files={"file": ("upload.csv", csv_buffer, "text/csv")},
            )
        
        if not r.is_success:
            detail = r.json().get("detail", r.text) if r.content else r.text
            raise APIError(r.status_code, detail)
        return r.json()