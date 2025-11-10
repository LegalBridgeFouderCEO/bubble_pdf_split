# Utiliser Python 3.11 pour éviter le bug Pydantic
FROM python:3.11-slim

# Définir le dossier de travail dans le container
WORKDIR /app

# Copier les fichiers requirements.txt
COPY requirements.txt .

# Mettre pip à jour et installer les dépendances
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier le reste du code
COPY . .

# Exposer le port utilisé par Render
EXPOSE 10000

# Commande de lancement de l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
