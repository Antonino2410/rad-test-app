import re

import streamlit as st

import pandas as pd


import pickle


import os


from io import BytesIO


import matplotlib.pyplot as plt


import copy




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


    """


    Carica lo storico delle richieste e normalizza Item Code e Requested_quantity se presenti.


    """


    if os.path.exists(path):


        try:


            df = pd.read_csv(path)


            if TS_COL in df.columns:


                df[TS_COL] = pd.to_datetime(df[TS_COL], errors="coerce")


            if COL_ITEM_CODE in df.columns:


                df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item)


            if COL_QTA_RICHIESTA in df.columns:


                df[COL_QTA_RICHIESTA] = df[COL_QTA_RICHIESTA].apply(try_int)


            return df


        except Exception:


            return pd.DataFrame(columns=cols)


    return pd.DataFrame(columns=cols)





def salva_csv(path, df):


    df.to_csv(path, index=False)





# ---------------- Normalization & robust parsing ----------------


def norma_item(x):


    """Normalizza Item Code: gestisce int/float/str e rimuove .0 finali."""


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


    # rimuovi eventuali .0 finali come "100012431.0"


    m = re.match(r'^(\d+)\.0+$', s)


    if m:


        s = m.group(1)


    return s.upper()





def try_int(v):


    """Parsing robusto di quantità: gestisce int/float/string con separatori."""


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


    # rimuovi spazi e apostrofi


    s = s.replace(" ", "").replace("'", "")


    # gestione numeri con punti e virgole come separatori di migliaia/decimali


    if "." in s and "," in s:


        last_dot = s.rfind('.')


        last_comma = s.rfind(',')


        if last_dot > last_comma:


            s = s.replace(',', '')


        else:


            s = s.replace('.', '').replace(',', '.')


    else:


        # se ha punti con gruppi di 3 considerali separatori migliaia


        if "." in s and "," not in s:


            parts = s.split('.')


            if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):


                s = s.replace('.', '')


        if "," in s and "." not in s:


            parts = s.split(',')


            if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):


                s = s.replace(',', '')


st.set_page_config(page_title="RAD-TEST App", layout="wide")


st.title("📦 RAD-TEST – Gestione Stock e Ordini")





# Inizializzazione session state


if "stock_mano" not in st.session_state:


    st.session_state["stock_mano"] = pd.DataFrame()


if "stock_riserva" not in st.session_state:


    st.session_state["stock_riserva"] = pd.DataFrame()


if "ordini" not in st.session_state:


    st.session_state["ordini"] = pd.DataFrame()





# Upload file


st.sidebar.header("📁 Carica i tuoi file Excel")


stock_file = st.sidebar.file_uploader("📦 Stock in mano", type=["xlsx"])


riserva_file = st.sidebar.file_uploader("📦 Stock di riserva", type=["xlsx"])


ordini_file = st.sidebar.file_uploader("📄 Ordini (con Order Number)", type=["xlsx"])





if stock_file:


    st.session_state["stock_mano"] = pd.read_excel(stock_file)


if riserva_file:


    st.session_state["stock_riserva"] = pd.read_excel(riserva_file)


if ordini_file:


    st.session_state["ordini"] = pd.read_excel(ordini_file)





stock_df = st.session_state["stock_mano"]


riserva_df = st.session_state["stock_riserva"]


ordini_df = st.session_state["ordini"]





# Analisi


st.header("🔎 Analisi Disponibilità per Order Number")





