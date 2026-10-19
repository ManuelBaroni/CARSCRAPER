import pandas as pd
import numpy as np
from database import get_db_connection, get_deal_score_weights
from scraper import rileva_incidentata

def calcola_statistiche_e_deal_score():
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT DISTINCT a.*
        FROM annunci a
        INNER JOIN alimentazioni_watchlist aw
            ON a.carburante = aw.carburante
        INNER JOIN regioni_watchlist r
            ON a.regione = r.regione
        WHERE aw.is_selected = 1
          AND r.is_selected = 1
          AND a.id NOT IN (SELECT id FROM annunci_esclusi)
          AND a.url NOT IN (SELECT url FROM annunci_esclusi WHERE url IS NOT NULL AND url != '')
    """, conn)
    conn.close()
    
    if df.empty:
        return df

    if "descrizione" not in df.columns:
        df["descrizione"] = ""
    if "is_incidentata" not in df.columns:
        df["is_incidentata"] = 0

    # Verifica/aggiorna flag incidentata su titolo, versione, descrizione e url
    df["is_incidentata"] = df.apply(
        lambda r: 1
        if (
            int(r.get("is_incidentata") or 0) == 1
            or rileva_incidentata(
                f"{r.get('titolo', '')} {r.get('versione', '')} {r.get('descrizione', '')} {r.get('url', '')}"
            )
        )
        else 0,
        axis=1,
    )

    df["gruppo_anno_key"] = df["marca"] + "_" + df["modello"] + "_" + df["anno"].astype(str)
    df["gruppo_modello_key"] = df["marca"] + "_" + df["modello"]

    # 1. Prezzo di Mercato calcolato ESCLUSIVAMENTE sulle auto NON incidentate (is_incidentata == 0)
    df_clean = df[df["is_incidentata"] == 0]

    if not df_clean.empty:
        mean_anno = df_clean.groupby("gruppo_anno_key")["prezzo"].mean()
        median_anno = df_clean.groupby("gruppo_anno_key")["prezzo"].median()
        mean_modello = df_clean.groupby("gruppo_modello_key")["prezzo"].mean()
        median_modello = df_clean.groupby("gruppo_modello_key")["prezzo"].median()

        df["prezzo_medio_mercato"] = df["gruppo_anno_key"].map(mean_anno)
        df["prezzo_mediano_mercato"] = df["gruppo_anno_key"].map(median_anno)

        df["prezzo_medio_mercato"] = df["prezzo_medio_mercato"].fillna(df["gruppo_modello_key"].map(mean_modello))
        df["prezzo_mediano_mercato"] = df["prezzo_mediano_mercato"].fillna(df["gruppo_modello_key"].map(median_modello))

        df["prezzo_medio_mercato"] = df["prezzo_medio_mercato"].fillna(df["prezzo"])
        df["prezzo_mediano_mercato"] = df["prezzo_mediano_mercato"].fillna(df["prezzo"])
    else:
        df["prezzo_medio_mercato"] = df["prezzo"]
        df["prezzo_mediano_mercato"] = df["prezzo"]

    # 2. Algoritmo Indice di Convenienza (Deal Score da 0 a 100) — le auto incidentate sono escluse
    weights = get_deal_score_weights()
    w_prezzo = float(weights.get("peso_prezzo", 45.0))
    w_km = float(weights.get("peso_km", 15.0))
    w_anno = float(weights.get("peso_anno", 12.0))
    w_cv = float(weights.get("peso_cv", 5.0))

    scores = []
    giudizi = []
    for idx, row in df.iterrows():
        if int(row["is_incidentata"]) == 1:
            scores.append(0.0)
            giudizi.append("🚨 Incidentata (Esclusa)")
            continue

        score = 50.0 # base
        
        # Fattore 1: Prezzo vs Media di Mercato (default peso: 45.0)
        if row['prezzo_medio_mercato'] > 0:
            diff_pct = (row['prezzo_medio_mercato'] - row['prezzo']) / row['prezzo_medio_mercato']
            score += diff_pct * w_prezzo
        
        # Fattore 2: Chilometraggio (default peso: 15.0)
        km = row['km']
        if km < 60000:
            score += w_km * (1.0 - (km / 60000))
        elif km > 100000 and w_km > 0:
            km_scale = w_km / 15.0
            penalita = min(25.0 * km_scale, ((km - 100000) / 10000) * 2.0 * km_scale)
            score -= penalita
            
        # Fattore 3: Anno (default peso: 12.0 su 15 anni = 0.8 pt/anno)
        eta = 2026 - row['anno']
        bonus_anno = max(0.0, (15 - eta) * (w_anno / 15.0))
        score += bonus_anno
        
        # Fattore 4: Potenza (CV) (default peso: 5.0)
        cv = row['potenza_cv'] if pd.notnull(row['potenza_cv']) else 90
        if cv > 100 and w_cv > 0:
            score += min(w_cv, (cv - 100) * 0.1 * (w_cv / 5.0))
            
        final_score = round(max(0.0, min(100.0, score)), 1)
        scores.append(final_score)

        if final_score >= 80:
            giudizi.append("🔥 Ottimo Affare")
        elif final_score >= 50:
            giudizi.append("⚖️ In Linea")
        else:
            giudizi.append("💸 Sovrapprezzata")
            
    df['deal_score'] = scores
    df['giudizio_affare'] = giudizi
    return df

def toggle_favorite_db(annuncio_id, current_state):
    conn = get_db_connection()
    cursor = conn.cursor()
    new_state = 0 if current_state else 1
    cursor.execute("UPDATE annunci SET is_favorite = ? WHERE id = ?", (new_state, annuncio_id))
    conn.commit()
    conn.close()
    return new_state
