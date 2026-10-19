# 🚗 Web Application - Monitoraggio Auto Usate (Segmento B)

Applicazione web sviluppata in Python con **Streamlit**, **SQLite**, e **Plotly** per il monitoraggio, l'importazione e l'analisi di convenienza di auto usate del **Segmento B** (ultimi 15 anni).

## 🚀 Stack Tecnologico
- **Frontend / UI**: Streamlit (interfaccia a 4 tab con navigazione fluida e stato persistente).
- **Database**: SQLite (`cars.db`) tramite script nativo `sqlite3`.
- **Ingegneria Dati / Scraping**: Modulo integrato con simulazione e parsing strutturato per AutoScout24 e Subito.it.
- **Analytics & Scoring**: Algoritmo custom di calcolo del prezzo di mercato e **Deal Score (0 - 100)**.

---

## 🛠️ Come Avviare l'Applicazione

1. Assicurati di avere Python installato insieme alle dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

2. Avvia l'applicazione Streamlit:
   ```bash
   streamlit run app.py
   ```

3. Apri il browser all'indirizzo indicato (solitamente `http://localhost:8501`).

---

## 📑 Struttura delle 4 Tab

- **Tab 1: Configurazione & Selezione Modelli**
  - Lista di riferimento pre-popolata con modelli del Segmento B (Renault Clio, Ford Fiesta, Toyota Yaris, VW Polo, Peugeot 208, Opel Corsa, Lancia Ypsilon, ecc.).
  - Filtro alimentazione rigoroso: **Diesel**, **Ibrido**, **GPL**, **Metano** (esclusi benzina pura ed elettrico puro BEV).
  - Raggruppamento per Brand e Motorizzazione e salvataggio della Watchlist attiva.

- **Tab 2: Scraping & Raccolta Dati**
  - Supporto per AutoScout24 e Subito.it.
  - Filtri per data annuncio (ultimi 3 giorni, 7 giorni, ecc.).
  - Estrazione e normalizzazione di tutti i campi chiave (`prezzo`, `km`, `anno`, `potenza_cv`, ecc.).
  - Barra di avanzamento in tempo reale (`st.progress`).

- **Tab 3: Statistiche & Algoritmo di Convenienza**
  - Calcolo del prezzo medio e mediano di mercato per ciascun gruppo omogeneo.
  - **Deal Score (0 - 100)** trasparente ponderato su prezzo, chilometraggio, anno e potenza.
  - Tabella interattiva con indicatori visivi e tasto rapido **"Preferito"** (`is_favorite`).
  - Grafico Scatter interattivo (**Prezzo vs Km** con colore variabile basato sul Deal Score).

- **Tab 4: Area DEV & Manutenzione**
  - Limitatore di scraping per test rapidi ed evitare blocchi IP.
  - Funzione di reset database protetta da checkbox di conferma.
  - Log e diagnostica delle ultime chiamate e performance dei portali.
