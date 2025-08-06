import streamlit as st
import pandas as pd
import pickle
import os
import datetime
import matplotlib.pyplot as plt

# ---------------- CONFIGURAZIONE ----------------
st.set_page_config(page_title="RAD-TEST", page_icon="🧪")

st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

# ---------------- COSTANTI ----------------
COL_ITEM_CODE = "Item Code"
COL_QTA_RICHIESTA = "Requested_quantity"
COL_LOCATION = "Location"
COL_QUANTITA = "Quantità"
COL_ORDER = "Order Number"

RICHIESTE_FILE = "storico_richieste.csv"
STOCK_MANO_FILE = "stock_in_mano.pkl"
STOCK_RISERVA_FILE = "stock_in_riserva.pkl"

# ---------------- FUNZIONI ----------------
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

# ---------------- CARICAMENTO DATI ----------------
richiesta = carica_csv(RICHIESTE_FILE)
stock_in_mano = carica_file_pickle(STOCK_MANO_FILE)
stock_in_riserva = carica_file_pickle(STOCK_RISERVA_FILE)

# Variabile di stato per prelievi temporanei
if "prelievo_temp" not in st.session_state:
    st.session_state.prelievo_temp = []

# ---------------- MENU ----------------
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Imposta soglia alert stock in mano", min_value=1, max_value=1000, value=20)

# ---------------- PAGINA STOCK IN MANO ----------------
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    uploaded_file = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        for _, row in df.iterrows():
            item = str(row[COL_ITEM_CODE])
            qta = row.get(COL_QUANTITA, 0)
            loc = row.get(COL_LOCATION, "")
            if item in stock_in_mano:
                stock_in_mano[item].append({"quantità": qta, "location": loc})
            else:
                stock_in_mano[item] = [{"quantità": qta, "location": loc}]
        salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
        st.success("Stock in mano aggiornato!")

# ---------------- PAGINA STOCK RISERVA ----------------
elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    uploaded_file = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        for _, row in df.iterrows():
            item = str(row[COL_ITEM_CODE])
            qta = row.get(COL_QUANTITA, 0)
            loc = row.get(COL_LOCATION, "")
            if item in stock_in_riserva:
                stock_in_riserva[item].append({"quantità": qta, "location": loc})
            else:
                stock_in_riserva[item] = [{"quantità": qta, "location": loc}]
        salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
        st.success("Stock in riserva aggiornato!")

# ---------------- PAGINA ANALISI ----------------
elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")
    
    uploaded_file = st.file_uploader("Carica file Excel richieste", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Timestamp"] = pd.Timestamp.now()
        richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]], ignore_index=True)
        salva_csv(RICHIESTE_FILE, richiesta)
        st.success("Storico richieste aggiornato!")

    # Alert stock basso in menù a tendina
    with st.expander("⚠️ Alert stock basso"):
        for item, entries in stock_in_mano.items():
            totale = sum(e["quantità"] for e in entries)
            if totale < soglia:
                locazioni_riserva = [f"{e['location']} ({e['quantità']})" for e in stock_in_riserva.get(item, []) if "inventory" in e["location"].lower()]
                if locazioni_riserva:
                    st.warning(f"{item} sotto soglia ({totale}) - Preleva da: {', '.join(locazioni_riserva)}")
                else:
                    st.warning(f"{item} sotto soglia ({totale}) - Nessuna riserva con 'INVENTORY' trovata")

    # Verifica per ordine specifico
    if not richiesta.empty:
        ordine_unico = st.selectbox("Seleziona un Order Number", richiesta["Order Number"].dropna().unique())
        if st.button("Verifica disponibilità per ordine"):
            st.session_state.prelievo_temp.clear()
            filtro_ordine = richiesta[richiesta["Order Number"] == ordine_unico]
            for _, riga in filtro_ordine.iterrows():
                item = str(riga[COL_ITEM_CODE])
                richiesta_qta = riga[COL_QTA_RICHIESTA]
                totale_in_mano = sum(e["quantità"] for e in stock_in_mano.get(item, []))

                if totale_in_mano >= richiesta_qta:
                    st.write(f"✅ {item} disponibile - Richiesta: {richiesta_qta}, In stock: {totale_in_mano}")
                    st.session_state.prelievo_temp.append((item, richiesta_qta, "in_mano"))
                else:
                    mancante = richiesta_qta - totale_in_mano
                    suggerimenti = []
                    for e in stock_in_riserva.get(item, []):
                        if "inventory" in e["location"].lower():
                            suggerimenti.append(f"{e['location']} ({e['quantità']})")
                    if suggerimenti:
                        st.write(f"⚠️ {item} mancano {mancante} pezzi. Preleva da: {', '.join(suggerimenti)}")
                        st.session_state.prelievo_temp.append((item, mancante, "riserva"))
                    else:
                        st.write(f"❌ {item} non disponibile in stock né in riserva con 'INVENTORY'.")

        # Pulsante conferma prelievo
        if st.session_state.prelievo_temp:
            if st.button("✅ Conferma prelievo"):
                for item, qta, tipo in st.session_state.prelievo_temp:
                    if tipo == "in_mano":
                        for e in stock_in_mano[item]:
                            if qta <= 0:
                                break
                            preleva = min(qta, e["quantità"])
                            e["quantità"] -= preleva
                            qta -= preleva
                    elif tipo == "riserva":
                        for e in stock_in_riserva[item]:
                            if "inventory" in e["location"].lower():
                                if qta <= 0:
                                    break
                                preleva = min(qta, e["quantità"])
                                e["quantità"] -= preleva
                                qta -= preleva
                salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
                salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
                st.success("Quantità aggiornate!")

            if st.button("❌ Annulla prelievo"):
                st.session_state.prelievo_temp.clear()
                st.info("Prelievo annullato.")

# ---------------- RICERCA RAPIDA ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Ricerca Item")
query = st.sidebar.text_input("Cerca Item Code")
if query:
    query = query.strip()
    trovato = False
    if query in stock_in_mano:
        totale = sum(e["quantità"] for e in stock_in_mano[query])
        locations = ", ".join(f"{e['location']} ({e['quantità']})" for e in stock_in_mano[query])
        st.sidebar.success(f"[In Mano] Totale: {totale} | {locations}")
        trovato = True
    if query in stock_in_riserva:
        totale = sum(e["quantità"] for e in stock_in_riserva[query])
        locations = ", ".join(f"{e['location']} ({e['quantità']})" for e in stock_in_riserva[query])
        st.sidebar.info(f"[In Riserva] Totale: {totale} | {locations}")
        trovato = True
    if not trovato:
        st.sidebar.warning("Item non trovato.")
