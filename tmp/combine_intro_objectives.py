from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


source = Path("output/pdf/Research_proposal_presentation_final_combined.pdf")
target = Path("output/pdf/Research_proposal_presentation_final_merged.pdf")
reader = PdfReader(str(source))
writer = PdfWriter()
width = float(reader.pages[0].mediabox.width)
height = float(reader.pages[0].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")
body_style = ParagraphStyle("body", fontName="Helvetica", fontSize=7.1,
                            leading=9.3, textColor=ink, spaceAfter=7)
small_style = ParagraphStyle("small", fontName="Helvetica", fontSize=6.8,
                             leading=9.0, textColor=ink, spaceAfter=6)


def footer(c, number):
    c.setFillColor(blue)
    c.rect(0, 0, width, 9, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5.8)
    c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
    c.drawCentredString(width * 0.57, 2.4, "Optimal Water Allocation")
    c.drawString(width - 80, 2.4, "2026")
    c.drawRightString(width - 4, 2.4, f"{number} / 20")


def setup(c, title):
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setFillColor(blue)
    c.rect(0, height - 30, width, 30, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 17)
    c.drawString(9, height - 22, title)


def panel(c, x, title, w, y=26, h=178):
    c.setFillColor(light)
    c.setStrokeColor(colors.HexColor("#B9BBD8"))
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    c.setFillColor(blue)
    c.roundRect(x, y + h - 15, w, 15, 4, stroke=0, fill=1)
    c.rect(x, y + h - 15, w, 4, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.2)
    c.drawString(x + 7, y + h - 10.2, title)


def items(c, x, y, w, entries, style=body_style):
    for entry in entries:
        p = Paragraph("&bull;&nbsp; " + entry, style)
        _, h = p.wrap(w, height)
        p.drawOn(c, x, y - h)
        y -= h + style.spaceAfter


def problem_questions(c, number):
    setup(c, "Problem Statement and Research Questions")
    margin, gap = 14, 12
    col_w = (width - 2 * margin - gap) / 2
    left, right = margin, margin + col_w + gap
    panel(c, left, "PROBLEM STATEMENT", col_w)
    panel(c, right, "RESEARCH QUESTIONS", col_w)
    items(c, left + 8, 178, col_w - 16, [
        "Water is required by households, industries, commercial users and public institutions.",
        "Availability may be limited during dry seasons.",
        "Some districts and consumer groups may experience greater shortages than others.",
        "A mathematical model is needed to support efficient and equitable water allocation.",
    ], small_style)
    items(c, right + 8, 178, col_w - 16, [
        "What are the water demand and available supply conditions in Kigali?",
        "How can water resources be allocated using linear programming?",
        "How can the model minimize unmet water demand?",
        "How can the model support decisions during dry seasons?",
    ], small_style)
    c.setFillColor(muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(12, 13, "Sources: [1], [3], [5], [6]")
    footer(c, number)


def objectives_hypotheses(c, number):
    setup(c, "Research Objectives and Hypotheses")
    margin, gap = 14, 12
    col_w = (width - 2 * margin - gap) / 2
    left, right = margin, margin + col_w + gap
    panel(c, left, "OBJECTIVES", col_w)
    panel(c, right, "HYPOTHESES", col_w)

    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(left + 8, 178, "General objective")
    p = Paragraph("To develop a linear programming model for optimal allocation of water resources during dry seasons in Kigali City.", small_style)
    _, ph = p.wrap(col_w - 16, height)
    p.drawOn(c, left + 8, 172 - ph)
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(left + 8, 137, "Specific objectives")
    items(c, left + 8, 128, col_w - 16, [
        "Examine water demand and available supply.",
        "Formulate a linear programming allocation model.",
        "Determine an allocation strategy that minimizes unmet demand.",
        "Assess the model's usefulness for dry-season decisions.",
    ], small_style)

    # Hypothesis boxes keep the two statements visually distinct.
    for y, title, statement in (
        (111, "Null hypothesis (H0)", "The proposed model does not improve allocation of available water resources."),
        (57, "Alternative hypothesis (H1)", "The model reduces weighted unmet demand while respecting the specified constraints."),
    ):
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#B9BBD8"))
        c.roundRect(right + 8, y, col_w - 16, 43, 3, stroke=1, fill=1)
        c.setFillColor(blue)
        c.setFont("Helvetica-Bold", 6.8)
        c.drawString(right + 14, y + 31, title)
        p = Paragraph(statement, small_style)
        _, ph = p.wrap(col_w - 28, height)
        p.drawOn(c, right + 14, y + 24 - ph)

    footer(c, number)


final_number = 0
for original_number, page in enumerate(reader.pages, start=1):
    if original_number in (5, 7):
        continue
    final_number += 1
    temp = BytesIO()
    c = canvas.Canvas(temp, pagesize=(width, height))
    if original_number == 4:
        problem_questions(c, final_number)
    elif original_number == 6:
        objectives_hypotheses(c, final_number)
    else:
        c.setFillColor(colors.white)
        c.rect(0, 0, width, 9, stroke=0, fill=1)
        footer(c, final_number)
    c.showPage()
    c.save()
    temp.seek(0)
    page.merge_page(PdfReader(temp).pages[0])
    writer.add_page(page)

if len(writer.pages) != 20:
    raise RuntimeError(f"Expected 20 slides, got {len(writer.pages)}")
with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
