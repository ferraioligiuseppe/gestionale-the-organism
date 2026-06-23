# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  INCASSO — blocco pagamento riutilizzabile (The Organism)            ║
║                                                                      ║
║  Pensato per essere agganciato a QUALSIASI sezione/tabella del       ║
║  gestionale (osteopatia, sedute, valutazione visiva, ...) e per      ║
║  funzionare anche per gli altri studi.                               ║
║                                                                      ║
║  Registra, a fine sezione/visita:                                    ║
║    • Listino  (prezzo pieno)                                         ║
║    • Sconto   (€ oppure %)                                           ║
║    • Netto dovuto      (calcolato)                                   ║
║    • Incassato ora     (gestisce acconto/saldo)                      ║
║    • Saldo residuo     (calcolato)                                   ║
║    • Metodo            (Contanti / POS / Bonifico / Assegno)         ║
║    • Stato pagamento   (Da saldare / Acconto / Saldato — calcolato)  ║
║                                                                      ║
║  USO TIPO (dentro un st.form):                                       ║
║      from modules.incasso import (                                    ║
║          ensure_incasso_columns, campi_incasso, salva_incasso,       ║
║          riepilogo_incasso)                                          ║
║      ensure_incasso_columns(conn, "osteo_seduta")   # una volta      ║
║      dati = campi_incasso("osteo_sed")              # nel form        ║
║      ... insert/update riga ...                                      ║
║      salva_incasso(conn, "osteo_seduta", row_id, dati)  # al submit  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

# Opzioni condivise (modificabili in un punto solo)
METODI = ["—", "Contanti", "POS / Bancomat", "Bonifico", "Assegno", "Altro"]
SCONTO_TIPI = ["Nessuno", "€", "%"]

# Colonne aggiunte alle tabelle delle sezioni (idempotente)
_COLONNE = [
    ("inc_listino",     "REAL"),
    ("inc_sconto_tipo", "TEXT"),
    ("inc_sconto_val",  "REAL"),
    ("inc_netto",       "REAL"),
    ("inc_incassato",   "REAL"),
    ("inc_residuo",     "REAL"),
    ("inc_metodo",      "TEXT"),
    ("inc_stato",       "TEXT"),
    ("inc_note",        "TEXT"),
]


def ensure_incasso_columns(conn, table: str) -> None:
    """Aggiunge le colonne incasso alla tabella se non esistono già.

    Idempotente e sicuro: ogni ALTER è protetto, su errore fa rollback
    e prosegue. `table` è un nome interno (non input utente).
    """
    cur = conn.cursor()
    for col, typ in _COLONNE:
        try:
            cur.execute(
                f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ};'
            )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def calcola(listino, sconto_tipo, sconto_val, incassato):
    """Ritorna (netto, residuo, stato, sconto_eur) — tutto arrotondato a 2 dec."""
    listino = float(listino or 0.0)
    sconto_val = float(sconto_val or 0.0)
    incassato = float(incassato or 0.0)

    if sconto_tipo == "%":
        sconto_eur = listino * sconto_val / 100.0
    elif sconto_tipo == "€":
        sconto_eur = sconto_val
    else:
        sconto_eur = 0.0

    sconto_eur = max(0.0, min(sconto_eur, listino))
    netto = round(listino - sconto_eur, 2)
    residuo = round(netto - incassato, 2)

    if netto <= 0 and incassato <= 0:
        stato = "—"
    elif incassato <= 0:
        stato = "Da saldare"
    elif residuo <= 0.01:
        stato = "Saldato"
    else:
        stato = "Acconto"

    return netto, residuo, stato, round(sconto_eur, 2)


