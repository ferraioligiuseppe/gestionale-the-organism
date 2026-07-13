# -*- coding: utf-8 -*-
"""
Timbro e firma per professionista — ogni professionista carica la propria
scansione (PNG/JPG), salvata nel database e usata automaticamente nei PDF
delle relazioni cliniche che genera.
"""
import io
import streamlit as st


def _ensure_schema(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS professionisti_timbri(
            username TEXT PRIMARY KEY,
            timbro_png BYTEA NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _username_corrente() -> str:
    u = st.session_state.get("user") or {}
    return (u.get("username") or u.get("display_name") or "").strip()


def _to_transparent_png(dati_immagine: bytes) -> bytes:
    """Converte l'immagine caricata in PNG con sfondo (quasi) bianco reso
    trasparente, cos\u00ec il timbro si sovrappone bene al testo del PDF."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(dati_immagine)).convert("RGBA")
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                lum = (r + g + b) / 3
                if lum > 225:
                    px[x, y] = (r, g, b, 0)
                elif lum > 180:
                    na = int(255 * (1 - (lum - 180) / 45))
                    px[x, y] = (r, g, b, na)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return dati_immagine


def carica_timbro(conn, username: str):
    """Ritorna i bytes PNG del timbro del professionista, o None."""
    if not username:
        return None
    try:
        _ensure_schema(conn)
        cur = conn.cursor()
        cur.execute("SELECT timbro_png FROM professionisti_timbri WHERE username=%s",
                    (username,))
        r = cur.fetchone()
        if r and r[0]:
            return bytes(r[0])
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    return None


def salva_timbro(conn, username: str, dati_immagine: bytes) -> bool:
    if not username:
        return False
    try:
        _ensure_schema(conn)
        png = _to_transparent_png(dati_immagine)
        cur = conn.cursor()
        cur.execute("""INSERT INTO professionisti_timbri(username, timbro_png, updated_at)
            VALUES(%s,%s,NOW())
            ON CONFLICT (username) DO UPDATE SET timbro_png=EXCLUDED.timbro_png,
                                                 updated_at=NOW()""",
                    (username, png))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def render_gestione_timbro(conn):
    """Piccolo pannello: ogni professionista carica/aggiorna il proprio
    timbro e firma scansionati, usati da qui in poi nei PDF che genera."""
    username = _username_corrente()
    with st.expander("🖋️ Il mio timbro e firma", expanded=False):
        if not username:
            st.caption("Accedi con il tuo utente per gestire il tuo timbro personale.")
            return
        attuale = carica_timbro(conn, username)
        if attuale:
            st.image(attuale, width=160, caption="Timbro attuale")
        file = st.file_uploader("Carica scansione (JPG/PNG, sfondo chiaro)",
                                type=["jpg", "jpeg", "png"], key="timbro_upload")
        if file is not None:
            if st.button("💾 Salva come mio timbro", key="timbro_save"):
                if salva_timbro(conn, username, file.getvalue()):
                    st.success("Timbro salvato. Verrà usato nei PDF che generi.")
                    st.rerun()
                else:
                    st.error("Salvataggio non riuscito.")
