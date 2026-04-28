# Dockerfile
# Image finale pour l'application

# ============================================
# Étape 1 : Image de base Python
# ============================================
FROM python:3.11-slim AS base

# Définit le répertoire de travail
WORKDIR /app

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================
# Étape 2 : Installation des dépendances
# ============================================
FROM base AS dependencies

# Copie uniquement les fichiers de dépendances
# (permet le cache Docker si les dépendances ne changent pas)
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Étape 3 : Image finale
# ============================================
FROM base AS final

# Copie les dépendances installées depuis l'étape précédente
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copie tout le code de l'application
COPY . .

# Expose le port de Streamlit
EXPOSE 8501

# Commande de démarrage
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]