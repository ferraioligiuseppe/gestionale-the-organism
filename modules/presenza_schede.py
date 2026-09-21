# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  CHI HA QUESTA SCHEDA APERTA                                         ║
║                                                                      ║
║  Le schede lunghe (visita oculistica, protocollo, modifica seduta)   ║
║  salvano tutti i campi insieme con un solo UPDATE. Se due postazioni ║
║  hanno aperta la stessa scheda, l'ultimo che salva riscrive anche i  ║
║  campi compilati dall'altro, senza che nessuno se ne accorga: il     ║
║  lavoro del primo sparisce e non resta traccia di cosa e' successo.  ║
║                                                                      ║
║  Questo modulo avvisa PRIMA, non blocca dopo.                        ║
║                                                                      ║
║  Perche' un avviso e non un blocco: un blocco vero richiede di       ║
║  rilasciarlo con certezza, e un browser chiuso male, una batteria    ║
║  scarica o una connessione caduta lasciano la scheda inchiodata      ║
║  finche' qualcuno non interviene sul database. In uno studio di      ║
║  poche persone il costo di quel blocco e' piu' alto del problema che ║
║  risolve. Chi e' avvisato decide: aspetto, chiamo, o vado avanti.    ║
║                                                                      ║
║  Nota onesta sulla finestra temporale: Streamlit si aggiorna solo    ║
║  quando qualcuno clicca. Chi sta scrivendo dentro un form non manda  ║
║  segnali per minuti interi. Per questo la presenza dura FINESTRA_MIN ║
║  minuti dall'ultimo segnale e il messaggio dice "di recente", non    ║
║  "in questo momento": e' quello che il dato sa davvero dire.         ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import datetime
import uuid

import streamlit as st

FINESTRA_MIN = 10        # per quanto una presenza resta valida
INTERVALLO_SEGNALE = 20  # secondi minimi fra due scritture della stessa sessione

_TABELLA_PRONTA = False


# ══════════════════════════════════════════════════════════════════════
#  Infrastruttura
# ══════════════════════════════════════════════════════════════════════

