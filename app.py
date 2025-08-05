import streamlit as st
import pandas as pd
import pickle
import os
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
# --- Helper I/O robusti ---
def carica_pickle_safe(path):
    """Carica pickle con gestione errori; restituisce {} se non valido."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception:
        # se il file è corrotto o in formato non previsto, ignora e ritorna vuoto
        return {}
    # Normalizza il formato di stock_in_riserva: ogni valore deve essere una lista
    if isinstance(data, dict):
        for k, v in list(data.items()):
            # Se è già lista ok; se è dict o altro, converti in lista
            if isinstance(v, list):
                continue
            else:
                data[k] = [v]  # anche se v è dict o numero lo mettiamo in lista
    return data
def salva_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)
def carica_csv(path, columns_default):
    if os.path.exists(path):
        df = pd.read_csv(path)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df
    else:
        return pd.DataFrame(columns=columns_default)
def salva_csv(path, df):
    df.to_csv(path, index=False)
# --- Caricamento persistente (robusto) ---
richiesta = carica_csv(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"])
stock_in_mano = carica_pickle_safe(STOCK_MANO_FILE)  # expected: dict[item] -> {"quantità": int, "location": str}
stock_in_riserva = carica_pickle_safe(STOCK_RISERVA_FILE)  # expected: dict[item] -> list of {"quantità": int, "location": str}
# Assicuriamoci che stock_in_mano sia dict (se venisse caricato altro, lo resettiamo)
if not isinstance(stock_in_mano, dict):
    stock_in_mano = {}
if not isinstance(stock_in_riserva, dict):
    stock_in_riserva = {}
# --- Interfaccia ---
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Imposta soglia alert stock in mano", min_value=1, max_value=10000, value=20)
# --- Pagina: carica stock in mano ---
if page == "Carica Stock In Mano":
    st.title(":posta_ricevuta: Carica Stock Magazzino In Mano")
    up = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            # aggiorna/replace totale: potresti voler invece unire; qui sostituiamo i valori per item
            for _, row in df.iterrows():
                item = row[COL_ITEM_CODE]
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                stock_in_mano[item] = {"quantità": qta, "location": loc}
            salva_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success(":segno_spunta_bianco: Stock in mano aggiornato e salvato.")
        else:
            st.error(f"Il file deve contenere le colonne: '{COL_ITEM_CODE}' e '{COL_QUANTITA}'")
# --- Pagina: carica stock riserva ---
elif page == "Carica Stock Riserva":
    st.title(":posta_ricevuta: Carica Stock Magazzino Riserva")
    up = st.file_uploader("Carica file Excel stock riserva", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns and COL_LOCATION in df.columns:
            # Raggruppa per Item + Location per sommare quantità
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            # Assicuriamoci che per ogni item abbiamo una lista
            for _, row in grouped.iterrows():
                item = row[COL_ITEM_CODE]
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                # se key non presente, inizializza con lista
                if not isinstance(stock_in_riserva.get(item), list):
                    stock_in_riserva[item] = []
                # aggiungi la location con quantità
                stock_in_riserva[item].append({"quantità": qta, "location": loc})
            salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success(":segno_spunta_bianco: Stock riserva aggiornato e salvato.")
        else:
            st.error(f"Il file deve contenere le colonne: '{COL_ITEM_CODE}', '{COL_QUANTITA}', '{COL_LOCATION}'")
# --- Pagina: analisi richieste e suggerimenti ---
elif page == "Analisi Richieste & Suggerimenti":
    st.title(":grafico_a_barre: Analisi Richieste & Suggerimenti")
    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        # Cerca di rinominare automaticamente alcune intestazioni comuni (opzionale)
        cols_map = {c: c.strip() for c in df.columns}
        df.rename(columns=cols_map, inplace=True)
        # Forza presenza colonne richieste
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            # Se manca Order Number, aggiungilo (possibile)
            if COL_ORDER not in df.columns:
                df[COL_ORDER] = df.get(COL_ORDER, pd.NA)
            # aggiungi timestamp
            df["Timestamp"] = pd.Timestamp.now()
            # concat nello storico
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success(":segno_spunta_bianco: Richieste aggiunte allo storico.")
        else:
            st.error(f"Il file richieste deve contenere almeno le colonne: '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")
    if richiesta.empty:
        st.info("Nessuno storico richieste. Carica almeno un file richieste.")
    else:
        st.subheader(":grafico_con_tendenza_in_aumento: Item più richiesti (ultimo mese)")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta["Timestamp"] >= cutoff]
        agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        st.bar_chart(agg.head(10))
        st.subheader(":lente: Verifica disponibilità per Order Number")
        ordine_list = richiesta[COL_ORDER].dropna().unique().tolist()
        if not ordine_list:
            st.info("Nessun Order Number nello storico (carica richieste con Order Number).")
        else:
            ordine_sel = st.selectbox("Seleziona Order Number", ordine_list)
            if st.button("Verifica ordine"):
                filtro = richiesta[richiesta[COL_ORDER] == ordine_sel]
                rows = []
                for _, r in filtro.iterrows():
                    item = r[COL_ITEM_CODE]
                    try:
                        req_qta = int(r[COL_QTA_RICHIESTA])
                    except Exception:
                        req_qta = 0
                    mano_qta = stock_in_mano.get(item, {}).get("quantità", 0)
                    status = ":segno_spunta_bianco: Disponibile"
                    reserve_locations_str = ""
                    if mano_qta < req_qta:
                        # quantità mancante
                        mancante = req_qta - mano_qta
                        # cerca tutte le location INVENTORY nello stock di riserva
                        locs = []
                        total_reserve = 0
                        for rec in stock_in_riserva.get(item, []):
                            loc_name = str(rec.get("location", ""))
                            if "inventory" in loc_name.lower():
                                try:
                                    q = int(rec.get("quantità", 0))
                                except Exception:
                                    q = 0
                                if q > 0:
                                    locs.append({"location": loc_name, "quantità": q})
                                    total_reserve += q
                        if locs:
                            # formatta lista location -> "LocA (10); LocB (5)"
                            reserve_locations_str = "; ".join([f"{l['location']} ({l['quantità']})" for l in locs])
                            if total_reserve >= mancante:
                                status = ":avviso: Da riserva (coperto)"
                            else:
                                status = ":x: Non sufficiente (anche da riserva)"
                        else:
                            status = ":x: Non disponibile in riserva INVENTORY"
                    # salva riga
                    rows.append({
                        "Item Code": item,
                        "Requested Quantity": req_qta,
                        "Available in Stock": mano_qta,
                        "Reserve Locations (INVENTORY)": reserve_locations_str,
                        "Status": status
                    })
                result_df = pd.DataFrame(rows)
                # Mostra con st.dataframe
                st.dataframe(result_df)
                # permetti download in excel (solo dati)
                buf = BytesIO()
                result_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button(
                    label=":posta_ricevuta: Scarica risultati (Excel)",
                    data=buf,
                    file_name=f"verifica_ordine_{ordine_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
# --- Sidebar: ricerca rapida ---
st.sidebar.markdown("---")
st.sidebar.markdown("### :lente_a_destra: Ricerca Item rapido")
query = st.sidebar.text_input("Cerca Item Code")
if query:
    query = query.strip()
    found = False
    if query in stock_in_mano:
        v = stock_in_mano[query]
        st.sidebar.success(f"[In Mano] {v.get('quantità',0)} @ {v.get('location','')}")
        found = True
    if query in stock_in_riserva:
        lst = stock_in_riserva[query]
        # mostro tutte le location di riserva
        lines = []
        for rec in lst:
            lines.append(f"{rec.get('location','')}: {rec.get('quantità',0)}")
        st.sidebar.info("[In Riserva]\n" + "\n".join(lines))
        found = True
    if not found:
        st.sidebar.warning("Item non trovato in nessuno stock.")
