import duckdb
import pandas as pd


def get_ai_engagement(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    result = con.execute(f"""
        SELECT service_type, session_date,
               COUNT(*) AS total_sessions,
               SUM(ai_chat_engaged) AS ai_chat_sessions,
               ROUND(AVG(ai_chat_engaged)*100, 2) AS ai_rate_pct,
               SUM(converted) AS conversions
        FROM dim_session
        WHERE service_type NOT IN ('None')
          AND session_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY service_type, session_date
        ORDER BY session_date, service_type
    """).df()
    con.close()
    return result


def get_summary_statistics(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    result = con.execute(f"""
        SELECT service_type,
               COUNT(DISTINCT session_date) AS days_observed,
               ROUND(AVG(daily_sessions), 2) AS mean_daily_sessions,
               ROUND(MEDIAN(daily_sessions), 2) AS median_daily_sessions,
               ROUND(STDDEV(daily_sessions), 2) AS stddev_daily_sessions,
               MIN(daily_sessions) AS min_daily_sessions,
               MAX(daily_sessions) AS max_daily_sessions,
               ROUND(STDDEV(daily_sessions)/AVG(daily_sessions)*100, 1) AS cv_pct
        FROM (
            SELECT service_type, session_date, COUNT(*) AS daily_sessions
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