from nicegui import app, ui

from api_client import APIClient, APIError
from theme import (BLUE, CARD_BG, CARD_BORDER, DARK_BG,
                             GREEN, RED, TEXT_MUTED, TEXT_PRIMARY)


def render():
    ui.query("body").style(f"background:{DARK_BG};margin:0")

    with ui.column().classes("items-center justify-center").style(
        "min-height:100vh; width:100%"
    ):
        with ui.column().classes("items-center").style("margin-bottom:32px"):
            ui.image("/assets/logo_cyber_2.jpg").style("width:72px;height:72px;border-radius:30%;object-fit:cover")
            ui.label("CyberNova").style(
                f"font-size:26px;font-weight:700;color:{TEXT_PRIMARY};margin-top:8px"
            )
            ui.label("Sales Intelligence Dashboard").style(
                f"font-size:13px;color:{TEXT_MUTED};margin-top:4px"
            )

        with ui.column().style(
            f"background:{CARD_BG};border:1px solid {CARD_BORDER};"
            "border-radius:10px;padding:32px;width:360px;gap:16px"
        ):
            ui.label("Sign In").style(
                f"font-size:18px;font-weight:600;color:{TEXT_PRIMARY}"
            )

            username_input = ui.input(
                placeholder="Username"
            ).style("width:100%").props("outlined dense dark")

            password_input = ui.input(
                placeholder="Password", password=True, password_toggle_button=True
            ).style("width:100%").props("outlined dense dark")

            error_label = ui.label("").style(
                f"color:{RED};font-size:13px;min-height:18px"
            )

            def do_login():
                error_label.set_text("")
                username = username_input.value.strip()
                password = password_input.value

                if not username or not password:
                    error_label.set_text("Please enter username and password.")
                    return

                try:
                    result = APIClient.login(username, password)
                    app.storage.user["token"]    = result["access_token"]
                    app.storage.user["role"]     = result["role"]
                    app.storage.user["username"] = result["username"]

                    role = result["role"]
                    if role == "systems_manager":
                        ui.navigate.to("/dashboard/systems-manager")
                    elif role == "sales_manager":
                        ui.navigate.to("/dashboard/sales-manager")
                    else:
                        ui.navigate.to("/dashboard/salesperson")

                except APIError as e:
                    if e.status_code == 403:
                        error_label.set_text(
                            "Account pending approval by the systems manager."
                        )
                    else:
                        error_label.set_text("Invalid username or password.")

            password_input.on("keydown.enter", do_login)

            ui.button("Sign In", on_click=do_login).style(
                f"width:100%;background:{BLUE};color:white;"
                "font-weight:600;border-radius:6px"
            ).props("unelevated")

            ui.separator().style(f"border-color:{CARD_BORDER}")

            with ui.row().classes("items-center justify-center").style("gap:6px"):
                ui.label("Don't have an account?").style(
                    f"font-size:13px;color:{TEXT_MUTED}"
                )
                ui.link("Request Access", "/register").style(
                    f"font-size:13px;color:{BLUE}"
                )