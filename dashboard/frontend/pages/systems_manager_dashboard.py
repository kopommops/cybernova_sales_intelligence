"""
frontend/pages/systems_manager_dashboard.py
--------------------------------------------
Systems Manager - REQ-17, 18, 19, 20.
Bell shows pending approvals. Delete with password confirmation. Reject pending.
"""

import tempfile
from pathlib import Path

from nicegui import app, ui
import pandas as pd
import io
from api_client import APIClient, APIError
from components.layout import build_layout
from theme import (
    BLUE, GREEN, ORANGE, PURPLE,
    RED, TEXT_HEADING, TEXT_MUTED, TEXT_PRIMARY,
)

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

    # fetch pending users for bell
    pending_users = []
    try:
        all_users    = api.get_all_users()
        pending_users = [u for u in all_users if not u["is_approved"]]
    except Exception:
        pass

    panels, tabs, bell_content = build_layout(
        default_tab="ingestion",
        alert_count=len(pending_users),
        bell_label="Pending Approvals",
        bell_icon="person_add",
        bell_colour=ORANGE,
    )

    # populate bell with pending user list
    if pending_users:
        with bell_content:
            for u in pending_users:
                with ui.element("div").style(
                    "padding:10px 16px;"
                    "border-bottom:1px solid rgba(48,54,61,0.4);"
                    "display:flex;align-items:center;gap:10px"
                ):
                    ui.html(
                        f'<div style="width:28px;height:28px;border-radius:50%;'
                        f'background:rgba(255,166,87,0.15);'
                        f'border:1px solid rgba(255,166,87,0.3);'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-size:12px;font-weight:700;color:{ORANGE};flex-shrink:0">'
                        f'{u["username"][0].upper()}</div>'
                    )
                    with ui.column().style("gap:1px;flex:1"):
                        ui.label(u["username"]).style(
                            f"font-size:12px;font-weight:600;color:{TEXT_PRIMARY}"
                        )
                        ui.label("Awaiting approval").style(
                            f"font-size:10px;color:{TEXT_MUTED}"
                        )
                    # quick approve button directly in bell
                    def quick_approve(uid=u["id"]):
                        try:
                            api.approve_user(uid, "salesperson")
                            ui.notify(
                                "User approved as salesperson",
                                color="positive", position="top-right"
                            )
                            ui.navigate.to("/dashboard/systems-manager")
                        except APIError as ex:
                            ui.notify(f"Failed: {ex.detail}", color="negative")

                    ui.button(icon="check", on_click=quick_approve).props(
                        "flat round dense"
                    ).style(f"color:{GREEN};flex-shrink:0").tooltip(
                        "Quick approve as salesperson"
                    )

            ui.label("Go to User Management for full control").style(
                f"font-size:11px;color:{TEXT_MUTED};"
                "padding:8px 16px;font-style:italic"
            )

    with panels:

        # ══ DATA INGESTION TAB ════════════════════════════════════════════════
        with ui.tab_panel("ingestion").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("Data Ingestion", "upload_file")

            with ui.element("div").style(
                "background:rgba(88,166,255,0.06);"
                "border:1px solid rgba(88,166,255,0.15);"
                "border-radius:10px;padding:14px 18px;"
                "display:flex;align-items:flex-start;gap:12px;margin-bottom:16px"
            ):
                ui.icon("info_outline").style(
                    f"color:{BLUE};font-size:18px;flex-shrink:0"
                )
                with ui.column().style("gap:4px"):
                    ui.label("IIS Log CSV Format Required").style(
                        f"font-size:13px;font-weight:600;color:{BLUE}"
                    )
                    ui.label(
                        "Upload a standard W3C Extended Log Format CSV file. "
                        "The system will validate fields, clean data, and load "
                        "all sessions into the star-schema database automatically."
                    ).style(f"font-size:12px;color:{TEXT_MUTED};line-height:1.6")

            upload_status = ui.column().style("gap:12px;width:100%")

            async def handle_upload(e):
                upload_status.clear()
                
                file_info = getattr(e, 'file', None)
                file_name = file_info.name if file_info else "Uploaded Log"
                
                with upload_status:
                    with ui.row().classes("items-center").style("gap:10px"):
                        ui.spinner("dots", size="md").style(f"color:{BLUE}")
                        ui.label(f"Processing {file_name}...").style(f"font-size:14px;color:{TEXT_MUTED}")
                
                try:
                    if not file_info:
                        raise ValueError("No file data received.")
                        
                    content_bytes = await file_info.read() 
                    
                    if not content_bytes:
                        raise ValueError("The uploaded file is empty.")

                    df = pd.read_csv(io.BytesIO(content_bytes), comment='#')
                    
                    result = api.process_and_upload_to_duckdb(df)
                    
                    upload_status.clear()
                    _upload_result(upload_status, result)
                    
                except Exception as ex:
                    upload_status.clear()
                    with upload_status:
                        with ui.row().classes("items-center").style("gap:8px"):
                            ui.icon("error").style(f"color:{RED};font-size:20px")
                            ui.label(f"Upload failed: {str(ex)}").style(f"color:{RED};font-size:13px")

            with ui.element("div").style(f"{_GLASS};padding:20px;width:100%"):
                ui.upload(
                    label="Drop CSV here or click to browse",
                    on_upload=handle_upload,
                    auto_upload=True,
                ).props("accept=.csv flat").style(
                    "width:100%;border:2px dashed rgba(88,166,255,0.3);"
                    "border-radius:12px;background:rgba(88,166,255,0.04)"
                )

            with upload_status:
                ui.label("No file uploaded yet.").style(
                    f"font-size:13px;color:{TEXT_MUTED};font-style:italic"
                )

        # ══ USER MANAGEMENT TAB ═══════════════════════════════════════════════
        with ui.tab_panel("users").style(
            "padding:24px;overflow-x:hidden;max-width:100%"
        ):
            _section("User Management", "manage_accounts")

            with ui.row().classes("items-center justify-between").style(
                "width:100%;margin-bottom:16px"
            ):
                ui.label("Registered Accounts").style(
                    f"font-size:15px;font-weight:600;color:{TEXT_HEADING}"
                )
                refresh_btn = ui.button(
                    "Refresh", icon="refresh"
                ).props("flat dense").style(f"color:{BLUE};font-size:12px")

            users_container = ui.column().style("gap:8px;width:100%")

            def load_users():
                users_container.clear()
                try:
                    users    = api.get_all_users()
                    pending  = [u for u in users if not u["is_approved"]]
                    approved = [u for u in users if u["is_approved"]]

                    with users_container:
                        if pending:
                            with ui.row().classes("items-center").style(
                                "gap:8px;margin-bottom:6px"
                            ):
                                ui.html(
                                    f'<span style="width:8px;height:8px;'
                                    f'border-radius:50%;background:{ORANGE};'
                                    f'display:inline-block"></span>'
                                )
                                ui.label(
                                    f"Pending Approval ({len(pending)})"
                                ).style(
                                    f"font-size:11px;font-weight:600;color:{ORANGE};"
                                    "text-transform:uppercase;letter-spacing:0.06em"
                                )
                            for u in pending:
                                _pending_row(u, api, load_users)

                            ui.element("div").style(
                                "height:1px;background:rgba(48,54,61,0.5);"
                                "margin:12px 0"
                            )

                        with ui.row().classes("items-center").style(
                            "gap:8px;margin-bottom:6px"
                        ):
                            ui.icon("check_circle").style(
                                f"font-size:14px;color:{GREEN}"
                            )
                            ui.label(
                                f"Approved Users ({len(approved)})"
                            ).style(
                                f"font-size:11px;font-weight:600;color:{TEXT_MUTED};"
                                "text-transform:uppercase;letter-spacing:0.06em"
                            )
                        for u in approved:
                            _approved_row(u, api, load_users, token)

                except APIError as ex:
                    with users_container:
                        with ui.row().classes("items-center").style("gap:8px"):
                            ui.icon("error_outline").style(
                                f"color:{RED};font-size:18px"
                            )
                            ui.label(f"Failed to load users: {ex.detail}").style(
                                f"color:{RED};font-size:13px"
                            )

            refresh_btn.on_click(load_users)
            load_users()


