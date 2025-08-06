import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Analisi Ordini & Disponibilità Magazzino")

# Caricamento file stock in mano
stock_mano_file = st.file_uploader("📄 Carica file Stock in Mano", type=["xlsx"], key="stock_mano")
# Caricamento file stock di riserva
stock_riserva_file = st.file_uploader("📄 Carica file Stock di Riserva", type=["xlsx"], key="stock_riserva")
# Caricamento file richieste ordini
ordini_file = st.file_uploader("📄 Carica file Analisi Ordini", type=["xlsx"], key="ordini")

# Controllo caricamento file
if stock_mano_file and stock_riserva_file and ordini_file:
    stock_mano_df = pd.read_excel(stock_mano_file)
    stock_riserva_df = pd.read_excel(stock_riserva_file)
    ordini_df = pd.read_excel(ordini_file)

    # Uniforma nomi colonne
    stock_mano_df.columns = stock_mano_df.columns.str.strip().str.lower()
    stock_riserva_df.columns = stock_riserva_df.columns.str.strip().str.lower()
    ordini_df.columns = ordini_df.columns.str.strip().str.lower()

    # Rinomina colonne chiave
    stock_mano_df = stock_mano_df.rename(columns={"item code": "item_code", "quantità": "quantity", "location": "location"})
    stock_riserva_df = stock_riserva_df.rename(columns={"item code": "item_code", "quantità": "quantity", "location": "location"})
    ordini_df = ordini_df.rename(columns={"item code": "item_code", "requested_quantity": "requested_quantity", "order number": "order_number"})

    st.subheader("📊 Risultato Analisi Ordini")

    risultati = []

    for index, riga in ordini_df.iterrows():
        item = str(riga["item_code"]).strip()
        qty_richiesta = int(riga["requested_quantity"])
        order = riga["order_number"]

        # Quantità disponibile nello stock in mano
        disponibile = stock_mano_df[stock_mano_df["item_code"] == item]["quantity"].sum()

        risultato = {
            "Order Number": order,
            "Item Code": item,
            "Requested Quantity": qty_richiesta,
            "Disponibile in Mano": disponibile
        }

        if disponibile >= qty_richiesta:
            risultato["Stato"] = "✅ Quantità disponibile"
            risultato["Suggerimento"] = "-"
        else:
            mancante = qty_richiesta - disponibile
            risultato["Stato"] = f"⚠️ Mancano {mancante} pezzi"
            # Ricerca nello stock riserva solo nelle location contenenti "inventory"
            riserva_item = stock_riserva_df[
                (stock_riserva_df["item_code"] == item) &
                (stock_riserva_df["location"].str.lower().str.contains("inventory"))
            ]
            suggerimenti = []
            totale_riserva = 0

            for _, riga_riserva in riserva_item.iterrows():
                if totale_riserva >= mancante:
                    break
                preleva = min(mancante - totale_riserva, riga_riserva["quantity"])
                totale_riserva += preleva
                suggerimenti.append(f'{riga_riserva["location"]}: {preleva}')

            if suggerimenti:
                risultato["Suggerimento"] = " → ".join(sugerimenti)
            else:
                risultato["Suggerimento"] = "❌ Nessuna quantità sufficiente in riserva"

        risultati.append(risultato)

    risultati_df = pd.DataFrame(risultati)

    st.dataframe(risultati_df, use_container_width=True)

else:
    st.warning("📂 Carica tutti e tre i file per iniziare l’analisi.")
