import streamlit as st
import re
import os
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from copy import deepcopy

# ------------------------------------------------------------
# 📘 Vandmærke — genereres automatisk (bagved teksten)
# ------------------------------------------------------------
def create_watermark():
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFillColorRGB(0.8, 0.8, 0.8, alpha=0.2)
    can.setFont("Times-Bold", 100)
    can.saveState()
    can.translate(300, 400)
    can.rotate(45)
    can.drawCentredString(0, 0, "RØNSLEV")
    can.restoreState()
    can.save()
    packet.seek(0)
    return PdfReader(packet)


# ------------------------------------------------------------
# 🔧 Hjælpefunktioner
# ------------------------------------------------------------
def add_watermark(input_pdf, watermark_reader):
    """
    Lægger vandmærket BAGVED indholdet på hver side.
    """
    if isinstance(input_pdf, (str, bytes, os.PathLike)):
        pdf_reader = PdfReader(input_pdf)
    else:
        input_pdf.seek(0)
        pdf_reader = PdfReader(input_pdf)

    watermark = watermark_reader.pages[0]
    pdf_writer = PdfWriter()

    for page in pdf_reader.pages:
        base = deepcopy(watermark)
        base.merge_page(page)  # Vandmærket bagved
        pdf_writer.add_page(base)

    output = BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    return output


def create_simple_pdf(content, font='Times-Roman', font_size=18, title_x=100, title_y=800):
    width, height = A4
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(font, font_size)

    side_label_x = 400
    max_width = side_label_x - title_x - 10
    line_height = font_size * 1.2

    words = content.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip() if current else w
        if pdfmetrics.stringWidth(test, font, font_size) <= max_width or current == "":
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        y = title_y - i * line_height
        can.drawString(title_x, y, line)

    can.showPage()
    can.save()
    packet.seek(0)
    return packet


def create_table_of_contents(titles, page_ranges):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont('Times-Bold', 18)
    can.drawString(100, 800, "Indholdsfortegnelse")
    can.setFont('Times-Roman', 12)

    top_margin = 760
    bottom_margin = 60
    line_height = 18
    y_pos = top_margin
    num_x, title_x, side_label_x, page_start_x = 100, 125, 400, 450
    max_title_width = side_label_x - title_x - 10
    font_name, font_size = 'Times-Roman', 12

    for i, (title, (start, end)) in enumerate(zip(titles, page_ranges), 1):
        prefix = f"{i}."
        words = title.split()
        lines, current_line = [], ""
        for w in words:
            test_line = (current_line + " " + w).strip() if current_line else w
            width = pdfmetrics.stringWidth(test_line, font_name, font_size)
            if width <= max_title_width or current_line == "":
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = w
        if current_line:
            lines.append(current_line)

        needed_height = line_height * len(lines)
        if y_pos - needed_height < bottom_margin:
            can.showPage()
            can.setFont(font_name, font_size)
            y_pos = top_margin

        first_line_y = y_pos
        can.setFillColor(colors.black)
        can.drawString(num_x, first_line_y, prefix)
        for li, line in enumerate(lines):
            can.drawString(title_x, y_pos - li * line_height, line)

        can.setFillColor(colors.black)
        can.drawString(side_label_x, first_line_y, "Side")

        can.setFont('Times-Bold', font_size)
        can.setFillColor(colors.blue)
        can.drawString(page_start_x, first_line_y, str(start))
        if end != start:
            start_width = pdfmetrics.stringWidth(str(start), 'Times-Bold', font_size)
            can.drawString(page_start_x + start_width + 2, first_line_y, f"-{end}")

        y_pos = first_line_y - needed_height - (line_height * 0.2)

    can.save()
    packet.seek(0)
    return packet


def merge_pdfs_with_structure(pdf_files, watermark_reader, start_page):
    merger = PdfMerger()
    titles = [os.path.splitext(os.path.basename(f))[0] for f in pdf_files]
    page_ranges = []
    current_page = start_page

    dummy_toc = create_table_of_contents(titles, [(0, 0)] * len(pdf_files))
    dummy_reader = PdfReader(dummy_toc)
    toc_pages = len(dummy_reader.pages)
    current_page += toc_pages

    for pdf in pdf_files:
        front_page = 1
        num_pages = len(PdfReader(pdf).pages)
        page_ranges.append((current_page, current_page + front_page + num_pages - 1))
        current_page += front_page + num_pages

    toc_pdf = add_watermark(create_table_of_contents(titles, page_ranges), watermark_reader)
    merger.append(toc_pdf)

    for title, pdf in zip(titles, pdf_files):
        front_pdf = add_watermark(create_simple_pdf(title), watermark_reader)
        merger.append(front_pdf)
        merger.append(pdf)

    output = BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output


