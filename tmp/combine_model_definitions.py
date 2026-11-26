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


source = Path("output/pdf/Research_proposal_presentation_final.pdf")
target = Path("output/pdf/Research_proposal_presentation_final_updated.pdf")
reader = PdfReader(str(source))
writer = PdfWriter()
width = float(reader.pages[0].mediabox.width)
height = float(reader.pages[0].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")


def draw_math(c, latex, x, y_center, max_width, font_size):
    raw = BytesIO()
    dpi = 400
    math_to_image(f"${latex}$", raw, prop=FontProperties(size=font_size), dpi=dpi, format="png", color="#111111")
    raw.seek(0)
    with Image.open(raw) as im:
        rgb = im.convert("RGB")
        px_w, px_h = im.size
        rgba = Image.new("RGBA", (px_w, px_h))
        rgba.putdata([(0, 0, 0, 255 - min(pixel)) for pixel in rgb.getdata()])
    image = BytesIO()
    rgba.save(image, format="PNG")
    image.seek(0)
    image_w, image_h = px_w * 72 / dpi, px_h * 72 / dpi
    scale = min(1.0, max_width / image_w)
    draw_w, draw_h = image_w * scale, image_h * scale
    c.drawImage(ImageReader(image), x + (max_width - draw_w) / 2,
                y_center - draw_h / 2, width=draw_w, height=draw_h, mask="auto")


def draw_footer(c, number, total):
    c.setFillColor(blue)
    c.rect(0, 0, width, 9, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5.8)
    c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
    c.drawCentredString(width * 0.57, 2.4, "Optimal Water Allocation")
    c.drawString(width - 80, 2.4, "2026")
    c.drawRightString(width - 4, 2.4, f"{number} / {total}")


def draw_panel(c, x, title, col_width):
    y, panel_height = 25, 180
    c.setFillColor(light)
    c.setStrokeColor(colors.HexColor("#B9BBD8"))
    c.roundRect(x, y, col_width, panel_height, 4, stroke=1, fill=1)
    c.setFillColor(blue)
    c.roundRect(x, y + panel_height - 15, col_width, 15, 4, stroke=0, fill=1)
    c.rect(x, y + panel_height - 15, col_width, 4, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.1)
    c.drawString(x + 6, y + panel_height - 10.2, title)


def combined_slide(c, number):
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setFillColor(blue)
    c.rect(0, height - 30, width, 30, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 17)
    c.drawString(9, height - 22, "Sets, Decision Variables and Parameters")

    gap, left = 9, 12
    col_width = (width - 2 * left - 2 * gap) / 3
    x1, x2, x3 = left, left + col_width + gap, left + 2 * (col_width + gap)
    draw_panel(c, x1, "SETS AND INDICES", col_width)
    draw_panel(c, x2, "DECISION VARIABLES", col_width)
    draw_panel(c, x3, "MODEL PARAMETERS", col_width)

    # Sets and indices
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x1 + 7, 181, "District index")
    draw_math(c, r"i\in\{1,2,3\}", x1 + 60, 183, col_width - 68, 8)
    c.setFont("Helvetica", 6.2)
    for y, item in zip((164, 153, 142), ("1  Gasabo", "2  Kicukiro", "3  Nyarugenge")):
        c.drawString(x1 + 9, y, item)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x1 + 7, 122, "Consumer category")
    draw_math(c, r"j\in\{1,2,3,4\}", x1 + 73, 124, col_width - 81, 8)
    c.setFont("Helvetica", 6.2)
    for y, item in zip((105, 94, 83, 72), (
        "1  Households", "2  Industries", "3  Commercial users", "4  Public institutions"
    )):
        c.drawString(x1 + 9, y, item)

    # Decision variables
    c.setFillColor(ink)
    draw_math(c, r"x_{ij}", x2 + 7, 171, 38, 12)
    c.setFont("Helvetica", 6.2)
    c.drawString(x2 + 48, 174, "Water allocated to")
    c.drawString(x2 + 48, 164, "category j in district i")
    draw_math(c, r"u_{ij}", x2 + 7, 116, 38, 12)
    c.drawString(x2 + 48, 119, "Unmet demand for")
    c.drawString(x2 + 48, 109, "category j in district i")
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x2 + 7, 75, "Measurement unit")
    draw_math(c, r"\mathrm{m^3/day}", x2 + 7, 54, col_width - 14, 10)

    # Parameters
    parameter_rows = [
        (r"D_{ij}", "Water demand"),
        (r"S_i", "Available water supply"),
        (r"C_i", "Distribution capacity"),
        (r"L_{ij}", "Minimum essential allocation"),
        (r"w_{ij}", "Weight on unmet demand"),
    ]
    for y, (symbol, description) in zip((174, 145, 116, 87, 58), parameter_rows):
        draw_math(c, symbol, x3 + 6, y, 36, 10)
        c.setFillColor(ink)
        c.setFont("Helvetica", 6.1)
        c.drawString(x3 + 43, y - 2, description)

    c.setFillColor(muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(12, 13, "Sources: [5], [6]")
    draw_footer(c, number, 24)


final_number = 0
for original_number, page in enumerate(reader.pages, start=1):
    if original_number in (16, 17):
        continue
    final_number += 1
    temp = BytesIO()
    c = canvas.Canvas(temp, pagesize=(width, height))
    if original_number == 15:
        combined_slide(c, final_number)
    else:
        c.setFillColor(colors.white)
        c.rect(0, 0, width, 9, stroke=0, fill=1)
        draw_footer(c, final_number, 24)
    c.showPage()
    c.save()
    temp.seek(0)
    page.merge_page(PdfReader(temp).pages[0])
    writer.add_page(page)

if len(writer.pages) != 24:
    raise RuntimeError(f"Expected 24 slides, got {len(writer.pages)}")
with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
