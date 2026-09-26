# -*- coding: utf-8 -*-
"""
Intestazione dello studio (per i PDF: relazioni, ricette).
Salva nome, indirizzo, P.IVA, contatti, titolo professionale di default e logo
nella tabella `studi`, per lo studio attivo.

Esposto:
  render_intestazione_studio(conn, studio_id)
  get_intestazione_studio(conn, studio_id) -> dict   (usato dai PDF)
"""
from __future__ import annotations
import base64
import streamlit as st

_COLS = ["nome", "indirizzo", "partita_iva", "telefono",
         "contatti", "titolo_default", "logo_base64", "carta_intestata_base64"]


def _ensure_cols(conn) -> None:
    cur = conn.cursor()
    for ddl in (
        "ALTER TABLE studi ADD COLUMN IF NOT EXISTS contatti TEXT",
        "ALTER TABLE studi ADD COLUMN IF NOT EXISTS titolo_default TEXT",
        "ALTER TABLE studi ADD COLUMN IF NOT EXISTS logo_base64 TEXT",
        "ALTER TABLE studi ADD COLUMN IF NOT EXISTS carta_intestata_base64 TEXT",
    ):
        try:
            cur.execute(ddl)
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass


def get_intestazione_studio(conn, studio_id: int) -> dict:
    """Ritorna i dati di intestazione dello studio (o {} se assenti/errore)."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT nome, indirizzo, partita_iva, telefono, contatti, "
            "titolo_default, logo_base64, carta_intestata_base64 FROM studi WHERE id = %s",
            (studio_id,),
        )
        row = cur.fetchone()
        if not row:
            return {}
        if isinstance(row, dict):
            return {k: row.get(k) for k in _COLS}
        return dict(zip(_COLS, row))
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return {}


def render_intestazione_studio(conn, studio_id: int) -> None:
    st.markdown("### 🧾 Intestazione dello studio")
    st.caption("Questi dati compaiono in cima alle relazioni e alle ricette in PDF.")

    _ensure_cols(conn)
    d = get_intestazione_studio(conn, studio_id)

    logo_b64 = d.get("logo_base64")
    if logo_b64:
        try:
            st.image(base64.b64decode(logo_b64), width=220, caption="Logo attuale")
        except Exception:
            st.caption("(logo presente ma non visualizzabile)")

    carta_b64 = d.get("carta_intestata_base64")
    if carta_b64:
        try:
            st.image(base64.b64decode(carta_b64), width=300,
                     caption="Carta intestata attuale (sfondo dei PDF)")
        except Exception:
            st.caption("(carta intestata presente ma non visualizzabile)")

    with st.form(f"intest_studio_{studio_id}"):
        nome = st.text_input("Nome studio", value=d.get("nome") or "")
        titolo = st.text_input(
            "Titolo professionale di default", value=d.get("titolo_default") or "",
            help="Es. 'Optometrista' — compare sotto il nome del professionista")
        indirizzo = st.text_area("Indirizzo", value=d.get("indirizzo") or "", height=70)
        c1, c2 = st.columns(2)
        with c1:
            piva = st.text_input("Partita IVA", value=d.get("partita_iva") or "")
        with c2:
            tel = st.text_input("Telefono", value=d.get("telefono") or "")
        contatti = st.text_input(
            "Riga contatti per il PDF", value=d.get("contatti") or "",
            help="Es. 'Tel. 081... | email@studio.it'. Se vuoto, nel PDF useremo il telefono.")
        logo_file = st.file_uploader("Logo (PNG o JPG)", type=["png", "jpg", "jpeg"])
        st.markdown("---")
        st.markdown("**Carta intestata (immagine pagina intera)**")
        st.caption("Se carichi un'immagine A4 (intestazione + piè di pagina), verrà usata come "
                   "sfondo delle relazioni/ricette. Sostituisce l'intestazione costruita dai campi sopra.")
        carta_file = st.file_uploader("Carta intestata (PNG o JPG)", type=["png", "jpg", "jpeg"],
                                      key=f"carta_{studio_id}")
        salva = st.form_submit_button("💾 Salva intestazione", use_container_width=True)

    if salva:
        new_logo = logo_b64
        if logo_file is not None:
            try:
                new_logo = base64.b64encode(logo_file.getvalue()).decode("ascii")
            except Exception as e:
                st.error(f"Logo non valido: {e}")
                new_logo = logo_b64
        new_carta = carta_b64
        if carta_file is not None:
            try:
                new_carta = base64.b64encode(carta_file.getvalue()).decode("ascii")
            except Exception as e:
                st.error(f"Carta intestata non valida: {e}")
                new_carta = carta_b64
        # nome è NOT NULL: non lasciarlo vuoto
        nome_val = (nome or "").strip() or d.get("nome") or "Studio"
        valori = (nome_val, indirizzo or None, piva or None, tel or None,
                  contatti or None, titolo or None, new_logo, new_carta)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE studi SET nome=%s, indirizzo=%s, partita_iva=%s, telefono=%s, "
                "contatti=%s, titolo_default=%s, logo_base64=%s, carta_intestata_base64=%s WHERE id=%s",
                valori + (int(studio_id),),
            )
            # Se lo studio non esiste ancora nella tabella, l'UPDATE non tocca
            # nessuna riga e non da' errore: la pagina diceva «salvato» e non
            # salvava niente. In quel caso si crea la riga.
            if (cur.rowcount or 0) == 0:
                # email_admin e db_url sono NOT NULL in una delle due versioni
                # della tabella (saas_tenant.py): si passano vuoti.
                cur.execute(
                    "INSERT INTO studi (id, codice, email_admin, db_url, nome, indirizzo, "
                    "partita_iva, telefono, contatti, titolo_default, logo_base64, "
                    "carta_intestata_base64) "
                    "VALUES (%s,%s,'','',%s,%s,%s,%s,%s,%s,%s,%s)",
                    (int(studio_id), f"studio_{int(studio_id)}") + valori,
                )
                # L'id e' stato scritto a mano: si riallinea il contatore, cosi'
                # un futuro studio registrato non prova a riusare lo stesso id.
                try:
                    cur.execute("SELECT setval(pg_get_serial_sequence('studi','id'), "
                                "(SELECT MAX(id) FROM studi))")
                except Exception:
                    pass
            conn.commit()
            # Controllo sul database, non sulla fiducia: si rilegge quello che
            # e' stato davvero scritto.
            cur.execute("SELECT COALESCE(length(carta_intestata_base64),0), "
                        "COALESCE(length(logo_base64),0) FROM studi WHERE id=%s", (int(studio_id),))
            _r = cur.fetchone()
            _lc = int((_r[0] if not isinstance(_r, dict) else list(_r.values())[0]) or 0) if _r else -1
            if _r is None:
                st.error("Salvataggio non riuscito: lo studio non risulta nel database.")
                return
            st.success("Intestazione salvata. Comparirà sui prossimi PDF."
                       + (" Carta intestata presente." if _lc > 0 else " Nessuna carta intestata caricata."))
            st.session_state["intestazione_studio"] = {
                "nome": nome_val, "indirizzo": indirizzo or "", "partita_iva": piva or "",
                "telefono": tel or "", "contatti": (contatti or tel or ""),
                "titolo_default": titolo or "", "logo_base64": new_logo or "",
                "carta_intestata_base64": new_carta or "",
            }
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            st.error(f"Errore nel salvataggio: {e}")
