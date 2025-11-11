from fastapi import FastAPI
from pydantic import BaseModel
import requests
from io import BytesIO
import pdfplumber
from openai import OpenAI
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ✅ Nouvelle syntaxe OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PDFRequest(BaseModel):
    file_url: str

def extract_text_from_pdf(url: str) -> str:
    """Télécharge le PDF et extrait le texte."""
    
    # ✅ Corriger les URLs Bubble
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

    # ✅ Appel à OpenAI
    try:
        logger.info("🤖 Appel OpenAI pour l'analyse...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un expert en droit du travail. "
                        "Analyse le contrat et produis un rapport structuré PRO, clair et lisible, avec paragraphes séparés, titres et puces. "
                        "Mets en évidence les points de vigilance et les risques, avec une évaluation du risque (faible / moyen / élevé). "
                        "Structure ton analyse ainsi : "
                        "\n\n1. Contexte général\n"
                        "2. Points de vigilance (liste à puces + niveau de risque)\n"
                        "3. Risques juridiques potentiels (par paragraphes)\n"
                        "4. Recommandations pratiques\n"
                        "\n"
                        "Utilise des paragraphes, pas de \\n inutiles. "
                        "Ajoute des sauts de ligne doubles entre les sections."
                    )
                },
                {
                    "role": "user",
                    "content": f"Voici le texte du contrat à analyser : {text}"
                }
            ],
            max_tokens=1200
        )
        
        ai_result = response.choices[0].message.content

        # ✅ Nettoyer les doublons de retours à la ligne
        # Conserver les paragraphes propres
        ai_result = ai_result.replace("\r", "")
        # Supprimer les triples, quadruples newlines
        while "\n\n\n" in ai_result:
            ai_result = ai_result.replace("\n\n\n", "\n\n")

        ai_result = ai_result.strip()

        logger.info(f"✅ Analyse OpenAI réussie : {len(ai_result)} caractères")
    except Exception as e:
        logger.error(f"❌ Erreur d'appel OpenAI : {e}")
        ai_result = f"Erreur d'appel OpenAI : {e}"

    return {
        "pdf_text": text[:1500],
        "openai_analysis": ai_result
    }


