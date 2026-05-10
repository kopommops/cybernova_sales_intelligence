import duckdb
import pandas as pd

SADC = ["Botswana", "South Africa", "Zimbabwe", "Zambia", "Namibia"]


def get_geo_dominance(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Service share (%) by country — SADC region only."""
    con = duckdb.connect(db_path, read_only=True)
    result = con.execute(f"""
        WITH cleaned AS (
            SELECT
                CASE
                    WHEN country IN ('BW','botswana','Botswana ','B.W.','Botswana')
                        THEN 'Botswana'
                    WHEN country IN ('SA','ZA','south africa','S.Africa','South Africa')
                        THEN 'South Africa'
                    WHEN country IN ('ZW','zimbabwe','Zimbabwe ','Zimbabwe')
                        THEN 'Zimbabwe'
                    WHEN country IN ('ZM','zambia','Zambia')
                        THEN 'Zambia'
                    WHEN country IN ('NA','namibia','Namibia')
                        THEN 'Namibia'
                    ELSE country
                END AS country,
                service_type,
                session_date
            FROM dim_session
            WHERE service_type NOT IN ('None')
              AND session_date BETWEEN '{start_date}' AND '{end_date}'
        )
        SELECT
            country,
            service_type,
            COUNT(*) AS sessions,
            ROUND(
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY country),
            2) AS pct_of_country
        FROM cleaned
        WHERE country IN ('Botswana','South Africa','Zimbabwe','Zambia','Namibia')
        GROUP BY country, service_type
        ORDER BY country, pct_of_country DESC
    """).df()
    con.close()
    return result


def get_geo_pivot(db_path: str, start_date: str, end_date: str) -> pd.DataFrame:
    """geo_dominance pivoted — index=country, columns=service_type."""
    df = get_geo_dominance(db_path, start_date, end_date)
    return (
        df.pivot(index="country", columns="service_type", values="pct_of_country")
        .fillna(0)
        .reindex(SADC)
    )