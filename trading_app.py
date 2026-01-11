import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

# Configuration
st.set_page_config(page_title="Trading Journal & Capital Manager", layout="wide")
st.title("📈 Dashboard de Trading Professionnel")

# --- INITIALISATION ---
if 'journal' not in st.session_state:
    st.session_state.journal = []

# Keep a locked initial capital so past trades don't change if user tweaks the sidebar value
if 'capital_initial_locked' not in st.session_state:
    st.session_state.capital_initial_locked = None

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Paramètres du Compte")
    capital_initial_input = st.number_input("Capital Initial ($)", min_value=0.0, value=1000.0, step=100.0, format="%.2f")
    # Option to lock the initial capital used for calculations
    if st.session_state.capital_initial_locked is None:
        if st.button("Verrouiller ce capital initial"):
            st.session_state.capital_initial_locked = float(capital_initial_input)
    else:
        st.markdown(f"**Capital initial verrouillé :** {st.session_state.capital_initial_locked:.2f} $")
        if st.button("Déverrouiller / Mettre à jour"):
            st.session_state.capital_initial_locked = None

    st.divider()
    st.header("🖊️ Nouveau Trade")
    with st.form("trade_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.date.today())
        actif = st.text_input("Actif", placeholder="ex: BTC/USDT")
        setup = st.selectbox("Setup", ["Breakout", "Retracement", "Range", "Scalp"])
        side = st.radio("Sens", ["Long", "Short"], horizontal=True)
        
        lot_size = st.number_input("Taille de Lot (Quantité)", min_value=0.0, format="%.8f")
        entry = st.number_input("Prix d'Entrée", format="%.8f")
        sl = st.number_input("Stop-loss", format="%.8f")
        tp = st.number_input("Take-profit", format="%.8f")
        exit_p = st.number_input("Prix de Sortie", format="%.8f")
        
        st.divider()
        img_avant = st.file_uploader("Capture AVANT", type=['png', 'jpg', 'jpeg'])
        img_apres = st.file_uploader("Capture APRÈS", type=['png', 'jpg', 'jpeg'])
        
        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL ---
if submitted:
    # Use locked capital if set, otherwise lock on first submission to current input
    if st.session_state.capital_initial_locked is None:
        st.session_state.capital_initial_locked = float(capital_initial_input)

    # Calcul PnL $
    pnl_dollars = (exit_p - entry) * lot_size if side == "Long" else (entry - exit_p) * lot_size

    # Calcul R:R (prévu)
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr_prevu = round(reward / risk, 2) if risk != 0 else 0.0

    # Save images as raw bytes in-memory (so they persist in session_state)
    def _read_file_bytes(uploaded):
        if uploaded is None:
            return None
        try:
            uploaded.seek(0)
        except Exception:
            pass
        return uploaded.read()

    img_avant_bytes = _read_file_bytes(img_avant)
    img_apres_bytes = _read_file_bytes(img_apres)

    new_trade = {
        "Date": pd.to_datetime(date),
        "Actif": actif.upper() if actif else "",
        "Setup": setup,
        "Sens": side,
        "Lot": float(lot_size),
        "Entrée": float(entry),
        "SL": float(sl),
        "TP": float(tp),
        "Sortie": float(exit_p),
        "R:R Prévu": rr_prevu,
        "PnL ($)": round(float(pnl_dollars), 2),
        "Capture_Avant_bytes": img_avant_bytes,
        "Capture_Apres_bytes": img_apres_bytes
    }
    st.session_state.journal.append(new_trade)
    st.success("Trade ajouté au journal ✅")

# --- AFFICHAGE DU DASHBOARD ---
if st.session_state.journal:
    df = pd.DataFrame(st.session_state.journal)

    # Ensure Date is datetime and sorted
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    # Calcul de la courbe de capital
    capital_initial = float(st.session_state.capital_initial_locked if st.session_state.capital_initial_locked is not None else capital_initial_input)
    df['Cumulative_PnL'] = df['PnL ($)'].cumsum()
    df['Current_Balance'] = capital_initial + df['Cumulative_PnL']
    # previous balance used to compute % gain per trade
    df['Prev_Balance'] = (df['Current_Balance'] - df['PnL ($)']).replace(0, pd.NA)
    df['Gain_Pct'] = (df['PnL ($)'] / df['Prev_Balance']) * 100
    df['Gain_Pct'] = df['Gain_Pct'].fillna(0)

    # Max Drawdown
    df['Peak'] = df['Current_Balance'].cummax()
    df['Drawdown'] = (df['Current_Balance'] - df['Peak']) / df['Peak'] * 100  # negative or zero
    max_drawdown = df['Drawdown'].min() if not df['Drawdown'].empty else 0.0

    # MÉTRIQUES CLÉS
    c1, c2, c3, c4 = st.columns(4)
    final_balance = df['Current_Balance'].iloc[-1]
    total_pnl_pct = ((final_balance - capital_initial) / capital_initial) * 100 if capital_initial != 0 else 0.0

    last_pnl = df['PnL ($)'].iloc[-1]
    c1.metric("Solde Actuel", f"{final_balance:.2f} $", delta=f"{last_pnl:.2f} $")
    c2.metric("Profit Global", f"{total_pnl_pct:.2f} %")
    c3.metric("R:R Moyen", f"{df['R:R Prévu'].replace(0, pd.NA).mean().fillna(0):.2f}")
    win_rate = (len(df[df['PnL ($)'] > 0]) / len(df)) * 100 if len(df) > 0 else 0.0
    c4.metric("Win Rate", f"{win_rate:.1f} %")

    # Additional metrics row
    d1, d2 = st.columns(2)
    d1.metric("Trades", f"{len(df)}")
    d2.metric("Max Drawdown", f"{max_drawdown:.2f} %")

    # GRAPHIQUE D'ÉVOLUTION
    st.subheader("📈 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Current_Balance'])

    # TABLEAU RÉCAPITULATIF (sans colonnes d'images brutes)
    display_df = df.drop(columns=['Capture_Avant_bytes', 'Capture_Apres_bytes', 'Cumulative_PnL', 'Peak', 'Prev_Balance', 'Drawdown'])
    display_df = display_df.rename(columns={
        "Lot": "Taille",
        "Entrée": "Prix Entrée",
        "SL": "Stop-loss",
        "TP": "Take-profit",
        "Sortie": "Prix Sortie",
        "R:R Prévu": "R:R Prévu",
        "PnL ($)": "PnL ($)",
        "Gain_Pct": "% Gain"
    })
    st.subheader("📋 Historique des Positions")
    st.dataframe(display_df, use_container_width=True)

    # Show images below the table with simple controls (delete last / clear all)
    st.subheader("🖼️ Captures")
    for i, row in df.iterrows():
        with st.expander(f"{row['Date'].date()} — {row['Actif']} — PnL: {row['PnL ($)']:+.2f} $"):
            col1, col2, col3 = st.columns([1, 1, 0.6])
            with col1:
                if row['Capture_Avant_bytes'] is not None:
                    st.image(BytesIO(row['Capture_Avant_bytes']), caption="Avant", use_column_width=True)
                else:
                    st.write("Aucune capture AVANT")
            with col2:
                if row['Capture_Apres_bytes'] is not None:
                    st.image(BytesIO(row['Capture_Apres_bytes']), caption="Après", use_column_width=True)
                else:
                    st.write("Aucune capture APRÈS")
            with col3:
                # Delete button for each trade (keyed by index to avoid collision)
                if st.button("Supprimer ce trade", key=f"del_{i}"):
                    st.session_state.journal.pop(i)
                    st.experimental_rerun()

    # Quick controls
    st.divider()
    col_clear, col_delete_last = st.columns(2)
    with col_delete_last:
        if st.button("Supprimer le dernier trade"):
            st.session_state.journal.pop(-1)
            st.experimental_rerun()
    with col_clear:
        if st.button("Effacer tout le journal"):
            st.session_state.journal.clear()
            st.experimental_rerun()

    # EXPORT CSV (exclude raw image bytes)
    export_df = df.drop(columns=['Capture_Avant_bytes', 'Capture_Apres_bytes', 'Cumulative_PnL', 'Peak', 'Prev_Balance', 'Drawdown'])
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter le journal (CSV)", data=csv, file_name=f"journal_{datetime.date.today()}.csv")

    # Export JSON (also images excluded)
    json_bytes = export_df.to_json(orient='records', date_format='iso').encode('utf-8')
    st.download_button("📥 Exporter le journal (JSON)", data=json_bytes, file_name=f"journal_{datetime.date.today()}.json")

else:
    # No trades yet; allow locking initial capital early if desired
    if st.session_state.capital_initial_locked is None:
        st.info(f"Configuration : Capital initial de {capital_initial_input:.2f} $. Verrouillez-le pour l'utiliser dans les calculs.")
    else:
        st.info(f"Configuration : Capital initial verrouillé de {st.session_state.capital_initial_locked:.2f} $. Ajoutez un trade pour commencer.")
