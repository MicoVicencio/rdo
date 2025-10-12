from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io

# --- Create watermark PDF ---
packet = io.BytesIO()
can = canvas.Canvas(packet, pagesize=letter)

page_width, page_height = letter

# --- Add text watermark ---
text = "CCC RESEARCH PROPERTY"
font_size = 30
can.setFont("Helvetica-Bold", font_size)
can.setFillColorRGB(0.6, 0.6, 0.6)  # light gray
text_width = can.stringWidth(text, "Helvetica-Bold", font_size)
x_text = (page_width - text_width) / 2
y_text = page_height / 2
can.saveState()
can.translate(x_text, y_text)
can.rotate(45)  # diagonal
can.setFillAlpha(0.3)  # text transparency
can.drawString(0, 0, text)
can.restoreState()

# --- Add logo image ---
logo_path = "image.png"
logo_width = 100
logo_height = 100
x_logo = (page_width - logo_width) / 2
y_logo = (page_height - logo_height) / 2
can.saveState()
can.setFillAlpha(0.2)  # image transparency
can.drawImage(ImageReader(logo_path), x_logo, y_logo, width=logo_width, height=logo_height, mask='auto')
can.restoreState()

can.save()
packet.seek(0)

# --- Read watermark PDF ---
watermark_pdf = PdfReader(packet)
watermark_page = watermark_pdf.pages[0]

# --- Read original PDF ---
original_pdf = PdfReader("CHAPTER 1-6_SDG RESEARCH-FlNAL-MANUSCRIPT-Google-Docs.pdf")
output_pdf = PdfWriter()

for page in original_pdf.pages:
    page.merge_page(watermark_page)
    output_pdf.add_page(page)

with open("document_with_watermark.pdf", "wb") as f:
    output_pdf.write(f)

print("Watermark with logo added successfully!")
