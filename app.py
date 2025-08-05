import streamlit as st
import pandas as pd
import pickle
import os
import datetime
import matplotlib.pyplot as plt
from io import BytesIO  # ✅ per risolvere l'errore NameError

# --- CONFIG APP ---
st.set_page_config(page_title="RAD-TEST", page_icon="🧪")

st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

# --- COSTANTI ---
COL_ITEM_CODE = "Item Code"
COL_QTA_RICHIESTA = "Requested_quantity"
COL_LOCATION = "Location"
COL_QUANTITA = "Quantità"
COL_ORDER = "Order Number"

RICHIESTE_FILE = "storico_richieste.csv"
STOCK_MANO_FILE = "stock_in_mano.pkl"
STOCK_RISERVA_FILE = "stock_in_riserva.pkl"

# --- FUNZIONI ---
def carica_file_pickle(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    return {}

def salva_file_pickle(file_path, data):
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def carica_csv(file_path):
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"])

def salva_csv(file_path, df):
    df.to_csv(file_path, index=False)

# --- CARICAMENTO DATI ---
richiesta = carica_csv(RICHIESTE_FILE)
stock_in_mano = carica_file_pickle(STOCK_MANO_FILE)
stock_in_riserva = carica_file_pickle(STOCK_RISERVA_FILE)

# --- MENU ---
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Imposta soglia alert stock in mano", min_value=1, max_value=1000, value=20)

# --- PAGINA CARICA STOCK IN MANO ---
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    uploaded_file = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = row[COL_ITEM_CODE]
                qta = row.get(COL_QUANTITA, 0)
                loc = row.get(COL_LOCATION, "")
                stock_in_mano[item] = {"quantità": qta, "location": loc}
            salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("Stock in mano aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")

# --- PAGINA CARICA STOCK RISERVA ---
elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    uploaded_file = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = row[COL_ITEM_CODE]
                qta = row.get(COL_QUANTITA, 0)
                loc = row.get(COL_LOCATION, "")
                stock_in_riserva[item] = {"quantità": qta, "location": loc}
            salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("Stock in riserva aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")

# --- PAGINA ANALISI ---
elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica file Excel richieste", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Timestamp"] = pd.Timestamp.now()
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Storico richieste aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    if richiesta.empty:
        st.info("Nessun dato richieste disponibile.")
    else:
        st.subheader("📈 Item più richiesti (ultimo mese)")
        un_mese_fa = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta["Timestamp"] >= un_mese_fa]
        richieste_aggregate = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        st.write(richieste_aggregate.head(10))

        fig, ax = plt.subplots()
        richieste_aggregate.head(10).plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
        ax.set_ylabel('')
        st.pyplot(fig)

        st.subheader("⚠️ Alert stock basso")
        for item, _ in richieste_aggregate.items():
            qta_in_mano = stock_in_mano.get(item, {}).get("quantità", 0)
            loc_in_mano = stock_in_mano.get(item, {}).get("location", "non definita")
            if qta_in_mano < soglia:
                # Cerca suggerimenti dallo stock di riserva con INVENTORY
                suggerimenti = [
                    f"{info['quantità']} da {info['location']}"
                    for codice, info in stock_in_riserva.items()
                    if codice == item and "inventory" in info.get("location", "").lower()
                ]
                if suggerimenti:
                    st.warning(f"'{item}' sotto soglia! In magazzino: {qta_in_mano} (Location: {loc_in_mano}). "
                               f"Richiamare da: {', '.join(suggerimenti)}")
                else:
                    st.warning(f"'{item}' sotto soglia! In magazzino: {qta_in_mano} (Location: {loc_in_mano}). Nessuna scorta 'INVENTORY' trovata.")

# --- BARRA LATERALE RICERCA ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Ricerca Rapida Item")
query = st.sidebar.text_input("Cerca Item Code")
if query:
    trovato = False
    if query in stock_in_mano:
        val = stock_in_mano[query]
        st.sidebar.success(f"[In Mano] Quantità: {val.get('quantità')} | Location: {val.get('location')}")
        trovato = True
    if query in stock_in_riserva:
        val = stock_in_riserva[query]
        st.sidebar.info(f"[In Riserva] Quantità: {val.get('quantità')} | Location: {val.get('location')}")
        trovato = True
    if not trovato:
        st.sidebar.warning("Item non trovato.")

