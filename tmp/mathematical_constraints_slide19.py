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


source = Path("output/pdf/Research_proposal_presentation_constraints_mathematical.pdf")
target = Path("output/pdf/Research_proposal_presentation_final.pdf")
reader = PdfReader(str(source))
writer = PdfWriter()
width = float(reader.pages[18].mediabox.width)
height = float(reader.pages[18].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")


def math_image(latex, font_size):
    raw = BytesIO()
    dpi = 400
    math_to_image(f"${latex}$", raw, prop=FontProperties(size=font_size), dpi=dpi, format="png", color="#111111")
    raw.seek(0)
    with Image.open(raw) as im:
        rgb = im.convert("RGB")
        px_w, px_h = im.size
        rgba = Image.new("RGBA", (px_w, px_h))
        rgba.putdata([(0, 0, 0, 255 - min(pixel)) for pixel in rgb.getdata()])
    output = BytesIO()
    rgba.save(output, format="PNG")
    output.seek(0)
    return output, px_w * 72 / dpi, px_h * 72 / dpi


def draw_math(c, latex, x, y_center, max_width, font_size):
    image, image_w, image_h = math_image(latex, font_size)
    scale = min(1.0, max_width / image_w)
    draw_w, draw_h = image_w * scale, image_h * scale
    c.drawImage(ImageReader(image), x + (max_width - draw_w) / 2,
                y_center - draw_h / 2, width=draw_w, height=draw_h, mask="auto")


def card(c, x, y, w, title, description, expression):
    h = 49
    c.setFillColor(light)
    c.setStrokeColor(colors.HexColor("#B9BBD8"))
    c.roundRect(x, y, w, h, 4, stroke=1, fill=1)
    c.setFillColor(blue)
    c.roundRect(x, y + h - 13, w, 13, 4, stroke=0, fill=1)
    c.rect(x, y + h - 13, w, 4, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.1)
    c.drawString(x + 6, y + h - 9.2, title)
    c.setFillColor(ink)
    c.setFont("Helvetica", 6.1)
    c.drawString(x + 6, y + h - 23, description)
    draw_math(c, expression, x + 6, y + 13, w - 12, 8.5)


buffer = BytesIO()
c = canvas.Canvas(buffer, pagesize=(width, height))
c.setFillColor(colors.white)
c.rect(0, 0, width, height, stroke=0, fill=1)
c.setFillColor(blue)
c.rect(0, height - 30, width, 30, stroke=0, fill=1)
c.setFillColor(colors.white)
c.setFont("Helvetica", 18)
c.drawString(9, height - 22, "Model Constraints")

col_w = (width - 3 * 14) / 2
left, right = 14, 14 + col_w + 14
card(c, left, 145, col_w, "Water supply", "District allocations cannot exceed available supply.",
     r"\sum_{j=1}^{4}x_{ij}\leq S_i,\quad i=1,2,3")
card(c, left, 88, col_w, "Demand balance", "Allocated and unmet amounts account for all demand.",
     r"x_{ij}+u_{ij}=D_{ij},\quad i=1,2,3,\;j=1,2,3,4")
card(c, left, 31, col_w, "Minimum essential allocation", "Each category receives its minimum allocation.",
     r"x_{ij}\geq L_{ij},\quad i=1,2,3,\;j=1,2,3,4")
card(c, right, 145, col_w, "Distribution capacity", "District distribution stays within system capacity.",
     r"\sum_{j=1}^{4}x_{ij}\leq C_i,\quad i=1,2,3")
card(c, right, 88, col_w, "Non-negativity", "Allocations and unmet demand cannot be negative.",
     r"x_{ij},u_{ij}\geq 0")

c.setFillColor(muted)
c.setFont("Helvetica", 5.5)
c.drawString(12, 13, "Sources: [3], [7], [8]")
c.setFillColor(blue)
c.rect(0, 0, width, 9, stroke=0, fill=1)
c.setFillColor(colors.white)
c.setFont("Helvetica", 5.8)
c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
c.drawCentredString(width * 0.57, 2.4, "Optimal Water Allocation")
c.drawString(width - 80, 2.4, "2026")
c.drawRightString(width - 4, 2.4, "19 / 26")
c.showPage()
c.save()

buffer.seek(0)
overlay = PdfReader(buffer).pages[0]
for index, page in enumerate(reader.pages):
    if index == 18:
        page.merge_page(overlay)
    writer.add_page(page)

with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
