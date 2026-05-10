import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta
import duckdb
import os

fake = Faker()
random.seed(42)
np.random.seed(42)

# output paths
DB_FILE  = "data/cybernova_analytics.duckdb"
CSV_FILE = "data/cybernova_iis_logs_messy.csv"

# server constants
SITE_NAME   = "W3SVC1"

SERVER_NAME = "GAB-SRV-WEB01"
SERVER_IP   = "172.16.0.45"
HOST_NAME   = "www.cybernova.co.bw"

# volume target
# sessions. each produces 3–8 requests 
TARGET_SESSIONS = 300_000   

# geography with country-to-service affinity weights
GEOGRAPHY = {
    "Botswana": {
        "cities": ["Gaborone", "Francistown", "Maun", "Kanye", "Lobatse"],
        "service_weights": [0.30, 0.20, 0.25, 0.15, 0.10],  # AI chat dominant
    },
    "South Africa": {
        "cities": ["Johannesburg", "Cape Town", "Durban", "Pretoria"],
        "service_weights": [0.15, 0.35, 0.28, 0.12, 0.10],  # pentest dominant
    },
    "Zimbabwe": {
        "cities": ["Harare", "Bulawayo", "Mutare"],
        "service_weights": [0.20, 0.18, 0.22, 0.25, 0.15],  # schedule demo dominant
    },
    "Zambia": {
        "cities": ["Lusaka", "Ndola", "Kitwe"],
        "service_weights": [0.22, 0.15, 0.20, 0.20, 0.23],
    },
    "Namibia": {
        "cities": ["Windhoek", "Swakopmund", "Walvis Bay"],
        "service_weights": [0.18, 0.22, 0.24, 0.18, 0.18],
    },
}

COUNTRY_VARIANTS = {
    "Botswana":     ["Botswana", "BW", "botswana", "Botswana ", "B.W."],
    "South Africa": ["South Africa", "SA", "ZA", "south africa", "S.Africa"],
    "Zimbabwe":     ["Zimbabwe", "ZW", "zimbabwe", "Zimbabwe "],
    "Zambia":       ["Zambia", "ZM", "zambia"],
    "Namibia":      ["Namibia", "NA", "namibia"],
}

SERVICES = [
    "AI Cyber Assistant",
    "Network Security Audit",
    "Penetration Testing",
    "Schedule Demo",
    "Cyber Awareness Webinar",
]

# sales funnel URI map 
FUNNEL_STAGES = {
    "AI Cyber Assistant":      ["/index.html", "/services.php", "/scheduledemo.php"],
    "Network Security Audit":  ["/index.html", "/services.php", "/scheduledemo.php"],
    "Penetration Testing":     ["/index.html", "/services.php", "/assessment", "/scheduledemo.php"],
    "Schedule Demo":           ["/index.html", "/scheduledemo.php"],
    "Cyber Awareness Webinar": ["/index.html", "/event.php",    "/scheduledemo.php"],
}

# probability of progressing to the next stage (drop-off model)
FUNNEL_DROP_OFF = {
    "AI Cyber Assistant":      [1.0, 0.68, 0.31],
    "Network Security Audit":  [1.0, 0.60, 0.27],
    "Penetration Testing":     [1.0, 0.55, 0.40, 0.24],
    "Schedule Demo":           [1.0, 0.45],
    "Cyber Awareness Webinar": [1.0, 0.70, 0.29],
}

AI_CHAT_PROB_BY_DEPTH = {1: 0.05, 2: 0.18, 3: 0.40, 4: 0.60}

# AI chat engagement conversion boost
# sessions that visit /ai-chat are more likely to convert which is the causal treatment effect
AI_CHAT_CONVERSION_BOOST = 0.20

# bot / scanner URIs
BOT_URIS = ["/.env", "/wp-login.php", "/admin/config.php", "/shell.php"]

# temporal patterns for demand chartt and heatmap
DOW_WEIGHTS = [0.20, 0.22, 0.20, 0.18, 0.12, 0.05, 0.03]  # Mon–Sun


