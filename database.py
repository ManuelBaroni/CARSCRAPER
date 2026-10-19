import sqlite3
import datetime

DB_NAME = "cars.db"

ALIMENTAZIONI_LIST = [
    "Benzina", "Diesel", "Ibrido", "GPL", "Metano", "Elettrico"
]

REGIONI_ITALIA = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
]

DEFAULT_DEAL_WEIGHTS = {
    "peso_prezzo": 45.0,
    "peso_km": 15.0,
    "peso_anno": 12.0,
    "peso_cv": 5.0,
}

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabella Alimentazioni attive (Tab 1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alimentazioni_watchlist (
        carburante TEXT PRIMARY KEY,
        is_selected BOOLEAN DEFAULT 1
    )
    """)

    # Tabella Regioni attive (Tab 1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regioni_watchlist (
        regione TEXT PRIMARY KEY,
        is_selected BOOLEAN DEFAULT 1
    )
    """)

    # Tabella Configurazione Pesi Deal Score
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deal_score_config (
        parametro TEXT PRIMARY KEY,
        peso REAL NOT NULL
    )
    """)

    # Tabella Blacklist Annunci Esclusi Manualmente (persistente per scraping futuri)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS annunci_esclusi (
        id TEXT PRIMARY KEY,
        url TEXT,
        titolo TEXT,
        motivo TEXT DEFAULT 'Anomalo / Escluso manualmente',
        timestamp TEXT
    )
    """)

    # Tabella Annunci Reali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS annunci (
        id TEXT PRIMARY KEY,
        portale TEXT NOT NULL,
        titolo TEXT NOT NULL,
        marca TEXT NOT NULL,
        modello TEXT NOT NULL,
        versione TEXT,
        prezzo INTEGER NOT NULL,
        anno INTEGER NOT NULL,
        km INTEGER NOT NULL,
        carburante TEXT NOT NULL,
        potenza_cv INTEGER,
        consumo_km_l REAL,
        tipo_venditore TEXT,
        localita TEXT,
        regione TEXT,
        descrizione TEXT DEFAULT '',
        is_incidentata BOOLEAN DEFAULT 0,
        data_annuncio TEXT,
        url TEXT,
        is_favorite BOOLEAN DEFAULT 0
    )
    """)

    # Migrazione sicura colonne localita, regione, descrizione, is_incidentata per DB esistenti
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(annunci)").fetchall()]
    if "localita" not in existing_cols:
        cursor.execute("ALTER TABLE annunci ADD COLUMN localita TEXT DEFAULT 'Roma'")
    if "regione" not in existing_cols:
        cursor.execute("ALTER TABLE annunci ADD COLUMN regione TEXT DEFAULT 'Lazio'")
    if "descrizione" not in existing_cols:
        cursor.execute("ALTER TABLE annunci ADD COLUMN descrizione TEXT DEFAULT ''")
    if "is_incidentata" not in existing_cols:
        cursor.execute("ALTER TABLE annunci ADD COLUMN is_incidentata BOOLEAN DEFAULT 0")

    # Tabella Log & Diagnostica
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scraping_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        portale TEXT NOT NULL,
        status TEXT NOT NULL,
        annunci_salvati INTEGER NOT NULL,
        tempo_risposta_sec REAL NOT NULL,
        dettagli TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM alimentazioni_watchlist")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO alimentazioni_watchlist (carburante, is_selected) VALUES (?, 1)",
            [(c,) for c in ALIMENTAZIONI_LIST],
        )

    cursor.execute("SELECT COUNT(*) FROM regioni_watchlist")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO regioni_watchlist (regione, is_selected) VALUES (?, 1)",
            [(r,) for r in REGIONI_ITALIA],
        )

    cursor.execute("SELECT COUNT(*) FROM deal_score_config")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO deal_score_config (parametro, peso) VALUES (?, ?)",
            list(DEFAULT_DEAL_WEIGHTS.items()),
        )

    conn.commit()
    conn.close()

def get_deal_score_weights():
    conn = get_db_connection()
    rows = conn.execute("SELECT parametro, peso FROM deal_score_config").fetchall()
    conn.close()
    weights = dict(DEFAULT_DEAL_WEIGHTS)
    for r in rows:
        if r["parametro"] in weights:
            weights[r["parametro"]] = float(r["peso"])
    return weights

def save_deal_score_weights(peso_prezzo, peso_km, peso_anno, peso_cv):
    conn = get_db_connection()
    cursor = conn.cursor()
    items = [
        ("peso_prezzo", float(peso_prezzo)),
        ("peso_km", float(peso_km)),
        ("peso_anno", float(peso_anno)),
        ("peso_cv", float(peso_cv)),
    ]
    cursor.executemany("INSERT OR REPLACE INTO deal_score_config (parametro, peso) VALUES (?, ?)", items)
    conn.commit()
    conn.close()

def escludi_annuncio_db(annuncio_id, url="", titolo="", motivo="Anomalo / Escluso manualmente"):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT OR REPLACE INTO annunci_esclusi (id, url, titolo, motivo, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (str(annuncio_id), str(url or ""), str(titolo or ""), str(motivo), now),
    )
    cursor.execute("DELETE FROM annunci WHERE id = ?", (str(annuncio_id),))
    if url:
        cursor.execute("DELETE FROM annunci WHERE url = ?", (str(url),))
    conn.commit()
    conn.close()

def ripristina_annuncio_escluso_db(annuncio_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM annunci_esclusi WHERE id = ?", (str(annuncio_id),))
    conn.commit()
    conn.close()

def get_excluded_ids_and_urls():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, url FROM annunci_esclusi").fetchall()
    conn.close()
    ex_ids = {str(r["id"]) for r in rows if r["id"]}
    ex_urls = {str(r["url"]) for r in rows if r["url"]}
    return ex_ids, ex_urls

if __name__ == "__main__":
    init_db()
    print("Database inizializzato con successo!")
