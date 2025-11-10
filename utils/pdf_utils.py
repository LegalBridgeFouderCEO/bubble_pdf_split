import pdfplumber
from fpdf import FPDF

def read_pdf_text(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def split_pdf_pages(file_path: str, start_page: int, end_page: int) -> tuple[str, str]:
    """Extrait les pages start_page à end_page et retourne le texte et le nouveau PDF."""
    text = ""
    pdf = pdfplumber.open(file_path)
    selected_pages = pdf.pages[start_page-1:end_page]  # 1-index
    pdf_out_file = f"split_{os.path.basename(file_path)}"

    # Créer un nouveau PDF
    pdf_writer = FPDF()
    for page in selected_pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
        pdf_writer.add_page()
        pdf_writer.set_font("Arial", size=12)
        for line in page_text.split("\n"):
            pdf_writer.multi_cell(0, 5, line)
    pdf_writer.output(pdf_out_file)
    pdf.close()
    return text, pdf_out_file
