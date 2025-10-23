from fastapi import FastAPI, Request
import requests
from io import BytesIO
import pdfplumber
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(url: str) -> str:
    """Télécharge le PDF et extrait le texte."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to download PDF: {str(e)}")

    pdf_file = BytesIO(response.content)
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"PDF reading failed: {str(e)}")

    return text.strip()

@app.post("/analyze-pdf")
async def analyze_pdf(request: Request):
    try:
        data = await request.json()
        file_url = data.get("file_url")
        if not file_url:
            return {"error": "No file_url provided"}

        print("Received file_url:", file_url)

        # Extraction du texte
        try:
            text_from_pdf = extract_text_from_pdf(file_url)
        except ValueError as e:
            return {"error": str(e)}

        if not text_from_pdf:
            return {"error": "No text extracted from PDF"}

        print("Extracted text length:", len(text_from_pdf))

        # Appel OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Tu es un assistant juridique."},
                    {"role": "user", "content": text_from_pdf}
                ],
                max_tokens=1000
            )
            ai_result = response['choices'][0]['message']['content']
        except Exception as e:
            return {"error": f"OpenAI call failed: {str(e)}"}

        return {"pdf_text": text_from_pdf, "openai_analysis": ai_result}

    except Exception as e:
        return {"error": f"Unexpected server error: {str(e)}"}

