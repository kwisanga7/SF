from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


source = Path("output/pdf/Research_proposal_presentation_final_updated.pdf")
target = Path("output/pdf/Research_proposal_presentation_final_combined.pdf")
reader = PdfReader(str(source))
writer = PdfWriter()
width = float(reader.pages[0].mediabox.width)
height = float(reader.pages[0].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")
body_style = ParagraphStyle("body", fontName="Helvetica", fontSize=7.2,
                            leading=9.6, textColor=ink, spaceAfter=8)


def footer(c, number):
    c.setFillColor(blue)
    c.rect(0, 0, width, 9, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5.8)
    c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
    c.drawCentredString(width * 0.57, 2.4, "Optimal Water Allocation")
    c.drawString(width - 80, 2.4, "2026")
    c.drawRightString(width - 4, 2.4, f"{number} / 22")


def setup_slide(c, title):
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


def draw_items(c, x, y, width_available, items, style=body_style):
    for item in items:
        p = Paragraph(item, style)
        _, h = p.wrap(width_available, height)
        p.drawOn(c, x, y - h)
        y -= h + style.spaceAfter


def significance_scope_slide(c, number):
    setup_slide(c, "Significance and Scope")
    gap, margin = 12, 14
    col_w = (width - 2 * margin - gap) / 2
    left, right = margin, margin + col_w + gap
    panel(c, left, "SIGNIFICANCE OF THE STUDY", col_w)
    panel(c, right, "SCOPE OF THE STUDY", col_w)

    significance = [
        "<b>Water authorities:</b> decision support for distributing limited water.",
        "<b>Households:</b> consideration of minimum essential water needs.",
        "<b>Businesses:</b> consideration of productive water uses.",
        "<b>Researchers:</b> application of optimization to water management.",
        "<b>Policy makers:</b> evidence for equitable water distribution.",
    ]
    scope = [
        "<b>Geographical:</b> Kigali City districts of Gasabo, Kicukiro and Nyarugenge.",
        "<b>Consumer categories:</b> households, industries, commercial users and public institutions.",
        "<b>Time:</b> June-September 2025, subject to availability of reliable data.",
    ]
    draw_items(c, left + 8, 178, col_w - 16, significance)
    draw_items(c, right + 8, 178, col_w - 16, scope)
    c.setFillColor(muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(12, 13, "Sources: [1], [2], [7]")
    footer(c, number)


def methodology_data_slide(c, number):
    setup_slide(c, "Research Methodology and Data Sources")
    gap, margin = 12, 14
    col_w = (width - 2 * margin - gap) / 2
    left, right = margin, margin + col_w + gap
    panel(c, left, "RESEARCH METHODOLOGY", col_w)
    panel(c, right, "DATA SOURCES", col_w)

    methods = [
        "<b>Research design:</b> quantitative.",
        "<b>Study area:</b> Kigali City, Rwanda.",
        "<b>Target population:</b> households, industries, commercial users, public institutions and water officials.",
        "<b>Sampling:</b> stratified and purposive sampling.",
        "<b>Proposed sample:</b> approximately 120 respondents.",
    ]
    sources = [
        "<b>Primary data</b>",
        "Questionnaires, interviews and observation.",
        "<b>Secondary data</b>",
        "WASAC; Rwanda Water Resources Board; National Institute of Statistics of Rwanda; City of Kigali.",
    ]
    draw_items(c, left + 8, 178, col_w - 16, methods)
    draw_items(c, right + 8, 178, col_w - 16, sources)
    c.setFillColor(muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(12, 13, "Sources: [2], [5], [6]")
    footer(c, number)


final_number = 0
for original_number, page in enumerate(reader.pages, start=1):
    if original_number in (9, 14):
        continue
    final_number += 1
    temp = BytesIO()
    c = canvas.Canvas(temp, pagesize=(width, height))
    if original_number == 8:
        significance_scope_slide(c, final_number)
    elif original_number == 13:
        methodology_data_slide(c, final_number)
    else:
        c.setFillColor(colors.white)
        c.rect(0, 0, width, 9, stroke=0, fill=1)
        footer(c, final_number)
    c.showPage()
    c.save()
    temp.seek(0)
    page.merge_page(PdfReader(temp).pages[0])
    writer.add_page(page)

if len(writer.pages) != 22:
    raise RuntimeError(f"Expected 22 slides, got {len(writer.pages)}")
with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