if not stock_df.empty and not riserva_df.empty and not ordini_df.empty:





    # Pulizia nomi colonne


    ordini_df.columns = [col.strip() for col in ordini_df.columns]


    stock_df.columns = [col.strip() for col in stock_df.columns]


    riserva_df.columns = [col.strip() for col in riserva_df.columns]





    # Selezione Order Number


    unique_orders = ordini_df["Order Number"].dropna().unique()


    selected_order = st.selectbox("Seleziona un Order Number", unique_orders)





    if selected_order:


        ordine_corrente = ordini_df[ordini_df["Order Number"] == selected_order]


        suggerimenti = []





        for _, riga in ordine_corrente.iterrows():


            item = str(riga["Item Code"]).strip()


            richiesta = float(riga["Requested_quantity"])





            # Quantità totale in mano


            stock_totale = stock_df[stock_df["Item Code"] == item]["Quantity"].sum()





            if stock_totale >= richiesta:


                suggerimenti.append({


                    "Item Code": item,


                    "Richiesta": richiesta,


                    "Disponibile in mano": stock_totale,


                    "Status": "✅ Sufficiente in stock in mano",


                    "Prelievi da riserva": ""


                })

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


    """Normalizza il valore a lista di dict [{'quantità':..,'location':..}, ...]"""


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





# ----------- get_locations_and_total (location principale: quantità massima) -----------


def get_locations_and_total(stock_dict, key):


    """


    Restituisce (list_of_tuples [(location, qty)], main_qty).


    Prendiamo LA location principale: la riga con quantità maggiore.


    """


    entries = stock_dict.get(key)


    if entries is None:


        return [], 0





    # Normalize to list


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





# ---------------- Load persistent data ----------------


richiesta = carica_csv_safe(RICHIESTE_FILE, [COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL])


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





# ---------------- Session state ----------------


if "pending_picks" not in st.session_state:


    st.session_state["pending_picks"] = []


if "confirm_disabled_for_order" not in st.session_state:


    st.session_state["confirm_disabled_for_order"] = {}


if "pre_pick_backup" not in st.session_state:


    st.session_state["pre_pick_backup"] = {}


if "confirm_prompt" not in st.session_state:


    st.session_state["confirm_prompt"] = {"type": None, "order": None}





# ---------------- Sidebar general UI ----------------


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


    up = st.file_uploader("Carica file Excel stock in mano (Item Code, Quantità, Location)", type=["xlsx", "xls"])


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


            # aggregate same Item+Location within uploaded file


            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()


            for _, r in grouped.iterrows():


                key = norma_item(r[COL_ITEM_CODE])


                q = try_int(r[COL_QUANTITA])


                loc = str(r[COL_LOCATION]).strip()


                existing = stock_in_mano.get(key, [])


                existing.append({"quantità": q, "location": loc})


                stock_in_mano[key] = existing


            salva_pickle(STOCK_MANO_FILE, stock_in_mano)


            st.success("Stock in mano salvato e aggregato correttamente.")


        else:


            st.error(f"File mancante colonne: '{COL_ITEM_CODE}', '{COL_QUANTITA}', '{COL_LOCATION}'.")





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


            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()


            for _, r in grouped.iterrows():


                key = norma_item(r[COL_ITEM_CODE])


                q = try_int(r[COL_QUANTITA])


                loc = str(r[COL_LOCATION]).strip()


                existing = stock_in_riserva.get(key, [])


                existing.append({"quantità": q, "location": loc})


                stock_in_riserva[key] = existing


            salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)


            st.success("Stock riserva salvato correttamente.")


        else:


            st.error(f"File mancante colonne: '{COL_ITEM_CODE}', '{COL_QUANTITA}', '{COL_LOCATION}'.")





# ---------------- Page: Analisi Richieste & Suggerimenti ----------------


