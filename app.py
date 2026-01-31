"""
Blob Analyse - Zenith Security
Streamlit App voor AI-analyse van werkbon blobvelden

4 Business Case Tabs:
1. Meerwerk Scanner - Detecteer gemiste facturatie
2. Contract Checker - Classificeer contract vs. meerwerk
3. Terugkeer Analyse - Vind terugkerende storingen
4. Compleetheid Check - Controleer notitie kwaliteit
"""

import streamlit as st
import json
import re
from pathlib import Path
from collections import defaultdict

# Page config
st.set_page_config(
    page_title="Blob Analyse - Zenith Security",
    page_icon="🔍",
    layout="wide"
)


@st.cache_data
def load_blob_data():
    """Laad de blobvelden sample data."""
    data_path = Path(__file__).parent / "data" / "sample_data.json"
    if not data_path.exists():
        return None
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@st.cache_data
def load_werkbonnen_data():
    """Laad de werkbonnen data uit DWH extract."""
    data_path = Path(__file__).parent / "data" / "werkbonnen_zenith.json"
    if not data_path.exists():
        return None
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# =============================================================================
# USE CASE 1: MEERWERK SCANNER
# =============================================================================

MEERWERK_PATTERNS = {
    "vervangen": {
        "patterns": [r"vervangen", r"vervanging", r"nieuwe?\s+\w+\s+geplaatst"],
        "indicatie": "Component vervanging",
        "gem_waarde": 150
    },
    "accu": {
        "patterns": [r"accu\s*(vervangen|gewisseld|nieuw)", r"batterij\s*(vervangen|nieuw)"],
        "indicatie": "Accu vervanging",
        "gem_waarde": 85
    },
    "pir": {
        "patterns": [r"pir\s*(vervangen|defect|nieuw)", r"detector\s*(vervangen|nieuw)"],
        "indicatie": "PIR/Detector vervanging",
        "gem_waarde": 120
    },
    "camera": {
        "patterns": [r"camera\s*(vervangen|nieuw|geplaatst)", r"recorder\s*(vervangen|nieuw)"],
        "indicatie": "Camera/Recorder vervanging",
        "gem_waarde": 350
    },
    "slot": {
        "patterns": [r"slot\s*(vervangen|nieuw)", r"sleutel\s*(bijgemaakt|nieuw|gemaakt)"],
        "indicatie": "Slot/Sleutel werk",
        "gem_waarde": 75
    },
    "sirene": {
        "patterns": [r"sirene\s*(vervangen|defect|nieuw)"],
        "indicatie": "Sirene vervanging",
        "gem_waarde": 95
    },
    "kabel": {
        "patterns": [r"kabel\s*(getrokken|nieuw|vervangen)", r"bekabeling\s*(nieuw|aangepast)"],
        "indicatie": "Bekabeling werk",
        "gem_waarde": 200
    },
    "software": {
        "patterns": [r"software\s*(update|upgrade)", r"firmware\s*(update|upgrade)"],
        "indicatie": "Software/Firmware update",
        "gem_waarde": 50
    },
    "extra_werk": {
        "patterns": [r"extra\s+\w+", r"bijkomend", r"aanvullend", r"tevens\s+\w+\s+(geplaatst|vervangen)"],
        "indicatie": "Extra werkzaamheden",
        "gem_waarde": 100
    }
}


def scan_for_meerwerk(tekst):
    """Scan een notitie op meerwerk indicatoren."""
    tekst_lower = tekst.lower()
    gevonden = []

    for categorie, config in MEERWERK_PATTERNS.items():
        for pattern in config["patterns"]:
            if re.search(pattern, tekst_lower):
                gevonden.append({
                    "categorie": categorie,
                    "indicatie": config["indicatie"],
                    "geschatte_waarde": config["gem_waarde"]
                })
                break  # Eén match per categorie is genoeg

    return gevonden


def clean_tekst(tekst):
    """Verwijder RTF rommel uit tekst."""
    # Verwijder "Arial;Symbol;" en varianten
    tekst = re.sub(r'^[A-Za-z;]+;\s*\n*', '', tekst)
    # Verwijder leading 'd' die vaak overblijft
    tekst = re.sub(r'^\s*d([A-Z])', r'\1', tekst)
    return tekst.strip()


