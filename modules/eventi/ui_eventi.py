# -*- coding: utf-8 -*-
"""
modules/eventi/ui_eventi.py

UI admin del modulo Eventi.
Entry point: render_eventi_section()

Funzionalità:
- Tab Lista eventi: visualizza eventi con filtri, espande per dettaglio
- Tab Nuovo evento: form di creazione (con fasce orarie opzionali)
- Dettaglio evento: modifica, lista iscritti, export CSV, link pubblico,
  occupazione slot, promozione lista attesa, annullamento iscrizioni,
  eliminazione evento
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
    crea_iscrizione,
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

# URL dell'app pubblica dove gira la pagina di iscrizione (apps/pnev_pubblico.py).
# Sovrascrivibile dai secrets con APP_URL_PUBBLICO se cambia il deploy.
APP_URL_PUBBLICO_DEFAULT = "https://gestionale-the-organism-n77ucp3n4us2hmqke9ck7n.streamlit.app"


# =============================================================================
# ENTRY POINT
# =============================================================================

def render_eventi_section():
    """Entry point UI eventi — chiamata dal router app_main."""
    st.title("📣 Marketing — Eventi e iscrizioni")
    st.caption(
        "Gestisci eventi pubblici (costellazioni, webinar, workshop, screening) "
        "e raccolta iscrizioni online — con fasce orarie opzionali."
    )

    try:
        from modules.app_core import get_connection
        conn = get_connection()
    except Exception as e:
        st.error(f"❌ Connessione DB fallita: {e}")
        return

    try:
        from .slots import ensure_slot_schema
        ensure_slot_schema(conn)
    except Exception as e:
        st.warning(f"Schema fasce orarie non applicato: {e}")

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
    if ev.get("slot_abilitati"):
        badges.append("🕐 fasce orarie")
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

    # ── Occupazione fasce orarie ───────────────────────────────────────
    if ev.get("slot_abilitati"):
        st.divider()
        st.markdown("**🕐 Occupazione fasce orarie**")
        try:
            from .slots import slot_con_disponibilita
            slots = slot_con_disponibilita(conn, ev)
        except Exception as e:
            slots = []
            st.error(f"Errore lettura slot: {e}")
        if not slots:
            st.caption("Nessuno slot generato: controlla ora inizio/fine nella tab Azioni.")
        else:
            cols = st.columns(4)
            for i, s in enumerate(slots):
                with cols[i % 4]:
                    etichetta = s["orario"].strftime("%H:%M")
                    if s["liberi"] == 0:
                        st.error(f"🔴 {etichetta} — pieno ({s['occupati']}/{s['posti_max']})")
                    elif s["occupati"] > 0:
                        st.warning(f"🟡 {etichetta} — {s['occupati']}/{s['posti_max']}")
                    else:
                        st.success(f"🟢 {etichetta} — libero")

    st.divider()

    # Link pubblico
    st.markdown("**🔗 Link pubblico per iscrizioni**")
    base_pubblico = st.secrets.get("APP_URL_PUBBLICO", APP_URL_PUBBLICO_DEFAULT).rstrip("/")
    link_pubblico = f"{base_pubblico}/?azione=iscrizione_evento&slug={ev['slug']}"
    st.code(link_pubblico, language=None)
    st.caption(
        "Copia questo link e incollalo nel post Facebook, in email, su WhatsApp, ecc. "
        + ("Chi lo apre scegli la fascia oraria libera e l'appuntamento viene creato "
           "in automatico anche sul Google Calendar dello studio."
           if ev.get("slot_abilitati") else "")
    )

    st.markdown("**🌐 Pubblicazione su pnev.it**")
    if ev.get("wp_url"):
        st.caption(f"Già pubblicato: {ev['wp_url']}")
    c_wp1, c_wp2 = st.columns(2)
    with c_wp1:
        if st.button("🚀 Pubblica / aggiorna su pnev.it", key=f"wp_pub_{ev['id']}"):
            from .wp_publish import pubblica_evento
            ok, msg = pubblica_evento(conn, ev, link_pubblico)
            if ok:
                st.success(f"Pubblicato: {msg}")
                st.rerun()
            else:
                st.error(msg)
    with c_wp2:
        if ev.get("wp_url"):
            if st.button("🗑️ Rimuovi da pnev.it", key=f"wp_rm_{ev['id']}"):
                from .wp_publish import rimuovi_evento
                ok, msg = rimuovi_evento(conn, ev)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ----- TAB ISCRITTI -----

def _render_tab_iscritti(conn, ev: dict):
    with st.popover("✉️ Test notifiche email"):
        # Le email degli eventi viaggiano su DUE strade diverse: le notifiche
        # scritte a mano dal gestionale passano da email_otp, le conferme
        # della pagina pubblica di iscrizione passano da email_eventi.
        # Finche' qui si provava solo la prima, il test diceva OK mentre le
        # conferme non partivano: erano proprio le due strade a non avere la
        # stessa configurazione. Ora si controllano entrambe.
        from modules.email_otp import diagnostica_email, invia_email as _ie

        st.markdown("**1 · Notifiche interne** (avvisi allo studio, iscrizioni manuali)")
        ok1, msg1 = diagnostica_email()
        (st.success if ok1 else st.error)(msg1)

        st.markdown("**2 · Conferme agli iscritti** (pagina pubblica di iscrizione)")
        try:
            from .email_eventi import diagnostica_invio
            ok2, msg2 = diagnostica_invio()
        except Exception as _e:
            ok2, msg2 = False, f"Diagnostica non disponibile: {_e}"
        (st.success if ok2 else st.error)(msg2)

        if ok1 and ok2:
            st.caption("Entrambe le strade funzionano: le conferme partono per "
                       "tutti gli eventi, comunque sia stata fatta l'iscrizione.")
        elif ok1 and not ok2:
            st.warning("Le notifiche interne partono, le conferme agli iscritti no. "
                       "È il caso in cui le email sembrano arrivare «per certi "
                       "eventi sì e per altri no»: dipende da come è stata fatta "
                       "l'iscrizione, non dall'evento.")

        st.divider()
        dest_test = st.text_input("Invia una mail di prova a", key=f"test_mail_{ev['id']}")
        if st.button("Invia prova", key=f"btn_test_mail_{ev['id']}") and dest_test.strip():
            esito = _ie(dest_test.strip(), "[Test] Notifiche gestionale",
                        "Se leggi questa mail, le notifiche del gestionale funzionano.")
            (st.success if esito else st.error)("Inviata." if esito else "Invio fallito.")

    if st.toggle("➕ Aggiungi iscrizione manualmente", key=f"tg_man_{ev['id']}"):
        # Il modulo chiedeva sempre "Nome genitore" e i dati del bambino, anche
        # per Costellazioni, webinar e workshop, che sono eventi per adulti:
        # l'operatore si trovava a scrivere il nome di un adulto in un campo
        # che diceva "genitore" e due campi bambino da lasciare vuoti.
        # Lo screening e' l'unico tipo in cui un genitore accompagna un
        # bambino; per gli altri si presume l'iscritto adulto, ma la
        # presunzione si puo' sempre ribaltare con la spunta qui sotto —
        # esistono workshop per famiglie.
        _tipo_ev = (ev.get("tipo") or "").strip().lower()
        _default_con_bambino = _tipo_ev == "screening"
        con_bambino = st.checkbox(
            "L'iscritto accompagna un bambino/a",
            value=_default_con_bambino,
            key=f"man_conbimbo_{ev['id']}",
            help="Attivo di default per lo screening. Per costellazioni, webinar e "
                 "workshop l'iscritto è la persona adulta che partecipa.")
        _et_nome = "Nome genitore" if con_bambino else "Nome"
        _et_cognome = "Cognome genitore" if con_bambino else "Cognome"

        with st.form(f"form_manuale_{ev['id']}"):
            c1, c2 = st.columns(2)
            m_nome = c1.text_input(_et_nome, key=f"man_nome_{ev['id']}")
            m_cognome = c2.text_input(_et_cognome, key=f"man_cognome_{ev['id']}")
            c3, c4 = st.columns(2)
            m_email = c3.text_input("Email", key=f"man_email_{ev['id']}")
            m_telefono = c4.text_input("Telefono", key=f"man_tel_{ev['id']}")
            m_nome_b = m_cognome_b = ""
            if con_bambino:
                c5, c6 = st.columns(2)
                m_nome_b = c5.text_input("Nome bambino/a", key=f"man_nomeb_{ev['id']}")
                m_cognome_b = c6.text_input("Cognome bambino/a", key=f"man_cognomeb_{ev['id']}")
            m_slot = None
            if ev.get("slot_abilitati"):
                from .slots import slot_con_disponibilita
                opzioni_slot = [s for s in slot_con_disponibilita(conn, ev) if s["liberi"] > 0]
                if opzioni_slot:
                    m_slot = st.selectbox(
                        "Fascia oraria", options=opzioni_slot,
                        format_func=lambda s: f"{s['orario'].strftime('%d/%m/%Y %H:%M')} ({s['liberi']} liberi)",
                        key=f"man_slot_{ev['id']}")
                else:
                    st.caption("Nessuna fascia con posti disponibili.")
            m_note = st.text_area("Note", key=f"man_note_{ev['id']}", height=68)
            m_stato_forzato = st.selectbox("Stato", ["Automatico", "Confermata", "Lista d'attesa"],
                                            key=f"man_stato_{ev['id']}")
            invia = st.form_submit_button("Aggiungi", type="primary")
        if invia:
            if not m_nome.strip() or not m_cognome.strip() or not m_email.strip():
                st.error("Nome, cognome ed email sono obbligatori.")
            else:
                try:
                    forza = {"Automatico": None, "Confermata": "confermata",
                             "Lista d'attesa": "lista_attesa"}[m_stato_forzato]
                    nota_completa = (f"Bambino/a: {m_nome_b.strip()} {m_cognome_b.strip()}"
                                      if (m_nome_b.strip() or m_cognome_b.strip()) else "")
                    if m_note.strip():
                        nota_completa = (nota_completa + " · " + m_note.strip()).strip(" ·")
                    nuova = crea_iscrizione(
                        conn, evento_id=ev["id"], nome=m_nome.strip(), cognome=m_cognome.strip(),
                        email=m_email.strip(), telefono=m_telefono.strip() or None,
                        note=nota_completa or None, consenso_privacy=True,
                        sorgente="manuale_studio", forza_stato=forza,
                    )
                    if m_slot:
                        from .slots import assegna_slot
                        assegna_slot(conn, nuova["id"], m_slot["orario"])
                    # Anagrafica automatica anche per l'inserimento manuale —
                    # usa i dati del BAMBINO (il paziente), non del genitore.
                    try:
                        cur_an = conn.cursor()
                        cog_m = (m_cognome_b.strip() or m_cognome.strip()).upper()
                        nom_m = (m_nome_b.strip() or m_nome.strip()).upper()
                        cur_an.execute(
                            "SELECT id FROM pazienti WHERE UPPER(cognome)=%s AND UPPER(nome)=%s LIMIT 1",
                            (cog_m, nom_m))
                        esistente = cur_an.fetchone()
                        if esistente:
                            paz_auto_id = int(esistente["id"] if isinstance(esistente, dict) else esistente[0])
                        else:
                            paz_auto_id = _crea_paziente_da_iscrizione(conn, {
                                "cognome": cog_m, "nome": nom_m,
                                "email": m_email, "telefono": m_telefono})
                        aggancia_paziente(conn, nuova["id"], paz_auto_id)
                    except Exception:
                        try: conn.rollback()
                        except Exception: pass
                    try:
                        from modules.email_otp import invia_email
                        riga_slot = (f"Slot: {m_slot['orario'].strftime('%d/%m/%Y alle %H:%M')}\n"
                                     if m_slot else "")
                        corpo_staff = (
                            f"Nuova iscrizione inserita manualmente dallo studio.\n\n"
                            f"Evento: {ev['titolo']}\n{riga_slot}"
                            f"Genitore: {m_cognome.strip()} {m_nome.strip()}\n"
                            f"Bambino/a: {m_cognome_b.strip()} {m_nome_b.strip()}\n"
                            f"Email: {m_email.strip()} · Tel: {m_telefono.strip() or '—'}\n"
                            f"Stato: {(forza or 'automatico').upper()}\n"
                            f"Note: {m_note.strip() or '—'}"
                        )
                        for dest in ("apstheorganism@gmail.com", "dr.ferraioligiuseppe@gmail.com"):
                            try:
                                invia_email(dest, f"[Iscrizione manuale] {ev['titolo']}", corpo_staff)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    st.success("Iscrizione aggiunta.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

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
            "Orario": i["slot_orario"].strftime("%d/%m %H:%M") if i.get("slot_orario") else "",
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
        if st.toggle("✏️ Modifica dati di questa iscrizione", key=f"tg_edit_{sel['id']}"):
            with st.form(f"form_edit_iscr_{sel['id']}"):
                e1, e2 = st.columns(2)
                e_nome = e1.text_input("Nome genitore", value=sel.get("nome") or "", key=f"ed_nome_{sel['id']}")
                e_cognome = e2.text_input("Cognome genitore", value=sel.get("cognome") or "", key=f"ed_cog_{sel['id']}")
                e3, e4 = st.columns(2)
                e_email = e3.text_input("Email", value=sel.get("email") or "", key=f"ed_email_{sel['id']}")
                e_tel = e4.text_input("Telefono", value=sel.get("telefono") or "", key=f"ed_tel_{sel['id']}")
                e_note = st.text_area("Note (incluso nome del bambino)", value=sel.get("note") or "",
                                       key=f"ed_note_{sel['id']}", height=68)
                e_slot = None
                if ev.get("slot_abilitati"):
                    from .slots import slot_con_disponibilita
                    tutti_slot = slot_con_disponibilita(conn, ev)
                    attuale = sel.get("slot_orario")
                    opzioni = [s for s in tutti_slot if s["liberi"] > 0 or (attuale and s["orario"] == attuale)]
                    if opzioni:
                        idx_def = next((i for i, s in enumerate(opzioni) if attuale and s["orario"] == attuale), 0)
                        e_slot = st.selectbox(
                            "Fascia oraria", options=opzioni, index=idx_def,
                            format_func=lambda s: f"{s['orario'].strftime('%d/%m/%Y %H:%M')} ({s['liberi']} liberi)",
                            key=f"ed_slot_{sel['id']}")
                salva_mod = st.form_submit_button("💾 Salva modifiche", type="primary")
            if salva_mod:
                try:
                    cur_e = conn.cursor()
                    cur_e.execute(
                        "UPDATE ev_iscrizioni SET nome=%s, cognome=%s, email=%s, telefono=%s, note=%s "
                        "WHERE id=%s",
                        (e_nome.strip(), e_cognome.strip(), e_email.strip(),
                         e_tel.strip() or None, e_note.strip() or None, sel["id"]))
                    conn.commit()
                    if e_slot:
                        from .slots import assegna_slot
                        assegna_slot(conn, sel["id"], e_slot["orario"])
                    st.success("Iscrizione aggiornata.")
                    st.rerun()
                except Exception as e:
                    try: conn.rollback()
                    except Exception: pass
                    st.error(f"Errore: {e}")

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
                if st.button("➕ Crea anagrafica da questa iscrizione", key=f"crea_paz_{sel['id']}"):
                    try:
                        nuovo_id = _crea_paziente_da_iscrizione(conn, sel)
                        aggancia_paziente(conn, sel["id"], nuovo_id)
                        st.success(f"Anagrafica creata (ID {nuovo_id}) e collegata.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

    st.markdown("---")
    st.markdown("**🔧 Sanatoria iscrizioni già presenti**")
    st.caption("Per gli iscritti inseriti prima degli aggiornamenti: crea le anagrafiche mancanti "
               "e reinvia le email di conferma non ancora partite.")
    sa1, sa2 = st.columns(2)
    if sa1.button("➕ Crea anagrafiche mancanti (tutti)", key=f"sanatoria_anag_{ev['id']}"):
        creati, gia_ok, errori = 0, 0, 0
        for i in iscrizioni:
            if i.get("paziente_id") or i["stato"] == "annullata":
                gia_ok += 1
                continue
            try:
                cur_s = conn.cursor()
                cur_s.execute(
                    "SELECT id FROM pazienti WHERE (email IS NOT NULL AND LOWER(email)=%s) "
                    "OR (UPPER(cognome)=%s AND UPPER(nome)=%s) LIMIT 1",
                    ((i.get("email") or "").lower(), (i.get("cognome") or "").upper(),
                     (i.get("nome") or "").upper()))
                ex = cur_s.fetchone()
                pid = int(ex["id"] if isinstance(ex, dict) else ex[0]) if ex else _crea_paziente_da_iscrizione(conn, i)
                aggancia_paziente(conn, i["id"], pid)
                creati += 1
            except Exception:
                try: conn.rollback()
                except Exception: pass
                errori += 1
        st.success(f"Anagrafiche collegate: {creati} · già a posto: {gia_ok} · errori: {errori}")
        st.rerun()

    if sa2.button("✉️ Reinvia conferme mancanti", key=f"sanatoria_mail_{ev['id']}"):
        from modules.email_otp import invia_email as _invia
        from .db_eventi import mark_email_conferma_inviata
        inviate, saltate, falliti = 0, 0, 0
        for i in iscrizioni:
            if i.get("email_conferma_inviata") or i["stato"] == "annullata" or not i.get("email"):
                saltate += 1
                continue
            try:
                slot_txt = (f"Appuntamento: {i['slot_orario'].strftime('%d/%m/%Y alle %H:%M')}\n"
                            if i.get("slot_orario") else
                            (f"Data: {ev['data_ora'].strftime('%d/%m/%Y alle %H:%M')}\n" if ev.get("data_ora") else ""))
                if i["stato"] == "lista_attesa":
                    corpo = (f"Ciao {i.get('nome','')},\n\nla tua iscrizione a \"{ev['titolo']}\" è stata "
                             f"registrata in LISTA D'ATTESA.\nTi contatteremo se si libera un posto.\n")
                    ogg = f"Sei in lista d'attesa — {ev['titolo']}"
                else:
                    corpo = (f"Ciao {i.get('nome','')},\n\nla tua iscrizione a \"{ev['titolo']}\" è confermata.\n"
                             + slot_txt)
                    ogg = f"Iscrizione confermata — {ev['titolo']}"
                if ev.get("sede"):
                    corpo += f"Sede: {ev['sede']}\n"
                corpo += "\nPer qualsiasi domanda scrivi a apstheorganism@gmail.com.\n\nStudio The Organism"
                if _invia(i["email"], ogg, corpo):
                    try: mark_email_conferma_inviata(conn, i["id"])
                    except Exception: pass
                    inviate += 1
                else:
                    falliti += 1
            except Exception:
                falliti += 1
        st.success(f"Email inviate: {inviate} · saltate (già inviate/annullate): {saltate} · fallite: {falliti}")
        st.rerun()

def _crea_paziente_da_iscrizione(conn, sel: dict) -> int:
    """Crea una nuova anagrafica dai dati dell'iscrizione a un evento.
    Il consenso privacy risulta già firmato al momento dell'iscrizione
    (spunta obbligatoria nel form pubblico), quindi viene registrato subito
    anche in consensi_privacy."""
    cur = conn.cursor()
    cognome = (sel.get("cognome") or "").strip().upper()
    nome = (sel.get("nome") or "").strip().upper()
    email = (sel.get("email") or "").strip().lower()
    tel = (sel.get("telefono") or "").strip()
    cur.execute(
        "INSERT INTO pazienti (cognome, nome, telefono, email, stato_paziente) "
        "VALUES (%s,%s,%s,%s,'ATTIVO') RETURNING id",
        (cognome, nome, tel or None, email or None),
    )
    row = cur.fetchone()
    nuovo_id = int(row["id"] if isinstance(row, dict) else row[0])
    try:
        cur.execute("""
            INSERT INTO consensi_privacy
            (paziente_id, tipo, consenso_trattamento, consenso_comunicazioni,
             canale_email, canale_whatsapp, data_ora, note)
            VALUES (%s,'adulto',1,1,1,1,NOW(),'Consenso firmato in fase di iscrizione evento')
        """, (nuovo_id,))
    except Exception:
        pass
    conn.commit()
    return nuovo_id


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
                "Posti max (0 = illimitati — lascia 0 se usi le fasce orarie)",
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

        st.divider()
        st.markdown("**🕐 Fasce orarie** — es. screening scolastico: 4 slot all'ora, ogni 15 minuti")
        slot_abilitati = st.checkbox("Abilita fasce orarie per questo evento", value=bool(ev.get("slot_abilitati")))
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            slot_ora_inizio = st.time_input("Fascia 1 — Dalle", value=ev.get("slot_ora_inizio") or time(9, 0))
        with cs2:
            slot_ora_fine = st.time_input("Fascia 1 — Alle", value=ev.get("slot_ora_fine") or time(13, 0))
        with cs3:
            slot_durata_minuti = st.number_input(
                "Durata slot (min)", min_value=5, max_value=120,
                value=int(ev.get("slot_durata_minuti") or 15),
            )
        with cs4:
            slot_posti = st.number_input(
                "Posti per slot", min_value=1, max_value=20,
                value=int(ev.get("slot_posti") or 1),
            )
        st.caption("Seconda fascia (opzionale) — es. pomeriggio 16:00-18:00. Lascia vuoto/uguale se non serve.")
        cs5, cs6 = st.columns(2)
        with cs5:
            slot_ora_inizio_2 = st.time_input("Fascia 2 — Dalle", value=ev.get("slot_ora_inizio_2") or time(0, 0), key=f"s2i_{ev['id']}")
        with cs6:
            slot_ora_fine_2 = st.time_input("Fascia 2 — Alle", value=ev.get("slot_ora_fine_2") or time(0, 0), key=f"s2f_{ev['id']}")

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
                    slot_abilitati=slot_abilitati,
                    slot_durata_minuti=slot_durata_minuti,
                    slot_ora_inizio=slot_ora_inizio,
                    slot_ora_fine=slot_ora_fine,
                    slot_ora_inizio_2=slot_ora_inizio_2 if slot_ora_inizio_2 != time(0, 0) else None,
                    slot_ora_fine_2=slot_ora_fine_2 if slot_ora_fine_2 != time(0, 0) else None,
                    slot_posti=slot_posti,
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
                with st.popover("Vedi/copia messaggio"):
                    st.code(voce["messaggio"], language=None)

    st.divider()
    st.markdown("**📋 Duplica evento in un'altra data**")
    st.caption("Copia titolo, tipo, sede, descrizione, posti e configurazione delle fasce orarie. "
               "Le iscrizioni NON vengono copiate.")
    with st.form(f"form_dup_{ev['id']}"):
        d1, d2 = st.columns(2)
        dup_data = d1.date_input("Nuova data", value=datetime.now().date(), key=f"dup_data_{ev['id']}")
        _ora_orig = ev["data_ora"].time() if ev.get("data_ora") else time(9, 0)
        dup_ora = d2.time_input("Nuovo orario", value=_ora_orig, key=f"dup_ora_{ev['id']}")
        dup_titolo = st.text_input("Titolo del nuovo evento",
                                    value=f"{ev.get('titolo','')} — {dup_data.strftime('%d/%m/%Y')}"
                                    if ev.get("titolo") else "",
                                    key=f"dup_tit_{ev['id']}")
        duplica = st.form_submit_button("📋 Crea copia", type="primary")
    if duplica:
        try:
            nuovo = crea_evento(
                conn,
                titolo=dup_titolo.strip() or ev.get("titolo", "Evento"),
                tipo=ev.get("tipo", "altro"),
                data_ora=datetime.combine(dup_data, dup_ora),
                durata_minuti=ev.get("durata_minuti"),
                sede=ev.get("sede"),
                descrizione=ev.get("descrizione"),
                posti_max=ev.get("posti_max"),
                prezzo=ev.get("prezzo"),
                conduttore=ev.get("conduttore"),
                attivo=True,
                iscrizioni_aperte=True,
                note_interne=ev.get("note_interne"),
                slot_abilitati=bool(ev.get("slot_abilitati")),
                slot_durata_minuti=ev.get("slot_durata_minuti"),
                slot_ora_inizio=ev.get("slot_ora_inizio"),
                slot_ora_fine=ev.get("slot_ora_fine"),
                slot_ora_inizio_2=ev.get("slot_ora_inizio_2"),
                slot_ora_fine_2=ev.get("slot_ora_fine_2"),
                slot_posti=ev.get("slot_posti"),
            )
            st.success(f"Evento duplicato (ID {nuovo['id']}) — lo trovi nella lista eventi.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore duplicazione: {e}")

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
                    if ev.get("wp_post_id"):
                        from .wp_publish import rimuovi_evento
                        rimuovi_evento(conn, ev)
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
            tipo = st.selectbox(
                "Tipo ✱", options=list(TIPI_VALIDI),
                help="«screening» → il form pubblico chiede i dati del bambino/a "
                     "e della scuola. Gli altri tipi chiedono i dati del "
                     "partecipante adulto.")
        with col2:
            posti_max = st.number_input(
                "Posti max (0 = illimitati — lascia 0 se usi le fasce orarie)",
                min_value=0, max_value=999, value=0,
            )

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

        st.divider()
        st.markdown(
            "**🕐 Fasce orarie** (opzionale) — es. screening scolastico: 4 appuntamenti "
            "all'ora, ogni 15 minuti. Chi si iscrive scieglie l'orario libero e "
            "l'appuntamento viene creato anche sul Google Calendar dello studio."
        )
        slot_abilitati = st.checkbox("Abilita fasce orarie per questo evento", value=False)
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            slot_ora_inizio = st.time_input("Fascia 1 — Dalle", value=time(9, 0))
        with cs2:
            slot_ora_fine = st.time_input("Fascia 1 — Alle", value=time(13, 0))
        with cs3:
            slot_durata_minuti = st.number_input("Durata slot (min)", min_value=5, max_value=120, value=15)
        with cs4:
            slot_posti = st.number_input("Posti per slot", min_value=1, max_value=20, value=1)
        st.caption("Seconda fascia (opzionale) — es. pomeriggio 16:00-18:00. Lascia le 00:00 se non serve.")
        cs5, cs6 = st.columns(2)
        with cs5:
            slot_ora_inizio_2 = st.time_input("Fascia 2 — Dalle", value=time(0, 0))
        with cs6:
            slot_ora_fine_2 = st.time_input("Fascia 2 — Alle", value=time(0, 0))

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
                    slot_abilitati=slot_abilitati,
                    slot_durata_minuti=slot_durata_minuti,
                    slot_ora_inizio=slot_ora_inizio,
                    slot_ora_fine=slot_ora_fine,
                    slot_ora_inizio_2=slot_ora_inizio_2 if slot_ora_inizio_2 != time(0, 0) else None,
                    slot_ora_fine_2=slot_ora_fine_2 if slot_ora_fine_2 != time(0, 0) else None,
                    slot_posti=slot_posti,
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