# ── Pending user row (approve + reject) ───────────────────────────────────────

def _pending_row(user: dict, api: APIClient, refresh_fn):
    ROLE_OPTS = ["salesperson", "sales_manager", "systems_manager"]

    with ui.row().classes("items-center").style(
        "background:rgba(255,166,87,0.05);"
        "border:1px solid rgba(255,166,87,0.2);"
        "border-radius:10px;padding:12px 16px;"
        "gap:12px;width:100%"
    ):
        ui.html(
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:rgba(255,166,87,0.15);'
            f'border:1px solid rgba(255,166,87,0.4);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:14px;font-weight:700;color:{ORANGE};flex-shrink:0">'
            f'{user["username"][0].upper()}</div>'
        )
        with ui.column().style("gap:2px;flex:1;min-width:0"):
            ui.label(user["username"]).style(
                f"font-size:14px;font-weight:600;color:{TEXT_PRIMARY}"
            )
            with ui.row().classes("items-center").style("gap:6px"):
                ui.html(
                    f'<span style="background:rgba(255,166,87,0.12);'
                    f'color:{ORANGE};padding:2px 8px;border-radius:12px;'
                    f'font-size:11px;font-weight:600">Pending</span>'
                )

        role_select = ui.select(
            options=ROLE_OPTS, value="salesperson", label=""
        ).style("min-width:150px;max-width:180px").props("outlined dense dark")

        def approve(uid=user["id"], sel=role_select):
            try:
                api.approve_user(uid, sel.value)
                ui.notify(
                    f"{user['username']} approved as {sel.value}",
                    color="positive", position="top-right"
                )
                refresh_fn()
            except APIError as ex:
                ui.notify(f"Failed: {ex.detail}", color="negative")

        def reject(uid=user["id"], uname=user["username"]):
            with ui.dialog() as confirm_dlg, ui.card().style(
                f"background:#161B22;border:1px solid #30363D;"
                "border-radius:10px;padding:24px;gap:16px;min-width:320px"
            ):
                with ui.column().style("gap:12px;width:100%"):
                    with ui.row().classes("items-center").style("gap:8px"):
                        ui.icon("person_remove").style(
                            f"color:{RED};font-size:20px"
                        )
                        ui.label(f"Reject '{uname}'?").style(
                            f"font-size:15px;font-weight:600;color:{TEXT_PRIMARY}"
                        )
                    ui.label(
                        "This will permanently remove their registration request."
                    ).style(f"font-size:13px;color:{TEXT_MUTED};line-height:1.5")
                    with ui.row().style("gap:8px;justify-content:flex-end;width:100%"):
                        ui.button("Cancel", on_click=confirm_dlg.close).props(
                            "flat"
                        ).style(f"color:{TEXT_MUTED}")

                        def do_reject():
                            try:
                                api._post(f"/auth/reject/{uid}", {})
                                ui.notify(
                                    f"Registration for '{uname}' rejected.",
                                    color="warning", position="top-right"
                                )
                                confirm_dlg.close()
                                refresh_fn()
                            except Exception as ex:
                                ui.notify(f"Failed: {str(ex)}", color="negative")

                        ui.button(
                            "Reject", icon="delete", on_click=do_reject
                        ).style(
                            f"background:{RED};color:white;border-radius:8px"
                        ).props("unelevated")

            confirm_dlg.open()

        ui.button("Approve", icon="check_circle", on_click=approve).style(
            f"background:rgba(63,185,80,0.15);color:{GREEN};"
            f"border:1px solid rgba(63,185,80,0.3);border-radius:8px;"
            "font-weight:600;font-size:12px"
        ).props("dense flat")

        ui.button("Reject", icon="close", on_click=reject).style(
            f"background:rgba(247,129,102,0.1);color:{RED};"
            f"border:1px solid rgba(247,129,102,0.3);border-radius:8px;"
            "font-weight:600;font-size:12px"
        ).props("dense flat")


