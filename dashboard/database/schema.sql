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
    converted           INTEGER    DEFAULT 0,
    ai_chat_engaged     INTEGER    DEFAULT 0,
    page_hits           INTEGER    DEFAULT 1,
    funnel_depth        INTEGER    DEFAULT 1
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
    role        VARCHAR        NOT NULL
                CHECK (role IN ('salesperson','sales_manager','systems_manager')),
    is_approved BOOLEAN        DEFAULT FALSE,
    created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);