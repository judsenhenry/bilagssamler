import streamlit as st
import os
from io import BytesIO
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


# --- PDF Hjælpefunktioner ---

def add_watermark(input_pdf, watermark_pdf):
    watermark_reader = PdfReader(watermark_pdf)
    watermark = watermark_reader.pages[0]

    if isinstance(input_pdf, str):
        pdf_reader = PdfReader(input_pdf)
    else:
        pdf_reader = PdfReader(input_pdf)

    pdf_writer = PdfWriter()
    for page in pdf_reader.pages:
        page.merge_page(watermark)
        pdf_writer.add_page(page)

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


# --- Streamlit App ---

st.title("📘 Rønslevs Bilagssamler")

uploaded_files = st.file_uploader("Upload dine 'BilagX.pdf'-filer", accept_multiple_files=True, type="pdf")
start_page = st.number_input("Start sidetal", min_value=1, value=2)

# Find vandmærket i projektmappen
watermark_path = os.path.join(os.path.dirname(__file__), "vandmærke.pdf")

if st.button("Generer PDF"):
    if not uploaded_files:
        st.error("Upload dine bilag først.")
    elif not os.path.exists(watermark_path):
        st.error("Filen 'vandmærke.pdf' blev ikke fundet i projektmappen!")
    else:
        with st.spinner("Genererer PDF..."):
            temp_files = []
            for uf in uploaded_files:
                path = f"/tmp/{uf.name}"
                with open(path, "wb") as f:
                    f.write(uf.read())
                temp_files.append(path)

            merged = merge_pdfs_with_structure(temp_files, watermark_path, start_page)
            numbered = add_page_numbers(merged, start_page)

            st.success("✅ PDF'er blev succesfuldt genereret!")
            st.download_button(
                "⬇️ Download samlet PDF",
                numbered,
                file_name="samlet_bilag_med_indholdsfortegnelse.pdf",
                mime="application/pdf"
            )
