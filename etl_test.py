import sys
from pathlib import Path

RAW_CSV = Path("data\\cybernova_iis_logs_messy.csv")
DB_PATH = Path("data\\cybernova_analytics.duckdb")

sys.path.insert(0, str(Path(__file__).parent / "dashboard"))

from dashboard.etl.ingest import ingest
from dashboard.etl.clean  import build_sessions, build_fact_rows
from dashboard.etl.loader import load_to_duckdb

from dashboard.analytics.kpis         import get_demand_trend, get_conversion_kpi, \
                                    get_engagement_heatmap, get_anomaly_alerts
from dashboard.analytics.funnel       import get_funnel_stages
from dashboard.analytics.summary_stats import get_ai_engagement, get_summary_statistics
from dashboard.analytics.geo          import get_geo_dominance

PASS = "PASS"
FAIL = "FAIL"

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    print(f"  {status}  {label}" + (f"  [{detail}]" if detail else ""))
    return condition


print("\n---------------------------------------------------")
print("  CyberNova ETL Validation")
print("--------------------------------------------------\n")

print("STEP 1 — ingest()")
df_sales, report = ingest(RAW_CSV)

check("Raw rows > 0",
      report["raw_rows"] > 0,
      f"{report['raw_rows']:,} raw rows")

check("Clean sales rows > 100,000",
      report["clean_rows"] > 100_000,
      f"{report['clean_rows']:,} clean rows")

check("REQ-26: parse accuracy ≥ 99.9%",
      report["req26_pass"],
      f"{report['parse_accuracy_pct']}%")

check("No MISSING_COLUMN errors",
      all(v["status"] != "MISSING_COLUMN" for v in report["fields"].values()))

print(f"\n  Field-level report:")
for field, info in report["fields"].items():
    status_sym = "Y" if info["status"] == "OK" else "⚠️ "
    print(f"    {status_sym}  {field}: {info['status']}  "
          f"(nulls: {info['null_count']})")

print("\nSTEP 2 — build_sessions()")
df_sessions = build_sessions(df_sales)

check("Session rows > 100,000",
      len(df_sessions) > 100_000,
      f"{len(df_sessions):,} sessions")

required_session_cols = [
    "session_id", "service_type", "country", "city",
    "session_date", "session_start_hour", "hour_of_day",
    "day_of_week", "converted", "ai_chat_engaged",
    "page_hits", "funnel_depth",
]
missing_cols = [c for c in required_session_cols if c not in df_sessions.columns]
check("All dim_session columns present",
      len(missing_cols) == 0,
      f"missing: {missing_cols}" if missing_cols else "all present")

check("No null session_ids",
      df_sessions["session_id"].notna().all())

check("converted values are 0 or 1",
      df_sessions["converted"].isin([0, 1]).all())

check("ai_chat_engaged values are 0 or 1",
      df_sessions["ai_chat_engaged"].isin([0, 1]).all())

check("funnel_depth range 1–4",
      df_sessions["funnel_depth"].between(1, 4).all())

check("session_start_hour == hour_of_day (same values)",
      (df_sessions["session_start_hour"] == df_sessions["hour_of_day"]).all())

print(f"\n  Services found: {sorted(df_sessions['service_type'].dropna().unique())}")
print(f"  Countries found: {sorted(df_sessions['country'].dropna().unique())}")
print(f"  Date range: {df_sessions['session_date'].min()} → "
      f"{df_sessions['session_date'].max()}")

print("\nSTEP 3 — build_fact_rows()")
df_fact = build_fact_rows(df_sales)

check("Fact rows > session rows (multiple requests per session)",
      len(df_fact) > len(df_sessions),
      f"{len(df_fact):,} fact rows")

check("All 4 funnel stages present in fact_requests",
      set(df_fact["funnel_stage"].unique()) >=
      {"awareness", "interest", "consideration", "conversion"})

check("request_id is unique",
      df_fact["request_id"].nunique() == len(df_fact))

print("\nSTEP 4 — load_to_duckdb()")
DB_PATH.unlink(missing_ok=True)  # clean slate for test

counts = load_to_duckdb(df_sessions, df_fact, db_path=DB_PATH)

check("dim_session loaded",
      counts["dim_session"] > 0,
      f"{counts['dim_session']:,} rows")

check("fact_requests loaded",
      counts["fact_requests"] > 0,
      f"{counts['fact_requests']:,} rows")

check("dim_time loaded",
      counts["dim_time"] > 0,
      f"{counts['dim_time']:,} rows")

check("dim_service loaded",
      counts["dim_service"] > 0,
      f"{counts['dim_service']:,} rows")

check("dim_geography loaded",
      counts["dim_geography"] > 0,
      f"{counts['dim_geography']:,} rows")

check("users table exists (empty)",
      counts["users"] == 0,
      "no users yet — correct")
print("\nSTEP 5 — analytics smoke tests against live DuckDB")
db = str(DB_PATH)
start, end = "2026-03-01", "2026-04-30"

try:
    df_trend = get_demand_trend(db, start, end)
    check("get_demand_trend() returns rows",
          len(df_trend) > 0, f"{len(df_trend)} rows")
except Exception as e:
    check("get_demand_trend()", False, str(e))

try:
    df_kpi = get_conversion_kpi(db, start, end)
    check("get_conversion_kpi() returns rows",
          len(df_kpi) > 0, f"{len(df_kpi)} rows")
except Exception as e:
    check("get_conversion_kpi()", False, str(e))

try:
    df_heat = get_engagement_heatmap(db, start, end)
    check("get_engagement_heatmap() returns rows",
          len(df_heat) > 0, f"{len(df_heat)} rows")
    check("heatmap has hour_of_day column",
          "hour_of_day" in df_heat.columns)
except Exception as e:
    check("get_engagement_heatmap()", False, str(e))

try:
    df_funnel = get_funnel_stages(db, start, end)
    check("get_funnel_stages() returns rows",
          len(df_funnel) > 0, f"{len(df_funnel)} rows")
    stages_found = set(df_funnel["funnel_stage"].unique())
    check("funnel has conversion stage",
          "conversion" in stages_found,
          f"stages: {stages_found}")
except Exception as e:
    check("get_funnel_stages()", False, str(e))

try:
    df_ai = get_ai_engagement(db, start, end)
    check("get_ai_engagement() returns rows",
          len(df_ai) > 0, f"{len(df_ai)} rows")
except Exception as e:
    check("get_ai_engagement()", False, str(e))

try:
    df_stats = get_summary_statistics(db, start, end)
    check("get_summary_statistics() returns rows",
          len(df_stats) > 0, f"{len(df_stats)} rows")
except Exception as e:
    check("get_summary_statistics()", False, str(e))

try:
    df_alerts = get_anomaly_alerts(db, start, end, threshold=90)
    check("get_anomaly_alerts() runs without error",
          True, f"{len(df_alerts)} breach rows")
except Exception as e:
    check("get_anomaly_alerts()", False, str(e))

try:
    df_geo = get_geo_dominance(db, start, end)
    check("get_geo_dominance() returns rows",
          len(df_geo) > 0, f"{len(df_geo)} rows")
    check("SADC countries present",
          {"Botswana", "South Africa"}.issubset(set(df_geo["country"].unique())))
except Exception as e:
    check("get_geo_dominance()", False, str(e))
print("\n-------------------------------------------------------------------")

print("  ETL validation complete.")
print(f"  Test DB written to: {DB_PATH.resolve()}")
print("  If all checks pass, rename/copy to data/cybernova.duckdb")
print("  and proceed to Phase 3 — Auth.")
print("------------------------------------------------------------------\n")