HOUR_WEIGHTS = [
    0.005, 0.003, 0.002, 0.002, 0.003, 0.005,   # 00–05
    0.010, 0.020, 0.040, 0.070, 0.075, 0.070,   # 06–11
    0.060, 0.050, 0.075, 0.075, 0.060, 0.050,   # 12–17
    0.040, 0.030, 0.020, 0.015, 0.010, 0.005,   # 18–23
]

START_DATE = datetime.utcnow() - timedelta(days=90)


def service_trend_multiplier(service: str, day_offset: int) -> float:
    """Simulate realistic 60-day demand trends per service"""
    if service == "AI Cyber Assistant":
        return 0.70 + (day_offset / 59) * 0.60         # growing +60 %
    elif service == "Penetration Testing":
        return 1.20 - (day_offset / 59) * 0.40         # declining −40 %
    elif service == "Cyber Awareness Webinar":
        return 2.50 if 9 <= day_offset <= 12 else 0.25  # webinar event spike
    else:
        return 1.00                                      # stable


def random_timestamp(day_offset: int) -> datetime:
    base = START_DATE + timedelta(days=day_offset)
    hour = random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
    return base.replace(hour=hour, minute=random.randint(0, 59),
                        second=random.randint(0, 59), microsecond=0)


# the core IIS W3C log entry builder
def build_log_entry(
    ts, client_ip, uri, status, time_taken,
    session_id, service_type, funnel_stage,
    country, city, conversion_flag, ai_chat_engaged,
) -> dict:
    return {
        # IIS W3C standard fields
        "date":            ts.strftime("%Y-%m-%d"),
        "time":            ts.strftime("%H:%M:%S"),
        "s-sitename":      SITE_NAME,
        "s-computername":  SERVER_NAME,
        "s-ip":            SERVER_IP,
        "s-port":          random.choice([80, 443]),
        "cs-method":       random.choice(["GET", "POST", "HEAD"]),
        "cs-uri-stem":     uri,
        "cs-uri-query":    "-",
        "c-ip":            client_ip,
        "cs-username":     "-",
        "cs-version":      "HTTP/1.1",
        "cs(User-Agent)":  fake.user_agent().replace(" ", "+"),
        "cs(Referer)":     "-",
        "cs(Cookie)":      "-",
        "cs-host":         HOST_NAME,
        "sc-status":       status,
        "sc-substatus":    0,
        "sc-win32-status": 0 if status < 400 else 2,
        "sc-bytes":        random.randint(200, 5000),
        "cs-bytes":        random.randint(100, 1000),
        "time-taken":      time_taken,
        # geolocation
        "client-country":  country,
        "client-city":     city,
        "client-region":   "Southern Africa",
        # sales intelligence fields (star-schema dimension keys)
        "session_id":      session_id,
        "service_type":    service_type,
        "funnel_stage":    funnel_stage,       # awareness / interest / consideration / conversion
        "conversion_flag": conversion_flag,    # 1 = session reached /scheduledemo.php 200
        "ai_chat_engaged": ai_chat_engaged,    # 1 = session included /ai-chat
        # time dimension keys
        "hour_of_day":     ts.hour,
        "day_of_week":     ts.strftime("%A"),
        "week_number":     ts.isocalendar()[1],
    }


# messiness layer
def apply_messiness(entry: dict) -> dict:
    """Introduce realistic IIS log data quality issues."""
    if random.random() < 0.005:
        entry["c-ip"] = None
    if random.random() < 0.02:
        entry["cs(User-Agent)"] = "-"
    if random.random() < 0.05:
        country = entry["client-country"]
        if country in COUNTRY_VARIANTS:
            entry["client-country"] = random.choice(COUNTRY_VARIANTS[country])
    if random.random() < 0.03:
        entry["cs-method"]    = entry["cs-method"].lower()
        entry["cs-uri-stem"]  = "  " + entry["cs-uri-stem"] + " "
    if random.random() < 0.02:
        entry["sc-bytes"] = f"{entry['sc-bytes']:,}"
    return entry

