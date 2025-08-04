import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
st.set_page_config(page_title="RAD-TEST", page_icon=":lente:", layout="wide")
st.image("rad_test_logo.png", width=200)
st.title(":pacco: RAD-TEST — Gestione Magazzino e Analisi")
soglia_alert = 20
# Stato iniziale
if "stock_in_mano" not in st.session_state:
    st.session_state.stock_in_mano = pd.DataFrame(columns=["Item Code", "Requested_quantity", "Location"])
if "stock_riserva" not in st.session_state:
    st.session_state.stock_riserva = pd.DataFrame(columns=["Item Code", "Requested_quantity", "Location"])
if "richieste" not in st.session_state:
    st.session_state.richieste = pd.DataFrame(columns=["Order Number", "Item Code", "Requested_quantity", "Timestamp"])
pagina = st.sidebar.selectbox(":portablocco: Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti",
    "Consulta Stock In Mano",
    "Consulta Stock Riserva",
    "Controllo Ordine per Order Number"
])
def carica_file_stock(nome):
    uploaded_file = st.file_uploader(f"Carica il file {nome} (Excel)", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success(f"{nome} caricato con successo!")
        st.write(df)
        return df
    return pd.DataFrame()
if pagina == "Carica Stock In Mano":
    st.header(":pacco: Carica Stock In Mano")
    df = carica_file_stock("Stock In Mano")
    if not df.empty:
        st.session_state.stock_in_mano = pd.concat([st.session_state.stock_in_mano, df], ignore_index=True)
elif pagina == "Carica Stock Riserva":
    st.header(":fabbrica: Carica Stock Riserva")
    df = carica_file_stock("Stock Riserva")
    if not df.empty:
        st.session_state.stock_riserva = pd.concat([st.session_state.stock_riserva, df], ignore_index=True)
elif pagina == "Analisi Richieste & Suggerimenti":
    st.header(":grafico_a_barre: Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica file delle Richieste (Excel)", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        st.session_state.richieste = pd.concat([st.session_state.richieste, df], ignore_index=True)
        st.success("Richieste caricate con successo!")
        st.write(st.session_state.richieste)
        un_mese_fa = datetime.now() - timedelta(days=30)
        recenti = st.session_state.richieste[st.session_state.richieste["Timestamp"] >= un_mese_fa]
        if not recenti.empty:
            st.subheader(":grafico_con_tendenza_in_aumento: Item più richiesti negli ultimi 30 giorni")
            top_items = recenti.groupby("Item Code")["Requested_quantity"].sum().sort_values(ascending=False)
            st.write(top_items)
            fig, ax = plt.subplots()
            top_items.plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
            ax.set_ylabel("")
            st.pyplot(fig)
            st.subheader(":lampadina: Suggerimento:")
            st.info("Tieni disponibili gli item più richiesti.")
elif pagina == "Consulta Stock In Mano":
    st.header(":lente: Consulta Stock In Mano")
    if st.session_state.stock_in_mano.empty:
        st.warning(":avviso: Nessun stock in mano caricato.")
    else:
        item = st.selectbox("Seleziona un Item Code", st.session_state.stock_in_mano["Item Code"].unique())
        filtro = st.session_state.stock_in_mano[st.session_state.stock_in_mano["Item Code"] == item]
        st.write(filtro)
        totale = filtro["Requested_quantity"].sum()
        if totale < soglia_alert:
            st.error(f":avviso: Quantità sotto soglia ({totale})")
            riserva = st.session_state.stock_riserva[st.session_state.stock_riserva["Item Code"] == item]
            if not riserva.empty:
                st.info(f":freccia_destra: Disponibile nella riserva: {riserva['Requested_quantity'].sum()}")
                st.write(riserva)
            else:
                st.warning("Nessuna riserva disponibile.")
elif pagina == "Consulta Stock Riserva":
    st.header(":lente: Consulta Stock Riserva")
    if st.session_state.stock_riserva.empty:
        st.warning(":avviso: Nessun stock di riserva caricato.")
    else:
        item = st.selectbox("Seleziona un Item Code", st.session_state.stock_riserva["Item Code"].unique())
        filtro = st.session_state.stock_riserva[st.session_state.stock_riserva["Item Code"] == item]
        st.write(filtro)
elif pagina == "Controllo Ordine per Order Number":
    st.header(":pacco: Controllo Ordini in Base a Order Number")
    if st.session_state.richieste.empty:
        st.warning(":avviso: Nessun ordine caricato.")
    else:
        ordine = st.selectbox("Seleziona un Order Number", st.session_state.richieste["Order Number"].unique())
        df_ordine = st.session_state.richieste[st.session_state.richieste["Order Number"] == ordine]
        st.write(df_ordine)
        for _, row in df_ordine.iterrows():
            item = row["Item Code"]
            qta_richiesta = row["Requested_quantity"]
            qta_stock = st.session_state.stock_in_mano[
                st.session_state.stock_in_mano["Item Code"] == item
            ]["Requested_quantity"].sum()
            if qta_stock >= qta_richiesta:
                st.success(f":segno_spunta_bianco: {item} — quantità disponibile ({qta_stock})")
            else:
                st.error(f":x: {item} — quantità insufficiente ({qta_stock} su {qta_richiesta})")
                riserva = st.session_state.stock_riserva[
                    (st.session_state.stock_riserva["Item Code"] == item) &
                    (st.session_state.stock_riserva["Location"].str.contains("inventory", case=False, na=False))
                ]
                if not riserva.empty:
                    st.info(":pacco: Disponibile in riserva:")
                    st.write(riserva[["Location", "Requested_quantity"]])
                else:
                    st.warning(":x: Nessuna riserva disponibile contenente 'inventory'")
