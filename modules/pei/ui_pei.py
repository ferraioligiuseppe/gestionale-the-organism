# -*- coding: utf-8 -*-
"""
modules/pei/ui_pei.py — PEI, Profilo Dinamico Funzionale, DF/PF e allegati PDF
del paziente, nel gestionale The Organism.

Il nucleo è modules/pei_core/ (lo stesso codice del TFA Manager).
Qui solo l'innesto: paziente attivo, studio, carta intestata, archivio.

Il PEI lo redige e lo approva il GLO della scuola: lo studio archivia i
documenti ricevuti (DF, PDF, PEI firmato) e prepara il proprio contributo.

Studio The Organism - Dott. Giuseppe Ferraioli
"""
from __future__ import annotations

import io

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from ..pei_core.ui import pagina_pei

# Carta intestata The Organism a piena pagina: intestazione ~32 mm in alto,
# indirizzo nel piede fino a ~42 mm dal fondo, pallini sul margine destro.
MARGINI_CARTA = (42 * mm, 22 * mm, 48 * mm, 20 * mm)


def _studio_id(conn) -> int:
    try:
        from ..documenti_clinici import _studio_corrente
        return int(_studio_corrente(conn) or st.session_state.get("studio_id") or 1)
    except Exception:
        return int(st.session_state.get("studio_id") or 1)


def _paziente(conn, paz_id) -> dict:
    cur = conn.cursor()
    try:
        cur.execute("SELECT cognome, nome FROM pazienti WHERE id=%s", (paz_id,))
        r = cur.fetchone()
        if r:
            r = r if isinstance(r, dict) else dict(zip(("cognome", "nome"), r))
            return {"nome_completo": f"{r.get('cognome') or ''} {r.get('nome') or ''}".strip().title()}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            cur.close()
        except Exception:
            pass
    return {"nome_completo": ""}


def _intestazione():
    """Callback (canvas, doc) che disegna la carta intestata dello studio, se c'è."""
    try:
        from ..pdf_templates import _carta_intestata_bytes
        dati = _carta_intestata_bytes()
    except Exception:
        dati = None
    if not dati:
        return None, None
    from reportlab.lib.utils import ImageReader
    img = ImageReader(io.BytesIO(dati))

    def disegna(canvas, doc):
        canvas.saveState()
        canvas.drawImage(img, 0, 0, width=A4[0], height=A4[1],
                         preserveAspectRatio=False, mask="auto")
        canvas.restoreState()
    return disegna, MARGINI_CARTA


def _archivia(conn, paz_id):
    """Salva il PDF esportato nei Documenti clinici del paziente."""
    def salva(nome, pdf, doc):
        try:
            from ..documenti_clinici import _assicura_tabella, _salva_documento

            class _File:
                name, type = nome, "application/pdf"
                def getvalue(self):
                    return pdf

            _assicura_tabella(conn)
            return _salva_documento(conn, paz_id, "Altro", _File(),
                                    f"{doc.titolo} — {doc.anno_scolastico}")
        except Exception as e:
            st.error(f"Archiviazione non riuscita: {e}")
            return False
    return salva


def render_pei(conn, paz_id):
    try:
        conn.rollback()  # parte pulito se un modulo precedente ha lasciato errori
    except Exception:
        pass
    try:
        from ..pei_core import db as pei_db
        pei_db.crea_tabelle(conn)
    except Exception as e:
        st.error(f"Errore inizializzazione tabelle PEI: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return

    st.caption("Il PEI è redatto e approvato dal GLO della scuola. Qui archivi DF, PDF e PEI "
               "ricevuti e prepari il contributo dello studio, su carta intestata: la «Relazione di "
               "funzionamento ICF-CY» è il documento dello studio per famiglia, UVM e GLO.")
    paz = _paziente(conn, paz_id)
    intestazione, margini = _intestazione()
    operatore = str(st.session_state.get("username") or st.session_state.get("user") or "")
    studio = _studio_id(conn)
    from .fonti_icf import pannello as pannello_icf
    from .fonti_pnev import pannello
    pann_pnev = pannello(conn, paz_id, operatore, studio)
    pann_icf = pannello_icf(conn, paz_id, operatore, studio)

    def pannelli(doc, pref):
        pann_pnev(doc, pref)
        pann_icf(doc, pref)

    pagina_pei(conn, rif_tipo="paziente", rif_id=int(paz_id), utente=operatore,
               tenant_id=studio, intestazione=intestazione, margini=margini,
               prima_del_modulo=pannelli, tipi_extra=["RICF"],
               valori_iniziali={"soggetto": paz["nome_completo"]},
               salva_esportato=_archivia(conn, paz_id),
               etichetta_salva="Salva nei Documenti clinici del paziente")
