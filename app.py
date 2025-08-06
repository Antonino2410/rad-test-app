import streamlit as st
import pandas as pd
import pickle
import os
import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="RAD-TEST", page_icon="🧪")

st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

# --- Costanti ---
COL_ITEM_CODE = "Item Code"
COL_QTA_RICHIESTA = "Requested_quantity"
COL_LOCATION = "Location"
COL_QUANTITA = "Quantità"
COL_ORDER = "Order Number"

RICHIESTE_FILE = "storico_richieste.csv"
STOCK_MANO_FILE = "stock_in_mano.pkl"
STOCK_RISERVA_FILE = "stock_in_riserva.pkl"

# --- Funzioni utili ---
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

# --- Caricamento dati ---
richiesta = carica_csv(RICHIESTE_FILE)
stock_in_mano = carica_file_pickle(STOCK_MANO_FILE)  # dict: {item: [{"quantità": x, "location": y}, ...]}
stock_in_riserva = carica_file_pickle(STOCK_RISERVA_FILE)

# --- Interfaccia ---
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Imposta soglia alert stock in mano", min_value=1, max_value=1000, value=20)

# --- Caricamento Stock ---
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    uploaded_file = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = str(row[COL_ITEM_CODE])
                qta = row.get(COL_QUANTITA, 0)
                loc = row.get(COL_LOCATION, "")

                if item not in stock_in_mano:
                    stock_in_mano[item] = []
                stock_in_mano[item].append({"quantità": qta, "location": loc})

            salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("Stock in mano aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")

elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    uploaded_file = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = str(row[COL_ITEM_CODE])
                qta = row.get(COL_QUANTITA, 0)
                loc = row.get(COL_LOCATION, "")

                if item not in stock_in_riserva:
                    stock_in_riserva[item] = []
                stock_in_riserva[item].append({"quantità": qta, "location": loc})

            salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("Stock in riserva aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")

# --- Analisi e Suggerimenti ---
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
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    if not richiesta.empty:
        # Verifica disponibilità per Order Number
        st.markdown("## 🔍 Verifica disponibilità per ordine specifico")
        if COL_ORDER in richiesta.columns:
            ordine_unico = st.selectbox("Seleziona un Order Number", richiesta[COL_ORDER].dropna().unique())
            if st.button("Verifica disponibilità per ordine"):
                filtro_ordine = richiesta[richiesta[COL_ORDER] == ordine_unico]
                for _, riga in filtro_ordine.iterrows():
                    item = str(riga[COL_ITEM_CODE])
                    richiesta_qta = riga[COL_QTA_RICHIESTA]

                    qta_stock_mano = sum([x["quantità"] for x in stock_in_mano.get(item, [])])
                    if qta_stock_mano >= richiesta_qta:
                        st.write(f"✅ {item} disponibile ({qta_stock_mano}/{richiesta_qta})")
                    else:
                        mancante = richiesta_qta - qta_stock_mano
                        st.warning(f"⚠️ {item} mancano {mancante} pezzi. Suggerimenti da magazzino di riserva:")

                        # Mostra tutte le location INVENTORY con quantità
                        if item in stock_in_riserva:
                            for entry in stock_in_riserva[item]:
                                if "inventory" in entry["location"].lower() and entry["quant]()
