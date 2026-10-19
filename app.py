import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import datetime
import importlib

import database
import scraper
import analytics

importlib.reload(database)
importlib.reload(scraper)
importlib.reload(analytics)

from database import (
    init_db,
    DB_NAME,
    REGIONI_ITALIA,
    ALIMENTAZIONI_LIST,
    DEFAULT_DEAL_WEIGHTS,
    get_deal_score_weights,
    save_deal_score_weights,
    escludi_annuncio_db,
    ripristina_annuncio_escluso_db,
)
from scraper import run_scraper
from analytics import calcola_statistiche_e_deal_score, toggle_favorite_db

# Configurazione Pagina Streamlit in stile OpenCode (Minimal & Dark/Clean)
st.set_page_config(
    page_title="CARSCRAPER — Segmento B Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Iniezione CSS personalizzato in stile OpenCode (Minimal, bordi netti, sfondi scuri/neutri)
st.markdown("""
<style>
    /* Stile generale e font minimal */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header e Titoli */
    h1, h2, h3, h4 {
        color: #ffffff;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    /* Card / Container minimal */
    div.stMarkdown container, div[data-testid="stVerticalBlock"] > div {
        border-radius: 6px;
    }
    
    /* Bottoni ad alto contrasto e ben evidenti */
    .stButton > button {
        background-color: #238636;
        color: #ffffff;
        border: 1px solid rgba(240, 246, 252, 0.1);
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #2ea043;
        border-color: #f0f6fc;
    }
    
    /* Bottoni secondari o di reset */
    button[kind="secondary"] {
        background-color: #21262d !important;
        color: #f85149 !important;
        border: 1px solid rgba(248, 81, 73, 0.4) !important;
    }
    button[kind="secondary"]:hover {
        background-color: #30363d !important;
    }
    
    /* Sidebar minimal */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Tabelle e DataFrame */
    div[data-testid="stDataFrame"] {
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    
    /* Link stilizzati */
    a.link-annuncio {
        color: #58a6ff;
        text-decoration: none;
        font-weight: 500;
    }
    a.link-annuncio:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# Inizializza DB all'avvio
init_db()

# --- HEADER PRINCIPALE ---
st.markdown("### ⚡ CARSCRAPER <small style='color: #8b949e; font-size: 14px;'>Monitoraggio & Analisi Segmento B</small>", unsafe_allow_html=True)

# --- NAVIGAZIONE A 4 TAB ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🛠️ 1. Alimentazione & Regioni", 
    "📥 2. Scraping & Raccolta Dati", 
    "📊 3. Statistiche & Deal Score", 
    "⚙️ 4. Area DEV & Manutenzione"
])

# ==========================================
# TAB 1: Configurazione Alimentazione & Regioni
# ==========================================
with tab1:
    st.markdown("#### Configurazione Alimentazione & Regioni")
    st.markdown("<small style='color: #8b949e;'>Seleziona le tipologie di alimentazione e le regioni da monitorare (nessun filtro preimpostato sui modelli).</small>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alimentazioni_watchlist ORDER BY carburante")
    carbs_rows = cursor.fetchall()
    cursor.execute("SELECT * FROM regioni_watchlist ORDER BY regione")
    regioni_rows = cursor.fetchall()
    conn.close()
    
    df_carbs = pd.DataFrame([dict(row) for row in carbs_rows]) if carbs_rows else pd.DataFrame({"carburante": ALIMENTAZIONI_LIST, "is_selected": 1})
    df_regioni = pd.DataFrame([dict(row) for row in regioni_rows]) if regioni_rows else pd.DataFrame({"regione": REGIONI_ITALIA, "is_selected": 1})
    
    carbs_list = sorted(df_carbs['carburante'].unique().tolist())
    regioni_list = sorted(df_regioni['regione'].unique().tolist())
    
    active_carb_df = df_carbs[df_carbs['is_selected'] == 1]
    active_reg_df = df_regioni[df_regioni['is_selected'] == 1]
    default_carbs = sorted(active_carb_df['carburante'].unique().tolist()) if not active_carb_df.empty else carbs_list
    default_regioni = sorted(active_reg_df['regione'].unique().tolist()) if not active_reg_df.empty else regioni_list
    
    if "tab1_carbs" not in st.session_state:
        st.session_state.tab1_carbs = default_carbs
    if "tab1_regions" not in st.session_state:
        st.session_state.tab1_regions = default_regioni
    if "w_tab1_carbs" not in st.session_state:
        st.session_state.w_tab1_carbs = st.session_state.tab1_carbs
    if "w_tab1_regions" not in st.session_state:
        st.session_state.w_tab1_regions = st.session_state.tab1_regions

    def _select_all_carbs():
        st.session_state.tab1_carbs = list(carbs_list)
        st.session_state.w_tab1_carbs = list(carbs_list)
        c = sqlite3.connect(DB_NAME)
        c.execute("UPDATE alimentazioni_watchlist SET is_selected = 1")
        c.commit()
        c.close()

    def _clear_all_carbs():
        st.session_state.tab1_carbs = []
        st.session_state.w_tab1_carbs = []
        c = sqlite3.connect(DB_NAME)
        c.execute("UPDATE alimentazioni_watchlist SET is_selected = 0")
        c.commit()
        c.close()

    def _select_all_regions():
        st.session_state.tab1_regions = list(regioni_list)
        st.session_state.w_tab1_regions = list(regioni_list)
        c = sqlite3.connect(DB_NAME)
        c.execute("UPDATE regioni_watchlist SET is_selected = 1")
        c.commit()
        c.close()

    def _clear_all_regions():
        st.session_state.tab1_regions = []
        st.session_state.w_tab1_regions = []
        c = sqlite3.connect(DB_NAME)
        c.execute("UPDATE regioni_watchlist SET is_selected = 0")
        c.commit()
        c.close()

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_carbs = st.multiselect("Filtra Alimentazione", carbs_list, key="w_tab1_carbs")
        st.session_state.tab1_carbs = selected_carbs
    with col_f2:
        selected_regions = st.multiselect("Filtra Regioni", regioni_list, key="w_tab1_regions")
        st.session_state.tab1_regions = selected_regions
        
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        st.button("Tutte le Alimentazioni", on_click=_select_all_carbs)
    with col_btn2:
        st.button("Svuota Alimentazioni", type="secondary", on_click=_clear_all_carbs)
    with col_btn3:
        st.button("Tutte le Regioni", on_click=_select_all_regions)
    with col_btn4:
        st.button("Svuota Regioni", type="secondary", on_click=_clear_all_regions)

    # Sincronizza immediatamente in DB le alimentazioni e le regioni selezionate
    conn = sqlite3.connect(DB_NAME)
    conn.execute("UPDATE alimentazioni_watchlist SET is_selected = 0")
    for c_name in selected_carbs:
        conn.execute("UPDATE alimentazioni_watchlist SET is_selected = 1 WHERE carburante = ?", (c_name,))

    conn.execute("UPDATE regioni_watchlist SET is_selected = 0")
    for reg_name in selected_regions:
        conn.execute("UPDATE regioni_watchlist SET is_selected = 1 WHERE regione = ?", (reg_name,))

    # Rimuove da annunci eventuali auto non appartenenti alle alimentazioni o regioni selezionate
    conn.execute("""
        DELETE FROM annunci
        WHERE is_favorite = 0
          AND (
              NOT EXISTS (
                  SELECT 1 FROM alimentazioni_watchlist aw
                  WHERE aw.is_selected = 1
                    AND aw.carburante = annunci.carburante
              )
              OR NOT EXISTS (
                  SELECT 1 FROM regioni_watchlist r
                  WHERE r.is_selected = 1
                    AND r.regione = annunci.regione
              )
          )
    """)
    conn.commit()
    conn.close()
            
    if st.button("💾 Salva Configurazione", type="primary"):
        st.success(f"✅ Configurazione salvata! ({len(selected_carbs)} alimentazioni e {len(selected_regions)} regioni attive)")

    st.markdown("---")
    st.markdown("#### ⚖️ Impostazioni Pesi Parametri Deal Score")
    st.markdown(
        "<small style='color: #8b949e;'>Personalizza il peso di ciascun parametro nel calcolo del Deal Score (0-100). Di default vengono usati i pesi attuali: Prezzo (45), KM (15), Anno (12), Potenza CV (5).</small>",
        unsafe_allow_html=True,
    )

    current_weights = get_deal_score_weights()
    if "w_peso_prezzo" not in st.session_state:
        st.session_state.w_peso_prezzo = float(current_weights["peso_prezzo"])
    if "w_peso_km" not in st.session_state:
        st.session_state.w_peso_km = float(current_weights["peso_km"])
    if "w_peso_anno" not in st.session_state:
        st.session_state.w_peso_anno = float(current_weights["peso_anno"])
    if "w_peso_cv" not in st.session_state:
        st.session_state.w_peso_cv = float(current_weights["peso_cv"])

    def _reset_default_weights():
        st.session_state.w_peso_prezzo = float(DEFAULT_DEAL_WEIGHTS["peso_prezzo"])
        st.session_state.w_peso_km = float(DEFAULT_DEAL_WEIGHTS["peso_km"])
        st.session_state.w_peso_anno = float(DEFAULT_DEAL_WEIGHTS["peso_anno"])
        st.session_state.w_peso_cv = float(DEFAULT_DEAL_WEIGHTS["peso_cv"])
        save_deal_score_weights(
            DEFAULT_DEAL_WEIGHTS["peso_prezzo"],
            DEFAULT_DEAL_WEIGHTS["peso_km"],
            DEFAULT_DEAL_WEIGHTS["peso_anno"],
            DEFAULT_DEAL_WEIGHTS["peso_cv"],
        )

    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        peso_prezzo = st.slider("💰 Peso Prezzo vs Mercato", 0.0, 100.0, step=1.0, key="w_peso_prezzo")
    with col_w2:
        peso_km = st.slider("🛣️ Peso Chilometraggio (KM)", 0.0, 50.0, step=1.0, key="w_peso_km")
    with col_w3:
        peso_anno = st.slider("🗓️ Peso Anno Immatricolazione", 0.0, 50.0, step=1.0, key="w_peso_anno")
    with col_w4:
        peso_cv = st.slider("🐎 Peso Potenza (CV)", 0.0, 30.0, step=1.0, key="w_peso_cv")

    save_deal_score_weights(peso_prezzo, peso_km, peso_anno, peso_cv)

    col_wb1, col_wb2 = st.columns([1, 3])
    with col_wb1:
        st.button("🔄 Ripristina Pesi di Default", type="secondary", on_click=_reset_default_weights)
    with col_wb2:
        st.markdown(
            f"<small style='color: #8b949e; line-height: 2.5;'>Pesi attivi — Prezzo: <b>{peso_prezzo}</b> (default 45.0) | KM: <b>{peso_km}</b> (default 15.0) | Anno: <b>{peso_anno}</b> (default 12.0) | CV: <b>{peso_cv}</b> (default 5.0)</small>",
            unsafe_allow_html=True,
        )

# ==========================================
# TAB 2: Scraping & Raccolta Dati
# ==========================================
with tab2:
    st.markdown("#### Scraping Annunci Reali & Ingestion")
    st.markdown("<small style='color: #8b949e;'>Raccolta annunci reali da AutoScout24 e Subito.it con link diretti al singolo annuncio, località e regione.</small>", unsafe_allow_html=True)
    
    # Inizializza session state per i filtri a monte se non presenti
    if 'scrape_portali' not in st.session_state:
        st.session_state.scrape_portali = ["AutoScout24", "Subito.it"]

    portali_scelti = st.multiselect(
        "Portali", 
        ["AutoScout24", "Subito.it"], 
        default=st.session_state.scrape_portali,
        key="w_portali"
    )
    st.session_state.scrape_portali = portali_scelti

    # Filtri a monte dello scraping (da - a) con i valori default richiesti
    st.markdown("##### ⚙️ Parametri & Filtri di Ricerca (Persistenti)")
    
    if 'scrape_prezzo_min' not in st.session_state:
        st.session_state.scrape_prezzo_min = 0
    if 'scrape_prezzo_max' not in st.session_state:
        st.session_state.scrape_prezzo_max = 15000
    if 'scrape_km_min' not in st.session_state:
        st.session_state.scrape_km_min = 0
    if 'scrape_km_max' not in st.session_state:
        st.session_state.scrape_km_max = 30000
    if 'scrape_anno_min' not in st.session_state:
        st.session_state.scrape_anno_min = 2015
    if 'scrape_anno_max' not in st.session_state:
        st.session_state.scrape_anno_max = 2026

    col_f_m1, col_f_m2, col_f_m3 = st.columns(3)
    with col_f_m1:
        st.markdown("**Prezzo (€)**")
        p_min, p_max = st.slider("Range Prezzo", 0, 50000, (st.session_state.scrape_prezzo_min, st.session_state.scrape_prezzo_max), step=500, key="w_pr_range")
        st.session_state.scrape_prezzo_min, st.session_state.scrape_prezzo_max = p_min, p_max
    with col_f_m2:
        st.markdown("**Chilometraggio (km)**")
        km_min, km_max = st.slider("Range KM", 0, 300000, (st.session_state.scrape_km_min, st.session_state.scrape_km_max), step=5000, key="w_km_range")
        st.session_state.scrape_km_min, st.session_state.scrape_km_max = km_min, km_max
    with col_f_m3:
        st.markdown("**Anno Immatricolazione**")
        a_min, a_max = st.slider("Range Anno", 2011, 2026, (st.session_state.scrape_anno_min, st.session_state.scrape_anno_max), step=1, key="w_an_range")
        st.session_state.scrape_anno_min, st.session_state.scrape_anno_max = a_min, a_max

    if st.button("🚀 Avvia Scraping con Filtri", type="primary"):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        selected_carbs_db = [r["carburante"] for r in conn.execute("SELECT carburante FROM alimentazioni_watchlist WHERE is_selected = 1").fetchall()]
        selected_regs = [r["regione"] for r in conn.execute("SELECT regione FROM regioni_watchlist WHERE is_selected = 1").fetchall()]
        conn.close()
        
        if not selected_carbs_db:
            st.error("⚠️ Seleziona almeno un'alimentazione nel Tab 1.")
        elif not selected_regs:
            st.error("⚠️ Seleziona almeno una regione nel Tab 1.")
        elif not portali_scelti:
            st.error("⚠️ Seleziona almeno un portale.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_prog(current, total, msg):
                pct = min(1.0, current / float(max(1, total)))
                progress_bar.progress(pct)
                status_text.text(f"Stato: {msg} ({current}/{total})")
                
            with st.spinner("Estrazione annunci reali in corso da AutoScout24 e Subito.it..."):
                tot_salvati = run_scraper(
                    selected_carbs=selected_carbs_db,
                    portali=st.session_state.scrape_portali,
                    max_entries=1000000,
                    data_filtro="tutti",
                    p_min=st.session_state.scrape_prezzo_min,
                    p_max=st.session_state.scrape_prezzo_max,
                    km_min=st.session_state.scrape_km_min,
                    km_max=st.session_state.scrape_km_max,
                    a_min=st.session_state.scrape_anno_min,
                    a_max=st.session_state.scrape_anno_max,
                    selected_regions=selected_regs,
                    progress_callback=update_prog
                )
                
            progress_bar.progress(1.0)
            st.success(f"🎉 Scraping completato! Salvati/Aggiornati **{tot_salvati}** annunci con link diretti verificati.")

    # Gestione & Reset Tab 2
    st.markdown("---")
    col_mgmt1, col_mgmt2 = st.columns([1, 3])
    with col_mgmt1:
        if st.button("🗑️ Svuota Tabella Annunci", type="secondary"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM annunci")
            conn.commit()
            conn.close()
            st.success("✅ Tabella annunci svuotata!")
            st.rerun()
    with col_mgmt2:
        st.markdown("<small style='color: #8b949e; line-height: 2.5;'>Elimina gli annunci raccolti senza modificare la Watchlist o i log.</small>", unsafe_allow_html=True)

    st.markdown("#### 📋 Griglia Annunci Raccolti & Link Diretti")
    mostra_inc_tab2 = st.checkbox("🚨 Mostra anche auto incidentate / sinistrate (nascoste di default)", value=False, key="chk_inc_tab2")
    conn = sqlite3.connect(DB_NAME)
    df_annunci_preview = pd.read_sql("""
        SELECT DISTINCT a.id, a.portale, a.marca, a.modello, a.versione, a.prezzo, a.anno, a.km, a.carburante,
                        a.localita, a.regione, a.is_incidentata, a.tipo_venditore, a.data_annuncio, a.url
        FROM annunci a
        INNER JOIN alimentazioni_watchlist aw
            ON a.carburante = aw.carburante
        INNER JOIN regioni_watchlist r
            ON a.regione = r.regione
        WHERE aw.is_selected = 1
          AND r.is_selected = 1
          AND a.id NOT IN (SELECT id FROM annunci_esclusi)
          AND a.url NOT IN (SELECT url FROM annunci_esclusi WHERE url IS NOT NULL AND url != '')
        ORDER BY a.data_annuncio DESC
    """, conn)
    conn.close()

    if not df_annunci_preview.empty:
        num_inc_t2 = int((df_annunci_preview["is_incidentata"] == 1).sum())
        if not mostra_inc_tab2:
            df_annunci_preview = df_annunci_preview[df_annunci_preview["is_incidentata"] == 0]
        df_annunci_preview["stato"] = df_annunci_preview["is_incidentata"].apply(lambda x: "🚨 Incidentata" if int(x) == 1 else "✅ Integra")
    else:
        num_inc_t2 = 0
    
    if df_annunci_preview.empty:
        st.info("Nessun annuncio presente nel database per i filtri selezionati.")
    else:
        st.markdown(f"<small style='color: #8b949e;'>Totale annunci visualizzati: **{len(df_annunci_preview)}** (Auto incidentate rilevate e nascoste/flaggate: **{num_inc_t2}**)</small>", unsafe_allow_html=True)
        st.dataframe(
            df_annunci_preview.drop(columns=["id", "is_incidentata"]),
            width='stretch',
            column_config={
                "url": st.column_config.LinkColumn("Link Annuncio", display_text="🔗 Apri Annuncio"),
                "localita": "Località",
                "regione": "Regione",
                "stato": "Stato",
                "prezzo": st.column_config.NumberColumn("Prezzo (€)", format="€ %d"),
                "km": st.column_config.NumberColumn("KM", format="%d km"),
            }
        )
        for idx, row in df_annunci_preview.head(30).iterrows():
            inc_badge = " | 🚨 **INCIDENTATA**" if int(row['is_incidentata']) == 1 else ""
            col_p1, col_p2 = st.columns([5, 1])
            with col_p1:
                st.markdown(f"""
                - **{row['marca']} {row['modello']}** ({row['anno']} - {row['km']:,} km) | **€ {row['prezzo']:,}** | ⛽ {row['carburante']} | 📍 **{row['localita']} ({row['regione']})** | 🏛️ {row['portale']}{inc_badge}
                &nbsp;&nbsp;&nbsp;&nbsp;🔗 [Apri Singolo Annuncio Diretto]({row['url']})
                """)
            with col_p2:
                if st.button("🚫 Escludi", key=f"del_t2_{row['id']}", type="secondary"):
                    escludi_annuncio_db(row["id"], row["url"], f"{row['marca']} {row['modello']} ({row['anno']}) - € {row['prezzo']}")
                    st.rerun()
            st.divider()

# ==========================================
# Tab 3: Statistiche & Algoritmo di Convenienza
# ==========================================
with tab3:
    st.markdown("#### Analisi di Mercato & Deal Score")
    st.markdown("<small style='color: #8b949e;'>Valutazione oggettiva della convenienza (0-100) basata su prezzo di mercato, km, anno e potenza. Le auto incidentate/sinistrate sono escluse da tutti i calcoli di prezzo e metriche.</small>", unsafe_allow_html=True)
    
    df_analyzed = calcola_statistiche_e_deal_score()
    
    if df_analyzed.empty:
        st.warning("Nessun dato disponibile per i modelli, le alimentazioni e le regioni selezionate. Esegui lo scraping nel Tab 2.")
    else:
        tot_incidentate = int((df_analyzed["is_incidentata"] == 1).sum())
        col_chk1, col_chk2 = st.columns(2)
        with col_chk1:
            solo_preferiti = st.checkbox("⭐ Mostra solo Preferiti")
        with col_chk2:
            mostra_incidentate = st.checkbox(
                f"🚨 Mostra auto incidentate / sinistrate ({tot_incidentate} rilevate — escluse dalle metriche)",
                value=False,
                key="chk_inc_tab3",
            )

        df_base = df_analyzed if mostra_incidentate else df_analyzed[df_analyzed["is_incidentata"] == 0]

        if df_base.empty:
            st.info("Nessun annuncio integro disponibile per i filtri selezionati.")
        else:
            # Filtri Avanzati Richiesti
            st.markdown("##### 🔍 Filtri Avanzati di Ricerca")
            col_f0, col_f0m, col_f1, col_f1r, col_f2, col_f3, col_f4, col_f5 = st.columns(8)
            with col_f0:
                brand_filter = st.selectbox("Marca", ["Tutti"] + sorted(df_base['marca'].unique().tolist()))
            with col_f0m:
                models_for_brand = df_base[df_base['marca'] == brand_filter]['modello'].unique().tolist() if brand_filter != "Tutti" else df_base['modello'].unique().tolist()
                model_filter = st.selectbox("Modello", ["Tutti"] + sorted(models_for_brand))
            with col_f1:
                carb_filter = st.selectbox("Alimentazione", ["Tutti"] + sorted(df_base['carburante'].unique().tolist()))
            with col_f1r:
                reg_filter = st.selectbox("Regione", ["Tutte"] + sorted(df_base['regione'].dropna().unique().tolist()))
            with col_f2:
                p_low, p_high = int(df_base['prezzo'].min()), max(int(df_base['prezzo'].min()) + 500, int(df_base['prezzo'].max()))
                max_prezzo = st.slider("Prezzo Max (€)", p_low, p_high, p_high, step=500)
            with col_f3:
                k_low, k_high = int(df_base['km'].min()), max(int(df_base['km'].min()) + 1000, int(df_base['km'].max()))
                max_km = st.slider("KM Max", k_low, k_high, k_high, step=1000)
            with col_f4:
                a_low, a_high = int(df_base['anno'].min()), max(int(df_base['anno'].min()) + 1, int(df_base['anno'].max()))
                min_anno = st.slider("Anno Min", a_low, a_high, a_low, step=1)
            with col_f5:
                ordinamento = st.selectbox("Ordinamento", ["Deal Score (Decr)", "Prezzo (Cres)", "Km (Cres)", "Anno (Rec)"])
                
            df_view = df_base.copy()
            if brand_filter != "Tutti":
                df_view = df_view[df_view['marca'] == brand_filter]
            if model_filter != "Tutti":
                df_view = df_view[df_view['modello'] == model_filter]
            if carb_filter != "Tutti":
                df_view = df_view[df_view['carburante'] == carb_filter]
            if reg_filter != "Tutte":
                df_view = df_view[df_view['regione'] == reg_filter]
                
            # Applicazione filtri avanzati km, prezzo, anno
            df_view = df_view[
                (df_view['prezzo'] <= max_prezzo) &
                (df_view['km'] <= max_km) &
                (df_view['anno'] >= min_anno)
            ]
            
            if solo_preferiti:
                df_view = df_view[df_view['is_favorite'] == 1]
                
            if ordinamento == "Deal Score (Decr)":
                df_view = df_view.sort_values(by="deal_score", ascending=False)
            elif ordinamento == "Prezzo (Cres)":
                df_view = df_view.sort_values(by="prezzo", ascending=True)
            elif ordinamento == "Km (Cres)":
                df_view = df_view.sort_values(by="km", ascending=True)
            elif ordinamento == "Anno (Rec)":
                df_view = df_view.sort_values(by="anno", ascending=False)

            st.markdown(f"<small style='color: #8b949e;'>Visualizzazione di {len(df_view)} annunci filtrati</small>", unsafe_allow_html=True)

            if not df_view.empty:
                df_grid = df_view.copy()
                df_grid["stato"] = df_grid["is_incidentata"].apply(lambda x: "🚨 Incidentata" if int(x) == 1 else "✅ Integra")
                st.dataframe(
                    df_grid[["portale", "marca", "modello", "versione", "carburante", "stato", "prezzo", "prezzo_medio_mercato", "anno", "km", "localita", "regione", "deal_score", "giudizio_affare", "url"]],
                    width='stretch',
                    column_config={
                        "url": st.column_config.LinkColumn("Link Annuncio", display_text="🔗 Apri Annuncio"),
                        "localita": "Località",
                        "regione": "Regione",
                        "stato": "Stato",
                        "prezzo": st.column_config.NumberColumn("Prezzo (€)", format="€ %d"),
                        "prezzo_medio_mercato": st.column_config.NumberColumn("Media Mercato (€)", format="€ %d"),
                        "km": st.column_config.NumberColumn("KM", format="%d km"),
                        "deal_score": st.column_config.NumberColumn("Deal Score", format="%.1f / 100"),
                    }
                )

            st.markdown("---")
            
            for idx, row in df_view.head(50).iterrows():
                col_i1, col_i2, col_i3, col_i4, col_i5 = st.columns([3, 1.5, 1.5, 1.5, 1])
                
                fav_icon = "⭐" if row['is_favorite'] == 1 else "☆"
                inc_tag = "\n\n🚨 ** VEICOLO INCIDENTATO / SINISTRATO (Escluso dalle metriche)**" if int(row['is_incidentata']) == 1 else ""
                col_i1.markdown(f"**{row['titolo']}**{inc_tag}\n\n*{row['portale']}* | {row['tipo_venditore']} | 📍 **{row['localita']} ({row['regione']})** | Data: {row['data_annuncio']}\n\n🔗 [Apri Singolo Annuncio Diretto]({row['url']})")
                col_i2.markdown(f"**€ {row['prezzo']:,}**\n<small style='color: #8b949e;'>Mercato (integre): € {int(row['prezzo_medio_mercato']):,}</small>", unsafe_allow_html=True)
                col_i3.markdown(f"🗓️ {row['anno']} | 🛣️ {row['km']:,} km\n⛽ {row['carburante']}\n📍 {row['localita']} ({row['regione']})")
                
                score = row['deal_score']
                giudizio = row['giudizio_affare']
                if int(row['is_incidentata']) == 1:
                    badge_color = "#f85149"
                    col_i4.markdown(f"<span style='color: {badge_color}; font-weight: 600;'>Esclusa da Score</span>\n\n**{giudizio}**", unsafe_allow_html=True)
                else:
                    if score >= 80:
                        badge_color = "#238636"
                    elif score >= 50:
                        badge_color = "#d29922"
                    else:
                        badge_color = "#f85149"
                    col_i4.markdown(f"<span style='color: {badge_color}; font-weight: 600;'>Score: {score}/100</span>\n\n**{giudizio}**", unsafe_allow_html=True)
                
                if col_i5.button(f"{fav_icon} Preferito", key=f"fav_{row['id']}"):
                    toggle_favorite_db(row['id'], row['is_favorite'])
                    st.rerun()
                if col_i5.button("🚫 Escludi", key=f"del_t3_{row['id']}", type="secondary"):
                    escludi_annuncio_db(row["id"], row["url"], row["titolo"])
                    st.rerun()
                st.divider()

            st.markdown("#### 📈 Scatter Plot Interattivo: Prezzo vs Chilometraggio")
            st.markdown("<small style='color: #8b949e;'>Ogni punto rappresenta un annuncio integro (le auto incidentate non vengono usate in nessuna metrica grafica).</small>", unsafe_allow_html=True)
            
            df_clean_view = df_view[df_view["is_incidentata"] == 0]
            available_scatter_brands = sorted(df_clean_view['marca'].unique().tolist())
            col_gp1, col_gp2 = st.columns(2)
            with col_gp1:
                score_range = st.slider("Filtra per Deal Score min/max nel grafico", 0, 100, (0, 100), key="sc_score_range")
            with col_gp2:
                brand_scatter_filter = st.multiselect("Filtra Brand nel grafico", available_scatter_brands, default=available_scatter_brands)
                
            df_scatter = df_clean_view[
                (df_clean_view['deal_score'] >= score_range[0]) & 
                (df_clean_view['deal_score'] <= score_range[1]) &
                (df_clean_view['marca'].isin(brand_scatter_filter))
            ]

            fig = px.scatter(
                df_scatter,
                x="km",
                y="prezzo",
                color="deal_score",
                size="potenza_cv",
                hover_name="titolo",
                hover_data=["marca", "modello", "anno", "carburante", "localita", "regione", "portale", "deal_score", "url"],
                color_continuous_scale="RdYlGn",
                template="plotly_dark",
                height=600
            )
            fig.update_layout(
                paper_bgcolor="#0d1117",
                plot_bgcolor="#161b22",
                font_color="#e6edf3",
                xaxis_title="Chilometraggio (km)",
                yaxis_title="Prezzo (€)"
            )
            
            # Mostra il grafico con selezione punti abilitata
            selected_point = st.plotly_chart(fig, width='stretch', on_select="rerun", selection_mode="points")
            
            # Se l'utente clicca su un punto nel grafico, mostra l'annuncio e il link diretto
            if selected_point and "selection" in selected_point and selected_point["selection"]["points"]:
                point_idx = selected_point["selection"]["points"][0]["point_index"]
                clicked_row = df_scatter.iloc[point_idx]
                
                st.markdown("---")
                st.markdown(f"#### 🎯 Annuncio Selezionato dal Grafico: **{clicked_row['titolo']}**")
                st.markdown(f"""
                - **Prezzo**: € {clicked_row['prezzo']:,} (Mercato: € {int(clicked_row['prezzo_medio_mercato']):,})
                - **KM**: {clicked_row['km']:,} km | **Anno**: {clicked_row['anno']} | **Alimentazione**: {clicked_row['carburante']}
                - **Località**: 📍 {clicked_row['localita']} ({clicked_row['regione']})
                - **Deal Score**: **{clicked_row['deal_score']}/100** ({clicked_row['giudizio_affare']})
                - **Portale**: {clicked_row['portale']} | **Venditore**: {clicked_row['tipo_venditore']}
                - 🔗 **[Apri Singolo Annuncio Diretto]({clicked_row['url']})**
                """)
                if st.button("🚫 Elimina / Escludi questo annuncio (Anomalo)", key=f"del_scatter_{clicked_row['id']}", type="secondary"):
                    escludi_annuncio_db(clicked_row["id"], clicked_row["url"], clicked_row["titolo"])
                    st.success("Annuncio escluso da tutte le metriche e dagli scraping futuri!")
                    st.rerun()

# ==========================================
# Tab 4: Area DEV & Manutenzione
# ==========================================
with tab4:
    st.markdown("#### Area DEV & Manutenzione Sistema")
    st.markdown("<small style='color: #8b949e;'>Diagnostica, log di sistema e ripristino database.</small>", unsafe_allow_html=True)
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.markdown("##### ⚙️ Configurazione")
        st.info("Nessun limite di scraping impostato (illimitato).")
        active_w = get_deal_score_weights()
        st.markdown(
            f"**Pesi Deal Score attivi**: Prezzo `{active_w['peso_prezzo']}` | KM `{active_w['peso_km']}` | Anno `{active_w['peso_anno']}` | CV `{active_w['peso_cv']}`"
        )
        
        st.markdown("##### 🔴 Reset Database Completo")
        confirm_reset = st.checkbox("Conferma reset totale database")
        if st.button("Cancella e Ricrea DB", type="secondary"):
            if confirm_reset:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS annunci")
                cursor.execute("DROP TABLE IF EXISTS alimentazioni_watchlist")
                cursor.execute("DROP TABLE IF EXISTS modelli_watchlist")
                cursor.execute("DROP TABLE IF EXISTS regioni_watchlist")
                cursor.execute("DROP TABLE IF EXISTS deal_score_config")
                cursor.execute("DROP TABLE IF EXISTS scraping_logs")
                conn.commit()
                conn.close()
                init_db()
                st.success("✅ Database ripristinato!")
                st.rerun()
            else:
                st.warning("Spunta la casella di conferma.")

    with col_d2:
        st.markdown("##### 📊 Log & Diagnostica Ultime Chiamate")
        conn = sqlite3.connect(DB_NAME)
        df_logs = pd.read_sql("SELECT timestamp, portale, status, annunci_salvati, tempo_risposta_sec, dettagli FROM scraping_logs ORDER BY id DESC LIMIT 20", conn)
        df_esclusi = pd.read_sql("SELECT id, titolo, motivo, timestamp, url FROM annunci_esclusi ORDER BY timestamp DESC", conn)
        conn.close()
        
        if df_logs.empty:
            st.info("Nessun log registrato.")
        else:
            st.dataframe(df_logs, width='stretch')

        st.markdown("---")
        st.markdown(f"##### 🚫 Blacklist Annunci Esclusi Manualmente ({len(df_esclusi)})")
        if df_esclusi.empty:
            st.info("Nessun annuncio escluso manualmente.")
        else:
            st.dataframe(
                df_esclusi,
                width='stretch',
                column_config={
                    "url": st.column_config.LinkColumn("Link Annuncio", display_text="🔗 Apri"),
                },
            )
            for _, ex_row in df_esclusi.head(15).iterrows():
                c_ex1, c_ex2 = st.columns([4, 1])
                c_ex1.markdown(f"<small>🚫 <b>{ex_row['titolo']}</b> ({ex_row['timestamp']})</small>", unsafe_allow_html=True)
                if c_ex2.button("Ripristina", key=f"rest_{ex_row['id']}"):
                    ripristina_annuncio_escluso_db(ex_row["id"])
                    st.rerun()
