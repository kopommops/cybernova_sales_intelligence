import pandas as pd

STAGE_DEPTH: dict[str, int] = {
    "awareness":     1,
    "interest":      2,
    "consideration": 3,
    "conversion":    4,
}


def build_sessions(df_sales: pd.DataFrame) -> pd.DataFrame:
    df_sessions = (
        df_sales.groupby("session_id")
        .agg(
            service_type       = ("service_type",    "first"),
            country            = ("client-country",  "first"),
            city               = ("client-city",      "first"),
            session_date       = ("date",             "first"),
            session_start_hour = ("hour_of_day",      "first"),
            hour_of_day        = ("hour_of_day",      "first"),
            day_of_week        = ("day_of_week",      "first"),
            converted          = ("conversion_flag",  "max"),
            ai_chat_engaged    = ("ai_chat_engaged",  "max"),
            page_hits          = ("session_id",        "count"),
            funnel_depth       = ("funnel_stage",
                                  lambda s: s.map(STAGE_DEPTH).max()),
        )
        .reset_index()
    )

    df_sessions = df_sessions.dropna(subset=["service_type"]).copy()
    df_sessions["country"] = df_sessions["country"].fillna("Unknown")
    df_sessions["city"]    = df_sessions["city"].fillna("Unknown")

    df_sessions["session_date"] = pd.to_datetime(df_sessions["session_date"])

    df_sessions["funnel_depth"] = (
        df_sessions["funnel_depth"].fillna(1).astype(int)
    )

    df_sessions["is_weekend"] = df_sessions["day_of_week"].isin(
        ["Saturday", "Sunday"]
    ).astype(int)
    df_sessions["day_of_week"] = pd.to_datetime(df_sessions["session_date"]).dt.day_name()

    return df_sessions


def build_fact_rows(df_sales: pd.DataFrame) -> pd.DataFrame:
    fact = df_sales[[
        "session_id", "date", "service_type",
        "funnel_stage", "conversion_flag",
        "ai_chat_engaged", "hour_of_day",
    ]].copy()

    fact = fact.dropna(subset=["service_type"]).copy()

    fact = fact.rename(columns={"conversion_flag": "converted"})
    fact["page_hits"] = 1
    fact["date"]      = pd.to_datetime(fact["date"])

    fact = fact.reset_index(drop=True)
    fact.insert(0, "request_id", fact.index + 1)

    return fact