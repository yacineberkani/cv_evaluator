
"""
CV Evaluator - Multi-Agent Streamlit Application
Main entry point for the CV evaluation system.
"""

import streamlit as st
import json
import os
import sys
import logging
import warnings
from datetime import datetime
from dotenv import load_dotenv

# ── Setup ──
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Suppress urllib3/requests compatibility warnings
warnings.filterwarnings("ignore", category=ImportWarning, module="requests")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.pdf_parser import extract_text_from_uploaded_file
from orchestrator import CVEvaluationOrchestrator
from models.schemas import FinalReport

# ── Page config ──
st.set_page_config(
    page_title="CV Evaluator - JEMS Group",
    page_icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAcCAMAAABF0y+mAAAAulBMVEUAAAD9sxr+YXP/bmP6eFj/Tob/vBFHcEz/iUf+YXL/UoL/tRn/VX7+shv/ToX/pSn/uBb/vRD/sB7/XnT/ljr+mjX+vRH/////TYf/vRD/U4H/WHz/jj//XXX/oiz/qyL/gkn/mzT/fVP/aGj/Ym//tBn/cGP/ljn/d1v/TXb/4+H/hYj/cUz/V2j/qgj/4sH/0tT/qrT/xr//vqn/z5r/maX/j23/rJn/Xkr/8/D/jiP/w2X+fBr/wEkOWfK9AAAAF3RSTlMBL17fFObgAP42wLzzVoXlfPH5f9SEgb0o5TAAAAGFSURBVCiRZdLpkoIwDADgckbAa92j4IkIrhyiiPfq+7/WJi0o6/KD6eSbtJkkjIkPAKx322i3DbtrAbDmB6BqYTgZjYZD13UNtcEAurZcLMJJra6hPxSsYLX8q64FtfmB0PC/gj5u+cFqRanhE11xM3wQBtnx5WIDETrzb1S/5DwVGsexVBUY9KZCOee7c5qu18X2IBVTlRnh+Ii4PXFepHgYVTWx/kxoSZkJ58kBD4VM7TInmk2n8+sGY+WF80uBhyQWRdnMjEivGOIn+lEmj0XJBnvzIrqYQvQuT8UPERWR9IdCVDE/i3SZykwPNd9T6IZvJudEVES9MJjzwMtth0VlO6p7TZ2yWR/Ry6nYzXVcnrKMytoK7DKF0CPcYy98HIFEVIuBWaNsY5AlhNjkNva2Q3jHxLzSY5KkND2VxiJSvXsum0y5GU1Po0UCXaDsBT0byMlXa6TUOq0upqWpl6jSqKnWczl1s3lxy9fkAtWb2zGf2lJfdp6B8uWYg0HP+VSgtl/wnEmGER38dAAAAABJRU5ErkJggg==",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    /* ── Global fonts & base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Header banner ── */
    .main-header {
        text-align: center;
        padding: 2rem 1.5rem;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: white;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255,255,255,0.08);
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.5px;
    }
    .main-header .subtitle {
        font-size: 1rem;
        opacity: 0.75;
        margin: 0;
    }
    .main-header .badge-row {
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        margin-top: 0.8rem;
        flex-wrap: wrap;
    }
    .main-header .badge {
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 0.2rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 500;
        backdrop-filter: blur(4px);
    }

    /* ── Upload zone ── */
    .upload-zone {
        border: 2px dashed #4f6ef7;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, rgba(79,110,247,0.05), rgba(118,75,162,0.05));
        margin-bottom: 1rem;
    }
    .upload-zone h3 { color: #4f6ef7; margin-bottom: 0.3rem; }
    .upload-zone p  { color: #888; font-size: 0.9rem; margin: 0; }

    /* ── File info banner ── */
    .file-info-banner {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        border: 1px solid #b1dfbb;
        border-radius: 10px;
        margin: 0.75rem 0 1.25rem 0;
    }
    .file-info-banner .icon { font-size: 1.8rem; }
    .file-info-banner .name { font-weight: 600; font-size: 1rem; color: #155724; }
    .file-info-banner .size { font-size: 0.82rem; color: #2d6a4f; }

    /* ── Score cards ── */
    .score-card {
        text-align: center;
        padding: 1.5rem 1rem;
        border-radius: 14px;
        margin: 0.4rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        transition: transform 0.2s;
    }
    .score-card:hover { transform: translateY(-2px); }
    .score-excellent { background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }
    .score-good      { background: linear-gradient(135deg, #36d1dc, #5b86e5); color: white; }
    .score-average   { background: linear-gradient(135deg, #f2994a, #f2c94c); color: white; }
    .score-low       { background: linear-gradient(135deg, #eb3349, #f45c43); color: white; }

    /* ── Verdict box ── */
    .verdict-box {
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        border-left: 5px solid;
        margin: 1rem 0;
    }
    .verdict-oui   { background: #d4edda; border-color: #28a745; }
    .verdict-non   { background: #f8d7da; border-color: #dc3545; }
    .verdict-maybe { background: #fff3cd; border-color: #ffc107; }

    /* ── Agent section (sidebar) ── */
    .agent-section {
        background: rgba(79,110,247,0.06);
        padding: 0.85rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
        border-left: 3px solid #4f6ef7;
    }

    /* ── Progress bar color ── */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4f6ef7, #764ba2);
    }

    /* ── Action buttons row ── */
    .action-row {
        display: flex;
        gap: 0.75rem;
        margin: 1rem 0;
        flex-wrap: wrap;
    }

    /* ── Section divider ── */
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a2e;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #4f6ef7;
        margin: 1.5rem 0 1rem 0;
    }

    /* ── Info chip ── */
    .chip {
        display: inline-block;
        background: #eef0ff;
        color: #4f6ef7;
        border-radius: 20px;
        padding: 0.15rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 500;
        margin: 0.15rem;
    }

    /* ── Tabs style override ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f3f4f8;
        padding: 4px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 0.88rem;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12);
    }

    /* ── Barème card ── */
    .bareme-card {
        padding: 1.4rem 1.6rem;
        border-radius: 16px;
        color: white;
        box-shadow: 0 6px 24px rgba(0,0,0,0.22);
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .bareme-card .bc-icon  { font-size: 3rem; line-height: 1; flex-shrink: 0; }
    .bareme-card .bc-body  { flex: 1; }
    .bareme-card .bc-label { font-size: 1.55rem; font-weight: 800; letter-spacing: -.5px; margin: 0; line-height: 1.15; }
    .bareme-card .bc-desc  { font-size: .95rem; opacity: .85; margin: .3rem 0 0; }
    .bareme-card .bc-score { font-size: 2.6rem; font-weight: 900; line-height: 1; flex-shrink: 0; text-align:right; }
    .bareme-card .bc-score span { font-size: 1.1rem; font-weight: 500; opacity: .8; }

    /* ── Barème scale strip ── */
    .bareme-scale {
        display: flex;
        border-radius: 8px;
        overflow: hidden;
        height: 36px;
        margin: .6rem 0 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .bareme-scale-seg {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: .72rem;
        font-weight: 600;
        color: white;
        transition: opacity .2s;
        cursor: default;
    }
    .bareme-scale-seg.active {
        outline: 3px solid white;
        outline-offset: -2px;
        z-index: 1;
        border-radius: 4px;
    }
    .bareme-scale-seg.inactive { opacity: .38; }

    /* ── Reset banner ── */
    .reset-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.9rem 1.25rem;
        background: linear-gradient(135deg, #fff8e1, #fff3cd);
        border: 1px solid #ffe082;
        border-radius: 10px;
        margin-bottom: 1.2rem;
    }
    .reset-banner .label { font-size: 0.9rem; font-weight: 500; color: #795548; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def get_score_class(score_100: float) -> str:
    if score_100 >= 75: return "score-excellent"
    if score_100 >= 55: return "score-good"
    if score_100 >= 35: return "score-average"
    return "score-low"


# ── Barème d'appréciation officiel ──
BAREME = [
    {
        "range": (0, 10),
        "label": "Inexploitable",
        "short": "DC inutilisable, décrédibilisant.",
        "emoji": "🚫",
        "gradient": "linear-gradient(135deg,#3a0000,#8b0000)",
        "text": "#ffcdd2",
        "bar_color": "#c62828",
    },
    {
        "range": (11, 12),
        "label": "Très insuffisant",
        "short": "DC incomplet, brouillon, donne une mauvaise image.",
        "emoji": "❌",
        "gradient": "linear-gradient(135deg,#7f0000,#d32f2f)",
        "text": "#ffcdd2",
        "bar_color": "#e53935",
    },
    {
        "range": (13, 14),
        "label": "Insuffisant",
        "short": "DC exploitable mais faible, non vendeur.",
        "emoji": "⚠️",
        "gradient": "linear-gradient(135deg,#bf360c,#f4511e)",
        "text": "#ffe0b2",
        "bar_color": "#f4511e",
    },
    {
        "range": (15, 16),
        "label": "Correct",
        "short": "DC utilisable mais perfectible, profil crédible mais banal.",
        "emoji": "📋",
        "gradient": "linear-gradient(135deg,#e65100,#fb8c00)",
        "text": "#fff3e0",
        "bar_color": "#fb8c00",
    },
    {
        "range": (17, 17),
        "label": "Bon",
        "short": "DC solide, clair, cohérent, peut être transmis.",
        "emoji": "👍",
        "gradient": "linear-gradient(135deg,#1565c0,#1e88e5)",
        "text": "#e3f2fd",
        "bar_color": "#1e88e5",
    },
    {
        "range": (18, 19),
        "label": "Très bon",
        "short": "DC percutant, vendeur, bien rédigé.",
        "emoji": "🌟",
        "gradient": "linear-gradient(135deg,#1b5e20,#2e7d32)",
        "text": "#e8f5e9",
        "bar_color": "#43a047",
    },
    {
        "range": (20, 20),
        "label": "Excellent",
        "short": "DC exemplaire, parfaitement aligné, riche en résultats et démonstrations.",
        "emoji": "🏆",
        "gradient": "linear-gradient(135deg,#4a148c,#7b1fa2)",
        "text": "#f3e5f5",
        "bar_color": "#8e24aa",
    },
]

ALL_LEVELS = [
    (0,  10, "Inexploitable",    "🚫", "#c62828"),
    (11, 12, "Très insuffisant", "❌", "#e53935"),
    (13, 14, "Insuffisant",      "⚠️", "#f4511e"),
    (15, 16, "Correct",          "📋", "#fb8c00"),
    (17, 17, "Bon",              "👍", "#1e88e5"),
    (18, 19, "Très bon",         "🌟", "#43a047"),
    (20, 20, "Excellent",        "🏆", "#8e24aa"),
]


def get_bareme(note_sur_20: float) -> dict:
    """Return the matching barème entry for a /20 score."""
    n = round(note_sur_20)
    for entry in BAREME:
        lo, hi = entry["range"]
        if lo <= n <= hi:
            return entry
    # Fallback: clamp to extremes
    return BAREME[0] if n < 10 else BAREME[-1]


def reset_evaluation():
    """
    Clear all evaluation-related session state keys.
    Called when user wants to start a new evaluation.
    """
    keys_to_clear = [
        "report",
        "cv_text",
        "evaluated_filename",
        "evaluation_started",
        "evaluation_complete",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)


# ══════════════════════════════════════════════
# LAYOUT COMPONENTS
# ══════════════════════════════════════════════

def render_header():
    st.markdown("""
    <style>
        /* Animation de clignotement */
        @keyframes blinker {
            50% {
                opacity: 0; /* Devient invisible au milieu du cycle */
            }
        }

        /* Classe pour le logo qui clignote */
        .blinking-logo {
            animation: blinker 4.0s linear infinite; 
            height: 50px;
        }

        .header-container {
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .main-header {
            text-align: center;
        }
    </style>
    
    <div class="main-header">
        <div class="header-container">
            <img src="https://www.jems-group.com/wp-content/uploads/2021/12/Logo.svg" 
                 alt="JEMS Group Logo" 
                 class="blinking-logo">
            <img src="https://readme-typing-svg.demolab.com?font=Bungee+Spice&size=40&duration=3000&pause=800&color=FFFFFF&vCenter=true&width=350&lines=CV+Evaluator" 
                 alt="CV Evaluator">
        </div>
        <p class="subtitle">Système Multi-Agents d'Évaluation de CV propulsé par IA GEN</p>
        <div class="badge-row">
            <span class="badge">⚡ 6 agents spécialisés</span>
            <span class="badge">🧠 Analyse déterministe</span>
            <span class="badge">📋 Rapport structuré</span>
            <span class="badge">🔗 LangChainc</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 .5rem;">
            <img src="https://img.icons8.com/fluency/96/artificial-intelligence.png" width="56">
            <div style="font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:.4rem;">Configuration</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Mode Gratuit Ollama Cloud ──
        use_ollama = st.toggle(
            "🆓 Utiliser le mode gratuit (Ollama Cloud)",
            value=False,
            help="Aucune clé API requise · Modèles open-source · Totalement gratuit",
        )

        if use_ollama:
            # Ollama Cloud models available
            ollama_models = 
            model = st.selectbox(
                "🤖 Modèle Ollama Cloud",
                ["qwen3-coder-next:cloud","gpt-oss:120b-cloud","deepseek-v3.1:671b-cloud"],
                index=0,
                help="Modèles open-source accessibles via l'API Ollama Cloud",
            )
            api_key = ""  # No API key needed for Ollama Cloud (uses default embedded key)
            st.info("🔑 Clé API Ollama incluse automatiquement")
        else:
            # ── Mode Premium (Gemini / OpenAI) ──
            api_key = st.text_input(
                "🔑 Clé API Google Gemini Ou OpenAI",
                type="password",
                value=os.getenv("GOOGLE_API_KEY", ""),
                help="Obtenez votre clé sur https://makersuite.google.com/app/apikey",
            )

            model = st.selectbox(
                "🤖 Modèle Gemini & OpenAI",
                ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro","gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4-turbo", "gpt-4"],
                index=0,
                help="Flash = rapide & économique · Pro = plus précis",
            )

        st.divider()
        st.caption("v1.0.0 · CV-Evaluator © JEMS GROUP")

        return api_key, model, use_ollama


# ══════════════════════════════════════════════
# RESULT RENDERERS
# ══════════════════════════════════════════════

def _bareme_color(note_20: float) -> str:
    """Return the exact hex color for a /20 score per the barème."""
    n = round(note_20)
    if n <= 10:  return "#c62828"   # Rouge — Inexploitable
    if n <= 12:  return "#e53935"   # Rouge-orange — Très insuffisant
    if n <= 14:  return "#f4511e"   # Orange — Insuffisant
    if n <= 16:  return "#7cb342"   # Vert clair — Correct
    if n == 17:  return "#388e3c"   # Vert moyen — Bon
    if n <= 19:  return "#2e7d32"   # Vert foncé — Très bon
    return "#1b5e20"                # Vert très foncé — Excellent


def _progress_ring_svg(value: float, max_val: float, label: str, sublabel: str, color: str, size: int = 160) -> str:
    """
    Generate an SVG animated progress ring.
    value   : raw score value
    max_val : maximum possible value
    label   : big centred text (the score string)
    sublabel: small text below (e.g. '/ 20')
    color   : stroke colour hex
    """
    pct        = min(value / max_val, 1.0)
    radius     = (size - 24) / 2
    circ       = 2 * 3.14159 * radius
    dash_val   = pct * circ
    track_color = "#e8eaf0"
    cx = cy    = size / 2
    anim_id    = f"anim_{label.replace('/','').replace(' ','')}"

    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @keyframes {anim_id} {{
        from {{ stroke-dashoffset: {circ:.2f}; }}
        to   {{ stroke-dashoffset: {circ - dash_val:.2f}; }}
      }}
    </style>
    <filter id="glow_{anim_id}">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <!-- Track -->
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none"
          stroke="{track_color}" stroke-width="12"/>
  <!-- Progress arc -->
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none"
          stroke="{color}" stroke-width="12"
          stroke-linecap="round"
          stroke-dasharray="{circ:.2f}"
          stroke-dashoffset="{circ:.2f}"
          transform="rotate(-90 {cx} {cy})"
          filter="url(#glow_{anim_id})"
          style="animation:{anim_id} 1.2s ease-out forwards;">
    <animate attributeName="stroke-dashoffset"
             from="{circ:.2f}" to="{circ - dash_val:.2f}"
             dur="1.2s" fill="freeze" calcMode="spline"
             keyTimes="0;1" keySplines="0.4 0 0.2 1"/>
  </circle>
  <!-- Centre label -->
  <text x="{cx}" y="{cy - 8}" text-anchor="middle" dominant-baseline="middle"
        font-family="Inter,sans-serif" font-size="28" font-weight="800" fill="{color}">{label}</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle"
        font-family="Inter,sans-serif" font-size="13" font-weight="500" fill="#9ea3b0">{sublabel}</text>
</svg>"""


def render_scores(report: FinalReport):
    scoring    = report.scoring
    score_20   = scoring.note_finale_sur_20
    score_10   = scoring.note_finale_sur_10
    score_100  = scoring.note_finale_sur_100
    bareme     = get_bareme(score_20)
    ring_color = _bareme_color(score_20)

    # ── Section title ──
    st.markdown('<div class="section-title">📊 Scores</div>', unsafe_allow_html=True)

    # ── 3 progress rings ──
    c10, c20, c100 = st.columns(3)

    ring_css = """
    <style>
    .ring-wrapper {
        display:flex; flex-direction:column; align-items:center;
        padding:1.4rem 1rem 1rem;
        background:#fff;
        border-radius:18px;
        box-shadow:0 2px 16px rgba(0,0,0,.07);
        border:1px solid #f0f1f5;
        transition:transform .2s;
    }
    .ring-wrapper:hover { transform:translateY(-3px); box-shadow:0 6px 24px rgba(0,0,0,.11); }
    .ring-title {
        font-family:'Inter',sans-serif;
        font-size:.78rem; font-weight:600; letter-spacing:.06em;
        text-transform:uppercase; color:#9ea3b0; margin-bottom:.6rem;
    }
    .ring-badge {
        margin-top:.8rem;
        display:inline-block;
        padding:.28rem .85rem;
        border-radius:20px;
        font-size:.82rem; font-weight:700;
        color:white;
    }
    </style>
    """
    st.markdown(ring_css, unsafe_allow_html=True)

    with c10:
        svg = _progress_ring_svg(score_10, 10, f"{score_10:.1f}", "/ 10", ring_color)
        st.markdown(
            f'<div class="ring-wrapper">'
            f'<div class="ring-title">Score sur 10</div>'
            f'{svg}'
            f'<div class="ring-badge" style="background:{ring_color};">{bareme["emoji"]} {bareme["label"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c20:
        svg = _progress_ring_svg(score_20, 20, f"{score_20:.1f}", "/ 20", ring_color, size=190)
        st.markdown(
            f'<div class="ring-wrapper" style="border:2px solid {ring_color}30;">'
            f'<div class="ring-title" style="color:{ring_color};">⭐ Score sur 20</div>'
            f'{svg}'
            f'<div class="ring-badge" style="background:{ring_color};font-size:.9rem;padding:.35rem 1.1rem;">'
            f'{bareme["emoji"]} {bareme["label"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c100:
        svg = _progress_ring_svg(score_100, 100, f"{score_100:.0f}", "/ 100", ring_color)
        st.markdown(
            f'<div class="ring-wrapper">'
            f'<div class="ring-title">Score sur 100</div>'
            f'{svg}'
            f'<div class="ring-badge" style="background:{ring_color};">{bareme["emoji"]} {bareme["label"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recommandation + Verdict row ──
    col_rec, col_ver = st.columns(2)

    with col_rec:
        rec       = report.quality_control.recommandation
        rec_emoji = {"Oui": "✅", "Non": "❌", "Peut-être": "⚠️"}.get(rec, "❓")
        rec_color = {"Oui": "#155724", "Non": "#721c24", "Peut-être": "#856404"}.get(rec, "#6c757d")
        rec_bg    = {"Oui": "#d4edda", "Non": "#f8d7da", "Peut-être": "#fff3cd"}.get(rec, "#f0f2f8")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;padding:1.1rem 1.4rem;
                    background:{rec_bg};border-radius:12px;border:1px solid {rec_color}30;">
            <span style="font-size:2rem;">{rec_emoji}</span>
            <div>
                <div style="font-size:.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:.06em;color:{rec_color};opacity:.7;">Recommandation</div>
                <div style="font-size:1.2rem;font-weight:800;color:{rec_color};">{rec}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_ver:
        verdict_label = report.quality_control.verdict.replace("_", " ").title()
        verdict_emoji = {"profil vendeur": "🌟", "profil banal": "😐", "profil intermediaire": "🤔"}.get(
            report.quality_control.verdict.replace("_", " "), "❓"
        )
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;padding:1.1rem 1.4rem;
                    background:#f5f6fa;border-radius:12px;border:1px solid #e0e2ea;">
            <span style="font-size:2rem;">{verdict_emoji}</span>
            <div>
                <div style="font-size:.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:.06em;color:#888;">Verdict</div>
                <div style="font-size:1.2rem;font-weight:800;color:#1a1a2e;">{verdict_label}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detail by criterion ──
    st.markdown('<div class="section-title">📈 Détail par critère</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, detail in enumerate(scoring.details):
        with cols[i]:
            pct = detail.score_brut * 10
            bar_color = _bareme_color(detail.score_brut * 2)   # map /10 → /20 scale for colour
            st.metric(
                label=f"{detail.critere}",
                value=f"{detail.score_brut}/10",
                delta=f"Pondéré : {detail.score_pondere:.2f}  (×{detail.poids})",
            )
            st.markdown(
                f'<div style="height:6px;border-radius:4px;background:#e8eaf0;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;background:{bar_color};'
                f'border-radius:4px;transition:width 1s ease;"></div></div><br>',
                unsafe_allow_html=True,
            )

    with st.expander("🔢 Détail du calcul mathématique"):
        st.code(scoring.calcul_intermediaire)
        if scoring.validation_mathematique:
            st.success("✅ Validation mathématique OK")
        else:
            st.error("❌ Erreur de calcul détectée")
        if scoring.erreur_calcul:
            st.warning(scoring.erreur_calcul)


def render_evaluation_table(report: FinalReport):
    st.markdown('<div class="section-title">📋 Tableau d\'Évaluation Détaillé</div>', unsafe_allow_html=True)

    table = report.evaluation_table
    if not table.lignes:
        st.warning("Aucune donnée dans le tableau d'évaluation.")
        return

    headers = ["Élément", "Clarté", "Cohérence", "Qualité réd.", "Pertinence", "Respect règles", "Erreurs naïves"]
    header_row = "| " + " | ".join(headers) + " |"
    separator  = "| " + " | ".join(["---"] * len(headers)) + " |"
    rows = []
    for row in table.lignes:
        cells = [
            f"**{row.element}**",
            f"{row.clarte.emoji} {row.clarte.justification[:50]}",
            f"{row.coherence.emoji} {row.coherence.justification[:50]}",
            f"{row.qualite_redactionnelle.emoji} {row.qualite_redactionnelle.justification[:50]}",
            f"{row.pertinence.emoji} {row.pertinence.justification[:50]}",
            f"{row.respect_regles.emoji} {row.respect_regles.justification[:50]}",
            f"{row.erreurs_naives.emoji} {row.erreurs_naives.justification[:50]}",
        ]
        rows.append("| " + " | ".join(cells) + " |")

    st.markdown("\n".join([header_row, separator] + rows), unsafe_allow_html=True)

    with st.expander("🔎 Voir les justifications complètes"):
        for row in table.lignes:
            st.markdown(f"#### {row.element}")
            detail_cols = st.columns(6)
            for j, (label, cell) in enumerate([
                ("Clarté", row.clarte),
                ("Cohérence", row.coherence),
                ("Qualité réd.", row.qualite_redactionnelle),
                ("Pertinence", row.pertinence),
                ("Respect règles", row.respect_regles),
                ("Erreurs naïves", row.erreurs_naives),
            ]):
                with detail_cols[j]:
                    st.markdown(f"**{label}** {cell.emoji}")
                    st.caption(cell.justification)
            st.divider()

    st.info(f"📝 {table.resume_tableau}")


def render_experience_analysis(report: FinalReport):
    st.markdown('<div class="section-title">🔍 Analyse des Expériences</div>', unsafe_allow_html=True)
    exp = report.experience_analysis

    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Score global", f"{exp.score_global_experiences}/10")
    with c2:
        st.info(f"💬 **Synthèse :** {exp.synthese}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ✅ Points forts")
        for p in exp.points_forts:
            st.markdown(f"- 🟢 {p}")
    with col2:
        st.markdown("#### ⚠️ Points faibles")
        for p in exp.points_faibles:
            st.markdown(f"- 🔴 {p}")

    if exp.donnees_manquantes:
        st.warning("**Données manquantes :** " + ", ".join(exp.donnees_manquantes))

    st.markdown(f"#### 💼 Expériences détaillées ({len(exp.experiences)})")
    for e in exp.experiences:
        with st.expander(f"💼 {e.poste} @ {e.entreprise} — {e.score}/10"):
            cols = st.columns([1, 1, 1])
            with cols[0]: st.markdown(f"📅 **Période :** {e.periode}")
            with cols[1]: st.markdown(f"⏱️ **Durée :** {e.duree_estimee or 'non précisée'}")
            with cols[2]: st.metric("Score", f"{e.score}/10")

            st.markdown(f"**Contexte métier :** {e.contexte_metier}")
            st.markdown(f"**Cohérence technique :** {e.coherence_technique}")

            if e.missions:
                st.markdown("**Missions :**")
                for m in e.missions:
                    st.markdown(f"  - {m}")
            if e.missions_differenciantes:
                st.markdown("**🌟 Missions différenciantes :**")
                for m in e.missions_differenciantes:
                    st.markdown(f"  - ⭐ {m}")
            if e.resultats_mesurables:
                st.markdown("**📊 Résultats mesurables :**")
                for r in e.resultats_mesurables:
                    st.markdown(f"  - 📈 {r}")
            if e.erreurs_naives:
                st.error("**❌ Erreurs naïves détectées :**")
                for err in e.erreurs_naives:
                    st.markdown(f"  - ⚠️ {err}")
            st.caption(f"**Justification du score :** {e.justification_score}")


def render_skills_education(report: FinalReport):
    st.markdown('<div class="section-title">🎯 Compétences & Formations</div>', unsafe_allow_html=True)
    se = report.skills_education

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Score Compétences", f"{se.score_competences}/10")
    with col2:
        st.metric("Score Formations", f"{se.score_formations}/10")

    st.markdown("#### 🛠️ Compétences")
    demonstrated     = [c for c in se.competences if c.demontree_dans_experience]
    not_demonstrated = [c for c in se.competences if not c.demontree_dans_experience]

    if demonstrated:
        st.markdown("**✅ Compétences démontrées**")
        for c in demonstrated:
            level = f" ({c.niveau_estime})" if c.niveau_estime else ""
            assoc = f" → _{c.experience_associee}_" if c.experience_associee else ""
            st.markdown(f"- ✅ **{c.nom}** `{c.categorie}`{level}{assoc}")

    if not_demonstrated:
        st.markdown("**❌ Compétences non démontrées**")
        for c in not_demonstrated:
            st.markdown(f"- ❌ **{c.nom}** `{c.categorie}` — Déclarée mais non prouvée")

    st.markdown("#### 🎓 Formations")
    for f in se.formations:
        year = f" ({f.annee})" if f.annee else ""
        st.markdown(f"- 📚 **{f.diplome}** — {f.etablissement}{year}")
        st.caption(f"  Cohérence parcours : {f.coherence_parcours}")

    st.info(f"**Cohérence formation ↔ parcours :** {se.coherence_formation_parcours}")


def render_summary_validation(report: FinalReport):
    st.markdown('<div class="section-title">✅ Validation du Résumé / Profil</div>', unsafe_allow_html=True)
    sv = report.summary_validation

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score Résumé", f"{sv.score_resume}/10")
    with col2:
        st.metric("Affirmations prouvées", f"{sv.taux_affirmations_prouvees:.0f}%")
    with col3:
        total  = len(sv.affirmations_analysees)
        proven = sum(1 for a in sv.affirmations_analysees if a.prouvee)
        st.metric("Ratio", f"{proven}/{total}")

    col_pos = st.columns(2)
    with col_pos[0]:
        st.info(f"📌 **Positionnement déclaré :** {sv.positionnement_declare}")
    with col_pos[1]:
        st.info(f"🔎 **Positionnement réel :** {sv.positionnement_reel}")

    if sv.ecarts_alignement:
        st.warning("**Écarts d'alignement :**")
        for e in sv.ecarts_alignement:
            st.markdown(f"- ⚠️ {e}")

    st.markdown("#### 📝 Analyse des affirmations")
    for a in sv.affirmations_analysees:
        icon  = "✅" if a.prouvee else "❌"
        label = a.affirmation[:80] + "…" if len(a.affirmation) > 80 else a.affirmation
        with st.expander(f"{icon} « {label} »"):
            st.markdown(f"**Prouvée :** {'Oui ✅' if a.prouvee else 'Non ❌'}")
            if a.preuve:
                st.markdown(f"**Preuve :** {a.preuve}")
            st.markdown(f"**Commentaire :** {a.commentaire}")


def render_quality_control(report: FinalReport):
    st.markdown('<div class="section-title">🏁 Contrôle Qualité Final</div>', unsafe_allow_html=True)
    qc = report.quality_control

    verdict_class = {"Oui": "verdict-oui", "Non": "verdict-non", "Peut-être": "verdict-maybe"}.get(
        qc.recommandation, "verdict-maybe"
    )
    st.markdown(f"""
    <div class="verdict-box {verdict_class}">
        <h3 style="margin:0 0 .4rem 0;">Recommandation : {qc.recommandation}</h3>
        <p style="margin:0;">{qc.justification_recommandation}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"**Verdict :** {qc.verdict.replace('_', ' ').title()}")
    with c2: st.markdown(f"**Alignement global :** {qc.alignement_global}")
    with c3: st.metric("Score Alignement", f"{qc.score_alignement}/10")

    st.markdown(f"**Justification :** {qc.justification_verdict}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💪 Forces")
        for f in qc.forces:
            st.markdown(f"- 🟢 {f}")
    with col2:
        st.markdown("#### 📉 Faiblesses")
        for f in qc.faiblesses:
            st.markdown(f"- 🔴 {f}")

    with st.expander("📋 Éléments vérifiés"):
        quality_colors = {"excellent": "🟢", "bon": "🔵", "moyen": "🟡", "faible": "🟠", "absent": "🔴"}
        for item in qc.elements_verifies:
            icon    = "✅" if item.present else "❌"
            q_emoji = quality_colors.get(item.qualite, "⚪")
            st.markdown(f"{icon} **{item.element}** — {q_emoji} {item.qualite.title()} : {item.commentaire}")


def render_export_section(report: FinalReport):
    """Render the Export tab with JSON download and CV text download."""
    st.markdown('<div class="section-title">📥 Export & Téléchargements</div>', unsafe_allow_html=True)

    report_json = report.model_dump_json(indent=2)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")

    col_json, col_txt, col_preview = st.columns([1, 1, 1])

    # ── JSON download ──
    with col_json:
        st.markdown("**📄 Rapport complet**")
        st.download_button(
            label="⬇️ Télécharger JSON",
            data=report_json,
            file_name=f"cv_evaluation_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )

    # ── CV text download ──
    with col_txt:
        st.markdown("**📝 Texte extrait du CV**")
        cv_text = st.session_state.get("cv_text", "")
        if cv_text:
            st.download_button(
                label="⬇️ Télécharger CV (.txt)",
                data=cv_text,
                file_name=f"cv_extrait_{timestamp}.txt",
                mime="text/plain",
                use_container_width=True,
                help="Télécharger le texte brut extrait du PDF",
            )
        else:
            st.info("Texte du CV non disponible.")

    # ── Copy preview ──
    with col_preview:
        st.markdown("**🔍 Aperçu JSON**")
        if st.button("👁️ Afficher aperçu", use_container_width=True):
            st.code(report_json[:600] + "\n…", language="json")

    with st.expander("🔎 Voir le JSON complet"):
        st.json(json.loads(report_json))


# ══════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════

def main():
    render_header()
    api_key, model, use_ollama = render_sidebar()

    # ── Upload section ──
    st.markdown('<div class="section-title">📤 Importer un CV</div>', unsafe_allow_html=True)

    # If a previous result exists, show a reset banner at the top
    if "report" in st.session_state:
        fname = st.session_state.get("evaluated_filename", "CV précédent")
        reset_col1, reset_col2 = st.columns([5, 1])
        with reset_col1:
            st.markdown(
                f'<div class="reset-banner">'
                f'<span class="label">📌 Résultat actuel : <strong>{fname}</strong> — '
                f'Pour analyser un nouveau CV, réinitialisez d\'abord.</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with reset_col2:
            if st.button("🔄 Réinitialiser", type="secondary", use_container_width=True,
                         help="Efface les résultats et permet de déposer un nouveau CV"):
                reset_evaluation()
                st.rerun()

    uploaded_file = st.file_uploader(
        "Glissez votre CV au format PDF ici",
        type=["pdf"],
        help="Format accepté : PDF · Taille max : 10 Mo · 2 pages max recommandées",
        disabled="report" in st.session_state,  # lock uploader once evaluated
    )

    # Validate file size early
    if uploaded_file and uploaded_file.size > 10 * 1024 * 1024:
        st.error("❌ Le fichier dépasse 10 Mo. Veuillez compresser votre PDF.")
        return

    if uploaded_file:
        # File info card
        st.markdown(
            f'<div class="file-info-banner">'
            f'<span class="icon">📄</span>'
            f'<div><div class="name">{uploaded_file.name}</div>'
            f'<div class="size">{uploaded_file.size / 1024:.1f} Ko · PDF</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # API key validation: required for Gemini/OpenAI, not for Ollama Cloud
        if not use_ollama and not api_key:
            st.error("⚠️ Veuillez entrer votre clé API Gemini/OpenAI dans la barre latérale.")
            return

        # ── Evaluate button ──
        if "report" not in st.session_state:
            if st.button("🚀 Lancer l'évaluation", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_box   = st.empty()

                def progress_callback(message: str, percentage: float):
                    progress_bar.progress(min(percentage, 1.0))
                    status_box.info(f"⏳ {message}")

                try:
                    # Step 1 – extract text
                    with st.spinner("📄 Extraction du texte du PDF…"):
                        try:
                            cv_text = extract_text_from_uploaded_file(uploaded_file)
                        except Exception as e:
                            # Handle custom PDFExtractionError with user-friendly message
                            error_msg = str(e)
                            if "vide" in error_msg.lower():
                                st.error("❌ Le PDF est vide. Veuillez vérifier le fichier.")
                            elif "scanné" in error_msg.lower() or "image" in error_msg.lower():
                                st.error(
                                    "❌ Le PDF semble être une image scannée. "
                                    "Le texte ne peut pas être extrait. "
                                    "Utilisez un PDF avec du texte sélectionnable."
                                )
                            else:
                                st.error(f"❌ Erreur lors de la lecture du PDF : {error_msg}")
                            return

                    if len(cv_text.strip()) < 100:
                        st.error(
                            "❌ Le PDF contient très peu de texte (< 100 caractères). "
                            "Veuillez vérifier le fichier."
                        )
                        return

                    # Persist extracted text for download later
                    st.session_state["cv_text"] = cv_text

                    with st.expander("📄 Texte extrait du CV (aperçu)", expanded=False):
                        st.text(cv_text[:3000] + ("…" if len(cv_text) > 3000 else ""))

                    # Step 2 – run evaluation
                    # Force ollama provider when using Ollama Cloud mode
                    if use_ollama:
                        # Use API key from environment variable (required for Ollama Cloud)
                        ollama_api_key = os.getenv("OLLAMA_API_KEY")
                        if not ollama_api_key:
                            st.error(
                                "⚠️ Clé API Ollama manquante. "
                                "Ajoutez OLLAMA_API_KEY dans votre fichier .env ou en variable d'environnement."
                            )
                            return
                        orchestrator = CVEvaluationOrchestrator(
                            api_key=ollama_api_key,
                            model_name=model,
                            cache_dir=None,
                            progress_callback=progress_callback,
                        )
                    else:
                        orchestrator = CVEvaluationOrchestrator(
                            api_key=api_key,
                            model_name=model,
                            cache_dir=None,
                            progress_callback=progress_callback,
                        )

                    report = orchestrator.evaluate(cv_text)

                    # Persist results
                    st.session_state["report"]             = report
                    st.session_state["evaluated_filename"] = uploaded_file.name

                    progress_bar.progress(1.0)
                    status_box.success("✅ Évaluation terminée avec succès !")

                except Exception as e:
                    error_msg = str(e)
                    # User-friendly error messages
                    if "API" in error_msg or "api" in error_msg.lower():
                        st.error("❌ Erreur de connexion à l'API. Vérifiez votre clé API et votre connexion internet.")
                    elif "timeout" in error_msg.lower():
                        st.error("⏱️ La requête a expiré. Le modèle est peut-être surchargé. Réessayez dans quelques instants.")
                    elif "JSON" in error_msg or "parsing" in error_msg.lower():
                        st.error("🔧 Erreur d'analyse de la réponse IA. Le modèle a renvoyé un format invalide. Réessayez.")
                    else:
                        st.error(f"❌ Erreur lors de l'évaluation : {error_msg}")
                    logger.error(f"[App] Evaluation error: {error_msg}", exc_info=True)
                    return

    # ── Results display ──
    if "report" in st.session_state:
        report = st.session_state["report"]

        # ══════════════════════════════════════════════
        # NEW EVALUATION SECTION - Prominent CTA
        # ══════════════════════════════════════════════
        st.markdown("""
        <style>
            .new-eval-section {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 1.5rem 2rem;
                background: linear-gradient(135deg, rgba(79,110,247,0.08), rgba(118,75,162,0.08));
                border: 2px solid #4f6ef7;
                border-radius: 16px;
                margin: 1.5rem 0;
                box-shadow: 0 4px 20px rgba(79,110,247,0.15);
            }
            .new-eval-text h3 {
                color: #1a1a2e;
                margin: 0 0 0.3rem 0;
                font-size: 1.3rem;
            }
            .new-eval-text p {
                color: #666;
                margin: 0;
                font-size: 0.95rem;
            }
            .new-eval-btn {
                background: linear-gradient(135deg, #4f6ef7, #764ba2);
                color: white;
                border: none;
                padding: 0.85rem 2rem;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(79,110,247,0.3);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .new-eval-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(79,110,247,0.4);
            }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="new-eval-section">
            <div class="new-eval-text">
                <h3>✨ Évaluation terminée !</h3>
                <p>Souhaitez-vous analyser un nouveau CV ?</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Full-width button for new evaluation
        if st.button(
            "🔄 Nouvelle évaluation",
            type="primary",
            use_container_width=True,
            help="Réinitialiser tous les résultats et commencer une nouvelle évaluation",
            key="new_evaluation_btn"
        ):
            reset_evaluation()
            st.rerun()

        st.divider()

        # Sidebar metadata
        with st.sidebar:
            st.divider()
            st.markdown("### 📊 Métadonnées")
            meta = report.metadata
            st.caption(f"📅 {meta.get('date_evaluation', 'N/A')}")

            # Display provider badge
            model_name = meta.get('modele_llm', 'N/A')
            provider_badge = ""
            if model_name.endswith("-cloud") or "ollama" in model_name.lower():
                provider_badge = "🆓 Ollama Cloud"
            elif model_name.startswith("gemini"):
                provider_badge = "💎 Google Gemini"
            else:
                provider_badge = "🔵 OpenAI"

            st.caption(f"🤖 {model_name}")
            st.markdown(f"<span class='chip'>{provider_badge}</span>", unsafe_allow_html=True)
            st.caption(f"⏱️ {meta.get('duree_evaluation_secondes', 'N/A')} s")
            st.caption(f"📂 {', '.join(meta.get('sections_detectees', []))}")

            # Also add a reset button in sidebar for convenience
            st.divider()
            if st.button(
                "🗑️ Effacer les résultats",
                type="secondary",
                use_container_width=True,
                help="Supprimer les résultats actuels",
                key="sidebar_reset_btn"
            ):
                reset_evaluation()
                st.rerun()

        tabs = st.tabs([
            "📊 Scores",
            "📋 Tableau",
            "🔍 Expériences",
            "🎯 Compétences",
            "✅ Résumé",
            "🏁 Qualité",
            "📥 Export",
        ])

        with tabs[0]: render_scores(report)
        with tabs[1]: render_evaluation_table(report)
        with tabs[2]: render_experience_analysis(report)
        with tabs[3]: render_skills_education(report)
        with tabs[4]: render_summary_validation(report)
        with tabs[5]: render_quality_control(report)
        with tabs[6]: render_export_section(report)


if __name__ == "__main__":
    main()