# session generator
def generate_session(day_offset: int, country: str) -> list:
    """
    Generate a realistic sales session following the CyberNova funnel.
    session_id ties all requests together for funnel reconstruction in EDA.
    """
    geo  = GEOGRAPHY[country]
    city = random.choice(geo["cities"])

    # country-weighted service selection with temporal trend multiplier
    trend_weights = [
        geo["service_weights"][i] * service_trend_multiplier(svc, day_offset)
        for i, svc in enumerate(SERVICES)
    ]
    total = sum(trend_weights)
    trend_weights = [w / total for w in trend_weights]
    service = random.choices(SERVICES, weights=trend_weights, k=1)[0]

    funnel_uris = FUNNEL_STAGES[service]
    drop_offs   = FUNNEL_DROP_OFF[service]
    session_id  = str(uuid.uuid4())
    client_ip   = fake.ipv4()
    ts          = random_timestamp(day_offset)
    entries     = []

    # walk the funnel with drop-off at each stage
    reached_uris = []
    for stage_idx, uri in enumerate(funnel_uris):
        if stage_idx > 0 and random.random() > drop_offs[stage_idx]:
            break
        reached_uris.append((stage_idx, uri))

    funnel_depth    = len(reached_uris)
    ai_chat_prob    = AI_CHAT_PROB_BY_DEPTH.get(funnel_depth, 0.05)
    ai_chat_engaged = int(random.random() < ai_chat_prob)
    converted       = int(reached_uris[-1][1] == "/scheduledemo.php") if reached_uris else 0


    # causal boost
    # AI chat engagement probabilistically pushes non-converted sessions
    # to conversion, this is the treatment effect measured by DoWhy
    if ai_chat_engaged and not converted:
        if random.random() < AI_CHAT_CONVERSION_BOOST:
            converted = 1
            if "/scheduledemo.php" not in [u for _, u in reached_uris]:
                reached_uris.append((len(funnel_uris) - 1, "/scheduledemo.php"))

    stage_labels = ["awareness", "interest", "consideration", "conversion"]

    for stage_idx, uri in reached_uris:
        label      = stage_labels[min(stage_idx, len(stage_labels) - 1)]
        time_taken = random.randint(20, 500)
        # an outlier
        # heavy LLM call on /ai-chat
        if uri == "/ai-chat" and random.random() < 0.02:
            time_taken = random.randint(8000, 30000)

        entry = build_log_entry(
            ts=ts + timedelta(seconds=len(entries) * random.randint(5, 45)),
            client_ip=client_ip, uri=uri, status=200,
            time_taken=time_taken, session_id=session_id,
            service_type=service, funnel_stage=label,
            country=country, city=city,
            conversion_flag=converted, ai_chat_engaged=ai_chat_engaged,
        )
        entry = apply_messiness(entry)
        entries.append(entry)

    return entries

# bot / scanner noise
def generate_bot_burst(day_offset: int) -> list:
    ts        = random_timestamp(day_offset)
    client_ip = fake.ipv4()
    return [
        build_log_entry(
            ts=ts + timedelta(seconds=i), client_ip=client_ip,
            uri=random.choice(BOT_URIS), status=404, time_taken=10,
            session_id="BOT-" + str(uuid.uuid4())[:8],
            service_type="None", funnel_stage="bot",
            country="Unknown", city="Unknown",
            conversion_flag=0, ai_chat_engaged=0,
        )
        for i in range(random.randint(5, 15))
    ]

