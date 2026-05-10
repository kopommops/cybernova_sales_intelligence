"""
frontend/pages/salesperson_dashboard.py
----------------------------------------
Salesperson dashboard - REQ-05 through REQ-12.
Zero ui.timer calls. Compact date inputs. Help panel above filter row.
"""

import os
import pandas as pd
import plotly.graph_objects as go
from nicegui import app, ui

from api_client import APIClient, APIError
from components.layout import build_layout
from theme import (
    BLUE, GREEN, ORANGE, PALETTE,
    PURPLE, RED, TEXT_HEADING, TEXT_MUTED, TEXT_PRIMARY, YELLOW,
)

_START    = "2026-02-06"
_END      = "2026-04-06"
_THRESHOLD = int(os.getenv("DEMAND_THRESHOLD", "184"))
_SERVICES = [
    "AI Cyber Assistant",
    "Cyber Awareness Webinar",
    "Network Security Audit",
    "Penetration Testing",
    "Schedule Demo",
]

_GLASS = (
    "background:rgba(22,27,34,0.65);"
    "backdrop-filter:blur(18px) saturate(140%);"
    "-webkit-backdrop-filter:blur(18px) saturate(140%);"
    "border:1px solid rgba(255,255,255,0.07);"
    "border-radius:12px;"
    "box-shadow:0 4px 24px rgba(0,0,0,0.35),"
    "inset 0 1px 0 rgba(255,255,255,0.05)"
)


