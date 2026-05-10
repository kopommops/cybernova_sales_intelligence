import os
import smtplib
from email.mime.text  import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth.rbac         import require_role
from api.deps.current_user import get_current_user
from api.deps.db           import get_db_path
from analytics.kpis          import get_conversion_kpi, get_anomaly_alerts
from analytics.causal        import get_causal_summary
from analytics.geo           import get_geo_dominance

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

DEMAND_THRESHOLD = int(os.getenv("DEMAND_THRESHOLD", "184"))
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama3-70b-8192")
SMTP_HOST        = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER        = os.getenv("SMTP_USER", "")
SMTP_PASS        = os.getenv("SMTP_PASS", "")

router = APIRouter(prefix="/api/manager", tags=["Sales Manager"])

_DEFAULT_START = "2026-02-06"
_DEFAULT_END   = "2026-04-06"


@router.get("/action-plan")
def action_plan(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    """
    Assembles current analytics context and sends it to Groq.
    Returns a structured action plan with prioritised recommendations,
    incorporating any active anomaly alerts automatically.
    """
    require_role(current_user["role"], "sales_manager")

    import json
    from groq import Groq

    # gather analytics context
    kpi_df     = get_conversion_kpi(db, start, end)
    alerts_df  = get_anomaly_alerts(db, start, end, threshold=DEMAND_THRESHOLD)
    causal     = get_causal_summary(db)
    geo_df     = get_geo_dominance(db, start, end)

    context = {
        "conversion_kpis":  kpi_df.to_dict(orient="records"),
        "anomaly_alerts":   alerts_df.to_dict(orient="records"),
        "causal_analysis":  causal,
        "geo_dominance":    geo_df.head(10).to_dict(orient="records"),
        "date_range":       {"start": start, "end": end},
    }

    SYSTEM_PROMPT = """
You are the CyberNova Sales Intelligence Advisor.
You receive structured analytics results from a B2B cybersecurity sales dashboard.
Your client is CyberNova Analytics Ltd, a Gaborone-based startup targeting SMEs,
financial institutions, and government agencies across Southern Africa.

Produce a JSON response with exactly these keys:
{
  "action_plan": [
    {"priority": 1, "action": "...", "rationale": "..."},
    ...up to 5 items...
  ],
  "causal_interpretation": "...",
  "regional_note": "..."
}

Rules:
- Each action must be a specific, directive sentence (e.g. "Assign two reps to Cyber Awareness Webinar recovery — it has breached the 90-session threshold on 28 days")
- Each rationale must cite at least one specific number from the input data
- Flag anomaly alerts in priority 1 with the exact breach count and affected service
- causal_interpretation must state the ATE value in percentage points and what it means for sales strategy
- regional_note must name specific SADC countries and their session share percentages
- Output ONLY valid JSON — no preamble, no markdown fences
"""

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": json.dumps(context, default=str)},
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    raw = response.choices[0].message.content

    # aggressive extraction — find first { and last }
    import re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # fallback strip
    cleaned = raw.strip()
    for prefix in ['```json', '```']:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    for suffix in ['```']:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Could not parse Groq response as JSON. "
                f"Raw: {raw[:300]}"
        )


class ChatMessage(BaseModel):
    role:    str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    history: list[ChatMessage]
    message: str

@router.post("/chat")
def chat(
    body: ChatRequest,
    db:   str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    require_role(current_user["role"], "sales_manager")

    from groq import Groq
    import json

    # pull live context so the chatbot answers from real data
    kpi_df    = get_conversion_kpi(db, _DEFAULT_START, _DEFAULT_END)
    alerts_df = get_anomaly_alerts(db, _DEFAULT_START, _DEFAULT_END,
                                   threshold=DEMAND_THRESHOLD)
    causal    = get_causal_summary(db)

    kpi_summary    = kpi_df.to_dict(orient="records")
    alerts_summary = alerts_df[["service_type","session_date","daily_sessions"]]\
                        .head(5).to_dict(orient="records")

    CHAT_SYSTEM = f"""
You are the CyberNova Sales Intelligence Advisor — a concise, data-literate
assistant for a B2B cybersecurity sales team in Southern Africa.

You have access to the following LIVE dashboard data. Always base your answers
on this data. Never invent services, figures, or trends not present here.

SERVICES IN THE DASHBOARD (these are the ONLY valid services):
- AI Cyber Assistant
- Cyber Awareness Webinar
- Network Security Audit
- Penetration Testing
- Schedule Demo

CURRENT KPIs:
{json.dumps(kpi_summary, default=str)}

ACTIVE ANOMALY ALERTS (services below demand threshold):
{json.dumps(alerts_summary, default=str)}

CAUSAL ANALYSIS RESULT:
ATE = {causal['ate_pp']} pp | Confidence = {causal['confidence_label']}
Interpretation: {causal['plain_language']}

Rules:
- Only reference services listed above
- Always cite specific numbers from the KPI data when answering
- Keep responses under 120 words unless detail is explicitly requested
- If asked something outside the dashboard data, say so clearly
"""

    messages = [{"role": "system", "content": CHAT_SYSTEM}]
    for msg in body.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

    client   = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL, messages=messages,
        temperature=0.3, max_tokens=400,
    )
    return {"response": response.choices[0].message.content}

