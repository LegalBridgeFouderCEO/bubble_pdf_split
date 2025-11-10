import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_text_with_openai(text: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un assistant juridique expert."},
            {"role": "user", "content": f"Analyse ce texte et identifie les points clés:\n{text}"}
        ],
        temperature=0
    )
    return response.choices[0].message.content
