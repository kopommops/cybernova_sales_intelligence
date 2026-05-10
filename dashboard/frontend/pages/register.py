from nicegui import ui

from api_client import APIClient, APIError
from theme import (BLUE, CARD_BG, CARD_BORDER, DARK_BG,
                             GREEN, RED, TEXT_MUTED, TEXT_PRIMARY)


def render():
    ui.query("body").style(f"background:{DARK_BG};margin:0")

    with ui.column().classes("items-center justify-center").style(
        "min-height:100vh;width:100%"
    ):
        with ui.column().style(
            f"background:{CARD_BG};border:1px solid {CARD_BORDER};"
            "border-radius:10px;padding:32px;width:360px;gap:16px"
        ):
            with ui.row().classes("items-center").style("gap:10px;margin-bottom:4px"):
                ui.image('/assets/logo_cyber_2.jpg').style("width:32px;height:32px;border-radius:30%;object-fit:cover")
                ui.label("Request Access").style(
                    f"font-size:18px;font-weight:600;color:{TEXT_PRIMARY}"
                )

            ui.label(
                "Your account will be reviewed by the systems manager "
                "before access is granted."
            ).style(f"font-size:13px;color:{TEXT_MUTED};line-height:1.5")

            username_input = ui.input(
                placeholder="Choose a username"
            ).style("width:100%").props("outlined dense dark")

            password_input = ui.input(
                placeholder="Password (min 8 characters)",
                password=True, password_toggle_button=True
            ).style("width:100%").props("outlined dense dark")

            confirm_input = ui.input(
                placeholder="Confirm password",
                password=True, password_toggle_button=True
            ).style("width:100%").props("outlined dense dark")

            message_label = ui.label("").style(
                "font-size:13px;min-height:18px"
            )

            def do_register():
                message_label.style(f"color:{RED}")
                message_label.set_text("")
                username = username_input.value.strip()
                password = password_input.value
                confirm  = confirm_input.value

                if not username or not password:
                    message_label.set_text("All fields are required.")
                    return
                if len(password) < 8:
                    message_label.set_text("Password must be at least 8 characters.")
                    return
                if password != confirm:
                    message_label.set_text("Passwords do not match.")
                    return

                try:
                    APIClient.register(username, password)
                    message_label.style(f"color:{GREEN}")
                    message_label.set_text(
                        "Account created. Awaiting systems manager approval."
                    )
                    username_input.set_value("")
                    password_input.set_value("")
                    confirm_input.set_value("")
                except APIError as e:
                    if e.status_code == 409:
                        message_label.set_text(
                            f"Username '{username}' is already taken."
                        )
                    elif e.status_code == 422:
                        message_label.set_text(
                            "Username must be at least 3 characters."
                        )
                    else:
                        message_label.set_text(f"Registration failed: {e.detail}")

            ui.button("Request Account", on_click=do_register).style(
                f"width:100%;background:{BLUE};color:white;"
                "font-weight:600;border-radius:6px"
            ).props("unelevated")

            ui.separator().style(f"border-color:{CARD_BORDER}")

            with ui.row().classes("items-center justify-center").style("gap:6px"):
                ui.label("Already have an account?").style(
                    f"font-size:13px;color:{TEXT_MUTED}"
                )
                ui.link("Sign In", "/login").style(
                    f"font-size:13px;color:{BLUE}"
                )