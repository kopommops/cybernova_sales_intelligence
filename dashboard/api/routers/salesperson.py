import os
from pathlib import Path
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query

from api.auth.rbac         import require_role
from api.deps.current_user import get_current_user
from api.deps.db           import get_db_path
from api.schemas.analytics import (
    AIEngagementRow, AnomalyAlertRow, CausalSummaryResponse,
    ConversionKPIRow, DemandTrendRow, FunnelRow,
    GeoRow, HeatmapRow, SummaryStatsRow,
)
from analytics.kpis          import (get_anomaly_alerts, get_conversion_kpi,
                                     get_demand_trend, get_engagement_heatmap)
from analytics.funnel        import get_funnel_stages
from analytics.summary_stats import get_ai_engagement, get_summary_statistics
from analytics.geo           import get_geo_dominance
from analytics.causal        import get_causal_summary

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

DEMAND_THRESHOLD = int(os.getenv("DEMAND_THRESHOLD", "90"))

router = APIRouter(prefix="/api/analytics", tags=["Salesperson Analytics"])

_DEFAULT_START = "2026-03-01"
_DEFAULT_END   = "2026-05-02"

from fastapi import HTTPException

# wrap get_engagement_heatmap call:
@router.get("/heatmap", response_model=list[HeatmapRow])
def engagement_heatmap(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    try:
        df = get_engagement_heatmap(db, start, end)
        return _df_to_records(df)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Heatmap query failed: {str(e)}"
        )

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    import datetime
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, (pd.Timestamp, datetime.date, datetime.datetime)):
                clean[k] = v.strftime("%Y-%m-%d")
            elif pd.isna(v) if not isinstance(v, (str, list, dict)) else False:
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    return records

def _guard(current_user: dict, minimum: str = "salesperson") -> None:
    require_role(current_user["role"], minimum)

@router.get("/demand-trend", response_model=list[DemandTrendRow])
def demand_trend(
    start: str = Query(default=_DEFAULT_START, description="YYYY-MM-DD"),
    end:   str = Query(default=_DEFAULT_END,   description="YYYY-MM-DD"),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_demand_trend(db, start, end)
    return _df_to_records(df)

@router.get("/conversion-kpi", response_model=list[ConversionKPIRow])
def conversion_kpi(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_conversion_kpi(db, start, end)
    return _df_to_records(df)

@router.get("/heatmap", response_model=list[HeatmapRow])
def engagement_heatmap(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_engagement_heatmap(db, start, end)
    return _df_to_records(df)


@router.get("/funnel", response_model=list[FunnelRow])
def conversion_funnel(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_funnel_stages(db, start, end)
    return _df_to_records(df)


@router.get("/ai-engagement", response_model=list[AIEngagementRow])
def ai_engagement(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_ai_engagement(db, start, end)
    return _df_to_records(df)


@router.get("/summary-stats", response_model=list[SummaryStatsRow])
def summary_stats(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_summary_statistics(db, start, end)
    return _df_to_records(df)

@router.get("/causal", response_model=CausalSummaryResponse)
def causal_analysis(
    force: bool = Query(default=False,
                        description="Force recompute even if cached"),
    db: str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    try:
        summary = get_causal_summary(db, force_recompute=force)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomaly-alerts", response_model=list[AnomalyAlertRow])
def anomaly_alerts(
    start:     str = Query(default=_DEFAULT_START),
    end:       str = Query(default=_DEFAULT_END),
    threshold: int = Query(default=DEMAND_THRESHOLD,
                           description="Daily session count below which an alert fires"),
    db:        str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_anomaly_alerts(db, start, end, threshold=threshold)
    return _df_to_records(df)


@router.get("/geo", response_model=list[GeoRow])
def geo_dominance(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    _guard(current_user)
    df = get_geo_dominance(db, start, end)
    return _df_to_records(df)