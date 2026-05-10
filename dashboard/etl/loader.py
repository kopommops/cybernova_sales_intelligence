import duckdb
import pandas as pd
from pathlib import Path


_DDL = """
CREATE TABLE IF NOT EXISTS dim_time (
    date_id     DATE    PRIMARY KEY,
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    week        INTEGER,
    day_of_week VARCHAR,
    is_weekend  BOOLEAN
);

CREATE TABLE IF NOT EXISTS dim_service (
    service_id   INTEGER PRIMARY KEY,
    service_type VARCHAR UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_geography (
    geo_id  INTEGER PRIMARY KEY,
    country VARCHAR NOT NULL,
    city    VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_session (
    session_id          VARCHAR PRIMARY KEY,
    service_type        VARCHAR NOT NULL,
    country             VARCHAR,
    city                VARCHAR,
    session_date        DATE,
    session_start_hour  INTEGER,
    hour_of_day         INTEGER,
    day_of_week         VARCHAR,
    converted           INTEGER DEFAULT 0,
    ai_chat_engaged     INTEGER DEFAULT 0,
    page_hits           INTEGER DEFAULT 1,
    funnel_depth        INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fact_requests (
    request_id      INTEGER PRIMARY KEY,
    session_id      VARCHAR,
    date            DATE,
    service_type    VARCHAR,
    funnel_stage    VARCHAR,
    converted       INTEGER DEFAULT 0,
    ai_chat_engaged INTEGER DEFAULT 0,
    hour_of_day     INTEGER,
    page_hits       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    username    VARCHAR UNIQUE NOT NULL,
    hashed_pw   VARCHAR        NOT NULL,
    role        VARCHAR        NOT NULL,
    is_approved BOOLEAN        DEFAULT FALSE,
    created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);
"""

_DATA_TABLES = [
    "fact_requests", "dim_session",
    "dim_geography", "dim_service", "dim_time",
]


def _build_dim_time(df_sessions: pd.DataFrame) -> pd.DataFrame:
    dates = df_sessions["session_date"].dropna().unique()
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        rows.append({
            "date_id":    d.date(),
            "year":       d.year,
            "quarter":    d.quarter,
            "month":      d.month,
            "week":       int(d.isocalendar().week),
            "day_of_week": d.day_name(),
            "is_weekend": d.dayofweek >= 5,
        })
    return pd.DataFrame(rows).drop_duplicates("date_id")


def _build_dim_service(df_sessions: pd.DataFrame) -> pd.DataFrame:
    services = sorted(df_sessions["service_type"].dropna().unique())
    return pd.DataFrame({
        "service_id":   range(1, len(services) + 1),
        "service_type": services,
    })


def _build_dim_geography(df_sessions: pd.DataFrame) -> pd.DataFrame:
    geo = (
        df_sessions[["country", "city"]]
        .dropna(subset=["country"])
        .drop_duplicates()
        .reset_index(drop=True)
    )
    geo.insert(0, "geo_id", geo.index + 1)
    return geo


def load_to_duckdb(
    df_sessions: pd.DataFrame,
    df_fact:     pd.DataFrame,
    db_path:     str | Path = "data/cybernova.duckdb",
    full_refresh: bool = True,
) -> dict:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    con.execute(_DDL)
    if full_refresh:
        for table in _DATA_TABLES:
            con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(_DDL)  # recreate after drop
    dim_time    = _build_dim_time(df_sessions)
    dim_service = _build_dim_service(df_sessions)
    dim_geo     = _build_dim_geography(df_sessions)

    dim_session_cols = [
        "session_id", "service_type", "country", "city",
        "session_date", "session_start_hour", "hour_of_day",
        "day_of_week", "converted", "ai_chat_engaged",
        "page_hits", "funnel_depth",
    ]
    df_dim_session = df_sessions[dim_session_cols].copy()
    fact_cols = [
        "request_id", "session_id", "date", "service_type",
        "funnel_stage", "converted", "ai_chat_engaged",
        "hour_of_day", "page_hits",
    ]
    df_fact_load = df_fact[fact_cols].copy()
    con.register("_dim_time",    dim_time)
    con.register("_dim_service", dim_service)
    con.register("_dim_geo",     dim_geo)
    con.register("_dim_session", df_dim_session)
    con.register("_fact",        df_fact_load)

    con.execute("INSERT OR IGNORE INTO dim_time SELECT * FROM _dim_time")
    con.execute("INSERT OR IGNORE INTO dim_service SELECT * FROM _dim_service")
    con.execute("INSERT OR IGNORE INTO dim_geography SELECT * FROM _dim_geo")
    con.execute("INSERT OR IGNORE INTO dim_session SELECT * FROM _dim_session")
    con.execute("INSERT OR IGNORE INTO fact_requests SELECT * FROM _fact")

    counts = {}
    for tbl in ["dim_time", "dim_service", "dim_geography",
                "dim_session", "fact_requests", "users"]:
        counts[tbl] = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]

    con.close()
    return counts