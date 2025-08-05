import streamlit as st
import pandas as pd
import pickle
import os
from io import BytesIO
import matplotlib.pyplot as plt
import datetime

# ---------------- Config ----------------
st.set_page_config(page_title="RAD-TEST", page_icon="🧪", layout="wide")

st.markdown("""
    <div style="display:flex; align-items:center; gap:15px;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Crystal_Clear_app_ksystemlog.svg/120px-Crystal_Clear_app_ksystemlog.svg.png" width="50">
        <h1 style="margin:0; color:#004080;">RAD-TEST</h1>
    </div>
""", unsafe_allow_html=True)

# ---------------- Constants ----------------
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

# ---------------- Helpers I/O ----------------
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

# ---------------- Normalization ----------------
def norma_item(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()

def try_int(v):
    try:
        return int(v)
    except Exception:
        return 0

# ---------------- Load persistent data ----------------
richiesta = carica_csv_safe(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL])
stock_in_mano_raw = carica_pickle_safe(STOCK_MANO_FILE)
stock_in_riserva_raw = carica_pickle_safe(STOCK_RISERVA_FILE)

# normalize keys to uppercase trimmed strings for consistency
def normalize_stock_keys(orig):
    out = {}
    if not isinstance(orig, dict):
        return {}
    for k, v in orig.items():
        nk = norma_item(k)
        out[nk] = v
    return out

stock_in_mano = normalize_stock_keys(stock_in_mano_raw)
stock_in_riserva = normalize_stock_keys(stock_in_riserva_raw)

# ---------------- UI - Sidebar global ----------------
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