def _assicura_tabella(conn) -> bool:
    """Una volta per processo: il DDL a ogni render e' esattamente il
    problema di lock che questo modulo dovrebbe aiutare a evitare."""
    global _TABELLA_PRONTA
    if _TABELLA_PRONTA:
        return True
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schede_aperte (
                paziente_id   BIGINT      NOT NULL,
                modulo        TEXT        NOT NULL,
                sessione      TEXT        NOT NULL,
                utente        TEXT,
                aggiornato_il TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (paziente_id, modulo, sessione)
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_schede_aperte_agg
                       ON schede_aperte (aggiornato_il);""")
        conn.commit()
        _TABELLA_PRONTA = True
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _sessione() -> str:
    """Identificativo stabile della scheda del browser. Non si puo' usare
    il nome utente: due postazioni possono essere entrate con lo stesso
    account, ed e' proprio il caso che crea piu' confusione."""
    if "_id_sessione" not in st.session_state:
        st.session_state["_id_sessione"] = uuid.uuid4().hex[:16]
    return st.session_state["_id_sessione"]


def _utente() -> str:
    u = st.session_state.get("user") or {}
    nome = (u.get("display_name") or u.get("username") or "").strip()
    return nome or "utente non identificato"


# ══════════════════════════════════════════════════════════════════════
#  Presenza
# ══════════════════════════════════════════════════════════════════════

def _registra(conn, paziente_id: int, modulo: str) -> None:
    """Scrive il proprio segnale, non piu' di una volta ogni
    INTERVALLO_SEGNALE secondi: Streamlit rilancia la pagina a ogni clic e
    senza freno questa diventerebbe la query piu' eseguita del gestionale."""
    chiave = f"_presenza_{paziente_id}_{modulo}"
    adesso = datetime.datetime.now()
    ultimo = st.session_state.get(chiave)
    if ultimo and (adesso - ultimo).total_seconds() < INTERVALLO_SEGNALE:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO schede_aperte (paziente_id, modulo, sessione, utente, aggiornato_il)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (paziente_id, modulo, sessione)
            DO UPDATE SET aggiornato_il = now(), utente = EXCLUDED.utente
        """, (int(paziente_id), modulo, _sessione(), _utente()))
        # Le presenze vecchie si buttano qui: senza, la tabella cresce a
        # ogni apertura e prima o poi qualcuno risulta presente da ieri.
        cur.execute("DELETE FROM schede_aperte WHERE aggiornato_il < now() - interval '2 hours'")
        conn.commit()
        st.session_state[chiave] = adesso
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _altri_presenti(conn, paziente_id: int, modulo: str):
    """Chi altro ha questa scheda aperta, escluso me."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT utente, sessione, aggiornato_il
            FROM schede_aperte
            WHERE paziente_id = %s AND modulo = %s AND sessione <> %s
              AND aggiornato_il > now() - (%s * interval '1 minute')
            ORDER BY aggiornato_il DESC
        """, (int(paziente_id), modulo, _sessione(), FINESTRA_MIN))
        return cur.fetchall() or []
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def rilascia(conn, paziente_id: int, modulo: str) -> None:
    """Toglie la propria presenza. Da chiamare dopo un salvataggio andato
    a buon fine: se hai salvato, la scheda non e' piu' tua."""
    try:
        cur = conn.cursor()
        cur.execute("""DELETE FROM schede_aperte
                       WHERE paziente_id=%s AND modulo=%s AND sessione=%s""",
                    (int(paziente_id), modulo, _sessione()))
        conn.commit()
        st.session_state.pop(f"_presenza_{paziente_id}_{modulo}", None)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Da chiamare nelle schede
# ══════════════════════════════════════════════════════════════════════

def avvisa_se_aperta_altrove(conn, paziente_id, modulo: str,
                             etichetta: str = "questa scheda") -> bool:
    """Registra la presenza e mostra l'avviso se c'e' qualcun altro.
    Ritorna True se un'altra postazione ha la scheda aperta.

    Una riga sola in cima alla schermata:

        if conn and paz_id:
            from .presenza_schede import avvisa_se_aperta_altrove
            avvisa_se_aperta_altrove(conn, paz_id, "oculistica",
                                     "la visita oculistica")
    """
    if not conn or not paziente_id:
        return False
    if not _assicura_tabella(conn):
        return False

    _registra(conn, paziente_id, modulo)
    altri = _altri_presenti(conn, paziente_id, modulo)
    if not altri:
        return False

    io_stesso = _utente()
    nomi, stessa_persona = [], False
    for riga in altri:
        nome = (riga[0] if not isinstance(riga, dict) else riga.get("utente")) or "utente non identificato"
        if nome == io_stesso:
            stessa_persona = True
        nomi.append(nome)

    unici = list(dict.fromkeys(nomi))
    if stessa_persona and len(unici) == 1:
        chi = "un'altra postazione collegata con il tuo stesso utente"
    elif len(unici) == 1:
        chi = f"**{unici[0]}**"
    else:
        chi = "**" + "**, **".join(unici[:-1]) + f"** e **{unici[-1]}**"

    st.warning(
        f"⚠️ {chi} ha aperto {etichetta} di questo paziente negli ultimi "
        f"{FINESTRA_MIN} minuti.\n\n"
        "Se salvate tutti e due, **l'ultimo salvataggio sovrascrive quello "
        "dell'altro** — compresi i campi che non avete toccato. "
        "Sentitevi prima di andare avanti."
    )
    with st.expander("Dettaglio"):
        for riga in altri:
            nome = (riga[0] if not isinstance(riga, dict) else riga.get("utente")) or "—"
            quando = riga[2] if not isinstance(riga, dict) else riga.get("aggiornato_il")
            try:
                minuti = int((datetime.datetime.now(quando.tzinfo) - quando).total_seconds() // 60)
                testo = "poco fa" if minuti < 1 else f"{minuti} minuti fa"
            except Exception:
                testo = "di recente"
            st.caption(f"{nome} — ultimo segnale {testo}")
        st.caption(
            f"La presenza vale {FINESTRA_MIN} minuti dall'ultimo clic. "
            "Chi sta scrivendo dentro un modulo non manda segnali finché non "
            "clicca qualcosa, quindi la scheda può risultare aperta anche se "
            "la persona se n'è andata — o risultare libera mentre qualcuno "
            "sta scrivendo."
        )
    return True


def pannello_schede_aperte(conn) -> None:
    """Chi sta lavorando su cosa, adesso. Un quadretto per la pagina di
    amministrazione: serve a capire se la concorrenza e' un problema
    reale in questo studio o una preoccupazione teorica."""
    if not conn or not _assicura_tabella(conn):
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.utente, s.modulo, p.cognome, p.nome, s.aggiornato_il
            FROM schede_aperte s
            LEFT JOIN pazienti p ON p.id = s.paziente_id
            WHERE s.aggiornato_il > now() - (%s * interval '1 minute')
            ORDER BY s.aggiornato_il DESC
        """, (FINESTRA_MIN,))
        righe = cur.fetchall() or []
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return

    st.markdown("#### 👥 Schede aperte adesso")
    if not righe:
        st.caption("Nessuna scheda aperta negli ultimi minuti.")
        return
    for r in righe:
        utente, modulo, cog, nom = r[0], r[1], r[2], r[3]
        paziente = f"{(cog or '').strip()} {(nom or '').strip()}".strip() or "paziente non trovato"
        st.caption(f"**{utente or '—'}** — {modulo} · {paziente}")