def render():
    token = app.storage.user.get("token", "")
    api   = APIClient(token)

    alerts = []
    try:
        alerts = api.get_anomaly_alerts(_START, _END)
    except Exception:
        pass

    panels, tabs, bell_content = build_layout(
        default_tab="overview",
        alert_count=len(alerts)
    )

    try:
        if alerts:
            with bell_content:
                for a in alerts[:10]:
                    with ui.element("div").style(
                        "padding:10px 16px;"
                        "border-bottom:1px solid rgba(48,54,61,0.4);"
                        "display:flex;flex-direction:column;gap:2px"
                    ):
                        ui.label(a["service_type"]).style(
                            f"font-size:12px;font-weight:600;color:{RED}"
                        )
                        ui.label(
                            f"{str(a['session_date'])[:10]}  "
                            f"{a['daily_sessions']} sessions "
                            f"(gap: {a['breach_gap']})"
                        ).style(f"font-size:11px;color:{TEXT_MUTED}")
                if len(alerts) > 10:
                    ui.label(
                        f"... and {len(alerts)-10} more breach days"
                    ).style(
                        f"font-size:11px;color:{TEXT_MUTED};"
                        "padding:8px 16px;font-style:italic"
                    )
    except Exception:
        pass

    app.storage.user["sp_loaded_tabs"] = {}

    with panels:

        # ══ OVERVIEW ══════════════════════════════════════════════════════════
        with ui.tab_panel("overview").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            # anomaly banner
            if alerts:
                with ui.row().classes("items-center").style(
                    "background:rgba(247,129,102,0.08);"
                    f"border:1px solid rgba(247,129,102,0.4);"
                    "border-radius:10px;padding:12px 16px;"
                    "gap:10px;width:100%;margin-bottom:16px"
                ):
                    ui.icon("warning_amber").style(
                        f"color:{RED};font-size:20px;flex-shrink:0"
                    )
                    ui.label(
                        f"{len(alerts)} demand breach alert(s) active - "
                        f"Cyber Awareness Webinar is below the "
                        f"{_THRESHOLD}-session daily threshold."
                    ).style(f"color:{RED};font-size:13px;font-weight:500")

            _section("Conversion KPIs by Service", "credit_card")

            @ui.refreshable
            def kpi_content():
                try:
                    kpis = api.get_conversion_kpi(_START, _END)
                    with ui.row().style("gap:12px;flex-wrap:wrap;width:100%"):
                        for k in kpis:
                            _kpi_card(k, api=api, start=_START, end=_END)
                except Exception as e:
                    _err(str(e))

            kpi_content()

        # ══ DEMAND ════════════════════════════════════════════════════════════
        with ui.tab_panel("demand").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Service Demand Trends", "bar_chart")
            _demand_tab(api)

        # ══ HEATMAP ═══════════════════════════════════════════════════════════
        with ui.tab_panel("heatmap").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Request Volume Heatmap - Hour x Day", "grid_on")

            @ui.refreshable
            def heatmap_content():
                try:
                    df = pd.DataFrame(api.get_heatmap(_START, _END))
                    if df.empty:
                        _err("No heatmap data available for this period.")
                        return
                    day_order = ["Monday","Tuesday","Wednesday",
                                 "Thursday","Friday","Saturday","Sunday"]
                    pivot = df.pivot_table(
                        index="day_of_week", columns="hour_of_day",
                        values="session_count", aggfunc="sum", fill_value=0,
                    ).reindex(
                        [d for d in day_order if d in df["day_of_week"].unique()]
                    )
                    fig = go.Figure(go.Heatmap(
                        z=pivot.values.tolist(),
                        x=[f"{h}:00" for h in pivot.columns],
                        y=list(pivot.index),
                        colorscale="Blues",
                        hovertemplate=(
                            "Day: %{y}<br>Hour: %{x}<br>"
                            "Sessions: %{z:,}<extra></extra>"
                        ),
                    ))
                    _dark_layout(fig, "")
                    fig.update_layout(
                        height=340, margin=dict(l=8, r=8, t=8, b=8)
                    )
                    with ui.element("div").style(
                        f"{_GLASS};padding:20px;width:100%"
                    ):
                        ui.plotly(fig).style("width:100%;height:340px").props(
                            'config=\'{"responsive":true}\''
                        )
                        ui.label(
                            f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}"
                        ).style(
                            f"font-size:10px;color:{TEXT_MUTED};"
                            "text-align:right;width:100%"
                        )

                    peak = (
                        df.sort_values("session_count", ascending=False)
                        .head(5)
                        .reset_index(drop=True)
                    )

                    with ui.element("div").style(
                        f"{_GLASS};padding:20px;width:100%;margin-top:16px;"
                        "display:flex;flex-direction:column;gap:12px"
                    ):
                        with ui.row().classes("items-center").style(
                            "gap:8px;margin-bottom:4px"
                        ):
                            ui.icon("workspace_premium").style(
                                f"color:{YELLOW};font-size:18px"
                            )
                            ui.label("Top 5 Peak Engagement Windows").style(
                                f"font-size:14px;font-weight:600;color:{TEXT_HEADING}"
                            )
                        ui.label(
                            "Highest session volumes by day and hour - "
                            "prioritise outreach in these windows."
                        ).style(f"font-size:12px;color:{TEXT_MUTED};margin-bottom:4px")

                        for i, row in peak.iterrows():
                            bar_pct = int(
                                (row["session_count"] / peak["session_count"].max()) * 100
                            )
                            with ui.element("div").style(
                                "background:rgba(13,17,23,0.5);"
                                "border:1px solid rgba(255,255,255,0.06);"
                                "border-radius:8px;padding:12px 16px;"
                                "display:flex;align-items:center;gap:16px"
                            ):
                                badge_colour = [
                                    "#FFD700","#C0C0C0","#CD7F32",BLUE,BLUE
                                ][i]
                                ui.html(
                                    f'<div style="width:24px;height:24px;'
                                    f'border-radius:50%;background:{badge_colour};'
                                    f'color:#0D1117;display:flex;align-items:center;'
                                    f'justify-content:center;font-size:11px;'
                                    f'font-weight:700;flex-shrink:0">#{i+1}</div>'
                                )
                                with ui.column().style("gap:1px;min-width:160px"):
                                    ui.label(
                                        f"{row['day_of_week']}  {row['hour_of_day']}:00"
                                    ).style(
                                        f"font-size:13px;font-weight:600;color:{TEXT_PRIMARY}"
                                    )
                                    ui.label("Peak engagement window").style(
                                        f"font-size:10px;color:{TEXT_MUTED}"
                                    )
                                with ui.element("div").style(
                                    "flex:1;background:rgba(48,54,61,0.5);"
                                    "border-radius:4px;height:6px;min-width:80px"
                                ):
                                    ui.element("div").style(
                                        f"width:{bar_pct}%;height:100%;"
                                        f"background:linear-gradient(90deg,{BLUE},{PURPLE});"
                                        "border-radius:4px;"
                                        "transition:width 0.4s ease"
                                    )
                                ui.label(f"{row['session_count']:,}").style(
                                    f"font-size:14px;font-weight:700;color:{BLUE};"
                                    "white-space:nowrap"
                                )
                                ui.label("sessions").style(
                                    f"font-size:10px;color:{TEXT_MUTED};white-space:nowrap"
                                )
                except Exception as e:
                    _err(str(e))

            heatmap_content()

        # ══ FUNNEL ════════════════════════════════════════════════════════════
        with ui.tab_panel("funnel").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Conversion Funnel by Service", "filter_alt")
            _help_panel(
                "Each funnel shows how sessions progress through the CyberNova sales journey: "
                "Awareness (first contact) → Interest (product page views) → "
                "Consideration (pricing/demo page) → Conversion (demo booked). "
                "The percentage shown is relative to the Awareness stage entry count."
            )

            @ui.refreshable
            def funnel_content():
                try:
                    df = pd.DataFrame(api.get_funnel(_START, _END))
                    if df.empty:
                        _err("No funnel data for this period.")
                        return
                    stage_order = ["awareness","interest",
                                   "consideration","conversion"]
                    with ui.row().style("gap:12px;width:100%;flex-wrap:wrap"):
                        for svc in df["service_type"].unique():
                            sdf = df[df["service_type"]==svc].copy()
                            sdf["funnel_stage"] = pd.Categorical(
                                sdf["funnel_stage"],
                                categories=stage_order, ordered=True
                            )
                            sdf = sdf.sort_values("funnel_stage")
                            fig = go.Figure(go.Funnel(
                                y=sdf["funnel_stage"].str.capitalize(),
                                x=sdf["sessions_at_stage"],
                                textposition="inside",
                                textinfo="value+percent initial",
                                marker_color=PALETTE[:len(sdf)],
                            ))
                            _dark_layout(fig, svc)
                            fig.update_layout(
                                height=260,
                                margin=dict(l=4,r=4,t=36,b=4)
                            )
                            with ui.element("div").style(
                                f"{_GLASS};padding:10px;flex:1;min-width:180px;"
                                "max-width:calc(25% - 9px)"
                            ):
                                ui.plotly(fig).style(
                                    "width:100%;height:260px"
                                ).props('config=\'{"responsive":true}\'')
                except Exception as e:
                    _err(str(e))

            funnel_content()

        # ══ AI ENGAGEMENT ═════════════════════════════════════════════════════
        with ui.tab_panel("ai").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("AI Assistant Engagement Rate", "smart_toy")
            _ai_tab(api)

        # ══ STATISTICS ════════════════════════════════════════════════════════
        with ui.tab_panel("stats").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Summary Statistics - Daily Sessions", "table_chart")
            _help_panel(
                "This table shows descriptive statistics for daily session counts "
                "per service. Mean and Median indicate central tendency. "
                "Std Dev and CV% measure volatility — a high CV% means demand "
                "is inconsistent and may need targeted stabilisation efforts."
            )

            @ui.refreshable
            def stats_content():
                try:
                    data = api.get_summary_stats(_START, _END)
                    cols_def = [
                        {"name":"service_type","label":"Service",
                         "field":"service_type","align":"left"},
                        {"name":"days_observed","label":"Days",
                         "field":"days_observed","align":"right"},
                        {"name":"mean","label":"Mean",
                         "field":"mean","align":"right"},
                        {"name":"median","label":"Median",
                         "field":"median","align":"right"},
                        {"name":"stddev","label":"Std Dev",
                         "field":"stddev","align":"right"},
                        {"name":"min_daily_sessions","label":"Min",
                         "field":"min_daily_sessions","align":"right"},
                        {"name":"max_daily_sessions","label":"Max",
                         "field":"max_daily_sessions","align":"right"},
                        {"name":"cv_pct","label":"CV %",
                         "field":"cv_pct","align":"right"},
                    ]
                    rows = [{
                        **r,
                        "mean":   round(r["mean_daily_sessions"],1),
                        "median": round(r["median_daily_sessions"],1),
                        "stddev": round(r["stddev_daily_sessions"],1),
                        "cv_pct": round(r["cv_pct"],1),
                    } for r in data]
                    with ui.element("div").style(
                        f"{_GLASS};padding:20px;width:100%"
                    ):
                        ui.table(
                            columns=cols_def, rows=rows,
                            row_key="service_type"
                        ).style("width:100%").props("flat dense")
                        ui.label(
                            f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}"
                        ).style(
                            f"font-size:10px;color:{TEXT_MUTED};"
                            "text-align:right;width:100%"
                        )
                except Exception as e:
                    _err(str(e))

            stats_content()

        # ══ CAUSAL ════════════════════════════════════════════════════════════
        with ui.tab_panel("causal").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _causal_tab(api)


