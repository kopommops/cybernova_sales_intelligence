from nicegui import ui
from theme import CARD_BORDER


def _skel(h: str = "20px", w: str = "100%", radius: str = "6px"):
    ui.element("div").style(
        f"height:{h};width:{w};border-radius:{radius};"
        "background:linear-gradient(90deg,"
        "rgba(48,54,61,0.4) 25%,rgba(48,54,61,0.7) 50%,"
        "rgba(48,54,61,0.4) 75%);"
        "background-size:800px 100%;"
        "animation:shimmer 1.4s infinite linear"
    )


def kpi_skeleton():
    with ui.row().style("gap:16px;width:100%;flex-wrap:wrap"):
        for _ in range(5):
            with ui.column().style(
                "background:rgba(22,27,34,0.65);backdrop-filter:blur(18px);"
                f"border:1px solid rgba(255,255,255,0.07);border-radius:12px;"
                "padding:20px;gap:10px;flex:1;min-width:160px"
            ):
                _skel("12px", "60%")
                _skel("32px", "80%", "8px")
                _skel("12px", "50%")


def chart_skeleton(height: str = "380px"):
    with ui.element("div").style(
        "background:rgba(22,27,34,0.65);backdrop-filter:blur(18px);"
        f"border:1px solid rgba(255,255,255,0.07);border-radius:12px;"
        f"padding:20px;width:100%;height:{height};"
        "display:flex;flex-direction:column;gap:12px"
    ):
        _skel("16px", "35%")
        ui.element("div").style("flex:1").add_slot(
            "default",
            f'<div style="height:100%;border-radius:8px;" class="skeleton"></div>'
        )
        with ui.row().style("gap:12px;justify-content:center"):
            for _ in range(4):
                _skel("10px", "60px")


def table_skeleton():
    with ui.element("div").style(
        "background:rgba(22,27,34,0.65);backdrop-filter:blur(18px);"
        f"border:1px solid rgba(255,255,255,0.07);border-radius:12px;"
        "padding:20px;gap:10px;display:flex;flex-direction:column"
    ):
        _skel("16px", "40%")
        for _ in range(5):
            with ui.row().style("gap:16px;margin-top:8px"):
                _skel("14px", "30%")
                _skel("14px", "15%")
                _skel("14px", "15%")
                _skel("14px", "15%")
                _skel("14px", "15%")


def causal_skeleton():
    with ui.column().style("gap:16px;width:100%"):
        with ui.row().style("gap:16px;flex-wrap:wrap"):
            for _ in range(3):
                with ui.element("div").style(
                    "background:rgba(22,27,34,0.65);backdrop-filter:blur(18px);"
                    "border:1px solid rgba(255,255,255,0.07);border-radius:12px;"
                    "padding:20px;flex:1;min-width:160px;gap:10px;"
                    "display:flex;flex-direction:column"
                ):
                    _skel("12px", "60%")
                    _skel("36px", "70%", "8px")
        chart_skeleton("260px")