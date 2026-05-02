"""Generate PDF report for a meeting with charts."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from datetime import datetime
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


def _make_action_items_chart(action_items: list) -> io.BytesIO | None:
    if not action_items:
        return None
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for item in action_items:
        p = item.get("priority", "medium").lower()
        if p in priority_counts:
            priority_counts[p] += 1

    labels = [k.capitalize() for k, v in priority_counts.items() if v > 0]
    values = [v for v in priority_counts.values() if v > 0]
    if not values:
        return None

    fig, ax = plt.subplots(figsize=(4, 3))
    bar_colors = ["#ef4444", "#f59e0b", "#22c55e"][:len(labels)]
    bars = ax.bar(labels, values, color=bar_colors, width=0.5, edgecolor="white")
    ax.set_title("Action Items by Priority", fontsize=11, fontweight="bold", pad=10)
    ax.set_ylabel("Count")
    ax.set_ylim(0, max(values) + 1)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                str(val), ha="center", va="bottom", fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_effectiveness_gauge(score: int) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(4, 2.5), subplot_kw={"aspect": "equal"})
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.2, 1.3)

    # Background arc
    theta = np.linspace(np.pi, 0, 100)
    ax.plot(np.cos(theta), np.sin(theta), color="#e5e7eb", linewidth=18, solid_capstyle="round")

    # Colored arc based on score
    fill_ratio = score / 10
    theta_fill = np.linspace(np.pi, np.pi - fill_ratio * np.pi, 100)
    if score <= 4:
        arc_color = "#ef4444"
    elif score <= 7:
        arc_color = "#f59e0b"
    else:
        arc_color = "#22c55e"
    ax.plot(np.cos(theta_fill), np.sin(theta_fill), color=arc_color, linewidth=18, solid_capstyle="round")

    ax.text(0, 0.3, f"{score}/10", ha="center", va="center", fontsize=22, fontweight="bold", color=arc_color)
    ax.text(0, 0.05, "Effectiveness", ha="center", va="center", fontsize=9, color="#6b7280")
    ax.axis("off")
    ax.set_title("Meeting Effectiveness", fontsize=11, fontweight="bold", pad=5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_sentiment_chart(sentiment: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    sentiment = sentiment.lower()
    sentiment_map = {
        "positive": (["Positive", "Neutral", "Negative"], [70, 20, 10], ["#22c55e", "#94a3b8", "#ef4444"]),
        "neutral":  (["Positive", "Neutral", "Negative"], [25, 55, 20], ["#22c55e", "#94a3b8", "#ef4444"]),
        "negative": (["Positive", "Neutral", "Negative"], [10, 20, 70], ["#22c55e", "#94a3b8", "#ef4444"]),
    }
    labels, sizes, clrs = sentiment_map.get(sentiment, sentiment_map["neutral"])
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=clrs,
                                      autopct="%1.0f%%", startangle=90,
                                      textprops={"fontsize": 8})
    for at in autotexts:
        at.set_fontweight("bold")
    ax.set_title("Meeting Sentiment", fontsize=11, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_meeting_pdf(meeting: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 textColor=colors.HexColor("#6366f1"), fontSize=22)
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                               textColor=colors.HexColor("#1e293b"), fontSize=13)
    normal = styles["Normal"]

    # Title
    story.append(Paragraph("MeetingMind AI Report", title_style))
    story.append(Spacer(1, 0.3*cm))

    ts = meeting.get("timestamp", "")
    if ts:
        try:
            ts = datetime.fromisoformat(ts).strftime("%B %d, %Y at %I:%M %p")
        except:
            pass
    story.append(Paragraph(f"<font color='grey'>Meeting #{meeting.get('id', '—')}  |  {ts}</font>", normal))
    story.append(Spacer(1, 0.6*cm))

    # Summary
    story.append(Paragraph("Summary", h2_style))
    story.append(Paragraph(meeting.get("summary", "N/A"), normal))
    story.append(Spacer(1, 0.5*cm))

    # ── CHARTS ROW ──────────────────────────────────────────────
    story.append(Paragraph("Analytics", h2_style))
    story.append(Spacer(1, 0.3*cm))

    chart_row = []

    # Effectiveness gauge
    score = meeting.get("effectiveness_score", 5)
    try:
        score = int(score)
    except:
        score = 5
    gauge_buf = _make_effectiveness_gauge(score)
    chart_row.append(Image(gauge_buf, width=6*cm, height=4*cm))

    # Sentiment pie
    sentiment = meeting.get("sentiment", "neutral")
    sent_buf = _make_sentiment_chart(sentiment)
    chart_row.append(Image(sent_buf, width=5.5*cm, height=4*cm))

    # Priority bar chart
    action_items = meeting.get("action_items", [])
    priority_buf = _make_action_items_chart(action_items)
    if priority_buf:
        chart_row.append(Image(priority_buf, width=6*cm, height=4*cm))

    if chart_row:
        chart_table = Table([chart_row], colWidths=[6.2*cm] * len(chart_row))
        chart_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(chart_table)
    story.append(Spacer(1, 0.6*cm))

    # ── ACTION ITEMS TABLE ───────────────────────────────────────
    story.append(Paragraph("Action Items", h2_style))
    if action_items:
        table_data = [["Assignee", "Task", "Deadline", "Priority"]]
        for item in action_items:
            priority = item.get("priority", "medium").upper()
            table_data.append([
                item.get("assignee", ""),
                item.get("task", ""),
                item.get("deadline") or "—",
                priority,
            ])
        table = Table(table_data, colWidths=[3.5*cm, 8*cm, 3*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f8ff"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No action items found.", normal))
    story.append(Spacer(1, 0.5*cm))

    # ── RISKS ────────────────────────────────────────────────────
    risks = meeting.get("risks", [])
    if risks:
        story.append(Paragraph("Risks & Blockers", h2_style))
        for r in risks:
            story.append(Paragraph(f"• {r}", normal))
        story.append(Spacer(1, 0.4*cm))

    # ── AGENT DECISIONS ──────────────────────────────────────────
    decisions = meeting.get("agent_decisions", [])
    if decisions:
        story.append(Paragraph("Agent Decisions", h2_style))
        for d in decisions:
            story.append(Paragraph(f"• {d}", normal))
        story.append(Spacer(1, 0.4*cm))

    # ── ACTIONS TAKEN ────────────────────────────────────────────
    actions_taken = meeting.get("actions_taken", [])
    if actions_taken:
        story.append(Paragraph("Actions Taken", h2_style))
        for action in actions_taken:
            story.append(Paragraph(f"• {action}", normal))
        story.append(Spacer(1, 0.4*cm))

    # ── TRANSCRIPT ───────────────────────────────────────────────
    story.append(Paragraph("Full Transcript", h2_style))
    transcript = meeting.get("transcript", "")
    story.append(Paragraph(
        transcript[:3000] + ("..." if len(transcript) > 3000 else ""),
        normal
    ))

    doc.build(story)
    return buffer.getvalue()