# ── Demand tab — compact horizontal filter bar ────────────────────────────────

def _demand_tab(api: APIClient):
    # help panel ABOVE the filter card
    _help_panel(
        "Use the date inputs and service filter to customise the analysis period. "
        "Click Apply to refresh the chart. "
        "Hover over any data point to see exact session counts."
    )

    # compact single-row filter bar
    with ui.element("div").style(
        f"{_GLASS};padding:12px 16px;margin-bottom:16px;width:100%;"
        "display:flex;flex-wrap:wrap;align-items:center;gap:12px"
    ):
        # Start date — compact text input
        with ui.column().style("gap:2px;min-width:110px"):
            ui.label("Start").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            d_start = ui.input(value="2026-03-01").style(
                "width:110px"
            ).props("dense outlined dark mask='####-##-##' placeholder='YYYY-MM-DD'")

        ui.label("/").style(f"color:{TEXT_MUTED};font-size:14px;padding-top:16px")

        # End date
        with ui.column().style("gap:2px;min-width:110px"):
            ui.label("End").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            d_end = ui.input(value="2026-05-02").style(
                "width:110px"
            ).props("dense outlined dark mask='####-##-##' placeholder='YYYY-MM-DD'")

        # Service multi-select
        with ui.column().style("gap:2px;flex:1;min-width:200px"):
            ui.label("Services").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            svc_select = ui.select(
                options=_SERVICES, multiple=True,
                value=list(_SERVICES), label=""
            ).props("outlined dense dark use-chips").style("width:100%")

        apply_btn = ui.button("Apply", icon="refresh").style(
            f"background:{BLUE};color:white;border-radius:8px;height:36px;"
            "margin-top:16px"
        ).props("unelevated dense")

    chart_area = ui.column().style("width:100%")

    def draw_demand():
        chart_area.clear()
        start = d_start.value.strip() or _START
        end   = d_end.value.strip()   or _END
        svcs  = svc_select.value or list(_SERVICES)
        try:
            df = pd.DataFrame(api.get_demand_trend(start, end))
            df = df[df["service_type"].isin(svcs)]
            fig = go.Figure()
            for i, svc in enumerate(df["service_type"].unique()):
                sdf = df[df["service_type"] == svc]
                fig.add_trace(go.Scatter(
                    x=sdf["session_date"], y=sdf["total_sessions"],
                    name=svc, mode="lines",
                    line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                    hovertemplate="%{y:,} sessions<extra>" + svc + "</extra>",
                ))
            _dark_layout(fig, "Daily Sessions by Service")
            fig.update_layout(
                height=420,
                legend=dict(
                    orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1
                )
            )
            with chart_area:
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.plotly(fig).style("width:100%;height:420px").props(
                        'config=\'{"responsive":true}\''
                    )
                    ui.label(
                        f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}"
                    ).style(
                        f"font-size:10px;color:{TEXT_MUTED};"
                        "text-align:right;width:100%"
                    )
        except Exception as e:
            with chart_area:
                _err(str(e))

    apply_btn.on_click(draw_demand)
    draw_demand()


# ── AI Engagement tab — compact filter bar ────────────────────────────────────

