import os
import uuid
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
from pathlib import Path

fake = Faker()
random.seed(99)
np.random.seed(99)

OUT_DIR = Path("dashboard/data/test")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SITE_NAME   = "W3SVC1"
SERVER_NAME = "GAB-SRV-WEB01"
SERVER_IP   = "172.16.0.45"
HOST_NAME   = "www.cybernova.co.bw"
START_DATE  = datetime(2026, 2, 1)

SERVICES = [
    "AI Cyber Assistant",
    "Network Security Audit",
    "Penetration Testing",
    "Schedule Demo",
    "Cyber Awareness Webinar",
]

COUNTRIES = {
    "Botswana":     ["Gaborone", "Francistown", "Maun"],
    "South Africa": ["Johannesburg", "Cape Town", "Pretoria"],
    "Zimbabwe":     ["Harare", "Bulawayo"],
    "Zambia":       ["Lusaka", "Ndola"],
    "Namibia":      ["Windhoek", "Swakopmund"],
}

FUNNEL_STAGES = ["awareness", "interest", "consideration", "conversion"]

HOUR_WEIGHTS = [
    0.005, 0.003, 0.002, 0.002, 0.003, 0.005,
    0.010, 0.020, 0.040, 0.070, 0.075, 0.070,
    0.060, 0.050, 0.075, 0.075, 0.060, 0.050,
    0.040, 0.030, 0.020, 0.015, 0.010, 0.005,
]

DOW_WEIGHTS = [0.20, 0.22, 0.20, 0.18, 0.12, 0.05, 0.03]

BOT_URIS = ["/.env", "/wp-login.php", "/shell.php"]


def _random_ts(offset_days: int) -> datetime:
    base = START_DATE + timedelta(days=offset_days)
    hour = random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
    return base.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )


def _make_row(
    ts: datetime,
    session_id: str,
    service_type: str,
    funnel_stage: str,
    country: str,
    city: str,
    converted: int,
    ai_chat: int,
) -> dict:
    """Build a single well-formed IIS log row."""
    return {
        "date":            ts.strftime("%Y-%m-%d"),
        "time":            ts.strftime("%H:%M:%S"),
        "s-sitename":      SITE_NAME,
        "s-computername":  SERVER_NAME,
        "s-ip":            SERVER_IP,
        "s-port":          443,
        "cs-method":       random.choice(["GET", "POST"]),
        "cs-uri-stem":     "/index.html",
        "cs-uri-query":    "-",
        "c-ip":            fake.ipv4(),
        "cs-username":     "-",
        "cs-version":      "HTTP/1.1",
        "cs(User-Agent)":  fake.user_agent(),
        "cs(Referer)":     "-",
        "cs(Cookie)":      "-",
        "cs-host":         HOST_NAME,
        "sc-status":       200,
        "sc-substatus":    0,
        "sc-win32-status": 0,
        "sc-bytes":        random.randint(200, 5000),
        "cs-bytes":        random.randint(100, 1000),
        "time-taken":      random.randint(20, 500),
        "client-country":  country,
        "client-city":     city,
        "client-region":   "Southern Africa",
        "session_id":      session_id,
        "service_type":    service_type,
        "funnel_stage":    funnel_stage,
        "conversion_flag": converted,
        "ai_chat_engaged": ai_chat,
        "hour_of_day":     ts.hour,
        "day_of_week":     ts.strftime("%A"),
        "week_number":     ts.isocalendar()[1],
    }


def _generate_clean_session(day_offset: int) -> list[dict]:
    """One clean, valid session through the funnel."""
    country = random.choice(list(COUNTRIES.keys()))
    city    = random.choice(COUNTRIES[country])
    svc     = random.choice(SERVICES)
    sid     = str(uuid.uuid4())
    ts      = _random_ts(day_offset)
    depth   = random.randint(1, 4)
    stages  = FUNNEL_STAGES[:depth]
    ai      = int(random.random() < 0.18)
    conv    = int(depth == 4 or (ai and random.random() < 0.20))
    rows    = []
    for i, stage in enumerate(stages):
        rows.append(_make_row(
            ts=ts + timedelta(seconds=i * random.randint(5, 45)),
            session_id=sid, service_type=svc,
            funnel_stage=stage, country=country, city=city,
            converted=conv, ai_chat=ai,
        ))
    return rows


def generate_pass_dataset(n_sessions: int = 10_000) -> pd.DataFrame:
    print(f"\n[PASS] Generating {n_sessions:,} clean sessions...")
    rows = []

    for s in range(n_sessions):
        day = random.randint(0, 59)
        rows.extend(_generate_clean_session(day))

        if random.random() < 0.008:
            ts = _random_ts(day)
            for i in range(random.randint(3, 8)):
                rows.append({
                    **_make_row(
                        ts=ts + timedelta(seconds=i),
                        session_id="BOT-" + str(uuid.uuid4())[:8],
                        service_type="None",
                        funnel_stage="bot",
                        country="Unknown", city="Unknown",
                        converted=0, ai_chat=0,
                    )
                })

    df = pd.DataFrame(rows).reset_index(drop=True)

    country_variants = {
        "Botswana":     ["BW", "botswana", "B.W."],
        "South Africa": ["SA", "ZA", "S.Africa"],
        "Zimbabwe":     ["ZW", "zimbabwe"],
        "Zambia":       ["ZM", "zambia"],
        "Namibia":      ["NA", "namibia"],
    }
    mask = np.random.random(len(df)) < 0.05
    for idx in df[mask].index:
        c = df.at[idx, "client-country"]
        if c in country_variants:
            df.at[idx, "client-country"] = random.choice(country_variants[c])

    # 2% lowercase cs-method
    mask2 = np.random.random(len(df)) < 0.02
    df.loc[mask2, "cs-method"] = df.loc[mask2, "cs-method"].str.lower()

    # FIX: Cast sc-bytes to object before inserting formatted strings (e.g. "1,234")
    df["sc-bytes"] = df["sc-bytes"].astype(object)
    mask3 = np.random.random(len(df)) < 0.02
    df.loc[mask3, "sc-bytes"] = df.loc[mask3, "sc-bytes"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else x
    )

    mask4 = np.random.random(len(df)) < 0.005
    df.loc[mask4, "c-ip"] = None

    print(f"  Rows generated  : {len(df):,}")
    print(f"  Sessions        : {df['session_id'].nunique():,}")
    print(f"  Columns         : {list(df.columns)}")
    return df


