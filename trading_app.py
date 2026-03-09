import streamlit as st
import pandas as pd
import datetime
import os

# Injection du manifest pour la PWA
st.markdown("""
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="theme-color" content="#2196F3">
""", unsafe_allow_html=True)

# ... le reste de ton code Streamlit ...

# Fichier de sauvegarde
JOURNAL_FILE = "journal_data.csv"

# Configuration de la page
st.set_page_config(page_title="Journal de Trading Pro", layout="wide")
st.title("📈 Dashboard Trading Mr Allamine : Analyse, Psychologie & Prix")

# Fonction pour charger les données existantes
def load_data():
    if os.path.exists(JOURNAL_FILE):
        df = pd.read_csv(JOURNAL_FILE)
        # Conversion des dates au bon format
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    return pd.DataFrame()

# Initialisation
if 'journal' not in st.session_state:
    st.session_state.journal = load_data()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Configuration")
    cap_init = st.number_input("Capital Initial ($)", min_value=0.0, value=25000.0)
    
    st.divider()
    st.header("🖊️ Nouveau Trade")
    with st.form("trade_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.date.today())
        actif = st.text_input("Symbole (ex: XAUUSD, GBPJPY)").upper()
        cat_calc = st.selectbox("Catégorie pour calcul", [
            "Forex Standard (EURUSD, GBPUSD...)", "Forex JPY (USDJPY, GBPJPY...)",
            "OR (XAUUSD)", "ARGENT (XAGUSD)", "INDICES (NAS100, US30, GER40)", "CRYPTO (BTC, ETH...)"
        ])
        confirmation = st.selectbox("Confirmation d'entrée", ["Breakout", "Prise de Liquidité", "CRT", "CHoCH / MSS", "Order Block", "Rebond Support/Résistance", "Retracement Fibo", "Autre"])
        emotions = st.select_slider("État émotionnel", options=["Stressé", "Anxieux", "Neutre", "Confiant", "Euphorique"], value="Neutre")
        side = st.radio("Sens", ["Long", "Short"], horizontal=True)
        col1, col2 = st.columns(2)
        entry = col1.number_input("Entrée", format="%.5f")
        exit_p = col2.number_input("Sortie", format="%.5f")
        col3, col4 = st.columns(2)
        lot = col3.number_input("Lots", format="%.4f", value=1.0)
        comms = col4.number_input("Frais/Comms ($)", min_value=0.0, value=0.0, step=0.1)
        col5, col6 = st.columns(2)
        sl = col5.number_input("Stop-Loss", format="%.5f")
        tp = col6.number_input("Take-Profit", format="%.5f")
        notes = st.text_area("Notes", placeholder="Pourquoi as-tu pris ce trade ?")
        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL ET SAUVEGARDE ---
if submitted:
    diff = (exit_p - entry) if side == "Long" else (entry - exit_p)
    if "Forex Standard" in cat_calc: pnl_brut = diff * lot * 100000
    elif "Forex JPY" in cat_calc: pnl_brut = diff * lot * 1000
    elif "OR" in cat_calc: pnl_brut = diff * lot * 100
    elif "ARGENT" in cat_calc: pnl_brut = diff * lot * 5000
    else: pnl_brut = diff * lot

    pnl_net = pnl_brut - comms
    risk = abs(entry - sl)
    rr = abs(tp - entry) / risk if risk != 0 else 0
    statut = "✅ Gain" if pnl_net > 0 else "❌ Perte" if pnl_net < 0 else "⚪ BE"
    
    nouveau_trade = pd.DataFrame([{
        "Date": date, "Actif": actif, "Sens": side, "Statut": statut,
        "Entrée": entry, "Sortie": exit_p, "SL": sl, "TP": tp,
        "PnL Net ($)": float(pnl_net), "Frais ($)": float(comms), "RR": float(rr),
        "Lot": lot, "Confirmation": confirmation, "Émotion": emotions, "Notes": notes
    }])

    st.session_state.journal = pd.concat([st.session_state.journal, nouveau_trade], ignore_index=True)
    st.session_state.journal.to_csv(JOURNAL_FILE, index=False)
    st.success(f"Trade enregistré ! Résultat net : {pnl_net:.2f} $")

# --- AFFICHAGE DU DASHBOARD ---
if not st.session_state.journal.empty:
    df = st.session_state.journal
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    df['Profit_Cumulé'] = df['PnL Net ($)'].cumsum()
    df['Capital_Evolution'] = cap_init + df['Profit_Cumulé']
    
    c1, c2, c3, c4 = st.columns(4)
    solde_actuel = df['Capital_Evolution'].iloc[-1]
    c1.metric("Solde Actuel", f"{solde_actuel:.2f} $")
    c2.metric("Profit Global %", f"{((solde_actuel - cap_init) / cap_init) * 100:.2f} %")
    c3.metric("Win Rate", f"{(len(df[df['PnL Net ($)'] > 0]) / len(df)) * 100:.1f} %")
    c4.metric("Frais Totaux", f"{df['Frais ($)'].sum():.2f} $")

    st.subheader("📈 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Capital_Evolution'])

    st.subheader("📋 Historique")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter CSV", data=csv, file_name="journal_trading.csv")
else:
    st.info("👋 Votre journal est vide.")