def _ai_tab(api: APIClient):
    _help_panel(
        "This chart shows the percentage of sessions per service where the "
        "AI Cyber Assistant was engaged. Use the filters to narrow the date range "
        "or compare specific services. Cross-reference with the Causal tab to "
        "understand how AI engagement drives demo conversions."
    )

    with ui.element("div").style(
        f"{_GLASS};padding:12px 16px;margin-bottom:16px;width:100%;"
        "display:flex;flex-wrap:wrap;align-items:center;gap:12px"
    ):
        with ui.column().style("gap:2px;min-width:110px"):
            ui.label("Start").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            ai_start = ui.input(value="2026-03-01").style(
                "width:110px"
            ).props("dense outlined dark mask='####-##-##' placeholder='YYYY-MM-DD'")

        ui.label("/").style(f"color:{TEXT_MUTED};font-size:14px;padding-top:16px")

        with ui.column().style("gap:2px;min-width:110px"):
            ui.label("End").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            ai_end = ui.input(value="2026-05-02").style(
                "width:110px"
            ).props("dense outlined dark mask='####-##-##' placeholder='YYYY-MM-DD'")

        with ui.column().style("gap:2px;flex:1;min-width:200px"):
            ui.label("Services").style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            ai_svc = ui.select(
                options=_SERVICES, multiple=True,
                value=list(_SERVICES), label=""
            ).props("outlined dense dark use-chips").style("width:100%")

        ai_apply = ui.button("Apply", icon="refresh").style(
            f"background:{BLUE};color:white;border-radius:8px;height:36px;"
            "margin-top:16px"
        ).props("unelevated dense")

    ai_area = ui.column().style("width:100%")

    def draw_ai():
        ai_area.clear()
        start = ai_start.value.strip() or _START
        end   = ai_end.value.strip()   or _END
        svcs  = ai_svc.value or list(_SERVICES)
        try:
            df = pd.DataFrame(api.get_ai_engagement(start, end))
            df = df[df["service_type"].isin(svcs)]
            fig = go.Figure()
            for i, svc in enumerate(df["service_type"].unique()):
                sdf = df[df["service_type"] == svc]
                fig.add_trace(go.Bar(
                    x=sdf["session_date"], y=sdf["ai_rate_pct"],
                    name=svc,
                    marker_color=PALETTE[i % len(PALETTE)],
                    hovertemplate="%{y:.1f}%<extra>" + svc + "</extra>",
                ))
            _dark_layout(fig, "AI Engagement Rate (%) by Service")
            fig.update_layout(
                barmode="group", height=400,
                legend=dict(
                    orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1
                )
            )
            with ai_area:
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.plotly(fig).style("width:100%;height:400px").props(
                        'config=\'{"responsive":true}\''
                    )
                    ui.label(
                        f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')}"
                    ).style(
                        f"font-size:10px;color:{TEXT_MUTED};"
                        "text-align:right;width:100%"
                    )
        except Exception as e:
            with ai_area:
                _err(str(e))

    ai_apply.on_click(draw_ai)
    draw_ai()


def _causal_tab(api: APIClient):
    _section("Causal Analysis - AI Assistant Impact", "hub")
    _help_panel(
        "This panel runs a causal inference model using the DoWhy library. "
        "The Average Treatment Effect (ATE) quantifies how much AI assistant "
        "engagement causally increases demo conversion probability, after "
        "controlling for service type, country, hour of day, and daily volume. "
        "Both refutation tests must pass for the result to be considered robust. "
        "Results are cached in the database — subsequent loads are instant."
    )

    with ui.row().style("gap:8px;margin-bottom:16px;flex-wrap:wrap"):
        run_btn = ui.button(
            "Run Causal Analysis", icon="hub"
        ).style(
            f"background:{PURPLE};color:white;font-weight:600;border-radius:8px"
        ).props("unelevated")

        rerun_btn = ui.button(
            "Force Re-run", icon="refresh"
        ).style(
            f"color:{TEXT_MUTED};border-radius:8px"
        ).props("flat")

    status_label = ui.label("").style(
        f"font-size:13px;color:{TEXT_MUTED};font-style:italic"
    )

    spinner_row = ui.row().classes("items-center").style("gap:8px")
    with spinner_row:
        ui.spinner("dots", size="lg").style(f"color:{PURPLE}")
        progress_label = ui.label("Loading session data from DuckDB...").style(
            f"font-size:13px;color:{TEXT_MUTED}"
        )
    spinner_row.set_visibility(False)

    progress_msgs = [
        "Loading session data from DuckDB...",
        "Preparing causal features...",
        "Identifying causal effect (backdoor criterion)...",
        "Estimating ATE via linear regression...",
        "Running placebo refutation test...",
        "Running random common cause refutation...",
        "Finalising results...",
    ]
    msg_index = {"i": 0}

    def cycle_msg():
        msg_index["i"] = (msg_index["i"] + 1) % len(progress_msgs)
        progress_label.set_text(progress_msgs[msg_index["i"]])

    progress_timer = ui.timer(4.0, cycle_msg, active=False)

    result_area = ui.column().style("gap:16px;width:100%")

    try:
        cached = api.get_causal(force=False)
        if cached.get("cached"):
            with result_area:
                with ui.row().classes("items-center").style(
                    "gap:6px;margin-bottom:4px"
                ):
                    ui.icon("cached").style(f"color:{GREEN};font-size:16px")
                    ui.label(
                        f"Showing cached result from "
                        f"{cached.get('cached_at', 'previous session')}. "
                        "Click 'Force Re-run' to recompute."
                    ).style(f"font-size:12px;color:{TEXT_MUTED}")
                _causal_panel(cached)
            run_btn.set_visibility(False)
        else:
            with result_area:
                _causal_panel(cached)
            run_btn.set_visibility(False)
    except APIError:
        status_label.set_text(
            "No cached result. Click 'Run Causal Analysis' to compute."
        )

    def _run(force: bool):
        try:
            run_btn.props("disabled")
            rerun_btn.props("disabled")
            status_label.set_text("")
            spinner_row.set_visibility(True)
            progress_timer.active = True
            result_area.clear()
            causal = api.get_causal(force=force)
            progress_timer.active = False
            spinner_row.set_visibility(False)
            run_btn.props(remove="disabled")
            rerun_btn.props(remove="disabled")
            run_btn.set_visibility(False)
            with result_area:
                if causal.get("cached") and not force:
                    with ui.row().classes("items-center").style(
                        "gap:6px;margin-bottom:4px"
                    ):
                        ui.icon("cached").style(f"color:{GREEN};font-size:16px")
                        ui.label(
                            f"Cached result from "
                            f"{causal.get('cached_at', 'previous session')}"
                        ).style(f"font-size:12px;color:{TEXT_MUTED}")
                _causal_panel(causal)
        except Exception as e:
            progress_timer.active = False
            spinner_row.set_visibility(False)
            run_btn.props(remove="disabled")
            rerun_btn.props(remove="disabled")
            status_label.set_text(f"Error: {str(e)}")

    run_btn.on_click(lambda: _run(force=False))
    rerun_btn.on_click(lambda: _run(force=True))


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _section(text: str, icon: str):
    with ui.row().classes("items-center").style("gap:8px;margin-bottom:16px"):
        ui.icon(icon).style(f"color:{BLUE};font-size:20px")
        ui.label(text).style(
            f"font-size:16px;font-weight:600;color:{TEXT_HEADING}"
        )


