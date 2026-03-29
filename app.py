"""
CV Evaluator - Multi-Agent Streamlit Application
Main entry point for the CV evaluation system.
"""

import streamlit as st
import json
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# ── Setup ──
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
        "short": "DC utilisable mais perfectible.",
        "emoji": "📋",
        "gradient": "linear-gradient(135deg,#e65100,#fb8c00)",
        "text": "#fff3e0",
        "bar_color": "#01ff1a",
    },
    {
        "range": (17, 17),
        "label": "Bon",
        "short": "DC solide, clair, cohérent, peut être transmis.",
        "emoji": "👍",
        "gradient": "linear-gradient(135deg,#1565c0,#1e88e5)",
        "text": "#e3f2fd",
        "bar_color": "#3cff00",
    },
    {
        "range": (18, 19),
        "label": "Très bon",
        "short": "DC percutant, vendeur, bien rédigé.",
        "emoji": "🌟",
        "gradient": "linear-gradient(135deg,#1b5e20,#2e7d32)",
        "text": "#e8f5e9",
        "bar_color": "#00ff0d",
    },
    {
        "range": (20, 20),
        "label": "Excellent",
        "short": "DC exemplaire, parfaitement aligné, riche en résultats et démonstrations.",
        "emoji": "🏆",
        "gradient": "linear-gradient(135deg,#4a148c,#7b1fa2)",
        "text": "#f3e5f5",
        "bar_color": "#48aa24",
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
    """Clear all evaluation-related session state keys."""
    for key in ["report", "cv_text", "evaluated_filename"]:
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
        <p class="subtitle">Système Multi-Agents d'Évaluation de CV propulsé par Gemini AI</p>
        <div class="badge-row">
            <span class="badge">⚡ 6 agents spécialisés</span>
            <span class="badge">🧠 Analyse déterministe</span>
            <span class="badge">📋 Rapport structuré</span>
            <span class="badge">🔗 LangChain + Pydantic</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=72)
        st.title("⚙️ Configuration")

        api_key = st.text_input(
            "🔑 Clé API Google Gemini",
            type="password",
            value=os.getenv("GOOGLE_API_KEY", ""),
            help="Obtenez votre clé sur https://makersuite.google.com/app/apikey",
        )

        model = st.selectbox(
            "🤖 Modèle Gemini",
            ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
            index=0,
            help="Flash = rapide & économique · Pro = plus précis",
        )

        st.divider()
        st.markdown("### 🏗️ Pipeline Multi-Agents")
        agents = [
            ("🔍", "ExperienceAnalysisAgent"),
            ("🎯", "SkillsEducationAgent"),
            ("✅", "SummaryValidationAgent"),
            ("📊", "ScoringAgent"),
            ("🏁", "QualityControlAgent"),
            ("📋", "TableGeneratorAgent"),
        ]
        for icon, name in agents:
            st.markdown(
                f'<div class="agent-section">{icon} <strong>{name}</strong></div>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("### 📏 Pondération des scores")
        st.markdown("""
| Critère | Poids |
|---------|-------|
| Expériences | **50 %** |
| Compétences | **20 %** |
| Formations  | **10 %** |
| Résumé      | **20 %** |
        """)

        st.divider()
        st.markdown("### 🏅 Barème /20")
        for lo, hi, label, emoji, color in ALL_LEVELS:
            range_txt = f"{lo}" if lo == hi else f"{lo}–{hi}"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:.5rem;margin:.18rem 0;">'
                f'<span style="font-size:.8rem;background:{color};color:white;'
                f'border-radius:4px;padding:.1rem .45rem;font-weight:600;white-space:nowrap;">'
                f'{range_txt}</span>'
                f'<span style="font-size:.82rem;">{emoji} {label}</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.caption("v1.0.0 · LangChain + Gemini · Pydantic Strict")

        return api_key, model


# ══════════════════════════════════════════════
# RESULT RENDERERS
# ══════════════════════════════════════════════

def render_scores(report: FinalReport):
    scoring   = report.scoring
    score_20  = scoring.note_finale_sur_20
    score_100 = scoring.note_finale_sur_100
    score_class = get_score_class(score_100)
    bareme    = get_bareme(score_20)

    st.markdown('<div class="section-title">📊 Résultat & Appréciation</div>', unsafe_allow_html=True)

    # ── Row 1 : barème card + recommandation + verdict ──
    col_bar, col_rec, col_ver = st.columns([3, 1, 1])

    with col_bar:
        # Main appreciation card driven by barème
        st.markdown(f"""
        <div class="bareme-card" style="background:{bareme['gradient']};">
            <div class="bc-icon">{bareme['emoji']}</div>
            <div class="bc-body">
                <p class="bc-label" style="color:{bareme['text']};">{bareme['label']}</p>
                <p class="bc-desc"  style="color:{bareme['text']};">{bareme['short']}</p>
                <p class="bc-desc"  style="color:{bareme['text']};margin-top:.5rem;font-size:.82rem;">
                    {score_100:.1f} / 100 &nbsp;·&nbsp; {scoring.note_finale_sur_10:.1f} / 10
                </p>
            </div>
            <div class="bc-score" style="color:{bareme['text']};">{score_20:.1f}<br><span>/ 20</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_rec:
        rec       = report.quality_control.recommandation
        rec_emoji = {"Oui": "✅", "Non": "❌", "Peut-être": "⚠️"}.get(rec, "❓")
        rec_color = {"Oui": "#155724", "Non": "#721c24", "Peut-être": "#856404"}.get(rec, "#6c757d")
        rec_bg    = {"Oui": "#d4edda", "Non": "#f8d7da", "Peut-être": "#fff3cd"}.get(rec, "#f0f2f8")
        st.markdown(f"""
        <div class="score-card" style="background:{rec_bg};height:100%;">
            <div style="font-size:2rem;">{rec_emoji}</div>
            <div style="font-size:.85rem;font-weight:600;color:{rec_color};margin-top:.4rem;">
                Recommandation<br><span style="font-size:1.05rem;">{rec}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_ver:
        verdict_label = report.quality_control.verdict.replace("_", " ").title()
        verdict_emoji = {"profil vendeur": "🌟", "profil banal": "😐", "profil intermediaire": "🤔"}.get(
            report.quality_control.verdict.replace("_", " "), "❓"
        )
        st.markdown(f"""
        <div class="score-card" style="background:#f0f2f8;height:100%;">
            <div style="font-size:2rem;">{verdict_emoji}</div>
            <div style="font-size:.85rem;font-weight:600;color:#1a1a2e;margin-top:.4rem;">{verdict_label}</div>
        </div>
        """, unsafe_allow_html=True)

    
    

    # Build proportional segments (total span = 20 notes)
    total_span = 21   # 0-20 inclusive → 21 values
    active_lo, active_hi = bareme["range"]

    segments_html = ""
    for lo, hi, label, emoji, color in ALL_LEVELS:
        span     = hi - lo + 1
        width_pct = span / total_span * 100
        is_active = (lo == active_lo)
        css_class = "bareme-scale-seg active" if is_active else "bareme-scale-seg inactive"
        range_txt = f"{lo}" if lo == hi else f"{lo}–{hi}"
        segments_html += (
            f'<div class="{css_class}" '
            f'style="width:{width_pct:.1f}%;background:{color};" '
            f'title="{label} ({range_txt}/20)">'
            f'{emoji} {range_txt}'
            f'</div>'
        )

    st.markdown(
        f'<div class="bareme-scale">{segments_html}</div>',
        unsafe_allow_html=True,
    )

    # Legend table
    legend_rows = ""
    for lo, hi, label, emoji, color in ALL_LEVELS:
        is_active = (lo == active_lo)
        range_txt = f"{lo}" if lo == hi else f"{lo} à {hi}"
        weight    = "font-weight:700;" if is_active else ""
        border    = f"border-left:4px solid {color};padding-left:.5rem;" if is_active else "padding-left:.74rem;"
        bg        = f"background:rgba(0,0,0,0.04);border-radius:6px;" if is_active else ""
        # find matching short description
        desc = next(e["short"] for e in BAREME if e["range"][0] == lo)
        legend_rows += (
            f'<tr style="{weight}{bg}">'
            f'<td style="{border}white-space:nowrap;">{emoji} <strong>{range_txt}/20</strong></td>'
            f'<td style="padding:0 1rem;white-space:nowrap;">{label}</td>'
            f'<td style="color:#555;font-size:.88rem;">{desc}</td>'
            f'</tr>'
        )

    st.markdown(
        f"""
        <table style="width:100%;border-collapse:collapse;font-size:.9rem;margin-bottom:1.2rem;">
          <thead>
            <tr style="color:#888;font-size:.78rem;border-bottom:1px solid #e0e0e0;">
              <th style="padding:.3rem .5rem;text-align:left;">Note</th>
              <th style="padding:.3rem 1rem;text-align:left;">Appréciation</th>
              <th style="padding:.3rem;text-align:left;">Description</th>
            </tr>
          </thead>
          <tbody>{legend_rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

    # ── Row 3 : detail by criterion ──
    st.markdown('<div class="section-title">📈 Détail par critère</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, detail in enumerate(scoring.details):
        with cols[i]:
            pct = detail.score_brut * 10
            st.metric(
                label=f"{detail.critere}",
                value=f"{detail.score_brut}/10",
                delta=f"Pondéré : {detail.score_pondere:.2f}  (×{detail.poids})",
            )
            st.progress(pct / 100)

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
    api_key, model = render_sidebar()

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
        help="Format accepté : PDF · Taille max recommandée : 10 Mo",
        disabled="report" in st.session_state,  # lock uploader once evaluated
    )

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

        if not api_key:
            st.error("⚠️ Veuillez entrer votre clé API Gemini dans la barre latérale.")
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
                        cv_text = extract_text_from_uploaded_file(uploaded_file)

                    if len(cv_text.strip()) < 50:
                        st.error("❌ Le PDF semble vide ou illisible. Veuillez vérifier le fichier.")
                        return

                    # Persist extracted text for download later
                    st.session_state["cv_text"] = cv_text

                    with st.expander("📄 Texte extrait du CV (aperçu)", expanded=False):
                        st.text(cv_text[:3000] + ("…" if len(cv_text) > 3000 else ""))

                    # Step 2 – run evaluation
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
                    st.error(f"❌ Erreur lors de l'évaluation : {str(e)}")
                    st.exception(e)
                    return

    # ── Results display ──
    if "report" in st.session_state:
        report = st.session_state["report"]
        st.divider()

        # Sidebar metadata
        with st.sidebar:
            st.divider()
            st.markdown("### 📊 Métadonnées")
            meta = report.metadata
            st.caption(f"📅 {meta.get('date_evaluation', 'N/A')}")
            st.caption(f"🤖 {meta.get('modele_llm', 'N/A')}")
            st.caption(f"⏱️ {meta.get('duree_evaluation_secondes', 'N/A')} s")
            st.caption(f"📂 {', '.join(meta.get('sections_detectees', []))}")

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
