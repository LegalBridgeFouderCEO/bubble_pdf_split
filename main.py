from fastapi import FastAPI
from pydantic import BaseModel
import requests
from io import BytesIO
import pdfplumber
from openai import OpenAI
import os
import logging
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ✅ nouvelle syntaxe OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PDFRequest(BaseModel):
    file_url: str

def extract_text_from_pdf(url: str) -> str:
    """Télécharge le PDF et extrait le texte."""
    # ✅ FIX: Gérer les URLs relatives de Bubble
    if url.startswith("//"):
        url = "https:" + url
        logger.info(f"🔧 URL relative corrigée : {url}")
    
    logger.info(f"📥 Téléchargement du PDF depuis : {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    pdf_file = BytesIO(response.content)
    logger.info(f"✅ PDF téléchargé : {len(response.content)} bytes")

    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        logger.info(f"📖 Nombre de pages détectées : {len(pdf.pages)}")
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    
    text = text.strip()
    logger.info(f"✅ Extraction terminée : {len(text)} caractères extraits")
    return text

@app.get("/")
async def root():
    return {"message": "API LegalBridge en ligne 🚀"}

@app.post("/analyze-pdf")
async def analyze_pdf(request_data: PDFRequest):
    logger.info("🚀 Nouvelle requête d'analyse PDF")
    
    file_url = request_data.file_url
    if not file_url:
        logger.error("❌ Aucune URL de fichier fournie")
        return {"error": "Aucune URL de fichier fournie."}
    
    logger.info(f"🔗 URL reçue : {file_url}")

    try:
        text = extract_text_from_pdf(file_url)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction du PDF : {e}")
        return {"error": f"Erreur lors de l'extraction du PDF : {str(e)}"}

    if not text:
        logger.warning("⚠️ Aucun texte extrait du PDF")
        return {"error": "Aucun texte extrait du PDF."}

    try:
        logger.info("🤖 Appel OpenAI pour l'analyse...")
        # ✅ nouvelle syntaxe OpenAI 1.x
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant juridique spécialisé en analyse contractuelle."},
                {"role": "user", "content": f"Analyse ce contrat et identifie les points de vigilance :\n\n{text}"}
            ],
            max_tokens=800
        )
        ai_result_raw = response.choices[0].message.content
        logger.info(f"✅ Analyse OpenAI réussie : {len(ai_result_raw)} caractères")

        # Nettoyage pour Bubble : enlever sauts de ligne et extraire les points numérotés
        ai_result_clean = ai_result_raw.replace("\n", " ").replace("  ", " ")
        points = re.findall(r"\d+\.\s(.+?)(?=\d+\.|$)", ai_result_clean)

    except Exception as e:
        logger.error(f"❌ Erreur d'appel OpenAI : {e}")
        points = [f"Erreur d'appel OpenAI : {e}"]

    return {
        "pdf_text": text[:1000],  # renvoie seulement un aperçu pour Bubble
        "openai_analysis_points": points
    }