def _err(msg: str, retry_fn=None):
    with ui.column().style(
        f"background:rgba(247,129,102,0.06);"
        f"border:1px solid rgba(247,129,102,0.3);"
        "border-radius:10px;padding:16px;gap:10px;width:100%"
    ):
        with ui.row().classes("items-center").style("gap:8px"):
            ui.icon("error_outline").style(f"color:{RED};font-size:20px")
            ui.label("Unable to load data").style(
                f"font-size:14px;font-weight:600;color:{RED}"
            )
        ui.label(
            "There was a problem fetching this data. "
            "This may be due to a network timeout or a server error."
        ).style(f"font-size:12px;color:{TEXT_MUTED};line-height:1.5")
        if retry_fn:
            ui.button("Try Again", icon="refresh", on_click=retry_fn).style(
                f"background:rgba(247,129,102,0.15);color:{RED};"
                "border-radius:8px;font-size:12px"
            ).props("flat dense")


def _dark_layout(fig: go.Figure, title: str = ""):
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color=TEXT_MUTED)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRIMARY, size=11),
        margin=dict(l=8, r=8, t=36, b=8),
        xaxis=dict(gridcolor="rgba(48,54,61,0.5)",
                   linecolor="rgba(48,54,61,0.5)"),
        yaxis=dict(gridcolor="rgba(48,54,61,0.5)",
                   linecolor="rgba(48,54,61,0.5)"),
        legend=dict(
            bgcolor="rgba(22,27,34,0.7)",
            bordercolor="rgba(48,54,61,0.5)",
            borderwidth=1, font=dict(size=11),
        ),
    )


def _help_panel(text: str):
    with ui.expansion("How to use this view", icon="help_outline").style(
        "background:rgba(22,27,34,0.5);"
        "border:1px solid rgba(48,54,61,0.5);"
        "border-radius:8px;margin-bottom:12px"
    ).props("dense"):
        ui.label(text).style(
            f"font-size:12px;color:{TEXT_MUTED};"
            "line-height:1.7;padding:8px 4px"
        )


def _kpi_card(k: dict, api: APIClient = None,
              start: str = _START, end: str = _END):
    rate   = k["conv_rate_pct"]
    colour = GREEN if rate >= 30 else (ORANGE if rate >= 15 else RED)
    badge  = "High" if rate >= 30 else ("Medium" if rate >= 15 else "Low")

    with ui.element("div").style(
        f"{_GLASS};padding:18px;flex:1;min-width:160px;"
        "max-width:calc(20% - 10px);display:flex;flex-direction:column;"
        "gap:8px;cursor:pointer;transition:border-color 0.2s,transform 0.15s"
    ).on("click", lambda k=k: _open_kpi_drawer(k, api, start, end)
          if api else None
    ).classes("kpi-hover-card"):

        with ui.row().classes("items-center justify-between"):
            ui.label(k["service_type"]).style(
                f"font-size:10px;color:{TEXT_MUTED};"
                "font-weight:600;text-transform:uppercase;"
                "letter-spacing:0.05em;line-height:1.3"
            )
            ui.html(
                f'<span style="color:{colour};'
                f'background:rgba({_col_rgb(colour)},0.12);'
                f'padding:2px 8px;border-radius:12px;'
                f'font-size:10px;font-weight:600">{badge}</span>'
            )

        ui.label(f"{rate}%").style(
            f"font-size:26px;font-weight:700;color:{colour};line-height:1.2"
        )
        ui.label("Conversion Rate").style(
            f"font-size:10px;color:{TEXT_MUTED}"
        )
        ui.element("div").style(
            "height:1px;background:rgba(255,255,255,0.06)"
        )
        with ui.row().style("gap:16px"):
            with ui.column().style("gap:1px"):
                ui.label(f"{k['total_sessions']:,}").style(
                    f"font-size:13px;font-weight:600;color:{TEXT_PRIMARY}"
                )
                ui.label("Sessions").style(f"font-size:10px;color:{TEXT_MUTED}")
            with ui.column().style("gap:1px"):
                ui.label(f"{k['ai_engagement_pct']}%").style(
                    f"font-size:13px;font-weight:600;color:{PURPLE}"
                )
                ui.label("AI Engaged").style(f"font-size:10px;color:{TEXT_MUTED}")

        if api:
            with ui.row().classes("items-center").style("gap:4px;margin-top:2px"):
                ui.icon("open_in_full").style(f"font-size:12px;color:{TEXT_MUTED}")
                ui.label("Click for details").style(
                    f"font-size:10px;color:{TEXT_MUTED}"
                )


