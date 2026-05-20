# -*- coding: utf-8 -*-
"""
modules/eventi/ui_eventi.py

UI admin del modulo Eventi.
Entry point: render_eventi_section()

Funzionalità:
- Tab Lista eventi: visualizza eventi con filtri, espande per dettaglio
- Tab Nuovo evento: form di creazione
- Dettaglio evento: modifica, lista iscritti, export CSV, link pubblico,
  promozione lista attesa, annullamento iscrizioni, eliminazione evento
"""

from __future__ import annotations

import io
import csv
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import streamlit as st

# Fuso orario locale studio (Europe/Rome) per evitare salvataggi naive
# che PostgreSQL interpreta come UTC e mostra con offset sbagliato.
ROME_TZ = ZoneInfo("Europe/Rome")

from .db_eventi import (
    TIPI_VALIDI,
    crea_evento,
    get_evento_by_id,
    lista_eventi,
    aggiorna_evento,
    toggle_evento_attivo,
    toggle_iscrizioni_aperte,
    elimina_evento,
    conta_iscritti,
    posti_rimasti,
    lista_iscrizioni,
    annulla_iscrizione,
    promuovi_da_lista_attesa,
    aggancia_paziente,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENTRY POINT
# =============================================================================

def render_eventi_section():
    """Entry point UI eventi — chiamata dal router app_main."""
    st.title("📣 Marketing — Eventi e iscrizioni")
    st.caption(
        "Gestisci eventi pubblici (costellazioni, webinar, workshop) "
        "e raccolta iscrizioni online."
    )

    try:
        from modules.app_core import get_connection
        conn = get_connection()
    except Exception as e:
        st.error(f"❌ Connessione DB fallita: {e}")
        return

    tab_lista, tab_nuovo = st.tabs(["📅 Lista eventi", "🆕 Nuovo evento"])

    with tab_lista:
        _render_lista_eventi(conn)

    with tab_nuovo:
        _render_form_crea_evento(conn)


# =============================================================================
# TAB 1 — LISTA EVENTI
# =============================================================================

def _render_lista_eventi(conn):
    # Filtri
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_tempo = st.selectbox(
            "Periodo",
            options=["Tutti", "Solo futuri", "Solo passati"],
            key="ev_filtro_tempo",
        )
    with col2:
        filtro_tipo = st.selectbox(
            "Tipo",
            options=["Tutti"] + list(TIPI_VALIDI),
            key="ev_filtro_tipo",
        )
    with col3:
        filtro_attivi = st.selectbox(
            "Visibilità",
            options=["Tutti", "Solo attivi", "Solo nascosti"],
            key="ev_filtro_attivi",
        )

    # Recupera eventi
    try:
        eventi = lista_eventi(
            conn,
            solo_attivi=(filtro_attivi == "Solo attivi"),
            tipo=(filtro_tipo if filtro_tipo != "Tutti" else None),
            solo_futuri=(filtro_tempo == "Solo futuri"),
            ordina_desc=(filtro_tempo != "Solo futuri"),  # futuri: ASC; resto: DESC
        )
    except Exception as e:
        st.error(f"Errore caricamento eventi: {e}")
        return

    # Filtro client-side per "Solo passati" e "Solo nascosti"
    if filtro_tempo == "Solo passati":
        now = datetime.now()
        eventi = [
            e for e in eventi
            if e.get("data_ora") and _aware_to_naive(e["data_ora"]) < now
        ]
    if filtro_attivi == "Solo nascosti":
        eventi = [e for e in eventi if not e.get("attivo")]

    if not eventi:
        st.info("Nessun evento corrisponde ai filtri.")
        return

    st.caption(f"{len(eventi)} eventi trovati")
    st.divider()

    # Lista in expander
    for ev in eventi:
        _render_evento_card(conn, ev)


def _render_evento_card(conn, ev: dict):
    """Card collassabile per un singolo evento, con tutte le azioni."""
    titolo = ev.get("titolo", "(senza titolo)")
    data_ora = ev.get("data_ora")
    tipo = ev.get("tipo", "")
    attivo = ev.get("attivo", True)
    iscrizioni_aperte = ev.get("iscrizioni_aperte", True)

    confermati = conta_iscritti(conn, ev["id"], "confermata")
    in_attesa = conta_iscritti(conn, ev["id"], "lista_attesa")
    annullati = conta_iscritti(conn, ev["id"], "annullata")
    posti_max = ev.get("posti_max")

    # Label header espandibile
    data_str = data_ora.strftime("%d/%m/%Y · %H:%M") if data_ora else "(data n/d)"
    badges = []
    if not attivo:
        badges.append("🚫 nascosto")
    if not iscrizioni_aperte:
        badges.append("🔒 iscrizioni chiuse")
    if posti_max and confermati >= posti_max:
        badges.append("🎟️ sold out")
    badges_str = " · ".join(badges)

    posti_str = f"{confermati}/{posti_max}" if posti_max else f"{confermati}"

    header = f"**{titolo}** · {data_str} · {tipo} · 👥 {posti_str}"
    if badges_str:
        header += f" · {badges_str}"

    with st.expander(header):
        _render_evento_dettaglio(conn, ev, confermati, in_attesa, annullati)


def _render_evento_dettaglio(conn, ev: dict, confermati: int, in_attesa: int, annullati: int):
    """Dettaglio espanso: tabs Info / Iscritti / Azioni."""
    tab_info, tab_iscritti, tab_azioni = st.tabs(
        [f"ℹ️ Info & link pubblico", f"👥 Iscritti ({confermati + in_attesa})", "⚙️ Azioni"]
    )

    with tab_info:
        _render_tab_info(conn, ev, confermati, in_attesa, annullati)

    with tab_iscritti:
        _render_tab_iscritti(conn, ev)

    with tab_azioni:
        _render_tab_azioni(conn, ev)


# ----- TAB INFO -----

def _render_tab_info(conn, ev: dict, confermati: int, in_attesa: int, annullati: int):
    col1, col2, col3 = st.columns(3)
    col1.metric("Confermati", confermati)
    col2.metric("Lista attesa", in_attesa)
    col3.metric("Annullati", annullati)

    if ev.get("posti_max"):
        rimasti = posti_rimasti(conn, ev["id"])
        st.progress(
            min(1.0, confermati / ev["posti_max"]),
            text=f"{confermati}/{ev['posti_max']} posti — {rimasti} disponibili",
        )

    st.divider()

    if ev.get("descrizione"):
        st.markdown("**Descrizione:**")
        st.write(ev["descrizione"])

    info_table = []
    if ev.get("sede"):
        info_table.append(("📍 Sede", ev["sede"]))
    if ev.get("conduttore"):
        info_table.append(("👤 Conduttore", ev["conduttore"]))
    if ev.get("durata_minuti"):
        info_table.append(("⏱️ Durata", f"{ev['durata_minuti']} min"))
    if ev.get("prezzo") is not None:
        info_table.append(("💶 Prezzo", f"{float(ev['prezzo']):.2f} €"))
    if ev.get("fb_event_url"):
        info_table.append(("🔗 Evento Facebook", ev["fb_event_url"]))
    if ev.get("note_interne"):
        info_table.append(("📝 Note interne", ev["note_interne"]))

    for label, val in info_table:
        st.markdown(f"**{label}:** {val}")

    st.divider()

    # Link pubblico
    st.markdown("**🔗 Link pubblico per iscrizioni**")
    base = st.secrets.get("app", {}).get("BASE_URL", "https://testgestionale.streamlit.app")
    link_pubblico = f"{base.rstrip('/')}/iscrizione_evento?slug={ev['slug']}"
    st.code(link_pubblico, language=None)
    st.caption(
        "Copia questo link e incollalo nel post Facebook, in email, "
        "su WhatsApp, ecc. (La pagina pubblica verrà attivata allo step 4.)"
    )


# ----- TAB ISCRITTI -----

def _render_tab_iscritti(conn, ev: dict):
    filtro_stato = st.radio(
        "Filtra per stato",
        options=["Tutti", "Confermati", "Lista attesa", "Annullati"],
        horizontal=True,
        key=f"flt_iscr_{ev['id']}",
    )
    stato_map = {
        "Confermati": "confermata",
        "Lista attesa": "lista_attesa",
        "Annullati": "annullata",
    }
    stato_filter = stato_map.get(filtro_stato)

    iscrizioni = lista_iscrizioni(conn, ev["id"], stato=stato_filter)

    if not iscrizioni:
        st.info("Nessuna iscrizione trovata.")
        return

    # Tabella riassuntiva
    table_data = [
        {
            "ID": i["id"],
            "Nome": f"{i['cognome']} {i['nome']}",
            "Email": i["email"],
            "Telefono": i.get("telefono") or "",
            "Stato": i["stato"],
            "Iscritto il": i["created_at"].strftime("%d/%m/%Y %H:%M") if i.get("created_at") else "",
            "Email conferma": "✅" if i.get("email_conferma_inviata") else "—",
            "Paziente": i.get("paziente_id") or "—",
        }
        for i in iscrizioni
    ]
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # Export CSV
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=list(table_data[0].keys()))
    writer.writeheader()
    writer.writerows(table_data)
    st.download_button(
        "📥 Esporta CSV",
        data=csv_buf.getvalue().encode("utf-8"),
        file_name=f"iscritti_{ev['slug']}.csv",
        mime="text/csv",
        key=f"dl_csv_{ev['id']}",
    )

    st.divider()

    # Azioni per singola iscrizione
    st.markdown("**Azioni rapide su una iscrizione**")
    sel = st.selectbox(
        "Seleziona iscritto",
        options=iscrizioni,
        format_func=lambda i: f"#{i['id']} — {i['cognome']} {i['nome']} ({i['stato']})",
        key=f"sel_iscr_{ev['id']}",
    )
    if sel:
        col1, col2, col3 = st.columns(3)
        with col1:
            if sel["stato"] != "annullata":
                if st.button("❌ Annulla iscrizione", key=f"ann_{sel['id']}"):
                    try:
                        annulla_iscrizione(conn, sel["id"])
                        # Promuovi automaticamente il primo della lista attesa
                        promosso = promuovi_da_lista_attesa(conn, ev["id"])
                        st.success("Iscrizione annullata")
                        if promosso:
                            st.info(
                                f"Promosso da lista attesa: {promosso['cognome']} {promosso['nome']}"
                            )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
        with col2:
            if sel["stato"] == "lista_attesa":
                if st.button("⬆️ Promuovi", key=f"prom_{sel['id']}"):
                    try:
                        from .db_eventi import aggiorna_stato_iscrizione
                        aggiorna_stato_iscrizione(conn, sel["id"], "confermata")
                        st.success("Promosso a confermata")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
        with col3:
            if not sel.get("paziente_id"):
                with st.popover("🔗 Collega a paziente"):
                    paz_id = _selettore_paziente(conn, key_suffix=f"link_{sel['id']}")
                    if paz_id and st.button("Collega", key=f"do_link_{sel['id']}"):
                        try:
                            aggancia_paziente(conn, sel["id"], paz_id)
                            st.success("Collegato")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore: {e}")