elif page == "Analisi Richieste & Suggerimenti":


    st.title("📊 Analisi Richieste & Suggerimenti")





    # ---------- FILE UPLOAD RICHIESTE (con normalizzazione e SOSTITUZIONE ordini esistenti) ----------


    up = st.file_uploader("Carica file Excel richieste (Item Code, Requested_quantity, Order Number)", type=["xlsx", "xls"])


    if up:


        df = pd.read_excel(up)


        st.write("Colonne trovate nel file caricato:", df.columns.tolist())





        # mappatura nomi colonne


        rename = {}


        for c in df.columns:


            lc = c.strip().lower()


            if lc in ["item code", "itemcode", "item number", "item_number", "item"]:


                rename[c] = COL_ITEM_CODE


            if lc in ["requested quantity", "requested_quantity", "requestedquantity", "quantità richiesta", "quantita richiesta", "requested_quant", "requested_quantit"]:


                rename[c] = COL_QTA_RICHIESTA


            if lc in ["order number", "ordernumber", "order"]:


                rename[c] = COL_ORDER


        if rename:


            df.rename(columns=rename, inplace=True)





        # normalizza Item Code e Requested_quantity


        if COL_ITEM_CODE in df.columns:


            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].apply(norma_item)


        if COL_QTA_RICHIESTA in df.columns:


            df[COL_QTA_RICHIESTA] = df[COL_QTA_RICHIESTA].apply(try_int)


        else:


            st.error(f"Colonna '{COL_QTA_RICHIESTA}' non trovata nel file; assicurati esista.")


            df = None





        if df is not None:


            # assicurati che ci sia colonna order


            if COL_ORDER not in df.columns:


                df[COL_ORDER] = pd.NA





            # Aggrega duplicati *all'interno del file caricato* (Order + Item)


            df_grouped = df.groupby([COL_ORDER, COL_ITEM_CODE], as_index=False)[COL_QTA_RICHIESTA].sum()


            df_grouped[TS_COL] = pd.Timestamp.now()





            # Debug (mostra i totali dell'upload) - puoi rimuovere queste due righe dopo test


            st.write("Riepilogo upload per Order (somma Requested_quantity nel file caricato):")


            st.write(df_grouped.groupby(COL_ORDER)[COL_QTA_RICHIESTA].sum())





            # Evita duplicazioni nello storico: rimuovi dallo storico le righe con gli stessi Order Number 


            # presenti nel file caricato (così il nuovo upload rimpiazza quello precedente per quegli ordini)


            if COL_ORDER not in richiesta.columns:


                richiesta[COL_ORDER] = pd.NA


            orders_in_upload = [o for o in df_grouped[COL_ORDER].dropna().unique().tolist()]


            if orders_in_upload:


                richiesta = richiesta[~richiesta[COL_ORDER].isin(orders_in_upload)]





            # Ora concateno il file raggruppato (che sostituisce eventuali precedenti per gli stessi ordini)


            df_to_add = df_grouped[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, TS_COL]]


            df_to_add[COL_QTA_RICHIESTA] = df_to_add[COL_QTA_RICHIESTA].apply(try_int)





            richiesta = pd.concat([richiesta, df_to_add], ignore_index=True, sort=False)


            salva_csv(RICHIESTE_FILE, richiesta)


            st.success("Richieste aggiunte allo storico (normalizzate, aggregate e sostituite per gli Order caricati).")





            # Debug: mostra totali nello storico per gli order appena caricati (dopo append)


            if orders_in_upload:


                st.write("Totali nello storico per gli order appena caricati (dopo append):")


                st.write(richiesta[richiesta[COL_ORDER].isin(orders_in_upload)]


                         .groupby(COL_ORDER)[COL_QTA_RICHIESTA].sum())





    # ---------- FINE UPLOAD RICHIESTE ----------





    if richiesta.empty:


        st.info("Nessuno storico richieste presente. Carica un file richieste.")


    else:


        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)


        recenti = richiesta[richiesta[TS_COL] >= cutoff].copy()


        # Assicuriamoci che Requested_quantity sia numerico


        if COL_QTA_RICHIESTA in recenti.columns:


            recenti[COL_QTA_RICHIESTA] = recenti[COL_QTA_RICHIESTA].apply(try_int)


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





        # --- Alert stock basso (expander) ---


        with st.expander("⚠️ Alert stock basso"):


            alert_rows = []


            for item, tot_req in agg.items():


                key = norma_item(item)


                locs_mano, main_mano_qty = get_locations_and_total(stock_in_mano, key)


                loc_mano_display = locs_mano[0][0] if locs_mano else "non definita"


                q_mano = main_mano_qty


                if q_mano < soglia:


                    reserve_locs = []


                    val = stock_in_riserva.get(key, [])


                    for rec in val:


                        if isinstance(rec, dict):


                            loc = str(rec.get("location","")).strip()


                            q = try_int(rec.get("quantità", 0))


                            if "inventory" in loc.lower():


                                reserve_locs.append((loc, q))


                    if reserve_locs:


                        suggestions = [f"{q} da {loc}" for (loc, q) in reserve_locs]


                        st.warning(f"'{key}' sotto soglia! In mano: {q_mano} ({loc_mano_display}). Suggerito da riserva: {', '.join(suggestions)}")


                        reserve_str = "; ".join([f"{loc} ({q})" for loc, q in reserve_locs])


                    else:


                        st.warning(f"'{key}' sotto soglia! In mano: {q_mano} ({loc_mano_display}). Nessuna location INVENTORY trovata.")


                        reserve_str = ""


                    alert_rows.append({


                        "Item Code": key,


                        "Quantità in mano": q_mano,


                        "Location in mano": loc_mano_display,


                        "Location riserva INVENTORY": reserve_str


                    })


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





        # ---------------- Verifica disponibilità per Order Number ----------------


        st.markdown("## 🔍 Verifica disponibilità per Order Number")


        order_list = richiesta[COL_ORDER].dropna().unique().tolist()


        if not order_list:


            st.info("Nessun Order Number nello storico richieste.")


        else:


            ordine_sel = st.selectbox("Seleziona Order Number", order_list)


            if st.button("Verifica ordine"):


                filtro = richiesta[richiesta[COL_ORDER] == ordine_sel].copy()


                # forzo numericità


                if COL_QTA_RICHIESTA in filtro.columns:


                    filtro[COL_QTA_RICHIESTA] = filtro[COL_QTA_RICHIESTA].apply(try_int)


                grouped = filtro.groupby(COL_ITEM_CODE, as_index=False)[COL_QTA_RICHIESTA].sum()





                rows = []


                pending_allocations = []


                for _, r in grouped.iterrows():


                    item = norma_item(r[COL_ITEM_CODE])


                    req_qta = try_int(r[COL_QTA_RICHIESTA])





                    locs_mano, q_mano = get_locations_and_total(stock_in_mano, item)


                    loc_mano_display = "; ".join([f"{l} ({q})" for l,q in locs_mano]) if locs_mano else "non definita"





                    if q_mano >= req_qta:


                        rows.append({


                            "Item Code": item,


                            "Requested_quantity": req_qta,


                            "Quantità disponibile": q_mano,


                            "Location stock in mano": loc_mano_display,


                            "Quantità da prelevare": 0,


                            "Location riserva (INVENTORY)": "",


                            "Status": "Disponibile",


                            "Status Icon": "✅"


                        })


                        pending_allocations.append({


                            "item": item,


                            "from_mano": req_qta,


                            "reserve_alloc": []


                        })


                    else:


                        missing = req_qta - q_mano


                        reserve_list = []


                        val = stock_in_riserva.get(item, [])


                        for rec in val:


                            if isinstance(rec, dict):


                                loc = str(rec.get("location","")).strip()


                                q = try_int(rec.get("quantità", 0))


                                if "inventory" in loc.lower():


                                    reserve_list.append([loc, q])


                        allocs = []


                        left = missing


                        for loc, q in reserve_list:


                            if left <= 0:


                                break


                            take = min(left, q)


                            if take > 0:


                                allocs.append({"location": loc, "qty": take})


                                left -= take


                        total_reserved = sum(a["qty"] for a in allocs)


                        if total_reserved >= missing and total_reserved > 0:


                            status = "Da riserva (coperto)"


                        elif total_reserved > 0:


                            status = "Non sufficiente (anche da riserva)"


                        else:


                            status = "Non disponibile in riserva INVENTORY"





                        rows.append({


                            "Item Code": item,


                            "Requested_quantity": req_qta,


                            "Quantità disponibile": q_mano,


                            "Location stock in mano": loc_mano_display,


                            "Quantità da prelevare": (req_qta - q_mano) if allocs else req_qta,


                            "Location riserva (INVENTORY)": "; ".join([f'{a["location"]} ({a["qty"]})' for a in allocs]),


                            "Status": status,


                            "Status Icon": "⚠️" if total_reserved > 0 else "❌"


                        })





                        pending_allocations.append({


                            "item": item,


                            "from_mano": q_mano,


                            "reserve_alloc": allocs


                        })





                st.session_state["pending_picks"] = pending_allocations


                st.session_state["pre_pick_backup"][ordine_sel] = {


                    "mano": deep_copy_stock(stock_in_mano),


                    "riserva": deep_copy_stock(stock_in_riserva)


                }


                st.session_state["confirm_disabled_for_order"][ordine_sel] = False


                st.session_state["confirm_prompt"] = {"type": None, "order": None}





                if rows:


                    df_res = pd.DataFrame(rows)


                    try:


                        df_res = df_res.sort_values(["Status", "Item Code"], ascending=[True, True]).reset_index(drop=True)


                    except Exception:


                        df_res = df_res.sort_values("Item Code", key=lambda s: s.astype(str)).reset_index(drop=True)


                    st.dataframe(df_res)





                    buf = BytesIO()


                    df_res.to_excel(buf, index=False)


                    st.download_button(


                        label="📥 Scarica report ordine (Excel)",


                        data=buf.getvalue(),


                        file_name=f"verifica_{ordine_sel}.xlsx",


                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


                    )


                else:


                    st.info("Nessun articolo trovato per questo ordine.")





            # Confirm / Undo UI


            if st.session_state.get("pending_picks"):


                ordine_key = ordine_sel


                confirmed_flag = st.session_state["confirm_disabled_for_order"].get(ordine_key, False)





                st.markdown("---")


                st.write("**Azioni per l'ordine selezionato:**")





                col1, col2 = st.columns(2)





                with col1:


                    if st.button("✅ Conferma prelievo", disabled=confirmed_flag, key=f"confirm_btn_{ordine_key}"):


                        st.session_state["confirm_prompt"] = {"type": "confirm", "order": ordine_key}





                    if st.session_state["confirm_prompt"].get("type") == "confirm" and st.session_state["confirm_prompt"].get("order") == ordine_key:


                        st.warning("Sei sicuro di voler **confermare** questo prelievo? Verranno scalate le quantità indicate.")


                        st.write("**Riepilogo quantità che verranno prelevate:**")


                        pending = st.session_state.get("pending_picks", [])


                        for p in pending:


                            item = p["item"]


                            from_mano = p.get("from_mano", 0)


                            allocs = p.get("reserve_alloc", [])


                            allocs_str = ", ".join([f'{a["qty"]} da {a["location"]}' for a in allocs]) if allocs else ""


                            st.write(f"- {item}: {from_mano} da IN MANO" + (f"; {allocs_str}" if allocs_str else ""))


                        ccol, dcol = st.columns([1,1])


                        with ccol:


                            if st.button("Sì, conferma", key=f"confirm_yes_{ordine_key}"):


                                # Apply picks


                                pending = st.session_state.get("pending_picks", [])


                                for pick in pending:


                                    item = pick["item"]


                                    take_from_mano = pick.get("from_mano", 0)


                                    if take_from_mano and item in stock_in_mano:


                                        rec_list = stock_in_mano[item]


                                        left = take_from_mano


                                        newlist = []


                                        for r in rec_list:


                                            if left <= 0:


                                                newlist.append(r)


                                                continue


                                            available = try_int(r.get("quantità", 0))


                                            used = min(available, left)


                                            remaining = available - used


                                            left -= used


                                            r["quantità"] = max(0, remaining)


                                            newlist.append(r)


                                        stock_in_mano[item] = newlist





                                    for alloc in pick.get("reserve_alloc", []):


                                        loc = alloc["location"]


                                        qty_to_take = alloc["qty"]


                                        val_list = stock_in_riserva.get(item, [])


                                        newlist = []


                                        left_alloc = qty_to_take


                                        for r in val_list:


                                            if isinstance(r, dict) and str(r.get("location","")).strip() == loc and left_alloc > 0:


                                                available = try_int(r.get("quantità", 0))


                                                used = min(available, left_alloc)


                                                r["quantità"] = max(0, available - used)


                                                left_alloc -= used


                                            newlist.append(r)


                                        stock_in_riserva[item] = newlist





                                salva_pickle(STOCK_MANO_FILE, stock_in_mano)


                                salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)


                                st.session_state["confirm_disabled_for_order"][ordine_key] = True





                                ver_rows = []


                                for pick in st.session_state.get("pending_picks", []):


                                    item = pick["item"]


                                    taken_mano = pick.get("from_mano", 0)


                                    reserve_allocs = pick.get("reserve_alloc", [])


                                    reserve_str = "; ".join([f'{a["location"]} ({a["qty"]})' for a in reserve_allocs]) if reserve_allocs else ""


                                    ver_rows.append({


                                        "Verification Timestamp": pd.Timestamp.now(),


                                        "Order Number": ordine_key,


                                        "Item Code": item,


                                        "Taken_from_Stock_in_Mano": taken_mano,


                                        "Reserve_Allocations": reserve_str


                                    })


                                if ver_rows:


                                    df_ver = pd.DataFrame(ver_rows)


                                    if os.path.exists(STORICO_VERIFICHE_FILE):


                                        try:


                                            existing = pd.read_csv(STORICO_VERIFICHE_FILE)


                                            combined = pd.concat([existing, df_ver], ignore_index=True)


                                        except Exception:


                                            combined = df_ver


                                    else:


                                        combined = df_ver


                                    salva_csv(STORICO_VERIFICHE_FILE, combined)


                                st.success("✅ Prelievo confermato e stock aggiornato.")


                                st.session_state["confirm_prompt"] = {"type": None, "order": None}


                        with dcol:


                            if st.button("No, annulla", key=f"confirm_no_{ordine_key}"):


                                st.session_state["confirm_prompt"] = {"type": None, "order": None}


                                st.info("Operazione di conferma annullata dall'utente.")





                with col2:


                    undo_disabled = not st.session_state["confirm_disabled_for_order"].get(ordine_key, False)


                    if st.button("↩️ Annulla prelievo", disabled=undo_disabled, key=f"undo_btn_{ordine_key}"):


                        st.session_state["confirm_prompt"] = {"type": "undo", "order": ordine_key}





                    if st.session_state["confirm_prompt"].get("type") == "undo" and st.session_state["confirm_prompt"].get("order") == ordine_key:


                        st.warning("Sei sicuro di voler **annullare** l'ultimo prelievo per questo ordine? Verranno ripristinate le quantità salvate nel backup.")


                        backup = st.session_state["pre_pick_backup"].get(ordine_key)


                        if backup:


                            st.write("Backup esistente — verranno ripristinati gli stock precedenti all'operazione.")


                        else:


                            st.write("Attenzione: nessun backup trovato; impossibile annullare.")


                        ccol2, dcol2 = st.columns([1,1])


                        with ccol2:


                            if st.button("Sì, annulla", key=f"undo_yes_{ordine_key}"):


                                backup = st.session_state["pre_pick_backup"].get(ordine_key)


                                if backup:


                                    stock_in_mano = backup.get("mano", stock_in_mano)


                                    stock_in_riserva = backup.get("riserva", stock_in_riserva)


                                    salva_pickle(STOCK_MANO_FILE, stock_in_mano)


                                    salva_pickle(STOCK_RISERVA_FILE, stock_in_riserva)


                                    st.session_state["confirm_disabled_for_order"][ordine_key] = False


                                    st.session_state["pending_picks"] = []


                                    st.success("🔄 Prelievo annullato e stock ripristinato.")


                                else:


                                    st.error("Nessun backup disponibile per questo ordine.")


                                st.session_state["confirm_prompt"] = {"type": None, "order": None}


                        with dcol2:


                            if st.button("No, mantieni", key=f"undo_no_{ordine_key}"):


                                st.session_state["confirm_prompt"] = {"type": None, "order": None}


                                st.info("Annullamento prelievo cancellato dall'utente.")





