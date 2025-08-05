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

# --- Funzioni ---
def carica_file_pickle(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
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

def get_reserve_locations_for_item(stock_reserve, item_key):
    """
    Restituisce una lista di tuple (location, quantità) per l'item in stock_reserve
    filtrando solo le location che contengono 'inventory' (case-insensitive).
    Gestisce sia valori singoli dict che liste di dict.
    """
    result = []
    val = stock_reserve.get(item_key)
    if val is None:
        return result

    # Se è una lista di record
    if isinstance(val, (list, tuple)):
        for rec in val:
            if not isinstance(rec, dict):
                continue
            loc = str(rec.get("location", "")).strip()
            try:
                q = int(rec.get("quantità", rec.get("Quantità", 0)))
            except Exception:
                q = 0
            if "inventory" in loc.lower():
                result.append((loc, q))
        return result

    # Se è un singolo dict
    if isinstance(val, dict):
        loc = str(val.get("location", "")).strip()
        try:
            q = int(val.get("quantità", val.get("Quantità", 0)))
        except Exception:
            q = 0
        if "inventory" in loc.lower():
            result.append((loc, q))
        return result

    # altri tipi (numero, stringa) non considerati come location utile
    return result

# --- Caricamento dati ---
richiesta = carica_csv(RICHIESTE_FILE)
stock_in_mano = carica_file_pickle(STOCK_MANO_FILE)
stock_in_riserva = carica_file_pickle(STOCK_RISERVA_FILE)

# In alcune vecchie versioni potresti avere valori non-normalizzati;
# se sono singoli dict converto in dict coerente (ma mantengo compatibilità).
if not isinstance(stock_in_mano, dict):
    stock_in_mano = {}
if not isinstance(stock_in_riserva, dict):
    stock_in_riserva = {}

# --- Menu ---
page = st.sidebar.radio("Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti"
])
soglia = st.sidebar.number_input("Imposta soglia alert stock in mano", min_value=1, max_value=1000, value=20)

