# toxic_radar_pro.py
# Enhanced Streamlit Webapp: "Toxic Radar Pro" with AI Analysis & Advanced Features

import math
import textwrap
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import streamlit as st
import openai
from io import BytesIO
import base64
from fpdf import FPDF
import random

# -----------------------------
# CONFIGURATION & INITIALIZATION
# -----------------------------

APP_TITLE = "🧭 Toxic Radar Pro — AI-Powered Relationship Analysis"
st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'critical' not in st.session_state:
    st.session_state.critical = {}
if 'saved_reports' not in st.session_state:
    st.session_state.saved_reports = []
if 'ai_insights' not in st.session_state:
    st.session_state.ai_insights = None
if 'timeline_data' not in st.session_state:
    st.session_state.timeline_data = []

# -----------------------------
# DATA MODELS
# -----------------------------

@dataclass
class Item:
    key: str
    text: str
    weight: float
    domain: str
    tip: str
    ai_keywords: List[str]

@dataclass
class Report:
    id: str
    timestamp: datetime
    score: float
    level: str
    answers: Dict
    critical: Dict
    context: Dict

# -----------------------------
# ENHANCED ITEMS WITH AI KEYWORDS
# -----------------------------

DOMAINS_ORDER = [
    "Respekt & Kommunikation",
    "Grenzen & Konsens", 
    "Kontrolle & Eifersucht",
    "Manipulation & Schuld",
    "Isolation & Abwertung",
    "Volatilität & Angstklima",
    "Verantwortung & Veränderung",
]

ITEMS = [
    # Respekt & Kommunikation
    Item("respect_1", "Ich werde häufig abgewertet, verspottet oder nicht ernst genommen.", 1.3, 
         "Respekt & Kommunikation", "Abwertung ist kein „Streitstil“, sondern ein Muster, das Selbstwert frisst.",
         ["Abwertung", "Verspottung", "Respektlosigkeit"]),
    
    Item("respect_2", "Diskussionen enden oft so, dass ich mich entschuldige – selbst wenn ich es nicht fühle.", 1.1,
         "Respekt & Kommunikation", "Wenn du ständig schuld bist, ist das ein Warnsignal für Schieflage.",
         ["Schuldzuweisung", "Unfairer Streit", "Selbstrechtfertigung"]),
    
    Item("respect_3", "Meine Bedürfnisse/Wünsche werden regelmäßig klein geredet oder übergangen.", 1.2,
         "Respekt & Kommunikation", "Eine Beziehung ohne Platz für Bedürfnisse ist keine Partnerschaft, sondern Anpassung.",
         ["Bedürfnisignorierung", "Nicht gesehen werden", "Übergangen werden"]),
    
    Item("respect_4", "Konflikte werden nicht fair geführt (Unterbrechen, Schreien, Drohen, Verniedlichen).", 1.2,
         "Respekt & Kommunikation", "Fairness ist der Mindeststandard – nicht die Kür.",
         ["Unfaire Konflikte", "Eskalation", "Kommunikationsprobleme"]),

    # ... (rest of items with similar enhancements - adding ai_keywords)
]

# Adding ai_keywords to all items (truncated for brevity, but same pattern for all)

CRITICAL_FLAGS = [
    ("crit_physical", "Es gab körperliche Gewalt (Schubsen, Festhalten, Schlagen) oder du hast Angst davor.", 
     ["körperliche Gewalt", "Gewaltandrohung", "physische Sicherheit"]),
    
    ("crit_threats", "Es gab Drohungen (dir, Kindern, Haustieren, sich selbst) oder Erpressung.",
     ["Drohungen", "Erpressung", "psychische Gewalt"]),
    
    ("crit_stalking", "Kontroll-/Stalking-Verhalten: Standort/Handy checken, Nachstellen, Passwörter fordern.",
     ["Stalking", "Kontrolle", "Überwachung"]),
    
    ("crit_sexual", "Sexueller Druck/Zwang oder du hast Intimität aus Angst/Schuld zugelassen.",
     ["sexueller Druck", "Einwilligung", "Grenzverletzung"]),
    
    ("crit_weapons", "Es gab Waffen/gefährliche Gegenstände im Kontext von Streit/Bedrohung.",
     ["Waffen", "Gefahr", "eskalierte Gewalt"]),
]

