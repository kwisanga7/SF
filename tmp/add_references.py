from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


source = Path(r"C:\Users\Kwisanga7\Downloads\Research_proposal_presentation (1).pdf")
target = Path("output/pdf/Research_proposal_presentation_with_references.pdf")
reader = PdfReader(str(source))
width = float(reader.pages[0].mediabox.width)
height = float(reader.pages[0].mediabox.height)

slide_sources = {
    3: "Sources: [1], [2], [3]",
    4: "Sources: [3], [5], [6]",
    8: "Source: [7]",
    9: "Sources: [1], [2]",
    10: "Sources: [3], [6]",
    11: "Sources: [3], [8]",
    12: "Sources: [3]-[6]",
    14: "Sources: [2], [5], [6]",
    17: "Sources: [5], [6]",
    18: "Sources: [3], [8]",
    19: "Sources: [3], [8]",
    20: "Sources: [3], [8]",
    21: "Sources: [7], [8]",
    22: "Sources: [3], [8]",
    23: "Source: [8]",
    24: "Sources: [3], [8]",
    25: "Sources: [3], [8]",
    28: "Sources: [3], [5], [6]",
}

refs = [
    "[1] Rwanda Environment Management Authority. (2015). <i>Rwanda State of Environment and Outlook Report</i>. Kigali: REMA.",
    "[2] National Institute of Statistics of Rwanda. (2023). <i>The Fifth Rwanda Population and Housing Census, 2022: Main Indicators Report</i>. Kigali: NISR.",
    "[3] Archibald, T. W., &amp; Marshall, S. E. (2018). Review of mathematical programming applications in water resource management under uncertainty. <i>Environmental Modelling &amp; Assessment, 23</i>, 753-777. https://doi.org/10.1007/s10666-018-9628-0",
    "[4] D'Ambrosio, C., Lodi, A., Wiese, S., &amp; Bragalli, C. (2015). Mathematical programming techniques in water network optimization. <i>European Journal of Operational Research, 243</i>(3), 774-788. https://doi.org/10.1016/j.ejor.2014.12.039",
    "[5] Japan International Cooperation Agency &amp; WASAC. (2021). <i>The Project for Water Supply Master Plan for City of Kigali: Final Report</i>.",
    "[6] Rwanda Natural Resources Authority. (2015). <i>Rwanda National Water Resources Master Plan</i>. Kigali: MINIRENA/RNRA.",
    "[7] World Health Organization. (2021). <i>Domestic water quantity, service level and health</i>. Geneva: WHO.",
    "[8] Hillier, F. S., &amp; Lieberman, G. J. (2015). <i>Introduction to Operations Research</i> (10th ed.). McGraw-Hill.",
]

style = ParagraphStyle(
    "reference", fontName="Helvetica", fontSize=7.0, leading=8.6,
    textColor=colors.HexColor("#222222"), spaceAfter=7,
)

writer = PdfWriter()
for page_number, page in enumerate(reader.pages, start=1):
    overlay_buffer = BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=(width, height))
    if page_number in slide_sources:
        c.setFont("Helvetica", 5.5)
        c.setFillColor(colors.HexColor("#555555"))
        cite_y = height - 42 if page_number == 24 else 12
        c.drawString(12, cite_y, slide_sources[page_number])
    if page_number == 29:
        # Replace the visible placeholder bibliography while keeping the
        # original branded title bar and footer.
        c.setFillColor(colors.white)
        c.rect(0, 9, width, height - 34, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#222222"))
        columns = (refs[:4], refs[4:])
        col_x = (20, width / 2 + 4)
        col_width = width / 2 - 26
        for items, x in zip(columns, col_x):
            y = height - 39
            for text in items:
                para = Paragraph(text, style)
                _, para_h = para.wrap(col_width, height)
                para.drawOn(c, x, y - para_h)
                y -= para_h + style.spaceAfter
    c.showPage()
    c.save()
    overlay_buffer.seek(0)
    overlay = PdfReader(overlay_buffer).pages[0]
    page.merge_page(overlay)
    writer.add_page(page)

target.parent.mkdir(parents=True, exist_ok=True)
with target.open("wb") as out:
    writer.write(out)
print(f"Wrote {target} ({len(writer.pages)} slides)")
