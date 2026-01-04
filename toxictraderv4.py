# toxicradar_pro_v4.py
# Streamlit App: Toxic Radar Pro — Visuell harmonisiertes Update
# Deploy-ready

from __future__ import annotations

import os
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

# OpenAI (openai>=1.0.0)
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


# =========================================================
# APP CONFIG
# =========================================================

APP_TITLE = "Toxic Radar Pro"
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# THEME / UI STYLES (HARMONIZED)
# =========================================================

THEMES = {
    "Midnight Serenity": {
        "bg": "#0f172a",          # Deep Slate
        "card": "rgba(30, 41, 59, 0.7)", # Semi-transparent Slate
        "text": "#f1f5f9",        # Slate 100
        "muted": "#94a3b8",       # Slate 400
        "accent": "#38bdf8",      # Sky 400
        "accent_grad": "linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)",
        "danger": "#f43f5e",      # Rose 500
        "success": "#10b981",     # Emerald 500
        "warning": "#f59e0b",     # Amber 500
        "border": "rgba(255, 255, 255, 0.08)",
        "shadow": "0 8px 32px rgba(0, 0, 0, 0.2)",
    },
    "Clean Daylight": {
        "bg": "#f8fafc",          # Slate 50
        "card": "rgba(255, 255, 255, 0.8)",
        "text": "#1e293b",        # Slate 800
        "muted": "#64748b",       # Slate 500
        "accent": "#0ea5e9",      # Sky 500
        "accent_grad": "linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)",
        "danger": "#ef4444",      # Red 500
        "success": "#10b981",     # Emerald 500
        "warning": "#f59e0b",     # Amber 500
        "border": "rgba(148, 163, 184, 0.2)",
        "shadow": "0 8px 32px rgba(148, 163, 184, 0.15)",
    },
}

