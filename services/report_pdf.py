"""
PDF Report generation service using ReportLab and Matplotlib.
Produces multi-page, executive decision-support audit reports with embedded charts,
financial KPI summaries, product rankings, alert manifests, and recommendations.
"""
import io
import os
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
)
from reportlab.pdfgen import canvas
from config import Config

class NumberedCanvas(canvas.Canvas):
    """Adds page numbers and footer to each page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 30, "Business Loss Detection & Decision Support System — Confidential Internal Report")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 30, page_text)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 42, 612 - 54, 42)
        self.restoreState()

def generate_monthly_chart_image(monthly_trends: list) -> io.BytesIO:
    """Generates a high-res chart showing Monthly Revenue vs Expenses and Net Profit."""
    if not monthly_trends:
        return None

    months = [m["month"] for m in monthly_trends]
    revenues = [m["revenue"] for m in monthly_trends]
    expenses = [m["operating_expenses"] + m["product_cost"] for m in monthly_trends]
    net_profits = [m["net_profit"] for m in monthly_trends]

    fig, ax1 = plt.subplots(figsize=(7.5, 3.2), dpi=200)
    fig.patch.set_facecolor("#f8fafc")
    ax1.set_facecolor("#ffffff")

    x = range(len(months))
    width = 0.35

    ax1.bar([i - width/2 for i in x], revenues, width=width, label="Total Revenue", color="#0d9488", alpha=0.9)
    ax1.bar([i + width/2 for i in x], expenses, width=width, label="Total Costs & Expenses", color="#e11d48", alpha=0.85)

    ax1.set_ylabel("INR (₹)", color="#1e293b", fontsize=9, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, fontsize=8, color="#334155")
    ax1.tick_params(axis="y", labelsize=8)
    ax1.grid(axis="y", linestyle="--", alpha=0.3, color="#94a3b8")

    # Net profit line overlay
    ax2 = ax1.twinx()
    ax2.plot(x, net_profits, color="#0284c7", marker="o", linewidth=2, label="Net Profit")
    ax2.axhline(0, color="#64748b", linestyle=":", linewidth=1)
    ax2.set_ylabel("Net Profit (₹)", color="#0284c7", fontsize=9, fontweight="bold")
    ax2.tick_params(axis="y", labelsize=8)

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8, framealpha=0.9)

    plt.title("Monthly Financial Performance: Revenue, Total Costs, & Net Profit", fontsize=10, fontweight="bold", pad=12, color="#0f172a")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def build_pdf_report(
    business_name: str,
    dataset_info: dict,
    kpis: dict,
    monthly_trends: list,
    product_performance: list,
    expense_dist: list,
    alerts_list: list,
) -> bytes:
    """Builds a complete PDF report and returns raw PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )
    small_style = ParagraphStyle(
        "SmallDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph("Business Loss Detection & Decision Support Report", title_style))
    story.append(Spacer(1, 4))
    d_span = f"{dataset_info.get('date_min', 'N/A')} to {dataset_info.get('date_max', 'N/A')}"
    subtitle_text = (
        f"<b>Enterprise:</b> {business_name} &nbsp;|&nbsp; "
        f"<b>Dataset:</b> {dataset_info.get('dataset_name', 'Active Dataset')} &nbsp;|&nbsp; "
        f"<b>Audit Period:</b> {d_span}"
    )
    story.append(Paragraph(subtitle_text, subtitle_style))
    story.append(Spacer(1, 12))

    # Executive Financial Summary Table
    story.append(Paragraph("1. Financial Summary & Key Performance Indicators", h2_style))
    rev = kpis.get("total_revenue", 0.0)
    pcost = kpis.get("total_product_cost", 0.0)
    gross = kpis.get("gross_profit", 0.0)
    gm = kpis.get("gross_margin")
    gm_str = f"{gm:.2f}%" if gm is not None else "N/A"
    exp = kpis.get("operating_expenses")
    exp_str = f"₹{exp:,.2f}" if exp is not None else "N/A"
    net = kpis.get("net_profit")
    net_str = f"₹{net:,.2f}" if net is not None else "N/A"
    nm = kpis.get("net_margin")
    nm_str = f"{nm:.2f}%" if nm is not None else "N/A"

    kpi_data = [
        ["Total Revenue", f"₹{rev:,.2f}", "Operating Expenses", exp_str],
        ["Product Cost (COGS)", f"₹{pcost:,.2f}", "Net Profit", net_str],
        ["Gross Profit", f"₹{gross:,.2f}", "Net Profit Margin", nm_str],
        ["Gross Margin", gm_str, "Active Flagged Alerts", str(len(alerts_list))],
    ]

    kpi_table = Table(kpi_data, colWidths=[125, 125, 130, 124])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Monthly Trends Chart
    chart_buf = generate_monthly_chart_image(monthly_trends)
    if chart_buf:
        story.append(Paragraph("2. Financial Performance Trend Chart", h2_style))
        story.append(Image(chart_buf, width=504, height=215))
        story.append(Spacer(1, 14))

    # Product Performance Ranking
    story.append(Paragraph("3. Product Performance & Inventory Audit (Top Items)", h2_style))
    prod_headers = ["Product", "Qty Sold", "Revenue (₹)", "Cost (₹)", "Profit (₹)", "Margin", "Stock", "Risk Status"]
    prod_rows = [prod_headers]

    for p in product_performance[:10]:
        m_str = f"{p['gross_margin']:.1f}%" if p['gross_margin'] is not None else "N/A"
        prod_rows.append([
            p["product_name"][:22],
            f"{p['quantity_sold']:,.0f}",
            f"₹{p['sales_revenue']:,.2f}",
            f"₹{p['product_cost']:,.2f}",
            f"₹{p['gross_profit']:,.2f}",
            m_str,
            f"{p['latest_inventory']:,.0f}",
            p["risk_status"],
        ])

    prod_table = Table(prod_rows, colWidths=[110, 48, 68, 68, 64, 46, 44, 56])
    prod_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 14))

    # Operating Expense Breakdown
    if expense_dist:
        story.append(Paragraph("4. Operating Expense Breakdown", h2_style))
        exp_headers = ["Category", "Total Incurred (₹)", "Share of Operating Expenses (%)"]
        exp_table_data = [exp_headers]
        for e in expense_dist:
            exp_table_data.append([
                e["category"],
                f"₹{e['amount']:,.2f}",
                f"{e['percentage']:.1f}%"
            ])
        exp_table = Table(exp_table_data, colWidths=[200, 150, 154])
        exp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(exp_table)
        story.append(Spacer(1, 14))

    # Detected Loss Risks & Recommendations
    story.append(Paragraph("5. Detected Potential Loss Alerts & Recommendations", h2_style))
    if not alerts_list:
        story.append(Paragraph("No loss anomalies or risk patterns were triggered for the active dataset.", body_style))
    else:
        for idx, a in enumerate(alerts_list, 1):
            sev = a.get("severity", "Medium")
            sev_color = "#e11d48" if sev == "High" else "#d97706" if sev == "Medium" else "#2563eb"
            header_text = f"<b>[{a['rule_code']}] {a['subject_name']}</b> — Period: {a['period_month']} &nbsp;|&nbsp; <font color='{sev_color}'><b>{sev} Severity</b></font>"
            expl_text = f"<b>Observation:</b> {a['explanation']}"
            rec_text = f"<b>Actionable Recommendation:</b> {a['recommendation']}"

            alert_block = [
                Paragraph(header_text, body_style),
                Paragraph(expl_text, small_style),
                Paragraph(rec_text, small_style),
                Spacer(1, 4),
            ]
            story.append(KeepTogether(alert_block))

    story.append(Spacer(1, 14))

    # Applied Thresholds Audit
    story.append(Paragraph("6. Audited Detection Thresholds", h2_style))
    th_rows = [["Rule", "Rule Name", "Core Condition", "Severity Thresholds"]]
    for r_code, th in Config.ANALYSIS_THRESHOLDS.items():
        th_rows.append([
            r_code,
            th["name"],
            th["condition"],
            f"High: {th.get('high_severity_margin') or th.get('high_severity_decline') or th.get('high_severity_increase') or th.get('high_severity_multiple') or th.get('high_severity_drop')}"
        ])
    th_table = Table(th_rows, colWidths=[40, 130, 204, 130])
    th_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(th_table)
    story.append(Spacer(1, 14))

    # Limitations Note (Required by Section 0, 5, 7, 14)
    story.append(Paragraph("7. Analytical Scope & System Limitations", h2_style))
    limitations_text = (
        "<b>Notice of Analytical Scope:</b> This system operates on deterministic, rule-based retail accounting logic. "
        "Alerts indicate potential historical anomalies and flagged risk patterns requiring operational investigation; "
        "they do not constitute guaranteed future loss forecasts or statistical predictions. "
        "Operating expenses are recorded at the business level and are not allocated to individual SKU lines. "
        "Thresholds are configurable defaults and should be calibrated to specific business operating margins."
    )
    story.append(Paragraph(limitations_text, small_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