def run_meerwerk_analyse(blob_data):
    """Voer meerwerk analyse uit op alle notities."""
    resultaten = []

    for notitie in blob_data.get("monteur_notities", []):
        tekst = notitie.get("tekst", "")
        tekst_clean = clean_tekst(tekst)
        meerwerk = scan_for_meerwerk(tekst_clean)

        if meerwerk:
            totaal_waarde = sum(m["geschatte_waarde"] for m in meerwerk)
            resultaten.append({
                "id": notitie.get("id"),
                "tekst": tekst_clean[:300],
                "meerwerk_items": meerwerk,
                "aantal_items": len(meerwerk),
                "geschatte_waarde": totaal_waarde
            })

    return sorted(resultaten, key=lambda x: x["geschatte_waarde"], reverse=True)


# =============================================================================
# USE CASE 2: CONTRACT CHECKER
# =============================================================================

CONTRACT_KEYWORDS = [
    "onderhoud", "preventief", "controle", "inspectie", "jaarlijks",
    "periodiek", "checklist", "servicebeurt", "onderhoudsbeurt"
]

MEERWERK_KEYWORDS = [
    "vervangen", "defect", "kapot", "storing", "reparatie", "nieuw",
    "extra", "bijkomend", "uitbreiding", "aanpassing", "wijziging"
]


def classify_werk(tekst):
    """Classificeer werk als contract of meerwerk."""
    tekst_lower = tekst.lower()

    # Vind welke keywords matchen
    contract_matches = [kw for kw in CONTRACT_KEYWORDS if kw in tekst_lower]
    meerwerk_matches = [kw for kw in MEERWERK_KEYWORDS if kw in tekst_lower]

    contract_score = len(contract_matches)
    meerwerk_score = len(meerwerk_matches)

    # Bepaal classificatie
    if meerwerk_score > contract_score:
        classificatie = "MEERWERK"
        confidence = min(95, 50 + (meerwerk_score - contract_score) * 15)
    elif contract_score > meerwerk_score:
        classificatie = "CONTRACT"
        confidence = min(95, 50 + (contract_score - meerwerk_score) * 15)
    else:
        classificatie = "ONZEKER"
        confidence = 50

    return {
        "classificatie": classificatie,
        "confidence": confidence,
        "contract_indicators": contract_score,
        "meerwerk_indicators": meerwerk_score,
        "contract_matches": contract_matches,
        "meerwerk_matches": meerwerk_matches
    }


def run_contract_analyse(blob_data):
    """Voer contract classificatie uit op alle notities."""
    resultaten = {"CONTRACT": [], "MEERWERK": [], "ONZEKER": []}

    for notitie in blob_data.get("monteur_notities", []):
        tekst = notitie.get("tekst", "")
        tekst_clean = clean_tekst(tekst)
        classificatie = classify_werk(tekst_clean)

        resultaten[classificatie["classificatie"]].append({
            "id": notitie.get("id"),
            "tekst": tekst_clean[:250],
            "classificatie": classificatie["classificatie"],
            "confidence": classificatie["confidence"],
            "contract_matches": classificatie["contract_matches"],
            "meerwerk_matches": classificatie["meerwerk_matches"]
        })

    return resultaten


# =============================================================================
# USE CASE 3: TERUGKEER ANALYSE
# =============================================================================

STORING_PATTERNS = [
    r"storing", r"defect", r"kapot", r"niet werkend", r"geen signaal",
    r"probleem", r"fout", r"error", r"alarm", r"vals\s*alarm"
]


