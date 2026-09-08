# -*- coding: utf-8 -*-
"""
modules/whodas/ui_whodas.py
Interfaccia Streamlit — WHODAS 2.0, versione a 36 item somministrata da un intervistatore.

PUNTI DI INTEGRAZIONE (verifica che corrispondano agli altri moduli, es. audiometria):
  1. get_conn / studio_id / paziente_id: qui arrivano come argomenti di render().
  2. carta_intestata: path dell'immagine di intestazione, caricata al login.
  3. Nomi tabella pazienti: il modulo NON interroga la tabella pazienti,
     riceve già il dict `paziente`.
"""

from datetime import date

import streamlit as st

from .db_whodas import (
    DOMINI, SCALA, VERSIONE, ATTRIBUZIONE, DOMANDE_ACCESSORIE,
    items_del_dominio, calcola_punteggi, crea_schema,
    salva_somministrazione, carica_somministrazione, lista_somministrazioni,
    elimina_somministrazione, serie_storica,
)
from .pdf_whodas import genera_pdf

CHIAVE = "whodas"

TESTO_CARTONCINO_1 = """
**Problemi di salute:** malattie o altri disturbi · traumi · problemi mentali o emotivi ·
problemi con alcol · problemi con droghe

**Avere difficoltà nello svolgere un'attività significa:** maggiore sforzo · malessere o
dolore · lentezza · cambiamento nel modo di svolgere l'attività

**Pensi solo agli ultimi 30 giorni.**
"""

PREAMBOLO = """
Questa intervista riguarda le difficoltà che le persone hanno in relazione ai propri
problemi di salute.

Per problemi di salute si intendono malattie o altri disturbi che possono essere di breve
o lunga durata, traumi, problemi mentali o emotivi e problemi con alcol o droghe.

Nel rispondere, vorrei che ripensasse agli ultimi 30 giorni. Vorrei anche che rispondesse
alle domande pensando a quanta difficoltà ha avuto, in media, negli ultimi 30 giorni, a
fare l'attività come la fa di solito.
"""


def _k(*parti):
    return "_".join([CHIAVE] + [str(p) for p in parti])


def _radio_item(codice, testo, valore_iniziale=None):
    """Radio orizzontale 1-5 per un item."""
    opzioni = list(SCALA.keys())
    indice = opzioni.index(valore_iniziale) if valore_iniziale in opzioni else None
    return st.radio(
        f"**{codice}** — {testo}",
        options=opzioni,
        index=indice,
        format_func=lambda v: f"{v} · {SCALA[v]}",
        horizontal=True,
        key=_k("item", codice),
    )


def render_whodas(conn, paziente_id):
    """Wrapper compatibile col router: prende (conn, paz_id) come gli altri moduli,
    recupera anagrafica e studio_id, e chiama render()."""
    import streamlit as st
    cur = conn.cursor()
    try:
        studio_id = None
        try:
            cur.execute("SELECT current_setting('app.current_studio', true)::bigint")
            row = cur.fetchone()
            studio_id = row[0] if row else None
        except Exception:
            pass
        cur.execute("SELECT id, Nome, Cognome, Data_Nascita FROM Pazienti WHERE id = %s", (paziente_id,))
        row = cur.fetchone()
        if not row:
            st.error("Paziente non trovato.")
            return
        pid, nome, cognome, data_nascita = row
        paziente = {
            "id": pid,
            "nome_completo": f"{nome or ''} {cognome or ''}".strip(),
            "data_nascita": data_nascita,
        }
    finally:
        try: cur.close()
        except Exception: pass
    render(conn, studio_id, paziente)


