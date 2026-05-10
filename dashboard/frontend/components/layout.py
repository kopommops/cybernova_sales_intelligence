"""
frontend/components/layout.py
"""

from nicegui import app, ui
from theme import (
    BLUE, GREEN, NAV_HEIGHT, ORANGE, PURPLE, RED,
    ROLE_COLOURS, TEXT_HEADING, TEXT_MUTED, TEXT_PRIMARY,
)

TABS = {
    "salesperson": [
        ("overview",  "dashboard",      "Overview"),
        ("demand",    "bar_chart",      "Demand"),
        ("heatmap",   "grid_on",        "Heatmap"),
        ("funnel",    "filter_alt",     "Funnel"),
        ("ai",        "smart_toy",      "AI Engagement"),
        ("stats",     "table_chart",    "Statistics"),
        ("causal",    "hub",            "Causal"),
    ],
    "sales_manager": [
        ("overview",  "dashboard",      "Overview"),
        ("demand",    "bar_chart",      "Demand"),
        ("heatmap",   "grid_on",        "Heatmap"),
        ("funnel",    "filter_alt",     "Funnel"),
        ("ai",        "smart_toy",      "AI Engagement"),
        ("stats",     "table_chart",    "Statistics"),
        ("causal",    "hub",            "Causal"),
        ("regional",  "public",         "Regional"),
        ("action",    "lightbulb",      "Action Plan"),
        ("advisor",   "chat",           "AI Advisor"),
        ("export",    "picture_as_pdf", "Export"),
    ],
    "systems_manager": [
        ("ingestion", "upload_file",     "Data Ingestion"),
        ("users",     "manage_accounts", "User Management"),
    ],
}


