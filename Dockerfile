# Dockerfile pour LegalBridge FastAPI sur Render

# 1️⃣ Image Python officielle
FROM python:3.11-slim

# 2️⃣ Définir le dossier de travail dans le conteneur
WORKDIR /app

# 3️⃣ Copier les fichiers requirements.txt et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4️⃣ Copier tout le code de ton projet
COPY . .

# 5️⃣ Exposer le port utilisé par Render
EXPOSE 10000

# 6️⃣ Commande pour lancer FastAPI avec uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]