def inject_css(theme_name: str) -> None:
    t = THEMES.get(theme_name, THEMES["Midnight Serenity"])
    
    st.markdown(
        f"""
        <style>
          :root {{
            --bg: {t["bg"]};
            --card: {t["card"]};
            --text: {t["text"]};
            --muted: {t["muted"]};
            --accent: {t["accent"]};
            --danger: {t["danger"]};
            --warning: {t["warning"]};
            --border: {t["border"]};
            --shadow: {t["shadow"]};
          }}

          /* Global App Styling */
          .stApp {{
            background-color: var(--bg);
            /* Subtle modern mesh gradient */
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(129, 140, 248, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(244, 63, 94, 0.03) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text);
          }}

          /* Typography */
          h1, h2, h3, h4, h5, h6 {{
            color: var(--text) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 600;
          }}
          
          p, div, label, span {{
            color: var(--text);
            font-family: 'Inter', sans-serif;
          }}
          
          .stMarkdown p {{
            line-height: 1.6;
            color: var(--text);
          }}

          /* Modern Cards with Glassmorphism */
          .tr-card {{
            background: var(--card);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 30px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
          }}
          
          .tr-card:hover {{
             box-shadow: 0 12px 40px rgba(0,0,0,0.15); /* Slightly lifted */
          }}

          /* Hero Section */
          .tr-hero {{
            background: {t['accent_grad']};
            border-radius: 24px;
            padding: 40px;
            color: white;
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.3);
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
          }}
          
          .tr-hero::before {{
            content: "";
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            pointer-events: none;
          }}

          .tr-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 99px;
            font-size: 0.85rem;
            font-weight: 500;
            border: 1px solid var(--border);
            background: rgba(255,255,255,0.1);
            color: inherit;
            margin-bottom: 8px;
          }}

          /* Buttons */
          .stButton > button {{
            border-radius: 12px;
            font-weight: 500;
            padding: 0.5rem 1.2rem;
            border: 1px solid var(--border);
            background-color: var(--card);
            color: var(--text);
            transition: all 0.2s ease;
          }}
          
          .stButton > button:hover {{
            border-color: var(--accent);
            color: var(--accent);
            background-color: rgba(255,255,255,0.02);
            transform: translateY(-1px);
          }}

          .stButton > button[kind="primary"] {{
            background: {t['accent_grad']};
            border: none;
            color: white;
            box-shadow: 0 4px 14px 0 rgba(0,118,255,0.25);
          }}
          
          .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 6px 20px rgba(0,118,255,0.23);
            transform: translateY(-2px);
            color: white;
          }}

          /* Inputs & Radios */
          div[data-baseweb="select"] > div {{
            background-color: var(--card);
            border-color: var(--border);
            color: var(--text);
            border-radius: 12px;
          }}
          
          /* Custom Radio Styling */
          div[role="radiogroup"] > label {{
            background: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            margin-bottom: 10px !important;
            transition: border-color 0.2s !important;
          }}
          
          div[role="radiogroup"] > label:hover {{
            border-color: var(--accent) !important;
          }}

          /* Progress Bar Customization */
          div[data-testid="stProgress"] > div > div {{
            background-color: var(--accent);
          }}
          
          div[data-testid="stProgress"] {{
            background-color: rgba(128,128,128,0.1);
            border-radius: 10px;
            height: 8px !important;
          }}

          /* Sidebar */
          section[data-testid="stSidebar"] {{
            background-color: var(--bg); 
            border-right: 1px solid var(--border);
          }}
          
          /* Remove top padding noise */
          .block-container {{
            padding-top: 2rem;
            max-width: 1000px; /* Limit width for better readability on large screens */
          }}

        </style>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# DATA MODELS
# =========================================================

@dataclass(frozen=True)
class Item:
    key: str
    domain: str
    text: str
    tip: str
    weight: float


DOMAINS_ORDER = [
    "Respekt & Kommunikation",
    "Grenzen & Konsens",
    "Kontrolle & Eifersucht",
    "Manipulation & Schuld",
    "Isolation & Abwertung",
    "Volatilität & Angstklima",
    "Verantwortung & Veränderung",
]

# Skala: 0..4 + N/A
ANSWER_OPTIONS = [
    (0, "⚪ Nie"),
    (1, "🟢 Selten"),
    (2, "🟡 Manchmal"),
    (3, "🟠 Oft"),
    (4, "🔴 Sehr oft"),
    (-1, "🚫 Nicht anwendbar"),
]

ITEMS: List[Item] = [
    # Respekt & Kommunikation
    Item("respect_1", "Respekt & Kommunikation", "Ich werde abgewertet, verspottet oder nicht ernst genommen.", "Abwertung ist kein ‚Streitstil‘ – es ist ein Muster, das Selbstwert abbaut.", 1.3),
    Item("respect_2", "Respekt & Kommunikation", "In Diskussionen entschuldige ich mich oft – selbst wenn ich es nicht fühle.", "Wenn du immer schuld bist, ist das selten Zufall.", 1.1),
    Item("respect_3", "Respekt & Kommunikation", "Meine Bedürfnisse/Wünsche werden klein geredet oder übergangen.", "Bedürfnisse sind keine ‚Dramatik‘, sondern legitime Infos.", 1.2),
    Item("respect_4", "Respekt & Kommunikation", "Konflikte laufen unfair (Unterbrechen, Schreien, Drohen, Lächerlichmachen).", "Fairness ist Mindeststandard.", 1.2),
    Item("respect_5", "Respekt & Kommunikation", "Nach Konflikten gibt es keine echte Klärung, nur Funkstille oder ‚weiter so‘.", "Ohne Reparatur bleibt ein Beziehungskonto im Minus.", 1.0),

    # Grenzen & Konsens
    Item("bound_1", "Grenzen & Konsens", "Meine Grenzen werden ignoriert oder ‚überredet‘.", "‚Nein‘ ist ein vollständiger Satz.", 1.4),
    Item("bound_2", "Grenzen & Konsens", "Ich sage oft Ja, um Ärger/Stress zu vermeiden.", "Das ist ein Alarmzeichen für Druck statt Freiwilligkeit.", 1.2),
    Item("bound_3", "Grenzen & Konsens", "Ich habe Angst, meine Meinung offen zu sagen.", "Angst ist kein Normalzustand in Nähe.", 1.3),
    Item("bound_4", "Grenzen & Konsens", "Es gibt Schuldgefühle, wenn ich Zeit/Space für mich brauche.", "Autonomie ist kein Egoismus.", 1.1),

    # Kontrolle & Eifersucht
    Item("control_1", "Kontrolle & Eifersucht", "Eifersucht/Kontrolle bestimmen Regeln (Kleidung, Kontakte, Social Media).", "Kontrolle wird oft als ‚Liebe‘ verkauft.", 1.4),
    Item("control_2", "Kontrolle & Eifersucht", "Mein Handy/Standort/Chats werden geprüft oder eingefordert.", "Transparenz ist freiwillig – Überwachung nicht.", 1.5),
    Item("control_3", "Kontrolle & Eifersucht", "Es gibt Vorwürfe/Stress, wenn ich ohne die Person etwas mache.", "Freiheit darf keine Strafe auslösen.", 1.2),
    Item("control_4", "Kontrolle & Eifersucht", "Es wird mit Entzug (Liebe, Sex, Geld, Aufmerksamkeit) gesteuert.", "Entzug ist ein Machtinstrument.", 1.2),

    # Manipulation & Schuld
    Item("manip_1", "Manipulation & Schuld", "Meine Wahrnehmung wird verdreht (‚Das hast du dir eingebildet‘).", "Gaslighting macht dich unsicher über dich selbst.", 1.5),
    Item("manip_2", "Manipulation & Schuld", "Es gibt ‚Doppelte Standards‘: Regeln gelten nur für mich.", "Ungleichheit ist ein strukturelles Problem.", 1.2),
    Item("manip_3", "Manipulation & Schuld", "Ich werde für Emotionen der anderen Person verantwortlich gemacht.", "Jede*r ist für seine Gefühle zuständig.", 1.3),
    Item("manip_4", "Manipulation & Schuld", "Nach Grenzverletzungen kommt Love-Bombing/Versöhnung ohne echte Änderung.", "Kurzfristige Wärme ersetzt keine Verhaltensänderung.", 1.2),
    Item("manip_5", "Manipulation & Schuld", "Ich fühle mich oft ‚verwirrt‘ nach Gesprächen, obwohl es um einfache Themen ging.", "Verwirrung ist ein typisches Nebenprodukt von Manipulation.", 1.1),

    # Isolation & Abwertung
    Item("iso_1", "Isolation & Abwertung", "Ich distanziere mich von Freunden/Familie, um Konflikte zu vermeiden.", "Isolation passiert oft schleichend.", 1.3),
    Item("iso_2", "Isolation & Abwertung", "Die Person macht meine nahen Beziehungen schlecht oder lächerlich.", "Abwertung deines Umfelds stärkt Abhängigkeit.", 1.2),
    Item("iso_3", "Isolation & Abwertung", "Ich werde öffentlich/privat bloßgestellt.", "Scham ist ein Werkzeug, kein ‚Spaß‘.", 1.3),
    Item("iso_4", "Isolation & Abwertung", "Ich fühle mich klein, unfähig oder ‚zu viel‘ in der Beziehung.", "Wenn du dich dauerhaft klein fühlst, ist das ein Muster.", 1.2),

    # Volatilität & Angstklima
    Item("vol_1", "Volatilität & Angstklima", "Die Stimmung kippt schnell, ich ‚laufe auf Eierschalen‘.", "Eierschalengefühl = permanenter Stressmodus.", 1.4),
    Item("vol_2", "Volatilität & Angstklima", "Es gibt Wutausbrüche, Einschüchterung, Türenknallen, Sachenwerfen.", "Eskalation ist Gefahr – auch ohne Schläge.", 1.5),
    Item("vol_3", "Volatilität & Angstklima", "Ich passe mein Verhalten an, um Ausbrüche zu verhindern.", "Das ist Anpassung aus Angst, nicht Nähe.", 1.3),
    Item("vol_4", "Volatilität & Angstklima", "Nach Eskalationen heißt es später ‚war nicht so schlimm‘.", "Bagatellisieren hält das Muster am Leben.", 1.2),

    # Verantwortung & Veränderung
    Item("resp_1", "Verantwortung & Veränderung", "Bei Problemen übernimmt die Person selten Verantwortung (Entschuldigungen ohne Verhalten).", "‚Sorry‘ ohne Änderung ist ein Loop.", 1.2),
    Item("resp_2", "Verantwortung & Veränderung", "Grenzen/Absprachen werden wiederholt gebrochen.", "Wiederholung = Muster, nicht Ausrutscher.", 1.4),
    Item("resp_3", "Verantwortung & Veränderung", "Hilfsangebote (Therapie/Coaching) werden abgelehnt oder sabotiert.", "Blockierte Hilfe verschlechtert Prognose.", 1.1),
    Item("resp_4", "Verantwortung & Veränderung", "Ich trage den Großteil emotionaler Arbeit/Organisation.", "Einseitigkeit erzeugt Erschöpfung.", 1.0),
]

CRITICAL_FLAGS = [
    ("crit_physical", "Es gab körperliche Gewalt (Schubsen, Festhalten, Schlagen) oder du hast Angst davor."),
    ("crit_threats", "Es gab Drohungen (dir, Kindern, Haustieren, sich selbst) oder Erpressung."),
    ("crit_stalking", "Kontroll-/Stalking-Verhalten: Standort/Handy checken, Nachstellen, Passwörter fordern."),
    ("crit_sexual", "Sexueller Druck/Zwang oder Intimität aus Angst/Schuld."),
    ("crit_weapons", "Waffen/gefährliche Gegenstände im Kontext von Streit/Bedrohung."),
]


# =========================================================
# STATE INIT
# =========================================================

def init_state() -> None:
    defaults = {
        "theme": "Midnight Serenity",
        "step": "intro",
        "context": {},
        "critical": {k: False for k, _ in CRITICAL_FLAGS},
        "answers": {i.key: None for i in ITEMS},
        "q_index": 0,
        "show_results": False,
        "ai_insights": None,
        "history": [],
        "model": "gpt-4o-mini",
        "temp": 0.6,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# =========================================================
# SCORING ENGINE
# =========================================================

class ToxicRadarEngine:
    @staticmethod
    def compute_score(answers: Dict[str, Optional[int]], critical: Dict[str, bool]) -> Tuple[float, Dict[str, float], pd.DataFrame]:
        rows = []
        domain_w = {d: 0.0 for d in DOMAINS_ORDER}
        domain_s = {d: 0.0 for d in DOMAINS_ORDER}

        total_w = 0.0
        total_s = 0.0

        for it in ITEMS:
            v = answers.get(it.key, None)
            if v is None or v == -1:
                continue
            nv = float(v) / 4.0
            total_w += it.weight
            total_s += nv * it.weight
            domain_w[it.domain] += it.weight
            domain_s[it.domain] += nv * it.weight

            if v >= 3:
                rows.append({
                    "Domain": it.domain,
                    "Frage": it.text,
                    "Antwort": v,
                    "Gewicht": it.weight,
                    "Beitrag": nv * it.weight
                })

        base = (total_s / total_w) if total_w > 0 else 0.0

        crit_count = sum(1 for k in critical if critical.get(k, False))
        if crit_count >= 2:
            boost = 0.35
        elif crit_count == 1:
            boost = 0.15
        else:
            boost = 0.0

        final = min(base + boost, 1.0)

        breakdown = {
            d: (domain_s[d] / domain_w[d]) if domain_w[d] > 0 else 0.0
            for d in DOMAINS_ORDER
        }

        df = pd.DataFrame(rows).sort_values(["Beitrag", "Gewicht"], ascending=False) if rows else pd.DataFrame(
            columns=["Domain", "Frage", "Antwort", "Gewicht", "Beitrag"]
        )

        return final, breakdown, df

    @staticmethod
    def classify(score: float, critical: Dict[str, bool]) -> str:
        crit_count = sum(1 for k in critical if critical.get(k, False))
        if crit_count >= 3:
            return "SCHWARZ"
        if crit_count == 2:
            return "DUNKELROT"
        if crit_count == 1:
            return "ROT" if score > 0.5 else "ORANGE"

        if score < 0.15:
            return "GRÜN"
        if score < 0.35:
            return "HELLGRÜN"
        if score < 0.55:
            return "GELB"
        if score < 0.75:
            return "ORANGE"
        if score < 0.9:
            return "ROT"
        return "DUNKELROT"

    @staticmethod
    def severity_color(level: str) -> str:
        return {
            "GRÜN": "#10b981",    # Emerald
            "HELLGRÜN": "#84cc16",# Lime
            "GELB": "#facc15",    # Yellow
            "ORANGE": "#fb923c",  # Orange
            "ROT": "#ef4444",     # Red
            "DUNKELROT": "#991b1b", # Dark Red
            "SCHWARZ": "#0f172a", # Dark Slate
        }.get(level, "#64748B")

    @staticmethod
    def recommendations(level: str, critical: Dict[str, bool]) -> List[str]:
        base = [
            "📓 **Dokumentiere Muster**: Datum, Situation, Verhalten, dein Gefühl, Folgen.",
            "🧩 **Klarer Boundary-Satz**: 'Wenn X passiert, dann mache ich Y.' (konkret & umsetzbar).",
            "🧭 **Reality-Check**: 1–2 vertrauenswürdige Personen spiegeln lassen, was du erlebst.",
        ]

        if any(critical.values()) or level in {"ROT", "DUNKELROT", "SCHWARZ"}:
            return [
                "🚨 **Sicherheit zuerst**: Wenn du dich bedroht fühlst → 112. Wenn möglich: sichere Orte, Schlüssel, Geld, Dokumente.",
                "📞 **Support aktivieren**: 2–3 Personen informieren, Codewort vereinbaren, Check-in Zeiten.",
                "🧰 **Professionelle Hilfe**: Beratungsstelle/Therapie/Rechtsberatung (je nach Situation).",
                *base,
            ]

        if level in {"ORANGE", "GELB"}:
            return [
                "🧪 **Experiment**: 14 Tage lang eine Grenze konsequent setzen und Wirkung beobachten.",
                "🗣️ **Konflikt-Regeln**: Kein Schreien/Beleidigen; Time-out; Rückkehr mit konkreter Klärung.",
                "📈 **Messpunkt**: Häufigkeit von Eskalationen/Abwertung pro Woche tracken.",
                *base,
            ]

        return [
            "✅ **Stärken sichern**: Was funktioniert, bewusst wiederholen.",
            "📌 **Frühwarnsignale**: 3 Trigger definieren (z. B. Spott, Kontrolle, Funkstille) + Plan.",
            *base,
        ]


# =========================================================
# VISUALS
# =========================================================

class VisualizationEngine:
    @staticmethod
    def radar(breakdown: Dict[str, float]) -> go.Figure:
        fig = go.Figure()
        
        # Use theme colors for chart
        fill_color = "rgba(56, 189, 248, 0.4)" if st.session_state.theme == "Midnight Serenity" else "rgba(14, 165, 233, 0.3)"
        line_color = "#38bdf8" if st.session_state.theme == "Midnight Serenity" else "#0ea5e9"
        text_color = "#e2e8f0" if st.session_state.theme == "Midnight Serenity" else "#334155"

        fig.add_trace(go.Scatterpolar(
            r=list(breakdown.values()),
            theta=list(breakdown.keys()),
            fill="toself",
            name="Ausprägung",
            line_color=line_color,
            fillcolor=fill_color
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], tickformat=",.0%", showline=False),
                bgcolor="rgba(0,0,0,0)",
            ),
            font=dict(family="Inter, sans-serif", size=12, color=text_color),
            showlegend=False,
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=50, r=50, t=30, b=30),
        )
        return fig

    @staticmethod
    def bar_domain(breakdown: Dict[str, float]) -> go.Figure:
        df = pd.DataFrame({"Domain": list(breakdown.keys()), "Belastung": list(breakdown.values())})
        
        bar_color = "#38bdf8" if st.session_state.theme == "Midnight Serenity" else "#0ea5e9"
        text_color = "#e2e8f0" if st.session_state.theme == "Midnight Serenity" else "#334155"

        fig = px.bar(df, x="Domain", y="Belastung")
        fig.update_traces(marker_color=bar_color, marker_line_width=0, opacity=0.9)
        
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)", tickformat=",.0%"),
            font=dict(family="Inter, sans-serif", size=12, color=text_color),
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20),
        )
        return fig


# =========================================================
# OPENAI / PDF LOGIC
# =========================================================

def get_api_key() -> str:
    override = st.session_state.get("api_key_override", "") or ""
    if override.strip():
        return override.strip()
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()

def ai_analyze(answers, critical, score, breakdown, context, model, temperature) -> Dict:
    if OpenAI is None:
        raise RuntimeError("OpenAI Paket nicht installiert.")
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Kein API Key gefunden.")

    client = OpenAI(api_key=api_key)
    
    # Simple summary builder
    answered_items = []
    for it in ITEMS:
        v = answers.get(it.key, None)
        if v is not None and v != -1 and v >= 2:
            answered_items.append(f"- {it.text} (Intensität {v}/4)")

    crit_on = [desc for k, desc in CRITICAL_FLAGS if critical.get(k, False)]
    domain_lines = [f"- {d}: {breakdown.get(d, 0.0):.0%}" for d in DOMAINS_ORDER]

    prompt = f"""
    Du bist ein erfahrener Therapeut. Analysiere folgende Daten:
    Kontext: {json.dumps(context, ensure_ascii=False)}
    Score: {score:.0%}
    Domains: {', '.join(domain_lines)}
    Muster (High): {'; '.join(answered_items[:15])}
    Kritisch: {'; '.join(crit_on) if crit_on else 'Keine'}
    
    Liefere:
    1) Top-3 Dynamiken
    2) Auswirkungen
    3) 5 Schritte
    4) Risiko
    5) 3 Affirmationen
    
    Antwort auf Deutsch, empathisch, direkt, keine Diagnose.
    """

    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "Therapeutischer Assistent."}, {"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return {"text": res.choices[0].message.content, "model": model, "created_at": datetime.now().isoformat()}

class ReportPDF:
    @staticmethod
    def build(report: Dict, ai: Optional[Dict]) -> BytesIO:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "Toxic Radar Pro - Analyse", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Erstellt am: {report['timestamp']} | Ergebnis: {report['level']}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Empfehlungen", ln=True)
        pdf.set_font("Arial", "", 11)
        for r in ToxicRadarEngine.recommendations(report["level"], report["critical"]):
            pdf.multi_cell(0, 7, f"- {r}")
            
        if ai:
            pdf.ln(5)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "KI-Analyse", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 7, ai.get("text", ""))

        buff = BytesIO()
        buff.write(pdf.output(dest="S").encode("latin1", errors="replace"))
        buff.seek(0)
        return buff


# =========================================================
# UI BUILDING BLOCKS
# =========================================================

def hero() -> None:
    st.markdown(
        f"""
        <div class="tr-hero">
          <div style="position:relative; z-index:2;">
            <div class="tr-badge">Self-Reflection AI Tool</div>
            <h1 style="color:white !important; margin:12px 0; font-size:2.8rem; font-weight:700;">{APP_TITLE}</h1>
            <p style="opacity:0.9; font-size:1.1rem; max-width:600px; line-height:1.6;">
                Erkenne Muster, schütze deine Energie. Ein interaktiver Check mit wissenschaftlich fundierten Fragen und optionaler KI-Auswertung.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def safety_box() -> None:
    with st.expander("🚨 Sicherheitshinweis (Wichtig)", expanded=False):
        st.warning(
            "Bei akuter Gefahr wähle sofort die **112**. Dieses Tool ersetzt keine Therapie."
        )
        st.markdown(
            "- **Hilfetelefon Gewalt gegen Frauen:** 08000 116 016\n"
            "- **TelefonSeelsorge:** 0800 111 0 111"
        )

