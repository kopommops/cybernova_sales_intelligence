import pandas as pd
import numpy as np
from pathlib import Path

COUNTRY_CANON = {
    "BW": "Botswana",        "botswana": "Botswana",
    "Botswana ": "Botswana", "B.W.": "Botswana",
    "SA": "South Africa",    "ZA": "South Africa",
    "south africa": "South Africa", "S.Africa": "South Africa",
    "ZW": "Zimbabwe",        "zimbabwe": "Zimbabwe",
    "Zimbabwe ": "Zimbabwe",
    "ZM": "Zambia",          "zambia": "Zambia",
    "NA": "Namibia",         "namibia": "Namibia",
}

REQUIRED_FIELDS = [
    "date", "time", "c-ip", "cs-uri-stem", "sc-status",
    "session_id", "service_type", "funnel_stage",
    "conversion_flag", "ai_chat_engaged",
    "client-country", "hour_of_day",
]

FUNNEL_STAGES = {"awareness", "interest", "consideration", "conversion", "bot"}


def ingest(csv_path: str | Path) -> tuple[pd.DataFrame, dict]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, low_memory=False)
    raw_rows = len(df)

    df["timestamp"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        errors="coerce",
    )
    invalid_timestamps = df["timestamp"].isna().sum()
    df = df.dropna(subset=["timestamp"])

    df["client-country"] = df["client-country"].replace(COUNTRY_CANON)

    df["time-taken"] = pd.to_numeric(df["time-taken"], errors="coerce")
    df["sc-bytes"] = df["sc-bytes"].apply(
        lambda x: float(str(x).replace(",", "")) if pd.notna(x) else np.nan
    )

    df["cs-uri-stem"] = df["cs-uri-stem"].str.strip()
    df["cs-method"]   = df["cs-method"].str.upper() if "cs-method" in df.columns else "GET"

    df["c-ip"]            = df["c-ip"].fillna("Unknown")
    df["conversion_flag"] = df["conversion_flag"].fillna(0).astype(int)
    df["ai_chat_engaged"] = df["ai_chat_engaged"].fillna(0).astype(int)

    df_sales = df[
        df["funnel_stage"].isin({"awareness", "interest", "consideration", "conversion"})
    ].copy()
    df_bots  = df[df["funnel_stage"] == "bot"].copy()

    total_cells = len(df_sales) * len(REQUIRED_FIELDS)
    null_cells  = df_sales[
        [f for f in REQUIRED_FIELDS if f in df_sales.columns]
    ].isnull().sum().sum()
    parse_accuracy = round((1 - null_cells / max(total_cells, 1)) * 100, 3)

    field_report = {}
    for col in REQUIRED_FIELDS:
        if col not in df_sales.columns:
            field_report[col] = {"status": "MISSING_COLUMN", "null_count": None}
        else:
            n_null = int(df_sales[col].isnull().sum())
            field_report[col] = {
                "status":     "OK" if n_null == 0 else "HAS_NULLS",
                "null_count": n_null,
            }

    report = {
        "raw_rows":          raw_rows,
        "clean_rows":        len(df_sales),
        "bot_rows":          len(df_bots),
        "invalid_timestamps": int(invalid_timestamps),
        "parse_accuracy_pct": parse_accuracy,
        "req26_pass":        parse_accuracy >= 99.9,
        "fields":            field_report,
    }

    return df_sales, report