# -----------------------------
# ENHANCED SCORING ENGINE
# -----------------------------

class ToxicRadarEngine:
    @staticmethod
    def compute_score(answers: Dict[str, int], critical: Dict[str, bool]) -> Tuple[float, Dict[str, float], Dict[str, float]]:
        """Return total score, domain breakdown, and pattern intensity scores."""
        total_w = sum(i.weight for i in ITEMS)
        total = 0.0
        
        domain_w = {d: 0.0 for d in DOMAINS_ORDER}
        domain_s = {d: 0.0 for d in DOMAINS_ORDER}
        pattern_scores = {}
        
        for item in ITEMS:
            v = answers.get(item.key, 0)
            nv = v / 4.0
            total += nv * item.weight
            domain_w[item.domain] += item.weight
            domain_s[item.domain] += nv * item.weight
            
            # Calculate pattern intensity
            if v >= 3:  # Often or Very often
                pattern_scores[item.key] = {
                    'intensity': v,
                    'weight': item.weight,
                    'domain': item.domain
                }
        
        base = total / total_w if total_w > 0 else 0.0
        
        # Enhanced critical flag handling
        crit_count = sum(1 for k, _, _ in CRITICAL_FLAGS if critical.get(k, False))
        if crit_count >= 2:
            boost = 0.35  # Major boost for multiple critical flags
        elif crit_count == 1:
            boost = 0.15
        else:
            boost = 0.0
            
        final = min(base + boost, 1.0)
        
        breakdown = {d: domain_s[d]/domain_w[d] if domain_w[d] > 0 else 0.0 
                    for d in DOMAINS_ORDER}
        
        return final, breakdown, pattern_scores
    
    @staticmethod
    def classify(score: float, critical: Dict[str, bool]) -> str:
        crit_count = sum(1 for k, _, _ in CRITICAL_FLAGS if critical.get(k, False))
        
        if crit_count >= 3:
            return "SCHWARZ"
        elif crit_count >= 2:
            return "DUNKELROT"
        elif crit_count == 1:
            if score > 0.5:
                return "ROT"
            else:
                return "ORANGE"
        else:
            if score < 0.15:
                return "GRÜN"
            elif score < 0.35:
                return "HELLGRÜN"
            elif score < 0.55:
                return "GELB"
            elif score < 0.75:
                return "ORANGE"
            elif score < 0.9:
                return "ROT"
            else:
                return "DUNKELROT"
    
    @staticmethod
    def get_severity_color(level: str) -> str:
        colors = {
            "GRÜN": "#00C853",
            "HELLGRÜN": "#64DD17", 
            "GELB": "#FFD600",
            "ORANGE": "#FF9100",
            "ROT": "#FF3D00",
            "DUNKELROT": "#D50000",
            "SCHWARZ": "#000000"
        }
        return colors.get(level, "#666666")
    
    @staticmethod
    def generate_pattern_analysis(pattern_scores: Dict) -> str:
        if not pattern_scores:
            return "Keine starken Muster erkannt."
        
        patterns_by_domain = {}
        for key, data in pattern_scores.items():
            domain = data['domain']
            if domain not in patterns_by_domain:
                patterns_by_domain[domain] = []
            item = next(i for i in ITEMS if i.key == key)
            patterns_by_domain[domain].append({
                'text': item.text,
                'intensity': data['intensity'],
                'weight': data['weight']
            })
        
        analysis = "## 🔍 Erkannte Muster:\n\n"
        for domain, patterns in patterns_by_domain.items():
            if patterns:
                analysis += f"**{domain}:**\n"
                for pattern in patterns[:3]:  # Top 3 per domain
                    intensity_str = "💀" * pattern['intensity']
                    analysis += f"• {pattern['text']} {intensity_str}\n"
                analysis += "\n"
        
        return analysis

# -----------------------------
# AI INTEGRATION
# -----------------------------

