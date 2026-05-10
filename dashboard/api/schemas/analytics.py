from pydantic import BaseModel
from typing import Optional

class DemandTrendRow(BaseModel):
    session_date: str
    service_type: str
    total_sessions: int
    conversions: float
    conv_rate_pct: float

class ConversionKPIRow(BaseModel):
    service_type: str
    total_sessions: int
    conversions: float
    conv_rate_pct: float
    ai_engagement_pct: float

class HeatmapRow(BaseModel):
    day_of_week: str
    hour_of_day: int
    session_count: int

class FunnelRow(BaseModel):
    service_type: str
    funnel_stage: str
    sessions_at_stage: int
    pct_of_entry: float

class AIEngagementRow(BaseModel):
    service_type: str
    session_date: str
    total_sessions: int
    ai_chat_sessions: float
    ai_rate_pct: float
    conversions: float


class SummaryStatsRow(BaseModel):
    service_type: str
    days_observed: int
    mean_daily_sessions: float
    median_daily_sessions: float
    stddev_daily_sessions: float
    min_daily_sessions: int
    max_daily_sessions: int
    cv_pct: float


class AnomalyAlertRow(BaseModel):
    service_type: str
    session_date: str
    daily_sessions: int
    breach_gap: int
    conv_rate_pct: float


class CausalSummaryResponse(BaseModel):
    ate_pp: float
    ci_lower: float
    ci_upper: float
    p_value: float
    placebo_pass: bool
    random_cause_pass: bool
    confidence_label: str      # "High", "Moderate", "Low"
    plain_language: str        # human-readable interpretation


class GeoRow(BaseModel):
    country: str
    service_type: str
    sessions: int
    pct_of_country: float


class FieldReport(BaseModel):
    field: str
    status: str          # "OK" or "HAS_NULLS" or "MISSING_COLUMN"
    null_count: Optional[int]


class UploadResponse(BaseModel):
    raw_rows: int
    clean_rows: int
    bot_rows: int
    invalid_timestamps: int
    parse_accuracy_pct: float
    req26_pass: bool
    dim_session_rows: int
    fact_request_rows: int
    fields: list[FieldReport]
    message: str

class CausalSummaryResponse(BaseModel):
    ate_pp:            float
    ci_lower:          float
    ci_upper:          float
    p_value:           float
    placebo_pass:      bool
    random_cause_pass: bool
    confidence_label:  str
    plain_language:    str
    cached:            bool = False
    cached_at:         str | None = None