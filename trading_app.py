import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Journal de Trading Pro", layout="wide")
st.title("📈 Dashboard & Calculateur de Pips Précis")

if 'journal' not in st.session_state:
    st.session_state.journal = []

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Configuration")
    cap_init = st.number_input("Capital Initial ($)", min_value=0.0, value=25000.0)
    
    st.divider()
    st.header("🖊️ Nouveau Trade")
    with st.form("trade_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.date.today())
        actif = st.text_input("Symbole (ex: XAGUSD, USDJPY, NAS100)").upper()
        
        # SÉLECTEUR DE CATÉGORIE POUR CALCUL PRÉCIS
        cat_calc = st.selectbox("Catégorie pour calcul des lots", [
            "Forex Standard (EURUSD, GBPUSD...)", 
            "Forex JPY (USDJPY, GBPJPY...)",
            "OR (XAUUSD)",
            "ARGENT (XAGUSD)",
            "INDICES (NAS100, US30, GER40)",
            "CRYPTO (BTC, ETH...)"
        ])
        
        side = st.radio("Sens", ["Long", "Short"], horizontal=True)
        
        col1, col2 = st.columns(2)
        entry = col1.number_input("Prix d'Entrée", format="%.5f")
        exit_p = col2.number_input("Prix de Sortie", format="%.5f")
        
        col3, col4 = st.columns(2)
        lot = col3.number_input("Nombre de Lots", format="%.4f", value=1.0)
        sl = col4.number_input("Stop-Loss", format="%.5f")
        tp = st.number_input("Take-Profit", format="%.5f")
        
        st.write("**Captures d'écran**")
        img_avant = st.file_uploader("AVANT", type=['png', 'jpg', 'jpeg'])
        img_apres = st.file_uploader("APRÈS", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL RIGOUREUSE ---
if submitted:
    diff = (exit_p - entry) if side == "Long" else (entry - exit_p)
    
    # DÉFINITION DES MULTIPLICATEURS (CONTRACT SIZE)
    if cat_calc == "Forex Standard (EURUSD, GBPUSD...)":
        # 1 lot = 100,000 unités | 1 pip (0.0001) = 10$
        pnl = diff * lot * 100000
    elif cat_calc == "Forex JPY (USDJPY, GBPJPY...)":
        # 1 lot = 100,000 unités | 1 pip (0.01) = ~6.5$ à 10$ selon le taux
        # Le multiplicateur standard MT5 pour le JPY est 1000 pour transformer 0.01 en 10$
        pnl = diff * lot * 1000
    elif cat_calc == "OR (XAUUSD)":
        # 1 lot = 100 onces | 1 point (1.00) = 100$
        pnl = diff * lot * 100
    elif cat_calc == "ARGENT (XAGUSD)":
        # 1 lot = 5000 onces | 1 point (1.00) = 5000$
        pnl = diff * lot * 5000
    elif cat_calc == "INDICES (NAS100, US30, GER40)":
        # Généralement 1 lot = 1$ par point
        pnl = diff * lot * 1
    else: # Crypto
        pnl = diff * lot * 1

    risk = abs(entry - sl)
    rr = abs(tp - entry) / risk if risk != 0 else 0
    
    st.session_state.journal.append({
        "Date": date, "Actif": actif, "Type": cat_calc, "Sens": side,
        "PnL ($)": float(pnl), "RR": float(rr), "Lot": lot,
        "Img_Avant": img_avant, "Img_Apres": img_apres
    })
    st.success(f"Trade enregistré ! Gain/Perte : {pnl:.2f} $")

# --- AFFICHAGE DU DASHBOARD ---
if st.session_state.journal:
    df = pd.DataFrame(st.session_state.journal)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    df['Profit_Cumulé'] = df['PnL ($)'].cumsum()
    df['Capital_Evolution'] = cap_init + df['Profit_Cumulé']
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Solde Actuel", f"{df['Capital_Evolution'].iloc[-1]:.2f} $")
    c2.metric("Profit %", f"{((df['Capital_Evolution'].iloc[-1]-cap_init)/cap_init)*100:.2f} %")
    c3.metric("Win Rate", f"{(len(df[df['PnL ($)']>0])/len(df))*100:.1f} %")

    st.subheader("📉 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Capital_Evolution'])

    st.subheader("📋 Historique")
    st.dataframe(df.drop(columns=['Img_Avant', 'Img_Apres', 'Profit_Cumulé']), use_container_width=True)

    st.divider()
    st.subheader("🖼️ Analyse Visuelle")
    idx = st.selectbox("Sélectionner un trade :", range(len(df)), format_func=lambda x: f"{df.iloc[x]['Date'].strftime('%d/%m')} - {df.iloc[x]['Actif']}")
    col_a, col_b = st.columns(2)
    with col_a:
        if df.iloc[idx]['Img_Avant']: st.image(df.iloc[idx]['Img_Avant'], caption="AVANT")
    with col_b:
        if df.iloc[idx]['Img_Apres']: st.image(df.iloc[idx]['Img_Apres'], caption="APRÈS")
    
    csv = df.drop(columns=['Img_Avant', 'Img_Apres']).to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter CSV", data=csv, file_name="journal_trading.csv")
