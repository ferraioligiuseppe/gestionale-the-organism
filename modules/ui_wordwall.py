# -*- coding: utf-8 -*-
"""
Modulo Esercizi Wordwall
=========================
Permette di associare alla scheda di un paziente delle attività Wordwall
(create dal professionista sul proprio account Wordwall) e di renderle
giocabili direttamente dentro il gestionale.

PASSO 1 — creazione tabella `wordwall_esercizi`        ✅
PASSO 3 — form di inserimento + lista esercizi         ✅
PASSO 4 — player iframe Wordwall integrato in pagina   ✅ (questo file)

Convenzioni rispettate dal resto dell'app:
- connessione via get_connection() -> wrapper _PgConn con .cursor()/.commit()
- placeholder %s
- tabella pazienti = Pazienti (id), colonna di collegamento = paziente_id
- paziente attivo in st.session_state["paziente_attivo_id"]
"""

import re
import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def init_wordwall_table(conn) -> None:
    """Crea la tabella degli esercizi Wordwall se non esiste ancora.

    Idempotente: usa IF NOT EXISTS, quindi può essere chiamata a ogni avvio
    senza effetti collaterali.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wordwall_esercizi (
                id              SERIAL PRIMARY KEY,
                paziente_id     INTEGER NOT NULL,
                titolo          TEXT NOT NULL,
                area            TEXT,
                wordwall_url    TEXT NOT NULL,
                note            TEXT,
                attivo          BOOLEAN DEFAULT TRUE,
                data_creazione  TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wordwall_paziente
            ON wordwall_esercizi (paziente_id)
            """
        )
        conn.commit()
    finally:
        cur.close()


def _ensure_schema(conn) -> None:
    """Esegue init_wordwall_table una sola volta per sessione Streamlit."""
    if not st.session_state.get("_wordwall_schema_ok"):
        init_wordwall_table(conn)
        st.session_state["_wordwall_schema_ok"] = True


# ---------------------------------------------------------------------------
# Aree predefinite (modificabili — è solo l'elenco del menu a tendina)
# ---------------------------------------------------------------------------
AREE_WORDWALL = [
    "Attenzione",
    "Funzioni esecutive",
    "Lettura",
    "Scrittura",
    "Linguaggio",
    "Matematica",
    "Memoria",
    "Prerequisiti",
    "Visuo-percettivo",
    "Altro",
]


# ---------------------------------------------------------------------------
# Utility: normalizzazione URL Wordwall
# ---------------------------------------------------------------------------
def _to_embed_url(url_or_iframe: str) -> str:
    """Trasforma quello che ha incollato il professionista in un URL d'embed.

    Accetta:
    - URL "resource": https://wordwall.net/it/resource/12345/titolo
    - URL "embed":    https://wordwall.net/it/embed/12345?themeId=...
    - URL "play":     https://wordwall.net/play/12345
    - Codice iframe completo: <iframe ... src="https://wordwall.net/embed/..." ...>
    - Qualsiasi altro URL: lo restituisce tale e quale (fallback).

    Restituisce un URL pronto per essere usato in components.iframe.
    """
    if not url_or_iframe:
        return ""

    raw = url_or_iframe.strip()

    # 1) se è un tag <iframe ...>, estraggo il src=""
    m = re.search(r'src\s*=\s*["\']([^"\']+)["\']', raw, flags=re.IGNORECASE)
    if m:
        raw = m.group(1).strip()

    # 2) /resource/ -> /embed/
    if "/resource/" in raw:
        raw = raw.replace("/resource/", "/embed/")

    # 3) /play/ -> /embed/
    if "/play/" in raw:
        raw = raw.replace("/play/", "/embed/")

    # 4) assicuro lo schema https
    if raw.startswith("http://"):
        raw = "https://" + raw[len("http://"):]
    if raw.startswith("//"):
        raw = "https:" + raw

    return raw


# ---------------------------------------------------------------------------
# Accesso DB
# ---------------------------------------------------------------------------
def _insert_esercizio(conn, paziente_id: int, titolo: str, area: str,
                       url: str, note: str) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO wordwall_esercizi
                (paziente_id, titolo, area, wordwall_url, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (paziente_id, titolo.strip(), (area or "").strip() or None,
             url.strip(), (note or "").strip() or None),
        )
        conn.commit()
    finally:
        cur.close()