def build_layout(
    default_tab:  str = None,
    alert_count:  int = 0,
    bell_label:   str = "Demand Alerts",
    bell_icon:    str = "warning_amber",
    bell_colour:  str = None,
) -> tuple:
    role        = app.storage.user.get("role", "salesperson")
    username    = app.storage.user.get("username", "User")
    tab_defs    = TABS.get(role, TABS["salesperson"])
    first       = default_tab or tab_defs[0][0]
    role_colour = ROLE_COLOURS.get(role, BLUE)
    role_label  = role.replace("_", " ").title()
    _bell_colour = bell_colour or RED

    dd_state   = {"open": False}
    bell_state = {"open": False}

    with ui.element("div").style(
        f"position:sticky;top:0;z-index:100;width:100%;"
        f"height:{NAV_HEIGHT};"
        "background:rgba(13,17,23,0.92);"
        "backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);"
        "border-bottom:1px solid rgba(48,54,61,0.7);"
        "display:flex;align-items:center;padding:0 16px;gap:0;"
        "overflow:visible"
    ):
        # Logo
        with ui.row().classes("items-center").style(
            "gap:8px;flex-shrink:0;margin-right:16px"
        ):
            ui.image("/assets/logo_cyber_2.jpg").style(
                "width:26px;height:26px;border-radius:6px;object-fit:cover"
            )
            ui.label("CyberNova").style(
                f"font-size:14px;font-weight:700;color:{TEXT_HEADING};"
                "white-space:nowrap"
            )

        # Tabs
        tabs = ui.tabs(value=first).style(
            "flex:1;min-width:0;overflow-x:auto;scrollbar-width:none"
        ).props("dense align='left' indicator-color='blue-5'")

        with tabs:
            for key, icon_name, label in tab_defs:
                with ui.tab(key, label="").props("no-caps").style(
                    f"color:{TEXT_MUTED};min-width:unset;padding:0 10px"
                ):
                    with ui.row().classes("items-center").style("gap:4px"):
                        ui.icon(icon_name).style("font-size:15px")
                        ui.label(label).style(
                            "font-size:12px;font-weight:500"
                        )

        # Bell
        bell_wrapper = ui.element("div").style(
            "position:relative;flex-shrink:0;margin-left:8px;overflow:visible"
        )
        with bell_wrapper:
            def toggle_bell():
                bell_state["open"] = not bell_state["open"]
                bell_panel.set_visibility(bell_state["open"])
                dd_state["open"] = False
                dd_panel.set_visibility(False)

            with ui.element("div").style(
                "position:relative;cursor:pointer;padding:6px;"
                "border-radius:8px;transition:background 0.15s"
            ).on("click", toggle_bell):
                ui.icon("notifications").style(
                    f"font-size:20px;"
                    f"color:{_bell_colour if alert_count > 0 else TEXT_MUTED}"
                )
                if alert_count > 0:
                    ui.html(
                        f'<span style="position:absolute;top:2px;right:2px;'
                        f'width:16px;height:16px;border-radius:50%;'
                        f'background:{_bell_colour};color:white;font-size:9px;'
                        f'font-weight:700;display:flex;align-items:center;'
                        f'justify-content:center;pointer-events:none">'
                        f'{min(alert_count, 99)}</span>'
                    )

            bell_panel = ui.element("div").style(
                "position:fixed;top:58px;right:56px;"
                "background:rgba(18,22,29,0.98);"
                "backdrop-filter:blur(24px);"
                "-webkit-backdrop-filter:blur(24px);"
                "border:1px solid rgba(48,54,61,0.9);"
                "border-radius:10px;padding:0;"
                "min-width:320px;max-width:380px;"
                "box-shadow:0 8px 32px rgba(0,0,0,0.7);"
                "z-index:9999;overflow:hidden"
            )
            bell_panel.set_visibility(False)

            with bell_panel:
                # Header
                with ui.row().classes("items-center justify-between").style(
                    f"padding:12px 16px;"
                    f"border-bottom:1px solid rgba(48,54,61,0.6)"
                ):
                    with ui.row().classes("items-center").style("gap:6px"):
                        ui.icon(bell_icon).style(
                            f"font-size:16px;color:{_bell_colour}"
                        )
                        ui.label(bell_label).style(
                            f"font-size:13px;font-weight:600;color:{TEXT_PRIMARY}"
                        )
                    if alert_count > 0:
                        ui.html(
                            f'<span style="background:rgba(255,255,255,0.08);'
                            f'color:{_bell_colour};padding:2px 8px;'
                            f'border-radius:12px;font-size:11px;font-weight:600">'
                            f'{alert_count} pending</span>'
                        )

                bell_content = ui.column().style(
                    "max-height:280px;overflow-y:auto;width:100%"
                )
                with bell_content:
                    if alert_count == 0:
                        with ui.row().classes("items-center justify-center").style(
                            "padding:24px;gap:8px"
                        ):
                            ui.icon("check_circle").style(
                                f"color:{GREEN};font-size:20px"
                            )
                            ui.label("No active alerts").style(
                                f"font-size:13px;color:{TEXT_MUTED}"
                            )

        # User pill
        pill_wrapper = ui.element("div").style(
            "position:relative;flex-shrink:0;margin-left:8px;overflow:visible"
        )
        with pill_wrapper:
            def toggle_dd():
                dd_state["open"] = not dd_state["open"]
                dd_panel.set_visibility(dd_state["open"])
                bell_state["open"] = False
                bell_panel.set_visibility(False)

            with ui.row().classes("items-center").style(
                "gap:6px;padding:5px 10px;border-radius:20px;"
                "background:rgba(255,255,255,0.06);"
                "border:1px solid rgba(255,255,255,0.08);"
                "cursor:pointer;user-select:none"
            ).on("click", toggle_dd):
                ui.html(
                    f'<div style="width:22px;height:22px;border-radius:50%;'
                    f'background:rgba({_rgb(role_colour)},0.2);'
                    f'border:1px solid rgba({_rgb(role_colour)},0.5);'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'font-size:11px;font-weight:700;color:{role_colour}">'
                    f'{username[0].upper()}</div>'
                )
                with ui.column().style("gap:0;line-height:1.2"):
                    ui.label(username).style(
                        f"font-size:12px;font-weight:600;color:{TEXT_PRIMARY};"
                        "white-space:nowrap"
                    )
                    ui.label(role_label).style(
                        f"font-size:10px;color:{role_colour};white-space:nowrap"
                    )
                ui.icon("expand_more").style(
                    f"font-size:14px;color:{TEXT_MUTED}"
                )

            dd_panel = ui.element("div").style(
                "position:fixed;top:58px;right:12px;"
                "background:rgba(18,22,29,0.98);"
                "backdrop-filter:blur(24px);"
                "-webkit-backdrop-filter:blur(24px);"
                "border:1px solid rgba(48,54,61,0.9);"
                "border-radius:10px;padding:6px;min-width:176px;"
                "box-shadow:0 8px 32px rgba(0,0,0,0.7);"
                "z-index:9999"
            )
            dd_panel.set_visibility(False)

            with dd_panel:
                with ui.column().style("gap:2px;width:100%"):
                    with ui.row().classes("items-center").style(
                        "gap:8px;padding:8px 10px;border-radius:6px"
                    ):
                        ui.icon("account_circle").style(
                            f"font-size:20px;color:{role_colour}"
                        )
                        with ui.column().style("gap:1px"):
                            ui.label(username).style(
                                f"font-size:12px;font-weight:600;color:{TEXT_PRIMARY}"
                            )
                            ui.label(role_label).style(
                                f"font-size:10px;color:{role_colour}"
                            )
                    ui.element("div").style(
                        "height:1px;background:rgba(48,54,61,0.6);margin:2px 4px"
                    )

                    def do_logout():
                        app.storage.user.clear()
                        ui.navigate.to("/login")

                    with ui.row().classes("items-center").style(
                        f"gap:8px;padding:8px 10px;border-radius:6px;"
                        "cursor:pointer;width:100%"
                    ).on("click", do_logout):
                        ui.icon("logout").style(f"font-size:16px;color:{RED}")
                        ui.label("Sign Out").style(
                            f"font-size:13px;color:{RED};font-weight:500"
                        )

    panels = ui.tab_panels(tabs, value=first).style(
        "background:transparent;width:100%;max-width:100%;"
        "overflow-x:hidden;overflow-y:auto"
    )

    return panels, tabs, bell_content


def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"