# ----- TAB AZIONI -----

def _render_tab_azioni(conn, ev: dict):
    st.markdown("**Modifica evento**")

    with st.form(f"form_edit_{ev['id']}"):
        titolo = st.text_input("Titolo", value=ev.get("titolo", ""))
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox(
                "Tipo",
                options=list(TIPI_VALIDI),
                index=list(TIPI_VALIDI).index(ev.get("tipo", "altro")),
            )
        with col2:
            posti_max = st.number_input(
                "Posti max (0 = illimitati)",
                min_value=0, max_value=999,
                value=ev.get("posti_max") or 0,
            )

        col3, col4 = st.columns(2)
        with col3:
            data_ev = st.date_input("Data", value=ev["data_ora"].date() if ev.get("data_ora") else None)
        with col4:
            ora_ev = st.time_input("Ora", value=ev["data_ora"].time() if ev.get("data_ora") else time(20, 30))

        col5, col6 = st.columns(2)
        with col5:
            durata = st.number_input(
                "Durata (minuti, 0 = non specificata)",
                min_value=0, max_value=999,
                value=ev.get("durata_minuti") or 0,
            )
        with col6:
            prezzo = st.number_input(
                "Prezzo €",
                min_value=0.0, value=float(ev.get("prezzo") or 0), step=5.0,
            )

        sede = st.text_input("Sede", value=ev.get("sede") or "")
        conduttore = st.text_input("Conduttore", value=ev.get("conduttore") or "")
        descrizione = st.text_area("Descrizione", value=ev.get("descrizione") or "", height=120)
        fb_event_url = st.text_input("URL evento Facebook (opzionale)", value=ev.get("fb_event_url") or "")
        immagine_url = st.text_input("URL immagine (opzionale)", value=ev.get("immagine_url") or "")
        note_interne = st.text_area("Note interne (non pubbliche)", value=ev.get("note_interne") or "", height=80)

        if st.form_submit_button("💾 Salva modifiche", type="primary"):
            try:
                aggiorna_evento(
                    conn, ev["id"],
                    titolo=titolo,
                    tipo=tipo,
                    data_ora=datetime.combine(data_ev, ora_ev, tzinfo=ROME_TZ),
                    durata_minuti=durata if durata > 0 else None,
                    sede=sede or None,
                    descrizione=descrizione or None,
                    posti_max=posti_max if posti_max > 0 else None,
                    prezzo=prezzo if prezzo > 0 else None,
                    fb_event_url=fb_event_url or None,
                    immagine_url=immagine_url or None,
                    conduttore=conduttore or None,
                    note_interne=note_interne or None,
                )
                st.success("✅ Evento aggiornato")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

    st.divider()
    st.markdown("**Visibilità e iscrizioni**")

    col1, col2 = st.columns(2)
    with col1:
        if ev.get("attivo"):
            if st.button("🚫 Nascondi evento", key=f"hide_{ev['id']}"):
                toggle_evento_attivo(conn, ev["id"], False)
                st.success("Evento nascosto")
                st.rerun()
        else:
            if st.button("✅ Mostra evento", key=f"show_{ev['id']}", type="primary"):
                toggle_evento_attivo(conn, ev["id"], True)
                st.success("Evento riattivato")
                st.rerun()
    with col2:
        if ev.get("iscrizioni_aperte"):
            if st.button("🔒 Chiudi iscrizioni", key=f"close_{ev['id']}"):
                toggle_iscrizioni_aperte(conn, ev["id"], False)
                st.success("Iscrizioni chiuse")
                st.rerun()
        else:
            if st.button("🔓 Riapri iscrizioni", key=f"open_{ev['id']}", type="primary"):
                toggle_iscrizioni_aperte(conn, ev["id"], True)
                st.success("Iscrizioni riaperte")
                st.rerun()

    st.divider()
    st.markdown("**📤 Re-invia email di conferma**")
    st.caption(
        "Re-invia l'email di conferma (con PDF aggiornato dal DB) a tutti gli iscritti "
        "che hanno stato **confermata**. Utile se hai corretto un dato dell'evento "
        "(orario, sede, conduttore) e vuoi notificare gli iscritti già registrati."
    )

    # Conta iscritti confermati
    try:
        from .db_eventi import lista_iscrizioni
        iscritti_confermati = lista_iscrizioni(conn, ev["id"], stato="confermata")
    except Exception as e:
        st.error(f"Errore lettura iscritti: {e}")
        iscritti_confermati = []

    if not iscritti_confermati:
        st.info("Nessun iscritto confermato per questo evento.")
    else:
        st.write(
            f"Iscritti confermati: **{len(iscritti_confermati)}** "
            f"({', '.join(i.get('email', '?') for i in iscritti_confermati[:3])}"
            f"{', ...' if len(iscritti_confermati) > 3 else ''})"
        )

        # Doppia conferma
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            conferma_reinvio = st.checkbox(
                f"✋ Confermo: voglio re-inviare l'email a tutti i {len(iscritti_confermati)} iscritti",
                key=f"chk_reinvia_{ev['id']}",
            )
        with col_btn2:
            if conferma_reinvio:
                if st.button(
                    "📤 Invia ora",
                    type="primary",
                    key=f"btn_reinvia_{ev['id']}",
                    use_container_width=True,
                ):
                    # Import lazy per evitare errori se moduli non disponibili
                    try:
                        from .email_eventi import invia_conferma_iscritto
                        from .pdf_evento import genera_pdf_conferma
                    except Exception as e:
                        st.error(f"Errore import: {e}")
                        st.stop()

                    successi = 0
                    errori = []
                    progress = st.progress(0, text="Invio in corso...")

                    for i, iscr in enumerate(iscritti_confermati):
                        try:
                            # Rigenera il PDF con i dati attuali (rilegge il DB)
                            pdf_bytes = genera_pdf_conferma(ev, iscr)
                            invia_conferma_iscritto(ev, iscr, pdf_bytes=pdf_bytes)
                            successi += 1
                        except Exception as e:
                            errori.append(f"{iscr.get('email', '?')}: {e}")
                        progress.progress(
                            (i + 1) / len(iscritti_confermati),
                            text=f"Inviata {i+1}/{len(iscritti_confermati)}",
                        )

                    progress.empty()

                    if successi:
                        st.success(f"✅ {successi} email inviate con successo")
                    if errori:
                        st.error(f"❌ {len(errori)} errori:")
                        for err in errori:
                            st.code(err)

    st.divider()
    st.markdown("**🔔 Promemoria pre-evento (48h / 24h)**")
    st.caption(
        "I promemoria email partono in automatico ogni notte (48h e 24h prima). "
        "Qui puoi inviarli manualmente subito, oppure generare la lista WhatsApp "
        "da inviare a mano."
    )

    tab_email, tab_wa = st.tabs(["📧 Email", "💬 WhatsApp (manuale)"])

    with tab_email:
        tipo_prom = st.radio(
            "Tipo promemoria",
            options=["48h", "24h"],
            horizontal=True,
            key=f"tipo_prom_{ev['id']}",
            help="48h = 'tra due giorni', 24h = 'ci vediamo domani'",
        )

        try:
            from .db_eventi import iscritti_senza_promemoria, lista_iscrizioni
            non_inviati = iscritti_senza_promemoria(conn, ev["id"], tipo_prom)
            tutti_confermati = lista_iscrizioni(conn, ev["id"], stato="confermata")
        except Exception as e:
            st.error(f"Errore lettura iscritti: {e}")
            non_inviati = []
            tutti_confermati = []

        st.write(
            f"Iscritti confermati: **{len(tutti_confermati)}** · "
            f"Non hanno ancora ricevuto il promemoria {tipo_prom}: **{len(non_inviati)}**"
        )

        if non_inviati:
            conferma_prom = st.checkbox(
                f"✋ Confermo invio promemoria {tipo_prom} a {len(non_inviati)} iscritti",
                key=f"chk_prom_{ev['id']}_{tipo_prom}",
            )
            if conferma_prom and st.button(
                f"📧 Invia promemoria {tipo_prom} ora",
                type="primary",
                key=f"btn_prom_{ev['id']}_{tipo_prom}",
            ):
                try:
                    from .email_eventi import invia_promemoria_iscritto
                    from .db_eventi import marca_promemoria_inviato
                except Exception as e:
                    st.error(f"Errore import: {e}")
                    st.stop()

                successi, errori = 0, []
                progress = st.progress(0, text="Invio...")
                for i, iscr in enumerate(non_inviati):
                    try:
                        invia_promemoria_iscritto(ev, iscr, tipo_prom)
                        marca_promemoria_inviato(conn, iscr["id"], tipo_prom)
                        successi += 1
                    except Exception as e:
                        errori.append(f"{iscr.get('email','?')}: {e}")
                    progress.progress((i + 1) / len(non_inviati),
                                      text=f"Inviata {i+1}/{len(non_inviati)}")
                progress.empty()
                if successi:
                    st.success(f"✅ {successi} promemoria {tipo_prom} inviati")
                if errori:
                    st.error(f"❌ {len(errori)} errori:")
                    for err in errori:
                        st.code(err)
        else:
            st.info(f"Tutti gli iscritti confermati hanno già ricevuto il promemoria {tipo_prom}.")

    with tab_wa:
        tipo_wa = st.radio(
            "Tipo messaggio",
            options=["48h", "24h"],
            horizontal=True,
            key=f"tipo_wa_{ev['id']}",
        )
        st.caption(
            "Clicca il link 💬 di ogni iscritto per aprire WhatsApp con il messaggio "
            "già pronto. Devi solo premere invio. (Funziona se il telefono è valido.)"
        )

        try:
            from .db_eventi import lista_iscrizioni
            from .promemoria_eventi import genera_lista_whatsapp
            confermati = lista_iscrizioni(conn, ev["id"], stato="confermata")
            lista_wa = genera_lista_whatsapp(ev, confermati, tipo_wa)
        except Exception as e:
            st.error(f"Errore: {e}")
            lista_wa = []

        if not lista_wa:
            st.info("Nessun iscritto confermato.")
        else:
            for voce in lista_wa:
                c1, c2 = st.columns([0.55, 0.45])
                with c1:
                    st.markdown(f"**{voce['nome']}**")
                    st.caption(f"📞 {voce['telefono']}")
                with c2:
                    if voce["link_wa"]:
                        st.link_button(
                            "💬 Apri WhatsApp",
                            voce["link_wa"],
                            use_container_width=True,
                        )
                    else:
                        st.caption("❌ telefono non valido")
                with st.expander("Vedi/copia messaggio"):
                    st.code(voce["messaggio"], language=None)

    st.divider()
    st.markdown("**⚠️ Zona pericolosa**")
    with st.popover("🗑️ Elimina evento definitivamente"):
        st.error(
            "⚠️ ATTENZIONE: questa azione **cancella anche tutte le iscrizioni** "
            "associate all'evento. Non si può annullare."
        )
        conferma = st.text_input(
            f"Per confermare scrivi: ELIMINA",
            key=f"conf_del_{ev['id']}",
        )
        if conferma == "ELIMINA":
            if st.button(
                "🗑️ Conferma eliminazione",
                key=f"do_del_{ev['id']}",
                type="primary",
            ):
                try:
                    elimina_evento(conn, ev["id"])
                    st.success("Evento eliminato")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# =============================================================================
