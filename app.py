import streamlit as st
import pandas as pd
import pickle
import os
import datetime
import matplotlib.pyplot as plt
from io import BytesIO
st.set_page_config(page_title="RAD-TEST", page_icon=":provetta:", layout="wide")
# --- Logo e titolo ---
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
# --- Caricamento dati persistenti ---
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
# --- Pagina: Carica Stock In Mano ---
if page == "Carica Stock In Mano":
    st.title(":posta_ricevuta: Carica Stock Magazzino In Mano")
    uploaded_file = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                stock_in_mano[row[COL_ITEM_CODE]] = {
                    "quantità": row.get(COL_QUANTITA, 0),
                    "location": row.get(COL_LOCATION, "")
                }
            salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("Stock in mano aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")
# --- Pagina: Carica Stock Riserva ---
elif page == "Carica Stock Riserva":
    st.title(":posta_ricevuta: Carica Stock Magazzino Riserva")
    uploaded_file = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            for _, row in grouped.iterrows():
                stock_in_riserva.setdefault(row[COL_ITEM_CODE], []).append({
                    "quantità": row[COL_QUANTITA],
                    "location": row[COL_LOCATION]
                })
            salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("Stock in riserva aggiornato!")
        else:
            st.error(f"Il file deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")
# --- Pagina: Analisi ---
elif page == "Analisi Richieste & Suggerimenti":
    st.title(":grafico_a_barre: Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica file Excel richieste", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Timestamp"] = pd.Timestamp.now()
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            richiesta = pd.concat(
                [richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]],
                ignore_index=True
            )
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Storico richieste aggiornato!")
        else:
            st.error(f"Il file deve contenere '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")
    if not richiesta.empty:
        st.subheader(":grafico_con_tendenza_in_aumento: Item più richiesti (ultimo mese)")
        un_mese_fa = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta["Timestamp"] >= un_mese_fa]
        richieste_agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        st.bar_chart(richieste_agg.head(10))
        st.subheader(":lente: Verifica disponibilità per ordine")
        ordine_sel = st.selectbox("Seleziona Order Number", richiesta[COL_ORDER].dropna().unique())
        if st.button("Verifica ordine"):
            filtro = richiesta[richiesta[COL_ORDER] == ordine_sel]
            risultati = []
            for _, riga in filtro.iterrows():
                item = riga[COL_ITEM_CODE]
                req_qta = riga[COL_QTA_RICHIESTA]
                stock_qta = stock_in_mano.get(item, {}).get("quantità", 0)
                status = ":segno_spunta_bianco: Disponibile"
                reserve_info = ""
                if stock_qta < req_qta:
                    mancante = req_qta - stock_qta
                    locs = []
                    for ris in stock_in_riserva.get(item, []):
                        if "inventory" in str(ris["location"]).lower():
                            locs.append(f"{ris['location']} ({ris['quantità']})")
                    if locs:
                        reserve_info = "; ".join(locs)
                        total_reserve = sum([int(x.split("(")[1].replace(")", "")) for x in locs])
                        status = "⚠ Da riserva" if total_reserve >= mancante else ":x: Non sufficiente"
                    else:
                        status = ":x: Non disponibile"
                risultati.append({
                    "Item Code": item,
                    "Requested Quantity": req_qta,
                    "Available in Stock": stock_qta,
                    "Reserve Locations": reserve_info,
                    "Status": status
                })
            df_result = pd.DataFrame(risultati)
            st.dataframe(df_result)
            # Download Excel
            buffer = BytesIO()
            df_result.to_excel(buffer, index=False)
            st.download_button(
                label=":posta_ricevuta: Scarica risultati in Excel",
                data=buffer,
                file_name=f"ordine_{ordine_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