def sidebar() -> None:
    with st.sidebar:
        st.markdown("### ⚙️ Einstellungen")
        st.session_state.theme = st.selectbox("Design wählen", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
        
        st.divider()
        st.markdown("### 🧠 KI-Integration")
        api_key_input = st.text_input("OpenAI API Key (Optional)", type="password", help="Wird nicht gespeichert, nur für diese Session genutzt.")
        if api_key_input:
            st.session_state.api_key_override = api_key_input
            
        st.divider()
        if st.button("Neustart", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


def nav_buttons(prev_step: Optional[str], next_step: Optional[str], next_label: str = "Weiter") -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, _, c2 = st.columns([1, 2, 1])
    with c1:
        if prev_step and st.button("← Zurück", use_container_width=True):
            st.session_state.step = prev_step
            st.rerun()
    with c2:
        if next_step and st.button(f"{next_label} →", type="primary", use_container_width=True):
            st.session_state.step = next_step
            st.rerun()


# =========================================================
# STEPS
# =========================================================

def step_intro() -> None:
    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown("### Willkommen")
    st.markdown(
        """
        Dieser Radar hilft dir, Klarheit in deine Beziehungssituation zu bringen.
        
        1. **Kontext:** Kurze Einordnung deiner Situation.
        2. **Warnzeichen:** Abfrage harter Ausschlusskriterien.
        3. **Deep Dive:** 32 Fragen zu verschiedenen Lebensbereichen.
        4. **Auswertung:** Visuelle Analyse und Handlungsempfehlungen.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons(None, "context", "Starten")

def step_context() -> None:
    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Deine Situation")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.context["beziehungsform"] = st.selectbox("Beziehungstyp", ["Partnerschaft", "Dating", "Ex-Partner", "Familie", "Job", "Freundschaft"])
        st.session_state.context["dauer"] = st.selectbox("Dauer", ["< 3 Monate", "3–12 Monate", "1–3 Jahre", "> 3 Jahre"])
    with c2:
        st.session_state.context["kontakt"] = st.selectbox("Kontaktfrequenz", ["Täglich", "Wöchentlich", "Selten", "Abgebrochen"])
        st.session_state.context["belastung"] = st.select_slider("Gefühlte Belastung", options=["Gering", "Mittel", "Hoch", "Extrem"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.session_state.context["notiz"] = st.text_area("Persönliche Notiz (Optional)", height=80, placeholder="Was beschäftigt dich gerade am meisten?")
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons("intro", "critical")

def step_critical() -> None:
    st.markdown('<div class="tr-card" style="border-left: 4px solid var(--danger);">', unsafe_allow_html=True)
    st.markdown("### ⚠️ Red Flags")
    st.markdown("Bitte bestätige ehrlich, ob folgende Punkte zutreffen. Dies beeinflusst die Sicherheitsempfehlungen massiv.")
    
    for k, desc in CRITICAL_FLAGS:
        st.session_state.critical[k] = st.checkbox(desc, value=st.session_state.critical.get(k, False))
        
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons("context", "questions")

def step_questions() -> None:
    total = len(ITEMS)
    current = st.session_state.q_index
    item = ITEMS[current]

    # Progress bar with custom styling
    st.progress((current + 1) / total)
    st.caption(f"Frage {current + 1} von {total}")

    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown(f"<span class='tr-badge'>{item.domain}</span>", unsafe_allow_html=True)
    st.markdown(f"### {item.text}")
    st.info(f"💡 {item.tip}")
    
    # Custom Radio Rendering
    current_val = st.session_state.answers.get(item.key, None)
    idx = 2 # Default middle
    if current_val is not None:
         # find index of val
         vals = [x[0] for x in ANSWER_OPTIONS]
         if current_val in vals:
             idx = vals.index(current_val)
    
    sel_label = st.radio("Antwort", [x[1] for x in ANSWER_OPTIONS], index=idx, label_visibility="collapsed")
    
    # Map back to int
    val_map = {lbl: val for val, lbl in ANSWER_OPTIONS}
    st.session_state.answers[item.key] = val_map[sel_label]
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("← Zurück", disabled=current==0, use_container_width=True):
            st.session_state.q_index -= 1
            st.rerun()
    with c2:
        if st.button("Überspringen", use_container_width=True):
            st.session_state.answers[item.key] = -1
            st.session_state.q_index += 1 if current < total -1 else 0
            if current == total - 1:
                st.session_state.step = "results"
            st.rerun()
    with c3:
        if current < total - 1:
            if st.button("Weiter", type="primary", use_container_width=True):
                st.session_state.q_index += 1
                st.rerun()
        else:
            if st.button("🏁 Auswertung anzeigen", type="primary", use_container_width=True):
                st.session_state.step = "results"
                st.rerun()

def step_results() -> None:
    score, breakdown, strong_df = ToxicRadarEngine.compute_score(st.session_state.answers, st.session_state.critical)
    level = ToxicRadarEngine.classify(score, st.session_state.critical)
    color = ToxicRadarEngine.severity_color(level)

    st.markdown(
        f"""
        <div class="tr-card" style="border-top: 6px solid {color}; text-align:center;">
          <div class="tr-badge">Ergebnis</div>
          <h1 style="color:{color} !important; font-size: 3.5rem; margin: 10px 0;">{level}</h1>
          <p style="font-size:1.2rem;">Belastungs-Score: <b>{score:.0%}</b></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tr-card">', unsafe_allow_html=True)
        st.markdown("### 🕸️ Muster-Radar")
        st.plotly_chart(VisualizationEngine.radar(breakdown), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tr-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Belastung nach Bereich")
        st.plotly_chart(VisualizationEngine.bar_domain(breakdown), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 💡 Deine nächsten Schritte")
    recs = ToxicRadarEngine.recommendations(level, st.session_state.critical)
    
    r_cols = st.columns(len(recs))
    for i, r in enumerate(recs):
        with r_cols[i]:
            st.markdown(f'<div class="tr-card" style="font-size:0.95rem; height:100%;">{r}</div>', unsafe_allow_html=True)

    if st.button("✨ KI-Analyse generieren (Beta)", type="primary", use_container_width=True):
        with st.spinner("Analysiere Daten..."):
            try:
                st.session_state.ai_insights = ai_analyze(
                    st.session_state.answers, st.session_state.critical, score, breakdown,
                    st.session_state.context, st.session_state.model, st.session_state.temp
                )
            except Exception as e:
                st.error(f"Fehler: {str(e)}")

    if st.session_state.ai_insights:
        st.markdown('<div class="tr-card">', unsafe_allow_html=True)
        st.markdown("### 🤖 KI-Einschätzung")
        st.markdown(st.session_state.ai_insights["text"])
        st.markdown("</div>", unsafe_allow_html=True)

    # Export
    report_data = {
        "id": "TR-Export", "timestamp": datetime.now().strftime("%Y-%m-%d"),
        "score": score, "level": level, "context": st.session_state.context,
        "critical": st.session_state.critical, "answers": {}, "breakdown": breakdown
    }
    
    pdf_bytes = ReportPDF.build(report_data, st.session_state.ai_insights)
    st.download_button("📄 PDF Report laden", data=pdf_bytes, file_name="toxic_radar_report.pdf", mime="application/pdf", use_container_width=True)

    if st.button("↺ Neuer Check"):
        st.session_state.step = "intro"
        st.rerun()


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    inject_css(st.session_state.theme)
    sidebar()
    hero()
    safety_box()

    step = st.session_state.step
    if step == "intro": step_intro()
    elif step == "context": step_context()
    elif step == "critical": step_critical()
    elif step == "questions": step_questions()
    elif step == "results": step_results()
    else: step_intro()

if __name__ == "__main__":
    main()