# TAB 2 — NUOVO EVENTO
# =============================================================================

def _render_form_crea_evento(conn):
    st.markdown("Compila i campi obbligatori (✱) e clicca **Crea evento**.")

    with st.form("form_crea_evento"):
        titolo = st.text_input("Titolo ✱")

        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo ✱", options=list(TIPI_VALIDI))
        with col2:
            posti_max = st.number_input("Posti max (0 = illimitati)", min_value=0, max_value=999, value=0)

        col3, col4 = st.columns(2)
        with col3:
            data_ev = st.date_input("Data ✱", value=datetime.now().date() + timedelta(days=7))
        with col4:
            ora_ev = st.time_input("Ora ✱", value=time(20, 30))

        col5, col6 = st.columns(2)
        with col5:
            durata = st.number_input("Durata (minuti)", min_value=0, max_value=999, value=120)
        with col6:
            prezzo = st.number_input("Prezzo €", min_value=0.0, value=0.0, step=5.0)

        sede = st.text_input("Sede", placeholder="Es: Studio The Organism, Via De Rosa 46, Pagani")
        conduttore = st.text_input("Conduttore", placeholder="Es: Dr. Giuseppe ...")
        descrizione = st.text_area("Descrizione (pubblica)", height=120)
        fb_event_url = st.text_input("URL evento Facebook (opzionale)")
        immagine_url = st.text_input("URL immagine (opzionale)")
        note_interne = st.text_area("Note interne (non pubbliche)", height=80)

        col7, col8 = st.columns(2)
        with col7:
            attivo = st.checkbox("Visibile (attivo)", value=True)
        with col8:
            iscrizioni_aperte = st.checkbox("Iscrizioni aperte", value=True)

        if st.form_submit_button("🆕 Crea evento", type="primary"):
            if not titolo or not titolo.strip():
                st.error("Il titolo è obbligatorio")
                return
            try:
                nuovo = crea_evento(
                    conn,
                    titolo=titolo,
                    tipo=tipo,
                    data_ora=datetime.combine(data_ev, ora_ev, tzinfo=ROME_TZ),
                    durata_minuti=durata if durata > 0 else None,
                    sede=sede or None,
                    descrizione=descrizione or None,
                    posti_max=posti_max if posti_max > 0 else None,
                    prezzo=prezzo if prezzo > 0 else None,
                    fb_event_url=fb_event_url or None,
                    immagine_url=immagine_url or None,
                    conduttore=conduttore or None,
                    attivo=attivo,
                    iscrizioni_aperte=iscrizioni_aperte,
                    note_interne=note_interne or None,
                )
                st.success(f"✅ Evento creato — id #{nuovo['id']}, slug: `{nuovo['slug']}`")
                st.balloons()
                st.info("Vai sul tab **Lista eventi** per gestirlo e copiare il link pubblico.")
            except Exception as e:
                st.error(f"Errore creazione evento: {e}")


# =============================================================================
# HELPER
# =============================================================================

def _aware_to_naive(dt: datetime) -> datetime:
    """Rimuove timezone per confronti con datetime.now() naive."""
    if dt.tzinfo is None:
        return dt
    return dt.replace(tzinfo=None)


def _selettore_paziente(conn, key_suffix: str = "") -> Optional[int]:
    """Selettore paziente per agganciare iscrizione → paziente esistente."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome FROM Pazienti "
            "WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' "
            "ORDER BY Cognome, Nome"
        )
        rows = cur.fetchall() or []
        cur.close()
    except Exception as e:
        st.error(f"Errore caricamento pazienti: {e}")
        return None

    if not rows:
        st.info("Nessun paziente registrato.")
        return None

    def _label(r):
        if isinstance(r, dict):
            return f"{r.get('id')} — {r.get('Cognome','')} {r.get('Nome','')}"
        return f"{r[0]} — {r[1]} {r[2]}"

    sel = st.selectbox(
        "Paziente",
        options=rows,
        format_func=_label,
        key=f"sel_paz_ev_{key_suffix}",
    )
    if isinstance(sel, dict):
        return int(sel.get("id"))
    return int(sel[0])
