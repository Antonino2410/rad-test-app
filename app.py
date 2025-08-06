import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestione Ordini", layout="wide")

st.title("📦 Analisi Disponibilità Ordini")

# Caricamento file
stock_file = st.file_uploader("📥 Carica file Stock In Mano", type=["xlsx"])
riserva_file = st.file_uploader("📥 Carica file Stock Riserva", type=["xlsx"])
ordini_file = st.file_uploader("📥 Carica file Ordini", type=["xlsx"])

if stock_file and riserva_file and ordini_file:
    # Caricamento e normalizzazione colonne
    stock_df = pd.read_excel(stock_file)
    riserva_df = pd.read_excel(riserva_file)
    ordini_df = pd.read_excel(ordini_file)

    # Pulizia nomi colonne per evitare KeyError
    stock_df.columns = stock_df.columns.str.strip().str.lower()
    riserva_df.columns = riserva_df.columns.str.strip().str.lower()
    ordini_df.columns = ordini_df.columns.str.strip().str.lower()

    # Campo da usare
    col_item = "item code"
    col_qty = "quantità"
    col_order = "order number"
    col_location = "location"

    st.subheader("🔍 Verifica Ordine")
    ordine_selezionato = st.selectbox("Seleziona Order Number", ordini_df[col_order].unique())

    if ordine_selezionato:
        # Filtra le righe dell'ordine selezionato
        ordine_df = ordini_df[ordini_df[col_order] == ordine_selezionato]
        risultati = []

        for _, riga in ordine_df.iterrows():
            item = riga[col_item]
            richiesto = riga["requested quantity"]

            # Calcolo disponibilità reale in mano
            in_mano_df = stock_df[stock_df[col_item] == item]
            disponibilità = in_mano_df[col_qty].sum()

            if disponibilità >= richiesto:
                risultati.append({
                    "Item": item,
                    "Richiesto": richiesto,
                    "Disponibile In Mano": disponibilità,
                    "Prelievo Riserva": "Non necessario"
                })
            else:
                mancante = richiesto - disponibilità
                # Trova da stock di riserva dove c'è disponibilità per l'item
                riserva_match = riserva_df[(riserva_df[col_item] == item) & 
                                           (riserva_df[col_location].str.lower().str.contains("inventory"))]

                suggerimenti = []
                for _, entry in riserva_match.iterrows():
                    q = entry[col_qty]
                    loc = entry[col_location]
                    if mancante <= 0:
                        break
                    da_prendere = min(mancante, q)
                    suggerimenti.append(f"{da_prendere} da {loc}")
                    mancante -= da_prendere

                suggerimento_finale = ", ".join(suggerimenti) if suggerimenti else "Non disponibile in riserva"

                risultati.append({
                    "Item": item,
                    "Richiesto": richiesto,
                    "Disponibile In Mano": disponibilità,
                    "Prelievo Riserva": suggerimento_finale
                })

        risultati_df = pd.DataFrame(risultati)
        st.dataframe(risultati_df, use_container_width=True)

else:
    st.info("📄 Carica tutti e tre i file per iniziare l'analisi.")
