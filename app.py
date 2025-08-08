import re
import streamlit as st
import pandas as pd
import pickle
import os
from io import BytesIO
import matplotlib.pyplot as plt
import copy

st.set_page_config(page_title="RAD-TEST", page_icon="🧪", layout="wide")

st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

COL_ITEM_CODE = "Item Code"
COL_QTA_RICHIESTA = "Requested_quantity"
COL_LOCATION = "Location"
COL_QUANTITA = "Quantità"
COL_ORDER = "Order Number"
TS_COL = "Timestamp"

RICHIESTE_FILE = "storico_richieste.csv"
STORICO_VERIFICHE_FILE = "storico_verifiche.csv"
STOCK_MANO_FILE = "stock_in_mano.pkl"
STOCK_RISERVA_FILE = "stock_in_riserva.pkl"

def carica_pickle_safe(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}

def salva_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)

def carica_csv_safe(path, cols):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if TS_COL in df.columns:
                df[TS_COL] = pd.to_datetime(df[TS_COL], errors="coerce")
            return df
        except Exception:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def salva_csv(path, df):
    df.to_csv(path, index=False)

def norma_item(x):
    if pd.isna(x):
        return ""
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x.is_integer():
            return str(int(x))
        return repr(x)
    s = str(x).strip()
    s = s.replace('\u200b', '').strip()
    if re.match(r'^\d+\.0+$', s):
        s = s.split('.')[0]
    return s.upper()

def try_int(v):
    if v is None:
        return 0
    try:
        if isinstance(v, int):
            return int(v)
        if isinstance(v, float):
            return int(round(v))
    except Exception:
        pass
    s = str(v).strip()
    if s == "":
        return 0
    s = s.replace(" ", "").replace("'", "")
    if "." in s and "," in s:
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        if last_dot > last_comma:
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')
    else:
        if "." in s and "," not in s:
            parts = s.split('.')
            if all(len(p) == 3 for p in parts[1:]):
                s = s.replace('.', '')
        if "," in s and "." not in s:
            parts = s.split(',')
            if all(len(p) == 3 for p in parts[1:]):
                s = s.replace(',', '')
            else:
                s = s.replace(',', '.')
    try:
        f = float(s)
        return int(round(f))
    except Exception:
        digits = re.sub(r'\D', '', s)
        if digits == "":
            return 0
        return int(digits)

def ensure_list_entry(v):
    if v is None:
        return []
    if isinstance(v, dict):
        return [v]
    if isinstance(v, (list, tuple)):
        return list(v)
    try:
        q = try_int(v)
        return [{"quantità": q, "location": ""}]
    except Exception:
        return []

def get_locations_and_total(stock_dict, key):
    entries = stock_dict.get(key)
    if entries is None:
        return [], 0
    if isinstance(entries, dict):
        entries_list = [entries]
    elif isinstance(entries, (list, tuple)):
        entries_list = list(entries)
    else:
        q = try_int(entries)
        return [("", q)], q
    max_loc = None
    max_qty = -1
    for rec in entries_list:
        if not isinstance(rec, dict):
            q = try_int(rec)
            loc = ""
        else:
            q = try_int(rec.get("quantità", 0))
            loc = str(rec.get("location", "") or "").strip()
        if q > max_qty:
            max_qty = q
            max_loc = loc
    if max_loc is None:
        return [], 0
    return [(max_loc, max_qty)], max_qty

def deep_copy_stock(s):
    return copy.deepcopy(s)

richiesta = carica_csv_safe(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL])
if COL_QTA_RICHIESTA in richiesta.columns:
    richiesta[COL_QTA_RICHIESTA] = richiesta[COL_QTA_RICHIESTA].apply(try_int)

stock_in_mano_raw = carica_pickle_safe(STOCK_MANO_FILE)
stock_in_riserva_raw = carica_pickle_safe(STOCK_RISERVA_FILE)

def normalize_stock(orig):
    out = {}
    if not isinstance(orig, dict):
        return {}
    for k, v in orig.items():
        nk = norma_item(k)
        out[nk] = ensure_list_entry(v)
    return out