# --- Pagine ---
if page == "Carica Stock In Mano":
    st.title("📥 Carica Stock Magazzino In Mano")
    uploaded_file = st.file_uploader("Carica file Excel stock in mano", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns:
            for _, row in df.iterrows():
                item = str(row[COL_ITEM_CODE]).strip().upper()
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                loc = "" if pd.isna(loc) else str(loc).strip()
                stock_in_mano[item] = {"quantità": qta, "location": loc}
            salva_file_pickle(STOCK_MANO_FILE, stock_in_mano)
            st.success("Stock in mano aggiornato!")
        else:
            st.error(f"Il file deve contenere le colonne '{COL_ITEM_CODE}' e '{COL_QUANTITA}'.")

elif page == "Carica Stock Riserva":
    st.title("📥 Carica Stock Magazzino Riserva")
    uploaded_file = st.file_uploader("Carica file Excel stock in riserva", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        if COL_ITEM_CODE in df.columns and COL_QUANTITA in df.columns and COL_LOCATION in df.columns:
            # raggruppa per Item + Location per sommare eventuali righe duplicate
            grouped = df.groupby([COL_ITEM_CODE, COL_LOCATION])[COL_QUANTITA].sum().reset_index()
            for _, row in grouped.iterrows():
                item = str(row[COL_ITEM_CODE]).strip().upper()
                try:
                    qta = int(row.get(COL_QUANTITA, 0))
                except Exception:
                    qta = 0
                loc = row.get(COL_LOCATION, "")
                loc = "" if pd.isna(loc) else str(loc).strip()
                # mantieni struttura: se già esiste ed è lista, append; se dict, converti in lista
                existing = stock_in_riserva.get(item)
                entry = {"quantità": qta, "location": loc}
                if existing is None:
                    stock_in_riserva[item] = [entry]
                elif isinstance(existing, list):
                    stock_in_riserva[item].append(entry)
                elif isinstance(existing, dict):
                    stock_in_riserva[item] = [existing, entry]
                else:
                    stock_in_riserva[item] = [entry]
            salva_file_pickle(STOCK_RISERVA_FILE, stock_in_riserva)
            st.success("Stock in riserva aggiornato!")
        else:
            st.error(f"Il file deve contenere le colonne '{COL_ITEM_CODE}', '{COL_QUANTITA}' e '{COL_LOCATION}'.")

elif page == "Analisi Richieste & Suggerimenti":
    st.title("📊 Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica file Excel richieste", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        # normalizza item code a maiuscolo senza spazi
        if COL_ITEM_CODE in df.columns:
            df[COL_ITEM_CODE] = df[COL_ITEM_CODE].astype(str).str.strip().str.upper()
        df["Timestamp"] = pd.Timestamp.now()
        if COL_ITEM_CODE in df.columns and COL_QTA_RICHIESTA in df.columns:
            richiesta = pd.concat([richiesta, df[[COL_ITEM_CODE, COL_QTA_RICHIESTA, COL_ORDER, "Timestamp"]]], ignore_index=True)
            salva_csv(RICHIESTE_FILE, richiesta)
            st.success("Storico richieste aggiornato!")
        else:
            st.error(f"Il file deve contenere le colonne '{COL_ITEM_CODE}' e '{COL_QTA_RICHIESTA}'.")

    if richiesta.empty:
        st.info("Nessun dato richieste disponibile.")
    else:
        st.subheader("📈 Item più richiesti (ultimo mese)")
        un_mese_fa = pd.Timestamp.now() - pd.Timedelta(days=30)
        recenti = richiesta[richiesta["Timestamp"] >= un_mese_fa]
        try:
            richieste_aggregate = recenti.groupby(COL_ITEM_CODE)[COL_QTA_RICHIESTA].sum().sort_values(ascending=False)
        except Exception:
            richieste_aggregate = pd.Series(dtype=float)

        if not richieste_aggregate.empty:
            st.write(richieste_aggregate.head(10))
            fig, ax = plt.subplots()
            richieste_aggregate.head(10).plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
            ax.set_ylabel('')
            st.pyplot(fig)
        else:
            st.info("Nessun dato richieste recenti.")

        # ---------- Alert stock basso con segnalazione location riserva ----------
        st.subheader("⚠️ Alert stock basso")
        alert_trovati = False
        for item, totale_richiesto in richieste_aggregate.items():
            # item è già maiuscolo perché normalizzato in caricamento richieste
            item_key = str(item).strip().upper()
            qta_in_mano = 0
            loc_in_mano = "non definita"
            mano_record = stock_in_mano.get(item_key)
            if isinstance(mano_record, dict):
                try:
                    qta_in_mano = int(mano_record.get("quantità", 0))
                except Exception:
                    qta_in_mano = 0
                loc_in_mano = mano_record.get("location", "non definita") or "non definita"
            elif isinstance(mano_record, (list, tuple)):
                # somma quantità se è lista
                total = 0
                loc_candidate = ""
                for rec in mano_record:
                    if isinstance(rec, dict):
                        try:
                            total += int(rec.get("quantità", 0))
                        except Exception:
                            pass
                        if not loc_candidate:
                            loc_candidate = rec.get("location", "")
                qta_in_mano = total
                loc_in_mano = loc_candidate or "non definita"
            elif isinstance(mano_record, (int, float, str)):
                try:
                    qta_in_mano = int(mano_record)
                except Exception:
                    qta_in_mano = 0

            if qta_in_mano < soglia:
                # trova tutte le location di riserva che contengono 'inventory'
                reserve_locs = get_reserve_locations_for_item(stock_in_riserva, item_key)
                if reserve_locs:
                    # crea messaggio con location e quantità
                    suggerimenti = [f"{q} da {loc}" for (loc, q) in reserve_locs if q > 0]
                    if suggerimenti:
                        st.warning(f"'{item_key}' è sotto soglia! In magazzino: {qta_in_mano} (Location: {loc_in_mano}). "
                                   f"Richiamare da: {', '.join(suggerimenti)}")
                    else:
                        st.warning(f"'{item_key}' è sotto soglia! In magazzino: {qta_in_mano} (Location: {loc_in_mano}). "
                                   f"Nessuna quantità disponibile nelle location INVENTORY.")
                else:
                    st.warning(f"'{item_key}' è sotto soglia! In magazzino: {qta_in_mano} (Location: {loc_in_mano}). "
                               f"Nessuna riserva trovata con 'inventory'.")
                alert_trovati = True

        if not alert_trovati:
            st.success("Nessun alert: tutti gli stock in mano sono sopra la soglia.")

        # --- Verifica per Order Number (raggruppata per Item Code) ---
        st.markdown("## 🔍 Verifica disponibilità per ordine specifico")
        if COL_ORDER in richiesta.columns:
            ordine_unico = st.selectbox("Seleziona un Order Number", richiesta[COL_ORDER].dropna().unique())
            if st.button("Verifica disponibilità per ordine"):
                filtro_ordine = richiesta[richiesta[COL_ORDER] == ordine_unico]
                # raggruppa per item e somma requested_quantity per evitare duplicati
                grouped = filtro_ordine.groupby(COL_ITEM_CODE, as_index=False)[COL_QTA_RICHIESTA].sum()

                rows = []
                for _, riga in grouped.iterrows():
                    item = str(riga[COL_ITEM_CODE]).strip().upper()
                    richiesta_qta = int(riga[COL_QTA_RICHIESTA]) if pd.notna(riga[COL_QTA_RICHIESTA]) else 0

                    mano_record = stock_in_mano.get(item, {})
                    qta_stock = 0
                    loc_stock = "non definita"
                    if isinstance(mano_record, dict):
                        qta_stock = int(mano_record.get("quantità", 0)) if mano_record.get("quantità", None) is not None else 0
                        loc_stock = mano_record.get("location", "non definita") or "non definita"
                    elif isinstance(mano_record, (list, tuple)):
                        total = 0
                        loc_candidate = ""
                        for rec in mano_record:
                            if isinstance(rec, dict):
                                try:
                                    total += int(rec.get("quantità", 0))
                                except Exception:
                                    pass
                                if not loc_candidate:
                                    loc_candidate = rec.get("location", "")
                        qta_stock = total
                        loc_stock = loc_candidate or "non definita"
                    elif isinstance(mano_record, (int, float, str)):
                        try:
                            qta_stock = int(mano_record)
                        except Exception:
                            qta_stock = 0

                    if qta_stock >= richiesta_qta:
                        rows.append({
                            "Item Code": item,
                            "Requested Quantity": richiesta_qta,
                            "Available in Stock": qta_stock,
                            "Location in Mano": loc_stock,
                            "Reserve Locations (INVENTORY)": "",
                            "Status": "✅ Disponibile"
                        })
                    else:
                        mancanti = richiesta_qta - qta_stock
                        reserve_locs = get_reserve_locations_for_item(stock_in_riserva, item)
                        reserve_str = ""
                        total_res = 0
                        if reserve_locs:
                            parts = []
                            for loc, q in reserve_locs:
                                parts.append(f"{q} da {loc}")
                                total_res += int(q)
                            reserve_str = "; ".join(parts)
                        if total_res >= mancanti and total_res > 0:
                            status = "⚠ Da riserva (coperto)"
                        elif total_res > 0:
                            status = "❌ Non sufficiente (anche da riserva)"
                        else:
                            status = "❌ Non disponibile in riserva INVENTORY"

                        rows.append({
                            "Item Code": item,
                            "Requested Quantity": richiesta_qta,
                            "Available in Stock": qta_stock,
                            "Location in Mano": loc_stock,
                            "Reserve Locations (INVENTORY)": reserve_str,
                            "Status": status
                        })

                # mostra tabella (sicurezza stringhe e ordinamento)
                if rows:
                    df_result = pd.DataFrame(rows)
                    if "Item Code" not in df_result.columns:
                        df_result["Item Code"] = ""
                    df_result["Item Code"] = df_result["Item Code"].astype(str).str.strip()
                    try:
                        df_result = df_result.sort_values(["Status", "Item Code"], ascending=[True, True]).reset_index(drop=True)
                    except Exception:
                        df_result = df_result.sort_values("Item Code", key=lambda s: s.astype(str)).reset_index(drop=True)
                    st.dataframe(df_result)
                    # download
                    buf = BytesIO()
                    df_result.to_excel(buf, index=False)
                    buf.seek(0)
                    st.download_button(
                        label="📥 Scarica risultati in Excel",
                        data=buf,
                        file_name=f"verifica_ordine_{ordine_unico}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info("Nessun articolo trovato per questo ordine.")
        else:
            st.info("Nessuna colonna Order Number nello storico richieste.")

# --- Barra laterale: Ricerca Rapida ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Ricerca Item")
query = st.sidebar.text_input("Cerca Item Code")
if query:
    q = str(query).strip().upper()
    trovato = False
    if q in stock_in_mano:
        rec = stock_in_mano[q]
        if isinstance(rec, dict):
            st.sidebar.success(f"[In Mano] Quantità: {rec.get('quantità',0)} | Location: {rec.get('location','')}")
        elif isinstance(rec, (list, tuple)):
            lines = []
            for e in rec:
                if isinstance(e, dict):
                    lines.append(f"{e.get('location','')}: {e.get('quantità',0)}")
            st.sidebar.success("[In Mano]\n" + "\n".join(lines))
        else:
            st.sidebar.success(f"[In Mano] {rec}")
        trovato = True
    if q in stock_in_riserva:
        lst = stock_in_riserva[q]
        lines = []
        for rec in lst:
            if isinstance(rec, dict):
                lines.append(f"{rec.get('location','')}: {rec.get('quantità',0)}")
        st.sidebar.info("[In Riserva]\n" + "\n".join(lines))
        trovato = True
    if not trovato:
        st.sidebar.warning("Item non trovato.")
