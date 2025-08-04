import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
# Configurazione pagina
st.set_page_config(page_title="RAD-TEST", page_icon=":lente:", layout="wide")
# Logo testuale
st.markdown("# :razzo: RAD-TEST")
st.title(":pacco: Gestione Magazzino e Analisi")
# Variabili globali
soglia_alert = 20  # Soglia per avviso stock basso
# Session state per salvare lo storico
if "stock_in_mano" not in st.session_state:
    st.session_state.stock_in_mano = pd.DataFrame(columns=["Item Code", "Quantità", "Location"])
if "stock_riserva" not in st.session_state:
    st.session_state.stock_riserva = pd.DataFrame(columns=["Item Code", "Quantità", "Location"])
if "richieste" not in st.session_state:
    st.session_state.richieste = pd.DataFrame(columns=["Item Code", "Requested_quantity", "Timestamp", "Order Number"])
# Sidebar menu
pagina = st.sidebar.selectbox(":portablocco: Menu", [
    "Carica Stock In Mano",
    "Carica Stock Riserva",
    "Analisi Richieste & Suggerimenti",
    "Consulta Stock",
    "Controllo Ordini"
])
# Funzione per caricare file
def carica_file_stock(nome):
    uploaded_file = st.file_uploader(f"Carica il file {nome} (Excel)", type=["xlsx", "xls"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success(f"{nome} caricato con successo!")
        st.write(df)
        return df
    else:
        return pd.DataFrame()
# Pagina 1 — Carica Stock In Mano
if pagina == "Carica Stock In Mano":
    st.header(":pacco: Carica Stock In Mano")
    df = carica_file_stock("Stock In Mano")
    if not df.empty:
        st.session_state.stock_in_mano = pd.concat([st.session_state.stock_in_mano, df], ignore_index=True)
# Pagina 2 — Carica Stock Riserva
elif pagina == "Carica Stock Riserva":
    st.header(":fabbrica: Carica Stock Riserva")
    df = carica_file_stock("Stock Riserva")
    if not df.empty:
        st.session_state.stock_riserva = pd.concat([st.session_state.stock_riserva, df], ignore_index=True)
# Pagina 3 — Analisi Richieste & Suggerimenti
elif pagina == "Analisi Richieste & Suggerimenti":
    st.header(":grafico_a_barre: Analisi Richieste & Suggerimenti")
    uploaded_file = st.file_uploader("Carica il file delle Richieste (Excel)", type=["xlsx", "xls"])
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
            st.info("Considera di tenere sempre disponibili gli item in cima alla lista.")
# Pagina 4 — Consulta Stock
elif pagina == "Consulta Stock":
    st.header(":lente: Consulta Disponibilità Stock Totale")
    ricerca = st.text_input(":lente: Cerca Item Code")
    if ricerca:
        st.subheader(f":pacco: Stock per Item: {ricerca}")
        stock_mano = st.session_state.stock_in_mano[st.session_state.stock_in_mano["Item Code"] == ricerca]
        stock_riserva = st.session_state.stock_riserva[st.session_state.stock_riserva["Item Code"] == ricerca]
        totale = pd.concat([stock_mano, stock_riserva])
        st.write(totale)
# Pagina 5 — Controllo Ordini
elif pagina == "Controllo Ordini":
    st.header(":portablocco: Controllo Evadibilità Ordini")
    uploaded_file = st.file_uploader("Carica file ordini (Excel)", type=["xlsx", "xls"])
    if uploaded_file:
        ordini = pd.read_excel(uploaded_file)
        ordini["Order Number"] = ordini["Order Number"].astype(str)
        st.write(":pacco: Ordini da controllare:", ordini)
        stock = st.session_state.stock_in_mano.groupby("Item Code")["Quantità"].sum()
        for _, riga in ordini.iterrows():
            item = riga["Item Code"]
            richiesta = riga["Requested_quantity"]
            ordine = riga["Order Number"]
            disponibilita = stock.get(item, 0)
            if disponibilita >= richiesta:
                st.success(f":segno_spunta_bianco: Ordine {ordine} — Item {item}: DISPONIBILE ({disponibilita} disponibili)")
            else:
                st.error(f":x: Ordine {ordine} — Item {item}: NON disponibile ({disponibilita} in stock).")
                # cerca nella riserva
                riserva = st.session_state.stock_riserva[
                    (st.session_state.stock_riserva["Item Code"] == item) &
                    (st.session_state.stock_riserva["Location"].str.contains("inventory", case=False, na=False))
                ]
                if not riserva.empty:
                    st.info(f":ripeti: Disponibile in magazzino di riserva:")
                    st.write(riserva[["Location", "Quantità"]])
                else:
                    st.warning(":avviso: Nessuna riserva disponibile per questo item.")