def extract_storingen(blob_data):
    """Extraheer storingen uit de data."""
    storingen = []

    # Analyseer storing_meldingen
    for melding in blob_data.get("storing_meldingen", []):
        tekst = melding.get("tekst", "").lower()

        # Tel storing indicatoren
        storing_score = sum(1 for p in STORING_PATTERNS if re.search(p, tekst))

        if storing_score > 0:
            storingen.append({
                "id": melding.get("id"),
                "tekst": melding.get("tekst", "")[:200],
                "type": "storing_melding",
                "score": storing_score
            })

    # Analyseer ook monteur notities
    for notitie in blob_data.get("monteur_notities", []):
        tekst = notitie.get("tekst", "").lower()
        storing_score = sum(1 for p in STORING_PATTERNS if re.search(p, tekst))

        if storing_score >= 2:  # Hogere drempel voor notities
            storingen.append({
                "id": notitie.get("id"),
                "tekst": notitie.get("tekst", "")[:200],
                "type": "monteur_notitie",
                "score": storing_score
            })

    return storingen


def analyse_terugkeer_patronen(blob_data, werkbonnen_data):
    """Analyseer terugkerende storingen en probleemlocaties."""
    # Verzamel alle storingen
    storingen = extract_storingen(blob_data)

    # Groepeer op keywords/type storing
    storing_types = defaultdict(int)
    for storing in storingen:
        tekst = storing["tekst"].lower()
        if "pir" in tekst or "detector" in tekst:
            storing_types["PIR/Detector problemen"] += 1
        elif "camera" in tekst or "recorder" in tekst:
            storing_types["Camera/Video problemen"] += 1
        elif "communicatie" in tekst or "signaal" in tekst:
            storing_types["Communicatie problemen"] += 1
        elif "accu" in tekst or "batterij" in tekst or "stroom" in tekst:
            storing_types["Voeding/Accu problemen"] += 1
        elif "slot" in tekst or "deur" in tekst:
            storing_types["Toegang/Slot problemen"] += 1
        else:
            storing_types["Overige storingen"] += 1

    return {
        "totaal_storingen": len(storingen),
        "storing_types": dict(storing_types),
        "details": sorted(storingen, key=lambda x: x["score"], reverse=True)[:50]
    }


# =============================================================================
# USE CASE 4: COMPLEETHEID CHECK
# =============================================================================

VEREISTE_ELEMENTEN = {
    "actie": {
        "patterns": [r"vervangen", r"geplaatst", r"aangepast", r"gerepareerd", r"getest", r"uitgevoerd", r"gecontroleerd"],
        "beschrijving": "Uitgevoerde actie",
        "gewicht": 3
    },
    "resultaat": {
        "patterns": [r"werkt", r"functioneert", r"opgelost", r"verholpen", r"in orde", r"naar behoren"],
        "beschrijving": "Resultaat/Status",
        "gewicht": 2
    },
    "component": {
        "patterns": [r"pir", r"camera", r"slot", r"sirene", r"centrale", r"detector", r"accu", r"kabel"],
        "beschrijving": "Component benoemd",
        "gewicht": 2
    },
    "locatie": {
        "patterns": [r"zone\s*\d+", r"verdieping", r"hal", r"kantoor", r"magazijn", r"entree", r"gang"],
        "beschrijving": "Locatie specificatie",
        "gewicht": 1
    }
}


def check_compleetheid(tekst):
    """Check de compleetheid van een notitie."""
    tekst_lower = tekst.lower()
    gevonden = {}
    totaal_score = 0
    max_score = sum(e["gewicht"] for e in VEREISTE_ELEMENTEN.values())

    for element, config in VEREISTE_ELEMENTEN.items():
        aanwezig = any(re.search(p, tekst_lower) for p in config["patterns"])
        gevonden[element] = aanwezig
        if aanwezig:
            totaal_score += config["gewicht"]

    percentage = int((totaal_score / max_score) * 100)

    # Bepaal kwaliteitslabel
    if percentage >= 75:
        kwaliteit = "GOED"
    elif percentage >= 50:
        kwaliteit = "MATIG"
    else:
        kwaliteit = "ONVOLLEDIG"

    return {
        "elementen": gevonden,
        "score": totaal_score,
        "max_score": max_score,
        "percentage": percentage,
        "kwaliteit": kwaliteit
    }