def add_page_numbers(input_pdf, start_page, bottom_margin=30):
    reader = PdfReader(input_pdf)
    num_pages = len(reader.pages)
    packet = BytesIO()
    can = canvas.Canvas(packet)
    font_name, font_size = 'Times-Bold', 12

    for i in range(num_pages):
        page = reader.pages[i]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        can.setPageSize((width, height))
        page_num = start_page + i
        text = str(page_num)
        text_width = pdfmetrics.stringWidth(text, font_name, font_size)
        x = (width - text_width) / 2.0
        y = bottom_margin
        can.setFont(font_name, font_size)
        can.setFillColor(colors.blue)
        can.drawString(x, y, text)
        can.showPage()

    can.save()
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    writer = PdfWriter()

    for base_page, overlay_page in zip(reader.pages, overlay_reader.pages):
        base_page.merge_page(overlay_page)
        writer.add_page(base_page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output


# ------------------------------------------------------------
# 🧮 Sorteringsfunktion
# ------------------------------------------------------------
def sort_bilag_filenames(files):
    def sort_key(name):
        name = os.path.splitext(os.path.basename(name))[0]
        m = re.search(r'[Bb]ilag\s*([0-9]+[a-zA-Z]*(?:\.[0-9a-zA-Z]+)*)', name)
        if not m:
            return (9999,)
        parts = m.group(1).split('.')
        key = []
        for p in parts:
            num = re.match(r'(\d+)([a-zA-Z]*)', p)
            if num:
                n, s = num.groups()
                key.append(int(n))
                if s:
                    key.append(ord(s.lower()))
            else:
                key.append(ord(p.lower()) if p else 0)
        return tuple(key)

    return sorted(files, key=sort_key)


# ------------------------------------------------------------
# 🌐 Streamlit GUI
# ------------------------------------------------------------
st.set_page_config(page_title="Rønslevs Bilagssamler", layout="centered")

st.title("📘 Rønslevs Bilagssamler")
st.markdown("""
Upload dine **bilags-PDF'er**, og appen samler dem automatisk til én samlet PDF med:

- Forside for hvert bilag  
- Automatisk indholdsfortegnelse  
- Vandmærke bagved tekst  
- Sidetal i bunden  

Appen sorterer filerne numerisk og alfabetisk — fx `1`, `1a`, `1a.1`, `1b`, `2`, `3.1`, osv.
""")

st.markdown("""
#### ✅ Gyldige filnavne:
- `Bilag 1 - Statisk system.pdf`
- `Bilag 2 - Lastplan.pdf`
- `Bilag 3.1 - Etagedæk.pdf`
- `Bilag 4a - Vindlast.pdf`
- `Bilag 4a.1 - Vindlast, niveau 1.pdf`
- `Bilag 4a.a - Ekstra dokument.pdf`
- `Bilag 4b - Fundamenter.pdf`

#### ⚠️ Undgå disse:
- `bilag1.pdf` *(mangler mellemrum)*
- `Appendix 1.pdf` *(mangler 'Bilag')*
- `BilagA.pdf` *(ingen tal før bogstav)*
""")

uploaded_files = st.file_uploader("📂 Vælg dine bilag", type=["pdf"], accept_multiple_files=True)
start_page = st.number_input("Startsidetal:", min_value=1, value=2)

if st.button("🔄 Generer samlet PDF") and uploaded_files:
    with st.spinner("Genererer PDF..."):
        temp_files = []
        for f in uploaded_files:
            temp_path = f.name
            with open(temp_path, "wb") as temp_out:
                temp_out.write(f.getbuffer())
            temp_files.append(temp_path)

        sorted_files = sort_bilag_filenames(temp_files)
        watermark_reader = create_watermark()

        merged = merge_pdfs_with_structure(sorted_files, watermark_reader, start_page)
        numbered = add_page_numbers(merged, start_page)

        st.success("PDF'en er genereret!")
        st.download_button(
            label="📥 Download samlet PDF",
            data=numbered,
            file_name="samlet_bilag_med_indholdsfortegnelse.pdf",
            mime="application/pdf"
        )

        for f in temp_files:
            os.remove(f)
