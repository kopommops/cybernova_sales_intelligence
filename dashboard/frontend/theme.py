DARK_BG      = "#0D1117"
CARD_BG      = "#161B22"
CARD_BORDER  = "#30363D"
SIDEBAR_BG   = "#0D1117"

TEXT_PRIMARY = "#C9D1D9"
TEXT_MUTED   = "#8B949E"
TEXT_HEADING = "#F0F6FC"

BLUE         = "#58A6FF"
GREEN        = "#3FB950"
RED          = "#F78166"
PURPLE       = "#D2A8FF"
ORANGE       = "#FFA657"
YELLOW       = "#E3B341"

PALETTE      = [BLUE, GREEN, RED, PURPLE, ORANGE, YELLOW,
                "#79C0FF", "#56D364", "#FF7B72"]

ROLE_COLOURS = {
    "salesperson":     BLUE,
    "sales_manager":   PURPLE,
    "systems_manager": ORANGE,
}

FONT_FAMILY  = "Inter, system-ui, sans-serif"
CARD_RADIUS  = "10px"
NAV_HEIGHT   = "56px"

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  font-family: {FONT_FAMILY};
  background: linear-gradient(160deg, #0D1117 0%, #111827 60%, #0f172a 100%) !important;
  color: {TEXT_PRIMARY};
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── Glassmorphism card ──────────────────────────────── */
.glass {{
  background: rgba(22, 27, 34, 0.65) !important;
  backdrop-filter: blur(18px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 24px rgba(0,0,0,0.35),
              inset 0 1px 0 rgba(255,255,255,0.05) !important;
  transition: box-shadow 0.25s ease, border-color 0.25s ease !important;
}}
.glass:hover {{
  border-color: rgba(88,166,255,0.18) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5),
              inset 0 1px 0 rgba(255,255,255,0.07) !important;
}}

/* ── Top navbar ─────────────────────────────────────── */
.cn-navbar {{
  position: sticky; top: 0; z-index: 100;
  height: {NAV_HEIGHT};
  background: rgba(13,17,23,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(48,54,61,0.7);
  display: flex; align-items: center;
  padding: 0 24px; gap: 0;
  width: 100%;
}}

/* ── Nav tabs ───────────────────────────────────────── */
.cn-tab {{
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 7px;
  font-size: 13px; font-weight: 500;
  color: {TEXT_MUTED}; cursor: pointer;
  text-decoration: none;
  transition: color 0.15s, background 0.15s;
  border: none; background: transparent;
  white-space: nowrap;
}}
.cn-tab:hover {{
  color: {TEXT_PRIMARY};
  background: rgba(255,255,255,0.06);
}}
.cn-tab.active {{
  color: {BLUE};
  background: rgba(88,166,255,0.12);
}}

/* ── User pill dropdown ─────────────────────────────── */
.cn-user-pill {{
  display: flex; align-items: center; gap: 8px;
  padding: 6px 14px; border-radius: 20px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
  transition: background 0.15s;
}}
.cn-user-pill:hover {{
  background: rgba(255,255,255,0.1);
}}
.cn-dropdown {{
  position: absolute; top: calc({NAV_HEIGHT} - 4px); right: 16px;
  background: rgba(22,27,34,0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(48,54,61,0.8);
  border-radius: 10px;
  padding: 6px;
  min-width: 180px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  z-index: 200;
}}

/* ── Skeleton loader ────────────────────────────────── */
@keyframes shimmer {{
  0%   {{ background-position: -800px 0; }}
  100% {{ background-position:  800px 0; }}
}}
.skeleton {{
  background: linear-gradient(
    90deg,
    rgba(48,54,61,0.4) 25%,
    rgba(48,54,61,0.7) 50%,
    rgba(48,54,61,0.4) 75%
  );
  background-size: 800px 100%;
  animation: shimmer 1.4s infinite linear;
  border-radius: 6px;
}}

/* ── Fade-in ────────────────────────────────────────── */
@keyframes fadeUp {{
  from {{ opacity:0; transform:translateY(10px); }}
  to   {{ opacity:1; transform:translateY(0);    }}
}}
.fade-up {{ animation: fadeUp 0.3s ease forwards; }}

/* ── Content area ───────────────────────────────────── */
.cn-content {{
  padding: 24px;
  max-width: 100%;
  overflow-x: hidden;
}}

/* ── Plotly responsive fix ──────────────────────────── */
.js-plotly-plot, .plotly, .plot-container {{
  width: 100% !important;
  max-width: 100% !important;
}}
.js-plotly-plot .plotly {{
  background: transparent !important;
}}

/* ── Tables ─────────────────────────────────────────── */
.q-table {{
  background: transparent !important;
  color: {TEXT_PRIMARY} !important;
  width: 100% !important;
}}
.q-table thead tr th {{
  background: rgba(13,17,23,0.6) !important;
  color: {TEXT_MUTED} !important;
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; font-weight: 600;
}}
.q-table tbody tr:hover {{
  background: rgba(48,54,61,0.3) !important;
}}

/* ── Inputs ─────────────────────────────────────────── */
.q-field__control {{
  background: rgba(22,27,34,0.8) !important;
  border-color: rgba(48,54,61,0.8) !important;
}}
.q-field__native, .q-field__input {{
  color: {TEXT_PRIMARY} !important;
}}

/* ── Scrollbar ──────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
  background: rgba(48,54,61,0.8);
  border-radius: 3px;
}}

/* ── Prevent horizontal overflow ────────────────────── */
.q-page, .q-page-container, .nicegui-content {{
  overflow-x: hidden !important;
  max-width: 100vw !important;
}}

.q-page, .q-page-container {{
  overflow: visible !important;
}}

.q-tab--active {{
    position: relative;
}}
.q-tab--active::after {{
    content: '';
    position: absolute;
    bottom: 0;
    left: 10%;
    width: 80%;
    height: 2px;
    background: linear-gradient(90deg, #58A6FF, #D2A8FF);
    border-radius: 2px;
}}

</style>
"""