# ---------------- Sidebar: Ricerca Rapida (Location principale) ----------------


st.sidebar.markdown("---")


st.sidebar.markdown("### 🔎 Ricerca Rapida")





query_item = st.sidebar.text_input("Cerca per Item Code")


if query_item:


    q = norma_item(query_item)


    found = False





    locs_mano, main_mano_qty = get_locations_and_total(stock_in_mano, q)


    if locs_mano:


        primary_loc_mano = locs_mano[0][0] or "Location non specificata"


        st.sidebar.success(f"[In Mano] Quantità principale: {main_mano_qty} @ {primary_loc_mano}")


        found = True


    else:


        st.sidebar.info("Nessuna presenza in mano.")





    locs_ris, main_ris_qty = get_locations_and_total(stock_in_riserva, q)


    if locs_ris:


        primary_loc_ris = locs_ris[0][0] or "Location non specificata"


        note = " <-- INVENTORY" if "inventory" in str(primary_loc_ris).lower() else ""


        st.sidebar.info(f"[In Riserva] Quantità principale: {main_ris_qty} @ {primary_loc_ris}{note}")


        found = True


    else:


        st.sidebar.info("Nessuna presenza in riserva.")





    if not found:


        st.sidebar.warning("Item non trovato in nessuno stock.")