def run_compleetheid_analyse(blob_data):
    """Voer compleetheid analyse uit op alle notities."""
    resultaten = {"GOED": [], "MATIG": [], "ONVOLLEDIG": []}
    scores = []

    for notitie in blob_data.get("monteur_notities", []):
        tekst = notitie.get("tekst", "")
        if len(tekst.strip()) < 10:  # Skip lege/minimale notities
            continue

        check = check_compleetheid(tekst)
        scores.append(check["percentage"])

        resultaten[check["kwaliteit"]].append({
            "id": notitie.get("id"),
            "tekst": tekst[:200],
            "score": check["percentage"],
            "elementen": check["elementen"]
        })

    gem_score = sum(scores) / len(scores) if scores else 0

    return {
        "verdeling": {k: len(v) for k, v in resultaten.items()},
        "gemiddelde_score": gem_score,
        "details": resultaten
    }


# =============================================================================
# STREAMLIT APP
# =============================================================================

# Load data
blob_data = load_blob_data()
werkbonnen_data = load_werkbonnen_data()

# Header
st.title("🔍 Blob Analyse - Zenith Security")
st.markdown("**Business Case Analyse** van werkbon blobvelden")

st.divider()

# Sidebar
with st.sidebar:
    # Notifica logo
    logo_path = Path(__file__).parent / "assets" / "notifica_logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
        st.divider()

    st.header("Over deze app")
    st.markdown("""
    Deze app analyseert ongestructureerde blobvelden
    uit Syntess werkbonnen voor Zenith Security.

    **4 Business Cases:**
    1. 💰 Meerwerk Scanner
    2. 📋 Contract Checker
    3. 🔄 Terugkeer Analyse
    4. ✅ Compleetheid Check
    """)

    st.divider()
    st.markdown("**Klant:** Zenith Security (1229)")
    st.markdown("**Status:** Pilot / Prototype")

    if blob_data:
        st.divider()
        st.markdown("**Dataset:**")
        totals = blob_data.get("metadata", {}).get("totals", {})
        st.caption(f"Notities: {totals.get('monteur_notities', 0)}")
        st.caption(f"Storingen: {totals.get('storing_meldingen', 0)}")
        st.caption(f"Cases: {totals.get('werk_context', 0)}")
        st.caption(f"Uren: {totals.get('uren_registraties', 0)}")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "💰 Meerwerk Scanner",
    "📋 Contract Checker",
    "🔄 Terugkeer Analyse",
    "✅ Compleetheid Check"
])