class AIAnalyzer:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def analyze_relationship(self, answers: Dict, critical: Dict, score: float, 
                           breakdown: Dict, context: Dict) -> Optional[Dict]:
        """Generate AI-powered insights about the relationship patterns."""
        
        try:
            # Prepare data for AI
            pattern_summary = []
            for item in ITEMS:
                if answers.get(item.key, 0) >= 2:  # Sometimes or more
                    pattern_summary.append(f"{item.text} (Intensität: {answers[item.key]}/4)")
            
            critical_summary = [desc for key, desc, _ in CRITICAL_FLAGS if critical.get(key, False)]
            
            prompt = f"""
            Analysiere diese Beziehungsdynamik als erfahrener Therapeut:
            
            KONTEXT: {context}
            GESAMTSCORE: {score:.1%}
            
            ERKANNTE MUSTER:
            {chr(10).join(pattern_summary[:10])}
            
            KRITISCHE FAKTOREN:
            {chr(10).join(critical_summary) if critical_summary else 'Keine'}
            
            BEREICHSANALYSE:
            {chr(10).join([f'{d}: {v:.1%}' for d, v in breakdown.items()])}
            
            Bitte analysiere:
            1. Welche toxischen Dynamiken sind am stärksten ausgeprägt?
            2. Was sind die psychologischen Auswirkungen auf die betroffene Person?
            3. Welche spezifischen Interventionsstrategien würdest du empfehlen?
            4. Wie schätzt du das Risiko für weitere Eskalation ein?
            
            Antworte auf Deutsch in einem mitfühlenden, aber klaren Ton.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Du bist ein einfühlsamer, aber direkter Beziehungstherapeut mit Expertise in toxischen Dynamiken."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Generate visual metaphors
            metaphors = self._generate_metaphors(score, critical)
            
            return {
                "analysis": response.choices[0].message.content,
                "metaphors": metaphors,
                "risk_level": self._assess_risk(score, critical),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            st.error(f"AI-Analyse fehlgeschlagen: {str(e)}")
            return None
    
    def _generate_metaphors(self, score: float, critical: Dict) -> List[str]:
        """Generate powerful visual metaphors for the relationship state."""
        metaphors = []
        
        if score > 0.8:
            metaphors.append("🌪️ **Emotionaler Tornado:** Chaotische Dynamik, die dich auszehrt")
            metaphors.append("🎭 **Theater der Angst:** Ständige Inszenierung von Dramen")
        elif score > 0.5:
            metaphors.append("⚖️ **Schieflage:** Immer wieder dasselbe Ungleichgewicht")
            metaphors.append("🎢 **Achterbahn:** Hochs und Tiefs ohne klare Richtung")
        else:
            metaphors.append("🧭 **Kompass justieren:** Orientierung für gesündere Wege")
        
        if any(critical.values()):
            metaphors.append("🚨 **Rotes Alarmsystem:** Kritische Grenzen wurden überschritten")
            
        return metaphors
    
    def _assess_risk(self, score: float, critical: Dict) -> str:
        crit_count = sum(1 for k, _, _ in CRITICAL_FLAGS if critical.get(k, False))
        
        if crit_count >= 2 or score > 0.8:
            return "Hoch – Sofortige Intervention empfohlen"
        elif crit_count == 1 or score > 0.6:
            return "Mittel-Hoch – Professionelle Unterstützung ratsam"
        elif score > 0.4:
            return "Mittel – Klare Veränderungen nötig"
        else:
            return "Niedrig-Mittel – Wachsame Beobachtung"

# -----------------------------
# VISUALIZATION ENGINE
# -----------------------------

class VisualizationEngine:
    @staticmethod
    def create_radar_chart(breakdown: Dict[str, float]) -> go.Figure:
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=list(breakdown.values()),
            theta=list(breakdown.keys()),
            fill='toself',
            fillcolor='rgba(255, 61, 0, 0.3)',
            line_color='rgba(255, 61, 0, 0.8)',
            name='Aktuelle Ausprägung'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickformat=',.0%'
                )
            ),
            showlegend=False,
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
    
    @staticmethod
    def create_timeline_chart(timeline_data: List) -> go.Figure:
        if len(timeline_data) < 2:
            return None
            
        dates = [d['date'] for d in timeline_data]
        scores = [d['score'] for d in timeline_data]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=scores,
            mode='lines+markers',
            line=dict(color='#FF3D00', width=3),
            marker=dict(size=10, color='#FF3D00'),
            name='Beziehungsbelastung'
        ))
        
        # Add danger zones
        fig.add_hrect(y0=0.75, y1=1.0, 
                     fillcolor="rgba(255, 0, 0, 0.1)", 
                     line_width=0, annotation_text="Kritische Zone")
        fig.add_hrect(y0=0.5, y1=0.75, 
                     fillcolor="rgba(255, 165, 0, 0.1)", 
                     line_width=0, annotation_text="Warnzone")
        
        fig.update_layout(
            title="Entwicklung der Beziehungsbelastung",
            xaxis_title="Datum",
            yaxis_title="Belastungsscore",
            yaxis_tickformat=',.0%',
            height=300,
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig

# -----------------------------
# REPORT GENERATOR
# -----------------------------

class ReportGenerator:
    @staticmethod
    def generate_pdf_report(report: Report, ai_insights: Optional[Dict] = None) -> BytesIO:
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 24)
        pdf.cell(0, 20, 'Toxic Radar Pro - Analysebericht', ln=True, align='C')
        
        # Date and ID
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, f'Erstellt am: {report.timestamp.strftime("%d.%m.%Y %H:%M")}', ln=True)
        pdf.cell(0, 10, f'Report-ID: {report.id}', ln=True)
        
        # Results
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 15, 'Ergebnisübersicht', ln=True)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Ampelstufe: {report.level}', ln=True)
        pdf.cell(0, 10, f'Gesamtscore: {report.score:.1%}', ln=True)
        
        # AI Insights if available
        if ai_insights:
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 15, 'KI-Analyse', ln=True)
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 8, ai_insights.get('analysis', ''))
            
            if ai_insights.get('metaphors'):
                pdf.set_font('Arial', 'I', 11)
                pdf.cell(0, 10, 'Bildliche Darstellung:', ln=True)
                for metaphor in ai_insights['metaphors'][:3]:
                    pdf.multi_cell(0, 8, f'• {metaphor}')
        
        # Recommendations
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 15, 'Empfohlene Maßnahmen', ln=True)
        pdf.set_font('Arial', '', 11)
        
        recommendations = ToxicRadarEngine.get_recommendations(report.level, report.critical)
        for i, rec in enumerate(recommendations, 1):
            pdf.multi_cell(0, 8, f'{i}. {rec}')
        
        # Save to bytes buffer
        buffer = BytesIO()
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        buffer.write(pdf_bytes)
        buffer.seek(0)
        
        return buffer

# -----------------------------
# STREAMLIT UI COMPONENTS
# -----------------------------

def show_hero_section():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 20px; color: white; margin-bottom: 2rem;">
            <h1 style="margin: 0;">{APP_TITLE}</h1>
            <p style="opacity: 0.9;">AI-gestützte Analyse toxischer Beziehungsmuster mit personalisierten Insights</p>
        </div>
        """, unsafe_allow_html=True)

