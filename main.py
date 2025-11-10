from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse
from utils.pdf_utils import read_pdf_text, split_pdf_pages
from utils.openai_utils import analyze_text_with_openai
import os

app = FastAPI(title="LegalBridge PDF Analysis API")

@app.get("/")
def root():
    return {"status": "ok", "message": "API is running"}

@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    start_page: int = Query(None, description="Page de début pour extraire le PDF (1-index)"),
    end_page: int = Query(None, description="Page de fin pour extraire le PDF (1-index)")
):
    try:
        # Sauvegarde temporaire du fichier uploadé
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb") as f:
            f.write(await file.read())

        # Extraction texte
        if start_page and end_page:
            # Extraction de pages spécifiques
            text, split_file = split_pdf_pages(file_location, start_page, end_page)
        else:
            text = read_pdf_text(file_location)
            split_file = None

        # Analyse via OpenAI
        analysis_result = analyze_text_with_openai(text)

        # Supprimer fichier temporaire initial
        os.remove(file_location)

        response = {"status": "success", "analysis": analysis_result}

        # Si split PDF existe, on le renvoie comme fichier
        if split_file:
            return FileResponse(path=split_file, filename=f"split_{file.filename}", media_type="application/pdf")

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

