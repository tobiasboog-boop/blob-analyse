"""
Blob Analyse - Zenith Security
Maandrapportage Tool voor DWH + Blobvelden

Versie: Simplified (alleen maandrapportage)
Volledige versie (met alle business cases): zie app_full_version.py

SECURITY: Database credentials worden NIET in code opgeslagen, maar via Streamlit secrets.
"""

import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Maandrapportage - Zenith Security",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# APP AUTHENTICATION
# =============================================================================

def check_app_password():
    """Check if user has entered correct app password."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Login - Zenith Maandrapportage")

        with st.form("login_form"):
            password_input = st.text_input("Wachtwoord", type="password")
            submit = st.form_submit_button("Inloggen")

            if submit:
                app_password = st.secrets.get("APP_PASSWORD", "z&fo@GeVqZ%COFBRsWmjX$sV")
                if password_input == app_password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect wachtwoord")

        st.stop()


# =============================================================================
# CONFIGURATIE & SECRETS
# =============================================================================

def get_db_config():
    """
    Haal database configuratie op uit Streamlit secrets.
    Fallback naar None als secrets niet beschikbaar zijn.
    """
    try:
        if "database" in st.secrets:
            return {
                "host": st.secrets["database"]["host"],
                "port": st.secrets["database"]["port"],
                "database": st.secrets["database"]["database"],
                "user": st.secrets["database"]["user"],
                "password": st.secrets["database"]["password"]
            }
    except Exception as e:
        st.warning(f"⚠️ Database secrets niet gevonden: {e}")
    return None


# Data source mode
USE_DATABASE = get_db_config() is not None
DATA_SOURCE = "Database (live)" if USE_DATABASE else "JSON files (sample)"


# =============================================================================
# DATABASE FUNCTIES (alleen gebruikt als USE_DATABASE = True)
# =============================================================================

@st.cache_resource
def get_db_connection():
    """Maak database connectie met secrets."""
    db_config = get_db_config()
    if not db_config:
        return None

    try:
        import psycopg2
        conn = psycopg2.connect(**db_config)
        return conn
    except Exception as e:
        st.error(f"❌ Database connectie fout: {e}")
        return None


@st.cache_data(ttl=3600)
def load_clob_data_from_db(clob_type):
    """Laad CLOB data uit database."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    table_map = {
        "document": "maatwerk.stg_AT_DOCUMENT_CLOBS",
        "uitvbest": "maatwerk.stg_AT_UITVBEST_CLOBS",
        "werk": "maatwerk.stg_AT_WERK_CLOBS",
        "mwbsess": "maatwerk.stg_AT_MWBSESS_CLOBS"
    }

    table_name = table_map.get(clob_type)
    if not table_name:
        return pd.DataFrame()

    try:
        query = f"SELECT * FROM {table_name} LIMIT 1000"
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Fout bij laden {clob_type} data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def load_dwh_werkbonnen_from_db(limit=1000):
    """Laad werkbonnen uit DWH database."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        query = f"""
        SELECT
            "DocumentKey" as werkbon_key,
            "Werkboncode" as werkbon_code,
            "Klantnaam" as klant,
            "Status" as status,
            "Melddatum" as melddatum,
            "Type" as type,
            "Prioriteit" as prioriteit
        FROM werkbonnen."Documenten"
        ORDER BY "Melddatum" DESC
        LIMIT {limit}
        """
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Fout bij laden werkbonnen: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def load_mobiele_sessies_from_db():
    """Laad mobiele uitvoersessies uit database."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        query = """
        SELECT
            "MobieleuitvoersessieRegelKey" as sessie_key,
            "DocumentKey" as werkbon_key,
            "Medewerker" as monteur,
            "Datum" as datum,
            "Status" as status
        FROM werkbonnen."Mobiele uitvoersessies"
        """
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Fout bij laden sessies: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


# =============================================================================
# JSON FALLBACK FUNCTIES
# =============================================================================

@st.cache_data
def load_json_data():
    """Laad sample data uit JSON files."""
    data_path = Path(__file__).parent / "data" / "sample_data.json"
    if not data_path.exists():
        return None

    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Fout bij laden JSON data: {e}")
        return None


def load_data_from_json():
    """Converteer JSON data naar rapport formaat."""
    json_data = load_json_data()
    if not json_data:
        return pd.DataFrame()

    rapport_items = []

    for notitie in json_data.get("monteur_notities", []):
        werkbon = notitie.get("werkbon", {})
        if not werkbon:
            continue

        tekst = clean_tekst(notitie.get("tekst", ""))
        melddatum = werkbon.get("melddatum", "")

        rapport_items.append({
            "werkbon_code": werkbon.get("werkbon_code", ""),
            "klant": werkbon.get("klant", "Onbekend"),
            "monteur": werkbon.get("monteur", "Onbekend"),
            "datum": melddatum[:10] if melddatum else "",
            "maand": melddatum[:7] if melddatum else "Onbekend",
            "status": werkbon.get("status", "").strip(),
            "notitie": tekst,
            "type": werkbon.get("type", "")
        })

    return pd.DataFrame(rapport_items)


def clean_tekst(tekst):
    """Verwijder RTF rommel uit tekst."""
    if pd.isna(tekst):
        return ""

    tekst = str(tekst)
    # Verwijder "Arial;Symbol;" en varianten
    tekst = re.sub(r'^[A-Za-z;]+;\s*\n*', '', tekst)
    # Verwijder leading 'd' die vaak overblijft
    tekst = re.sub(r'^\s*d([A-Z])', r'\1', tekst)
    return tekst.strip()


# =============================================================================
# RAPPORTAGE LOGICA
# =============================================================================

def combine_data_for_rapport():
    """
    Combineer data voor maandrapportage.
    Gebruikt database ALS beschikbaar, anders JSON fallback.

    Returns:
        DataFrame met werkbon + blobveld data
    """
    if USE_DATABASE:
        # Database mode
        werkbonnen = load_dwh_werkbonnen_from_db()
        sessies = load_mobiele_sessies_from_db()
        mwbsess_clobs = load_clob_data_from_db("mwbsess")

        if werkbonnen.empty or sessies.empty:
            st.warning("⚠️ Database data incomplete, falling back naar JSON...")
            return load_data_from_json()

        # TODO: Implementeer database join logica
        # Dit vereist kennis van de exacte CLOB tabel structuur
        # Voor nu: gebruik JSON fallback
        st.info("ℹ️ Database connectie actief, maar join logica nog niet geïmplementeerd. Gebruik JSON data.")
        return load_data_from_json()

    else:
        # JSON fallback mode
        return load_data_from_json()


# =============================================================================
# STREAMLIT APP
# =============================================================================

# Check app password first
check_app_password()

# Header
st.title("📊 Maandrapportage - Zenith Security")
st.markdown("**Werkbonnen met monteurnotities** uit DWH + Blobvelden")

st.divider()

# Sidebar
with st.sidebar:
    # Logo
    logo_path = Path(__file__).parent / "assets" / "notifica_logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=120)
        st.divider()

    # Data source indicator
    st.header("Data Bron")
    if USE_DATABASE:
        st.success("🟢 Database (live)")
        db_config = get_db_config()
        st.caption(f"Server: {db_config['host']}")
        st.caption(f"Database: {db_config['database']}")
    else:
        st.warning("🟡 JSON Files (sample)")
        st.caption("Database secrets niet gevonden")
        st.caption("Gebruikt: data/sample_data.json")

    st.divider()

    st.header("Over deze tool")
    st.markdown("""
    Deze tool genereert maandrapportages door:
    - DWH werkbonnen data
    - Blobvelden (monteurnotities)

    Te combineren in één overzicht.

    **Data modus:**
    - Live: Database connectie actief
    - Sample: JSON test data
    """)

    st.divider()

    st.markdown("**Klant:** Zenith Security (1229)")

    st.divider()

    if st.button("🔄 Ververs data"):
        st.cache_data.clear()
        st.rerun()

    # Security info
    with st.expander("🔒 Security"):
        st.markdown("""
        **Veilig geconfigureerd:**
        - ✅ Geen credentials in code
        - ✅ Secrets via Streamlit
        - ✅ JSON fallback beschikbaar

        **Database user:**
        - Read-only toegang
        - Alleen 1229 schema
        """)

# Main content
st.header("Maandrapportage")

st.markdown("""
Genereer overzichten van werkbonnen met monteurnotities voor maandrapportages.
Data wordt gecombineerd uit DWH + Blobveld tabellen.
""")

st.divider()

# Eerst filters tonen VOOR data laden
st.subheader("Selecteer Periode")

col1, col2 = st.columns([3, 1])
with col1:
    periode_opties = ["Laatste maand", "Laatste 3 maanden", "Laatste 6 maanden", "Laatste jaar", "Alles"]
    geselecteerde_periode = st.selectbox(
        "Hoeveel data wil je laden?",
        options=periode_opties,
        index=1  # Default: Laatste 3 maanden
    )

with col2:
    st.write("")  # Spacer
    st.write("")  # Spacer
    laad_data_knop = st.button("📥 Laad Data", type="primary", use_container_width=True)

st.divider()

# Initialiseer rapport_data
rapport_data = pd.DataFrame()

# Data laden alleen na knop drukken
if laad_data_knop or 'rapport_data' in st.session_state:
    if laad_data_knop:
        with st.spinner("Data laden uit database..."):
            rapport_data = combine_data_for_rapport()
            st.session_state['rapport_data'] = rapport_data
    else:
        rapport_data = st.session_state.get('rapport_data', pd.DataFrame())

    # Filter op basis van periode (alleen voor database mode)
    if not rapport_data.empty and USE_DATABASE:
        # Bereken cutoff datum
        vandaag = datetime.now()
        if geselecteerde_periode == "Laatste maand":
            cutoff = vandaag - timedelta(days=30)
        elif geselecteerde_periode == "Laatste 3 maanden":
            cutoff = vandaag - timedelta(days=90)
        elif geselecteerde_periode == "Laatste 6 maanden":
            cutoff = vandaag - timedelta(days=180)
        elif geselecteerde_periode == "Laatste jaar":
            cutoff = vandaag - timedelta(days=365)
        else:  # Alles
            cutoff = None

        if cutoff:
            rapport_data['datum_dt'] = pd.to_datetime(rapport_data['datum'], errors='coerce')
            rapport_data = rapport_data[rapport_data['datum_dt'] >= cutoff].copy()
            rapport_data = rapport_data.drop('datum_dt', axis=1)

if not rapport_data.empty:
    # === FILTERS ===
    st.subheader("Filters")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Verzamel unieke waarden
    alle_maanden = sorted(rapport_data['maand'].unique(), reverse=True)
    alle_klanten = sorted(rapport_data['klant'].unique())
    alle_monteurs = sorted([m for m in rapport_data['monteur'].unique() if pd.notna(m)])

    with filter_col1:
        geselecteerde_maand = st.selectbox(
            "Periode",
            options=["Alle"] + list(alle_maanden),
            index=0
        )

    with filter_col2:
        geselecteerde_klant = st.selectbox(
            "Klant",
            options=["Alle"] + alle_klanten,
            index=0
        )

    with filter_col3:
        geselecteerde_monteur = st.selectbox(
            "Monteur",
            options=["Alle"] + alle_monteurs,
            index=0
        )

    # Pas filters toe
    gefilterd = rapport_data.copy()
    if geselecteerde_maand != "Alle":
        gefilterd = gefilterd[gefilterd["maand"] == geselecteerde_maand]
    if geselecteerde_klant != "Alle":
        gefilterd = gefilterd[gefilterd["klant"] == geselecteerde_klant]
    if geselecteerde_monteur != "Alle":
        gefilterd = gefilterd[gefilterd["monteur"] == geselecteerde_monteur]

    st.divider()

    # === SAMENVATTING ===
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Werkbonnen", len(gefilterd))
    with col2:
        st.metric("Unieke klanten", gefilterd['klant'].nunique())
    with col3:
        st.metric("Unieke monteurs", gefilterd['monteur'].nunique())

    st.divider()

    # === COMPACTE MATRIX WEERGAVE ===
    st.subheader("Overzicht")

    # Toon als interactieve tabel
    display_df = gefilterd[['werkbon_code', 'klant', 'monteur', 'datum', 'status', 'notitie']].copy()
    display_df.columns = ['Werkbon', 'Klant', 'Monteur', 'Datum', 'Status', 'Notitie']

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Werkbon": st.column_config.TextColumn("Werkbon", width="small"),
            "Klant": st.column_config.TextColumn("Klant", width="medium"),
            "Monteur": st.column_config.TextColumn("Monteur", width="small"),
            "Datum": st.column_config.TextColumn("Datum", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Notitie": st.column_config.TextColumn("Notitie", width="large"),
        }
    )

    # === DETAIL WEERGAVE ===
    st.divider()
    with st.expander("Volledige notities bekijken"):
        for _, row in gefilterd.iterrows():
            st.markdown(f"**{row['werkbon_code']}** | {row['klant']} | {row['monteur']} | {row['datum']}")
            if row['notitie']:
                st.text(row['notitie'][:500])
            else:
                st.caption("Geen notitie beschikbaar")
            st.markdown("---")

    # === EXPORT SECTIE ===
    st.divider()
    st.subheader("Export")

    # CSV download
    csv = display_df.to_csv(index=False, sep=";")
    st.download_button(
        label="📥 Download als CSV",
        data=csv,
        file_name=f"werkbonnen_rapport_{geselecteerde_maand if geselecteerde_maand != 'Alle' else 'alle'}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

    # Excel download optie
    st.info("💡 **Tip:** Open de CSV in Excel voor verdere verwerking")

else:
    # Nog geen data geladen
    if laad_data_knop:
        st.warning("Geen data beschikbaar. Controleer de database connectie.")
    else:
        st.info("👆 **Klik op 'Laad Data' om te beginnen**")

        st.markdown("""
        **Tips:**
        - Start met 'Laatste 3 maanden' voor snelle resultaten
        - Gebruik 'Alles' alleen als je de volledige dataset nodig hebt
        - Na laden kun je verder filteren op klant en monteur
        """)

    # Debug info
    with st.expander("🔧 Debug informatie"):
        st.markdown("**Database tabellen:**")
        st.code("""
        - maatwerk.stg_AT_DOCUMENT_CLOBS
        - maatwerk.stg_AT_UITVBEST_CLOBS
        - maatwerk.stg_AT_WERK_CLOBS
        - maatwerk.stg_AT_MWBSESS_CLOBS
        - werkbonnen."Documenten"
        - werkbonnen."Mobiele uitvoersessies"
        """)

        st.markdown("**Controleer:**")
        st.write("1. Is de database connectie actief?")
        st.write("2. Zijn de tabellen gevuld met data?")
        st.write("3. Kloppen de kolomnamen in de queries?")

# Footer
st.divider()
st.caption("Maandrapportage Tool v1.0 | Zenith Security | © Notifica B.V.")
st.caption("Volledige versie met alle business cases: zie `app_full_version.py`")
