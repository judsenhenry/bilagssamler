import streamlit as st
import os
from io import BytesIO
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from copy import deepcopy
import re

# -----------------------
# PDF Hjælpefunktioner
# -----------------------

def add_watermark(input_pdf, watermark_pdf):
    """Placér vandmærket bagved teksten."""
    watermark_reader = PdfReader(watermark_pdf)
    watermark = watermark_reader.pages[0]

    if isinstance(input_pdf, (str, bytes, os.PathLike)):
        pdf_reader = PdfReader(input_pdf)
    else:
        input_pdf.seek(0)
        pdf_reader = PdfReader(input_pdf)

    pdf_writer = PdfWriter()
    for page in pdf_reader.pages:
        new_page = deepcopy(watermark)
        # Original side ovenpå vandmærket
        new_page.merge_page(page)
        pdf_writer.add_page(new_page)

    output_pdf = BytesIO()
    pdf_writer.write(output_pdf)
    output_pdf.seek(0)
    return output_pdf

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

    num_x = 100
    title_x = 125
    side_label_x = 400
    page_start_x = 450
    max_title_width = side_label_x - title_x - 10

    font_name = 'Times-Roman'
    font_size = 12

    for i, (title, (start, end)) in enumerate(zip(titles, page_ranges), 1):
        prefix = f"{i}."
        words = title.split()
        lines = []
        current_line = ""
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
        can.setFont(font_name, font_size)
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

def merge_pdfs_with_structure(pdf_files, watermark_pdf, start_page):
    merger = PdfMerger()
    titles = [os.path.splitext(f.name)[0] for f in pdf_files]

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

    toc_pdf = add_watermark(create_table_of_contents(titles, page_ranges), watermark_pdf)
    merger.append(toc_pdf)

    for title, pdf in zip(titles, pdf_files):
        front_pdf = add_watermark(create_simple_pdf(title), watermark_pdf)
        merger.append(front_pdf)
        merger.append(pdf)

    output = BytesIO()
    merger.write(output)
    output.seek(0)
    return output

def add_page_numbers(input_pdf, start_page, bottom_margin=30):
    pdf_reader = PdfReader(input_pdf)
    num_pages = len(pdf_reader.pages)

    packet = BytesIO()
    can = canvas.Canvas(packet)
    font_name = 'Times-Bold'
    font_size = 12

    for i in range(num_pages):
        page = pdf_reader.pages[i]
        llx, lly, urx, ury = map(float, [page.mediabox.lower_left[0], page.mediabox.lower_left[1],
                                         page.mediabox.upper_right[0], page.mediabox.upper_right[1]])
        width = urx - llx
        height = ury - lly
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
    numbering_pdf = PdfReader(packet)
    pdf_writer = PdfWriter()
    for page, num_page in zip(pdf_reader.pages, numbering_pdf.pages):
        page.merge_page(num_page)
        pdf_writer.add_page(page)

    output = BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    return output

# -----------------------
# Sorteringsfunktion
# -----------------------

def get_sorted_pdf_files(uploaded_files):
    def sort_key(file):
        name = os.path.splitext(file.name)[0]
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

    return sorted(uploaded_files, key=sort_key)

# -----------------------
# Streamlit App
# -----------------------

st.title("📘 Rønslevs Bilagssamler")

st.markdown("""
### 📄 Upload dine PDF-bilag
Upload dine **bilagsfiler** herunder.

Appen genkender og sorterer automatisk filerne ud fra deres nummer og underdel, så dine bilag står i korrekt rækkefølge i den samlede PDF.

Det er vigtigt, at filnavnene **starter med 'Bilag'** (eller 'bilag'), efterfulgt af tal, og eventuelt bogstaver og punktum.

#### ✅ Eksempler på gyldige filnavne:
- `Bilag 1 - Statisk system.pdf`
- `Bilag 2 - Lastplan.pdf`
- `Bilag 3.1 - Etagedæk.pdf`
- `Bilag 3.2 - Fundamenter.pdf`
- `Bilag 4a - Vindlast.pdf`
- `Bilag 4a.1 - Vindlast, niveau 1.pdf`
- `Bilag 4a.2 - Vindlast, niveau 2.pdf`
- `Bilag 4a.a - Ekstra dokument.pdf`
- `Bilag 4b - Andre bilag.pdf`
- `Bilag 10 - Slutrapport.pdf`

#### ⚠️ Undgå disse:
- `bilag1.pdf` *(mangler mellemrum mellem 'Bilag' og tal)*  
- `Appendix 1.pdf` *(mangler "Bilag")*  
- `BilagA.pdf` *(ingen tal før bogstav, kan give forkert sortering)*  

Appen sorterer filerne **numerisk og alfabetisk**: 1, 1a, 1a.1, 1a.2, 1b, 2, 3.1 osv.
""")

uploaded_files = st.file_uploader("Vælg bilag", type=["pdf"], accept_multiple_files=True)
start_page = st.number_input("Start sidetal", min_value=1, value=2)

# Vandmærke PDF placeres i samme mappe som scriptet
watermark_path = os.path.join(os.path.dirname(__file__), "vandmærke.pdf")

if uploaded_files:
    if not os.path.isfile(watermark_path):
        st.warning("Vandmærke-fil 'vandmærke.pdf' mangler i scriptmappen.")
    else:
        if st.button("📄 Generer samlet PDF"):
            sorted_files = get_sorted_pdf_files(uploaded_files)
            merged_pdf = merge_pdfs_with_structure(sorted