# =============================================================================
# TAB 1: MEERWERK SCANNER
# =============================================================================
with tab1:
    st.header("💰 Meerwerk Scanner")

    # ===================
    # SECTIE 1: HET DOEL
    # ===================
    st.subheader("🎯 Doel")
    st.markdown("""
    Monteurs schrijven notities bij werkbonnen. Soms staat daar extra werk in dat
    **wel uitgevoerd maar niet gefactureerd** wordt. Deze scanner vindt die gevallen.
    """)

    # ===================
    # SECTIE 2: HOE WERKT HET
    # ===================
    st.subheader("⚙️ Hoe werkt het?")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Stap 1: Scannen**")
        st.caption("We doorzoeken monteurnotities op woorden die wijzen op extra werk")
    with col2:
        st.markdown("**Stap 2: Herkennen**")
        st.caption("Woorden als 'vervangen', 'nieuw', 'extra' triggeren een melding")
    with col3:
        st.markdown("**Stap 3: Controleren**")
        st.caption("Jullie checken of dit werk daadwerkelijk gefactureerd is")

    # Toon de zoekwoorden
    with st.expander("📋 Welke woorden zoeken we?"):
        st.markdown("""
        | Categorie | Zoekwoorden | Geschatte waarde |
        |-----------|-------------|------------------|
        | Component vervanging | "vervangen", "vervanging", "nieuw geplaatst" | €150 |
        | Accu werk | "accu vervangen", "batterij nieuw" | €85 |
        | PIR/Detector | "pir vervangen", "detector nieuw" | €120 |
        | Camera/Recorder | "camera vervangen", "recorder nieuw" | €350 |
        | Slot/Sleutel | "slot vervangen", "sleutel bijgemaakt" | €75 |
        | Bekabeling | "kabel getrokken", "bekabeling nieuw" | €200 |
        """)

    st.divider()

    # ===================
    # SECTIE 3: DE RESULTATEN
    # ===================
    st.subheader("📊 Top 10 Meerwerk Kandidaten")

    if blob_data:
        # Voer analyse direct uit (geen knop nodig)
        resultaten = run_meerwerk_analyse(blob_data)

        if resultaten:
            # Compacte samenvatting
            st.caption(f"Gescand: {len(blob_data.get('monteur_notities', []))} notities → {len(resultaten)} met potentieel meerwerk gevonden")

            st.divider()

            # Toon top 10
            for i, result in enumerate(resultaten[:10], 1):
                indicaties = [m["indicatie"] for m in result["meerwerk_items"]]

                # Header met nummer en belangrijkste info
                st.markdown(f"### #{i} — {indicaties[0]}")

                col1, col2 = st.columns([2, 1])

                with col1:
                    # De notitie zelf
                    st.markdown("**Monteur notitie:**")
                    st.info(result["tekst"])

                with col2:
                    # Gevonden indicatoren
                    st.markdown("**Gedetecteerd:**")
                    for m in result["meerwerk_items"]:
                        st.write(f"• {m['indicatie']}")

                    st.markdown("**Vraag:**")
                    st.warning("Is dit gefactureerd?")

                # Werkbon koppeling (placeholder - moet nog geïmplementeerd)
                with st.expander("🔗 Bekijk gekoppelde werkbon"):
                    st.caption(f"Blobveld ID: {result['id']}")
                    st.info("⚠️ Werkbon koppeling wordt nog ontwikkeld. Zoek handmatig op dit ID in Syntess.")

                st.divider()

            # Meer laden optie
            if len(resultaten) > 10:
                if st.button(f"📥 Laad meer ({len(resultaten) - 10} overig)", key="load_more_meerwerk"):
                    st.session_state.show_all_meerwerk = True

                if st.session_state.get("show_all_meerwerk"):
                    for i, result in enumerate(resultaten[10:20], 11):
                        st.markdown(f"**#{i}** — {result['meerwerk_items'][0]['indicatie']}")
                        st.text(result["tekst"][:150] + "...")
        else:
            st.success("✅ Geen potentieel meerwerk gevonden in de huidige dataset")
    else:
        st.warning("Geen data geladen")

