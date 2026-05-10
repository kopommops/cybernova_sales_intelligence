import duckdb
import pandas as pd

DEMAND_THRESHOLD = 90

def _get_cols(con, table: str) -> set:
    """Return set of column names for a table."""
    return {r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name = '{table}'"
    ).fetchall()}

def get_db(db_path: str):
    return duckdb.connect(db_path, read_only=True)


def get_demand_trend(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = get_db(db_path)
    result = con.execute(f"""
        SELECT session_date, service_type,
               COUNT(*) AS total_sessions,
               SUM(converted) AS conversions,
               ROUND(AVG(converted)*100, 2) AS conv_rate_pct
        FROM dim_session
        WHERE service_type NOT IN ('None')
          AND session_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY session_date, service_type
        ORDER BY session_date, service_type
    """).df()
    con.close()
    return result


def get_conversion_kpi(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = get_db(db_path)
    result = con.execute(f"""
        SELECT service_type,
               COUNT(*) AS total_sessions,
               SUM(converted) AS conversions,
               ROUND(AVG(converted)*100, 2) AS conv_rate_pct,
               ROUND(AVG(ai_chat_engaged)*100, 2) AS ai_engagement_pct
        FROM dim_session
        WHERE service_type NOT IN ('None')
          AND session_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY service_type
        ORDER BY conv_rate_pct DESC
    """).df()
    con.close()
    return result

def get_engagement_heatmap(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Hour x day session volume heatmap — REQ-07."""
    con = duckdb.connect(db_path, read_only=True)

    # inspect actual columns in dim_session
    cols = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'dim_session'"
    ).fetchall()]

    # resolve hour column name
    if "session_start_hour" in cols:
        hour_col = "session_start_hour"
    elif "hour_of_day" in cols:
        hour_col = "hour_of_day"
    else:
        con.close()
        return pd.DataFrame(columns=["day_of_week", "hour_of_day", "session_count"])

    # resolve day column name
    if "day_of_week" in cols:
        day_col = "day_of_week"
    else:
        # derive from session_date
        day_col = "strftime(session_date, '%A')"

    result = con.execute(f"""
        SELECT
            {day_col}        AS day_of_week,
            {hour_col}       AS hour_of_day,
            COUNT(*)         AS session_count
        FROM dim_session
        WHERE session_date BETWEEN '{start_date}' AND '{end_date}'
          AND {hour_col} IS NOT NULL
        GROUP BY {day_col}, {hour_col}
        ORDER BY {hour_col}
    """).df()
    con.close()
    return result


def get_summary_stats(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = get_db(db_path)
    result = con.execute(f"""
        SELECT service_type,
               COUNT(DISTINCT session_date) AS days_observed,
               ROUND(AVG(daily_sessions), 2) AS mean_daily_sessions,
               ROUND(MEDIAN(daily_sessions), 2) AS median_daily_sessions,
               ROUND(STDDEV(daily_sessions), 2) AS stddev_daily_sessions,
               MIN(daily_sessions) AS min_daily_sessions,
               MAX(daily_sessions) AS max_daily_sessions,
               ROUND(AVG(daily_conv_rate), 2) AS mean_conv_rate_pct
        FROM (
            SELECT service_type, session_date,
                   COUNT(*) AS daily_sessions,
                   ROUND(AVG(converted)*100, 2) AS daily_conv_rate
            FROM dim_session
            WHERE service_type NOT IN ('None')
              AND session_date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY service_type, session_date
        )
        GROUP BY service_type
        ORDER BY mean_daily_sessions DESC
    """).df()
    con.close()
    return result


def get_anomaly_alerts(
    db_path: str, start_date: str, end_date: str,
    threshold: int = DEMAND_THRESHOLD
) -> pd.DataFrame:
    con = get_db(db_path)
    result = con.execute(f"""
        SELECT service_type, session_date, daily_sessions,
               {threshold} - daily_sessions AS breach_gap,
               ROUND(daily_conv_rate, 2) AS conv_rate_pct
        FROM (
            SELECT service_type, session_date,
                   COUNT(*) AS daily_sessions,
                   AVG(converted)*100 AS daily_conv_rate
            FROM dim_session
            WHERE service_type NOT IN ('None')
              AND session_date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY service_type, session_date
        )
        WHERE daily_sessions < {threshold}
        ORDER BY session_date, service_type
    """).df()
    con.close()
    return result