import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from api.auth.rbac         import require_role
from api.deps.current_user import get_current_user
from api.schemas.analytics import FieldReport, UploadResponse
from etl.ingest import ingest
from etl.clean  import build_sessions, build_fact_rows
from etl.loader import load_to_duckdb

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

_DB_PATH_RAW = os.getenv("DB_PATH", "data/cybernova_analytics.duckdb")

router = APIRouter(prefix="/api/system", tags=["Systems Manager"])


def _resolve_db() -> str:
    p = Path(_DB_PATH_RAW)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / p
    return str(p)

@router.post("/upload", response_model=UploadResponse, status_code=200)
async def upload_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Systems manager uploads IIS web server log CSV.
    Runs full ETL pipeline and returns field-level validation feedback.

    REQ-17 — secure upload interface
    REQ-18 — descriptive field-level error feedback
    REQ-25 — DuckDB handles 100k+ rows
    REQ-26 — parse accuracy reported
    """
    require_role(current_user["role"], "systems_manager")

    # validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only CSV files are accepted. "
                   f"Received: '{file.filename}'",
        )

    # write upload to a temp file — ingest() needs a file path
    contents = await file.read()
    with tempfile.NamedTemporaryFile(
        suffix=".csv", delete=False, mode="wb"
    ) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        df_sales, report = ingest(tmp_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV parse error: {str(e)}",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # build session and fact DataFrames
    df_sessions = build_sessions(df_sales)
    df_fact     = build_fact_rows(df_sales)

    # load to DuckDB (full refresh — safe for re-upload)
    counts = load_to_duckdb(
        df_sessions, df_fact,
        db_path=_resolve_db(),
        full_refresh=False
    )

    # build field report for REQ-18
    field_reports = [
        FieldReport(
            field=field,
            status=info["status"],
            null_count=info["null_count"],
        )
        for field, info in report["fields"].items()
    ]

    return UploadResponse(
        raw_rows=report["raw_rows"],
        clean_rows=report["clean_rows"],
        bot_rows=report["bot_rows"],
        invalid_timestamps=report["invalid_timestamps"],
        parse_accuracy_pct=report["parse_accuracy_pct"],
        req26_pass=report["req26_pass"],
        dim_session_rows=counts["dim_session"],
        fact_request_rows=counts["fact_requests"],
        fields=field_reports,
        message=(
            f"Upload successful. {counts['dim_session']:,} sessions loaded. "
            f"Parse accuracy: {report['parse_accuracy_pct']}%."
            if report["req26_pass"]
            else f"Upload completed with warnings. "
                 f"Parse accuracy {report['parse_accuracy_pct']}% "
                 f"is below the 99.9% target. Review field errors above."
        ),
    )