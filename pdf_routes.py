from fastapi import APIRouter, Request
import requests, pdfplumber, openai, os
from io import BytesIO

router = APIRouter()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(url: str) -> str:
    response = requests.get(url)
    pdf_file = BytesIO(response.content)
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text.strip()

@router.post("/analyze-pdf")
async def analyze_pdf(request: Request):
    data = await request.json()
    file_url = data.get("file_url")
    if not file_url:
        return {"error": "No file_url provided"}
    
    text_from_pdf = extract_text_from_pdf(file_url)
    if not text_from_pdf:
        return {"error": "Unable to extract text from PDF"}

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
        return {"error": str(e)}

    return {"pdf_text": text_from_pdf, "openai_analysis": ai_result}
