# -*- coding: utf-8 -*-
"""Screening 0-4 anni — osservativo e parent-report.

Distinto dallo Screening breve e dal Protocollo completo: sotto i 4 anni non
si somministrano prove prestazionali (lettura, scrittura, calcolo), quindi il
dato viene da racconto dei genitori + osservazione diretta guidata + griglia
motoria secondo i marker di Teitelbaum.

Esito: semaforo verde/giallo/rosso — una decisione su cosa fare adesso, non un
punteggio di prestazione: a questa età il valore prognostico del singolo item è
debole e il rischio di falsi positivi alto.

Riferimento per la sezione motoria: Teitelbaum P. et al., "Movement analysis in
infancy may be useful for early diagnosis of autism", PNAS 1998; e "Eshkol-
Wachman movement notation in diagnosis", PNAS 2004. Ricerca pubblicata, usata
qui come griglia osservativa qualitativa — non come test diagnostico.
"""
from __future__ import annotations
import json
import streamlit as st
import pandas as pd


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS screening_04 (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_screening DATE,
                operatore TEXT,
                esito TEXT,
                dati JSONB,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva(conn, paz_id, operatore, esito, dati) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO screening_04 (paziente_id, data_screening, operatore, esito, dati)
            VALUES (%s, CURRENT_DATE, %s, %s, %s)
        """, (paz_id, operatore, esito, json.dumps(dati, default=str)))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def _storico(conn, paz_id, limit=10):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT data_screening, operatore, esito FROM screening_04
            WHERE paziente_id=%s ORDER BY creato_il DESC LIMIT %s
        """, (paz_id, limit))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


def _tab(righe, fisse, key):
    df = pd.DataFrame(righe)
    cfg = {c: st.column_config.TextColumn(disabled=True) for c in fisse}
    for c in df.columns:
        if c not in fisse and c.startswith("0-1-2"):
            cfg[c] = st.column_config.SelectboxColumn(options=["", "0", "1", "2"])
        elif c not in fisse and c in ("Sì/No", "Presente"):
            cfg[c] = st.column_config.SelectboxColumn(options=["", "Sì", "No", "Dubbio"])
    return st.data_editor(df, key=key, hide_index=True, use_container_width=True, column_config=cfg)


def _dati_paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT cognome, nome, data_nascita FROM pazienti WHERE id=%s", (paz_id,))
        r = cur.fetchone()
        if not r:
            return {}
        return dict(r) if hasattr(r, "get") else {"cognome": r[0], "nome": r[1], "data_nascita": r[2]}
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return {}


