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
# Funzioni I/O e normalizzazione
# ---------------------------
def norma_item_code(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def _normalize_res_entry(e):
    if isinstance(e, dict):
        q = e.get("quantità", e.get("Quantità", e.get("Quantita", 0)))
        loc = e.get("location", e.get("Location", e.get("location_name", "")))
        try:
            q = int(q)
        except Exception:
            q = 0
        loc = "" if pd.isna(loc) else str(loc).strip()
        return {"quantità": q, "location": loc}
    if isinstance(e, (int, float, str)):
        try:
            q = int(e)
        except Exception:
            q = 0
        return {"quantità": q, "location": ""}
    return {"quantità": 0, "location": ""}

def normalize_stock_in_riserva_dict(orig):
    new = {}
    if not isinstance(orig, dict):
        return {}
    for k, v in orig.items():
        nk = norma_item_code(k)
        items = []
        if isinstance(v, list):
            for e in v:
                items.append(_normalize_res_entry(e))
        elif isinstance(v, dict):
            items.append(_normalize_res_entry(v))
        elif isinstance(v, (int, float, str)):
            items.append(_normalize_res_entry(v))
        new[nk] = items
    return new

def normalize_stock_in_mano_dict(orig):
    new = {}
    if not isinstance(orig, dict):
        return {}
    for k, v in orig.items():
        nk = norma_item_code(k)
        if isinstance(v, dict):
            q = v.get("quantità", v.get("Quantità", v.get("Quantita",0)))
            loc = v.get("location", v.get("Location",""))
            try:
                q = int(q)
            except Exception:
                q = 0
            loc = "" if pd.isna(loc) else str(loc).strip()
            new[nk] = {"quantità": q, "location": loc}
        elif isinstance(v, (list, tuple)):
            total = 0
            loc = ""
            for e in v:
                if isinstance(e, dict):
                    q = e.get("quantità", e.get("Quantità", e.get("Quantita",0)))
                    try:
                        total += int(q)
                    except Exception:
                        pass
                    if not loc:
                        loc = e.get("location", e.get("Location",""))
                elif isinstance(e, (int, float, str)):
                    try:
                        total += int(e)
                    except Exception:
                        pass
            loc = "" if pd.isna(loc) else str(loc).strip()
            new[nk] = {"quantità": total, "location": loc}
        elif isinstance(v, (int, float, str)):
            try:
                q = int(v)
            except Exception:
                q = 0
            new[nk] = {"quantità": q, "location": ""}
        else:
            new[nk] = {"quantità": 0, "location": ""}
    return new

def carica_pickle_safe(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except Exception:
        return {}
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
    val = stock_in_mano.get(item, None)
    if isinstance(val, dict):
        try:
            return int(val.get("quantità", 0))
        except Exception:
            return 0
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
    if isinstance(val, (int, float)):
        return int(val)
    return 0

def estrai_location_from_stock_mano(stock_in_mano, item):
    val = stock_in_mano.get(item, None)
    if isinstance(val, dict):
        return val.get("location", "")
    if isinstance(val, (list, tuple)) and len(val) > 0:
        first = val[0]
        if isinstance(first, dict):
            return first.get("location", "")
    return ""

# ---------------------------
# Caricamento persistente all'avvio e normalizzazione
# ---------------------------
richiesta = carica_csv(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TIMESTAMP_COL])
_raw_stock_in_mano = carica_pickle_safe(STOCK_MANO_FILE)
_raw_stock_in_riserva = carica_pickle_safe(STOCK_RISERVA_FILE)

stock_in_mano = normalize_stock_in_mano_dict(_raw_stock_in_mano)
stock_in_riserva = normalize_stock_in_riserva_dict(_raw_stock_in_riserva)

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

# Debug toggle
show_keys = st.sidebar.checkbox("Mostra prime chiavi stock (debug)", value=False)

# ---------------------------
# Pagina: Carica Stock In Mano
# ---------------------------
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    up = st.file_uploader("Carica file Excel stock in mano (Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
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
                raw = row[COL_ITEM_CODE]
                item = norma_item_code(raw)
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                loc = "" if pd.isna(loc) else str(loc).strip()
                stock_in_mano[item] = {"quantità": qta, "location": loc}
            salva_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("✅ Stock in mano aggiornato e salvato.")
        else:
            st.error("Il file deve contenere colonne per 'Item Code' e 'Quantità' (o equivalenti).")

# ---------------------------
# Pagina: Carica Stock Riserva
# ---------------------------
elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    up = st.file_uploader("Carica file Excel stock riserva (Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
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
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            for _, row in grouped.iterrows():
                raw = row[COL_ITEM_CODE]
                item = norma_item_code(raw)
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                loc = "" if pd.isna(loc) else str(loc).strip()
                if not isinstance(stock_in_riserva.get(item), list):
                    stock_in_riserva[item] = []
                stock_in_riserva[item].append({"quantità": qta, "location": loc})
            stock_in_riserva = normalize_stock_in_riserva_dict(stock_in_riserva)
            salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("✅ Stock riserva aggiornato e salvato.")
        else:
            st.error("Il file deve contenere colonne per 'Item Code', 'Quantità' e 'Location' (o equivalenti).")

# ---------------------------
# Pagina: Analisi Richieste & Suggerimenti
# ---------------------------
elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")

    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())

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

        if COL_ITEM_CODE in df.columns:
            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item_code)

        df[TIMESTAMP_COL] = pd.Timestamp.now()

        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            if COL_ORDER not in df.columns:
                df[COL_ORDER] = pd.NA
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TIMESTAMP_COL]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("✅ Richieste aggiunte allo storico.")
        else:
            st.error(f"Il file richieste deve contenere almeno le colonne: '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    if not richiesta.empty:
        st.subheader("📈 Item più richiesti (ultimi 30 giorni)")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta[TIMESTAMP_COL] >= cutoff]
        try:
            agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        except Exception:
            agg = pd.Series(dtype=float)
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
                # raggruppa per Item Code sommando Requested_quantity
                filtro_grouped = filtro.groupby(COL_ITEM_CODE, as_index=False)[COL_QTA_RICHIESTA].sum()
                rows = []
                for _, r in filtro_grouped.iterrows():
                    item = r[COL_ITEM_CODE]
                    try:
                        req_qta = int(r[COL_QTA_RICHIESTA])
                    except Exception:
                        req_qta = 0
                    mano_qta = stock_in_mano.get(item, {}).get("quantità", 0)
                    if mano_qta is None:
                        mano_qta = 0
                    try:
                        mano_qta = int(mano_qta)
                    except Exception:
                        mano_qta = 0

                    status = "✅ Disponibile"
                    reserve_locations_str = ""

                    if mano_qta < req_qta:
                        missing = req_qta - mano_qta
                        locs = []
                        total_reserve = 0
                        for rec in stock_in_riserva.get(item, []):
                            loc_name = str(rec.get("location", "")).strip()
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

                result_df = pd.DataFrame(rows).sort_values("Item Code").reset_index(drop=True)
                st.dataframe(result_df)

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
st.sidebar.markdown("### 🔎 Ricerca Item rapido")

query = st.sidebar.text_input("Cerca Item Code")
if query:
    q = norma_item_code(query)
    found = False
    if q in stock_in_mano:
        qta_mano = stock_in_mano[q].get("quantità", 0)
        loc = stock_in_mano[q].get("location", "")
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

# debug output keys
if show_keys:
    st.sidebar.markdown("**Esempio chiavi caricate:**")
    st.sidebar.write("Stock in mano (prime 50):", list(stock_in_mano.keys())[:50])
    st.sidebar.write("Stock in riserva (prime 50):", list(stock_in_riserva.keys())[:50])
