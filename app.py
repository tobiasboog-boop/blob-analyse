"""
Blob Analyse - Zenith Security
Streamlit App voor AI-analyse van werkbon blobvelden
"""

import streamlit as st
import json
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Blob Analyse - Zenith Security",
    page_icon="🔍",
    layout="wide"
)

# Header
st.title("🔍 Blob Analyse - Zenith Security")
st.markdown("**Pilot:** AI-analyse van werkbon blobvelden")

st.divider()

# Sidebar
with st.sidebar:
    st.header("Over deze app")
    st.markdown("""
    Deze app analyseert ongestructureerde blobvelden
    uit Syntess werkbonnen voor Zenith Security.

    **Relevante blobvelden:**
    - Monteur notities
    - Storingsmeldingen
    - Casebeschrijvingen
    - Urenregistraties
    """)

    st.divider()
    st.markdown("**Klant:** Zenith Security (1229)")
    st.markdown("**Status:** Pilot / Prototype")

# Main content
tab1, tab2, tab3 = st.tabs(["📊 Overzicht", "🔎 Zoeken", "🤖 AI Analyse"])

with tab1:
    st.header("Dataset Overzicht")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Monteur Notities", "16.521", help="AT_MWBSESS/NOTITIE.txt")
    with col2:
        st.metric("Storingsmeldingen", "12.446", help="AT_UITVBEST/TEKST.txt")
    with col3:
        st.metric("Casebeschrijvingen", "561", help="AT_WERK/GC_INFORMATIE.txt")
    with col4:
        st.metric("Urenregistraties", "1.015", help="AT_MWBSESS/INGELEVERDE_URENREGELS.txt")

    st.divider()

    st.subheader("Blobveld Types")

    data = {
        "Blobveld": ["NOTITIE.txt", "TEKST.txt", "GC_INFORMATIE.txt", "INGELEVERDE_URENREGELS.txt"],
        "Bron": ["AT_MWBSESS", "AT_UITVBEST", "AT_WERK", "AT_MWBSESS"],
        "Type": ["RTF", "RTF", "RTF", "XML"],
        "Inhoud": [
            "Vrije notities van monteurs",
            "Storingsmeldingen en werkbeschrijvingen",
            "Casebeschrijvingen en werkbon-context",
            "Gestructureerde urenregistratie"
        ]
    }

    st.table(data)

with tab2:
    st.header("Zoeken in Blobvelden")

    st.info("🚧 **Coming soon:** Zoekfunctionaliteit wordt toegevoegd zodra de data is geladen.")

    search_query = st.text_input("Zoekterm", placeholder="Bijv. storing, alarm, preventie...")

    col1, col2 = st.columns(2)
    with col1:
        blobveld_filter = st.multiselect(
            "Filter op blobveld",
            ["Monteur Notities", "Storingsmeldingen", "Casebeschrijvingen", "Urenregistraties"],
            default=["Monteur Notities", "Storingsmeldingen"]
        )
    with col2:
        max_results = st.slider("Max resultaten", 10, 100, 25)

    if st.button("🔍 Zoeken", type="primary"):
        if search_query:
            st.warning(f"Zoeken naar '{search_query}' in {len(blobveld_filter)} blobveld(en)...")
            st.info("Data moet nog worden geladen. Zie instructies hieronder.")
        else:
            st.error("Voer een zoekterm in")

with tab3:
    st.header("AI Analyse")

    st.info("🚧 **Coming soon:** AI-analyse met OpenAI/Claude voor:")

    st.markdown("""
    - **Samenvatten** van lange notities
    - **Categoriseren** van storingstypes
    - **Extractie** van keywords en thema's
    - **Sentiment** analyse van klantcommunicatie
    """)

    st.divider()

    st.subheader("Voorbeeld: Notitie Analyse")

    example_text = st.text_area(
        "Plak een voorbeeld notitie:",
        value="Nog niet klaar geen patchingen gemaakt. Verdere info bij Tim bekend. Klant was niet aanwezig, nieuwe afspraak maken.",
        height=100
    )

    if st.button("🤖 Analyseer met AI", type="primary"):
        with st.spinner("Analyseren..."):
            # Placeholder voor AI analyse
            st.success("**AI Analyse Resultaat:**")
            st.markdown("""
            - **Status:** Werk niet afgerond
            - **Reden:** Klant afwezig
            - **Actie nodig:** Nieuwe afspraak inplannen
            - **Contactpersoon:** Tim (voor meer info)
            - **Keywords:** patchingen, afspraak, klant afwezig
            """)

# Footer
st.divider()
st.caption("Blob Analyse v0.1 | Zenith Security Pilot | © Notifica B.V.")