def _open_kpi_drawer(k: dict, api: APIClient, start: str, end: str):
    svc    = k["service_type"]
    rate   = k["conv_rate_pct"]
    colour = GREEN if rate >= 30 else (ORANGE if rate >= 15 else RED)

    backdrop = ui.element("div").style(
        "position:fixed;inset:0;"
        "background:rgba(0,0,0,0.55);"
        "backdrop-filter:blur(3px);"
        "z-index:400"
    )

    drawer = ui.element("div").style(
        "position:fixed;top:0;right:0;bottom:0;"
        "width:min(560px, 95vw);"
        "background:rgba(16,21,28,0.98);"
        "backdrop-filter:blur(24px);"
        "border-left:1px solid rgba(48,54,61,0.8);"
        "box-shadow:-8px 0 40px rgba(0,0,0,0.6);"
        "z-index:401;"
        "display:flex;flex-direction:column;"
        "animation:slideInRight 0.25s ease"
    )

    ui.add_head_html("""
    <style>
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to   { transform: translateX(0);    opacity: 1; }
    }
    .kpi-hover-card:hover {
        border-color: rgba(88,166,255,0.35) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5),
                    inset 0 1px 0 rgba(255,255,255,0.08) !important;
    }
    </style>
    """)

    def close_drawer():
        backdrop.delete()
        drawer.delete()

    backdrop.on("click", close_drawer)

    with drawer:
        with ui.row().classes("items-center justify-between").style(
            "padding:20px 24px;"
            "border-bottom:1px solid rgba(48,54,61,0.6);"
            "flex-shrink:0"
        ):
            with ui.column().style("gap:2px"):
                ui.label(svc).style(
                    f"font-size:16px;font-weight:700;color:{TEXT_PRIMARY}"
                )
                ui.label("Service Performance Detail").style(
                    f"font-size:12px;color:{TEXT_MUTED}"
                )
            with ui.row().classes("items-center").style("gap:8px"):
                ui.html(
                    f'<span style="color:{colour};'
                    f'background:rgba({_col_rgb(colour)},0.12);'
                    f'padding:4px 12px;border-radius:12px;'
                    f'font-size:12px;font-weight:600">'
                    f'{rate}% Conv Rate</span>'
                )
                with ui.element("div").style(
                    "cursor:pointer;padding:6px;border-radius:8px;"
                    "background:rgba(255,255,255,0.06)"
                ).on("click", close_drawer):
                    ui.icon("close").style(
                        f"font-size:18px;color:{TEXT_MUTED}"
                    )

        with ui.element("div").style(
            "flex:1;overflow-y:auto;padding:24px;"
            "display:flex;flex-direction:column;gap:20px"
        ):
            with ui.row().style("gap:12px;flex-wrap:wrap;width:100%"):
                for label, value, col in [
                    ("Total Sessions", f"{k['total_sessions']:,}", BLUE),
                    ("Conversions",
                     f"{int(k['total_sessions'] * rate / 100):,}", colour),
                    ("AI Engagement", f"{k['ai_engagement_pct']}%", PURPLE),
                ]:
                    with ui.element("div").style(
                        "background:rgba(22,27,34,0.7);"
                        "border:1px solid rgba(255,255,255,0.07);"
                        "border-radius:10px;padding:14px 16px;"
                        "flex:1;min-width:120px;"
                        "display:flex;flex-direction:column;gap:4px"
                    ):
                        ui.label(value).style(
                            f"font-size:22px;font-weight:700;color:{col}"
                        )
                        ui.label(label).style(
                            f"font-size:11px;color:{TEXT_MUTED};"
                            "text-transform:uppercase;letter-spacing:0.05em"
                        )

            _drawer_section("Demand Trend", "bar_chart")
            try:
                df_trend = pd.DataFrame(api.get_demand_trend(start, end))
                df_svc = df_trend[df_trend["service_type"] == svc].copy()
                if not df_svc.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_svc["session_date"],
                        y=df_svc["total_sessions"],
                        mode="lines", fill="tozeroy",
                        line=dict(color=colour, width=2),
                        fillcolor=f"rgba({_col_rgb(colour)},0.12)",
                        hovertemplate="%{y:,} sessions<extra></extra>",
                    ))
                    df_svc["rolling"] = (
                        df_svc["total_sessions"].rolling(7, min_periods=1).mean()
                    )
                    fig.add_trace(go.Scatter(
                        x=df_svc["session_date"],
                        y=df_svc["rolling"],
                        mode="lines",
                        line=dict(color=BLUE, width=1.5, dash="dot"),
                        name="7-day avg",
                        hovertemplate="%{y:.0f} avg<extra></extra>",
                    ))
                    _drawer_chart_layout(fig)
                    fig.update_layout(
                        height=200, showlegend=True,
                        legend=dict(
                            font=dict(size=10, color=TEXT_MUTED),
                            bgcolor="rgba(0,0,0,0)",
                            x=0, y=1.1, orientation="h",
                        )
                    )
                    with ui.element("div").style(
                        "background:rgba(13,17,23,0.5);"
                        "border:1px solid rgba(255,255,255,0.06);"
                        "border-radius:10px;padding:12px;width:100%"
                    ):
                        ui.plotly(fig).style("width:100%;height:200px").props(
                            'config=\'{"responsive":true,"displayModeBar":false}\''
                        )
                else:
                    _drawer_empty("No trend data available.")
            except Exception as e:
                _drawer_empty(f"Could not load trend: {str(e)}")

            _drawer_section("Conversion Funnel", "filter_alt")
            try:
                df_funnel = pd.DataFrame(api.get_funnel(start, end))
                df_svc_f  = df_funnel[df_funnel["service_type"] == svc].copy()
                stage_order = ["awareness","interest","consideration","conversion"]
                if not df_svc_f.empty:
                    df_svc_f["funnel_stage"] = pd.Categorical(
                        df_svc_f["funnel_stage"],
                        categories=stage_order, ordered=True
                    )
                    df_svc_f = df_svc_f.sort_values("funnel_stage")
                    fig2 = go.Figure(go.Funnel(
                        y=df_svc_f["funnel_stage"].str.capitalize(),
                        x=df_svc_f["sessions_at_stage"],
                        textposition="inside",
                        textinfo="value+percent initial",
                        marker_color=PALETTE[:len(df_svc_f)],
                    ))
                    _drawer_chart_layout(fig2)
                    fig2.update_layout(height=220, margin=dict(l=4,r=4,t=8,b=4))
                    with ui.element("div").style(
                        "background:rgba(13,17,23,0.5);"
                        "border:1px solid rgba(255,255,255,0.06);"
                        "border-radius:10px;padding:12px;width:100%"
                    ):
                        ui.plotly(fig2).style("width:100%;height:220px").props(
                            'config=\'{"responsive":true,"displayModeBar":false}\''
                        )
                else:
                    _drawer_empty("No funnel data for this service.")
            except Exception as e:
                _drawer_empty(f"Could not load funnel: {str(e)}")

            _drawer_section("AI Engagement Rate", "smart_toy")
            try:
                df_ai    = pd.DataFrame(api.get_ai_engagement(start, end))
                df_svc_a = df_ai[df_ai["service_type"] == svc].copy()
                if not df_svc_a.empty:
                    fig3 = go.Figure(go.Bar(
                        x=df_svc_a["session_date"],
                        y=df_svc_a["ai_rate_pct"],
                        marker_color=f"rgba({_col_rgb(PURPLE)},0.7)",
                        hovertemplate="%{y:.1f}%<extra></extra>",
                    ))
                    fig3.add_trace(go.Scatter(
                        x=df_svc_a["session_date"],
                        y=df_svc_a["conversions"],
                        mode="lines", yaxis="y2",
                        line=dict(color=colour, width=1.5),
                        name="Conversions",
                        hovertemplate="%{y:,}<extra>Conversions</extra>",
                    ))
                    _drawer_chart_layout(fig3)
                    fig3.update_layout(
                        height=200,
                        yaxis2=dict(
                            overlaying="y", side="right",
                            showgrid=False,
                            tickfont=dict(color=colour, size=9),
                        ),
                        barmode="overlay", showlegend=True,
                        legend=dict(
                            font=dict(size=10, color=TEXT_MUTED),
                            bgcolor="rgba(0,0,0,0)",
                            x=0, y=1.1, orientation="h",
                        ),
                    )
                    with ui.element("div").style(
                        "background:rgba(13,17,23,0.5);"
                        "border:1px solid rgba(255,255,255,0.06);"
                        "border-radius:10px;padding:12px;width:100%"
                    ):
                        ui.plotly(fig3).style("width:100%;height:200px").props(
                            'config=\'{"responsive":true,"displayModeBar":false}\''
                        )
                else:
                    _drawer_empty("No AI engagement data.")
            except Exception as e:
                _drawer_empty(f"Could not load AI data: {str(e)}")

            _drawer_section("Summary Statistics", "table_chart")
            try:
                stats    = api.get_summary_stats(start, end)
                svc_stat = next(
                    (s for s in stats if s["service_type"] == svc), None
                )
                if svc_stat:
                    stat_items = [
                        ("Mean Daily Sessions",
                         f"{svc_stat['mean_daily_sessions']:.1f}", BLUE),
                        ("Median Daily Sessions",
                         f"{svc_stat['median_daily_sessions']:.1f}", BLUE),
                        ("Std Dev",
                         f"{svc_stat['stddev_daily_sessions']:.1f}", ORANGE),
                        ("CV %", f"{svc_stat['cv_pct']:.1f}%", ORANGE),
                        ("Min", str(svc_stat["min_daily_sessions"]), GREEN),
                        ("Max", str(svc_stat["max_daily_sessions"]), GREEN),
                    ]
                    with ui.row().style("gap:10px;flex-wrap:wrap;width:100%"):
                        for label, value, col in stat_items:
                            with ui.element("div").style(
                                "background:rgba(13,17,23,0.5);"
                                "border:1px solid rgba(255,255,255,0.06);"
                                "border-radius:8px;padding:10px 14px;"
                                "flex:1;min-width:100px;"
                                "display:flex;flex-direction:column;gap:3px"
                            ):
                                ui.label(value).style(
                                    f"font-size:18px;font-weight:700;color:{col}"
                                )
                                ui.label(label).style(
                                    f"font-size:10px;color:{TEXT_MUTED};"
                                    "text-transform:uppercase;letter-spacing:0.04em"
                                )
                else:
                    _drawer_empty("No stats available.")
            except Exception as e:
                _drawer_empty(f"Could not load stats: {str(e)}")


