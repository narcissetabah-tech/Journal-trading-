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
if 'next_id' not in st.session_state:
    st.session_state.next_id = 1
if 'capital_initial' not in st.session_state:
    st.session_state.capital_initial = 1000.0

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Paramètres du Compte")
    # Persist capital initial in session_state so other UI re-renders keep it
    st.session_state.capital_initial = st.number_input(
        "Capital Initial ($)",
        min_value=0.0,
        value=st.session_state.capital_initial,
        step=100.0,
    )

    st.divider()
    st.header("🖊️ Nouveau Trade")
    with st.form("trade_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.date.today())
        actif = st.text_input("Actif", placeholder="ex: BTC/USDT")
        setup = st.selectbox("Setup", ["Breakout", "Retracement", "Range", "Scalp"])
        side = st.radio("Sens", ["Long", "Short"], horizontal=True)

        lot_size = st.number_input("Taille de Lot (Quantité)", min_value=0.0, format="%.4f", value=0.0)
        entry = st.number_input("Prix d'Entrée", format="%.5f", value=0.0)
        sl = st.number_input("Stop-loss", format="%.5f", value=0.0)
        tp = st.number_input("Take-profit", format="%.5f", value=0.0)
        exit_p = st.number_input("Prix de Sortie", format="%.5f", value=0.0)

        st.divider()
        img_avant = st.file_uploader("Capture AVANT", type=['png', 'jpg', 'jpeg'])
        img_apres = st.file_uploader("Capture APRÈS", type=['png', 'jpg', 'jpeg'])

        submitted = st.form_submit_button("Enregistrer le Trade")

# --- LOGIQUE DE CALCUL ---
def read_uploaded_file(uploaded):
    if uploaded is None:
        return None, None
    uploaded.seek(0)
    b = uploaded.read()
    name = getattr(uploaded, "name", None)
    return b, name

if submitted:
    # Basic validations
    errors = []
    if not actif:
        errors.append("L'actif est requis.")
    if lot_size <= 0:
        errors.append("La taille de lot doit être supérieure à 0.")
    if entry == 0:
        errors.append("Le prix d'entrée doit être renseigné.")
    if sl == 0:
        errors.append("Le stop-loss doit être renseigné.")
    if tp == 0:
        errors.append("Le take-profit doit être renseigné.")
    if exit_p == 0:
        errors.append("Le prix de sortie doit être renseigné.")
    if errors:
        for e in errors:
            st.sidebar.error(e)
    else:
        # Calcul PnL $
        pnl_dollars = (exit_p - entry) * lot_size if side == "Long" else (entry - exit_p) * lot_size

        # Calcul R:R (prévu) et R:R (réalisé)
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_prevu = reward / risk if risk != 0 else None
        rr_realise = (pnl_dollars / risk) if (risk != 0) else None

        avant_bytes, avant_name = read_uploaded_file(img_avant)
        apres_bytes, apres_name = read_uploaded_file(img_apres)

        new_trade = {
            "ID": st.session_state.next_id,
            "Date": date,
            "Actif": actif.upper(),
            "Setup": setup,
            "Sens": side,
            "Lot": lot_size,
            "Entrée": entry,
            "SL": sl,
            "TP": tp,
            "Sortie": exit_p,
            "R:R Prévu": round(rr_prevu, 2) if rr_prevu is not None else None,
            "R:R Réalisé": round(rr_realise, 2) if rr_realise is not None else None,
            "PnL ($)": round(pnl_dollars, 2),
            "Capture_Avant_bytes": avant_bytes,
            "Capture_Avant_name": avant_name,
            "Capture_Apres_bytes": apres_bytes,
            "Capture_Apres_name": apres_name,
        }
        st.session_state.journal.append(new_trade)
        st.session_state.next_id += 1
        st.success("Trade enregistré ✅")

# --- AFFICHAGE DU DASHBOARD ---
if st.session_state.journal:
    df = pd.DataFrame(st.session_state.journal)

    # Convertir Date en datetime si besoin
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    # Calculs financiers
    df['Cumulative_PnL'] = df['PnL ($)'].cumsum()
    df['Current_Balance'] = st.session_state.capital_initial + df['Cumulative_PnL']
    # Gain en % par trade relatif au solde avant le trade
    df['Balance_Avant'] = df['Current_Balance'] - df['PnL ($)']
    df['Gain_Pct'] = df.apply(
        lambda r: (r['PnL ($)'] / r['Balance_Avant'] * 100) if r['Balance_Avant'] != 0 else 0,
        axis=1
    )

    # Drawdown
    df['Running_Max'] = df['Current_Balance'].cummax()
    df['Drawdown'] = (df['Current_Balance'] - df['Running_Max']) / df['Running_Max']
    max_drawdown = df['Drawdown'].min() if not df['Drawdown'].empty else 0.0

    # Métriques clés
    c1, c2, c3, c4, c5 = st.columns(5)
    final_balance = df['Current_Balance'].iloc[-1]
    total_pnl_pct = ((final_balance - st.session_state.capital_initial) / st.session_state.capital_initial) * 100
    total_trades = len(df)
    wins = df[df['PnL ($)'] > 0]
    losses = df[df['PnL ($)'] <= 0]
    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
    avg_win = wins['PnL ($)'].mean() if not wins.empty else 0
    avg_loss = abs(losses['PnL ($)'].mean()) if not losses.empty else 0
    payoff = (avg_win / avg_loss) if avg_loss != 0 else None
    expectancy = (win_rate/100) * avg_win - (1 - win_rate/100) * avg_loss

    c1.metric("Solde Actuel", f"{final_balance:.2f} $", delta=f"{df['PnL ($)'].iloc[-1]:.2f} $")
    c2.metric("Profit Global", f"{total_pnl_pct:.2f} %")
    c3.metric("R:R Moyen (prévu)", f"{df['R:R Prévu'].dropna().mean():.2f}" if not df['R:R Prévu'].dropna().empty else "N/A")
    c4.metric("Win Rate", f"{win_rate:.1f} %")
    c5.metric("Max Drawdown", f"{(max_drawdown*100):.2f} %")

    # Indicateurs supplémentaires
    st.markdown(f"- Trades: **{total_trades}**  •  Avg Win: **{avg_win:.2f} $**  •  Avg Loss: **{avg_loss:.2f} $**  •  Payoff: **{payoff:.2f}**" if payoff else f"- Trades: **{total_trades}**  •  Avg Win: **{avg_win:.2f} $**  •  Avg Loss: **{avg_loss:.2f} $**")
    st.markdown(f"- Expectancy (en $): **{expectancy:.2f}**")

    # GRAPHIQUE D'ÉVOLUTION
    st.subheader("📈 Évolution du Capital")
    st.line_chart(df.set_index('Date')['Current_Balance'])

    # TABLEAU RÉSUMÉ (sans colonnes binaires d'images)
    st.subheader("📋 Historique des Positions")
    display_df = df[[
        'ID', 'Date', 'Actif', 'Setup', 'Sens', 'Lot', 'Entrée', 'SL', 'TP', 'Sortie',
        'R:R Prévu', 'R:R Réalisé', 'PnL ($)', 'Gain_Pct', 'Current_Balance'
    ]].copy()
    # Formattage
    display_df['Date'] = display_df['Date'].dt.date
    display_df['Gain_Pct'] = display_df['Gain_Pct'].map(lambda x: f"{x:.2f} %")
    display_df['Current_Balance'] = display_df['Current_Balance'].map(lambda x: f"{x:.2f} $")

    st.dataframe(display_df.sort_values('Date'), use_container_width=True)

    # Détails par trade (affichage image + suppression)
    st.subheader("🔎 Détails des trades")
    for i, row in df.iterrows():
        with st.expander(f"Trade {row['ID']} — {row['Actif']} — {row['Date'].date()}"):
            cols = st.columns([2, 2, 1, 1])
            cols[0].write(f"**Entrée:** {row['Entrée']}")
            cols[0].write(f"**Sortie:** {row['Sortie']}")
            cols[1].write(f"**PnL ($):** {row['PnL ($)']:.2f}")
            cols[1].write(f"**R:R Réalisé:** {row['R:R Réalisé'] if pd.notna(row['R:R Réalisé']) else 'N/A'}")
            cols[2].write(f"**Lot:** {row['Lot']}")
            cols[3].write(f"**Setup:** {row['Setup']}")

            img_cols = st.columns(2)
            if pd.notna(row.get('Capture_Avant_bytes')):
                try:
                    img_cols[0].image(BytesIO(row['Capture_Avant_bytes']), caption=row.get('Capture_Avant_name') or "Avant")
                except Exception:
                    img_cols[0].write("Image avant non disponible")
            else:
                img_cols[0].write("Aucune capture AVANT")

            if pd.notna(row.get('Capture_Apres_bytes')):
                try:
                    img_cols[1].image(BytesIO(row['Capture_Apres_bytes']), caption=row.get('Capture_Apres_name') or "Après")
                except Exception:
                    img_cols[1].write("Image après non disponible")
            else:
                img_cols[1].write("Aucune capture APRÈS")

            # Bouton suppression
            if st.button("Supprimer ce trade", key=f"del_{int(row['ID'])}"):
                idx_to_remove = None
                for idx_j, t in enumerate(st.session_state.journal):
                    if t.get("ID") == int(row['ID']):
                        idx_to_remove = idx_j
                        break
                if idx_to_remove is not None:
                    st.session_state.journal.pop(idx_to_remove)
                    st.success(f"Trade {row['ID']} supprimé")
                    st.experimental_rerun()

    # EXPORT
    export_df = df.drop(columns=[
        'Capture_Avant_bytes', 'Capture_Avant_name', 'Capture_Apres_bytes', 'Capture_Apres_name',
        'Running_Max', 'Drawdown', 'Balance_Avant'
    ]).copy()
    export_df['Date'] = export_df['Date'].dt.date
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter le journal (CSV)", data=csv, file_name=f"journal_{datetime.date.today()}.csv")

else:
    st.info(f"Configuration : Capital initial de {st.session_state.capital_initial} $. Ajoutez un trade pour commencer.")
