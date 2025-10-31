from fastapi import FastAPI
from pydantic import BaseModel
import requests
from io import BytesIO
import pdfplumber
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Définition du schéma d’entrée
class PDFRequest(BaseModel):
    file_url: str

def extract_text_from_pdf(url: str) -> str:
    """Télécharge le PDF et extrait le texte."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    pdf_file = BytesIO(response.content)

    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text.strip()

@app.get("/")
async def root():
    return {"message": "API LegalBridge en ligne 🚀"}

# ✅ Le endpoint déclare maintenant qu’il attend un JSON conforme à PDFRequest
@app.post("/analyze-pdf")
async def analyze_pdf(request_data: PDFRequest):
    file_url = request_data.file_url
    if not file_url:
        return {"error": "Aucune URL de fichier fournie."}

    text = extract_text_from_pdf(file_url)
    if not text:
        return {"error": "Aucun texte extrait du PDF."}

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant juridique spécialisé en analyse contractuelle."},
                {"role": "user", "content": f"Analyse ce contrat :\n\n{text}"}
            ],
            max_tokens=800
        )
        ai_result = response["choices"][0]["message"]["content"]
    except Exception as e:
        ai_result = f"Erreur d'appel OpenAI : {e}"

    return {"pdf_text": text[:1000], "openai_analysis": ai_result}
