from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from src.routes.pdf_routes import router as pdf_router
def analyse_text(text):
    return f"Texte reçu : {text[:50]}..."  # Renvoie les 50 premiers caractères pour test

def clean_text(text):
    return text.strip()
app = FastAPI(
    title="LegalBridge PDF Analysis API",
    description=
    "API pour diviser les PDFs en chunks et les analyser avec LangChain et OpenAI GPT-5",
    version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.include_router(pdf_router, prefix="/api", tags=["PDF Analysis"])


@app.get("/")
async def root():
    return {
        "message": "LegalBridge PDF Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "analyze_pdf": "/api/analyze-pdf"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