def show_safety_warning():
    with st.expander("🚨 WICHTIG: Sicherheitshinweis", expanded=True):
        st.warning("""
        **Bei akuter Gefahr: Notruf 112**
        
        Dieses Tool ist keine Diagnose und ersetzt keine professionelle Hilfe. 
        Bei Gewalt, Bedrohungen oder akuter Gefährdung wende dich sofort an:
        - Hilfetelefon Gewalt gegen Frauen: 08000 116 016
        - Telefonseelsorge: 0800 111 0 111
        - Ärztlichen Bereitschaftsdienst: 116 117
        """)

def show_context_section():
    st.subheader("📋 Kontextinformationen")
    cols = st.columns(4)
    
    with cols[0]:
        rel_type = st.selectbox(
            "Beziehungsform",
            ["Romantische Partnerschaft", "Ehe", "Dating", "Ex-Partner", 
             "Familie", "Freundschaft", "Arbeitsverhältnis", "Sonstiges"]
        )
    
    with cols[1]:
        duration = st.selectbox(
            "Dauer",
            ["< 3 Monate", "3-12 Monate", "1-3 Jahre", "3-7 Jahre", "> 7 Jahre"]
        )
    
    with cols[2]:
        frequency = st.selectbox(
            "Kontakthäufigkeit",
            ["Täglich", "Mehrmals wöchentlich", "Wöchentlich", "Monatlich", "Unregelmäßig"]
        )
    
    with cols[3]:
        impact = st.select_slider(
            "Aktuelle Belastung",
            options=["Gering", "Mittel", "Hoch", "Sehr hoch"],
            value="Mittel"
        )
    
    return {
        "relationship_type": rel_type,
        "duration": duration,
        "contact_frequency": frequency,
        "current_impact": impact
    }

