import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analisi Stock e Ordini", layout="wide")

st.title("🔍 Analisi disponibilità stock per Order Number")

# Upload file stock in mano
stock_mano_file = st.file_uploader("Carica file Stock in Mano", type=["xlsx", "xls"], key="stock_mano")
# Upload file stock in riserva
stock_riserva_file = st.file_uploader("Carica file Stock in Riserva", type=["xlsx", "xls"], key="stock_riserva")
# Upload file richieste ordini
ordini_file = st.file_uploader("Carica file Ordini (con Order Number e richieste)", type=["xlsx", "xls"], key="ordini")

if stock_mano_file and stock_riserva_file and ordini_file:
    try:
        # Leggi i file caricati
        df_mano = pd.read_excel(stock_mano_file)
        df_riserva = pd.read_excel(stock_riserva_file)
        df_ordini = pd.read_excel(ordini_file)

        # Normalizza i nomi delle colonne
        df_mano.columns = df_mano.columns.str.strip().str.lower()
        df_riserva.columns = df_riserva.columns.str.strip().str.lower()
        df_ordini.columns = df_ordini.columns.str.strip().str.lower()

        # Controllo colonne essenziali
        required_cols = ["item code", "quantità", "location"]
        for col in required_cols:
            if col not in df_mano.columns or col not in df_riserva.columns:
                st.error(f"Manca la colonna '{col}' in uno dei file di stock.")
                st.stop()

        if "order number" not in df_ordini.columns or "item code" not in df_ordini.columns or "requested quantity" not in df_ordini.columns:
            st.error("Il file ordini deve contenere le colonne 'Order Number', 'Item Code', 'Requested Quantity'.")
            st.stop()

        # Analisi
        risultati = []

        for _, row in df_ordini.iterrows():
            order = row["order number"]
            item = row["item code"]
            richiesta = row["requested quantity"]

            # Quantità disponibile in stock in mano
            in_mano = df_mano[df_mano["item code"] == item]["quantità"].sum()

            if in_mano >= richiesta:
                risultati.append({
                    "Order Number": order,
                    "Item Code": item,
                    "Quantità Richiesta": richiesta,
                    "Quantità In Mano": in_mano,
                    "Quantità da Riserva": 0,
                    "Location Riserva": ""
                })
            else:
                # Calcolo mancante
                mancante = richiesta - in_mano
                riserva_item = df_riserva[df_riserva["item code"] == item].copy()

                riserva_item = riserva_item.sort_values(by="quantità", ascending=False)

                locations_utilizzate = []
                quantità_totale_ricavata = 0

                for _, riga in riserva_item.iterrows():
                    q = riga["quantità"]
                    loc = riga["location"]
                    if quantità_totale_ricavata + q <= mancante:
                        quantità_totale_ricavata += q
                        locations_utilizzate.append(f"{loc} ({q})")
                    else:
                        q_needed = mancante - quantità_totale_ricavata
                        quantità_totale_ricavata += q_needed
                        locations_utilizzate.append(f"{loc} ({q_needed})")
                        break

                risultati.append({
                    "Order Number": order,
                    "Item Code": item,
                    "Quantità Richiesta": richiesta,
                    "Quantità In Mano": in_mano,
                    "Quantità da Riserva": quantità_totale_ricavata,
                    "Location Riserva": "; ".join(locations_utilizzate)
                })

        risultati_df = pd.DataFrame(risultati)

        st.success("✅ Analisi completata con successo!")
        st.dataframe(risultati_df, use_container_width=True)

        # Download risultati
        csv = risultati_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Scarica risultati in CSV", data=csv, file_name="analisi_ordini.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Errore nell'analisi: {e}")
else:
    st.info("Carica tutti i file per iniziare l'analisi.")