# ── Approved user row (role change + delete with password) ────────────────────

def _approved_row(user: dict, api: APIClient, refresh_fn, token: str):
    ROLE_OPTS    = ["salesperson", "sales_manager", "systems_manager"]
    role_colour  = {
        "salesperson":    BLUE,
        "sales_manager":  PURPLE,
        "systems_manager": ORANGE,
    }.get(user["role"], BLUE)

    current_username = app.storage.user.get("username", "")
    is_self = user["username"] == current_username

    with ui.row().classes("items-center").style(
        "background:rgba(22,27,34,0.5);"
        "border:1px solid rgba(48,54,61,0.5);"
        "border-radius:10px;padding:12px 16px;"
        "gap:12px;width:100%"
    ):
        ui.html(
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:rgba({_rgb(role_colour)},0.15);'
            f'border:1px solid rgba({_rgb(role_colour)},0.4);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:14px;font-weight:700;color:{role_colour};flex-shrink:0">'
            f'{user["username"][0].upper()}</div>'
        )
        with ui.column().style("gap:2px;flex:1;min-width:0"):
            with ui.row().classes("items-center").style("gap:6px"):
                ui.label(user["username"]).style(
                    f"font-size:14px;font-weight:600;color:{TEXT_PRIMARY}"
                )
                if is_self:
                    ui.html(
                        f'<span style="background:rgba(88,166,255,0.12);'
                        f'color:{BLUE};padding:1px 6px;border-radius:8px;'
                        f'font-size:10px;font-weight:600">You</span>'
                    )
            ui.html(
                f'<span style="background:rgba({_rgb(role_colour)},0.12);'
                f'color:{role_colour};padding:2px 8px;border-radius:12px;'
                f'font-size:11px;font-weight:600">'
                f'{user["role"].replace("_"," ").title()}</span>'
            )

        role_select = ui.select(
            options=ROLE_OPTS, value=user["role"], label=""
        ).style("min-width:150px;max-width:180px").props("outlined dense dark")

        def change_role(uid=user["id"], sel=role_select):
            try:
                api.change_role(uid, sel.value)
                ui.notify(
                    f"Role updated to {sel.value}",
                    color="positive", position="top-right"
                )
                refresh_fn()
            except APIError as ex:
                ui.notify(f"Failed: {ex.detail}", color="negative")

        ui.button("Update", icon="save", on_click=change_role).style(
            f"color:{BLUE};font-size:12px"
        ).props("dense flat")

        # Delete button — disabled for self
        if not is_self:
            def delete(uid=user["id"], uname=user["username"]):
                with ui.dialog() as del_dlg, ui.card().style(
                    f"background:#161B22;border:1px solid #30363D;"
                    "border-radius:10px;padding:24px;gap:16px;min-width:340px"
                ):
                    with ui.column().style("gap:12px;width:100%"):
                        with ui.row().classes("items-center").style("gap:8px"):
                            ui.icon("delete_forever").style(
                                f"color:{RED};font-size:20px"
                            )
                            ui.label(f"Delete '{uname}'?").style(
                                f"font-size:15px;font-weight:600;color:{TEXT_PRIMARY}"
                            )
                        ui.label(
                            "This action is permanent and cannot be undone. "
                            "Please re-enter your password to confirm."
                        ).style(
                            f"font-size:13px;color:{TEXT_MUTED};line-height:1.5"
                        )
                        pw_input = ui.input(
                            placeholder="Your password",
                            password=True,
                            password_toggle_button=True
                        ).style("width:100%").props("outlined dense dark")
                        err_label = ui.label("").style(
                            f"color:{RED};font-size:12px;min-height:16px"
                        )
                        with ui.row().style(
                            "gap:8px;justify-content:flex-end;width:100%"
                        ):
                            ui.button(
                                "Cancel", on_click=del_dlg.close
                            ).props("flat").style(f"color:{TEXT_MUTED}")

                            def do_delete():
                                if not pw_input.value.strip():
                                    err_label.set_text(
                                        "Password is required."
                                    )
                                    return
                                try:
                                    api.delete_user(uid, pw_input.value)
                                    ui.notify(
                                        f"User '{uname}' deleted.",
                                        color="positive",
                                        position="top-right"
                                    )
                                    del_dlg.close()
                                    refresh_fn()
                                except APIError as ex:
                                    err_label.set_text(ex.detail)

                            ui.button(
                                "Delete", icon="delete_forever",
                                on_click=do_delete
                            ).style(
                                f"background:{RED};color:white;"
                                "border-radius:8px"
                            ).props("unelevated")

                del_dlg.open()

            ui.button(
                icon="delete_outline", on_click=delete
            ).props("flat round dense").style(
                f"color:{RED};flex-shrink:0"
            ).tooltip(f"Delete {user['username']}")


