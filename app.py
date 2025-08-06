import streamlit as st
import pandas as pd

st.set_page_config(page_title="RAD-TEST App", layout="wide")
st.title("📦 RAD-TEST – Gestione Stock e Ordini")

# Inizializzazione session state
if "stock_mano" not in st.session_state:
    st.session_state["stock_mano"] = pd.DataFrame()
if "stock_riserva" not in st.session_state:
    st.session_state["stock_riserva"] = pd.DataFrame()
if "ordini" not in st.session_state:
    st.session_state["ordini"] = pd.DataFrame()

# Upload file
st.sidebar.header("📁 Carica i tuoi file Excel")
stock_file = st.sidebar.file_uploader("📦 Stock in mano", type=["xlsx"])
riserva_file = st.sidebar.file_uploader("📦 Stock di riserva", type=["xlsx"])
ordini_file = st.sidebar.file_uploader("📄 Ordini (con Order Number)", type=["xlsx"])

if stock_file:
    st.session_state["stock_mano"] = pd.read_excel(stock_file)
if riserva_file:
    st.session_state["stock_riserva"] = pd.read_excel(riserva_file)
if ordini_file:
    st.session_state["ordini"] = pd.read_excel(ordini_file)

stock_df = st.session_state["stock_mano"]
riserva_df = st.session_state["stock_riserva"]
ordini_df = st.session_state["ordini"]

# Analisi
st.header("🔎 Analisi Disponibilità per Order Number")

if not stock_df.empty and not riserva_df.empty and not ordini_df.empty:

    # Pulizia nomi colonne
    ordini_df.columns = [col.strip() for col in ordini_df.columns]
    stock_df.columns = [col.strip() for col in stock_df.columns]
    riserva_df.columns = [col.strip() for col in riserva_df.columns]

    # Selezione Order Number
    unique_orders = ordini_df["Order Number"].dropna().unique()
    selected_order = st.selectbox("Seleziona un Order Number", unique_orders)

    if selected_order:
        ordine_corrente = ordini_df[ordini_df["Order Number"] == selected_order]
        suggerimenti = []

        for _, riga in ordine_corrente.iterrows():
            item = str(riga["Item Code"]).strip()
            richiesta = float(riga["Requested_quantity"])

            # Quantità totale in mano
            stock_totale = stock_df[stock_df["Item Code"] == item]["Quantity"].sum()

            if stock_totale >= richiesta:
                suggerimenti.append({
                    "Item Code": item,
                    "Richiesta": richiesta,
                    "Disponibile in mano": stock_totale,
                    "Status": "✅ Sufficiente in stock in mano",
                    "Prelievi da riserva": ""
                })
            else:
                mancante = richiesta - stock_totale
                suggeriti = []
                riserva_item = riserva_df[
                    (riserva_df["Item Code"] == item) &
                    (riserva_df["Location"].str.lower().str.contains("inventory"))
                ].sort_values("Quantity", ascending=False)

                for _, loc in riserva_item.iterrows():
                    if mancante <= 0:
                        break
                    qty = loc["Quantity"]
                    take = min(qty, mancante)
                    suggeriti.append(f"{take} da {loc['Location']}")
                    mancante -= take

                suggerimenti.append({
                    "Item Code": item,
                    "Richiesta": richiesta,
                    "Disponibile in mano": stock_totale,
                    "Status": "⚠️ Parziale",
                    "Prelievi da riserva": ", ".join(suggeriti) if suggeriti else "❌ Nessuna riserva trovata"
                })

        risultato = pd.DataFrame(suggerimenti)
        st.dataframe(risultato, use_container_width=True)

else:
    st.info("Carica tutti e tre i file Excel per eseguire l'analisi.")
