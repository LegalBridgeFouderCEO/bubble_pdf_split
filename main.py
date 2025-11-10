from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import requests
from io import BytesIO
import pdfplumber
from openai import OpenAI
import os
import logging
from fpdf import FPDF
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class PDFRequest(BaseModel):
    file_url: str


class PDFGenerationRequest(BaseModel):
    analysis_text: str
    document_title: str = "Analyse Juridique LegalBridge"
    client_name: str = ""


def extract_text_from_pdf(url: str) -> dict:
    """
    Télécharge le PDF et extrait le texte.
    Retourne un dictionnaire avec le texte, le nombre de pages et des métadonnées.
    """
    try:
        logger.info(f"📥 Téléchargement du PDF depuis : {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        logger.info(f"📄 Content-Type reçu : {content_type}")

        file_size = len(response.content)
        logger.info(f"📊 Taille du fichier : {file_size} octets ({file_size / 1024:.2f} KB)")

        if file_size == 0:
            logger.error("❌ Le fichier téléchargé est vide")
            return {
                "text": "",
                "pages": 0,
                "error": "Le fichier PDF est vide",
                "is_scanned": False
            }

        pdf_file = BytesIO(response.content)

        text = ""
        page_count = 0
        empty_pages = 0

        with pdfplumber.open(pdf_file) as pdf:
            page_count = len(pdf.pages)
            logger.info(f"📖 Nombre de pages détectées : {page_count}")

            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    empty_pages += 1
                    logger.warning(f"⚠️ Page {i} vide ou sans texte extractible")
                text += page_text + "\n"

        text = text.strip()
        text_length = len(text)
        logger.info(f"✅ Extraction terminée : {text_length} caractères extraits")

        is_scanned = (empty_pages / page_count) > 0.5 if page_count > 0 else False

        if text_length == 0:
            logger.error("❌ Aucun texte extrait du PDF")
            return {
                "text": "",
                "pages": page_count,
                "error": "Aucun texte extractible. Le PDF est peut-être scanné ou composé uniquement d'images.",
                "is_scanned": is_scanned
            }

        return {
            "text": text,
            "pages": page_count,
            "characters": text_length,
            "empty_pages": empty_pages,
            "is_scanned": is_scanned,
            "error": None
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction du PDF : {e}", exc_info=True)
        return {
            "text": "",
            "pages": 0,
            "error": f"Erreur lors de l'extraction du PDF : {str(e)}",
            "is_scanned": False
        }


def generate_pdf_document(analysis_text: str, document_title: str, client_name: str = "") -> BytesIO:
    """
    Génère un PDF professionnel à partir du texte d'analyse avec FPDF2.
    """
    pdf = FPDF()
    pdf.add_page()

    # Titre principal
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "LegalBridge", ln=True, align="C")

    # Sous-titre
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, document_title, ln=True, align="C")

    # Client
    if client_name:
        pdf.set_font("Helvetica", "I", 12)
        pdf.cell(0, 10, f"Client : {client_name}", ln=True, align="C")

    # Date
    pdf.set_font("Helvetica", "", 12)
    date_str = datetime.now().strftime("%d/%m/%Y")
    pdf.cell(0, 10, f"Date : {date_str}", ln=True, align="C")
    pdf.ln(10)

    # Contenu
    pdf.set_font("Helvetica", "", 11)
    lines = analysis_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue

        # Détection des titres (simple)
        if line.startswith("#") or (line.isupper() and len(line) < 100):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 8, line.strip("#").strip())
            pdf.set_font("Helvetica", "", 11)
        else:
            pdf.multi_cell(0, 7, line)

    # Pied de page
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 10, "Document généré par LegalBridge - Analyse juridique automatisée", ln=True, align="C")

    # Export
    pdf_output = pdf.output(dest='S').encode('latin1')
    buffer = BytesIO()
    buffer.write(pdf_output)
    buffer.seek(0)

    return buffer


@app.get("/")
async def root():
    return {"message": "API LegalBridge en ligne 🚀", "status": "healthy"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "LegalBridge PDF Analyzer",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.post("/analyze-pdf")
async def analyze_pdf(request_data: PDFRequest):
    file_url = request_data.file_url

    logger.info(f"🚀 Nouvelle requête d'analyse PDF")
    logger.info(f"🔗 URL reçue : {file_url}")

    if not file_url:
        raise HTTPException(status_code=400, detail="Aucune URL de fichier fournie.")

    extraction_result = extract_text_from_pdf(file_url)

    text = extraction_result.get("text", "")
    error = extraction_result.get("error")

    if error:
        logger.error(f"❌ Erreur d'extraction : {error}")
        return {
            "pdf_text": "",
            "gpt_analyse": f"⚠️ Impossible d'analyser le document : {error}",
            "metadata": extraction_result
        }

    if not text:
        return {
            "pdf_text": "",
            "gpt_analyse": "⚠️ Aucun texte n'a pu être extrait de ce PDF.",
            "metadata": extraction_result
        }

    try:
        logger.info("🤖 Appel OpenAI pour l'analyse...")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un assistant juridique expert en analyse contractuelle."
                },
                {
                    "role": "user",
                    "content": f"Analyse ce contrat et identifie les points de vigilance :\n\n{text}"
                }
            ],
            max_tokens=1500,
            temperature=0.3
        )

        ai_result = response.choices[0].message.content
        logger.info("✅ Analyse OpenAI réussie")

    except Exception as e:
        logger.error(f"❌ Erreur OpenAI : {e}", exc_info=True)
        ai_result = f"⚠️ Erreur lors de l'analyse IA : {str(e)}"

    return {
        "pdf_text": text,
        "gpt_analyse": ai_result,
        "metadata": extraction_result
    }


@app.post("/generate-pdf")
async def generate_pdf(request_data: PDFGenerationRequest):
    try:
        logger.info("📄 Génération d'un PDF...")

        if not request_data.analysis_text:
            raise HTTPException(status_code=400, detail="Le texte d'analyse est vide")

        pdf_buffer = generate_pdf_document(
            analysis_text=request_data.analysis_text,
            document_title=request_data.document_title,
            client_name=request_data.client_name
        )

        filename = f"Analyse_LegalBridge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du PDF : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du PDF : {str(e)}")