def campi_incasso(prefix: str, defaults: dict | None = None) -> dict:
    """Disegna i campi incasso. Da chiamare dentro un st.form.

    Ritorna un dict 'grezzo' con i valori inseriti (il calcolo di
    netto/residuo/stato avviene in salva_incasso, al submit).
    """
    d = defaults or {}
    st.markdown("#### 💶 Incasso")

    c1, c2, c3 = st.columns(3)
    with c1:
        listino = st.number_input(
            "Listino €", min_value=0.0, step=5.0,
            value=float(d.get("inc_listino") or 0.0), key=f"{prefix}_listino")
    with c2:
        _st = d.get("inc_sconto_tipo") or "Nessuno"
        sconto_tipo = st.selectbox(
            "Sconto", SCONTO_TIPI,
            index=SCONTO_TIPI.index(_st) if _st in SCONTO_TIPI else 0,
            key=f"{prefix}_sconto_tipo")
    with c3:
        sconto_val = st.number_input(
            "Valore sconto", min_value=0.0, step=1.0,
            value=float(d.get("inc_sconto_val") or 0.0),
            key=f"{prefix}_sconto_val",
            help="In € o in % a seconda della scelta a fianco")

    c4, c5, c6 = st.columns(3)
    with c4:
        incassato = st.number_input(
            "Incassato ora €", min_value=0.0, step=5.0,
            value=float(d.get("inc_incassato") or 0.0),
            key=f"{prefix}_incassato",
            help="Quanto paga adesso (per acconto/saldo)")
    with c5:
        _m = d.get("inc_metodo") or "—"
        metodo = st.selectbox(
            "Metodo", METODI,
            index=METODI.index(_m) if _m in METODI else 0,
            key=f"{prefix}_metodo")
    with c6:
        note = st.text_input(
            "Note incasso", value=d.get("inc_note") or "",
            key=f"{prefix}_note")

    return {
        "inc_listino": listino,
        "inc_sconto_tipo": sconto_tipo,
        "inc_sconto_val": sconto_val,
        "inc_incassato": incassato,
        "inc_metodo": metodo,
        "inc_note": note,
    }


def salva_incasso(conn, table: str, row_id: int, dati: dict):
    """Calcola netto/residuo/stato e li salva sulla riga indicata.

    Ritorna (netto, residuo, stato) per poter mostrare il riepilogo.
    """
    netto, residuo, stato, _sc = calcola(
        dati.get("inc_listino"), dati.get("inc_sconto_tipo"),
        dati.get("inc_sconto_val"), dati.get("inc_incassato"))
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE {table} SET
            inc_listino     = %s,
            inc_sconto_tipo = %s,
            inc_sconto_val  = %s,
            inc_netto       = %s,
            inc_incassato   = %s,
            inc_residuo     = %s,
            inc_metodo      = %s,
            inc_stato       = %s,
            inc_note        = %s
        WHERE id = %s
        """,
        (
            float(dati.get("inc_listino") or 0.0),
            dati.get("inc_sconto_tipo") or "Nessuno",
            float(dati.get("inc_sconto_val") or 0.0),
            netto,
            float(dati.get("inc_incassato") or 0.0),
            residuo,
            dati.get("inc_metodo") or "—",
            stato,
            dati.get("inc_note") or "",
            row_id,
        ),
    )
    conn.commit()
    return netto, residuo, stato


def riepilogo_incasso(netto, residuo, stato) -> str:
    """Stringa breve per st.success/st.caption dopo il salvataggio."""
    icona = {"Saldato": "✅", "Acconto": "🟡", "Da saldare": "🔴"}.get(stato, "•")
    base = f"{icona} {stato} — netto € {float(netto or 0):.2f}"
    if (residuo or 0) > 0.01:
        base += f" · residuo da incassare € {float(residuo):.2f}"
    return base


def badge_incasso(rec: dict) -> str:
    """Riga riassuntiva per lo storico, a partire da un record con i campi inc_*."""
    if not rec:
        return ""
    netto = rec.get("inc_netto")
    if netto in (None, ""):
        return ""
    stato = rec.get("inc_stato") or "—"
    icona = {"Saldato": "✅", "Acconto": "🟡", "Da saldare": "🔴"}.get(stato, "•")
    parti = [f"{icona} {stato}", f"netto € {float(netto or 0):.2f}"]
    inc = rec.get("inc_incassato")
    if inc not in (None, ""):
        parti.append(f"incassato € {float(inc or 0):.2f}")
    res = rec.get("inc_residuo")
    if res not in (None, "") and float(res or 0) > 0.01:
        parti.append(f"residuo € {float(res):.2f}")
    met = rec.get("inc_metodo")
    if met and met != "—":
        parti.append(str(met))
    return " · ".join(parti)