def render(conn, studio_id, paziente, carta_intestata=None):
    """
    conn:            connessione PostgreSQL già aperta e con app.studio_id impostato
    studio_id:       id dello studio (tenant)
    paziente:        dict {"id", "nome_completo", "data_nascita", ...}
    carta_intestata: path immagine intestazione per il PDF
    """
    crea_schema(conn)
    paziente_id = paziente["id"]

    st.subheader("WHODAS 2.0 — Profilo di funzionamento")
    st.caption(
        "Versione a 36 item, somministrata da un intervistatore. "
        "Le domande vanno lette ad alta voce; le istruzioni fra parentesi no. "
        "Durata indicativa 15-20 minuti."
    )

    tab_nuova, tab_storico = st.tabs(["Somministrazione", "Storico e andamento"])

    # ===================================================================== #
    # TAB 1 — Somministrazione
    # ===================================================================== #
    with tab_nuova:
        with st.expander("Cartoncino promemoria #1 — da mostrare al paziente", expanded=False):
            st.markdown(TESTO_CARTONCINO_1)
            st.markdown("**Cartoncino promemoria #2 — scala di risposta**")
            st.markdown(" · ".join(f"**{v}** {t}" for v, t in SCALA.items()))

        with st.expander("Preambolo da leggere ad alta voce", expanded=False):
            st.markdown(PREAMBOLO)

        st.markdown("##### Sezione 1-2 — Dati dell'intervista e informazioni generali")

        c1, c2, c3 = st.columns(3)
        with c1:
            data_somm = st.date_input("Data della somministrazione", value=date.today(),
                                      format="DD/MM/YYYY", key=_k("data"))
            numero_intervista = st.number_input("N. intervista", min_value=1, value=1,
                                                step=1, key=_k("n_intervista"))
        with c2:
            id_intervistatore = st.text_input("Identificativo intervistatore",
                                              key=_k("id_intervistatore"))
            situazione_vita = st.selectbox(
                "F5 — Situazione di vita",
                options=[1, 2, 3],
                format_func=lambda v: {
                    1: "Indipendente nella comunità",
                    2: "Assistito a domicilio",
                    3: "Ricoverato / struttura residenziale",
                }[v],
                key=_k("situazione"),
            )
        with c3:
            sesso = st.selectbox("A1 — Sesso", options=[1, 2],
                                 format_func=lambda v: "Femmina" if v == 1 else "Maschio",
                                 key=_k("sesso"))
            eta = st.number_input("A2 — Età", min_value=0, max_value=120, value=40,
                                  step=1, key=_k("eta"))

        c4, c5, c6 = st.columns(3)
        with c4:
            anni_scuola = st.number_input("A3 — Anni di scuola frequentati", min_value=0,
                                          max_value=30, value=13, step=1, key=_k("scuola"))
        with c5:
            stato_civile = st.selectbox(
                "A4 — Stato civile",
                options=[1, 2, 3, 4, 5, 6],
                format_func=lambda v: {
                    1: "Nubile/Celibe", 2: "Attualmente sposato/a", 3: "Separato/a",
                    4: "Divorziato/a", 5: "Vedovo/a", 6: "Convivente",
                }[v],
                key=_k("stato_civile"),
            )
        with c6:
            attivita = st.selectbox(
                "A5 — Principale attività lavorativa",
                options=list(range(1, 10)),
                format_func=lambda v: {
                    1: "Lavoro retribuito", 2: "Lavoro autonomo",
                    3: "Lavoro non retribuito", 4: "Studente/ssa", 5: "Casalingo/a",
                    6: "In pensione", 7: "Non occupato/a (salute)",
                    8: "Non occupato/a (altri motivi)", 9: "Altro",
                }[v],
                key=_k("attivita"),
            )
        attivita_altro = ""
        if attivita == 9:
            attivita_altro = st.text_input("A5 — Specificare", key=_k("attivita_altro"))

        # Regola del manuale: gli item 5(2) si somministrano solo a chi lavora o studia
        lavora_default = attivita in (1, 2, 3, 4)
        lavora_studia = st.checkbox(
            "Il paziente lavora (retribuito, autonomo o non retribuito) oppure "
            "frequenta scuola/università → somministrare gli item D5.5-D5.10",
            value=lavora_default,
            key=_k("lavora"),
        )
        if not lavora_studia:
            st.info(
                "Item lavorativi/scolastici esclusi: il punteggio totale sarà calcolato "
                "sui 32 item, come previsto dal manuale."
            )

        st.divider()
        st.markdown("##### Sezione 4 — Domini")

        risposte = {}
        for dominio, meta in DOMINI.items():
            if dominio == "5(2)" and not lavora_studia:
                continue
            with st.expander(f"Dominio {dominio} — {meta['titolo']}", expanded=(dominio == "1")):
                st.caption(meta["introduzione"])
                st.markdown(f"*{meta['prompt']}*")
                for codice, testo in items_del_dominio(dominio):
                    risposte[codice] = _radio_item(codice, testo)
                    st.markdown("")

        # ---- Domande accessorie condizionate ---------------------------- #
        st.markdown("##### Domande accessorie")

        d5_01 = None
        if any(risposte.get(c) not in (None, 1) for c in ["D5.2", "D5.3", "D5.4"]):
            d5_01 = st.number_input(
                f"D5.01 — {DOMANDE_ACCESSORIE['D5.01']}",
                min_value=0, max_value=30, value=0, step=1, key=_k("d5_01"),
            )

        d5_9 = d5_10 = d5_02 = None
        if lavora_studia:
            cc1, cc2 = st.columns(2)
            with cc1:
                d5_9 = st.radio(f"D5.9 — {DOMANDE_ACCESSORIE['D5.9']}",
                                options=[1, 2],
                                format_func=lambda v: "No" if v == 1 else "Sì",
                                horizontal=True, key=_k("d5_9"))
            with cc2:
                d5_10 = st.radio(f"D5.10 — {DOMANDE_ACCESSORIE['D5.10']}",
                                 options=[1, 2],
                                 format_func=lambda v: "No" if v == 1 else "Sì",
                                 horizontal=True, key=_k("d5_10"))
            attivato = (
                any(risposte.get(c) not in (None, 1) for c in ["D5.5", "D5.6", "D5.7", "D5.8"])
                or d5_9 == 2 or d5_10 == 2
            )
            if attivato:
                d5_02 = st.number_input(
                    f"D5.02 — {DOMANDE_ACCESSORIE['D5.02']}",
                    min_value=0, max_value=30, value=0, step=1, key=_k("d5_02"),
                )

        h1, h2, h3 = st.columns(3)
        with h1:
            h1_v = st.number_input(f"H1 — {DOMANDE_ACCESSORIE['H1']}", min_value=0,
                                   max_value=30, value=0, step=1, key=_k("h1"))
        with h2:
            h2_v = st.number_input(f"H2 — {DOMANDE_ACCESSORIE['H2']}", min_value=0,
                                   max_value=30, value=0, step=1, key=_k("h2"))
        with h3:
            h3_v = st.number_input(f"H3 — {DOMANDE_ACCESSORIE['H3']}", min_value=0,
                                   max_value=30, value=0, step=1, key=_k("h3"))

        note = st.text_area("Note del clinico (non entrano nel punteggio)", key=_k("note"))

        # ---- Anteprima punteggi ------------------------------------------ #
        punteggi = calcola_punteggi(risposte, lavora_studia)
        mancanti = punteggi["item_mancanti"]

        st.divider()
        if mancanti:
            st.warning(f"Item ancora da compilare ({len(mancanti)}): " + ", ".join(mancanti))
        else:
            tot = punteggi["totale"]
            st.success("Questionario completo.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Punteggio semplice", f"{tot['semplice_grezzo']}",
                      help=f"Intervallo {tot['semplice_min']}–{tot['semplice_max']}")
            m2.metric("Punteggio IRT", f"{tot['irt']:.1f} / 100")
            m3.metric("Percentile popolazione", f"{tot['percentile']:.1f}°")

            righe = []
            for dominio, meta in DOMINI.items():
                p = punteggi["domini"].get(dominio)
                if p is None:
                    continue
                righe.append({
                    "Dominio": f"{dominio} — {meta['titolo']}",
                    "Somma grezza": p["semplice_grezzo"],
                    "Semplice 0-100": p["semplice_pct"],
                    "IRT 0-100": p["irt"],
                })
            st.dataframe(righe, use_container_width=True, hide_index=True)

        # ---- Salvataggio -------------------------------------------------- #
        if st.button("Salva somministrazione", type="primary",
                     disabled=bool(mancanti), key=_k("salva")):
            anagrafica = {
                "data_somministrazione": data_somm,
                "numero_intervista": int(numero_intervista),
                "id_intervistato": str(paziente_id),
                "id_intervistatore": id_intervistatore or None,
                "situazione_vita": situazione_vita,
                "sesso": sesso,
                "eta": int(eta),
                "anni_scuola": int(anni_scuola),
                "stato_civile": stato_civile,
                "attivita_lavorativa": attivita,
                "attivita_altro": attivita_altro or None,
                "lavora_studia": lavora_studia,
                "note": note or None,
                "completata": True,
            }
            accessorie = {
                "d5_01_giorni": d5_01,
                "d5_02_giorni": d5_02,
                "d5_9_ridotto": d5_9,
                "d5_10_guadagnato_meno": d5_10,
                "h1_giorni": int(h1_v),
                "h2_giorni": int(h2_v),
                "h3_giorni": int(h3_v),
            }
            nuovo_id = salva_somministrazione(
                conn, studio_id, paziente_id, anagrafica, risposte, accessorie
            )
            st.session_state[_k("ultima")] = nuovo_id
            st.success(f"Somministrazione salvata (id {nuovo_id}).")

        st.caption(ATTRIBUZIONE)

    # ===================================================================== #
    # TAB 2 — Storico, referto PDF, andamento
    # ===================================================================== #
    with tab_storico:
        elenco = lista_somministrazioni(conn, studio_id, paziente_id)
        if not elenco:
            st.info("Nessuna somministrazione WHODAS registrata per questo paziente.")
            return

        opzioni = {
            s["id"]: f"{s['data_somministrazione'].strftime('%d/%m/%Y')} — "
                     f"intervista n. {s['numero_intervista'] or '—'}"
                     f"{'' if s['completata'] else ' (incompleta)'}"
            for s in elenco
        }
        scelta = st.selectbox("Somministrazione", options=list(opzioni.keys()),
                              format_func=lambda i: opzioni[i], key=_k("scelta_storico"))

        testata, risposte_sal = carica_somministrazione(conn, studio_id, scelta)
        if testata is None:
            st.error("Somministrazione non trovata.")
            return

        p = calcola_punteggi(risposte_sal, testata["lavora_studia"])
        if p["totale"]:
            m1, m2, m3 = st.columns(3)
            m1.metric("Punteggio semplice", f"{p['totale']['semplice_grezzo']}")
            m2.metric("Punteggio IRT", f"{p['totale']['irt']:.1f} / 100")
            m3.metric("Percentile popolazione", f"{p['totale']['percentile']:.1f}°")

        righe = []
        for dominio, meta in DOMINI.items():
            d = p["domini"].get(dominio)
            if d is None:
                continue
            righe.append({
                "Dominio": f"{dominio} — {meta['titolo']}",
                "Somma grezza": d["semplice_grezzo"],
                "Semplice 0-100": d["semplice_pct"],
                "IRT 0-100": d["irt"],
            })
        st.dataframe(righe, use_container_width=True, hide_index=True)

        storico = serie_storica(conn, studio_id, paziente_id)

        if len(storico) > 1:
            st.markdown("##### Andamento del punteggio totale (IRT)")
            st.line_chart(
                {
                    "IRT 0-100": [
                        s["punteggi"]["totale"]["irt"] if s["punteggi"]["totale"] else None
                        for s in storico
                    ]
                },
                x_label="Somministrazioni in ordine cronologico",
                y_label="Punteggio IRT",
            )

        c1, c2 = st.columns([3, 1])
        with c1:
            dettaglio = st.checkbox("Includi il dettaglio delle risposte nel referto",
                                    value=True, key=_k("dettaglio_pdf"))
            pdf = genera_pdf(
                paziente, testata, risposte_sal,
                carta_intestata=carta_intestata,
                includi_dettaglio_item=dettaglio,
                storico=storico,
            )
            nome_file = (
                f"WHODAS_{paziente.get('nome_completo', 'paziente').replace(' ', '_')}"
                f"_{testata['data_somministrazione'].strftime('%Y%m%d')}.pdf"
            )
            st.download_button("Scarica referto PDF", data=pdf, file_name=nome_file,
                               mime="application/pdf", type="primary", key=_k("pdf"))
        with c2:
            if st.button("Elimina", key=_k("elimina")):
                st.session_state[_k("conferma_elimina")] = scelta
            if st.session_state.get(_k("conferma_elimina")) == scelta:
                st.warning("Confermi l'eliminazione definitiva?")
                if st.button("Sì, elimina", key=_k("elimina_conferma")):
                    elimina_somministrazione(conn, studio_id, scelta)
                    st.session_state.pop(_k("conferma_elimina"), None)
                    st.rerun()
