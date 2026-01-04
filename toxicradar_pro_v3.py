
# toxicradar_pro_v3.py
# Streamlit App: Toxic Radar Pro — interaktiver Beziehungs-Check + optionale KI-Insights
# Deploy-ready (API Key via ENV oder Streamlit Secrets)

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

APP_TITLE = "🧭 Toxic Radar Pro"
st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")


# =========================================================
# THEME / UI STYLES
# =========================================================

THEMES = {
    "Radar Dark": {
        "bg": "#0B1220",
        "card": "#101A2D",
        "text": "#E7EEF9",
        "muted": "#AFC2E6",
        "accent": "#2EE59D",     # Radar green
        "accent2": "#7C3AED",    # Purple
        "danger": "#FF3D00",
        "warning": "#FFB000",
        "border": "rgba(255,255,255,0.10)",
    },
    "Radar Light": {
        "bg": "#F7FAFF",
        "card": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#475569",
        "accent": "#0EA5E9",     # Cyan
        "accent2": "#7C3AED",    # Purple
        "danger": "#DC2626",
        "warning": "#F59E0B",
        "border": "rgba(2,6,23,0.10)",
    },
}

def inject_css(theme_name: str) -> None:
    t = THEMES.get(theme_name, THEMES["Radar Dark"])
    st.markdown(
        f"""
        <style>
          :root {{
            --bg: {t["bg"]};
            --card: {t["card"]};
            --text: {t["text"]};
            --muted: {t["muted"]};
            --accent: {t["accent"]};
            --accent2: {t["accent2"]};
            --danger: {t["danger"]};
            --warning: {t["warning"]};
            --border: {t["border"]};
          }}

          /* App background */
          .stApp {{
            background: radial-gradient(1200px 600px at 20% 0%, rgba(124,58,237,0.12), transparent 60%),
                        radial-gradient(900px 500px at 80% 10%, rgba(46,229,157,0.10), transparent 60%),
                        var(--bg);
            color: var(--text);
          }}

          /* Typography tweaks */
          html, body, [class*="css"] {{
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
          }}

          /* Cards */
          .tr-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 18px 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
          }}

          .tr-hero {{
            background: linear-gradient(135deg, rgba(124,58,237,0.95), rgba(14,165,233,0.92));
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 22px;
            padding: 22px 22px;
            color: white;
            box-shadow: 0 14px 34px rgba(0,0,0,0.22);
          }}

          .tr-badge {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            border: 1px solid var(--border);
            color: var(--text);
            background: rgba(255,255,255,0.06);
          }}

          /* Make sidebar feel modern */
          section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(16,26,45,0.85), rgba(16,26,45,0.60));
            border-right: 1px solid var(--border);
          }}

          /* Buttons */
          .stButton > button {{
            border-radius: 14px;
            border: 1px solid var(--border);
            padding: 0.65rem 1rem;
          }}
          .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--accent2), var(--accent));
            border: 0;
          }}

          /* Radio/slider labels spacing */
          div[role="radiogroup"] > label {{
            padding: 10px 10px !important;
            border-radius: 14px !important;
            border: 1px solid var(--border) !important;
            margin-bottom: 8px !important;
            background: rgba(255,255,255,0.04) !important;
          }}

          /* Reduce top whitespace */
          .block-container {{
            padding-top: 1.6rem;
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
    (-1, "🚫 Nicht anwendbar / kann ich nicht beurteilen"),
]

# Eine solide, vollständige Fragenbank (deploy-ready)
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
        "theme": "Radar Dark",
        "step": "intro",  # intro -> context -> critical -> questions -> results
        "context": {},
        "critical": {k: False for k, _ in CRITICAL_FLAGS},
        "answers": {i.key: None for i in ITEMS},  # int 0..4, -1 for N/A
        "q_index": 0,
        "show_results": False,
        "ai_insights": None,
        "history": [],  # saved reports
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
        """
        Score 0..1, Domain breakdown 0..1, and a DataFrame of strongest items.
        N/A (-1) answers are excluded from denominator to avoid forcing guesses.
        """
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
            "GRÜN": "#00C853",
            "HELLGRÜN": "#64DD17",
            "GELB": "#FFD600",
            "ORANGE": "#FF9100",
            "ROT": "#FF3D00",
            "DUNKELROT": "#D50000",
            "SCHWARZ": "#111111",
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
        fig.add_trace(go.Scatterpolar(
            r=list(breakdown.values()),
            theta=list(breakdown.keys()),
            fill="toself",
            name="Ausprägung",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickformat=",.0%")),
            showlegend=False,
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=20, b=20),
        )
        return fig

    @staticmethod
    def bar_domain(breakdown: Dict[str, float]) -> go.Figure:
        df = pd.DataFrame({"Domain": list(breakdown.keys()), "Belastung": list(breakdown.values())})
        fig = px.bar(df, x="Domain", y="Belastung")
        fig.update_layout(
            yaxis_tickformat=",.0%",
            height=420,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        return fig


# =========================================================
# OPENAI INTEGRATION (optional)
# =========================================================

def get_api_key() -> str:
    # priority: session override -> st.secrets -> env
    override = st.session_state.get("api_key_override", "") or ""
    if override.strip():
        return override.strip()
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return str(st.secrets["OPENAI_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()

def ai_analyze(
    answers: Dict[str, Optional[int]],
    critical: Dict[str, bool],
    score: float,
    breakdown: Dict[str, float],
    context: Dict,
    model: str,
    temperature: float,
) -> Dict:
    if OpenAI is None:
        raise RuntimeError("openai Paket nicht verfügbar. Bitte openai>=1.0.0 installieren.")
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Kein API Key gefunden. Setze OPENAI_API_KEY als ENV oder in Streamlit Secrets.")

    client = OpenAI(api_key=api_key)

    # Summaries
    answered_items = []
    for it in ITEMS:
        v = answers.get(it.key, None)
        if v is None or v == -1:
            continue
        if v >= 2:
            answered_items.append(f"- {it.text} (Intensität {v}/4)")

    crit_on = [desc for k, desc in CRITICAL_FLAGS if critical.get(k, False)]
    domain_lines = [f"- {d}: {breakdown.get(d, 0.0):.0%}" for d in DOMAINS_ORDER]

    prompt = f"""
Du bist ein erfahrener Therapeut (mit Fokus auf toxische Dynamiken, Gewaltprävention und Selbstschutz).
Analysiere die folgenden Angaben strukturiert und praxisnah.

KONTEXT (kurz):
{json.dumps(context, ensure_ascii=False)}

SCORE:
- Gesamt: {score:.0%}

DOMAINS:
{chr(10).join(domain_lines)}

MUSTER (ab "manchmal"):
{chr(10).join(answered_items[:18]) if answered_items else "- (keine Angabe)"}

KRITISCHE FLAGS:
{chr(10).join([f"- {c}" for c in crit_on]) if crit_on else "- Keine"}

Bitte liefere:
1) Top-3 Dynamiken (klar benennen + Woran erkennt man das?).
2) Wahrscheinliche Auswirkungen (kurz, nicht pathologisieren).
3) 5 konkrete nächste Schritte (inkl. 1 Sicherheits-Schritt, auch wenn niedriges Risiko).
4) Risiko-Einschätzung (niedrig/mittel/hoch) + warum.
5) 3 Sätze, die die Person sich sagen kann (Selbstvalidierung, nicht kitschig).