class EmailRequest(BaseModel):
    recipient: str
    subject:   str
    body:      str


@router.post("/send-email", status_code=200)
def send_email(
    body: EmailRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Sends a pre-populated email derived from the action plan.
    REQ-15 — sales manager triggers email via CTA button.
    """
    require_role(current_user["role"], "sales_manager")

    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = body.recipient
    msg["Subject"] = body.subject
    msg.attach(MIMEText(body.body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, body.recipient, msg.as_string())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email failed to send: {str(e)}",
        )

    return {"message": f"Email sent to {body.recipient}."}


@router.get("/export-pdf")
def export_pdf(
    start: str = Query(default=_DEFAULT_START),
    end:   str = Query(default=_DEFAULT_END),
    db:    str = Depends(get_db_path),
    current_user: dict = Depends(get_current_user),
):
    """
    Generates a PDF report of current dashboard insights.
    Uses reportlab (pure Python) — no GTK/system dependencies.
    REQ-16 — sales manager exports dashboard as downloadable PDF.
    """
    require_role(current_user["role"], "sales_manager")

    import io
    from reportlab.lib          import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles   import getSampleStyleSheet
    from reportlab.lib.units    import cm
    from reportlab.platypus     import (Paragraph, SimpleDocTemplate,
                                        Spacer, Table, TableStyle)

    kpi_df    = get_conversion_kpi(db, start, end)
    alerts_df = get_anomaly_alerts(db, start, end, threshold=DEMAND_THRESHOLD)
    causal    = get_causal_summary(db)

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles   = getSampleStyleSheet()
    elements = []

    # ── Title ─────────────────────────────────────────────────────────────────
    elements.append(Paragraph("CyberNova Sales Intelligence Report", styles["Title"]))
    elements.append(Paragraph(f"Period: {start} to {end}", styles["Normal"]))
    elements.append(Paragraph(f"Generated by: {current_user['sub']}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # ── KPI table ─────────────────────────────────────────────────────────────
    elements.append(Paragraph("Conversion KPIs by Service", styles["Heading2"]))
    kpi_data = [["Service", "Sessions", "Conv Rate", "AI Engagement"]]
    for r in kpi_df.to_dict(orient="records"):
        kpi_data.append([
            str(r["service_type"]),
            f"{r['total_sessions']:,}",
            f"{r['conv_rate_pct']}%",
            f"{r['ai_engagement_pct']}%",
        ])
    kpi_table = Table(kpi_data, hAlign="LEFT")
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # ── Anomaly alerts ────────────────────────────────────────────────────────
    elements.append(Paragraph(
        f"Anomaly Alerts (threshold: {DEMAND_THRESHOLD} sessions/day)",
        styles["Heading2"]
    ))
    if len(alerts_df) == 0:
        elements.append(Paragraph("No alerts in this period.", styles["Normal"]))
    else:
        alert_data = [["Service", "Date", "Daily Sessions", "Gap"]]
        for r in alerts_df.to_dict(orient="records"):
            alert_data.append([
                str(r["service_type"]),
                str(r["session_date"])[:10],
                str(r["daily_sessions"]),
                str(r["breach_gap"]),
            ])
        alert_table = Table(alert_data, hAlign="LEFT")
        alert_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c0392b")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID",       (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        elements.append(alert_table)
    elements.append(Spacer(1, 16))

    # ── Causal analysis ───────────────────────────────────────────────────────
    elements.append(Paragraph("Causal Analysis — AI Assistant Impact", styles["Heading2"]))
    elements.append(Paragraph(causal["plain_language"], styles["Normal"]))
    elements.append(Spacer(1, 8))
    causal_data = [
        ["ATE", "95% CI Lower", "95% CI Upper", "p-value", "Confidence"],
        [
            f"{causal['ate_pp']:+.2f} pp",
            f"{causal['ci_lower']:.2f} pp",
            f"{causal['ci_upper']:.2f} pp",
            str(causal["p_value"]),
            causal["confidence_label"],
        ],
    ]
    causal_table = Table(causal_data, hAlign="LEFT")
    causal_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.grey),
    ]))
    elements.append(causal_table)

    doc.build(elements)
    buffer.seek(0)
    pdf_bytes = buffer.read()

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cybernova_report.pdf"},
    )