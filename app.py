import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestione Stock", layout="wide")
st.title("📦 Gestione Stock & Analisi Ordini")

# Funzione per rinominare le colonne in modo intelligente
def rinomina_colonne(df):
    cols_lower = df.columns.str.strip().str.lower()
    mapping = {}
    for orig, lower in zip(df.columns, cols_lower):
        if "item" in lower and "code" in lower:
            mapping[orig] = "item_code"
        elif "quant" in lower and "request" not in lower:
            mapping[orig] = "quantity"
        elif "loc" in lower:
            mapping[orig] = "location"
        elif "order" in lower and "number" in lower:
            mapping[orig] = "order_number"
        elif "request" in lower:
            mapping[orig] = "requested_quantity"
    return df.rename(columns=mapping)

# Upload file
st.sidebar.header("📁 Carica i file")

file_stock_mano = st.sidebar.file_uploader("Stock in mano", type=["xlsx", "xls", "csv"])
file_stock_riserva = st.sidebar.file_uploader("Stock in riserva", type=["xlsx", "xls", "csv"])
file_ordini = st.sidebar.file_uploader("File ordini", type=["xlsx", "xls", "csv"])

if file_stock_mano and file_stock_riserva and file_ordini:
    try:
        stock_mano_df = pd.read_excel(file_stock_mano) if file_stock_mano.name.endswith(("xlsx", "xls")) else pd.read_csv(file_stock_mano)
        stock_riserva_df = pd.read_excel(file_stock_riserva) if file_stock_riserva.name.endswith(("xlsx", "xls")) else pd.read_csv(file_stock_riserva)
        ordini_df = pd.read_excel(file_ordini) if file_ordini.name.endswith(("xlsx", "xls")) else pd.read_csv(file_ordini)

        # Rinomina colonne
        stock_mano_df = rinomina_colonne(stock_mano_df)
        stock_riserva_df = rinomina_colonne(stock_riserva_df)
        ordini_df = rinomina_colonne(ordini_df)

        # Debug visivo
        # st.write("Colonne stock_mano:", stock_mano_df.columns.tolist())
        # st.write("Colonne stock_riserva:", stock_riserva_df.columns.tolist())
        # st.write("Colonne ordini:", ordini_df.columns.tolist())

        risultati = []

        for _, riga in ordini_df.iterrows():
            item = riga["item_code"]
            order_n = riga["order_number"]
            richiesta = riga["requested_quantity"]

            stock_disponibile = stock_mano_df[stock_mano_df["item_code"] == item]["quantity"].sum()

            if stock_disponibile >= richiesta:
                risultati.append({
                    "Order Number": order_n,
                    "Item Code": item,
                    "Quantità richiesta": richiesta,
                    "Quantità disponibile (mano)": stock_disponibile,
                    "Status": "✔️ Stock sufficiente",
                    "Suggerimento": "-"
                })
            else:
                mancante = richiesta - stock_disponibile

                riserva_righe = stock_riserva_df[stock_riserva_df["item_code"] == item]
                riserva_righe = riserva_righe[riserva_righe["quantity"] > 0]

                suggerimenti = []
                for _, riga_r in riserva_righe.iterrows():
                    loc = riga_r["location"]
                    qta_loc = riga_r["quantity"]

                    if mancante <= 0:
                        break

                    take = min(mancante, qta_loc)
                    suggerimenti.append(f"{take} da {loc}")
                    mancante -= take

                risultati.append({
                    "Order Number": order_n,
                    "Item Code": item,
                    "Quantità richiesta": richiesta,
                    "Quantità disponibile (mano)": stock_disponibile,
                    "Status": "⚠️ Stock insufficiente",
                    "Suggerimento": ", ".join(suggerimenti) if suggerimenti else "🔴 Nessuna riserva disponibile"
                })

        risultati_df = pd.DataFrame(risultati)

        st.subheader("📊 Analisi Ordini")
        st.dataframe(risultati_df, use_container_width=True)

    except Exception as e:
        st.error(f"Errore nel caricamento o analisi dei dati: {e}")

else:
    st.warning("📌 Carica tutti e tre i file per iniziare l’analisi.")
