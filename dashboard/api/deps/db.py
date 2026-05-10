import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, status

load_dotenv()

_DB_PATH = os.getenv("DB_PATH", "..\\data\\cybernova.duckdb")


def get_db_path() -> str:
    """
    FastAPI dependency. Resolves DB_PATH from .env and confirms
    the file exists before any analytics query runs.

    Usage:
        @router.get("/some-endpoint")
        def endpoint(db: str = Depends(get_db_path)):
            return get_demand_trend(db, start, end)
    """
    path = Path(_DB_PATH)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialised. "
                   "Please ask the systems manager to upload the log data.",
        )
    return str(path)