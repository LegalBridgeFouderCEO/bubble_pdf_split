from fastapi import APIRouter

router = APIRouter()

@router.post("/analyze-pdf")
async def analyze_pdf():
    return {"result": "Analyse PDF simulée (à compléter plus tard)"}
