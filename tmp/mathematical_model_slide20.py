from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


source = Path("output/pdf/Research_proposal_presentation_constraints_combined.pdf")
target = Path("output/pdf/Research_proposal_presentation_constraints_mathematical.pdf")
reader = PdfReader(str(source))
writer = PdfWriter()
page_width = float(reader.pages[19].mediabox.width)
page_height = float(reader.pages[19].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")


def formula_image(latex, font_size):
    raw_buffer = BytesIO()
    dpi = 400
    math_to_image(f"${latex}$", raw_buffer, prop=FontProperties(size=font_size), dpi=dpi, format="png", color="#111111")
    raw_buffer.seek(0)
    with Image.open(raw_buffer) as image:
        pixels = image.convert("RGB")
        width_px, height_px = image.size
        rgba = Image.new("RGBA", (width_px, height_px))
        rgba.putdata([(0, 0, 0, 255 - min(pixel)) for pixel in pixels.getdata()])
    buffer = BytesIO()
    rgba.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer, width_px * 72 / dpi, height_px * 72 / dpi


def draw_formula(c, latex, x, y_center, max_width, font_size):
    buffer, image_width, image_height = formula_image(latex, font_size)
    scale = min(1.0, max_width / image_width)
    drawn_width = image_width * scale
    drawn_height = image_height * scale
    c.drawImage(
        ImageReader(buffer), x + (max_width - drawn_width) / 2,
        y_center - drawn_height / 2, width=drawn_width,
        height=drawn_height, mask="auto",
    )


overlay_buffer = BytesIO()
c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
c.setFillColor(colors.white)
c.rect(0, 0, page_width, page_height, stroke=0, fill=1)
c.setFillColor(blue)
c.rect(0, page_height - 30, page_width, 30, stroke=0, fill=1)
c.setFillColor(colors.white)
c.setFont("Helvetica", 18)
c.drawString(9, page_height - 22, "Complete Mathematical Model")

# Objective panel
c.setFillColor(blue)
c.roundRect(18, 177, page_width - 36, 40, 5, stroke=0, fill=1)
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 7.5)
c.drawString(27, 202, "Objective")
draw_formula(c, r"\min Z=\sum_{i=1}^{3}\sum_{j=1}^{4}w_{ij}u_{ij}", 27, 196, page_width - 54, 10.5)

c.setFillColor(ink)
c.setFont("Helvetica-Bold", 9)
c.drawString(20, 158, "Subject to")
rows = [
    ("Supply", r"\sum_{j=1}^{4}x_{ij}\leq S_i,\quad i=1,2,3"),
    ("Demand balance", r"x_{ij}+u_{ij}=D_{ij},\quad i=1,2,3,\;j=1,2,3,4"),
    ("Minimum allocation", r"x_{ij}\geq L_{ij},\quad i=1,2,3,\;j=1,2,3,4"),
    ("Distribution capacity", r"\sum_{j=1}^{4}x_{ij}\leq C_i,\quad i=1,2,3"),
    ("Non-negativity", r"x_{ij},u_{ij}\geq 0"),
]
row_top = 145
for idx, (label, latex) in enumerate(rows):
    y = row_top - idx * 22
    c.setFillColor(light if idx % 2 == 0 else colors.white)
    c.roundRect(18, y - 7, page_width - 36, 19, 3, stroke=0, fill=1)
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 7.1)
    c.drawString(25, y, label)
    draw_formula(c, latex, 145, y + 2, page_width - 158, 10.5)

c.setFillColor(muted)
c.setFont("Helvetica", 5.5)
c.drawString(12, 13, "Sources: [3], [8]")
c.setFillColor(blue)
c.rect(0, 0, page_width, 9, stroke=0, fill=1)
c.setFillColor(colors.white)
c.setFont("Helvetica", 5.8)
c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
c.drawCentredString(page_width * 0.57, 2.4, "Optimal Water Allocation")
c.drawString(page_width - 80, 2.4, "2026")
c.drawRightString(page_width - 4, 2.4, "20 / 26")
c.showPage()
c.save()

overlay_buffer.seek(0)
overlay = PdfReader(overlay_buffer).pages[0]
for index, page in enumerate(reader.pages):
    if index == 19:
        page.merge_page(overlay)
    writer.add_page(page)

with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
