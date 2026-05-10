from nicegui import app, ui

from theme import GLOBAL_CSS
app.add_static_files('/assets', 'dashboard/frontend/assets')

ui.add_head_html(GLOBAL_CSS,shared=True)
ui.add_head_html(
    '<link rel="icon" href="https://cdn-icons-png.flaticon.com/512/2092/2092663.png">',
    shared=True
)

def _get_token() -> str | None:
    return app.storage.user.get("token")

def _get_role() -> str | None:
    return app.storage.user.get("role")

def _require_auth(minimum_role: str = "salesperson"):
    """Redirect to login if not authenticated or wrong role."""
    from theme import ROLE_COLOURS
    ROLE_LEVEL = {"salesperson": 1, "sales_manager": 2, "systems_manager": 3}
    token = _get_token()
    role  = _get_role()
    if not token:
        ui.navigate.to("/login")
        return False
    if ROLE_LEVEL.get(role, 0) < ROLE_LEVEL.get(minimum_role, 99):
        ui.navigate.to("/login")
        return False
    return True

@ui.page("/")
def index():
    ui.navigate.to("/login")


@ui.page("/login")
def login_page():
    from pages.login import render
    render()


@ui.page("/register")
def register_page():
    from pages.register import render
    render()


@ui.page("/dashboard/salesperson")
def salesperson_page():
    if not _require_auth("salesperson"):
        return
    from pages.salesperson_dashboard import render
    render()


@ui.page("/dashboard/sales-manager")
def sales_manager_page():
    if not _require_auth("sales_manager"):
        return
    from pages.sales_manager_dashboard import render
    render()


@ui.page("/dashboard/systems-manager")
def systems_manager_page():
    if not _require_auth("systems_manager"):
        return
    from pages.systems_manager_dashboard import render
    render()

if __name__ == "__main__":
    ui.run(
        title="CyberNova Sales Intelligence",
        dark=True,
        port=8081,
        reload=False,
        favicon="/assets/favicon.ico",
        storage_secret="cybernova-storage-secret-2026",
    )