# ── Upload result ─────────────────────────────────────────────────────────────

def _upload_result(container, result: dict):
    with container:
        colour = GREEN if result["req26_pass"] else ORANGE
        icon   = "check_circle" if result["req26_pass"] else "warning"

        with ui.row().classes("items-center").style(
            "gap:10px;margin-bottom:8px"
        ):
            ui.icon(icon).style(f"color:{colour};font-size:24px")
            with ui.column().style("gap:2px"):
                ui.label(
                    "Upload Successful" if result["req26_pass"]
                    else "Upload Complete - Review Warnings"
                ).style(f"font-size:15px;font-weight:700;color:{colour}")
                ui.label(result["message"]).style(
                    f"font-size:12px;color:{TEXT_MUTED}"
                )

        with ui.row().style("gap:12px;flex-wrap:wrap;width:100%"):
            for icon_name, label, value, col in [
                ("upload",           "Raw Rows",
                 f"{result['raw_rows']:,}",           BLUE),
                ("cleaning_services","Clean Rows",
                 f"{result['clean_rows']:,}",          GREEN),
                ("smart_toy",        "Bot Rows",
                 f"{result['bot_rows']:,}",            TEXT_MUTED),
                ("storage",          "Sessions Loaded",
                 f"{result['dim_session_rows']:,}",    PURPLE),
                ("verified",         "Parse Accuracy",
                 f"{result['parse_accuracy_pct']}%",  colour),
            ]:
                with ui.element("div").style(
                    "background:rgba(22,27,34,0.6);"
                    "border:1px solid rgba(48,54,61,0.5);"
                    "border-radius:10px;padding:14px 18px;"
                    "flex:1;min-width:120px;display:flex;flex-direction:column;gap:4px"
                ):
                    with ui.row().classes("items-center").style("gap:6px"):
                        ui.icon(icon_name).style(f"font-size:14px;color:{col}")
                        ui.label(label).style(
                            f"font-size:10px;color:{TEXT_MUTED};"
                            "text-transform:uppercase;letter-spacing:0.05em"
                        )
                    ui.label(value).style(
                        f"font-size:20px;font-weight:700;color:{col}"
                    )

        ui.label("Field Validation Report").style(
            f"font-size:13px;font-weight:600;color:{TEXT_HEADING};margin-top:8px"
        )
        cols = [
            {"name": "field",      "label": "Field",
             "field": "field",      "align": "left"},
            {"name": "status",     "label": "Status",
             "field": "status",     "align": "left"},
            {"name": "null_count", "label": "Nulls",
             "field": "null_count", "align": "right"},
        ]
        rows = [{
            "field":      f["field"],
            "status":     f["status"],
            "null_count": f["null_count"] if f["null_count"] is not None else "-",
        } for f in result["fields"]]
        with ui.element("div").style(
            "background:rgba(22,27,34,0.5);border-radius:10px;"
            "overflow:hidden;width:100%"
        ):
            ui.table(
                columns=cols, rows=rows, row_key="field"
            ).style("width:100%").props("dense flat")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(text: str, icon: str):
    with ui.row().classes("items-center").style("gap:8px;margin-bottom:16px"):
        ui.icon(icon).style(f"color:{BLUE};font-size:20px")
        ui.label(text).style(
            f"font-size:16px;font-weight:600;color:{TEXT_HEADING}"
        )


def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"