# ---------------- Page: Carica Stock In Mano ----------------
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock - IN MANO")
    up = st.file_uploader("Carica file Excel stock in mano (colonne: Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        # try to rename common variants
        rename = {}
        for c in df.columns:
            lc = c.strip().lower()
            if lc in ["item code", "itemcode", "item number", "item_number", "item"]:
                rename[c] = COL_ITEM_CODE
            if lc in ["quantità", "quantita", "quantity", "qty"]:
                rename[c] = COL_QUANTITA
            if lc in ["location", "loc"]:
                rename[c] = COL_LOCATION
        if rename:
            df.rename(columns=rename, inplace=True)

        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, r in df.iterrows():
                key = norma_item(r[COL_ITEM_CODE])
                q = try_int(r.get(COL_QUANTITA, 0))
                loc = r.get(COL_LOCATION, "") or ""
                # store as dict for each key; if multiple lines for same item, keep last (or customize)
                stock_in_mano[key] = {"quantità": q, "location": str(loc).strip()}
            salva_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("Stock in mano salvato correttamente.")
        else:
            st.error(f"File non contiene colonne richieste: '{COL_ITEM_CODE}', '{COL_QUANTITA}'.")

# ---------------- Page: Carica Stock Riserva ----------------
elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock - RISERVA")
    up = st.file_uploader("Carica file Excel stock riserva (Item Code, Quantità, Location)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
        rename = {}
        for c in df.columns:
            lc = c.strip().lower()
            if lc in ["item code", "itemcode", "item number", "item_number", "item"]:
                rename[c] = COL_ITEM_CODE
            if lc in ["quantità", "quantita", "quantity", "qty"]:
                rename[c] = COL_QUANTITA
            if lc in ["location", "loc"]:
                rename[c] = COL_LOCATION
        if rename:
            df.rename(columns=rename, inplace=True)

        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns and COL_LOCATION in df.columns:
            # group by item+location sum quantities
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            for _, r in grouped.iterrows():
                key = norma_item(r[COL_ITEM_CODE])
                q = try_int(r[COL_QUANTITA])
                loc = str(r[COL_LOCATION]).strip()
                existing = stock_in_riserva.get(key)
                entry = {"quantità": q, "location": loc}
                if existing is None:
                    stock_in_riserva[key] = [entry]
                elif isinstance(existing, list):
                    existing.append(entry)
                    stock_in_riserva[key] = existing
                elif isinstance(existing, dict):
                    stock_in_riserva[key] = [existing, entry]
                else:
                    stock_in_riserva[key] = [entry]
            salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("Stock riserva salvato correttamente.")
        else:
            st.error(f"File non contiene colonne richieste: '{COL_ITEM_CODE}', '{COL_QUANTITA}', '{COL_LOCATION}'.")

# ---------------- Page: Analisi Richieste & Suggerimenti ----------------
elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")

    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])
    if up:
        df = pd.read_excel(up)
        st.write("Colonne trovate:", df.columns.tolist())
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

        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            if COL_ORDER not in df.columns:
                df[COL_ORDER] = pd.NA
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Richieste aggiunte allo storico.")
        else:
            st.error(f"Il file richieste deve contenere almeno '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    if richiesta.empty:
        st.info("Nessuno storico richieste presente. Carica almeno un file richieste.")
    else:
        # aggregate last 30 days
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta[TS_COL] >= cutoff]
        try:
            agg = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        except Exception:
            agg = pd.Series(dtype=float)

        st.subheader("📈 Item più richiesti (ultimi 30 giorni)")
        if not agg.empty:
            st.write(agg.head(10))
            fig, ax = plt.subplots()
            agg.head(10).plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
            ax.set_ylabel('')
            st.pyplot(fig)
        else:
            st.info("Nessun dato richieste recenti.")

        # --- Alert stock basso expander (with inventory suggestions) ---
        with st.expander("⚠️ Alert stock basso"):
            alert_rows = []
            for item, tot_req in agg.items():
                key = norma_item(item)
                mano_rec = stock_in_mano.get(key, {})
                # quantity in mano
                q_mano = 0
                loc_mano = "non definita"
                if isinstance(mano_rec, dict):
                    q_mano = try_int(mano_rec.get("quantità", 0))
                    loc_mano = mano_rec.get("location", "") or "non definita"
                elif isinstance(mano_rec, (list, tuple)):
                    total = 0
                    loc_candidate = ""
                    for rec in mano_rec:
                        if isinstance(rec, dict):
                            total += try_int(rec.get("quantità", 0))
                            if not loc_candidate:
                                loc_candidate = rec.get("location", "")
                    q_mano = total
                    loc_mano = loc_candidate or "non definita"

                if q_mano < soglia:
                    # find reserve locations with 'inventory'
                    reserve_locs = []
                    val = stock_in_riserva.get(key)
                    if isinstance(val, dict):
                        loc = str(val.get("location", "")).strip()
                        q = try_int(val.get("quantità", 0))
                        if "inventory" in loc.lower():
                            reserve_locs.append((loc, q))
                    elif isinstance(val, (list, tuple)):
                        for rec in val:
                            if isinstance(rec, dict):
                                loc = str(rec.get("location", "")).strip()
                                q = try_int(rec.get("quantità", 0))
                                if "inventory" in loc.lower():
                                    reserve_locs.append((loc, q))
                    # build message
                    if reserve_locs:
                        suggestions = [f"{q} da {loc}" for (loc, q) in reserve_locs]
                        st.warning(f"'{key}' sotto soglia! In mano: {q_mano} ({loc_mano}). Suggerito da riserva: {', '.join(suggestions)}")
                        reserve_str = "; ".join([f"{loc} ({q})" for loc, q in reserve_locs])
                    else:
                        st.warning(f"'{key}' sotto soglia! In mano: {q_mano} ({loc_mano}). Nessuna location INVENTORY trovata.")
                        reserve_str = ""
                    alert_rows.append({
                        "Item Code": key,
                        "Quantità in mano": q_mano,
                        "Location in mano": loc_mano,
                        "Location riserva INVENTORY": reserve_str
                    })
            # download report alert if any
            if alert_rows:
                df_alert = pd.DataFrame(alert_rows).sort_values("Item Code").reset_index(drop=True)
                buf = BytesIO()
                df_alert.to_excel(buf, index=False)
                st.download_button(
                    label="📥 Scarica report alert (Excel)",
                    data=buf.getvalue(),
                    file_name="alert_stock_basso.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.success("Nessun alert: tutti gli stock in mano sono sopra la soglia.")

        # --- Verifica disponibilità per Order Number (select + button) ---
        st.markdown("## 🔍 Verifica disponibilità per Order Number")
        order_list = richiesta[COL_ORDER].dropna().unique().tolist()
        if not order_list:
            st.info("Nessun Order Number nello storico richieste.")
        else:
            ordine_sel = st.selectbox("Seleziona Order Number", order_list)
            if st.button("Verifica ordine"):
                filtro = richiesta[richiesta[COL_ORDER] == ordine_sel]
                # group by item and sum requested quantity to avoid duplicates
                grouped = filtro.groupby(COL_ITEM_CODE, as_index=False)[COL_QTA_RICHIESTA].sum()

                rows = []
                verifica_rows_to_save = []  # for storico_verifiche.csv

                for _, r in grouped.iterrows():
                    item = norma_item(r[COL_ITEM_CODE])
                    req_qta = try_int(r[COL_QTA_RICHIESTA])
                    # stock in mano
                    mano_rec = stock_in_mano.get(item, {})
                    q_mano = 0
                    loc_mano = "non definita"
                    if isinstance(mano_rec, dict):
                        q_mano = try_int(mano_rec.get("quantità", 0))
                        loc_mano = mano_rec.get("location", "") or "non definita"
                    elif isinstance(mano_rec, (list, tuple)):
                        total = 0
                        loc_cand = ""
                        for rec in mano_rec:
                            if isinstance(rec, dict):
                                total += try_int(rec.get("quantità", 0))
                                if not loc_cand:
                                    loc_cand = rec.get("location", "")
                        q_mano = total
                        loc_mano = loc_cand or "non definita"

                    if q_mano >= req_qta:
                        status = "✅ Disponibile"
                        quantita_da_prelevare = 0
                        reserve_locations_str = ""
                    else:
                        missing = req_qta - q_mano
                        # collect reserve locations containing 'inventory'
                        reserve_list = []
                        val = stock_in_riserva.get(item)
                        if isinstance(val, dict):
                            loc = str(val.get("location", "")).strip()
                            q = try_int(val.get("quantità", 0))
                            if "inventory" in loc.lower():
                                reserve_list.append((loc, q))
                        elif isinstance(val, (list, tuple)):
                            for rec in val:
                                if isinstance(rec, dict):
                                    loc = str(rec.get("location", "")).strip()
                                    q = try_int(rec.get("quantità", 0))
                                    if "inventory" in loc.lower():
                                        reserve_list.append((loc, q))
                        reserve_info_parts = []
                        total_res_available = 0
                        for loc, q in reserve_list:
                            take = min(missing, q)
                            if q > 0:
                                reserve_info_parts.append(f"{loc} ({q})")
                                total_res_available += q
                        reserve_locations_str = "; ".join(reserve_info_parts)
                        if total_res_available >= missing and total_res_available > 0:
                            status = "⚠ Da riserva (coperto)"
                            quantita_da_prelevare = missing
                        elif total_res_available > 0:
                            status = "❌ Non sufficiente (anche da riserva)"
                            quantita_da_prelevare = missing
                        else:
                            status = "❌ Non disponibile in riserva INVENTORY"
                            quantita_da_prelevare = missing

                    rows.append({
                        "Item Code": item,
                        "Requested_quantity": req_qta,
                        "Quantità disponibile": q_mano,
                        "Location stock in mano": loc_mano,
                        "Quantità da prelevare": quantita_da_prelevare,
                        "Location riserva (INVENTORY)": reserve_locations_str,
                        "Status": status
                    })

                    # prepare a row for storico_verifiche
                    verifica_rows_to_save.append({
                        "Verification Timestamp": pd.Timestamp.now(),
                        "Order Number": ordine_sel,
                        "Item Code": item,
                        "Requested_quantity": req_qta,
                        "Available_in_Stock": q_mano,
                        "Location_in_Stock": loc_mano,
                        "Quantity_missing": quantita_da_prelevare,
                        "Reserve_Locations_INVENTORY": reserve_locations_str,
                        "Status": status
                    })

                # display results
                if rows:
                    df_res = pd.DataFrame(rows)
                    # color by status using pandas Styler
                    def color_row(row):
                        stt = str(row.get("Status", "")).lower()
                        if "❌" in stt or "non sufficiente" in stt or "non disponibile" in stt:
                            color = "background-color: #f7c6c6"
                        elif "⚠" in stt or "da riserva" in stt:
                            color = "background-color: #fff2b8"
                        elif "✅" in stt or "disponibile" in stt:
                            color = "background-color: #d8f3d8"
                        else:
                            color = ""
                        return [color] * len(row)

                    try:
                        df_res = df_res.sort_values(["Status", "Item Code"], ascending=[True, True]).reset_index(drop=True)
                    except Exception:
                        df_res = df_res.sort_values("Item Code", key=lambda s: s.astype(str)).reset_index(drop=True)

                    styled = df_res.style.apply(color_row, axis=1)
                    st.dataframe(styled)

                    # download result excel
                    buf = BytesIO()
                    df_res.to_excel(buf, index=False)
                    buf.seek(0)
                    st.download_button(
                        label="📥 Scarica report ordine (Excel)",
                        data=buf.getvalue(),
                        file_name=f"report_{ordine_sel}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # --- append verification rows to storico_verifiche.csv (file unico) ---
                    df_ver = pd.DataFrame(verifica_rows_to_save)
                    # ensure file exists or append appropriately
                    if os.path.exists(STORICO_VERIFICHE_FILE):
                        try:
                            existing = pd.read_csv(STORICO_VERIFICHE_FILE)
                            combined = pd.concat([existing, df_ver], ignore_index=True)
                        except Exception:
                            combined = df_ver
                    else:
                        combined = df_ver
                    # convert timestamp column to iso format for CSV
                    if "Verification Timestamp" in combined.columns:
                        combined["Verification Timestamp"] = pd.to_datetime(combined["Verification Timestamp"], errors="coerce")
                    salva_csv(STORICO_VERIFICHE_FILE, combined)
                    st.success(f"✅ Verifica salvata in '{STORICO_VERIFICHE_FILE}'.")
                else:
                    st.info("Nessun articolo trovato per questo Order Number.")

# ---------------- Sidebar: ricerca Item & Location ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Ricerca Rapida")

# search by Item Code
query_item = st.sidebar.text_input("Cerca per Item Code")
if query_item:
    q = norma_item(query_item)
    found = False
    if q in stock_in_mano:
        rec = stock_in_mano[q]
        if isinstance(rec, dict):
            st.sidebar.success(f"[In Mano] {rec.get('quantità',0)} @ {rec.get('location','')}")
        elif isinstance(rec, (list,tuple)):
            lines = []
            for r in rec:
                if isinstance(r, dict):
                    lines.append(f"{r.get('location','')}: {r.get('quantità',0)}")
            st.sidebar.success("[In Mano]\n" + "\n".join(lines))
        found = True
    if q in stock_in_riserva:
        rec = stock_in_riserva[q]
        if isinstance(rec, dict):
            st.sidebar.info(f"[In Riserva] {rec.get('quantità',0)} @ {rec.get('location','')}")
        elif isinstance(rec, (list,tuple)):
            lines = []
            for r in rec:
                if isinstance(r, dict):
                    s = f"{r.get('location','')}: {r.get('quantità',0)}"
                    if "inventory" in str(r.get('location','')).lower():
                        s += "  <-- INVENTORY"
                    lines.append(s)
            st.sidebar.info("[In Riserva]\n" + "\n".join(lines))
        found = True
    if not found:
        st.sidebar.warning("Item non trovato in nessuno stock.")

# filter by Location
st.sidebar.markdown("### 📍 Filtra per Location")
all_locations = set()
for d in (stock_in_mano, stock_in_riserva):
    for v in d.values():
        if isinstance(v, dict):
            loc = v.get("location", "")
            if loc:
                all_locations.add(loc)
        elif isinstance(v, (list,tuple)):
            for rec in v:
                if isinstance(rec, dict):
                    loc = rec.get("location","")
                    if loc:
                        all_locations.add(loc)

if all_locations:
    sel_loc = st.sidebar.selectbox("Seleziona Location", sorted(all_locations))
    if sel_loc:
        st.sidebar.markdown(f"**Item in '{sel_loc}':**")
        for label, d in [("In Mano", stock_in_mano), ("In Riserva", stock_in_riserva)]:
            items_here = {k:v for k,v in d.items() if (
                (isinstance(v, dict) and v.get("location","")==sel_loc) or
                (isinstance(v, (list,tuple)) and any((isinstance(r, dict) and r.get("location","")==sel_loc) for r in v))
            )}
            if items_here:
                st.sidebar.write(f"**{label}:**")
                for item_code, rec in items_here.items():
                    if isinstance(rec, dict):
                        st.sidebar.write(f"- {item_code} → {rec.get('quantità',0)}")
                    else:
                        # list
                        for r in rec:
                            if isinstance(r, dict) and r.get("location","")==sel_loc:
                                st.sidebar.write(f"- {item_code} → {r.get('quantità',0)}")
else:
    st.sidebar.info("Nessuna location registrata nei dati caricati.")