def _email_consenso(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT tutore_email FROM consensi_privacy WHERE paziente_id=%s
                       ORDER BY data_ora DESC NULLS LAST, id DESC LIMIT 1""", (paz_id,))
        r = cur.fetchone()
        email = (r["tutore_email"] if hasattr(r, "get") else r[0]) if r else None
        return (email or "").strip() or None
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return None


def _relazione_semplice(nome, esito, dati) -> str:
    righe = [f"Screening 0-4 anni — {nome}", f"Esito: {esito}", ""]
    for titolo, contenuto in dati.items():
        if not contenuto:
            continue
        righe.append(f"## {titolo.replace('_',' ').capitalize()}")
        if isinstance(contenuto, dict):
            for k, v in contenuto.items():
                if v not in (None, "", [], {}):
                    righe.append(f"- {k.replace('_',' ').capitalize()}: {v}")
        else:
            righe.append(f"- {contenuto}")
        righe.append("")
    righe.append("Questo screening è una prima osservazione orientativa, non una diagnosi. "
                 "A questa età il quadro evolve rapidamente: il senso della rilevazione è decidere "
                 "se monitorare o approfondire, non etichettare.")
    return "\n".join(righe)


def _genera_relazione(conn, paz_id, esito, dati):
    paz = _dati_paziente(conn, paz_id)
    nome = f"{paz.get('cognome','')} {paz.get('nome','')}".strip() or "il/la bambino/a"

    testo = None
    try:
        from .ai_estrazione import genera_testo, ai_disponibile
        if ai_disponibile():
            prompt = (
                f"Scrivi una relazione per i genitori a partire da uno screening osservativo 0-4 anni "
                f"su {nome}.\n\nESITO COMPLESSIVO: {esito}\n\nDATI RACCOLTI:\n"
                f"{json.dumps(dati, ensure_ascii=False, indent=2, default=str)}\n\n"
                f"Scrivi in italiano semplice, mai allarmistico. Spiega cosa è stato osservato, cosa è "
                f"nella norma per l'età e cosa merita attenzione. A questa età NON si formulano diagnosi: "
                f"chiudi con indicazioni pratiche concrete e, se l'esito è giallo o rosso, con quali "
                f"approfondimenti considerare e in quali tempi. Massimo 400 parole."
            )
            sistema = ("Sei un assistente clinico dello Studio The Organism (Metodo PNEV). Scrivi per "
                       "genitori di bambini molto piccoli: chiaro, concreto, mai allarmistico, sempre "
                       "orientato al passo successivo.")
            with st.spinner("Genero la relazione…"):
                bozza = genera_testo(prompt, sistema)
            if not bozza.startswith("⚠️"):
                testo = bozza
    except Exception:
        pass

    if testo is None:
        st.info("AI non disponibile: uso una relazione semplice basata sui dati inseriti.")
        testo = _relazione_semplice(nome, esito, dati)

    st.text_area("Bozza relazione (modificabile prima dell'invio)", value=testo,
                 height=320, key="s04_bozza")
    finale = st.session_state.get("s04_bozza", testo)

    dest = _email_consenso(conn, paz_id)
    if not dest:
        st.warning("Nessuna email nel consenso privacy: copia il testo e invialo manualmente.")
        return
    if st.button(f"📤 Invia ora a {dest}", key="s04_invia", type="primary"):
        try:
            from .email_otp import invia_email
            invia_email(dest, f"Screening 0-4 anni — {nome}", finale + "\n\n— Studio The Organism")
            try:
                invia_email("dr.ferraioligiuseppe@gmail.com",
                            f"[Screening 0-4] {nome} — esito {esito}", finale)
            except Exception:
                pass
            st.success(f"Relazione inviata a {dest}.")
        except Exception as e:
            st.error(f"Errore invio: {e}")


def render_screening_04(conn=None, paz_id=None, paziente=None) -> None:
    st.header("🧸 Screening 0-4 anni")
    st.caption("Osservativo e parent-report: niente prove prestazionali. L'esito è una decisione "
               "(monitorare o approfondire), non un punteggio.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    c1, c2 = st.columns(2)
    operatore = c1.text_input("Operatore", key="s04_operatore")
    eta_mesi = c2.text_input("Età in mesi", key="s04_eta_mesi")
    st.caption("💡 Chiedi ai genitori di portare i video che hanno già sul telefono (primi mesi, "
               "rotolamento, gattonamento, primi passi): la griglia motoria si compila anche così, "
               "senza richiedere collaborazione al bambino.")

    t1, t2, t3, t4, t5 = st.tabs([
        "👪 Racconto dei genitori", "👀 Osservazione diretta",
        "🤸 Motorio (Teitelbaum)", "👁️👂 Visivo e uditivo", "🚦 Esito"])

    with t1:
        st.markdown("**Tappe comunicative**")
        tappe_com = _tab([
            {"Tappa": "Lallazione variata (ba-da-ga)", "Età attesa": "7-10 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Risponde al proprio nome", "Età attesa": "9-12 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Pointing per chiedere (richiestivo)", "Età attesa": "10-12 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Pointing per mostrare (dichiarativo)", "Età attesa": "12-15 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Prime parole con significato", "Età attesa": "12-15 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Circa 50 vocaboli prodotti", "Età attesa": "18-24 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Combina due parole", "Età attesa": "24 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Frasi di 3+ parole", "Età attesa": "30-36 mesi", "Presente": "", "Età riferita": ""},
            {"Tappa": "Racconta un fatto accaduto", "Età attesa": "36-48 mesi", "Presente": "", "Età riferita": ""},
        ], ["Tappa", "Età attesa"], "s04_tappe_com")

        st.markdown("**Segnali di attenzione (red flag) — riferiti dai genitori**")
        st.caption("Il singolo item non significa nulla: conta il cumulo e la persistenza.")
        red_flag = st.multiselect("Segnalazioni", [
            "Non risponde al nome (dai 12 mesi)",
            "Non usa il pointing dichiarativo (dai 15 mesi)",
            "Non cerca lo sguardo dell'adulto per condividere",
            "Non porta oggetti per mostrarli",
            "Gioco ripetitivo o solo su una parte dell'oggetto",
            "Assenza di gioco simbolico (dai 24 mesi)",
            "Perdita di competenze già acquisite (regressione)",
            "Non imita gesti o azioni",
            "Preferisce stare solo, poca reciprocità",
            "Stereotipie motorie (flapping, dondolio, camminata sulle punte)",
            "Ipo/iper-reattività sensoriale marcata (suoni, tessuti, luci)",
        ], key="s04_red_flag")

        st.markdown("**Alimentazione, sonno, regolazione**")
        c3, c4 = st.columns(2)
        allattamento = c3.text_input("Allattamento (seno/biberon, durata, difficoltà di suzione)", key="s04_allatt")
        svezzamento = c4.text_input("Svezzamento e passaggio ai solidi", key="s04_svezz")
        alimentazione = st.multiselect("Alimentazione", [
            "Selettività marcata (pochi cibi accettati)", "Rifiuta consistenze grumose/solide",
            "Non mastica, deglutisce interi", "Reflusso/coliche importanti in anamnesi",
            "Alimentazione nella norma"], key="s04_alim")
        sonno = st.multiselect("Sonno", [
            "Fatica ad addormentarsi", "Risvegli frequenti", "Dorme a bocca aperta",
            "Russa", "Sonno nella norma"], key="s04_sonno")
        regolazione = st.text_area("Regolazione emotiva (pianto inconsolabile, difficoltà di consolazione, "
                                    "crisi di rabbia)", key="s04_regol", height=68)

        st.markdown("**Anamnesi rilevante a questa età**")
        c5, c6 = st.columns(2)
        parto_04 = c5.selectbox("Parto", ["", "Eutocico", "Distocico", "Cesareo programmato",
                                          "Cesareo d'urgenza"], key="s04_parto")
        settimane = c6.text_input("Settimane di gestazione / peso alla nascita", key="s04_settimane")
        otiti_04 = st.text_input("Otiti ricorrenti, tubi timpanici, screening uditivo neonatale",
                                  key="s04_otiti")
        st.caption("Le otiti ricorrenti nei primi due anni pesano molto sullo sviluppo del linguaggio: "
                   "vanno sempre indagate.")
        familiarita_04 = st.text_input("Familiarità (linguaggio, DSA, ASD, ritardi)", key="s04_familiarita")

    with t2:
        st.markdown("**Osservazione diretta guidata**")
        st.caption("0 = assente · 1 = presente ma incostante/immaturo · 2 = adeguato per l'età. "
                   "Bastano 5-10 minuti di gioco libero con un paio di giochi semplici.")
        osservazione = _tab([
            {"Area": "Contatto oculare spontaneo", "0-1-2": "", "Note": ""},
            {"Area": "Attenzione condivisa (guarda te → guarda l'oggetto → torna a te)", "0-1-2": "", "Note": ""},
            {"Area": "Risposta al nome in situazione", "0-1-2": "", "Note": ""},
            {"Area": "Imitazione motoria (batti le mani, tocca il naso)", "0-1-2": "", "Note": ""},
            {"Area": "Imitazione verbale (suoni, parole)", "0-1-2": "", "Note": ""},
            {"Area": "Gioco funzionale (usa l'oggetto per il suo scopo)", "0-1-2": "", "Note": ""},
            {"Area": "Gioco simbolico (fa finta di)", "0-1-2": "", "Note": ""},
            {"Area": "Comprensione ordine a 1 passaggio", "0-1-2": "", "Note": ""},
            {"Area": "Comprensione ordine a 2 passaggi", "0-1-2": "", "Note": ""},
            {"Area": "Produzione verbale in situazione", "0-1-2": "", "Note": ""},
            {"Area": "Reciprocità nel gioco a turni", "0-1-2": "", "Note": ""},
            {"Area": "Tolleranza al cambio di attività", "0-1-2": "", "Note": ""},
        ], ["Area"], "s04_osservazione")
        note_osservazione = st.text_area("Note sull'osservazione (qualità del contatto, strategie che "
                                          "hanno funzionato, cosa ha destabilizzato)",
                                          key="s04_note_oss", height=68)

    with t3:
        st.markdown("**Griglia motoria — marker di Teitelbaum**")
        st.caption("Teitelbaum et al., PNAS 1998 e 2004: analisi retrospettiva di video familiari. "
                   "Griglia osservativa qualitativa, NON un test diagnostico: conta il cumulo di "
                   "asimmetrie e atipie, non il singolo item.")

        st.markdown("_Riflessi e reazioni di raddrizzamento_")
        riflessi_t = _tab([
            {"Marker": "Rotolamento sempre dallo stesso lato (asimmetria)", "Presente": "", "Note": ""},
            {"Marker": "Reazione di raddrizzamento del capo assente o asimmetrica", "Presente": "", "Note": ""},
            {"Marker": "ATNR persistente oltre i 6 mesi", "Presente": "", "Note": ""},
            {"Marker": "Reazione di paracadute asimmetrica o assente", "Presente": "", "Note": ""},
            {"Marker": "Moro persistente oltre i 4-6 mesi", "Presente": "", "Note": ""},
        ], ["Marker"], "s04_riflessi_t")

        st.markdown("_Qualità delle tappe motorie (non solo il timing)_")
        tappe_mot = _tab([
            {"Tappa": "Rotolamento", "Età riferita": "", "Qualità": "", "Atipia osservata": ""},
            {"Tappa": "Seduta autonoma", "Età riferita": "", "Qualità": "", "Atipia osservata": ""},
            {"Tappa": "Gattonamento", "Età riferita": "", "Qualità": "", "Atipia osservata": ""},
            {"Tappa": "Stazione eretta", "Età riferita": "", "Qualità": "", "Atipia osservata": ""},
            {"Tappa": "Primi passi", "Età riferita": "", "Qualità": "", "Atipia osservata": ""},
        ], ["Tappa"], "s04_tappe_mot")
        st.caption("Atipie da cercare: rotolamento «a blocco» senza dissociazione dei cingoli · seduta "
                   "con base allargata e appoggio posteriore prolungato · gattonamento asimmetrico o "
                   "saltato · avvio del cammino su base allargata persistente · assenza di rotazione "
                   "del tronco · braccia in guardia alta oltre i tempi attesi.")

        st.markdown("_Segni posturali caratteristici_")
        segni_post = _tab([
            {"Segno": "Inclinazione asimmetrica del capo in stazione eretta (tilted posture)", "Presente": "", "Note": ""},
            {"Segno": "Cammino sulle punte persistente", "Presente": "", "Note": ""},
            {"Segno": "Asimmetria nell'uso degli arti superiori", "Presente": "", "Note": ""},
            {"Segno": "Base di appoggio allargata oltre i tempi attesi", "Presente": "", "Note": ""},
            {"Segno": "Assenza di dissociazione cingoli nel cammino", "Presente": "", "Note": ""},
            {"Segno": "Equilibrio monopodalico assente (dai 3 anni)", "Presente": "", "Note": ""},
            {"Segno": "Salto a piedi uniti assente (dai 2;6)", "Presente": "", "Note": ""},
        ], ["Segno"], "s04_segni_post")

        st.markdown("_Prassie orali_")
        prassie_04 = _tab([
            {"Prassia": "Suzione efficace (in anamnesi)", "0-1-2": "", "Note": ""},
            {"Prassia": "Masticazione", "0-1-2": "", "Note": ""},
            {"Prassia": "Soffio (spegnere una candela)", "0-1-2": "", "Note": ""},
            {"Prassia": "Postura linguale a riposo", "0-1-2": "", "Note": ""},
            {"Prassia": "Competenza labiale (bocca chiusa a riposo)", "0-1-2": "", "Note": ""},
        ], ["Prassia"], "s04_prassie")

        video_genitori = st.text_area("Video familiari visionati (quali, quale età, cosa emerge)",
                                       key="s04_video", height=68)

    with t4:
        st.markdown("**Visivo funzionale** (nessuno strumento, solo funzione)")
        visivo_04 = _tab([
            {"Prova": "Inseguimento oculare orizzontale", "0-1-2": "", "Note": ""},
            {"Prova": "Inseguimento verticale", "0-1-2": "", "Note": ""},
            {"Prova": "Convergenza su oggetto avvicinato", "0-1-2": "", "Note": ""},
            {"Prova": "Fissazione stabile su volto", "0-1-2": "", "Note": ""},
            {"Prova": "Reazione di difesa alla minaccia visiva", "0-1-2": "", "Note": ""},
            {"Prova": "Simmetria dei riflessi corneali (occhio allineato)", "0-1-2": "", "Note": ""},
        ], ["Prova"], "s04_visivo")
        segnali_visivi = st.multiselect("Segnali riferiti o osservati", [
            "Strabismo intermittente", "Strabismo costante", "Chiude un occhio alla luce",
            "Avvicina molto gli oggetti", "Nistagmo", "Inclina il capo per guardare",
            "Nessun segnale"], key="s04_segn_vis")

        st.markdown("**Uditivo funzionale**")
        uditivo_04 = _tab([
            {"Prova": "Reazione a suono laterale (non visibile)", "0-1-2": "", "Note": ""},
            {"Prova": "Localizzazione della sorgente sonora", "0-1-2": "", "Note": ""},
            {"Prova": "Risposta al nome chiamato da dietro", "0-1-2": "", "Note": ""},
            {"Prova": "Reazione a voce sussurrata", "0-1-2": "", "Note": ""},
            {"Prova": "Discriminazione di suoni familiari", "0-1-2": "", "Note": ""},
        ], ["Prova"], "s04_uditivo")
        segnali_uditivi = st.multiselect("Segnali riferiti o osservati", [
            "Alza il volume della TV", "Non risponde se chiamato da un'altra stanza",
            "Chiede di ripetere spesso", "Ipersensibile ai suoni forti",
            "Storia di otiti ricorrenti", "Nessun segnale"], key="s04_segn_ud")

    with t5:
        st.markdown("**Esito dello screening**")
        st.caption("A questa età l'esito non è una prestazione: è la decisione su cosa fare adesso.")
        esito = st.radio("Semaforo", [
            "🟢 Verde — sviluppo nei tempi attesi, ricontrollo a 6 mesi",
            "🟡 Giallo — monitoraggio ravvicinato a 3 mesi + indicazioni ai genitori",
            "🔴 Rosso — invio per approfondimento specialistico",
        ], key="s04_esito")
        aree_attenzione = st.multiselect("Aree che meritano attenzione", [
            "Comunicazione e linguaggio", "Interazione sociale e reciprocità",
            "Motorio e posturale", "Prassie orali e alimentazione",
            "Visivo funzionale", "Uditivo funzionale", "Regolazione e sonno",
            "Riflessi primitivi residui"], key="s04_aree")
        invii = st.multiselect("Invii/approfondimenti proposti", [
            "Neuropsichiatria infantile (NPI)", "Logopedia", "Audiologia / esame audiometrico",
            "Oculistica pediatrica", "Osteopatia", "Terapia miofunzionale",
            "Fisioterapia / psicomotricità", "Percorso PNEV — riflessi primitivi",
            "Percorso PNEV — stimolazione uditiva (MAPS)",
            "Nessun invio, solo monitoraggio"], key="s04_invii")
        indicazioni_genitori = st.text_area("Indicazioni pratiche per i genitori (cosa fare a casa da subito)",
                                             key="s04_indicazioni", height=90)
        note_esito = st.text_area("Note per l'équipe", key="s04_note_esito", height=68)

    dati = {
        "anagrafica_screening": {"operatore": operatore, "eta_mesi": eta_mesi},
        "racconto_genitori": {
            "tappe_comunicative": tappe_com.to_dict("records"), "red_flag": red_flag,
            "allattamento": allattamento, "svezzamento": svezzamento,
            "alimentazione": alimentazione, "sonno": sonno, "regolazione": regolazione,
            "parto": parto_04, "settimane_peso": settimane, "otiti": otiti_04,
            "familiarita": familiarita_04,
        },
        "osservazione_diretta": {
            "griglia": osservazione.to_dict("records"), "note": note_osservazione,
        },
        "motorio_teitelbaum": {
            "riflessi": riflessi_t.to_dict("records"),
            "tappe_motorie": tappe_mot.to_dict("records"),
            "segni_posturali": segni_post.to_dict("records"),
            "prassie_orali": prassie_04.to_dict("records"),
            "video_familiari": video_genitori,
        },
        "visivo_uditivo": {
            "visivo": visivo_04.to_dict("records"), "segnali_visivi": segnali_visivi,
            "uditivo": uditivo_04.to_dict("records"), "segnali_uditivi": segnali_uditivi,
        },
        "esito": {
            "semaforo": esito, "aree_attenzione": aree_attenzione, "invii": invii,
            "indicazioni_genitori": indicazioni_genitori, "note_equipe": note_esito,
        },
    }

    if st.button("💾 Salva screening 0-4", type="primary", key="s04_salva"):
        if _salva(conn, paz_id, operatore, esito, dati):
            st.success("Screening salvato.")

    st.markdown("---")
    st.markdown("#### 📄 Relazione per i genitori")
    st.caption("Disponibile subito, anche senza salvare: usa i dati inseriti qui sopra. "
               "Se l'AI non è disponibile genera comunque una relazione semplice.")
    if st.button("✉️ Genera relazione e invia ai genitori", key="s04_genera"):
        _genera_relazione(conn, paz_id, esito, dati)

    st.markdown("---")
    st.markdown("#### Storico")
    righe = _storico(conn, paz_id)
    if not righe:
        st.caption("Nessuno screening 0-4 registrato finora.")
    else:
        for data_s, op, es in righe:
            st.caption(f"📅 {data_s} · {op or '—'} · {es or '—'}")