# generation loop
def generate_dataset(n_sessions: int) -> pd.DataFrame:
    print("CyberNova Sales Intelligence Log Generator")
    print("==========================================")
    print(f"Target sessions : {n_sessions:,}")
    print(f"Date range      : {START_DATE.strftime('%Y-%m-%d')} to today")
    print(f"Countries       : {', '.join(GEOGRAPHY.keys())}\n")

    all_entries      = []
    countries        = list(GEOGRAPHY.keys())
    country_weights  = [0.40, 0.25, 0.15, 0.12, 0.08]

    for session_num in range(n_sessions):
        if session_num % 5000 == 0:
            pct = session_num / n_sessions * 100
            print(f"  Generating... {pct:.0f}%  ({len(all_entries):,} rows so far)")

        day_offset = random.randint(0, 59)

        # around 5 % bot burst instead of a real session
        if random.random() < 0.008:
            all_entries.extend(generate_bot_burst(day_offset))
            continue

        country = random.choices(countries, weights=country_weights, k=1)[0]
        all_entries.extend(generate_session(day_offset, country))

    df = pd.DataFrame(all_entries)

    # unit inconsistency
    # some rows report bytes in KB
    df["sc-bytes-kb"] = df["sc-bytes"].apply(
        lambda x: float(str(x).replace(",", "")) / 1024 if pd.notna(x) else None
    )

    # redirect loop noise 
    redirect_ts = random_timestamp(random.randint(0, 29))
    redirect_rows = [
        build_log_entry(
            ts=redirect_ts, client_ip=fake.ipv4(), uri="/old-home",
            status=301, time_taken=5,
            session_id="REDIRECT-" + str(uuid.uuid4())[:8],
            service_type="None", funnel_stage="redirect",
            country="Unknown", city="Unknown",
            conversion_flag=0, ai_chat_engaged=0,
        )
        for _ in range(10)
    ]
    df = pd.concat([df, pd.DataFrame(redirect_rows)], ignore_index=True)

    # truncated cookie 
    cookie_entry = build_log_entry(
        ts=random_timestamp(5), client_ip=fake.ipv4(), uri="/index.html",
        status=200, time_taken=100,
        session_id="TRUNC-" + str(uuid.uuid4())[:8],
        service_type="None", funnel_stage="awareness",
        country="Botswana", city="Gaborone",
        conversion_flag=0, ai_chat_engaged=0,
    )
    cookie_entry["cs(Cookie)"] = "session=" + ("x" * 4080) + "..."
    df = pd.concat([df, pd.DataFrame([cookie_entry])], ignore_index=True)

    df = df.reset_index(drop=True)

    print(f"\nGeneration complete.")
    print(f"  Total rows      : {len(df):,}")
    print(f"  Sessions        : {df['session_id'].nunique():,}")
    conv_sessions = df[df["conversion_flag"] == 1]["session_id"].nunique()
    ai_sessions   = df[df["ai_chat_engaged"] == 1]["session_id"].nunique()
    bot_rows      = len(df[df["funnel_stage"] == "bot"])
    print(f"  Conversions     : {conv_sessions:,}")
    print(f"  AI chat engaged : {ai_sessions:,}")
    print(f"  Bot rows        : {bot_rows:,}\n")
    return df


