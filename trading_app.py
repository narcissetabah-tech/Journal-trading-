import streamlit as st
import pandas as pd
import datetime

# Configuration de la page
st.set_page_config(page_title="Dashboard Trading Ultime", layout="wide")
st.title("📊 Dashboard Complet de Trading")

# Initialisation du journal dans la session
if 'journal' not in st.session_state:
    st.session_state.journal = []

# --- BARRE LATÉRALE (SAISIE) ---
with st.sidebar:
    st.header("⚙️ Paramètres")
    cap_init = st.number_input("Capital Initial ($)", min_value=0.0, value=25000.0)
    
    st.divider()
    st.header("🖊️ Nouveau Trade")
    with st.form("trade_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.date.today())
        actif = st.text_input("Actif (ex: EURUSD)")
        side = st.radio("Sens", ["Long", "Short"], horizontal=True)
        
        col1, col2 = st.columns(2)
        entry = col1.number_input("Entrée", format="%.5f")
        exit_p = col2.number_input("Sortie", format="%.5f")
        
        col3, col4 = st.columns(2)
        lot = col3.number_input("Lots/Qté", format="%.4f", value=1.0)
        sl = col4.number_input("Stop-Loss", format="%.5f")
        tp = st.number_input("Take-Profit", format="%.5f")
        
        st.write("**Captures d'écran**")
        img_avant = st.file_uploader("AVANT le trade", type=['png', 'jpg', 'jpeg'])
        img_apres = st.file_uploader("APRÈS le trade", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL ---
if submitted:
    pnl = (exit_p - entry) * lot if side == "Long" else (entry - exit_p) * lot
    risk = abs(entry - sl)
    rr = abs(tp - entry) / risk if risk != 0 else 0
    
    st.session_state.journal.append({
        "Date": date,
        "Actif": actif.upper(),
        "Sens": side,
        "Entrée": entry,
        "Sortie": exit_p,
        "Lot": lot,
        "PnL ($)": float(pnl),
        "RR Prévu": float(rr),
        "Img_Avant": img_avant,
        "Img_Apres": img_apres
    })
    st.success("Trade ajouté avec succès ! ✅")

# --- AFFICHAGE DU DASHBOARD ---
if st.session_state.journal:
    df = pd.DataFrame(st.session_state.journal)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Calcul Capital
    df['Profit_Cumulé'] = df['PnL ($)'].cumsum()
    df['Evolution_Capital'] = cap_init + df['Profit_Cumulé']
    
    # 1. Métriques de tête
    c1, c2, c3 = st.columns(3)
    solde_actuel = df['Evolution_Capital'].iloc[-1]
    profit_global = ((solde_actuel - cap_init) / cap_init) * 100
    win_rate = (len(df[df['PnL ($)'] > 0]) / len(df)) * 100
    
    c1.metric("Solde Actuel", f"{solde_actuel:.2f} $", f"{df['PnL ($)'].iloc[-1]:.2f} $")
    c2.metric("Profit Global", f"{profit_global:.2f} %")
    c3.metric("Win Rate", f"{win_rate:.1f} %")

    # 2. Graphique d'évolution
    st.subheader("📈 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Evolution_Capital'])

    # 3. Tableau de données
    st.subheader("📋 Historique Détaillé")
    st.dataframe(df.drop(columns=['Img_Avant', 'Img_Apres', 'Profit_Cumulé']), use_container_width=True)

    # 4. Analyse Visuelle (Captures)
    st.divider()
    st.subheader("🖼️ Analyse Visuelle")
    idx = st.selectbox("Sélectionnez un trade pour voir les images :", 
                       range(len(df)), 
                       format_func=lambda x: f"Trade {x+1}: {df.iloc[x]['Actif']} ({df.iloc[x]['Date'].strftime('%d/%m')})")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**AVANT (Analyse)**")
        if df.iloc[idx]['Img_Avant']:
            st.image(df.iloc[idx]['Img_Avant'])
        else:
            st.info("Aucune capture avant.")
    with col_b:
        st.write("**APRÈS (Résultat)**")
        if df.iloc[idx]['Img_Apres']:
            st.image(df.iloc[idx]['Img_Apres'])
        else:
            st.info("Aucune capture après.")
            
    # 5. Export
    csv = df.drop(columns=['Img_Avant', 'Img_Apres']).to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter en CSV", data=csv, file_name="mon_journal.csv")

else:
    st.info("👋 Votre journal est prêt. Ajoutez un trade dans la barre latérale pour commencer l'analyse.")
