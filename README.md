# 🧠 CV Evaluator — Système Multi-Agents d'Évaluation de CV

[![CI/CD Pipeline](https://github.com/yacineberkani/cv_evaluator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yacineberkani/cv_evaluator/actions/workflows/ci-cd.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-1C3C3C?logo=langchain)](https://www.langchain.com/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://www.docker.com/)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Spaces-FFD21E?logo=huggingface)](https://huggingface.co/spaces/yacineberkani/cv_evaluator)
[![License](https://img.shields.io/badge/License-JEMSLABS-green)](./README.md)

---

## 📌 Description

Application d'évaluation automatisée de CV utilisant une architecture **multi-agents** propulsée par **LangChain** et plusieurs backends LLM au choix : **Google Gemini**, **OpenAI ChatGPT** et **Ollama** (cloud). Le système analyse, évalue et note chaque section d'un CV de manière **déterministe et reproductible**, puis restitue un rapport structuré avec score, tableau d'évaluation, verdict et recommandations.

**Stack technique :** Python 3.11 · Streamlit · LangChain · Google Gemini / ChatGPT / Ollama · Pydantic · PyMuPDF · Docker · GitHub Actions · Hugging Face Spaces




<table>
<tr>
<td width="100%">

## 📹 Voir la vidéo de démonstration
---
https://github.com/user-attachments/assets/45300066-c809-473d-ba67-3bd57212b555

</td>
</tr>
</table>

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                       │
│         Upload PDF → Affichage Résultats → Export JSON      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   ORCHESTRATOR                              │
│        (Gestion du pipeline, cache, parallélisme)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────┼────────────────────┐
    │                  │                    │
┌───▼──────────┐       │                    │
│  Phase 1     │       │                    │
│  Experience  │       │                    │
│  Analysis    │       │                    │
│  Agent       │       │                    │
└──────┬───────┘       │                    │
       │               │                    │
┌──────▼───────┐ ┌─────▼─────────┐          │
│  Phase 2a    │ │  Phase 2b     │          │
│  Skills &    │ │  Summary      │   (parallel)
│  Education   │ │  Validation   │          │
│  Agent       │ │  Agent        │          │
└──────┬───────┘ └──────┬────────┘          │
       └────────┬───────┘                   │
                ▼                           │
       ┌─────────────────┐                  │
       │  Phase 3        │                  │
       │  Scoring Agent  │                  │
       └──────┬──────────┘                  │
              ▼                             │
    ┌──────────────┐ ┌────────────────┐     │
    │  Phase 4a    │ │  Phase 4b      │  (parallel)
    │  Quality     │ │  Table         │     │
    │  Control     │ │  Generator     │     │
    │  Agent       │ │  Agent         │     │
    └──────────────┘ └────────────────┘     │
                                            │
    ┌───────────────────────────────────────┘
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAPPORT FINAL (JSON)                     │
│    Score /100 · Tableau · Verdict · Recommandation          │
└─────────────────────────────────────────────────────────────┘
```

### Les 6 Agents

| # | Agent | Rôle | Entrées | Sorties |
|---|-------|------|---------|---------|
| 1 | `ExperienceAnalysisAgent` | Analyse chaque expérience professionnelle | Texte expériences + CV complet | Score, missions, résultats, erreurs détectées |
| 2 | `SkillsEducationAgent` | Évalue compétences & formations | Texte compétences/formations + résultat Agent 1 | Scores, compétences démontrées vs non démontrées |
| 3 | `SummaryValidationAgent` | Valide le résumé vs preuves concrètes | Texte résumé + résultat Agent 1 | Taux de preuve, écarts identifiés, score |
| 4 | `ScoringAgent` | Calcule le score pondéré global | Scores des agents 1 à 3 | Note /10, /20, /100 + détail par critère |
| 5 | `QualityControlAgent` | Verdict final et recommandations | Résultats agents 1 à 4 | Verdict, recommandation, forces/faiblesses |
| 6 | `TableGeneratorAgent` | Génère le tableau d'évaluation visuel | Résultats agents 1 à 3 | Tableau avec emojis + justifications |

---

## 📂 Structure du Projet

```
cv_evaluator/
├── app.py                          # Application Streamlit (frontend)
├── orchestrator.py                 # Orchestration multi-agents
├── requirements.txt                # Dépendances Python (production)
├── requirements-dev.txt            # Dépendances de développement (tests, linting)
├── pyproject.toml                  # Configuration du projet (ruff, pytest, mypy)
├── Dockerfile                      # Image Docker multi-stage, utilisateur non-root
├── docker-compose.prod.yml         # Compose pour déploiement production
├── .dockerignore                   # Exclusions du build Docker
├── .env.example                    # Template variables d'environnement
├── .gitignore                      # Exclusions Git
├── README.md                       # Ce fichier
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml               # Pipeline CI/CD (qualité, tests, Docker, HF deploy)
│
├── .devcontainer/                  # Configuration Dev Container (VS Code)
│
├── assets/                         # Ressources statiques
│   └── ci-cd-success.png           # Capture d'écran du pipeline CI/CD réussi
│
├── agents/                         # Agents spécialisés
│   ├── __init__.py
│   ├── base_agent.py               # Classe de base (LangChain + LLM abstrait)
│   ├── experience_agent.py         # Agent 1 : Analyse expériences
│   ├── skills_education_agent.py   # Agent 2 : Compétences & formations
│   ├── summary_validation_agent.py # Agent 3 : Validation résumé
│   ├── scoring_agent.py            # Agent 4 : Calcul scores
│   ├── quality_control_agent.py    # Agent 5 : Contrôle qualité
│   └── table_generator_agent.py    # Agent 6 : Tableau d'évaluation
│
├── models/                         # Schémas Pydantic
│   ├── __init__.py
│   └── schemas.py                  # Tous les modèles de données validés
│
├── prompts/                        # Templates de prompts
│   ├── __init__.py
│   └── templates.py                # Prompts optimisés par provider LLM
│
├── tests/                          # Suite de tests
│   ├── __init__.py
│   └── ...                         # Tests unitaires et d'intégration
│
└── utils/                          # Utilitaires
    ├── __init__.py
    ├── pdf_parser.py               # Extraction PDF (PyMuPDF)
    ├── chunking.py                 # Découpage sémantique du CV
    └── cache.py                    # Cache des résultats intermédiaires
```

---

## 🚀 Installation & Exécution Locale

### Prérequis

- Python 3.10+
- Une clé API LLM au choix :
  - **Google Gemini** — [obtenir ici](https://makersuite.google.com/app/apikey)
  - **OpenAI ChatGPT** — [obtenir ici](https://platform.openai.com/api-keys)
  - **Ollama** (local ou cloud)

### Installation

```bash
# Cloner le projet
git clone https://github.com/yacineberkani/cv_evaluator.git
cd cv_evaluator

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate       # Linux/Mac
# ou : venv\Scripts\activate   # Windows

# Installer les dépendances de production
pip install -r requirements.txt

# (Optionnel) Installer les dépendances de développement
pip install -r requirements-dev.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env et renseigner votre clé API
```

### Exécution

```bash
streamlit run app.py
```

L'application s'ouvrira sur `http://localhost:8501`.

---

## 🐳 Exécution avec Docker

Le projet inclut un **Dockerfile multi-stage** optimisé (image slim, utilisateur non-root, port 7860 compatible Hugging Face Spaces).

### Build de l'image

```bash
docker build -t cv-evaluator .
```

### Lancement du conteneur

```bash
docker run -p 7860:7860 \
  -e GOOGLE_API_KEY=votre_clé_ici \
  cv-evaluator
```

L'application sera accessible sur `http://localhost:7860`.

### Avec Docker Compose (production)

```bash
docker compose -f docker-compose.prod.yml up
```

> **Note :** Le Dockerfile expose le port `7860` — obligatoire pour Hugging Face Spaces. Le binaire `streamlit` est explicitement copié depuis l'étape `dependencies` vers l'étape finale (`COPY --from=dependencies /usr/local/bin /usr/local/bin`), ce qui est indispensable dans un build multi-stage.

---

## ☁️ Déploiement sur Hugging Face Spaces

Le déploiement est entièrement automatisé via un pipeline **GitHub Actions CI/CD** déclenché à chaque `push` sur la branche `main`.

### Pipeline CI/CD — 4 jobs

```
push → main
       │
       ├─ [1] quality     → Linting (ruff), formatage, vérification types (mypy)
       │
       ├─ [2] tests        → Exécution des tests unitaires (pytest) avec mock LLM
       │
       ├─ [3] build        → Build Docker multi-stage + validation de l'image
       │        (dépend de : quality + tests)
       │
       └─ [4] deploy       → Push vers Hugging Face Spaces via l'API HF
                (dépend de : build)
```

### Secrets GitHub à configurer

Rendez-vous dans **Settings → Secrets and variables → Actions** de votre repository :

| Secret | Description |
|--------|-------------|
| `HF_TOKEN` | Token d'accès Hugging Face (write) |
| `HF_SPACE_NAME` | Nom du Space HF cible (ex. `yacineberkani/cv_evaluator`) |
| `GOOGLE_API_KEY` | Clé API Google Gemini (injectée dans le Space) |
| `OPENAI_API_KEY` | Clé API OpenAI (optionnel, si provider ChatGPT utilisé) |

### Fonctionnement automatique

Une fois les secrets configurés, chaque `git push` sur `main` déclenche automatiquement le pipeline. En cas de succès sur tous les jobs, le Space Hugging Face est mis à jour sans intervention manuelle.

---

## 📊 Statut du Déploiement

Le pipeline CI/CD passe intégralement — qualité, tests, build Docker et déploiement Hugging Face sont tous au vert.

![CI/CD Pipeline Success](./assets/ci-cd-success.png)

---

## ⚙️ Variables d'Environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `GOOGLE_API_KEY` | Clé API Google Gemini | *(obligatoire si provider Gemini)* |
| `OPENAI_API_KEY` | Clé API OpenAI ChatGPT | *(obligatoire si provider ChatGPT)* |
| `OLLAMA_BASE_URL` | URL du serveur Ollama | `http://localhost:11434` |
| `LLM_PROVIDER` | Provider LLM actif (`gemini`, `openai`, `ollama`) | `gemini` |
| `GEMINI_MODEL` | Modèle Gemini à utiliser | `gemini-2.5-flash-lite` |
| `GEMINI_TEMPERATURE` | Température LLM (0 = déterministe) | `0` |

---

## 📏 Formule de Scoring

```
Note /10 = (Expériences × 0.5) + (Compétences × 0.2) + (Formations × 0.1) + (Résumé × 0.2)
```

- **Note /20** = Note /10 × 2
- **Note /100** = Note /10 × 10

Le `ScoringAgent` effectue le calcul via le LLM, puis le valide **programmatiquement** via Pydantic pour garantir la cohérence du résultat.

---

## 🔧 Bonnes Pratiques Implémentées

### Intelligence Artificielle

- ✅ **Déterminisme** : température = 0, prompts stricts, sorties JSON validées par Pydantic
- ✅ **Gestion d'erreurs** : retry avec backoff exponentiel (3 tentatives max), fallback de parsing JSON robuste
- ✅ **Chunking sémantique** : découpage du CV par sections (expériences, compétences, résumé) pour respecter la fenêtre de contexte du LLM
- ✅ **Parallélisme** : les paires d'agents 2a/2b et 4a/4b s'exécutent en parallèle via `ThreadPoolExecutor`
- ✅ **Caching** : résultats intermédiaires mis en cache pour éviter les appels LLM redondants
- ✅ **Modularité** : chaque agent est une classe indépendante, extensible et testable isolément
- ✅ **Validation stricte** : chaque sortie JSON est validée par un modèle Pydantic dédié avant traitement
- ✅ **Données manquantes** : signalement systématique d'une section absente plutôt qu'invention de données

### DevOps

- ✅ **Docker multi-stage non-root** : image slim en 3 étapes (`base → dependencies → final`), l'utilisateur `user` (UID 1000) est imposé par Hugging Face Spaces
- ✅ **Pipeline CI/CD GitHub Actions** : 4 jobs ordonnés (qualité → tests → build → déploiement) avec dépendances explicites
- ✅ **Déploiement continu** : chaque push sur `main` déclenche automatiquement la mise à jour du Space HF
- ✅ **Cohérence des ports** : port `7860` utilisé de bout en bout (Dockerfile, docker-compose, CMD Streamlit) pour la compatibilité native avec Hugging Face Spaces

---

## 🧩 Défis Techniques Relevés

Ce projet a nécessité la résolution de plusieurs problèmes non triviaux lors du déploiement sur Hugging Face Spaces :

- **Port incorrect** : Streamlit démarrait par défaut sur le port `8501`, incompatible avec HF Spaces qui exige le port `7860`. Correction appliquée dans le `CMD` du Dockerfile et dans `docker-compose.prod.yml`.
- **Binaires manquants en multi-stage build** : dans un build Docker multi-stage, seuls les `site-packages` étaient copiés vers l'image finale, mais pas les exécutables (`streamlit`, etc.) présents dans `/usr/local/bin`. Ajout explicite de `COPY --from=dependencies /usr/local/bin /usr/local/bin`.
- **Emoji invalide dans le YAML CI/CD** : certains caractères Unicode (emojis) dans les `name:` des steps GitHub Actions provoquaient des erreurs de parsing YAML. Suppression ou remplacement par des équivalents textuels.
- **Dépôt Git imbriqué** : un sous-dossier contenant un `.git/` propre était ignoré par Git lors du push, entraînant un déploiement incomplet sur HF. Résolu par suppression du `.git/` interne ou utilisation d'un submodule explicite.
- **Permissions utilisateur HF** : Hugging Face impose l'UID `1000` pour l'utilisateur non-root. Configuration du `useradd -m -u 1000 user` et `COPY --chown=user:user` dans le Dockerfile.

---

## 📄 Licence

**JEMSLABS** — Tous droits réservés.