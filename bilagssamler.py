def add_watermark(input_pdf, watermark_pdf):
    # Læs vandmærket
    watermark_reader = PdfReader(watermark_pdf)
    watermark = watermark_reader.pages[0]

    # Læs input-PDF'en (uanset om det er path eller BytesIO)
    if isinstance(input_pdf, (str, bytes, os.PathLike)):
        pdf_reader = PdfReader(input_pdf)
    else:
        input_pdf.seek(0)
        pdf_reader = PdfReader(input_pdf)

    pdf_writer = PdfWriter()

    for page in pdf_reader.pages:
        # Opret en ny side som kopi af vandmærket
        new_page = watermark_reader.pages[0]
        new_page = new_page  # Copy of the watermark
        # Kopiér for at undgå at overskrive originalen
        from copy import deepcopy
        new_page = deepcopy(watermark)

        # Læg den originale side ovenpå vandmærket
        new_page.merge_page(page)
        pdf_writer.add_page(new_page)

    output_pdf = BytesIO()
    pdf_writer.write(output_pdf)
    output_pdf.seek(0)
    return output_pdf
