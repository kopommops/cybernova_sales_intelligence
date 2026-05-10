import duckdb
import pandas as pd


def get_funnel_stages(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    result = con.execute(f"""
        SELECT f.service_type, f.funnel_stage,
               COUNT(DISTINCT f.session_id) AS sessions_at_stage
        FROM fact_requests f
        WHERE f.service_type NOT IN ('None', 'bot')
          AND f.funnel_stage IN ('awareness','interest','consideration','conversion')
          AND f.date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY f.service_type, f.funnel_stage
        ORDER BY f.service_type,
            CASE f.funnel_stage
                WHEN 'awareness'     THEN 1
                WHEN 'interest'      THEN 2
                WHEN 'consideration' THEN 3
                WHEN 'conversion'    THEN 4
            END
    """).df()
    con.close()

    # adding entry totals and drop-off percentages
    entry_counts = (
        result[result["funnel_stage"] == "awareness"]
        .set_index("service_type")["sessions_at_stage"]
        .to_dict()
    )
    result["pct_of_entry"] = result.apply(
        lambda r: round(
            r["sessions_at_stage"] / entry_counts.get(r["service_type"], 1) * 100, 1
        ), axis=1
    )
    return result