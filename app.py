import streamlit as st
import pandas as pd
import pickle
import os
import matplotlib.pyplot as plt
st.set_page_config(page_title="RAD-TEST", page_icon=":provetta:")
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
stock_in_mano = carica_file_pickle(STOCK_MANO_FILE)
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
    st.title(":posta_ricevuta: Carica Stock Magazzino In Mano")
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
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")
elif page == "Carica Stock Riserva":
    st.title(":posta_ricevuta: Carica Stock Magazzino Riserva")
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
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")
# --- Analisi e Suggerimenti ---
elif page == "Analisi Richieste & Suggerimenti":
    st.title(":grafico_a_barre: Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica file Excel richieste", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Timestamp"] = pd.Timestamp.now()
        if all(col in df.columns for col in [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER]):
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Storico richieste aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno le colonne '{COL_ITEM_CODE}', '{COL_QTA_RICHIESTA}' e '{COL_ORDER}'.")
    if richiesta.empty:
        st.info("Nessun dato richieste disponibile.")
    else:
        st.subheader(":grafico_con_tendenza_in_aumento: Item più richiesti (ultimo mese)")
        un_mese_fa = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta["Timestamp"] >= un_mese_fa]
        richieste_aggregate = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        st.write(richieste_aggregate.head(10))
        fig, ax = plt.subplots()
        richieste_aggregate.head(10).plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
        ax.set_ylabel('')
        st.pyplot(fig)
        st.subheader(":avviso: Alert stock basso")
        for item, qta_richiesta in richieste_aggregate.items():
            qta_in_mano = stock_in_mano.get(item, {}).get("quantità", 0)
            loc = stock_in_mano.get(item, {}).get("location", "non definita")
            if qta_in_mano < soglia:
                st.warning(f"'{item}' è sotto soglia! In magazzino: {qta_in_mano}. Richiamare da: {loc}")
        st.markdown("## 🔍 Verifica disponibilità per ordine specifico")
        ordine_unico = st.selectbox("Seleziona un Order Number", richiesta[COL_ORDER].dropna().unique())
        if st.button("Verifica disponibilità per ordine"):
            filtro_ordine = richiesta[richiesta[COL_ORDER] == ordine_unico]
            for _, riga in filtro_ordine.iterrows():
                item = riga[COL_ITEM_CODE]
                richiesta_qta = riga[COL_QTA_RICHIESTA]
                qta_stock = stock_in_mano.get(item, {}).get("quantità", 0)
                loc_stock = stock_in_mano.get(item, {}).get("location", "non definita")
                if qta_stock >= richiesta_qta:
                    st.success(f":segno_spunta_bianco: '{item}' disponibile - Richiesta: {richiesta_qta}, In stock: {qta_stock} (Location: {loc_stock})")
                else:
                    mancante = richiesta_qta - qta_stock
                    suggerimenti = []
                    for chiave_item, info in stock_in_riserva.items():
                        if chiave_item == item and "inventory" in info.get("location", "").lower():
                            riserva_qta = info.get("quantità", 0)
                            if riserva_qta > 0:
                                qta_da_prendere = min(mancante, riserva_qta)
                                suggerimenti.append(f"- {qta_da_prendere} da {info['location']}")
                    if suggerimenti:
                        st.warning(f":avviso: '{item}' mancano {mancante} pezzi.
Suggerimenti:
" + "\n".join(suggerimenti))
                    else:
                        st.error(f":x: '{item}' non disponibile in stock né in magazzini con 'inventory'.")
# --- Barra laterale: Ricerca Stock ---
st.sidebar.markdown("---")
st.sidebar.markdown("### :lente_a_destra: Ricerca Item")
query = st.sidebar.text_input("Cerca Item Code")
if query:
    query = query.strip()
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
        st.sidebar.warning("Item non trovato in nessuno stock.")