# ---------------- Sidebar: Filtra per Location ----------------


st.sidebar.markdown("### 📍 Filtra per Location")


all_locations = set()


for d in (stock_in_mano, stock_in_riserva):


    for v in d.values():


        if isinstance(v, dict):


            loc = v.get("location", "")


            if loc:


                all_locations.add(loc)


        elif isinstance(v, (list, tuple)):


            for rec in v:


                if isinstance(rec, dict):


                    loc = rec.get("location","")


                    if loc:


                        all_locations.add(loc)


                mancante = richiesta - stock_totale


                suggeriti = []


                riserva_item = riserva_df[


                    (riserva_df["Item Code"] == item) &


                    (riserva_df["Location"].str.lower().str.contains("inventory"))


                ].sort_values("Quantity", ascending=False)





                for _, loc in riserva_item.iterrows():


                    if mancante <= 0:


                        break


                    qty = loc["Quantity"]


                    take = min(qty, mancante)


                    suggeriti.append(f"{take} da {loc['Location']}")


                    mancante -= take





                suggerimenti.append({


                    "Item Code": item,


                    "Richiesta": richiesta,


                    "Disponibile in mano": stock_totale,


                    "Status": "⚠️ Parziale",


                    "Prelievi da riserva": ", ".join(suggeriti) if suggeriti else "❌ Nessuna riserva trovata"


                })





        risultato = pd.DataFrame(suggerimenti)


        st.dataframe(risultato, use_container_width=True)




if all_locations:


    sel_loc = st.sidebar.selectbox("Seleziona Location", sorted(all_locations))


    if sel_loc:


        st.sidebar.markdown(f"**Item in '{sel_loc}':**")


        for label, d in [("In Mano", stock_in_mano), ("In Riserva", stock_in_riserva)]:


            items_here = {}


            for item_code, rec in d.items():


                if isinstance(rec, dict):


                    if rec.get("location","") == sel_loc:


                        items_here[item_code] = items_here.get(item_code, 0) + try_int(rec.get("quantità",0))


                elif isinstance(rec, (list, tuple)):


                    for r in rec:


                        if isinstance(r, dict) and r.get("location","") == sel_loc:


                            items_here[item_code] = items_here.get(item_code, 0) + try_int(r.get("quantità",0))


            if items_here:


                st.sidebar.write(f"**{label}:**")


                for item_code, qty in items_here.items():


                    st.sidebar.write(f"- {item_code} → {qty}")

else:


    st.sidebar.info("Nessuna location registrata nei dati caricati.")


    st.info("Carica tutti e tre i file Excel per eseguire l'analisi.")
