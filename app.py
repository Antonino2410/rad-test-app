import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analisi Stock & Ordini", layout="wide")

st.title("📦 Analisi Disponibilità Item per Order Number")

# Funzione robusta per rinominare le colonne
def rinomina_colonne(df):
    colonne = df.columns.str.lower()
    mapping = {}
    for col in colonne:
        if "item" in col and "code" in col:
            mapping[col] = "item_code"
        elif "quant" in col:
            mapping[col] = "quantity"
        elif "loc" in col:
            mapping[col] = "location"
        elif "order" in col and "number" in col:
            mapping[col] = "order_number"
        elif "request" in col:
            mapping[col] = "requested_quantity"
    df.columns = colonne
    df = df.rename(columns=mapping)
    return df

# Caricamento dei file
st.sidebar.header("📂 Carica i tuoi file Excel")

file_stock_mano = st.sidebar.file_uploader("Stock In Mano", type=["xls", "xlsx"])
file_stock_riserva = st.sidebar.file_uploader("Stock Riserva", type=["xls", "xlsx"])
file_ordini = st.sidebar.file_uploader("File Ordini", type=["xls", "xlsx"])

if file_stock_mano and file_stock_riserva and file_ordini:
    try:
        stock_mano_df = pd.read_excel(file_stock_mano)
        stock_riserva_df = pd.read_excel(file_stock_riserva)
        ordini_df = pd.read_excel(file_ordini)

        # Rinomina colonne
        stock_mano_df = rinomina_colonne(stock_mano_df)
        stock_riserva_df = rinomina_colonne(stock_riserva_df)
        ordini_df = rinomina_colonne(ordini_df)

        # Converti quantity e requested_quantity a numerici
        stock_mano_df["quantity"] = pd.to_numeric(stock_mano_df["quantity"], errors="coerce").fillna(0)
        stock_riserva_df["quantity"] = pd.to_numeric(stock_riserva_df["quantity"], errors="coerce").fillna(0)
        ordini_df["requested_quantity"] = pd.to_numeric(ordini_df["requested_quantity"], errors="coerce").fillna(0)

        risultato = []

        for _, ordine in ordini_df.iterrows():
            item = ordine["item_code"]
            order_number = ordine["order_number"]
            richiesta = ordine["requested_quantity"]

            # Quantità in stock in mano
            stock_mano_item = stock_mano_df[stock_mano_df["item_code"] == item]
            qty_mano = stock_mano_item["quantity"].sum()

            if qty_mano >= richiesta:
                risultato.append({
                    "Order Number": order_number,
                    "Item Code": item,
                    "Requested Qty": richiesta,
                    "Disponibile in stock in mano": qty_mano,
                    "Azioni": "✅ Soddisfatto con stock in mano",
                    "Location Riserva": "-"
                })
            else:
                # Trova dove prendere il resto dallo stock riserva
                mancante = richiesta - qty_mano
                riserva_item = stock_riserva_df[stock_riserva_df["item_code"] == item]
                riserva_item = riserva_item[riserva_item["quantity"] > 0]
                riserva_item = riserva_item.sort_values("quantity", ascending=False)

                locations = []
                prelevato = 0

                for _, riga in riserva_item.iterrows():
                    if prelevato >= mancante:
                        break
                    q = riga["quantity"]
                    da_prel = min(q, mancante - prelevato)
                    prelevato += da_prel
                    locations.append(f"{riga['location']} ({int(da_prel)})")

                if prelevato >= mancante:
                    azione = "⚠️ Parziale da stock in mano, integrare da riserva"
                else:
                    azione = "❌ Quantità insufficiente anche in riserva"

                risultato.append({
                    "Order Number": order_number,
                    "Item Code": item,
                    "Requested Qty": richiesta,
                    "Disponibile in stock in mano": qty_mano,
                    "Azioni": azione,
                    "Location Riserva": "; ".join(locations) if locations else "-"
                })

        risultato_df = pd.DataFrame(risultato)

        st.subheader("📊 Risultato Analisi Disponibilità")
        st.dataframe(risultato_df, use_container_width=True)

        # Opzione download
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode("utf-8")

        csv = convert_df(risultato_df)

        st.download_button(
            label="📥 Scarica Risultato in CSV",
            data=csv,
            file_name="analisi_disponibilita.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Errore nel caricamento o analisi dei dati: {e}")
else:
    st.info("📁 Carica tutti e tre i file per iniziare l'analisi.")
