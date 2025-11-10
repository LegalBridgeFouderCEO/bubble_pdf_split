from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import requests
from io import BytesIO
import pdfplumber
from openai import OpenAI
import os
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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
        
        # Téléchargement avec timeout augmenté
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Vérification du Content-Type
        content_type = response.headers.get('Content-Type', '')
        logger.info(f"📄 Content-Type reçu : {content_type}")
        
        # Vérification de la taille
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
        
        # Détection de PDF scanné (plus de 50% de pages vides)
        is_scanned = (empty_pages / page_count) > 0.5 if page_count > 0 else False
        
        if is_scanned:
            logger.warning(f"⚠️ PDF probablement scanné : {empty_pages}/{page_count} pages vides")
        
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
        
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout lors du téléchargement du PDF")
        return {
            "text": "",
            "pages": 0,
            "error": "Timeout lors du téléchargement du fichier (>30s)",
            "is_scanned": False
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur de téléchargement : {e}")
        return {
            "text": "",
            "pages": 0,
            "error": f"Erreur de téléchargement : {str(e)}",
            "is_scanned": False
        }
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction : {e}", exc_info=True)
        return {
            "text": "",
            "pages": 0,
            "error": f"Erreur lors de l'extraction du PDF : {str(e)}",
            "is_scanned": False
        }

def generate_pdf_document(analysis_text: str, document_title: str, client_name: str = "") -> BytesIO:
    """
    Génère un PDF professionnel avec l'analyse juridique.
    """
    buffer = BytesIO()
    
    # Création du document PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Style pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#1a4d8f',
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Style pour le sous-titre
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor='#666666',
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Style pour le contenu
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['BodyText'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        fontName='Helvetica'
    )
    
    # Style pour les sections
    section_style = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#1a4d8f',
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    # Construction du document
    story = []
    
    # En-tête
    story.append(Paragraph("LegalBridge", title_style))
    story.append(Paragraph(document_title, subtitle_style))
    
    if client_name:
        story.append(Paragraph(f"Client : {client_name}", subtitle_style))
    
    # Date
    date_str = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(f"Date : {date_str}", subtitle_style))
    story.append(Spacer(1, 1*cm))
    
    # Ligne de séparation
    story.append(Paragraph("<para align='center'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</para>", content_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Contenu de l'analyse
    # Diviser le texte en paragraphes
    paragraphs = analysis_text.split('\n')
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            story.append(Spacer(1, 0.3*cm))
            continue
        
        # Détection des titres (commencent par #, **, ou sont en majuscules)
        if para.startswith('#'):
            # Markdown heading
            para = para.lstrip('#').strip()
            story.append(Paragraph(para, section_style))
        elif para.startswith('**') and para.endswith('**'):
            # Markdown bold
            para = para.strip('*').strip()
            story.append(Paragraph(f"<b>{para}</b>", section_style))
        elif para.isupper() and len(para) < 100:
            # Titre en majuscules
            story.append(Paragraph(para, section_style))
        else:
            # Paragraphe normal
            # Remplacer les markdown bold
            para = para.replace('**', '<b>').replace('**', '</b>')
            story.append(Paragraph(para, content_style))
    
    # Pied de page
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("<para align='center'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</para>", content_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("<para align='center'><i>Document généré par LegalBridge - Analyse juridique automatisée</i></para>", subtitle_style))
    
    # Génération du PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer

@app.get("/")
async def root():
    return {"message": "API LegalBridge en ligne 🚀", "status": "healthy"}

@app.get("/health")
async def health():
    """Endpoint de santé pour vérifier que l'API fonctionne."""
    return {
        "status": "healthy",
        "service": "LegalBridge PDF Analyzer",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.post("/analyze-pdf")
async def analyze_pdf(request_data: PDFRequest):
    """
    Analyse un PDF : extraction de texte + analyse OpenAI.
    
    Retourne :
    - pdf_text : le texte complet extrait
    - gpt_analyse : l'analyse OpenAI (compatible avec Bubble)
    - metadata : informations sur le PDF
    """
    file_url = request_data.file_url
    
    logger.info(f"🚀 Nouvelle requête d'analyse PDF")
    logger.info(f"🔗 URL reçue : {file_url}")
    
    if not file_url:
        logger.error("❌ Aucune URL fournie")
        raise HTTPException(status_code=400, detail="Aucune URL de fichier fournie.")
    
    # Extraction du texte
    extraction_result = extract_text_from_pdf(file_url)
    
    text = extraction_result.get("text", "")
    error = extraction_result.get("error")
    
    # Si erreur d'extraction, retourner immédiatement
    if error:
        logger.error(f"❌ Erreur d'extraction : {error}")
        return {
            "pdf_text": "",
            "gpt_analyse": f"⚠️ Impossible d'analyser le document : {error}",
            "metadata": {
                "pages": extraction_result.get("pages", 0),
                "is_scanned": extraction_result.get("is_scanned", False),
                "error": error
            }
        }
    
    if not text:
        logger.error("❌ Texte extrait vide")
        return {
            "pdf_text": "",
            "gpt_analyse": "⚠️ Aucun texte n'a pu être extrait de ce PDF. Il s'agit peut-être d'un document scanné ou composé uniquement d'images.",
            "metadata": {
                "pages": extraction_result.get("pages", 0),
                "is_scanned": extraction_result.get("is_scanned", False),
                "error": "Texte vide"
            }
        }
    
    logger.info(f"✅ Texte extrait : {len(text)} caractères")
    
    # Appel OpenAI
    try:
        logger.info("🤖 Appel OpenAI pour l'analyse...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un assistant juridique spécialisé en analyse contractuelle. Tu dois identifier les points de vigilance, les clauses importantes et les risques potentiels."
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
        logger.info(f"✅ Analyse OpenAI réussie : {len(ai_result)} caractères")
        
    except Exception as e:
        logger.error(f"❌ Erreur OpenAI : {e}", exc_info=True)
        ai_result = f"⚠️ Erreur lors de l'analyse IA : {str(e)}"
    
    # Retour de la réponse complète
    return {
        "pdf_text": text,  # Texte complet (pas tronqué)
        "gpt_analyse": ai_result,  # Nom cohérent avec Bubble
        "metadata": {
            "pages": extraction_result.get("pages", 0),
            "characters": extraction_result.get("characters", 0),
            "empty_pages": extraction_result.get("empty_pages", 0),
            "is_scanned": extraction_result.get("is_scanned", False)
        }
    }

@app.post("/generate-pdf")
async def generate_pdf(request_data: PDFGenerationRequest):
    """
    Génère un PDF professionnel à partir du texte d'analyse.
    
    Paramètres :
    - analysis_text : Le texte de l'analyse à inclure dans le PDF
    - document_title : Le titre du document (optionnel)
    - client_name : Le nom du client (optionnel)
    
    Retourne :
    - Un fichier PDF téléchargeable
    """
    try:
        logger.info("📄 Génération d'un PDF...")
        logger.info(f"📝 Longueur du texte : {len(request_data.analysis_text)} caractères")
        
        if not request_data.analysis_text:
            raise HTTPException(status_code=400, detail="Le texte d'analyse est vide")
        
        # Génération du PDF
        pdf_buffer = generate_pdf_document(
            analysis_text=request_data.analysis_text,
            document_title=request_data.document_title,
            client_name=request_data.client_name
        )
        
        logger.info("✅ PDF généré avec succès")
        
        # Nom du fichier
        filename = f"Analyse_LegalBridge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Retour du PDF
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du PDF : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du PDF : {str(e)}")