def _list_esercizi(conn, paziente_id: int) -> list:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, titolo, area, wordwall_url, note, attivo, data_creazione
              FROM wordwall_esercizi
             WHERE paziente_id = %s
          ORDER BY attivo DESC, data_creazione DESC
            """,
            (paziente_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()


def _toggle_attivo(conn, esercizio_id: int, nuovo_stato: bool) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE wordwall_esercizi SET attivo = %s WHERE id = %s",
            (nuovo_stato, esercizio_id),
        )
        conn.commit()
    finally:
        cur.close()


def _delete_esercizio(conn, esercizio_id: int) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM wordwall_esercizi WHERE id = %s",
            (esercizio_id,),
        )
        conn.commit()
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# UI: form di inserimento
# ---------------------------------------------------------------------------
def _form_nuovo_esercizio(conn, paziente_id: int) -> None:
    with st.expander("➕ Aggiungi un esercizio Wordwall", expanded=False):
        with st.form(key=f"ww_form_new_{paziente_id}", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                titolo = st.text_input(
                    "Titolo *",
                    placeholder="es. Abbinamento sinonimi",
                )
            with col2:
                area = st.selectbox("Area", AREE_WORDWALL, index=0)

            url = st.text_input(
                "URL Wordwall *",
                placeholder="https://wordwall.net/it/resource/...  oppure incolla il codice <iframe ...>",
                help=(
                    "Su Wordwall, dalla tua attività, clicca «Condividi» o "
                    "«Incorpora» e incolla qui il link o il codice iframe completo. "
                    "Il modulo lo normalizza in automatico."
                ),
            )

            note = st.text_area(
                "Note (facoltative)",
                placeholder="Indicazioni per il paziente, frequenza consigliata…",
                height=80,
            )

            submitted = st.form_submit_button("💾 Salva esercizio")

        if submitted:
            if not titolo.strip():
                st.error("Il titolo è obbligatorio.")
                return
            if not url.strip():
                st.error("L'URL Wordwall è obbligatorio.")
                return
            if "wordwall.net" not in url.lower():
                st.warning(
                    "L'URL non sembra di Wordwall. Salvo lo stesso, ma "
                    "verifica che sia corretto."
                )
            try:
                _insert_esercizio(conn, paziente_id, titolo, area, url, note)
                st.success("Esercizio salvato ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")


# ---------------------------------------------------------------------------
# UI: lista esercizi (con player integrato)
# ---------------------------------------------------------------------------
PLAYER_HEIGHT_DEFAULT = 600  # px


def _lista_esercizi(conn, paziente_id: int) -> None:
    esercizi = _list_esercizi(conn, paziente_id)

    if not esercizi:
        st.info("Nessun esercizio assegnato a questo paziente.")
        return

    active_player_key = f"ww_active_player_{paziente_id}"
    active_player = st.session_state.get(active_player_key)

    st.markdown(f"**Esercizi assegnati:** {len(esercizi)}")
    st.markdown("---")

    for e in esercizi:
        es_id   = e["id"]
        titolo  = e["titolo"]
        area    = e["area"] or "—"
        url     = e["wordwall_url"]
        note    = e["note"] or ""
        attivo  = bool(e["attivo"])
        data_c  = e["data_creazione"]

        is_playing = (active_player == es_id)
        header_icon = "▶️" if is_playing else ("🟢" if attivo else "⚪")

        with st.expander(
            f"{header_icon} **{titolo}** · {area}",
            expanded=is_playing,
        ):
            colA, colB = st.columns([3, 2])
            with colA:
                st.markdown(f"🔗 [Apri su Wordwall (nuova scheda)]({url})")
                if note:
                    st.caption(note)
                try:
                    st.caption(f"Creato il {data_c.strftime('%d/%m/%Y %H:%M')}")
                except Exception:
                    st.caption(f"Creato il {data_c}")

            with colB:
                # Player toggle
                if is_playing:
                    if st.button("⏹️ Chiudi player", key=f"ww_stop_{es_id}"):
                        st.session_state[active_player_key] = None
                        st.rerun()
                else:
                    if st.button("▶️ Apri player", key=f"ww_play_{es_id}"):
                        st.session_state[active_player_key] = es_id
                        st.rerun()

                # Attivo / disattivo
                if attivo:
                    if st.button("⏸️ Disattiva", key=f"ww_off_{es_id}"):
                        _toggle_attivo(conn, es_id, False)
                        st.rerun()
                else:
                    if st.button("▶️ Riattiva", key=f"ww_on_{es_id}"):
                        _toggle_attivo(conn, es_id, True)
                        st.rerun()

                # Elimina con conferma
                conferma_key = f"ww_del_conf_{es_id}"
                if st.session_state.get(conferma_key):
                    st.warning("Confermi l'eliminazione?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Sì, elimina", key=f"ww_del_yes_{es_id}"):
                            # se sto eliminando l'esercizio attivo, chiudo il player
                            if active_player == es_id:
                                st.session_state[active_player_key] = None
                            _delete_esercizio(conn, es_id)
                            st.session_state.pop(conferma_key, None)
                            st.rerun()
                    with c2:
                        if st.button("Annulla", key=f"ww_del_no_{es_id}"):
                            st.session_state.pop(conferma_key, None)
                            st.rerun()
                else:
                    if st.button("🗑️ Elimina", key=f"ww_del_{es_id}"):
                        st.session_state[conferma_key] = True
                        st.rerun()

            # Player a tutta larghezza, sotto la riga colA/colB
            if is_playing:
                embed_url = _to_embed_url(url)
                if not embed_url:
                    st.error("URL non valido per l'embed.")
                else:
                    st.markdown("")
                    components.iframe(
                        embed_url,
                        height=PLAYER_HEIGHT_DEFAULT,
                        scrolling=True,
                    )
                    st.caption(
                        "Se l'attività non parte qui dentro, usa il link "
                        "«Apri su Wordwall (nuova scheda)»: alcune attività "
                        "hanno restrizioni anti-embed."
                    )


# ---------------------------------------------------------------------------
# Render principale
# ---------------------------------------------------------------------------
def render_wordwall(conn, paziente_id: int) -> None:
    """Pagina Esercizi Wordwall per il paziente attivo."""
    _ensure_schema(conn)

    st.subheader("🎮 Esercizi Wordwall")
    st.caption(
        "Assegna a questo paziente attività Wordwall create dal tuo account. "
        "Apri il player per giocare direttamente nella scheda."
    )

    _form_nuovo_esercizio(conn, paziente_id)
    st.markdown("")
    _lista_esercizi(conn, paziente_id)