# =============================================================================
# TAB 2: CONTRACT CHECKER
# =============================================================================
with tab2:
    st.header("📋 Contract Checker")

    st.info("""
    **Doelstelling:** Automatisch classificeren of werkzaamheden binnen het servicecontract vallen of factureerbaar meerwerk zijn.

    **Potentiële benefit:** Tijdsbesparing op administratieve controle + correcte facturatie. Geschatte besparing: **2 uur/week** aan handmatige controle.
    """)

    if blob_data:
        if st.button("🔍 Start Contract Analyse", type="primary", key="contract_btn"):
            with st.spinner("Classificeren van werkzaamheden..."):
                resultaten = run_contract_analyse(blob_data)

            st.divider()

            # Samenvatting
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Contract werk", len(resultaten["CONTRACT"]),
                         help="Valt waarschijnlijk binnen servicecontract")
            with col2:
                st.metric("Meerwerk", len(resultaten["MEERWERK"]),
                         help="Waarschijnlijk factureerbaar")
            with col3:
                st.metric("Onzeker", len(resultaten["ONZEKER"]),
                         help="Handmatige controle nodig")

            # Visualisatie
            st.divider()
            totaal = sum(len(v) for v in resultaten.values())

            st.subheader("📊 Verdeling")
            col1, col2, col3 = st.columns(3)
            with col1:
                pct = (len(resultaten["CONTRACT"]) / totaal) * 100 if totaal else 0
                st.progress(pct / 100)
                st.caption(f"Contract: {pct:.0f}%")
            with col2:
                pct = (len(resultaten["MEERWERK"]) / totaal) * 100 if totaal else 0
                st.progress(pct / 100)
                st.caption(f"Meerwerk: {pct:.0f}%")
            with col3:
                pct = (len(resultaten["ONZEKER"]) / totaal) * 100 if totaal else 0
                st.progress(pct / 100)
                st.caption(f"Onzeker: {pct:.0f}%")

            # Toon meerwerk items (meest interessant)
            st.divider()
            st.subheader("🔴 Potentieel Meerwerk (te factureren)")

            st.markdown("""
            **Hoe werkt het?** De classificatie zoekt naar keywords:
            - 🔴 **Meerwerk keywords:** vervangen, defect, kapot, storing, reparatie, nieuw, extra, etc.
            - 🟢 **Contract keywords:** onderhoud, preventief, controle, inspectie, periodiek, etc.
            """)

            for i, item in enumerate(resultaten["MEERWERK"][:15], 1):
                meerwerk_kw = ", ".join(item.get("meerwerk_matches", [])) or "geen"
                with st.expander(f"#{i} | Gevonden: **{meerwerk_kw}** | ID: {item['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🔴 Meerwerk keywords gevonden:**")
                        if item.get("meerwerk_matches"):
                            for kw in item["meerwerk_matches"]:
                                st.write(f"  • `{kw}`")
                        else:
                            st.write("  (geen)")
                    with col2:
                        st.markdown("**🟢 Contract keywords gevonden:**")
                        if item.get("contract_matches"):
                            for kw in item["contract_matches"]:
                                st.write(f"  • `{kw}`")
                        else:
                            st.write("  (geen)")

                    st.markdown(f"**Conclusie:** {item['confidence']}% zekerheid dat dit **meerwerk** is")
                    st.divider()
                    st.markdown("**Originele notitie:**")
                    st.info(item["tekst"])
    else:
        st.warning("Geen data geladen")

# =============================================================================
# TAB 3: TERUGKEER ANALYSE
# =============================================================================
with tab3:
    st.header("🔄 Terugkeer Analyse")

    st.info("""
    **Doelstelling:** Identificeer terugkerende storingen en probleemlocaties om proactief preventief onderhoud aan te bieden.

    **Potentiële benefit:**
    - Extra omzet door preventieve onderhoudscontracten
    - Minder spoedbezoeken = lagere kosten
    - Hogere klanttevredenheid

    **Geschatte waarde:** 1 preventief contract per 10 geïdentificeerde probleemlocaties à €500/jaar = extra omzet.
    """)

    if blob_data:
        if st.button("🔍 Start Terugkeer Analyse", type="primary", key="terugkeer_btn"):
            with st.spinner("Analyseren van storingen..."):
                resultaten = analyse_terugkeer_patronen(blob_data, werkbonnen_data)

            st.divider()

            # Samenvatting
            st.metric("Totaal storingen gedetecteerd", resultaten["totaal_storingen"])

            # Storing types
            st.divider()
            st.subheader("📊 Storing Categorieën")

            storing_types = resultaten["storing_types"]
            if storing_types:
                # Sorteer op aantal
                sorted_types = sorted(storing_types.items(), key=lambda x: x[1], reverse=True)

                for storing_type, aantal in sorted_types:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(storing_type)
                        pct = (aantal / resultaten["totaal_storingen"]) * 100
                        st.progress(pct / 100)
                    with col2:
                        st.metric("Aantal", aantal)

            # Aanbevelingen
            st.divider()
            st.subheader("💡 Aanbevelingen")

            if storing_types:
                top_storing = max(storing_types.items(), key=lambda x: x[1])
                st.success(f"""
                **Meest voorkomende storing:** {top_storing[0]} ({top_storing[1]}x)

                **Aanbeveling:** Focus preventief onderhoud op deze categorie.
                Potentieel {top_storing[1] // 5} klanten voor uitgebreid servicecontract.
                """)

            # Detail voorbeelden
            st.divider()
            st.subheader("🔎 Storing Details")

            for i, storing in enumerate(resultaten["details"][:15], 1):
                with st.expander(f"#{i} | Score {storing['score']} | {storing['type']}"):
                    st.markdown(f"**ID:** {storing['id']}")
                    st.markdown(f"**Bron:** {storing['type']}")
                    st.divider()
                    st.text(storing["tekst"])
    else:
        st.warning("Geen data geladen")