# data persitence
def save_to_duckdb_and_csv(df: pd.DataFrame) -> None:
    """
    Persist raw flat file AND a star schema in DuckDB.

    Star schema (Ch. 3 — Dimensional Modelling):
      fact_requests  — one row per HTTP request (grain)
      dim_service    — service catalogue dimension
      dim_time       — date / hour / day-of-week dimension
      dim_geography  — country / city / region dimension
      dim_session    — session-level summary (conversion, ai_chat, funnel depth)
    """
    print(f"Saving CSV     -> {CSV_FILE}")
    df.to_csv(CSV_FILE, index=False)

    print(f"Saving DuckDB  -> {DB_FILE}")
    con = duckdb.connect(DB_FILE)

    con.execute("DROP TABLE IF EXISTS iis_logs")
    con.execute("CREATE TABLE iis_logs AS SELECT * FROM df")

    con.execute("DROP TABLE IF EXISTS dim_service")
    con.execute("""
        CREATE TABLE dim_service AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY service_type) AS service_key,
            service_type,
            CASE service_type
                WHEN 'AI Cyber Assistant'      THEN 'AI & Automation'
                WHEN 'Network Security Audit'  THEN 'Security Assessment'
                WHEN 'Penetration Testing'     THEN 'Security Assessment'
                WHEN 'Schedule Demo'           THEN 'Sales Engagement'
                WHEN 'Cyber Awareness Webinar' THEN 'Education & Events'
                ELSE 'Other'
            END AS service_category
        FROM (SELECT DISTINCT service_type FROM iis_logs WHERE service_type != 'None')
    """)

    con.execute("DROP TABLE IF EXISTS dim_geography")
    con.execute("""
        CREATE TABLE dim_geography AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY "client-country", "client-city") AS geo_key,
            "client-country" AS client_country,
            "client-city"    AS client_city,
            "client-region"
        FROM (
            SELECT DISTINCT "client-country", "client-city", "client-region"
            FROM iis_logs
            WHERE "client-country" NOT IN ('Unknown', 'None')
        )
    """)

    con.execute("DROP TABLE IF EXISTS dim_time")
    con.execute("""
        CREATE TABLE dim_time AS
        SELECT DISTINCT
            date, hour_of_day, day_of_week, week_number,
            CASE WHEN day_of_week IN ('Saturday','Sunday') THEN FALSE ELSE TRUE END AS is_weekday
        FROM iis_logs
    """)

    con.execute("DROP TABLE IF EXISTS dim_session")
    con.execute("""
        CREATE TABLE dim_session AS
        SELECT
            session_id,
            MAX(service_type)    AS service_type,
            MAX(conversion_flag) AS converted,
            MAX(ai_chat_engaged) AS ai_chat_engaged,
            "client-country"     AS country,
            "client-city"        AS city,
            MIN(date)            AS session_date,
            MIN(hour_of_day)     AS session_start_hour,
            COUNT(*)             AS page_hits,
            MAX(CASE funnel_stage
                WHEN 'conversion'    THEN 4
                WHEN 'consideration' THEN 3
                WHEN 'interest'      THEN 2
                WHEN 'awareness'     THEN 1
                ELSE 0 END)         AS max_funnel_depth
        FROM iis_logs
        WHERE funnel_stage NOT IN ('bot', 'redirect', 'None')
        GROUP BY session_id, "client-country", "client-city"
    """)

    con.execute("DROP TABLE IF EXISTS fact_requests")
    con.execute("""
        CREATE TABLE fact_requests AS
        SELECT
            session_id,
            "cs-uri-stem"    AS uri,
            "sc-status"      AS http_status,
            "time-taken"     AS time_taken_ms,
            "sc-bytes"       AS bytes_sent,
            service_type,
            funnel_stage,
            conversion_flag,
            ai_chat_engaged,
            date,
            hour_of_day,
            day_of_week,
            "client-country" AS country,
            "client-city"    AS city
        FROM iis_logs
    """)

    req_count = con.execute("SELECT COUNT(*) FROM fact_requests").fetchone()[0]
    ses_count = con.execute("SELECT COUNT(*) FROM dim_session").fetchone()[0]
    conv_rate = con.execute("""
        SELECT ROUND(AVG(converted) * 100, 2)
        FROM dim_session WHERE service_type != 'None'
    """).fetchone()[0]

    print(f"\nDuckDB Star Schema Summary")
    print(f"  fact_requests rows  : {req_count:,}")
    print(f"  dim_session rows    : {ses_count:,}")
    print(f"  Overall conv. rate  : {conv_rate} %")
    print(f"  Tables: fact_requests, dim_session, dim_service, dim_geography, dim_time")
    con.close()


if __name__ == "__main__":
    df = generate_dataset(TARGET_SESSIONS)
    save_to_duckdb_and_csv(df)
    print("\nDone. Files written:")
    print(f"  {CSV_FILE}  ({os.path.getsize(CSV_FILE) / 1_000_000:.1f} MB)")
    print(f"  {DB_FILE}")