def show_critical_flags():
    st.subheader("⚠️ Kritische Warnzeichen")
    st.info("Diese Faktoren erhöhen das Risiko erheblich und erfordern besondere Aufmerksamkeit.")
    
    critical = {}
    cols = st.columns(2)
    
    for idx, (key, desc, _) in enumerate(CRITICAL_FLAGS):
        with cols[idx % 2]:
            critical[key] = st.checkbox(
                f"**{desc}**",
                value=st.session_state.critical.get(key, False),
                key=f"crit_{key}",
                help="Wenn dies zutrifft, hat Sicherheit höchste Priorität"
            )
    
    return critical

def show_questionnaire():
    st.subheader("🔍 Beziehungsmuster-Check")
    
    # Progress tracking
    total_items = len(ITEMS)
    answered = sum(1 for v in st.session_state.answers.values() if v > 0)
    progress = answered / total_items
    
    st.progress(progress, text=f"Fortschritt: {answered}/{total_items} Fragen beantwortet")
    
    # Domain-based questionnaire with tabs
    tabs = st.tabs(DOMAINS_ORDER)
    
    for idx, domain in enumerate(DOMAINS_ORDER):
        with tabs[idx]:
            domain_items = [i for i in ITEMS if i.domain == domain]
            
            for item in domain_items:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{item.text}**")
                    st.caption(item.tip)
                
                with col2:
                    # Visual scale input
                    value = st.slider(
                        "",
                        min_value=0,
                        max_value=4,
                        value=st.session_state.answers.get(item.key, 0),
                        key=item.key,
                        label_visibility="collapsed"
                    )
                    st.session_state.answers[item.key] = value
                    
                    # Visual indicator
                    if value >= 3:
                        st.markdown("🔴 **Häufig**")
                    elif value == 2:
                        st.markdown("🟡 **Manchmal**")
                    elif value == 1:
                        st.markdown("🟢 **Selten**")
                    else:
                        st.markdown("⚪ **Nie**")
            
            st.divider()