# =============================================================================
# TAB 4: COMPLEETHEID CHECK
# =============================================================================
with tab4:
    st.header("✅ Compleetheid Check")

    st.info("""
    **Doelstelling:** Controleer of monteurnotities voldoende informatie bevatten voor facturatie, contractvalidatie en kennisbehoud.

    **Potentiële benefit:**
    - Minder terugbelacties door incomplete info
    - Betere kennisoverdracht tussen monteurs
    - Snellere afhandeling van facturen

    **Geschatte besparing:** 15 min/dag aan terugbelacties = **60 uur/jaar**
    """)

    if blob_data:
        if st.button("🔍 Start Compleetheid Check", type="primary", key="compleet_btn"):
            with st.spinner("Analyseren van notitie kwaliteit..."):
                resultaten = run_compleetheid_analyse(blob_data)

            st.divider()

            # Samenvatting
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Gemiddelde score", f"{resultaten['gemiddelde_score']:.0f}%")
            with col2:
                st.metric("Goed", resultaten["verdeling"]["GOED"],
                         help="Score >= 75%")
            with col3:
                st.metric("Matig", resultaten["verdeling"]["MATIG"],
                         help="Score 50-75%")
            with col4:
                st.metric("Onvolledig", resultaten["verdeling"]["ONVOLLEDIG"],
                         help="Score < 50%")

            # Visualisatie
            st.divider()
            st.subheader("📊 Kwaliteitsverdeling")

            totaal = sum(resultaten["verdeling"].values())
            col1, col2, col3 = st.columns(3)

            with col1:
                pct = (resultaten["verdeling"]["GOED"] / totaal) * 100 if totaal else 0
                st.markdown("**✅ Goed**")
                st.progress(pct / 100)
                st.caption(f"{pct:.0f}%")

            with col2:
                pct = (resultaten["verdeling"]["MATIG"] / totaal) * 100 if totaal else 0
                st.markdown("**⚠️ Matig**")
                st.progress(pct / 100)
                st.caption(f"{pct:.0f}%")

            with col3:
                pct = (resultaten["verdeling"]["ONVOLLEDIG"] / totaal) * 100 if totaal else 0
                st.markdown("**❌ Onvolledig**")
                st.progress(pct / 100)
                st.caption(f"{pct:.0f}%")

            # Verbeterpunten
            st.divider()
            st.subheader("💡 Verbeterpunten")

            st.markdown("""
            **Vereiste elementen voor complete notitie:**
            - ✏️ **Actie** - Wat is er gedaan? (vervangen, getest, aangepast)
            - 📍 **Locatie** - Waar precies? (zone, verdieping, ruimte)
            - 🔧 **Component** - Welk onderdeel? (PIR, camera, slot)
            - ✅ **Resultaat** - Wat is de status? (werkt, opgelost, defect)
            """)

            # Onvolledige notities tonen
            st.divider()
            st.subheader("❌ Onvolledige Notities (actie nodig)")

            for i, item in enumerate(resultaten["details"]["ONVOLLEDIG"][:10], 1):
                ontbrekend = [k for k, v in item["elementen"].items() if not v]
                with st.expander(f"#{i} | Score {item['score']}% | Ontbreekt: {', '.join(ontbrekend)}"):
                    st.markdown(f"**ID:** {item['id']}")
                    st.markdown(f"**Score:** {item['score']}%")
                    st.markdown("**Aanwezige elementen:**")
                    for elem, aanwezig in item["elementen"].items():
                        icon = "✅" if aanwezig else "❌"
                        st.write(f"{icon} {VEREISTE_ELEMENTEN[elem]['beschrijving']}")
                    st.divider()
                    st.text(item["tekst"])
    else:
        st.warning("Geen data geladen")

# Footer
st.divider()
st.caption("Blob Analyse v0.4 | Zenith Security Pilot | © Notifica B.V.")