Antwort auf Deutsch. Keine Diagnosen. Keine Schuldzuweisung. Klar, direkt, mitfühlend.
""".strip()

    res = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Du bist ein einfühlsamer, aber direkter Therapeut. Fokus: Klarheit, Sicherheit, Selbstschutz."},
            {"role": "user", "content": prompt},
        ],
        temperature=float(temperature),
        max_tokens=1200,
    )
    return {
        "text": res.choices[0].message.content,
        "model": model,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


# =========================================================
# PDF REPORT
# =========================================================

class ReportPDF:
    @staticmethod
    def build(report: Dict, ai: Optional[Dict]) -> BytesIO:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=14)

        def h(txt: str, size: int = 16):
            pdf.set_font("Arial", "B", size)
            pdf.multi_cell(0, 10, txt)

        def p(txt: str, size: int = 11):
            pdf.set_font("Arial", "", size)
            pdf.multi_cell(0, 7, txt)

        h("Toxic Radar Pro — Analysebericht", 20)
        p(f"Erstellt am: {report['timestamp']}")
        p(f"Report-ID: {report['id']}")
        pdf.ln(2)

        h("Ergebnis", 16)
        p(f"Ampelstufe: {report['level']}")
        p(f"Score: {report['score']:.0%}")
        pdf.ln(2)

        h("Kontext", 14)
        p(json.dumps(report["context"], ensure_ascii=False, indent=2))
        pdf.ln(2)

        h("Kritische Warnzeichen", 14)
        crit_on = [desc for k, desc in CRITICAL_FLAGS if report["critical"].get(k, False)]
        p("\n".join([f"- {c}" for c in crit_on]) if crit_on else "- Keine")
        pdf.ln(2)

        h("Empfehlungen", 14)
        for r in ToxicRadarEngine.recommendations(report["level"], report["critical"]):
            p(f"- {r}")

        if ai:
            pdf.ln(2)
            h("KI-Analyse (optional)", 14)
            p(ai.get("text", ""))

        buff = BytesIO()
        buff.write(pdf.output(dest="S").encode("latin1"))
        buff.seek(0)
        return buff


# =========================================================
# UI BUILDING BLOCKS
# =========================================================

def hero() -> None:
    st.markdown(
        f"""
        <div class="tr-hero">
          <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;">
            <div>
              <div class="tr-badge">AI-gestützter Selbstreflexions-Check</div>
              <h1 style="margin:10px 0 6px 0;">{APP_TITLE}</h1>
              <div style="opacity:0.95;max-width:70ch;">
                Interaktiver Fragebogen (Fragen nacheinander) + klare Auswertung nach Bereichen.
                Optional kannst du dir zusätzlich eine KI-Einschätzung generieren lassen (API-Key via ENV/Secrets).
              </div>
            </div>
            <div style="text-align:right;opacity:0.9;">
              <div style="font-size:12px;">Version</div>
              <div style="font-weight:700;">v3</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def safety_box() -> None:
    with st.expander("🚨 Sicherheitshinweis (bitte lesen)", expanded=True):
        st.warning(
            "Bei akuter Gefahr: **112**. Dieses Tool ist **keine Diagnose** und ersetzt keine professionelle Hilfe. "
            "Wenn Gewalt, Drohungen oder Stalking im Spiel sind: Sicherheit hat Priorität."
        )
        st.markdown(
            "- Hilfetelefon Gewalt gegen Frauen: **08000 116 016**  \n"
            "- TelefonSeelsorge: **0800 111 0 111** / **0800 111 0 222**  \n"
            "- Ärztlicher Bereitschaftsdienst: **116 117**"
        )

def sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚙️ Einstellungen")
        st.session_state.theme = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme))
        st.divider()

        st.markdown("### 🔑 OpenAI (optional)")
        has_key = bool(get_api_key())
        st.caption("Für KI-Insights: setze **OPENAI_API_KEY** als ENV oder in **.streamlit/secrets.toml**.")
        st.write("Status:", "✅ Key erkannt" if has_key else "⚪ Kein Key erkannt")

        st.session_state.api_key_override = st.text_input(
            "Key temporär überschreiben (wird nicht gespeichert)",
            type="password",
            value=st.session_state.get("api_key_override", ""),
        )

        st.session_state.model = st.text_input("Model", value=st.session_state.model)
        st.session_state.temp = st.slider("Temperatur", 0.0, 1.0, float(st.session_state.temp), 0.05)

        st.divider()
        st.markdown("### 🧹 Reset")
        if st.button("Alles zurücksetzen"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.divider()
        st.markdown("### 📌 Navigation")
        st.caption("Du kannst jederzeit zurückspringen, ohne Antworten zu verlieren.")
        st.write("Aktueller Schritt:", f"**{st.session_state.step}**")


def nav_buttons(prev_step: Optional[str], next_step: Optional[str], next_label: str = "Weiter") -> None:
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if prev_step and st.button("← Zurück", use_container_width=True):
            st.session_state.step = prev_step
            st.rerun()
    with c3:
        if next_step and st.button(f"{next_label} →", type="primary", use_container_width=True):
            st.session_state.step = next_step
            st.rerun()


# =========================================================
# STEPS
# =========================================================

def step_intro() -> None:
    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown("### So funktioniert’s")
    st.markdown(
        "1) Kontext (kurz)  \n"
        "2) Kritische Warnzeichen  \n"
        "3) Fragen **nacheinander** (schnell, fokussiert)  \n"
        "4) Ergebnis + Empfehlungen + optional KI-Insights  \n\n"
        "💡 Tipp: Nutze **Nicht anwendbar**, wenn du wirklich keine Einschätzung hast – das hält die Auswertung sauber."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons(None, "context", next_label="Start")

def step_context() -> None:
    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Kontext")
    cols = st.columns(4)
    with cols[0]:
        rel_type = st.selectbox("Beziehungsform", [
            "Romantische Partnerschaft", "Ehe", "Dating", "Ex-Partner",
            "Familie", "Freundschaft", "Arbeitsverhältnis", "Sonstiges"
        ], index=0)
    with cols[1]:
        duration = st.selectbox("Dauer", ["< 3 Monate", "3–12 Monate", "1–3 Jahre", "3–7 Jahre", "> 7 Jahre"], index=2)
    with cols[2]:
        contact = st.selectbox("Kontakthäufigkeit", ["Täglich", "Mehrmals wöchentlich", "Wöchentlich", "Monatlich", "Unregelmäßig"], index=0)
    with cols[3]:
        burden = st.select_slider("Aktuelle Belastung", options=["Gering", "Mittel", "Hoch", "Sehr hoch"], value="Mittel")

    note = st.text_area("Optional: 1–2 Sätze, was dich gerade am meisten beschäftigt (für dich / oder für KI-Analyse)", height=90)

    st.session_state.context = {
        "beziehungsform": rel_type,
        "dauer": duration,
        "kontakt": contact,
        "belastung": burden,
        "notiz": note.strip(),
    }
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons("intro", "critical")

def step_critical() -> None:
    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown("### ⚠️ Kritische Warnzeichen")
    st.info("Wenn hier etwas zutrifft, ist Sicherheit immer wichtiger als ‚Beziehungsarbeit‘.")
    cols = st.columns(2)
    for idx, (k, desc) in enumerate(CRITICAL_FLAGS):
        with cols[idx % 2]:
            st.session_state.critical[k] = st.checkbox(desc, value=bool(st.session_state.critical.get(k, False)))
    st.markdown("</div>", unsafe_allow_html=True)
    nav_buttons("context", "questions")

def _answered_count() -> int:
    return sum(1 for v in st.session_state.answers.values() if v is not None)

def _total_count() -> int:
    return len(ITEMS)

def step_questions() -> None:
    # Progress / Overview
    answered = _answered_count()
    total = _total_count()
    st.progress(answered / total, text=f"Fortschritt: {answered}/{total}")

    # Domain badge
    q_idx = int(st.session_state.q_index)
    q_idx = max(0, min(q_idx, total - 1))
    st.session_state.q_index = q_idx
    item = ITEMS[q_idx]

    st.markdown('<div class="tr-card">', unsafe_allow_html=True)
    st.markdown(f"### 🔍 Frage {q_idx+1} von {total}")
    st.markdown(f"<span class='tr-badge'>{item.domain}</span>", unsafe_allow_html=True)
    st.markdown(f"#### {item.text}")
    st.caption(item.tip)

    # Current value -> radio index
    cur = st.session_state.answers.get(item.key, None)
    labels = [lbl for _, lbl in ANSWER_OPTIONS]
    values = [val for val, _ in ANSWER_OPTIONS]
    if cur is None:
        default_index = 2  # preselect "Manchmal" as neutral middle
    else:
        default_index = values.index(cur) if cur in values else 2

    choice_label = st.radio(
        "Deine Einschätzung",
        labels,
        index=default_index,
        label_visibility="collapsed"
    )
    chosen_val = values[labels.index(choice_label)]
    st.session_state.answers[item.key] = chosen_val

    # Quick jump (optional)
    with st.expander("⚡ Schnell springen", expanded=False):
        jump = st.number_input("Zu Frage Nr.", min_value=1, max_value=total, value=q_idx + 1)
        if st.button("Springen"):
            st.session_state.q_index = int(jump) - 1
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Navigation buttons with validation
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("← Vorherige", use_container_width=True, disabled=(q_idx == 0)):
            st.session_state.q_index = max(0, q_idx - 1)
            st.rerun()
    with c2:
        if st.button("Überspringen", use_container_width=True):
            st.session_state.answers[item.key] = -1
            st.session_state.q_index = min(total - 1, q_idx + 1)
            st.rerun()
    with c3:
        if q_idx < total - 1:
            if st.button("Nächste →", type="primary", use_container_width=True):
                st.session_state.q_index = min(total - 1, q_idx + 1)
                st.rerun()
        else:
            if st.button("🚀 Auswerten", type="primary", use_container_width=True):
                st.session_state.step = "results"
                st.rerun()

def step_results() -> None:
    score, breakdown, strong_df = ToxicRadarEngine.compute_score(st.session_state.answers, st.session_state.critical)
    level = ToxicRadarEngine.classify(score, st.session_state.critical)
    color = ToxicRadarEngine.severity_color(level)

    # Result hero
    st.markdown(
        f"""
        <div class="tr-card" style="border:1px solid {color};">
          <div style="display:flex;gap:18px;align-items:center;justify-content:space-between;flex-wrap:wrap;">
            <div>
              <div class="tr-badge">Ergebnis</div>
              <h2 style="margin:8px 0 0 0;color:{color};font-size:42px;line-height:1;">{level}</h2>
              <div style="font-size:18px;margin-top:8px;">Gesamtbelastung: <b>{score:.0%}</b></div>
            </div>
            <div style="min-width:260px;">
              <div class="tr-badge">Domains</div>
              <div style="margin-top:10px;opacity:0.95;">
                {", ".join([f"{d.split(' ')[0]} {breakdown.get(d,0):.0%}" for d in DOMAINS_ORDER[:3]])}
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Charts
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🧭 Radar")
        st.plotly_chart(VisualizationEngine.radar(breakdown), use_container_width=True)
    with c2:
        st.markdown("### 📊 Bereiche")
        st.plotly_chart(VisualizationEngine.bar_domain(breakdown), use_container_width=True)

    # Strong patterns
    st.markdown("### 🔥 Auffällige Muster (Antwort: Oft / Sehr oft)")
    if strong_df.empty:
        st.info("Keine starken Muster markiert (oder vieles wurde als N/A übersprungen).")
    else:
        st.dataframe(strong_df[["Domain", "Frage", "Antwort", "Gewicht"]], use_container_width=True, hide_index=True)

    # Recommendations
    st.markdown("### 🛡️ Empfehlungen")
    recs = ToxicRadarEngine.recommendations(level, st.session_state.critical)
    cols = st.columns(2)
    for i, r in enumerate(recs):
        with cols[i % 2]:
            st.info(r)

    # Optional AI
    st.markdown("### 🤖 Optionale KI-Analyse")
    if st.button("🧠 KI-Analyse generieren", type="primary"):
        try:
            with st.spinner("KI analysiert…"):
                st.session_state.ai_insights = ai_analyze(
                    answers=st.session_state.answers,
                    critical=st.session_state.critical,
                    score=score,
                    breakdown=breakdown,
                    context=st.session_state.context,
                    model=st.session_state.model,
                    temperature=st.session_state.temp,
                )
            st.success("Fertig.")
        except Exception as e:
            st.error(str(e))

    if st.session_state.ai_insights:
        st.markdown('<div class="tr-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.ai_insights.get("text", ""))
        st.caption(f"Model: {st.session_state.ai_insights.get('model')} • {st.session_state.ai_insights.get('created_at')}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Export
    st.markdown("### 📤 Export")
    report = {
        "id": f"TR{random.randint(10000, 99999)}",
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "score": score,
        "level": level,
        "context": st.session_state.context,
        "critical": st.session_state.critical,
        "answers": st.session_state.answers,
        "breakdown": breakdown,
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        pdf = ReportPDF.build(report, st.session_state.ai_insights)
        st.download_button(
            "📄 PDF herunterladen",
            data=pdf,
            file_name=f"toxic_radar_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "🧾 JSON exportieren",
            data=json.dumps(report, ensure_ascii=False, indent=2, default=str),
            file_name="toxic_radar_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with c3:
        summary = (
            f"Toxic Radar Pro — Ergebnis: {level}\n"
            f"Score: {score:.0%}\n"
            f"Datum: {report['timestamp']}\n"
            f"Kritische Warnzeichen: {'JA' if any(st.session_state.critical.values()) else 'NEIN'}\n"
        )
        st.download_button(
            "📋 Kurzfassung (txt)",
            data=summary,
            file_name="toxic_radar_kurzfassung.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # Save to history (local session)
    if st.button("💾 In Verlauf speichern"):
        st.session_state.history.append(report)
        st.success("Gespeichert (nur in dieser Session).")

    # Navigation
    nav_buttons("questions", "questions", next_label="Zurück zu den Fragen")


# =========================================================
# MAIN ROUTER
# =========================================================

def main() -> None:
    inject_css(st.session_state.theme)
    sidebar()

    hero()
    safety_box()

    step = st.session_state.step

    if step == "intro":
        step_intro()
    elif step == "context":
        step_context()
    elif step == "critical":
        step_critical()
    elif step == "questions":
        step_questions()
    elif step == "results":
        step_results()
    else:
        st.session_state.step = "intro"
        st.rerun()


if __name__ == "__main__":
    main()
