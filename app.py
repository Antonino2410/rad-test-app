import streamlit as st
import pandas as pd
import pickle
import os
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="RAD-TEST", page_icon="🧪", layout="wide")

# --- Titolo / logo ---
st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

# --- Costanti colonne ---
COL_ITEM_CODE = "Item Code"
COL_QTA_RICHIESTA = "Requested_quantity"
COL_LOCATION = "Location"
COL_QUANTITA = "Quantità"
COL_ORDER = "Order Number"
TIMESTAMP_COL = "Timestamp"

# --- File persistenti ---
RICHIESTE_FILE = "storico_richieste.csv"
STOCK_MANO_FILE = "stock_in_mano.pkl"
STOCK_RISERVA_FILE = "stock_in_riserva.pkl"

# ---------------------------
# Helper I/O e normalizzazione
# ---------------------------
def carica_pickle_safe(path):
    """Carica pickle (o {} se non esiste/errore). Normalizza stock_in_riserva come dict[item] -> list[dict]."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception:
        return {}
    # Normalizza: se è dict, assicurati che i valori siano liste quando si tratta riserva
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if isinstance(v, list):
                continue
            # converti singolo dict/numero in lista
            data[k] = [v]
    return data if isinstance(data, dict) else {}

def salva_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)

def carica_csv(path, default_cols):
    if os.path.exists(path):
        df = pd.read_csv(path)
        if TIMESTAMP_COL in df.columns:
            df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL], errors="coerce")
        return df
    return pd.DataFrame(columns=default_cols)

def salva_csv(path, df):
    df.to_csv(path, index=False)

# ---------------------------
# Funzione robusta estrazione quantità
# ---------------------------
def estrai_quantita_from_stock_mano(stock_in_mano, item):
    """
    Restituisce la quantità disponibile in stock_in_mano per 'item'.
    Gestisce diversi formati per backward-compatibility.
    """
    val = stock_in_mano.get(item, None)
    # dict con chiave 'quantità'
    if isinstance(val, dict):
        try:
            return int(val.get("quantità", 0))
        except Exception:
            return 0
    # lista di dict o valori
    if isinstance(val, (list, tuple)):
        total = 0
        for e in val:
            if isinstance(e, dict):
                try:
                    total += int(e.get("quantità", 0))
                except Exception:
                    continue
            elif isinstance(e, (int, float, str)):
                try:
                    total += int(e)
                except Exception:
                    continue
        return total
    # numero semplice
    if isinstance(val, (int, float)):
        return int(val)
    # fallback 0
    return 0

def estrai_location_from_stock_mano(stock_in_mano, item):
    """
    Cerca una location rappresentativa nello stock in mano per mostrare all'utente.
    """
    val = stock_in_mano.get(item, None)
    if isinstance(val, dict):
        return val.get("location", "")
    if isinstance(val, (list, tuple)) and len(val) > 0:
        first = val[0]
        if isinstance(first, dict):
            return first.get("location", "")
    return ""

# ---------------------------
# Caricamento persistente all'avvio
# ---------------------------
richiesta = carica_csv(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TIMESTAMP_COL])
stock_in_mano = carica_pickle_safe(STOCK_MANO_FILE)       # dict[item] -> {"quantità": x, "location": "A"}
stock_in_riserva = carica_pickle_safe(STOCK_RISERVA_FILE) # dict[item] -> [ {"quantità": x, "location": "X"}, ... ]

# sicurezza: se non dict, resetta
if not isinstance(stock_in_mano, dict):
    stock_in_mano = {}
if not isinstance(stock_in_riserva, dict):
    stock_in_riserva = {}

# ---------------------------
# Interfaccia (menu)
# ---------------------------
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Soglia alert stock in mano", min_value=1, max_value=10000, value=20)

# ---------------------------
# Pagina: carica stock in mano
# ---------------------------
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    up = st.file_uploader("Carica file Excel stock in mano (Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        # cerca mapping case-insensitive: prova a mappare colonne comuni
        df_cols = {c.strip(): c for c in df.columns}
        # controlla esattezza o prova a trovare alternative
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            pass
        else:
            # prova a rinominare 'Item Number' -> Item Code, 'Quantità' varianti -> Quantità
            rename_map = {}
            for c in df.columns:
                cl = c.strip().lower()
                if cl in ["item number", "item_number", "itemcode", "item code", "item"]:
                    rename_map[c] = COL_ITEM_CODE
                if cl in ["quantità", "quantita", "quantity", "qty"]:
                    rename_map[c] = COL_QUANTITA
                if cl in ["location", "loc"]:
                    rename_map[c] = COL_LOCATION
            if rename_map:
                df.rename(columns=rename_map, inplace=True)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = row[COL_ITEM_CODE]
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                stock_in_mano[item] = {"quantità": qta, "location": loc}
            salva_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("✅ Stock in mano aggiornato e salvato.")
        else:
            st.error(f"Il file deve contenere colonne per 'Item Code' e 'Quantità' (o equivalenti).")

# ---------------------------
# Pagina: carica stock riserva
# ---------------------------
elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    up = st.file_uploader("Carica file Excel stock riserva (Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        # tentativo di rinomina colonna come sopra
        rename_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl in ["item number", "item_number", "itemcode", "item code", "item"]:
                rename_map[c] = COL_ITEM_CODE
            if cl in ["quantità", "quantita", "quantity", "qty"]:
                rename_map[c] = COL_QUANTITA
            if cl in ["location", "loc"]:
                rename_map[c] = COL_LOCATION
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns and COL_LOCATION in df.columns:
            # raggruppa per item+location e somma quantità
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            # assicura che stock_in_riserva[item] sia lista
            for _, row in grouped.iterrows():
                item = row[COL_ITEM_CODE]
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                if not isinstance(stock_in_riserva.get(item), list):
                    stock_in_riserva[item] = []
                # aggiungi la location (non unisci duplicate: grouped già somma)
                stock_in_riserva[item].append({"quantità": qta, "location": loc})
            salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("✅ Stock riserva aggiornato e salvato.")
        else:
            st.error(f"Il file deve contenere colonne per 'Item Code', 'Quantità' e 'Location' (o equivalenti).")

# ---------------------------
# Pagina: Analisi richieste & suggerimenti # --------------------------- elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")

    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())

        # rinomina colonne comuni (fai match semplice)
        rename_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl in ["item number", "item_number", "itemcode", "item code", "item"]:
                rename_map[c] = COL_ITEM_CODE
            if cl in ["requested quantity", "requested_quantity", "requestedquantity", "requested quantity", "quantità richiesta", "quantita richiesta"]:
                rename_map[c] = COL_QTA_RICHIESTA
            if cl in ["order number", "ordernumber", "order"]:
                rename_map[c] = COL_ORDER
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        # Forza timestamp
        df[TIMESTAMP_COL] = pd.Timestamp.now()

        # Controllo colonne minime
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            if COL_ORDER not in df.columns:
                df[COL_ORDER] = pd.NA
            # append nello storico
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TIMESTAMP_COL]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("✅ Richieste aggiunte allo storico.")
        else:
            st.error(f"Il file richieste deve contenere almeno le colonne: '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    # Se abbiamo storico, mostra analisi e verifica ordine
    if not richiesta.empty:
        st.subheader("📈 Item più richiesti (ultimi 30 giorni)")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta[TIMESTAMP_COL] >= cutoff]
        agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        if not agg.empty:
            st.bar_chart(agg.head(10))
        else:
            st.info("Nessun dato richieste recenti.")

        st.subheader("🔍 Verifica disponibilità per Order Number")
        ordine_list = richiesta[COL_ORDER].dropna().unique().tolist()
        if not ordine_list:
            st.info("Nessun Order Number nello storico. Carica richieste con Order Number se vuoi usare questa funzione.")
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
                    mano_qta = estrai_quantita_from_stock_mano(stock_in_mano, item)
                    status = "✅ Disponibile"
                    reserve_locations_str = ""

                    if mano_qta < req_qta:
                        missing = req_qta - mano_qta
                        locs = []
                        total_reserve = 0
                        # cerca tutte le location INVENTORY nello stock di riserva
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
                            reserve_locations_str = "; ".join([f"{l['location']} ({l['quantità']})" for l in locs])
                            if total_reserve >= missing:
                                status = "⚠ Da riserva (coperto)"
                            else:
                                status = "❌ Non sufficiente (anche da riserva)"
                        else:
                            status = "❌ Non disponibile in riserva INVENTORY"

                    rows.append({
                        "Item Code": item,
                        "Requested Quantity": req_qta,
                        "Available in Stock": mano_qta,
                        "Reserve Locations (INVENTORY)": reserve_locations_str,
                        "Status": status
                    })

                result_df = pd.DataFrame(rows)
                # Mostra tabella
                st.dataframe(result_df)

                # Download Excel (dati puliti)
                buf = BytesIO()
                result_df.to_excel(buf, index=False)
                buf.seek(0)
                st.download_button(
                    label="📥 Scarica risultati (Excel)",
                    data=buf,
                    file_name=f"verifica_ordine_{ordine_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    else:
        st.info("Nessuno storico richieste: carica almeno un file richieste.")

# ---------------------------
# Sidebar: ricerca rapida
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Ricerca Item rapido") query = st.sidebar.text_input("Cerca Item Code") if query:
    q = query.strip()
    found = False
    if q in stock_in_mano:
        v = stock_in_mano[q]
        # estrai quantità robusta
        qta_mano = estrai_quantita_from_stock_mano(stock_in_mano, q)
        loc = estrai_location_from_stock_mano(stock_in_mano, q)
        st.sidebar.success(f"[In Mano] {qta_mano} @ {loc}")
        found = True
    if q in stock_in_riserva:
        lst = stock_in_riserva[q]
        lines = []
        for rec in lst:
            lines.append(f"{rec.get('location','')}: {rec.get('quantità',0)}")
        st.sidebar.info("[In Riserva]\n" + "\n".join(lines))
        found = True
    if not found:
        st.sidebar.warning("Item non trovato in nessuno stock.")