def generate_fail_dataset(n_rows: int = 5_000) -> pd.DataFrame:
    print(f"\n[FAIL] Generating {n_rows:,} deliberately broken rows...")

    rows = []
    for _ in range(n_rows):
        day = random.randint(0, 59)
        rows.extend(_generate_clean_session(day))
        if len(rows) >= n_rows:
            break
    df = pd.DataFrame(rows[:n_rows]).reset_index(drop=True)

    print(f"  Base rows: {len(df):,}  — now applying {8} failure modes...")

    df = df.drop(columns=["session_id"])
    print("  F1: Dropped 'session_id' column")

    df = df.drop(columns=["hour_of_day"])
    print("  F2: Dropped 'hour_of_day' column")

    corrupt_mask = np.random.random(len(df)) < 0.40
    df.loc[corrupt_mask, "date"] = "not-a-date"
    df.loc[corrupt_mask, "time"] = "99:99:99"
    n_corrupt = corrupt_mask.sum()
    print(f"  F3: Corrupted {n_corrupt:,} timestamps ({n_corrupt/len(df)*100:.0f}%)")

    svc_mask = np.random.random(len(df)) < 0.30
    df.loc[svc_mask, "service_type"] = np.nan
    print(f"  F4: Blanked service_type in {svc_mask.sum():,} rows")

    # FIX: Cast conversion_flag to object before injecting strings like "maybe"
    df["conversion_flag"] = df["conversion_flag"].astype(object)
    conv_mask = np.random.random(len(df)) < 0.25
    df.loc[conv_mask, "conversion_flag"] = random.choices(
        ["yes", "no", "maybe", "TRUE", "NULL"], k=conv_mask.sum()
    )
    print(f"  F5: Injected string conversion_flag in {conv_mask.sum():,} rows")

    stage_mask = np.random.random(len(df)) < 0.35
    df.loc[stage_mask, "funnel_stage"] = random.choices(
        ["bounced", "exit", "unknown", None, "404"], k=stage_mask.sum()
    )
    print(f"  F6: Injected invalid funnel_stage in {stage_mask.sum():,} rows")

    # FIX: Cast sc-bytes to object before injecting strings like "???"
    df["sc-bytes"] = df["sc-bytes"].astype(object)
    bytes_mask = np.random.random(len(df)) < 0.20
    df.loc[bytes_mask, "sc-bytes"] = random.choices(
        ["N/A", "??", "error", "--", ""], k=bytes_mask.sum()
    )
    print(f"  F7: Garbage sc-bytes in {bytes_mask.sum():,} rows")

    df["client-country"] = np.nan
    print("  F8: Wiped entire client-country column")

    print(f"\n  Final rows : {len(df):,}")
    print(f"  Columns    : {list(df.columns)}")
    return df


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("CyberNova Test Dataset Generator")
    print("----------------------------------------------------------------------")
    print(f"Output directory: {OUT_DIR.resolve()}\n")

    df_pass = generate_pass_dataset(n_sessions=5_000)
    pass_path = OUT_DIR / "cybernova_PASS.csv"
    df_pass.to_csv(pass_path, index=False)
    size_mb = pass_path.stat().st_size / 1_000_000
    print(f"\n  Saved: {pass_path}  ({size_mb:.1f} MB)")

    df_fail = generate_fail_dataset(n_rows=2_000)
    fail_path = OUT_DIR / "cybernova_FAIL.csv"
    df_fail.to_csv(fail_path, index=False)
    size_mb = fail_path.stat().st_size / 1_000_000
    print(f"  Saved: {fail_path}  ({size_mb:.1f} MB)")

    print("\n--------------------------------------------------------------------")
    print("What to test in the UI:")
    print("")
    print("  PASS — cybernova_PASS.csv")
    print("    Expected: green upload banner, parse accuracy >= 99.9%,")
    print("    all field statuses OK or HAS_NULLS (c-ip only),")
    print("    session and fact rows loaded successfully.")
    print("")
    print("  FAIL — cybernova_FAIL.csv")
    print("    Expected: field validation report shows MISSING_COLUMN")
    print("    for session_id and hour_of_day, HAS_NULLS on client-country,")
    print("    parse accuracy well below 99.9%, orange warning banner,")
    print("    ingest completes with warnings (does not crash).")
    print("-----------------------------------------------------------------------")