from fastapi import FastAPI, File, UploadFile
from io import BytesIO
import pdfplumber
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/analyze-pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    try:
        # Lire le contenu du fichier
        content = await file.read()

        # Extraction du texte PDF
        text = ""
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"

        if not text.strip():
            return {"error": "Aucun texte extrait du PDF"}

        # Appel OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un assistant juridique."},
                {"role": "user", "content": text}
            ],
            max_tokens=1000
        )
        ai_result = response['choices'][0]['message']['content']

        return {"pdf_text": text, "openai_analysis": ai_result}

    except Exception as e:
        return {"error": f"Erreur serveur inattendue: {str(e)}"}

