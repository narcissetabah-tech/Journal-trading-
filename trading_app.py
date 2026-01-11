import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Journal de Trading Pro", layout="wide")
st.title("📈 Dashboard Trading : Analyse, Psychologie & Prix")

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
        actif = st.text_input("Symbole (ex: XAUUSD, GBPJPY)").upper()
        
        cat_calc = st.selectbox("Catégorie pour calcul", [
            "Forex Standard (EURUSD, GBPUSD...)", 
            "Forex JPY (USDJPY, GBPJPY...)",
            "OR (XAUUSD)",
            "ARGENT (XAGUSD)",
            "INDICES (NAS100, US30, GER40)",
            "CRYPTO (BTC, ETH...)"
        ])

        confirmation = st.selectbox("Confirmation d'entrée", [
            "Breakout", "Prise de Liquidité", "CRT", "CHoCH / MSS", 
            "Order Block", "Rebond Support/Résistance", "Retracement Fibo", "Autre"
        ])
        
        emotions = st.select_slider("État émotionnel", 
            options=["Stressé", "Anxieux", "Neutre", "Confiant", "Euphorique"], value="Neutre")

        side = st.radio("Sens", ["Long", "Short"], horizontal=True)
        
        col1, col2 = st.columns(2)
        entry = col1.number_input("Entrée", format="%.5f")
        exit_p = col2.number_input("Sortie", format="%.5f")
        
        col3, col4 = st.columns(2)
        lot = col3.number_input("Lots", format="%.4f", value=1.0)
        sl = col4.number_input("Stop-Loss", format="%.5f")
        tp = st.number_input("Take-Profit", format="%.5f")

        notes = st.text_area("Notes (Raison du trade, erreurs, etc.)", placeholder="Pourquoi as-tu pris ce trade ?")
        
        st.write("**Captures d'écran**")
        img_avant = st.file_uploader("AVANT", type=['png', 'jpg', 'jpeg'])
        img_apres = st.file_uploader("APRÈS", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL ---
if submitted:
    diff = (exit_p - entry) if side == "Long" else (entry - exit_p)
    
    if cat_calc == "Forex Standard (EURUSD, GBPUSD...)":
        pnl = diff * lot * 100000
    elif cat_calc == "Forex JPY (USDJPY, GBPJPY...)":
        pnl = diff * lot * 1000
    elif cat_calc == "OR (XAUUSD)":
        pnl = diff * lot * 100
    elif cat_calc == "ARGENT (XAGUSD)":
        pnl = diff * lot * 5000
    elif cat_calc == "INDICES (NAS100, US30, GER40)":
        pnl = diff * lot * 1
    else: 
        pnl = diff * lot * 1

    risk = abs(entry - sl)
    rr = abs(tp - entry) / risk if risk != 0 else 0
    statut = "✅ Gain" if pnl > 0 else "❌ Perte" if pnl < 0 else "⚪ BE"
    
    st.session_state.journal.append({
        "Date": date, "Actif": actif, "Sens": side, "Statut": statut,
        "PnL ($)": float(pnl), "Lot": lot, 
        "Entrée": entry, "Sortie": exit_p, "SL": sl, "TP": tp, "RR": float(rr),
        "Confirmation": confirmation, "Émotion": emotions, "Notes": notes,
        "Img_Avant": img_avant, "Img_Apres": img_apres
    })
    st.success(f"Trade enregistré ! Résultat : {pnl:.2f} $")

# --- AFFICHAGE DU DASHBOARD ---
if st.session_state.journal:
    df = pd.DataFrame(st.session_state.journal)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    df['Profit_Cumulé'] = df['PnL ($)'].cumsum()
    df['Capital_Evolution'] = cap_init + df['Profit_Cumulé']
    
    # Métriques de performance
    c1, c2, c3 = st.columns(3)
    c1.metric("Solde Actuel", f"{df['Capital_Evolution'].iloc[-1]:.2f} $")
    c2.metric("Profit Global %", f"{((df['Capital_Evolution'].iloc[-1]-cap_init)/cap_init)*100:.2f} %")
    c3.metric("Win Rate", f"{(len(df[df['PnL ($)']>0])/len(df))*100:.1f} %")

    st.subheader("📈 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Capital_Evolution'])

    # --- TABLEAU DÉTAILLÉ (AVEC PRIX D'ENTRÉE ET SORTIE) ---
    st.subheader("📋 Historique Détaillé des Prix & Notes")
    # Sélection des colonnes pour un affichage propre
    view_columns = ["Date", "Actif", "Sens", "Statut", "Entrée", "Sortie", "SL", "TP", "PnL ($)", "RR", "Confirmation", "Notes"]
    st.dataframe(df[view_columns], use_container_width=True)

    st.divider()
    st.subheader("🖼️ Analyse Visuelle & Psychologique")
    idx = st.selectbox("Détails du trade :", range(len(df)), 
                       format_func=lambda x: f"{df.iloc[x]['Date'].strftime('%d/%m')} - {df.iloc[x]['Actif']} ({df.iloc[x]['Statut']})")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.info(f"**Analyse :** {df.iloc[idx]['Confirmation']}")
    with col_info2:
        st.info(f"**Psychologie :** {df.iloc[idx]['Émotion']}")
    with col_info3:
        st.warning(f"**Notes :** {df.iloc[idx]['Notes']}")

    col_a, col_b = st.columns(2)
    with col_a:
        if df.iloc[idx]['Img_Avant']: st.image(df.iloc[idx]['Img_Avant'], caption="Setup AVANT")
    with col_b:
        if df.iloc[idx]['Img_Apres']: st.image(df.iloc[idx]['Img_Apres'], caption="Résultat APRÈS")
    
    csv = df.drop(columns=['Img_Avant', 'Img_Apres']).to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter CSV complet", data=csv, file_name="mon_journal_trading.csv")
else:
    st.info("👋 Votre journal est prêt. Saisissez votre premier trade dans la barre latérale.")
