# 🧠 CV Evaluator — Système Multi-Agents d'Évaluation de CV

## 📌 Description

Application d'évaluation automatisée de CV utilisant une architecture **multi-agents** propulsée par **LangChain + Google Gemini**. Le système analyse, évalue et note chaque section d'un CV de manière déterministe et reproductible.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                        │
│         Upload PDF → Affichage Résultats → Export JSON       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   ORCHESTRATOR                               │
│        (Gestion du pipeline, cache, parallélisme)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────┼────────────────────┐
    │                  │                    │
    ▼                  │                    │
┌─────────────┐       │                    │
│  Phase 1    │       │                    │
│ Experience  │       │                    │
│ Analysis    │       │                    │
│ Agent       │       │                    │
└──────┬──────┘       │                    │
       │              │                    │
       ▼              │                    │
┌──────────────┐ ┌────▼──────────┐         │
│  Phase 2a    │ │  Phase 2b     │         │
│  Skills &    │ │  Summary      │  (parallel)
│  Education   │ │  Validation   │         │
│  Agent       │ │  Agent        │         │
└──────┬───────┘ └──────┬────────┘         │
       │                │                  │
       └────────┬───────┘                  │
                ▼                          │
       ┌─────────────┐                    │
       │  Phase 3    │                    │
       │  Scoring    │                    │
       │  Agent      │                    │
       └──────┬──────┘                    │
              │                           │
              ▼                           │
    ┌──────────────┐ ┌────────────────┐   │
    │  Phase 4a    │ │  Phase 4b      │   │
    │  Quality     │ │  Table         │(parallel)
    │  Control     │ │  Generator     │   │
    │  Agent       │ │  Agent         │   │
    └──────────────┘ └────────────────┘   │
                                          │
    ┌─────────────────────────────────────┘
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAPPORT FINAL (JSON)                       │
│    Score /100 • Tableau • Verdict • Recommandation           │
└─────────────────────────────────────────────────────────────┘
```

### Les 6 Agents

| # | Agent | Rôle | Entrées | Sorties |
|---|-------|------|---------|---------|
| 1 | `ExperienceAnalysisAgent` | Analyse chaque expérience | Texte expériences + CV complet | Score, missions, résultats, erreurs |
| 2 | `SkillsEducationAgent` | Évalue compétences & formations | Texte compétences/formations + résultat Agent 1 | Scores, compétences démontrées/non |
| 3 | `SummaryValidationAgent` | Valide le résumé vs preuves | Texte résumé + résultat Agent 1 | Taux de preuve, écarts, score |
| 4 | `ScoringAgent` | Calcule le score pondéré | Scores des agents 1-3 | Note /10, /20, /100 + détail |
| 5 | `QualityControlAgent` | Verdict final | Résultats agents 1-4 | Verdict, recommandation, forces/faiblesses |
| 6 | `TableGeneratorAgent` | Tableau d'évaluation | Résultats agents 1-3 | Tableau avec emojis + justifications |

---

## 📂 Structure du Projet

```
cv_evaluator/
├── app.py                          # Application Streamlit (frontend)
├── orchestrator.py                 # Orchestration multi-agents
├── requirements.txt                # Dépendances Python
├── .env.example                    # Template variables d'environnement
├── README.md                       # Ce fichier
│
├── agents/                         # Agents spécialisés
│   ├── __init__.py
│   ├── base_agent.py               # Classe de base (LangChain + Gemini)
│   ├── experience_agent.py         # Agent 1 : Analyse expériences
│   ├── skills_education_agent.py   # Agent 2 : Compétences & formations
│   ├── summary_validation_agent.py # Agent 3 : Validation résumé
│   ├── scoring_agent.py            # Agent 4 : Calcul scores
│   ├── quality_control_agent.py    # Agent 5 : Contrôle qualité
│   └── table_generator_agent.py    # Agent 6 : Tableau d'évaluation
│
├── models/                         # Schémas Pydantic
│   ├── __init__.py
│   └── schemas.py                  # Tous les modèles de données
│
├── prompts/                        # Templates de prompts
│   ├── __init__.py
│   └── templates.py                # Prompts optimisés pour Gemini
│
└── utils/                          # Utilitaires
    ├── __init__.py
    ├── pdf_parser.py               # Extraction PDF (PyMuPDF)
    ├── chunking.py                 # Découpage sémantique du CV
    └── cache.py                    # Cache des résultats intermédiaires
```

---

## 🚀 Installation & Exécution

### Prérequis
- Python 3.10+
- Clé API Google Gemini ([obtenir ici](https://makersuite.google.com/app/apikey))

### Installation

```bash
# Cloner le projet
git clone <https://github.com/yacineberkani/cv_evaluator>
cd cv_evaluator

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API
cp .env.example .env
# Éditer .env et ajouter votre GOOGLE_API_KEY
```

### Exécution

```bash
streamlit run app.py
```

L'application s'ouvrira sur `http://localhost:8501`.

---

## ⚙️ Variables d'Environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `GOOGLE_API_KEY` | Clé API Google Gemini | (obligatoire) |
| `GEMINI_MODEL` | Modèle Gemini à utiliser | `gemini-1.5-flash` |
| `GEMINI_TEMPERATURE` | Température (0 = déterministe) | `0` |

---

## 📏 Formule de Scoring

```
Note /10 = (Expériences × 0.5) + (Compétences × 0.2) + (Formations × 0.1) + (Résumé × 0.2)
```

- Note /20 = Note /10 × 2
- Note /100 = Note /10 × 10

Le `ScoringAgent` effectue le calcul via LLM puis le valide programmatiquement.

---

## 🔧 Bonnes Pratiques Implémentées

- ✅ **Déterminisme** : température = 0, prompts stricts, sorties JSON validées par Pydantic
- ✅ **Gestion d'erreurs** : retry avec backoff exponentiel (3 tentatives), fallback de parsing JSON
- ✅ **Chunking sémantique** : découpage du CV par sections pour respecter la fenêtre de contexte
- ✅ **Parallélisme** : agents 2a/2b et 4a/4b s'exécutent en parallèle via ThreadPoolExecutor
- ✅ **Caching** : résultats intermédiaires stockés pour éviter les appels redondants
- ✅ **Modularité** : chaque agent est une classe indépendante extensible
- ✅ **Validation stricte** : chaque sortie JSON est validée par un modèle Pydantic dédié
- ✅ **Données manquantes** : signalement systématique au lieu d'invention

---

## 📄 Licence

MIT
