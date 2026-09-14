# -*- coding: utf-8 -*-
"""Diario crisi — modulo pubblico per genitori/tutori.
Nessun login richiesto — il link con token collega automaticamente al
paziente giusto (stesso sistema magic-link di MAPS-Read)."""
import streamlit as st
import sys, os
import datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.app_core import get_connection
from modules.pnev_pubblico import db_pnev_pubblico as db_link

st.set_page_config(page_title="Diario delle crisi — The Organism", page_icon="⚡", layout="centered")

conn = get_connection()

qp = st.query_params
token = (qp.get("t", "") or "").strip()

if not token:
    st.error("Link non valido: manca il codice di accesso.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com")
    st.stop()

utente_id = db_link.valida_magic_link(conn, token)
if not utente_id:
    st.error("⛔ Link scaduto o non valido. Chiedi allo studio un nuovo link.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com")
    st.stop()

# paz_id: il magic link porta a un utente_id dell'area pubblica PNEV, che nel
# gestionale è agganciato a paziente_id — se non è ancora agganciato,
# registriamo comunque l'episodio con utente_id, da collegare in seguito.
paz_id = db_link.get_paziente_id_da_utente(conn, utente_id) if hasattr(db_link, "get_paziente_id_da_utente") else None
riferimento_id = paz_id or utente_id

st.title("⚡ Diario delle crisi")
st.caption("Registra qui l'episodio appena avvenuto: arriva direttamente allo Studio The Organism.")

cur = conn.cursor()
try:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crisi_epilessia_diario (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT,
            data_crisi DATE,
            ora_crisi TEXT,
            durata_min TEXT,
            tipo TEXT,
            descrizione TEXT,
            fattore_scatenante TEXT,
            farmaco_soccorso TEXT,
            stato_postcritico TEXT,
            note TEXT,
            inserito_da_genitore BOOLEAN DEFAULT FALSE,
            creato_il TIMESTAMPTZ DEFAULT now()
        )
    """)
    cur.execute("ALTER TABLE crisi_epilessia_diario ADD COLUMN IF NOT EXISTS inserito_da_genitore BOOLEAN DEFAULT FALSE;")
    conn.commit()
except Exception:
    try: conn.rollback()
    except Exception: pass

with st.form("diario_pubblico_form"):
    c1, c2 = st.columns(2)
    data_crisi = c1.date_input("Data", value=datetime.date.today(), key="dp_data")
    ora_crisi = c2.text_input("Ora (es. 14:30)", key="dp_ora")
    c3, c4 = st.columns(2)
    durata_min = c3.text_input("Durata (es. 2 min)", key="dp_durata")
    tipo = c4.text_input("Tipo di crisi osservata (se lo sai)", key="dp_tipo")
    descrizione = st.text_area("Cosa hai visto (descrizione dell'episodio)", key="dp_descrizione", height=90)
    c5, c6 = st.columns(2)
    fattore_scatenante = c5.text_input("Cosa può averla scatenata (febbre, stanchezza, luci...)", key="dp_fattore")
    farmaco_soccorso = c6.text_input("Farmaco al bisogno somministrato (se sì)", key="dp_farmaco")
    stato_postcritico = st.text_input("Come è stato dopo (confuso, ha dormito, quanto ci ha messo a riprendersi)",
                                       key="dp_postcritico")
    note = st.text_area("Altre annotazioni", key="dp_note", height=68)
    invia = st.form_submit_button("📤 Invia allo Studio", type="primary")

if invia:
    try:
        cur.execute("""
            INSERT INTO crisi_epilessia_diario
            (paziente_id, data_crisi, ora_crisi, durata_min, tipo, descrizione,
             fattore_scatenante, farmaco_soccorso, stato_postcritico, note, inserito_da_genitore)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (riferimento_id, data_crisi, ora_crisi, durata_min, tipo, descrizione,
              fattore_scatenante, farmaco_soccorso, stato_postcritico, note))
        conn.commit()
        st.success("✅ Episodio inviato allo Studio The Organism. Grazie.")
        try:
            from modules.email_otp import invia_email
            for dest in ("apstheorganism@gmail.com", "dr.ferraioligiuseppe@gmail.com"):
                invia_email(dest, "[Diario crisi] Nuovo episodio segnalato",
                            f"Nuovo episodio nel diario delle crisi.\nData: {data_crisi} · Ora: {ora_crisi}\n"
                            f"Tipo: {tipo or '—'}\nDescrizione: {descrizione or '—'}\n"
                            f"Farmaco somministrato: {farmaco_soccorso or '—'}\nNote: {note or '—'}")
        except Exception:
            pass
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore invio: {e}")

st.caption("Per qualsiasi urgenza contatta subito il 118 o il numero indicato dal medico — questo modulo "
           "non sostituisce l'assistenza in emergenza.")