def show_results(answers, critical, context):
    engine = ToxicRadarEngine()
    score, breakdown, patterns = engine.compute_score(answers, critical)
    level = engine.classify(score, critical)
    color = engine.get_severity_color(level)
    
    # Main result display
    st.markdown(f"""
    <div style="padding: 2rem; background: {color}10; border: 2px solid {color}; 
                border-radius: 15px; margin: 2rem 0;">
        <div style="text-align: center;">
            <h1 style="color: {color}; margin: 0; font-size: 3rem;">{level}</h1>
            <p style="font-size: 1.5rem;">Gesamtbelastung: <strong>{score:.1%}</strong></p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(VisualizationEngine.create_radar_chart(breakdown), use_container_width=True)
    
    with col2:
        # Pattern intensity chart
        pattern_df = pd.DataFrame([
            {"Domain": d, "Intensity": sum(1 for p in patterns.values() 
                                          if p['domain'] == d)}
            for d in DOMAINS_ORDER
        ])
        
        fig = px.bar(pattern_df, x='Domain', y='Intensity', 
                     color='Intensity', color_continuous_scale='RdYlGn_r')
        fig.update_layout(title="Musterintensität pro Bereich", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Pattern analysis
    st.markdown(engine.generate_pattern_analysis(patterns))
    
    return score, breakdown, level, patterns

def show_ai_insights(api_key, answers, critical, score, breakdown, context):
    if not api_key:
        st.info("🔑 Gib deinen OpenAI-API-Schlüssel ein, um KI-Insights zu erhalten.")
        return
    
    if st.button("🧠 KI-Analyse generieren", type="primary"):
        with st.spinner("AI analysiert die Muster..."):
            analyzer = AIAnalyzer(api_key)
            insights = analyzer.analyze_relationship(
                answers, critical, score, breakdown, context
            )
            
            if insights:
                st.session_state.ai_insights = insights
                
                st.success("✅ KI-Analyse abgeschlossen!")
                
                # Display insights
                st.markdown("## 🤖 KI-Insights")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(insights['analysis'])
                
                with col2:
                    st.markdown("### 📊 Risikobewertung")
                    st.metric("Risikolevel", insights['risk_level'])
                    
                    st.markdown("### 🎯 Bildhafte Darstellung")
                    for metaphor in insights['metaphors']:
                        st.info(metaphor)

def show_recommendations(level, critical, patterns):
    st.markdown("## 🛡️ Personalisierte Handlungsempfehlungen")
    
    # Generate recommendations based on patterns
    recs = []
    
    # Safety first for critical flags
    if any(critical.values()):
        recs.extend([
            "🚨 **Sicherheitsplan erstellen:** Notrufnummern, Fluchtweg, wichtige Dokumente",
            "📞 **Supportnetzwerk aktivieren:** 2-3 vertrauenswürdige Personen informieren",
            "📱 **Dokumentation starten:** Vorfälle mit Datum und Details notieren"
        ])
    
    # Pattern-specific recommendations
    if patterns:
        top_domain = max(set(p['domain'] for p in patterns.values()), 
                        key=lambda d: sum(1 for p in patterns.values() if p['domain'] == d))
        
        domain_recs = {
            "Grenzen & Konsens": [
                "🎯 **Eine klare Grenze definieren:** 'Wenn X passiert, dann werde ich Y tun'",
                "🗣️ **Nein-Übungen:** Im sicheren Umfeld Nein-Sagen trainieren",
                "⏱️ **24-Stunden-Regel:** Vor wichtigen Entscheidungen 24h warten"
            ],
            "Manipulation & Schuld": [
                "📝 **Realitäts-Check:** Fakten vs. Gefühle täglich notieren",
                "🔍 **Gaslighting erkennen:** 'Das war nicht meine Erfahrung' als Standardantwort",
                "🧘 **Selbstvalidierung:** Eigene Wahrnehmung täglich bestätigen"
            ],
            # ... more domain-specific recommendations
        }
        
        recs.extend(domain_recs.get(top_domain, []))
    
    # Display recommendations
    cols = st.columns(2)
    for idx, rec in enumerate(recs):
        with cols[idx % 2]:
            st.info(rec)

def show_export_options(report_data, ai_insights):
    st.markdown("## 📤 Ergebnisse exportieren")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Als PDF speichern", type="secondary"):
            generator = ReportGenerator()
            pdf_buffer = generator.generate_pdf_report(report_data, ai_insights)
            
            st.download_button(
                label="📥 PDF herunterladen",
                data=pdf_buffer,
                file_name=f"toxic_radar_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
    
    with col2:
        # JSON export
        export_data = {
            "report": report_data.__dict__,
            "ai_insights": ai_insights,
            "exported_at": datetime.now().isoformat()
        }
        
        st.download_button(
            label="📝 Als JSON exportieren",
            data=json.dumps(export_data, indent=2, default=str),
            file_name="toxic_radar_data.json",
            mime="application/json"
        )
    
    with col3:
        # Shareable summary
        summary = f"""
        🔍 Toxic Radar Analyse - {report_data.level}
        📊 Score: {report_data.score:.1%}
        📅 {datetime.now().strftime('%d.%m.%Y')}
        
        {'⚠️ Kritische Warnzeichen erkannt' if any(report_data.critical.values()) else '✅ Keine kritischen Warnzeichen'}
        
        #ToxicRadar #Beziehungsanalyse #Selbstreflexion
        """
        
        st.download_button(
            label="📱 Zusammenfassung kopieren",
            data=summary,
            file_name="zusammenfassung.txt",
            mime="text/plain"
        )

# -----------------------------
# SIDEBAR SETTINGS
# -----------------------------

def show_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/radar.png", width=80)
        st.title("Toxic Radar Pro")
        
        st.divider()
        
        # API Settings
        st.subheader("🔑 KI-Einstellungen")
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Für erweiterte KI-Analysen (optional)"
        )
        
        st.divider()
        
        # Quick Actions
        st.subheader("⚡ Schnellaktionen")
        
        if st.button("🔄 Test zurücksetzen", type="secondary"):
            st.session_state.answers = {}
            st.session_state.critical = {}
            st.session_state.ai_insights = None
            st.rerun()
        
        if st.button("💾 Aktuelles Ergebnis speichern"):
            if 'score' in locals() or 'score' in globals():
                report = Report(
                    id=f"TR{random.randint(10000, 99999)}",
                    timestamp=datetime.now(),
                    score=score,
                    level=level,
                    answers=st.session_state.answers.copy(),
                    critical=st.session_state.critical.copy(),
                    context=context
                )
                st.session_state.saved_reports.append(report)
                st.success("Ergebnis gespeichert!")
        
        st.divider()
        
        # Resources
        st.subheader("🆘 Hilfsressourcen")
        st.markdown("""
        - [Hilfetelefon Gewalt](https://www.hilfetelefon.de)
        - [Telefonseelsorge](https://www.telefonseelsorge.de)
        - [Nummer gegen Kummer](https://www.nummergegenkummer.de)
        - [Weißer Ring](https://www.weisser-ring.de)
        """)
    
    return api_key

# -----------------------------
# MAIN APP
# -----------------------------

def main():
    # Hero Section
    show_hero_section()
    
    # Safety Warning
    show_safety_warning()
    
    # Sidebar
    api_key = show_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Fragebogen", "📊 Ergebnisse", "📈 Verlauf", "⚙️ Einstellungen"])
    
    with tab1:
        # Context
        context = show_context_section()
        
        # Critical Flags
        st.session_state.critical = show_critical_flags()
        
        # Questionnaire
        show_questionnaire()
        
        # Calculate button
        if st.button("🚀 Analyse starten", type="primary", use_container_width=True):
            st.session_state.show_results = True
            st.rerun()
    
    # Results Tab
    if st.session_state.get('show_results', False):
        with tab2:
            if not st.session_state.answers:
                st.warning("Bitte fülle zuerst den Fragebogen aus.")
            else:
                # Calculate and show results
                score, breakdown, level, patterns = show_results(
                    st.session_state.answers,
                    st.session_state.critical,
                    context
                )
                
                # Create report object
                report = Report(
                    id=f"TR{random.randint(10000, 99999)}",
                    timestamp=datetime.now(),
                    score=score,
                    level=level,
                    answers=st.session_state.answers.copy(),
                    critical=st.session_state.critical.copy(),
                    context=context
                )
                
                # AI Insights
                show_ai_insights(
                    api_key,
                    st.session_state.answers,
                    st.session_state.critical,
                    score,
                    breakdown,
                    context
                )
                
                # Recommendations
                show_recommendations(level, st.session_state.critical, patterns)
                
                # Export options
                show_export_options(report, st.session_state.ai_insights)
    
    # History Tab
    with tab3:
        if st.session_state.saved_reports:
            st.subheader("📅 Verlauf gespeicherter Analysen")
            
            for report in reversed(st.session_state.saved_reports[-5:]):  # Last 5
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{report.timestamp.strftime('%d.%m.%Y %H:%M')}**")
                    st.caption(f"Kontext: {report.context.get('relationship_type', 'N/A')}")
                
                with col2:
                    color = ToxicRadarEngine.get_severity_color(report.level)
                    st.markdown(f"<span style='color:{color};font-weight:bold'>{report.level}</span>", 
                               unsafe_allow_html=True)
                
                with col3:
                    st.write(f"{report.score:.1%}")
                
                st.divider()
        else:
            st.info("Noch keine Analysen gespeichert. Führe eine Analyse durch und speichere sie.")
    
    # Settings Tab
    with tab4:
        st.subheader("⚙️ App-Einstellungen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("Anonyme Nutzungsstatistiken", value=True)
            st.checkbox("Erinnerungen für Follow-ups", value=False)
            st.checkbox("Detaillierte Tooltips anzeigen", value=True)
        
        with col2:
            theme = st.selectbox("Design-Theme", ["Hell", "Dunkel", "Auto"])
            language = st.selectbox("Sprache", ["Deutsch", "English"])
            font_size = st.select_slider("Schriftgröße", ["Klein", "Mittel", "Groß"])
        
        st.divider()
        
        # Data management
        st.subheader("📦 Datenverwaltung")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Alle Daten löschen", type="secondary"):
                st.session_state.clear()
                st.success("Alle Daten wurden gelöscht!")
        
        with col2:
            if st.button("💾 Backup erstellen"):
                backup_data = {
                    "reports": [r.__dict__ for r in st.session_state.saved_reports],
                    "last_updated": datetime.now().isoformat()
                }
                
                st.download_button(
                    label="📥 Backup herunterladen",
                    data=json.dumps(backup_data, indent=2, default=str),
                    file_name=f"toxic_radar_backup_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()