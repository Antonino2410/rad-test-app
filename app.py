import streamlit as st
import pandas as pd

st.title("📦 Analisi Ordini e Magazzino")

# Caricamento file
stock_file = st.file_uploader("Carica il file dello Stock in Mano", type=["xlsx"])
riserva_file = st.file_uploader("Carica il file dello Stock in Riserva", type=["xlsx"])
richieste_file = st.file_uploader("Carica il file delle Richieste Ordine", type=["xlsx"])

if stock_file and riserva_file and richieste_file:
    try:
        # Caricamento dati
        stock_df = pd.read_excel(stock_file)
        riserva_df = pd.read_excel(riserva_file)
        richieste_df = pd.read_excel(richieste_file)

        # Pulizia colonne
        stock_df.columns = stock_df.columns.str.strip().str.lower()
        riserva_df.columns = riserva_df.columns.str.strip().str.lower()
        richieste_df.columns = richieste_df.columns.str.strip().str.lower()

        # Rinomina colonne se necessario
        if "item code" in stock_df.columns:
            stock_df.rename(columns={"item code": "item_code"}, inplace=True)
        if "quantità" in stock_df.columns:
            stock_df.rename(columns={"quantità": "quantità_in_mano"}, inplace=True)

        if "item code" in riserva_df.columns:
            riserva_df.rename(columns={"item code": "item_code"}, inplace=True)
        if "quantità" in riserva_df.columns:
            riserva_df.rename(columns={"quantità": "quantità_riserva"}, inplace=True)

        if "item code" in richieste_df.columns:
            richieste_df.rename(columns={"item code": "item_code"}, inplace=True)
        if "requested quantity" in richieste_df.columns:
            richieste_df.rename(columns={"requested quantity": "requested_quantity"}, inplace=True)

        # Somma quantità totali per item
        stock_sum = stock_df.groupby("item_code")["quantità_in_mano"].sum().reset_index()
        riserva_sum = riserva_df.groupby(["item_code", "location"])["quantità_riserva"].sum().reset_index()

        # Merge richieste con stock in mano
        merged = pd.merge(richieste_df, stock_sum, on="item_code", how="left")

        # Verifica disponibilità
        merged["quantità_in_mano"] = merged["quantità_in_mano"].fillna(0)
        merged["sufficiente_in_mano"] = merged["quantità_in_mano"] >= merged["requested_quantity"]

        # Se insufficiente, suggerisci da dove prelevare
        suggerimenti = []

        for _, row in merged.iterrows():
            item = row["item_code"]
            richiesto = row["requested_quantity"]
            disponibile = row["quantità_in_mano"]
            ordine = row["order number"]

            if disponibile >= richiesto:
                suggerimenti.append("✔️ Quantità sufficiente in stock in mano")
            else:
                deficit = richiesto - disponibile
                riserva_item = riserva_sum[riserva_sum["item_code"] == item]
                riserva_item = riserva_item.sort_values("quantità_riserva", ascending=False)

                suggerito = ""
                accumulato = 0
                for _, ris in riserva_item.iterrows():
                    if accumulato >= deficit:
                        break
                    qta = ris["quantità_riserva"]
                    loc = ris["location"]
                    da_prel = min(qta, deficit - accumulato)
                    suggerito += f"Recupera {da_prel} da {loc}. "
                    accumulato += da_prel

                if suggerito == "":
                    suggerito = "❌ Quantità insufficiente anche in riserva"
                suggerimenti.append(suggerito)

        merged["suggerimento"] = suggerimenti

        st.success("Analisi completata!")
        st.write("### 📋 Risultato dell'analisi")
        st.dataframe(merged[["order number", "item_code", "requested_quantity", "quantità_in_mano", "sufficiente_in_mano", "suggerimento"]])

        # Download risultato
        csv = merged.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Scarica risultato in CSV", data=csv, file_name="analisi_magazzino.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Errore nel caricamento o analisi dei dati: {e}")
else:
    st.info("Carica tutti e tre i file per eseguire l’analisi.")
