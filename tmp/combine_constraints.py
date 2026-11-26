from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


source = Path("output/pdf/Research_proposal_presentation_with_references.pdf")
target = Path("output/pdf/Research_proposal_presentation_constraints_combined.pdf")
reader = PdfReader(str(source))
width = float(reader.pages[0].mediabox.width)
height = float(reader.pages[0].mediabox.height)
blue = colors.HexColor("#3638B3")
ink = colors.HexColor("#222222")
light = colors.HexColor("#F6F7FB")
muted = colors.HexColor("#555555")


def draw_footer(c, slide_no, total):
    c.setFillColor(blue)
    c.rect(0, 0, width, 9, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 5.8)
    c.drawString(0, 2.4, "UWASE Gloria (University of Rwanda)")
    c.drawCentredString(width * 0.57, 2.4, "Optimal Water Allocation")
    c.drawString(width - 80, 2.4, "2026")
    c.drawRightString(width - 4, 2.4, f"{slide_no} / {total}")


def draw_card(c, x, y, w, title, description, formula):
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
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 6, y + 8, formula)


writer = PdfWriter()
final_slide = 0
for original_no, page in enumerate(reader.pages, start=1):
    # Replace original slides 19-23 with the combined constraint slide.
    if 20 <= original_no <= 23:
        continue
    final_slide += 1

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    if original_no == 19:
        # Draw a clean slide over the old page content.
        c.setFillColor(colors.white)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        c.setFillColor(blue)
        c.rect(0, height - 30, width, 30, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 18)
        c.drawString(9, height - 22, "Model Constraints")

        col_w = (width - 3 * 14) / 2
        left_x, right_x = 14, 14 + col_w + 14
        draw_card(c, left_x, 145, col_w, "Water supply", "District allocations cannot exceed available supply.", "sum(j=1..4) x_ij <= S_i,   i=1,2,3")
        draw_card(c, left_x, 88, col_w, "Demand balance", "Allocated and unmet amounts account for all demand.", "x_ij + u_ij = D_ij,   i=1..3, j=1..4")
        draw_card(c, left_x, 31, col_w, "Minimum essential allocation", "Each category receives its minimum allocation.", "x_ij >= L_ij,   i=1..3, j=1..4")
        draw_card(c, right_x, 145, col_w, "Distribution capacity", "District distribution stays within system capacity.", "sum(j=1..4) x_ij <= C_i,   i=1,2,3")
        draw_card(c, right_x, 88, col_w, "Non-negativity", "Allocations and unmet demand cannot be negative.", "x_ij, u_ij >= 0")
        c.setFillColor(muted)
        c.setFont("Helvetica", 5.5)
        c.drawString(12, 13, "Sources: [3], [7], [8]")
        draw_footer(c, final_slide, 26)
    elif original_no == 24:
        # Reformat the full formulation so every term is visible on the slide.
        c.setFillColor(colors.white)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        c.setFillColor(blue)
        c.rect(0, height - 30, width, 30, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 18)
        c.drawString(9, height - 22, "Complete Mathematical Model")

        c.setFillColor(blue)
        c.roundRect(18, 178, width - 36, 38, 5, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(27, 203, "Objective")
        c.setFont("Helvetica", 9)
        c.drawString(27, 187, "min Z = sum(i=1..3) sum(j=1..4) w_ij u_ij")

        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(20, 159, "Subject to")
        rows = [
            ("Supply", "sum(j=1..4) x_ij <= S_i,   i=1,2,3"),
            ("Demand balance", "x_ij + u_ij = D_ij,   i=1..3, j=1..4"),
            ("Minimum allocation", "x_ij >= L_ij,   i=1..3, j=1..4"),
            ("Distribution capacity", "sum(j=1..4) x_ij <= C_i,   i=1,2,3"),
            ("Non-negativity", "x_ij, u_ij >= 0"),
        ]
        row_top = 145
        for idx, (label, formula) in enumerate(rows):
            y = row_top - idx * 22
            c.setFillColor(light if idx % 2 == 0 else colors.white)
            c.roundRect(18, y - 7, width - 36, 19, 3, stroke=0, fill=1)
            c.setFillColor(blue)
            c.setFont("Helvetica-Bold", 7.1)
            c.drawString(25, y, label)
            c.setFillColor(ink)
            c.setFont("Helvetica", 7.4)
            c.drawString(150, y, formula)

        c.setFillColor(muted)
        c.setFont("Helvetica", 5.5)
        c.drawString(12, 13, "Sources: [3], [8]")
        draw_footer(c, final_slide, 26)
    else:
        # Replace the old page number footer with the correct shorter count.
        c.setFillColor(colors.white)
        c.rect(0, 0, width, 9, stroke=0, fill=1)
        draw_footer(c, final_slide, 26)

    c.showPage()
    c.save()
    buffer.seek(0)
    overlay = PdfReader(buffer).pages[0]
    page.merge_page(overlay)
    writer.add_page(page)

if len(writer.pages) != 26:
    raise RuntimeError(f"Expected 26 slides, got {len(writer.pages)}")

with target.open("wb") as stream:
    writer.write(stream)
print(f"Wrote {target} ({len(writer.pages)} slides)")
