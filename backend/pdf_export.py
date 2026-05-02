"""Generate PDF report for a meeting."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime
import io

def generate_meeting_pdf(meeting: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("title", parent=styles["Title"], textColor=colors.HexColor("#6366f1"), fontSize=22)
    story.append(Paragraph("🤖 MeetingMind AI Report", title_style))
    story.append(Spacer(1, 0.3*cm))

    # Metadata
    ts = meeting.get("timestamp", "")
    if ts:
        try:
            ts = datetime.fromisoformat(ts).strftime("%B %d, %Y at %I:%M %p")
        except:
            pass
    story.append(Paragraph(f"<font color='grey'>Meeting #{meeting.get('id')} &nbsp;|&nbsp; {ts}</font>", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Summary
    story.append(Paragraph("📝 Summary", styles["Heading2"]))
    story.append(Paragraph(meeting.get("summary", "N/A"), styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Action Items Table
    story.append(Paragraph("✅ Action Items", styles["Heading2"]))
    action_items = meeting.get("action_items", [])
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
        story.append(Paragraph("No action items found.", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Actions Taken
    story.append(Paragraph("⚡ Actions Taken", styles["Heading2"]))
    for action in meeting.get("actions_taken", []):
        story.append(Paragraph(f"• {action}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Transcript
    story.append(Paragraph("🎤 Full Transcript", styles["Heading2"]))
    transcript = meeting.get("transcript", "")
    story.append(Paragraph(transcript[:3000] + ("..." if len(transcript) > 3000 else ""), styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