def _drawer_section(text: str, icon: str):
    with ui.row().classes("items-center").style("gap:6px"):
        ui.icon(icon).style(f"color:{BLUE};font-size:16px")
        ui.label(text).style(
            f"font-size:13px;font-weight:600;color:{TEXT_HEADING}"
        )


def _drawer_empty(msg: str):
    ui.label(msg).style(
        f"font-size:12px;color:{TEXT_MUTED};font-style:italic;padding:8px 0"
    )


def _drawer_chart_layout(fig: go.Figure):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRIMARY, size=10),
        margin=dict(l=4, r=4, t=8, b=4),
        xaxis=dict(
            gridcolor="rgba(48,54,61,0.4)",
            linecolor="rgba(48,54,61,0.4)",
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            gridcolor="rgba(48,54,61,0.4)",
            linecolor="rgba(48,54,61,0.4)",
            tickfont=dict(size=9),
        ),
    )


def _causal_panel(causal: dict):
    ate   = causal["ate_pp"]
    ci_lo = causal["ci_lower"]
    ci_hi = causal["ci_upper"]
    pval  = causal["p_value"]
    conf  = causal["confidence_label"]
    plain = causal["plain_language"]

    conf_colour  = GREEN if conf == "High" else (ORANGE if conf == "Moderate" else RED)
    pval_display = "< 0.0001" if pval == 0.0 else str(pval)

    with ui.column().style(f"{_GLASS};padding:24px;gap:20px;width:100%"):
        with ui.row().style("gap:16px;flex-wrap:wrap;width:100%"):
            with ui.element("div").style(
                "background:rgba(13,17,23,0.5);"
                "border:1px solid rgba(255,255,255,0.07);"
                "border-radius:10px;padding:16px;gap:6px;"
                "flex:1;min-width:160px;display:flex;flex-direction:column"
            ):
                ui.label("AVERAGE TREATMENT EFFECT").style(
                    f"font-size:10px;color:{TEXT_MUTED};"
                    "letter-spacing:0.07em;font-weight:600"
                )
                ui.label(f"{ate:+.2f} pp").style(
                    f"font-size:32px;font-weight:700;color:{PURPLE}"
                )
                ui.label(
                    f"95% CI  [{ci_lo:.2f}, {ci_hi:.2f}]  |  "
                    f"p-value: {pval_display}"
                ).style(f"font-size:11px;color:{TEXT_MUTED}")

            with ui.element("div").style(
                "background:rgba(13,17,23,0.5);"
                "border:1px solid rgba(255,255,255,0.07);"
                "border-radius:10px;padding:16px;gap:10px;"
                "flex:1;min-width:160px;display:flex;flex-direction:column"
            ):
                ui.label("MODEL CONFIDENCE").style(
                    f"font-size:10px;color:{TEXT_MUTED};"
                    "letter-spacing:0.07em;font-weight:600"
                )
                ui.label(conf).style(
                    f"font-size:28px;font-weight:700;color:{conf_colour}"
                )
                ui.linear_progress(
                    value=1.0 if conf == "High" else 0.6
                    if conf == "Moderate" else 0.3,
                ).style(
                    f"height:5px;border-radius:3px;"
                    f"--q-color-primary:{conf_colour}"
                )

            with ui.element("div").style(
                "background:rgba(13,17,23,0.5);"
                "border:1px solid rgba(255,255,255,0.07);"
                "border-radius:10px;padding:16px;gap:8px;"
                "flex:1;min-width:160px;display:flex;flex-direction:column"
            ):
                ui.label("REFUTATION TESTS").style(
                    f"font-size:10px;color:{TEXT_MUTED};"
                    "letter-spacing:0.07em;font-weight:600"
                )
                for label, passed in [
                    ("Placebo Treatment",   causal["placebo_pass"]),
                    ("Random Common Cause", causal["random_cause_pass"]),
                ]:
                    c  = GREEN if passed else RED
                    ic = "check_circle" if passed else "cancel"
                    with ui.row().classes("items-center").style("gap:8px"):
                        ui.icon(ic).style(f"color:{c};font-size:18px")
                        ui.label(label).style(
                            f"font-size:13px;color:{TEXT_PRIMARY}"
                        )

        with ui.element("div").style(
            "background:rgba(210,168,255,0.06);"
            "border:1px solid rgba(210,168,255,0.18);"
            "border-radius:10px;padding:16px;gap:8px;"
            "display:flex;flex-direction:column"
        ):
            with ui.row().classes("items-center").style("gap:8px"):
                ui.icon("insights").style(f"color:{PURPLE};font-size:18px")
                ui.label("Plain Language Interpretation").style(
                    f"font-size:13px;font-weight:600;color:{PURPLE}"
                )
            ui.label(plain).style(
                f"font-size:13px;color:{TEXT_PRIMARY};line-height:1.7"
            )

        _dag_viz()
        with ui.row().classes("items-center").style("gap:6px;margin-top:4px"):
            ui.icon("info_outline").style(f"font-size:14px;color:{TEXT_MUTED}")
            ui.label(
                "DAG constructed using DoWhy backdoor criterion. "
                "Confounders identified from domain knowledge of the CyberNova sales process."
            ).style(f"font-size:11px;color:{TEXT_MUTED};line-height:1.5")


