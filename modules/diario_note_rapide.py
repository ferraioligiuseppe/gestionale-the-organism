# -*- coding: utf-8 -*-
"""Blocco note del diario — sempre a portata, in qualunque schermata.

Il diario clinico esiste già come destinazione (Pazienti → Scheda clinica →
Diario), ma il momento in cui serve davvero è un altro: mentre sei in visita,
dentro la valutazione visiva o la seduta MAPS o la restituzione ai genitori.
Uscire dal modulo per annotare significa perdere il punto in cui eri, quindi
di fatto non si annota — e l'informazione si perde.

Questo modulo mette il diario nella barra laterale: resta visibile qualunque
sia la schermata aperta, scrive sullo stesso diario clinico, e registra da
sé chi ha scritto e da quale schermata. Nessuna voce nuova nel menu.

Uso — una riga sola, già richiamata dal router per ogni schermata:
    from .diario_note_rapide import blocco_note_laterale
    blocco_note_laterale(conn, paz_id, paziente, schermata=sotto)
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

TZ = ZoneInfo("Europe/Rome")

# I tipi che servono davvero mentre sei col paziente davanti. Gli altri
# (anamnesi, programma, chiusura…) restano nel diario completo: qui
# comparirebbero solo come rumore in un menu a tendina da usare di corsa.
TIPI_RAPIDI = {
    "seduta": "🪑 Seduta",
    "colloquio": "💬 Colloquio",
    "valutazione": "📊 Valutazione",
    "verifica": "📈 Verifica",
    "nota": "📝 Nota libera",
}


def _autore() -> str:
    for chiave in ("utente_nome", "nome_utente", "username", "utente"):
        valore = st.session_state.get(chiave)
        if valore:
            return str(valore)
    return "—"


def _nome_paziente(paziente, paz_id) -> str:
    if isinstance(paziente, dict):
        nome = " ".join(str(paziente.get(k) or "").strip()
                        for k in ("cognome", "Cognome", "nome", "Nome")).strip()
        nome = " ".join(nome.split())
        if nome:
            return nome
    return f"ID {paz_id}"


def blocco_note_laterale(conn, paz_id=None, paziente=None, schermata: str = "") -> None:
    """Blocco note nella barra laterale, disponibile in ogni schermata."""
    if conn is None:
        return

    with st.sidebar:
        st.markdown("---")

        if not paz_id:
            st.caption("🗓️ **Diario** — seleziona un paziente per annotare.")
            return

        aperto = st.session_state.get("diario_note_aperto", False)
        etichetta = "🗓️ Chiudi blocco note" if aperto else "🗓️ Blocco note"
        if st.button(etichetta, key="diario_note_toggle", use_container_width=True):
            st.session_state["diario_note_aperto"] = not aperto
            st.rerun()

        if not st.session_state.get("diario_note_aperto"):
            return

        try:
            from .diario_clinico import aggiungi_nota, lista_voci, crea_schema, TIPI_VOCE
        except Exception as e:
            st.caption(f"Diario non disponibile: {e}")
            return

        studio_id = st.session_state.get("studio_id", 1)

        # Lo schema si crea una volta per sessione: farlo a ogni rerun
        # significa una DDL a ogni click, con i lock che ne conseguono.
        if not st.session_state.get("_diario_schema_ok"):
            try:
                crea_schema(conn)
                st.session_state["_diario_schema_ok"] = True
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.caption(f"Errore schema diario: {e}")
                return

        st.caption(f"**{_nome_paziente(paziente, paz_id)}**")

        with st.form("form_nota_rapida", clear_on_submit=True):
            tipo = st.selectbox(
                "Tipo", list(TIPI_RAPIDI.keys()),
                format_func=lambda k: TIPI_RAPIDI[k],
                key="diario_nota_tipo", label_visibility="collapsed")
            testo = st.text_area(
                "Nota", height=140, key="diario_nota_testo",
                label_visibility="collapsed",
                placeholder="Cosa è emerso, cosa hai osservato, cosa dire alla famiglia…")
            in_referto = st.checkbox("Da riportare in relazione", value=False,
                                      key="diario_nota_referto")
            salva = st.form_submit_button("💾 Salva nel diario",
                                           use_container_width=True, type="primary")

        if salva:
            if not (testo or "").strip():
                st.warning("Scrivi qualcosa prima di salvare.")
            else:
                # La schermata da cui stai scrivendo finisce nel titolo: mesi
                # dopo, rileggendo il diario, sapere che una nota è nata
                # durante la valutazione visiva o durante MAPS cambia come la
                # interpreti.
                titolo = f"{TIPI_RAPIDI[tipo].split(' ', 1)[-1]}"
                if schermata:
                    titolo += f" · da {schermata}"
                try:
                    voce_id = aggiungi_nota(
                        conn, studio_id, paz_id, tipo,
                        testo=testo.strip(), titolo=titolo,
                        riassunto=testo.strip()[:200], autore=_autore())
                    if in_referto and voce_id:
                        try:
                            from .diario_clinico import aggiorna_voce
                            aggiorna_voce(conn, studio_id, voce_id,
                                          visibile_in_referto=True)
                        except Exception:
                            pass
                    st.success("Salvato.")
                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    st.error(f"Errore: {e}")

        # Le ultime voci servono a non ripetersi e a riprendere il filo di
        # quanto detto la volta prima, senza cambiare schermata.
        try:
            voci = lista_voci(conn, studio_id, paz_id, limite=3) or []
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            voci = []
        if voci:
            st.caption("**Ultime voci**")
            for v in voci:
                data = v.get("data_voce")
                quando = data.strftime("%d/%m") if hasattr(data, "strftime") else ""
                etichetta_tipo = TIPI_VOCE.get(v.get("tipo_voce"), v.get("tipo_voce") or "")
                riassunto = (v.get("riassunto") or v.get("testo") or "").strip()
                if len(riassunto) > 110:
                    riassunto = riassunto[:110].rstrip() + "…"
                st.markdown(
                    f"<div style='font-size:11.5px; line-height:1.45; "
                    f"border-left:2px solid #d8e5de; padding-left:7px; "
                    f"margin-bottom:7px;'>"
                    f"<span style='color:#6B7C74;'>{quando} · {etichetta_tipo}</span><br>"
                    f"{riassunto}</div>",
                    unsafe_allow_html=True)
