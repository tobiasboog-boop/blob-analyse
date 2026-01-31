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


@st.cache_data
def load_data():
    """Laad de sample data uit JSON."""
    data_path = Path(__file__).parent / "data" / "sample_data.json"

    if not data_path.exists():
        return None

    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def search_in_data(data, query, selected_types):
    """Zoek in de blobvelden data."""
    results = []
    query_lower = query.lower()

    type_mapping = {
        "Monteur Notities": "monteur_notities",
        "Storingsmeldingen": "storing_meldingen",
        "Casebeschrijvingen": "werk_context",
        "Urenregistraties": "uren_registraties"
    }

    for display_name, data_key in type_mapping.items():
        if display_name in selected_types:
            for item in data.get(data_key, []):
                if query_lower in item.get("tekst", "").lower():
                    results.append({
                        "id": item.get("id"),
                        "type": display_name,
                        "tekst": item.get("tekst"),
                        "totaal_uren": item.get("totaal_uren")
                    })

    return results


# Load data
data = load_data()

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

    if data:
        st.divider()
        st.markdown("**Data geladen:**")
        totals = data.get("metadata", {}).get("totals", {})
        st.caption(f"Notities: {totals.get('monteur_notities', 0)}")
        st.caption(f"Storingen: {totals.get('storing_meldingen', 0)}")
        st.caption(f"Cases: {totals.get('werk_context', 0)}")
        st.caption(f"Uren: {totals.get('uren_registraties', 0)}")

# Main content
tab1, tab2, tab3 = st.tabs(["📊 Overzicht", "🔎 Zoeken", "🤖 AI Analyse"])

with tab1:
    st.header("Dataset Overzicht")

    if data:
        totals = data.get("metadata", {}).get("totals", {})

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Monteur Notities", f"{totals.get('monteur_notities', 0)}", help="AT_MWBSESS/NOTITIE.txt")
        with col2:
            st.metric("Storingsmeldingen", f"{totals.get('storing_meldingen', 0)}", help="AT_UITVBEST/TEKST.txt")
        with col3:
            st.metric("Casebeschrijvingen", f"{totals.get('werk_context', 0)}", help="AT_WERK/GC_INFORMATIE.txt")
        with col4:
            st.metric("Urenregistraties", f"{totals.get('uren_registraties', 0)}", help="AT_MWBSESS/INGELEVERDE_URENREGELS.txt")

        st.divider()

        st.subheader("Blobveld Types")

        table_data = {
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
        st.table(table_data)

        st.divider()

        # Voorbeelden tonen
        st.subheader("Voorbeelden uit de data")

        example_type = st.selectbox(
            "Selecteer type",
            ["Monteur Notities", "Storingsmeldingen", "Casebeschrijvingen", "Urenregistraties"]
        )

        type_mapping = {
            "Monteur Notities": "monteur_notities",
            "Storingsmeldingen": "storing_meldingen",
            "Casebeschrijvingen": "werk_context",
            "Urenregistraties": "uren_registraties"
        }

        examples = data.get(type_mapping[example_type], [])[:5]

        for i, example in enumerate(examples, 1):
            with st.expander(f"Voorbeeld {i} - ID: {example.get('id', 'N/A')}"):
                st.text(example.get("tekst", "Geen tekst beschikbaar"))
                if example.get("totaal_uren"):
                    st.caption(f"Totaal uren: {example['totaal_uren']}")
    else:
        st.warning("⚠️ Geen data geladen. Zorg dat `data/sample_data.json` aanwezig is.")

with tab2:
    st.header("Zoeken in Blobvelden")

    if data:
        search_query = st.text_input("🔍 Zoekterm", placeholder="Bijv. storing, alarm, preventie, sleutel...")

        col1, col2 = st.columns(2)
        with col1:
            blobveld_filter = st.multiselect(
                "Filter op blobveld",
                ["Monteur Notities", "Storingsmeldingen", "Casebeschrijvingen", "Urenregistraties"],
                default=["Monteur Notities", "Storingsmeldingen", "Casebeschrijvingen"]
            )
        with col2:
            max_results = st.slider("Max resultaten", 10, 100, 25)

        if search_query:
            results = search_in_data(data, search_query, blobveld_filter)

            st.divider()

            if results:
                st.success(f"**{len(results)} resultaten** gevonden voor '{search_query}'")

                # Toon resultaten per type
                for i, result in enumerate(results[:max_results], 1):
                    with st.expander(f"{result['type']} - ID: {result['id']}"):
                        # Highlight de zoekterm
                        tekst = result['tekst']
                        st.text(tekst)

                        if result.get('totaal_uren'):
                            st.caption(f"Totaal uren: {result['totaal_uren']}")

                if len(results) > max_results:
                    st.info(f"Toont {max_results} van {len(results)} resultaten. Verhoog 'Max resultaten' om meer te zien.")
            else:
                st.warning(f"Geen resultaten gevonden voor '{search_query}'")
        else:
            st.info("Voer een zoekterm in om te zoeken in de blobvelden.")

            # Suggesties
            st.markdown("**Suggesties:**")
            suggestions = ["storing", "alarm", "sleutel", "camera", "defect", "monteur", "klant"]
            cols = st.columns(len(suggestions))
            for i, suggestion in enumerate(suggestions):
                with cols[i]:
                    if st.button(suggestion, key=f"sug_{suggestion}"):
                        st.session_state.search_query = suggestion
                        st.rerun()
    else:
        st.warning("⚠️ Geen data geladen.")

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

    # Laat gebruiker een voorbeeld kiezen of eigen tekst invoeren
    if data:
        example_texts = [item["tekst"][:500] for item in data.get("monteur_notities", [])[:5]]

        input_method = st.radio("Invoer methode", ["Selecteer voorbeeld", "Eigen tekst"])

        if input_method == "Selecteer voorbeeld" and example_texts:
            selected_example = st.selectbox("Kies een voorbeeld notitie", example_texts)
            example_text = selected_example
        else:
            example_text = st.text_area(
                "Plak een notitie:",
                value="Nog niet klaar geen patchingen gemaakt. Verdere info bij Tim bekend. Klant was niet aanwezig, nieuwe afspraak maken.",
                height=100
            )
    else:
        example_text = st.text_area(
            "Plak een notitie:",
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
            st.caption("*Dit is een placeholder. Echte AI-analyse wordt later toegevoegd.*")

# Footer
st.divider()
st.caption("Blob Analyse v0.2 | Zenith Security Pilot | © Notifica B.V.")
