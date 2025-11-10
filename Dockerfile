# Étape 1 : image de base Python 3.11
FROM python:3.11-slim

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers requirements.txt et main.py
COPY requirements.txt .
COPY main.py .

# Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port utilisé par uvicorn
EXPOSE 10000

# Commande pour lancer ton app FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]

