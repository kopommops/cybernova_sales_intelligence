"""
frontend/pages/sales_manager_dashboard.py
------------------------------------------
Sales manager - REQ-13 through REQ-16.
No ui.timer. Persistent chat. Filters on demand/AI tabs.
"""

import pandas as pd
import plotly.graph_objects as go
from nicegui import app, ui

from api_client import APIClient, APIError
from components.layout import build_layout
from pages.salesperson_dashboard import (
    _GLASS, _causal_panel, _causal_tab, _dark_layout,
    _demand_tab, _ai_tab, _err, _kpi_card, _section, _col_rgb, _help_panel
)
from theme import (
    BLUE, GREEN, ORANGE, PALETTE,
    PURPLE, RED, TEXT_HEADING, TEXT_MUTED, TEXT_PRIMARY, YELLOW,
)



_START    = "2026-02-06"
_END      = "2026-04-06"
_SERVICES = [
    "AI Cyber Assistant", "Cyber Awareness Webinar",
    "Network Security Audit", "Penetration Testing", "Schedule Demo",
]


def render():
    token = app.storage.user.get("token", "")
    api   = APIClient(token)

    if "chat_history" not in app.storage.user:
        app.storage.user["chat_history"] = []

    # fetch alerts for bell
    alerts = []
    try:
        alerts = api.get_anomaly_alerts(_START, _END)
    except APIError:
        pass

    panels, tabs, bell_content = build_layout(
        default_tab="overview", alert_count=len(alerts)
    )

    # populate bell
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
                        f"{a['session_date'][:10]}  "
                        f"{a['daily_sessions']} sessions "
                        f"(gap: {a['breach_gap']})"
                    ).style(f"font-size:11px;color:{TEXT_MUTED}")
            if len(alerts) > 10:
                ui.label(
                    f"... and {len(alerts) - 10} more breach days"
                ).style(
                    f"font-size:11px;color:{TEXT_MUTED};"
                    "padding:8px 16px;font-style:italic"
                )

    with panels:

        # ── Overview ──────────────────────────────────────────────────────────
        with ui.tab_panel("overview").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Conversion KPIs by Service", "credit_card")
            try:
                kpis = api.get_conversion_kpi(_START, _END)
                with ui.row().style("gap:12px;flex-wrap:wrap;width:100%"):
                    for k in kpis:
                        _kpi_card(k, api=api, start=_START, end=_END)
            except APIError as e:
                _err(e.detail)

        # ── Demand (with filters) ──────────────────────────────────────────────
        with ui.tab_panel("demand").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Service Demand Trends", "bar_chart")
            _demand_tab(api)

        # ── Heatmap ───────────────────────────────────────────────────────────
        with ui.tab_panel("heatmap").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Request Volume Heatmap - Hour x Day", "grid_on")
            try:
                df = pd.DataFrame(api.get_heatmap(_START, _END))
                day_order = ["Monday", "Tuesday", "Wednesday",
                             "Thursday", "Friday", "Saturday", "Sunday"]
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
                fig.update_layout(height=340, margin=dict(l=8, r=8, t=8, b=8))
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.plotly(fig).style("width:100%;height:340px").props(
                        'config=\'{"responsive":true}\''
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
                    with ui.row().classes("items-center").style("gap:8px;margin-bottom:4px"):
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
                        bar_pct = int((row["session_count"] / peak["session_count"].max()) * 100)
                        with ui.element("div").style(
                            "background:rgba(13,17,23,0.5);"
                            "border:1px solid rgba(255,255,255,0.06);"
                            "border-radius:8px;padding:12px 16px;"
                            "display:flex;align-items:center;gap:16px"
                        ):
                            # Rank badge
                            badge_colour = [
                                "#FFD700", "#C0C0C0", "#CD7F32", BLUE, BLUE
                            ][i]
                            ui.html(
                                f'<div style="width:24px;height:24px;border-radius:50%;'
                                f'background:{badge_colour};color:#0D1117;'
                                f'display:flex;align-items:center;justify-content:center;'
                                f'font-size:11px;font-weight:700;flex-shrink:0">#{i+1}</div>'
                            )
                            # Day + hour
                            with ui.column().style("gap:1px;min-width:160px"):
                                ui.label(
                                    f"{row['day_of_week']}  {row['hour_of_day']}:00"
                                ).style(
                                    f"font-size:13px;font-weight:600;color:{TEXT_PRIMARY}"
                                )
                                ui.label("Peak engagement window").style(
                                    f"font-size:10px;color:{TEXT_MUTED}"
                                )
                            # Progress bar
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
                            # Count
                            ui.label(f"{row['session_count']:,}").style(
                                f"font-size:14px;font-weight:700;color:{BLUE};"
                                "white-space:nowrap"
                            )
                            ui.label("sessions").style(
                                f"font-size:10px;color:{TEXT_MUTED};white-space:nowrap"
                            )
            except APIError as e:
                _err(e.detail)


        # ── Funnel ────────────────────────────────────────────────────────────
        with ui.tab_panel("funnel").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Conversion Funnel by Service", "filter_alt")
            try:
                df = pd.DataFrame(api.get_funnel(_START, _END))
                stage_order = ["awareness", "interest",
                               "consideration", "conversion"]
                with ui.row().style("gap:12px;width:100%;flex-wrap:wrap"):
                    for svc in df["service_type"].unique():
                        sdf = df[df["service_type"] == svc].copy()
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
                            height=260, margin=dict(l=4, r=4, t=36, b=4)
                        )
                        with ui.element("div").style(
                            f"{_GLASS};padding:10px;flex:1;min-width:180px;"
                            "max-width:calc(25% - 9px)"
                        ):
                            ui.plotly(fig).style("width:100%;height:260px").props(
                                'config=\'{"responsive":true}\''
                            )
            except APIError as e:
                _err(e.detail)

        # ── AI Engagement (with filters) ───────────────────────────────────────
        with ui.tab_panel("ai").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("AI Assistant Engagement Rate", "smart_toy")
            _ai_tab(api)

        # ── Statistics ────────────────────────────────────────────────────────
        with ui.tab_panel("stats").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Summary Statistics - Daily Sessions", "table_chart")
            try:
                data = api.get_summary_stats(_START, _END)
                cols = [
                    {"name": "service_type", "label": "Service",
                     "field": "service_type", "align": "left"},
                    {"name": "days_observed", "label": "Days",
                     "field": "days_observed", "align": "right"},
                    {"name": "mean", "label": "Mean",
                     "field": "mean", "align": "right"},
                    {"name": "median", "label": "Median",
                     "field": "median", "align": "right"},
                    {"name": "stddev", "label": "Std Dev",
                     "field": "stddev", "align": "right"},
                    {"name": "min_daily_sessions", "label": "Min",
                     "field": "min_daily_sessions", "align": "right"},
                    {"name": "max_daily_sessions", "label": "Max",
                     "field": "max_daily_sessions", "align": "right"},
                    {"name": "cv_pct", "label": "CV %",
                     "field": "cv_pct", "align": "right"},
                ]
                rows = [{
                    **r,
                    "mean":   round(r["mean_daily_sessions"], 1),
                    "median": round(r["median_daily_sessions"], 1),
                    "stddev": round(r["stddev_daily_sessions"], 1),
                    "cv_pct": round(r["cv_pct"], 1),
                } for r in data]
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.table(
                        columns=cols, rows=rows, row_key="service_type"
                    ).style("width:100%").props("flat dense")
            except APIError as e:
                _err(e.detail)

        # ── Causal ────────────────────────────────────────────────────────────
        with ui.tab_panel("causal").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _causal_tab(api)

        # ── Regional ──────────────────────────────────────────────────────────
        with ui.tab_panel("regional").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("SADC Regional Service Dominance", "public")
            try:
                data   = api.get_geo(_START, _END)
                df_geo = pd.DataFrame(data)

                country_totals = (
                    df_geo.groupby("country")["sessions"]
                    .sum().reset_index()
                    .rename(columns={"sessions": "total_sessions"})
                )
                iso3 = {
                    "Botswana": "BWA", "South Africa": "ZAF",
                    "Zimbabwe": "ZWE", "Zambia": "ZMB", "Namibia": "NAM",
                }
                country_totals["iso3"] = country_totals["country"].map(iso3)

                hover_text = {}
                for country in df_geo["country"].unique():
                    cdf   = df_geo[df_geo["country"] == country]
                    lines = [f"<b>{country}</b>"]
                    for _, row in cdf.iterrows():
                        lines.append(
                            f"{row['service_type']}: {row['pct_of_country']}%"
                        )
                    hover_text[country] = "<br>".join(lines)

                country_totals["hover"] = country_totals["country"].map(
                    hover_text
                )

                map_fig = go.Figure(go.Choropleth(
                    locations=country_totals["iso3"],
                    z=country_totals["total_sessions"],
                    text=country_totals["hover"],
                    hoverinfo="text",
                    colorscale=[
                        [0.0, "rgba(13,17,23,0.6)"],
                        [0.3, "rgba(30,50,100,0.8)"],
                        [0.6, "rgba(50,100,200,0.9)"],
                        [1.0, "rgba(88,166,255,1.0)"],
                    ],
                    colorbar=dict(
                        title=dict(
                            text="Sessions",
                            font=dict(color=TEXT_MUTED, size=11)
                        ),
                        tickfont=dict(color=TEXT_MUTED, size=10),
                        bgcolor="rgba(22,27,34,0.8)",
                        bordercolor="rgba(48,54,61,0.5)",
                        thickness=12, len=0.6,
                    ),
                    showscale=True,
                ))
                map_fig.update_layout(
                    geo=dict(
                        scope="africa", showframe=False,
                        showcoastlines=True,
                        coastlinecolor="rgba(48,54,61,0.6)",
                        showland=True,
                        landcolor="rgba(22,27,34,0.8)",
                        showocean=True,
                        oceancolor="rgba(13,17,23,0.9)",
                        showlakes=False, showcountries=True,
                        countrycolor="rgba(48,54,61,0.5)",
                        bgcolor="rgba(0,0,0,0)",
                        center=dict(lat=-20, lon=28),
                        projection_scale=3.2,
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=440,
                    font=dict(color=TEXT_PRIMARY),
                )
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.plotly(map_fig).style("width:100%;height:440px").props(
                        'config=\'{"responsive":true}\''
                    )

                ui.label("Service Share by Country (%)").style(
                    f"font-size:14px;font-weight:600;color:{TEXT_HEADING};"
                    "margin-top:20px;margin-bottom:12px"
                )
                df_pivot = df_geo.pivot_table(
                    index="country", columns="service_type",
                    values="pct_of_country", fill_value=0,
                ).reset_index().round(1)
                t_cols = [
                    {"name": "country", "label": "Country",
                     "field": "country", "align": "left"}
                ] + [
                    {"name": c, "label": c, "field": c, "align": "right"}
                    for c in df_pivot.columns if c != "country"
                ]
                with ui.element("div").style(
                    f"{_GLASS};padding:20px;width:100%"
                ):
                    ui.table(
                        columns=t_cols,
                        rows=df_pivot.to_dict(orient="records"),
                        row_key="country"
                    ).style("width:100%").props("flat dense")

            except APIError as e:
                _err(e.detail)
            except Exception as e:
                _err(str(e))

        # ── Action Plan ───────────────────────────────────────────────────────
        with ui.tab_panel("action").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("AI-Generated Action Plan", "lightbulb")
            action_area = ui.column().style("gap:16px;width:100%")

            #gen_btn = ui.button(
            #    "Generate Action Plan", icon="auto_awesome"
            #).style(
            #    f"background:{PURPLE};color:white;font-weight:600;"
            #    "border-radius:8px;margin-bottom:8px"
            #).props("unelevated")

            #with action_area:
            #    ui.label(
            #        "Click 'Generate Action Plan' to fetch AI recommendations."
            #    ).style(f"font-size:13px;color:{TEXT_MUTED};font-style:italic")

            # In the action tab, replace load_action and the initial state:

            # check cache
            cached_plan = app.storage.user.get("action_plan_result")

            _help_panel(
                "The AI Advisor analyses current KPIs, anomaly alerts, and causal "
                "results to generate prioritised recommendations. "
                "Use the email CTA to send the plan directly to your sales team."
            )

            gen_btn = ui.button(
                "Generate Action Plan" if not cached_plan else "Regenerate",
                icon="auto_awesome"
            ).style(
                f"background:{PURPLE};color:white;font-weight:600;"
                "border-radius:8px;margin-bottom:8px"
            ).props("unelevated")

            action_area = ui.column().style("gap:16px;width:100%")

            # render cached immediately
            if cached_plan:
                with action_area:
                    _action_plan_content(cached_plan, api)
            else:
                with action_area:
                    ui.label(
                        "Click 'Generate Action Plan' to fetch AI recommendations."
                    ).style(f"font-size:13px;color:{TEXT_MUTED};font-style:italic")

            def load_action():
                action_area.clear()
                with action_area:
                    with ui.column().style("align-items:center;padding:32px;gap:8px"):
                        ui.spinner("dots", size="lg").style(f"color:{PURPLE}")
                        ui.label("Generating recommendations...").style(
                            f"font-size:13px;color:{TEXT_MUTED}"
                        )
                try:
                    plan = api.get_action_plan(_START, _END)
                    app.storage.user["action_plan_result"] = plan  # cache it
                    action_area.clear()
                    with action_area:
                        _action_plan_content(plan, api)
                    gen_btn.set_text("Regenerate")
                except Exception as e:
                    action_area.clear()
                    with action_area:
                        _err(f"Action plan failed: {str(e)}")

            gen_btn.on_click(load_action)

        # ── AI Advisor ────────────────────────────────────────────────────────
        with ui.tab_panel("advisor").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("AI Sales Advisor", "chat")
            _chatbot_panel(api)

        # ── Export ────────────────────────────────────────────────────────────
        with ui.tab_panel("export").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Export Dashboard Report", "picture_as_pdf")
            _help_panel(
                "Download a formatted PDF report containing current KPIs, "
                "anomaly alerts, and causal analysis results. "
                "The report reflects the default analysis period. "
                "Ensure the causal analysis has been run at least once before exporting."
            )

            with ui.element("div").style(
                f"{_GLASS};padding:24px;width:100%;gap:20px;"
                "display:flex;flex-direction:column"
            ):
                with ui.row().classes("items-center").style("gap:16px"):
                    ui.icon("picture_as_pdf").style(
                        f"color:{RED};font-size:36px;flex-shrink:0"
                    )
                    with ui.column().style("gap:4px;flex:1"):
                        ui.label("Download PDF Report").style(
                            f"font-size:15px;font-weight:600;color:{TEXT_HEADING}"
                        )
                        ui.label(
                            "Exports current KPIs, anomaly alerts, and causal "
                            "analysis as a formatted PDF document."
                        ).style(f"font-size:13px;color:{TEXT_MUTED}")

                # status label for feedback
                export_status = ui.label("").style(
                    f"font-size:12px;color:{TEXT_MUTED};font-style:italic"
                )

                export_btn = ui.button(
                    "Download PDF", icon="download"
                ).style(
                    f"background:{RED};color:white;font-weight:600;"
                    "border-radius:8px;align-self:flex-start"
                ).props("unelevated")

                def download_pdf():
                    export_btn.props("disabled")
                    export_btn.set_text("Generating...")
                    export_status.set_text("Preparing report, please wait...")
                    try:
                        import httpx
                        url = (
                            "http://127.0.0.1:8000/api/manager/export-pdf"
                            f"?start={_START}&end={_END}"
                        )
                        headers = {"Authorization": f"Bearer {token}"}
                        with httpx.Client(timeout=60) as client:
                            r = client.get(url, headers=headers)
                        if r.is_success:
                            ui.download(r.content, "cybernova_report.pdf")
                            export_status.set_text(
                                "Report downloaded successfully."
                            )
                            ui.notify(
                                "Report downloaded.",
                                color="positive",
                                position="top-right"
                            )
                        else:
                            export_status.set_text("Export failed. Try again.")
                            ui.notify("PDF export failed", color="negative")
                    except Exception as e:
                        export_status.set_text(f"Error: {str(e)}")
                        ui.notify(f"Export failed: {str(e)}", color="negative")
                    finally:
                        export_btn.props(remove="disabled")
                        export_btn.set_text("Download PDF")

                export_btn.on_click(download_pdf)


# ── Action plan content ───────────────────────────────────────────────────────

def _action_plan_content(plan: dict, api: APIClient):
    priority_colours = [RED, ORANGE, YELLOW, BLUE, GREEN]

    with ui.column().style(f"{_GLASS};padding:24px;gap:16px;width:100%"):
        for item in plan.get("action_plan", []):
            p   = item["priority"]
            col = priority_colours[min(p - 1, 4)]
            with ui.element("div").style(
                f"border-left:3px solid {col};"
                "background:rgba(13,17,23,0.5);"
                "border-radius:0 10px 10px 0;"
                "padding:14px 16px;"
                "display:flex;gap:14px;align-items:flex-start"
            ):
                ui.html(
                    f'<div style="width:26px;height:26px;border-radius:50%;'
                    f'background:{col};color:white;display:flex;'
                    f'align-items:center;justify-content:center;'
                    f'font-size:12px;font-weight:700;flex-shrink:0">'
                    f'{p}</div>'
                )
                with ui.column().style("gap:4px;flex:1;min-width:0"):
                    ui.label(item["action"]).style(
                        f"font-size:14px;font-weight:600;color:{TEXT_HEADING}"
                    )
                    ui.label(item["rationale"]).style(
                        f"font-size:12px;color:{TEXT_MUTED};line-height:1.5"
                    )

    if plan.get("causal_interpretation"):
        with ui.element("div").style(
            "background:rgba(210,168,255,0.06);"
            "border:1px solid rgba(210,168,255,0.18);"
            "border-radius:10px;padding:16px;gap:8px;"
            "display:flex;flex-direction:column"
        ):
            ui.label("Causal Interpretation").style(
                f"font-size:11px;font-weight:600;color:{PURPLE};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            ui.label(plan["causal_interpretation"]).style(
                f"font-size:13px;color:{TEXT_PRIMARY};line-height:1.6"
            )

    if plan.get("regional_note"):
        with ui.element("div").style(
            "background:rgba(88,166,255,0.06);"
            "border:1px solid rgba(88,166,255,0.18);"
            "border-radius:10px;padding:16px;gap:8px;"
            "display:flex;flex-direction:column"
        ):
            ui.label("Regional Note").style(
                f"font-size:11px;font-weight:600;color:{BLUE};"
                "text-transform:uppercase;letter-spacing:0.05em"
            )
            ui.label(plan["regional_note"]).style(
                f"font-size:13px;color:{TEXT_PRIMARY};line-height:1.6"
            )

    if plan.get("action_plan"):
        _email_cta(api, plan)


def _email_cta(api: APIClient, plan: dict):
    body = "\n".join([
        f"{i['priority']}. {i['action']}\n   {i['rationale']}\n"
        for i in plan.get("action_plan", [])
    ])
    with ui.element("div").style(
        f"{_GLASS};padding:20px;gap:12px;width:100%;"
        "display:flex;flex-direction:column"
    ):
        with ui.row().classes("items-center").style("gap:8px"):
            ui.icon("email").style(f"color:{BLUE};font-size:20px")
            ui.label("Send Action Plan to Sales Team").style(
                f"font-size:14px;font-weight:600;color:{TEXT_HEADING}"
            )
        to_input = ui.input(
            placeholder="recipient@example.com"
        ).style("width:100%").props("outlined dense dark")
        subj_input = ui.input(
            value="CyberNova Action Plan",
            placeholder="Subject"
        ).style("width:100%").props("outlined dense dark")
        body_input = ui.textarea(value=body).style(
            "width:100%;min-height:100px"
        ).props("outlined dark")

        def send():
            if not to_input.value.strip():
                ui.notify("Enter a recipient", color="warning")
                return
            try:
                api.send_email(
                    to_input.value.strip(),
                    subj_input.value,
                    body_input.value
                )
                ui.notify("Email sent!", color="positive", position="top-right")
            except APIError as e:
                ui.notify(f"Failed: {e.detail}", color="negative")

        ui.button("Send Email", icon="send", on_click=send).style(
            f"background:{BLUE};color:white;font-weight:600;border-radius:8px"
        ).props("unelevated")


# ── Chatbot ───────────────────────────────────────────────────────────────────

def _chatbot_panel(api: APIClient):
    with ui.element("div").style(
        f"{_GLASS};width:100%;overflow:hidden;"
        "display:flex;flex-direction:column"
    ):
        messages_col = ui.column().style(
            "padding:16px;gap:8px;min-height:320px;max-height:480px;"
            "overflow-y:auto;width:100%"
        )

        history = app.storage.user.get("chat_history", [])
        with messages_col:
            if not history:
                ui.label(
                    "Ask me anything about your sales data, "
                    "conversion rates, or regional performance."
                ).style(f"font-size:13px;color:{TEXT_MUTED};font-style:italic")
            else:
                for msg in history:
                    _chat_bubble(msg["role"], msg["content"])

        ui.element("div").style("height:1px;background:rgba(48,54,61,0.5)")

        with ui.row().style(
            "padding:12px 16px;gap:10px;align-items:center;width:100%"
        ):
            msg_input = ui.input(
                placeholder="Ask the AI Advisor..."
            ).style("flex:1;min-width:0").props("outlined dense dark borderless")

            def send_msg():
                text = msg_input.value.strip()
                if not text:
                    return
                msg_input.set_value("")

                with messages_col:
                    _chat_bubble("user", text)

                with messages_col:
                    loading = ui.row().classes("items-center").style("gap:6px")
                    with loading:
                        ui.spinner(size="xs").style(f"color:{PURPLE}")
                        ui.label("Thinking...").style(
                            f"font-size:12px;color:{TEXT_MUTED}"
                        )

                hist = app.storage.user.get("chat_history", [])
                try:
                    response = api.send_chat(hist, text)
                    hist.append({"role": "user",      "content": text})
                    hist.append({"role": "assistant", "content": response})
                    app.storage.user["chat_history"] = hist
                    loading.delete()
                    with messages_col:
                        _chat_bubble("assistant", response)
                except APIError as e:
                    loading.delete()
                    with messages_col:
                        ui.label(f"Error: {e.detail}").style(
                            f"color:{RED};font-size:12px"
                        )

            msg_input.on("keydown.enter", send_msg)
            ui.button(icon="send", on_click=send_msg).props(
                "flat round"
            ).style(f"color:{BLUE};flex-shrink:0")

            def clear_chat():
                app.storage.user["chat_history"] = []
                messages_col.clear()
                with messages_col:
                    ui.label(
                        "Ask me anything about your sales data."
                    ).style(f"font-size:13px;color:{TEXT_MUTED};font-style:italic")

            ui.button(icon="delete_outline", on_click=clear_chat).props(
                "flat round"
            ).style(f"color:{TEXT_MUTED};flex-shrink:0").tooltip("Clear chat")


def _chat_bubble(role: str, content: str):
    if role == "user":
        with ui.row().style("justify-content:flex-end;width:100%"):
            ui.html(
                f'<div style="background:rgba(88,166,255,0.15);'
                f'border-radius:10px 10px 2px 10px;padding:10px 14px;'
                f'max-width:72%;font-size:13px;color:{TEXT_PRIMARY};'
                f'line-height:1.5;word-wrap:break-word">{content}</div>'
            )
    else:
        with ui.row().style("justify-content:flex-start;width:100%"):
            ui.html(
                f'<div style="background:rgba(22,27,34,0.8);'
                f'border:1px solid rgba(48,54,61,0.6);'
                f'border-radius:10px 10px 10px 2px;padding:10px 14px;'
                f'max-width:72%;font-size:13px;color:{TEXT_PRIMARY};'
                f'line-height:1.5;word-wrap:break-word">{content}</div>'
            )