def _dag_viz():
    nodes = {
        "ai_chat\nengaged":       (2.0, 0.0, PURPLE),
        "converted":              (2.0, 4.0, GREEN),
        "service\nenc":           (0.0, 2.0, BLUE),
        "country\nenc":           (0.8, 2.0, BLUE),
        "hour of\nday":           (3.2, 2.0, BLUE),
        "daily request\nvolume":  (4.2, 2.0, BLUE),
    }
    coords = {k: (v[0], v[1]) for k, v in nodes.items()}
    edges = [
        ("service\nenc",          "ai_chat\nengaged"),
        ("service\nenc",          "converted"),
        ("country\nenc",          "ai_chat\nengaged"),
        ("country\nenc",          "converted"),
        ("hour of\nday",          "ai_chat\nengaged"),
        ("hour of\nday",          "converted"),
        ("daily request\nvolume", "ai_chat\nengaged"),
        ("daily request\nvolume", "converted"),
        ("ai_chat\nengaged",      "converted"),
    ]
    ex, ey = [], []
    for src, tgt in edges:
        x0, y0 = coords[src]; x1, y1 = coords[tgt]
        ex += [x0, x1, None]; ey += [y0, y1, None]

    keys = list(nodes.keys())
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(width=1.5, color="rgba(48,54,61,0.8)"),
        hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=[coords[k][0] for k in keys],
        y=[coords[k][1] for k in keys],
        mode="markers+text",
        marker=dict(
            size=28, color=[nodes[k][2] for k in keys],
            line=dict(width=2, color="rgba(22,27,34,0.9)"),
        ),
        text=keys,
        textposition=[
            "bottom center","top center",
            "top left","top left","top right","top right",
        ],
        textfont=dict(size=10, color=TEXT_PRIMARY),
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(visible=False, range=[-0.6, 5.0]),
        yaxis=dict(visible=False, range=[-0.8, 5.0]),
    )

    with ui.column().style("gap:8px"):
        with ui.row().classes("items-center").style("gap:8px"):
            ui.icon("account_tree").style(f"color:{BLUE};font-size:18px")
            ui.label("Causal DAG - Backdoor Variables").style(
                f"font-size:13px;font-weight:600;color:{TEXT_HEADING}"
            )
        with ui.row().style("gap:16px"):
            for colour, role in [
                (PURPLE,"Treatment"),(GREEN,"Outcome"),(BLUE,"Confounder")
            ]:
                with ui.row().classes("items-center").style("gap:5px"):
                    ui.html(
                        f'<span style="width:10px;height:10px;border-radius:50%;'
                        f'background:{colour};display:inline-block"></span>'
                    )
                    ui.label(role).style(f"font-size:11px;color:{TEXT_MUTED}")
        ui.plotly(fig).style("width:100%;height:280px").props(
            'config=\'{"responsive":true}\''
        )


def _col_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"