stock_in_mano = normalize_stock(stock_in_mano_raw)
stock_in_riserva = normalize_stock(stock_in_riserva_raw)

if "pending_picks" not in st.session_state:
    st.session_state["pending_picks"] = []
if "confirm_disabled_for_order" not in st.session_state:
    st.session_state["confirm_disabled_for_order"] = {}
if "pre_pick_backup" not in st.session_state:
    st.session_state["pre_pick_backup"] = {}
if "confirm_prompt" not in st.session_state:
    st.session_state["confirm_prompt"] = {"type": None, "order": None}

page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Soglia alert stock in mano", min_value=1, max_value=10000, value=20)
show_debug = st.sidebar.checkbox("Mostra debug (prime chiavi)", False)
if show_debug:
    st.sidebar.write("Stock in mano (prime 20):", list(stock_in_mano.keys())[:20])
    st.sidebar.write("Stock in riserva (prime 20):", list(stock_in_riserva.keys())[:20])

if page == "Carica Stock In Mano":
    file_up = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if file_up:
        df = pd.read_excel(file_up)
        if COL_ITEM_CODE in df.columns:
            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item)
        stock_in_mano = {}
        for _, row in df.iterrows():
            code = norma_item(row.get(COL_ITEM_CODE))
            qty = try_int(row.get(COL_QUANTITA, 0))
            loc = str(row.get(COL_LOCATION, "") or "").strip()
            stock_in_mano[code] = [{"quantità": qty, "location": loc}]
        salva_pickle(STOCK_MANO_FILE, stock_in_mano)
        st.success("Stock in mano salvato.")

elif page == "Carica Stock Riserva":
    file_up = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if file_up:
        df = pd.read_excel(file_up)
        if COL_ITEM_CODE in df.columns:
            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item)
        stock_in_riserva = {}
        for _, row in df.iterrows():
            code = norma_item(row.get(COL_ITEM_CODE))
            qty = try_int(row.get(COL_QUANTITA, 0))
            loc = str(row.get(COL_LOCATION, "") or "").strip()
            stock_in_riserva[code] = [{"quantità": qty, "location": loc}]
        salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
        st.success("Stock in riserva salvato.")

elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")

    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        rename = {}
        for c in df.columns:
            lc = c.strip().lower()
            if lc in ["item code", "itemcode", "item number", "item_number", "item"]:
                rename[c] = COL_ITEM_CODE
            if lc in ["requested quantity", "requested_quantity", "requestedquantity", "quantità richiesta", "quantita richiesta"]:
                rename[c] = COL_QTA_RICHIESTA
            if lc in ["order number", "ordernumber", "order"]:
                rename[c] = COL_ORDER
        if rename:
            df.rename(columns=rename, inplace=True)
        if COL_ITEM_CODE in df.columns:
            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item)
        df[TS_COL] = pd.Timestamp.now()
        if COL_QTA_RICHIESTA in df.columns:
            df[COL_QTA_RICHIESTA] = df[COL_QTA_RICHIESTA].apply(try_int)
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            if COL_ORDER not in df.columns:
                df[COL_ORDER] = pd.NA
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Richieste aggiunte allo storico.")

    if not richiesta.empty:
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta[TS_COL] >= cutoff].copy()
        if COL_QTA_RICHIESTA in recenti.columns:
            recenti[COL_QTA_RICHIESTA] = recenti[COL_QTA_RICHIESTA].apply(try_int)
        agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        st.subheader("Totale richieste ultimi 30 giorni")
        st.dataframe(agg)

        ordini = richiesta[COL_ORDER].dropna().unique()
        ordine_sel = st.selectbox("Seleziona ordine", [""] + list(ordini))
        if ordine_sel:
            filtro = richiesta[richiesta[COL_ORDER] == ordine_sel].copy()
            if COL_QTA_RICHIESTA in filtro.columns:
                filtro[COL_QTA_RICHIESTA] = filtro[COL_QTA_RICHIESTA].apply(try_int)
            grouped = filtro.groupby(COL_ITEM_CODE, as_index=False)[COL_QTA_RICHIESTA].sum()
            st.dataframe(grouped)
