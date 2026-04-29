# Étape 1 : Image de base Python
FROM python:3.11-slim AS base

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Créer un utilisateur non-root (UID 1000 imposé par HF)
RUN useradd -m -u 1000 user

# Définit le répertoire de travail
WORKDIR /app

# Étape 2 : Installation des dépendances
FROM base AS dependencies

# Copie uniquement les fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Étape 3 : Image finale
FROM base AS final

# Copie les dépendances installées depuis l'étape précédente
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copie tout le code de l'application avec les bons propriétaires
COPY --chown=user:user . .

# Bascule vers l'utilisateur non-root
USER user

# Expose le port attendu par Hugging Face Spaces
EXPOSE 7860

# Commande de démarrage
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]