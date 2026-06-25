# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  DOCUMENTI CLINICI — archivio referti del paziente (Mattone 1)        ║
║                                                                      ║
║  Carica nel database OVH (tabella dedicata, protetta dallo stesso    ║
║  isolamento per studio delle cartelle) i documenti del paziente:     ║
║  PDF e foto/scansioni di esami visivi, funzionali, diagnosi          ║
║  precedenti. Si rileggono, si scaricano, si eliminano.               ║
║                                                                      ║
║  È la base per i mattoni successivi: lettura AI dei documenti,       ║
║  quadro storico unificato, diagnosi assistita.                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

TIPI = ["Esame visivo", "Esame funzionale", "Diagnosi / referto",
        "Esame uditivo", "Riflessi / INPP", "Altro"]

_MIME_ESTENSIONI = {
    "application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png",
    "image/webp": "webp", "image/heic": "heic",
}


def _assicura_tabella(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documenti_clinici (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            studio_id INT,
            tipo TEXT,
            nome_file TEXT,
            mime TEXT,
            dati BYTEA,
            note TEXT,
            estratto TEXT,
            data TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("ALTER TABLE documenti_clinici ADD COLUMN IF NOT EXISTS estratto TEXT;")
    conn.commit()


def _studio_corrente(conn):
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_setting('app.current_studio', true)")
        v = cur.fetchone()[0]
        return int(v) if v else 1
    except Exception:
        return 1


def render_documenti(conn=None, paz_id=None, paziente=None):
    st.header("📎 Documenti clinici")
    st.caption("Archivio referti del paziente: esami visivi e funzionali, diagnosi "
               "precedenti. Caricali qui per ritrovarli a ogni visita.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    try:
        _assicura_tabella(conn)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Impossibile preparare l'archivio: {e}")
        return

    # ── Caricamento ───────────────────────────────────────────────────
    with st.expander("⬆️ Carica un documento", expanded=True):
        with st.form("doc_upload", clear_on_submit=True):
            file = st.file_uploader("File (PDF o foto)",
                                    type=["pdf", "jpg", "jpeg", "png", "webp", "heic"])
            c1, c2 = st.columns(2)
            with c1:
                tipo = st.selectbox("Tipo di documento", TIPI)
            with c2:
                note = st.text_input("Note (facoltative)")
            inviato = st.form_submit_button("💾 Salva nel database", type="primary")
            if inviato:
                if not file:
                    st.warning("Scegli prima un file.")
                else:
                    if _salva_documento(conn, paz_id, tipo, file, note):
                        st.success(f"Documento «{file.name}» salvato.")
                        st.rerun()
                    else:
                        st.error("Salvataggio non riuscito.")

    st.markdown("---")
    st.markdown("#### Documenti in archivio")
    _elenco(conn, paz_id)


def _salva_documento(conn, paz_id, tipo, file, note) -> bool:
    try:
        dati = file.getvalue()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documenti_clinici "
            "(paziente_id, studio_id, tipo, nome_file, mime, dati, note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (paz_id, _studio_corrente(conn), tipo, file.name,
             file.type or "", dati, note or ""))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tipo, nome_file, mime, note, data, octet_length(dati) "
            "FROM documenti_clinici WHERE paziente_id=%s ORDER BY data DESC",
            (paz_id,))
        righe = cur.fetchall()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Lettura archivio non riuscita: {e}")
        return

    if not righe:
        st.info("Nessun documento ancora caricato per questo paziente.")
        return

    for doc_id, tipo, nome, mime, note, data, peso in righe:
        data_str = data.strftime("%d/%m/%Y %H:%M") if data else ""
        peso_kb = f"{(peso or 0)/1024:.0f} KB"
        with st.container():
            c1, c2, c3 = st.columns([5, 2, 2])
            with c1:
                st.markdown(f"**{nome}**")
                st.caption(f"{tipo} · {data_str} · {peso_kb}"
                           + (f" · {note}" if note else ""))
            with c2:
                if st.button("⬇️ Scarica", key=f"dl_{doc_id}"):
                    _scarica(conn, doc_id, nome, mime)
            with c3:
                if st.button("🗑 Elimina", key=f"del_{doc_id}"):
                    _elimina(conn, doc_id)
                    st.rerun()
            # anteprima immagini
            if mime and mime.startswith("image/"):
                with st.expander("👁 Anteprima"):
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT dati FROM documenti_clinici WHERE id=%s",
                                    (doc_id,))
                        st.image(bytes(cur.fetchone()[0]), use_container_width=True)
                    except Exception:
                        st.caption("Anteprima non disponibile.")
            # analisi AI
            _blocco_ai(conn, doc_id, mime, nome)
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)


def _scarica(conn, doc_id, nome, mime):
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati FROM documenti_clinici WHERE id=%s", (doc_id,))
        dati = bytes(cur.fetchone()[0])
        st.download_button("📥 Conferma download", data=dati, file_name=nome,
                           mime=mime or "application/octet-stream",
                           key=f"dlc_{doc_id}")
    except Exception as e:
        st.error(f"Download non riuscito: {e}")


def _elimina(conn, doc_id):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM documenti_clinici WHERE id=%s", (doc_id,))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _leggi_estratto(conn, doc_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT estratto FROM documenti_clinici WHERE id=%s", (doc_id,))
        r = cur.fetchone()
        return r[0] if r else None
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _blocco_ai(conn, doc_id, mime, nome):
    """Analisi AI del documento: estrae i dati clinici e li salva accanto al file."""
    try:
        from .ai_estrazione import estrai_da_documento, ai_disponibile
    except Exception:
        return

    estratto = _leggi_estratto(conn, doc_id)
    with st.expander("🤖 Analisi AI" + (" ✅" if estratto else "")):
        if not ai_disponibile():
            st.caption("AI non ancora configurata (chiave nei Secrets). "
                       "Una volta attiva, qui potrai estrarre i dati dal documento.")
            return
        if estratto:
            st.markdown(estratto)
            if st.button("🔄 Rianalizza", key=f"ai_re_{doc_id}"):
                estratto = None
        if not estratto:
            if st.button("🤖 Estrai dati con AI", key=f"ai_go_{doc_id}", type="primary"):
                with st.spinner("Lettura del documento in corso…"):
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT dati, mime, nome_file FROM documenti_clinici "
                                    "WHERE id=%s", (doc_id,))
                        d, m, n = cur.fetchone()
                        risultato = estrai_da_documento(bytes(d), m or mime, n or nome)
                    except Exception as e:
                        risultato = f"⚠️ Errore lettura file: {e}"
                st.markdown(risultato)
                if not risultato.startswith("⚠️"):
                    try:
                        cur = conn.cursor()
                        cur.execute("UPDATE documenti_clinici SET estratto=%s WHERE id=%s",
                                    (risultato, doc_id))
                        conn.commit()
                        st.success("Analisi salvata in cartella.")
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
