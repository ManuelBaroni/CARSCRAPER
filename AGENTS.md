# AGENTS.md

## Commands & Environment

- **Run the app**: `streamlit` is not on the system `PATH`. Always invoke it via Python's module runner:
  ```powershell
  python -m streamlit run app.py --server.headless true --server.port 8501
  ```
- **Initialize / seed database**:
  ```powershell
  python database.py
  ```
- **Quick syntax / import check**:
  ```powershell
  python -c "import database, scraper, analytics, app"
  ```

## Architecture & Data Flow

Single-directory Python/Streamlit app backed by local SQLite (`cars.db`):

- `app.py`: 4-tab Streamlit UI (`Configurazione & Modelli`, `Scraping & Raccolta Dati`, `Statistiche & Deal Score`, `Area DEV & Manutenzione`) with custom dark CSS (`#0d1117` / `#161b22` / `#238636`) and filter state persisted in `st.session_state`.
- `database.py`: Manages `cars.db` with four tables: `alimentazioni_watchlist` (`ALIMENTAZIONI_LIST`), `regioni_watchlist` (`REGIONI_ITALIA`), `annunci` (includes `localita` and `regione`), and `scraping_logs`. `init_db()` seeds `alimentazioni_watchlist` and `regioni_watchlist` when their respective tables are empty (`COUNT(*) == 0`).
- `scraper.py`: `run_scraper()` fetches real live listings from AutoScout24 (`__NEXT_DATA__` JSON) and Subito.it (`hades.subito.it` JSON API) across all car brands and models (no preset model list), filtering strictly by active `alimentazioni_watchlist`, `regioni_watchlist`, and the Tab 2 range filters (`p_min`, `p_max`, `km_min`, `km_max`, `a_min`, `a_max`). Stores direct individual listing URLs (`/annunci/...` and `/auto/...htm`), `localita`, and `regione`.
- `analytics.py`: `calcola_statistiche_e_deal_score()` joins `annunci` against active `alimentazioni_watchlist` and `regioni_watchlist` (`is_selected = 1`), computes `prezzo_medio_mercato` and `prezzo_mediano_mercato` grouped by `marca + modello + anno` (with fallback to `marca + modello`, then `prezzo`), and scores listings `0–100` (`deal_score`) using `2026` as the reference year.

## Gotchas & Conventions

- **`README.md` is partially stale**: `README.md` still states that `Benzina` and `Elettrico` are excluded and references a Tab 4 scraping limiter. In reality, all 6 fuel types (`Benzina`, `Diesel`, `Ibrido`, `GPL`, `Metano`, `Elettrico`) are supported and scraping is unlimited. Trust the `.py` files over `README.md`.
- **`run_scraper` signature mismatch risk**: `app.py` calls `run_scraper()` with keyword arguments `p_min`, `p_max`, `km_min`, `km_max`, `a_min`, `a_max` alongside `selected_models`, `portali`, `max_entries`, `data_filtro`, and `progress_callback`. Ensure `scraper.py:run_scraper` accepts these parameters when modifying either file.
- **Streamlit 1.66+ API**: Do not use `use_container_width=True`. Use `width='stretch'` on `st.plotly_chart` and `st.dataframe`.
- **Plotly point selection**: Tab 3's scatter plot uses `on_select="rerun"` and `selection_mode="points"`, indexing into `df_scatter.iloc[point_idx]`. Any filtering applied to `df_scatter` must stay aligned with the DataFrame passed to `px.scatter`.
- **Portal URLs**: `scraper.py` extracts real direct listing URLs (`https://www.autoscout24.it/annunci/...` from `__NEXT_DATA__` and `https://www.subito.it/auto/...htm` from `hades.subito.it/v1/search/items`). Never use synthetic per-listing UUIDs (they 404) or generic search page URLs.
