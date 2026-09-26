# -*- coding: utf-8 -*-
"""Screening rapido multi-area — per eventi/scuola (tipo "Giornata del
benessere del bambino"), separato dalla Valutazione PNEV completa.

Raccoglie in una scheda breve i test-chiave di linguaggio, apprendimento,
visuo-posturale, miofunzionale e osteopatico — pensata per una prima
rilevazione veloce, non per il percorso clinico completo del paziente.

Ogni test ha una breve spiegazione del significato e, dove ha senso, uno
stimolo mostrabile a schermo grande: apri questa pagina anche sul secondo
monitor rivolto verso il bambino, così vede quello che vediamo noi.
"""
from __future__ import annotations
import datetime
import json
import random
import streamlit as st


def _big(html: str):
    st.markdown(f"<div style='font-size:2.2rem; letter-spacing:.15em; "
                f"text-align:center; padding:14px 0; font-weight:600'>{html}</div>",
                unsafe_allow_html=True)


def _icona_svg(tipo, colore="#1D6B44", size=34):
    """Icone originali (forme geometriche semplici), non riprodotte da alcuna
    scheda commerciale — usate come stimolo per Visual Skills/Peek-A-Boo."""
    forme = {
        "cerchio": f'<circle cx="17" cy="17" r="13" fill="{colore}"/>',
        "quadrato": f'<rect x="5" y="5" width="24" height="24" rx="4" fill="{colore}"/>',
        "triangolo": f'<polygon points="17,4 30,29 4,29" fill="{colore}"/>',
        "stella": f'<polygon points="17,3 21,13 32,13 23,20 26,31 17,24 8,31 11,20 2,13 13,13" fill="{colore}"/>',
        "cuore": f'<path d="M17 29 C4 20 2 10 9 6 C13 4 17 8 17 11 C17 8 21 4 25 6 C32 10 30 20 17 29 Z" fill="{colore}"/>',
        "croce": f'<rect x="13" y="3" width="8" height="28" fill="{colore}"/><rect x="3" y="13" width="28" height="8" fill="{colore}"/>',
        "casa": f'<polygon points="17,4 30,16 24,16 24,30 10,30 10,16 4,16" fill="{colore}"/>',
        "albero": f'<rect x="14" y="20" width="6" height="10" fill="#8a5a2b"/><circle cx="17" cy="14" r="12" fill="{colore}"/>',
    }
    svg = forme.get(tipo, forme["cerchio"])
    return f'<svg width="{size}" height="{size}" viewBox="0 0 34 34">{svg}</svg>'


def _riga_test_binoculare(numero, titolo, distanza, opzioni, key_prefix):
    """Una riga di test tipo Telebinocular: mostra le icone (disegni originali)
    delle opzioni possibili e fa scegliere quella osservata — stesso principio
    clinico delle schede Keystone, senza riprodurne il layout protetto."""
    st.markdown(f"**Test {numero} — {titolo}** _{('lontano' if distanza=='L' else 'vicino')}_")
    cols = st.columns(len(opzioni) + 1)
    icone_cli = ["cerchio", "quadrato", "triangolo", "stella", "cuore", "croce", "casa", "albero"]
    for i, opz in enumerate(opzioni):
        with cols[i]:
            st.markdown(_icona_svg(icone_cli[i % len(icone_cli)]), unsafe_allow_html=True)
            st.caption(opz)
    scelta = st.radio(" ", opzioni, key=f"{key_prefix}_{numero}", horizontal=True, label_visibility="collapsed")
    return scelta


def _finestra_bambino(html_inner: str, key: str):
    """Compatibilità: usa ora il modulo condiviso finestra_bambino, così tutti
    i test del gestionale riusano la stessa finestra sul secondo monitor."""
    from .finestra_bambino import bottone_secondo_monitor
    bottone_secondo_monitor(html_inner, key)


def _significato(testo: str):
    st.caption(f"ℹ️ **Cosa significa:** {testo}")


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS screening_valutazioni (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_screening DATE,
                operatore TEXT,
                linguaggio JSONB,
                apprendimento JSONB,
                visuo_posturale JSONB,
                miofunzionale JSONB,
                osteopatico JSONB,
                note TEXT,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva(conn, paz_id, operatore, sezioni, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO screening_valutazioni
            (paziente_id, data_screening, operatore, linguaggio, apprendimento,
             visuo_posturale, miofunzionale, osteopatico, note)
            VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s)
        """, (
            paz_id, operatore,
            json.dumps(sezioni["linguaggio"]), json.dumps(sezioni["apprendimento"]),
            json.dumps(sezioni["visuo_posturale"]), json.dumps(sezioni["miofunzionale"]),
            json.dumps(sezioni["osteopatico"]), note,
        ))
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
            SELECT id, data_screening, operatore, note FROM screening_valutazioni
            WHERE paziente_id=%s ORDER BY creato_il DESC LIMIT %s
        """, (paz_id, limit))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


def _dati_paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT cognome, nome, data_nascita, email FROM pazienti WHERE id=%s""",
                    (paz_id,))
        r = cur.fetchone()
        if not r:
            return {}
        if hasattr(r, "get"):
            return dict(r)
        return {"cognome": r[0], "nome": r[1], "data_nascita": r[2], "email": r[3]}
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return {}


def _email_consenso(conn, paz_id):
    """Email del genitore/tutore dal consenso privacy più recente."""
    try:
        cur = conn.cursor()
        cur.execute("""SELECT tutore_email FROM consensi_privacy
                       WHERE paziente_id=%s ORDER BY data_ora DESC NULLS LAST, id DESC LIMIT 1""",
                    (paz_id,))
        r = cur.fetchone()
        email = (r["tutore_email"] if hasattr(r, "get") else r[0]) if r else None
        return (email or "").strip() or None
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return None


def _questionari_paziente(conn, paz_id, limit=5):
    """Ultimi questionari compilati dal paziente, se la tabella esiste."""
    try:
        cur = conn.cursor()
        cur.execute("""SELECT tipo, risposte, creato_il FROM questionari_risposte
                       WHERE paziente_id=%s ORDER BY creato_il DESC LIMIT %s""",
                    (paz_id, limit))
        return cur.fetchall() or []
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


def _relazione_template(nome_completo, sezioni, note) -> str:
    """Relazione senza AI, nello stile Studio The Organism (intestazione,
    aree valutate A-F, conclusioni, consigli) — sempre disponibile anche
    se l'AI non è configurata o non risponde."""
    righe = []
    etichette = {
        "linguaggio": "B. Abilità del linguaggio", "apprendimento": "C. Apprendimenti",
        "visuo_posturale": "A/D. Visuo-posturale", "miofunzionale": "E. Valutazione miofunzionale",
        "osteopatico": "D. Valutazione osteopatica",
    }
    aree_con_dati = []
    for chiave, titolo in etichette.items():
        dati = {k: v for k, v in (sezioni.get(chiave) or {}).items() if v not in (None, "", [], False)}
        if not dati:
            continue
        aree_con_dati.append(titolo)
        righe.append(f"## {titolo}")
        for k, v in dati.items():
            righe.append(f"- {k.replace('_',' ').capitalize()}: {v}")
        righe.append("")
    if note:
        righe.append(f"Note dell'operatore: {note}")
        righe.append("")
    righe.append(
        "Questo screening è una prima rilevazione orientativa e criteriale, non una "
        "valutazione clinica completa né una diagnosi. Per un approfondimento diagnostico "
        "(anche in équipe multidisciplinare con neuropsichiatria infantile, laddove le "
        "aree segnalate lo richiedano) consigliamo di prenotare una valutazione PNEV completa."
    )
    return "\n".join(righe)


def _genera_e_invia_relazione(conn, paz_id, sezioni, note):
    paziente = _dati_paziente(conn, paz_id)
    nome_completo = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip() or "il/la bambino/a"

    testo = None
    try:
        from .ai_estrazione import genera_testo, ai_disponibile
        if ai_disponibile():
            questionari = _questionari_paziente(conn, paz_id)
            q_riassunto = "\n".join(
                f"- {q.get('tipo') if hasattr(q,'get') else q[0]}: compilato" for q in questionari
            ) or "Nessun questionario aggiuntivo disponibile."
            prompt = (
                f"Scrivi una relazione di screening su {nome_completo}, nello stile e nel registro "
                f"di una relazione clinica dello Studio The Organism (Metodo PNEV): professionale, "
                f"organizzata per aree (linguaggio, apprendimento, visuo-posturale, miofunzionale, "
                f"osteopatico), con un linguaggio che deve poter essere condiviso anche con un'équipe "
                f"multidisciplinare (inclusa neuropsichiatria infantile) quando un'area lo richiede — "
                f"quindi preciso nei termini tecnici usati, ma sempre accompagnato da una spiegazione "
                f"in parole semplici per il genitore.\n\n"
                f"DATI RACCOLTI (per area):\n"
                f"Linguaggio: {sezioni.get('linguaggio')}\n"
                f"Apprendimento: {sezioni.get('apprendimento')}\n"
                f"Visuo-posturale: {sezioni.get('visuo_posturale')}\n"
                f"Miofunzionale: {sezioni.get('miofunzionale')}\n"
                f"Osteopatico: {sezioni.get('osteopatico')}\n"
                f"Note dell'operatore: {note or '—'}\n\n"
                f"Questionari già compilati dalla famiglia:\n{q_riassunto}\n\n"
                f"Struttura: per ciascuna area valutata segnala se i risultati sono nella norma o se "
                f"emerge un'area da approfondire (specifica se il termine tecnico usato richiede una "
                f"spiegazione a parte); chiudi con una sezione \"Si consiglia\" con 3-5 indicazioni "
                f"concrete — che possono comprendere un approfondimento specialistico specifico "
                f"(es. valutazione neuropsicologica, invio ad équipe NPI, valutazione logopedica) "
                f"quando i dati lo giustificano, oltre a consigli pratici da poter già iniziare a casa. "
                f"Non scrivere una diagnosi: è uno screening orientativo e criteriale, non una "
                f"valutazione clinica completa tarata."
            )
            sistema = ("Sei un assistente clinico dello Studio The Organism (Metodo PNEV). Scrivi "
                       "relazioni di screening con un registro professionale, utilizzabili anche per "
                       "un invio in équipe multidisciplinare (NPI, logopedia, neuropsicologia) quando "
                       "necessario, ma sempre comprensibili al genitore — mai allarmistiche, sempre "
                       "orientate a un'azione concreta successiva.")
            with st.spinner("Genero la relazione con l'AI…"):
                bozza = genera_testo(prompt, sistema)
            if not bozza.startswith("⚠️"):
                testo = bozza
    except Exception:
        pass

    if testo is None:
        st.info("AI non disponibile in questo momento: uso una relazione semplice basata sui dati inseriti.")
        testo = _relazione_template(nome_completo, sezioni, note)

    try:
        from .intestazione_relazioni import incornicia
        testo = incornicia(
            testo, "Relazione di screening",
            nome_paziente=nome_completo,
            data_nascita=(paziente.get("data_nascita").strftime("%d/%m/%Y")
                          if hasattr(paziente.get("data_nascita"), "strftime")
                          else str(paziente.get("data_nascita") or "")),
            includi_npi_interna=True,
        )
    except Exception:
        pass

    st.text_area("Bozza relazione (modificabile prima dell'invio)", value=testo,
                 height=320, key="scr_bozza_relazione")
    testo_finale = st.session_state.get("scr_bozza_relazione", testo)

    email_dest = _email_consenso(conn, paz_id)
    if not email_dest:
        st.warning("Nessuna email trovata nel consenso privacy del paziente: "
                   "correggi il testo sopra e invia manualmente.")
        return

    if st.button(f"📤 Invia ora a {email_dest}", key="scr_invia_conferma", type="primary"):
        try:
            from .email_otp import invia_email
            invia_email(email_dest,
                        f"Risultati screening — {nome_completo}",
                        testo_finale)
            for staff in ("apstheorganism@gmail.com", "dr.ferraioligiuseppe@gmail.com"):
                try:
                    invia_email(staff, f"[Screening] Relazione inviata — {nome_completo}", testo_finale)
                except Exception:
                    pass
            st.success(f"Relazione inviata a {email_dest}.")
        except Exception as e:
            st.error(f"Errore invio: {e}")


# Testi di lettura ad alta voce — brani ORIGINALI (non IReST: quello è materiale
# editoriale protetto, va usato con le tavole fisiche originali dello studio).
# Qui solo testi nostri, di lunghezza omogenea, per una misura ripetibile
# intra-soggetto (non norme di popolazione).
_TESTI_IREST = [
    {"nome": "Il mercato", "testo": "Ogni giovedì mattina la piazza del paese si riempiva di bancarelle colorate, disposte in file ordinate lungo tutto il perimetro. I venditori arrivavano già alle sei, scaricando cassette di frutta, formaggi e stoffe dai loro furgoni. Verso le nove la piazza era già piena di gente che camminava lenta tra i banchi, fermandosi a chiacchierare con i venditori che conosceva da anni. Alcuni bambini si divertivano a contare quante bancarelle vendevano dolciumi, mentre i genitori sceglievano con calma la verdura più fresca per il pranzo della domenica.", "parole": 96},
    {"nome": "Il faro", "testo": "Sulla punta più estrema della costa si ergeva un faro bianco, visibile da chilometri di distanza nelle notti serene. Il guardiano che lo custodiva viveva lì da più di trent'anni, insieme a un gatto che lo seguiva ovunque tra le scale a chiocciola. Ogni sera, poco prima del tramonto, saliva fino alla lanterna per controllare che la luce girasse regolarmente, proteggendo le barche dagli scogli nascosti sotto la superficie dell'acqua. Con il tempo, quel gesto era diventato quasi un rito, ripetuto senza mai saltare una sera.", "parole": 92},
    {"nome": "La bottega del falegname", "testo": "Nel retro della vecchia bottega, tra segatura e attrezzi appesi alle pareti, il falegname lavorava seduto su uno sgabello basso, la pialla in mano e la radio accesa in sottofondo. Ogni pezzo di legno veniva scelto con cura, osservato controluce per capire dove si nascondevano i nodi più duri. I clienti che entravano si fermavano spesso a guardarlo lavorare, incuriositi dal modo in cui trasformava semplici tavole in mobili solidi e ben rifiniti, pronti per arredare case che non avrebbe mai visto.", "parole": 90},
    {"nome": "La gita in barca", "testo": "Quella mattina il mare era completamente calmo, senza nemmeno un'onda a increspare la superficie. Il pescatore aveva deciso di portare i due nipoti al largo, mostrando loro come si preparavano le reti prima di calarle in acqua. I bambini osservavano tutto con attenzione, facendo domande su ogni corda e ogni nodo, mentre la barca si allontanava piano dalla riva. Al ritorno, stanchi ma contenti, raccontarono ai genitori ogni singolo dettaglio della giornata passata sull'acqua.", "parole": 84},
    {"nome": "Il vecchio orologio", "testo": "Sopra il camino del salotto era appeso un orologio a pendolo, ereditato dal nonno insieme alla casa. Ogni ora suonava un rintocco leggermente stonato, che con gli anni era diventato un suono familiare per tutta la famiglia. Nessuno aveva mai voluto farlo riparare del tutto, perché quel piccolo difetto sembrava far parte della sua storia. Quando arrivavano ospiti, spesso qualcuno notava il suono particolare e chiedeva da quanto tempo fosse in famiglia quell'orologio così antico.", "parole": 86},
]
_PROBLEMI_CALCOLO = ["7 + 5 =", "12 − 4 =", "6 × 3 =", "20 ÷ 4 =", "15 + 8 ="]


def _trova_paziente_per_cf(conn, codice_fiscale: str):
    """Cerca un paziente già in anagrafica con lo stesso codice fiscale."""
    if not codice_fiscale:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pazienti WHERE UPPER(codice_fiscale) = UPPER(%s) LIMIT 1",
                    (codice_fiscale.strip(),))
        r = cur.fetchone()
        return (r[0] if r else None)
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return None


def _crea_paziente_da_iscrizione(conn, iscr) -> int | None:
    """Crea un paziente in anagrafica a partire da un'iscrizione evento, se non
    già agganciato — usa nome/cognome/data nascita del bambino e email/telefono
    del genitore come contatto. Se esiste già un paziente con lo stesso codice
    fiscale, riusa quello invece di duplicare."""
    gid = lambda k: (iscr.get(k) if hasattr(iscr, "get") else None)
    cf = gid("codice_fiscale") or gid("codice_fiscale_bambino")
    esistente = _trova_paziente_per_cf(conn, cf)
    if esistente:
        return esistente
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pazienti (cognome, nome, data_nascita, email, telefono, codice_fiscale, stato_paziente)
            VALUES (%s, %s, %s, %s, %s, %s, 'ATTIVO') RETURNING id
        """, (
            # stato_paziente e' NOT NULL: senza, l'inserimento veniva rifiutato.
            # Maiuscolo come in anagrafica, cosi' la ricerca lo trova.
            (gid("cognome_bambino") or gid("cognome") or "").strip().upper(),
            (gid("nome_bambino") or gid("nome") or "").strip().upper(),
            gid("data_nascita_bambino") or gid("data_nascita"),
            gid("email"), gid("telefono"), cf,
        ))
        _r = cur.fetchone()
        new_id = int(_r["id"] if isinstance(_r, dict) else _r[0])
        conn.commit()
        return new_id
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore creazione anagrafica: {e}")
        return None


def sincronizza_tutte_iscrizioni_in_anagrafica(conn) -> dict:
    """Passa TUTTI gli iscritti di TUTTI gli eventi: se già presenti in
    anagrafica per codice fiscale li aggancia, altrimenti li crea. Non
    duplica mai un paziente con lo stesso codice fiscale."""
    from .eventi.db_eventi import lista_eventi, lista_iscrizioni, aggancia_paziente
    creati, agganciati, saltati = 0, 0, 0
    for e in (lista_eventi(conn) or []):
        evento_id = e.get("id") if hasattr(e, "get") else e[0]
        for iscr in (lista_iscrizioni(conn, evento_id) or []):
            gid = lambda k: (iscr.get(k) if hasattr(iscr, "get") else None)
            if gid("paziente_id"):
                saltati += 1
                continue
            cf = gid("codice_fiscale") or gid("codice_fiscale_bambino")
            esistente = _trova_paziente_per_cf(conn, cf)
            if esistente:
                aggancia_paziente(conn, gid("id"), esistente)
                agganciati += 1
            else:
                nuovo_id = _crea_paziente_da_iscrizione(conn, iscr)
                if nuovo_id:
                    aggancia_paziente(conn, gid("id"), nuovo_id)
                    creati += 1
    return {"creati": creati, "agganciati": agganciati, "saltati": saltati}


def _selettore_da_evento(conn):
    """Box 'Da evento': scegli un evento e un iscritto, il paziente viene
    creato/agganciato in automatico e diventa il paziente attivo."""
    try:
        from .eventi.db_eventi import lista_eventi, lista_iscrizioni, aggancia_paziente
    except Exception:
        return
    with st.expander("📥 Prendi anagrafica da un evento (es. Giornata del benessere del bambino)"):
        if st.button("🔄 Sincronizza TUTTI gli iscritti di TUTTI gli eventi in anagrafica",
                      key="scr_sync_tutti"):
            esito = sincronizza_tutte_iscrizioni_in_anagrafica(conn)
            st.success(f"Creati {esito['creati']} nuovi pazienti · agganciati {esito['agganciati']} "
                       f"a pazienti già esistenti (stesso codice fiscale) · {esito['saltati']} già collegati.")
        st.markdown("---")
        eventi = lista_eventi(conn) or []
        if not eventi:
            st.caption("Nessun evento trovato.")
            return
        nomi_eventi = {f"{e.get('titolo') if hasattr(e,'get') else e[1]} — "
                       f"{e.get('id') if hasattr(e,'get') else e[0]}": (e.get('id') if hasattr(e,'get') else e[0])
                       for e in eventi}
        scelto = st.selectbox("Evento", list(nomi_eventi.keys()), key="scr_evento_scelto")
        evento_id = nomi_eventi[scelto]
        iscrizioni = lista_iscrizioni(conn, evento_id) or []
        if not iscrizioni:
            st.caption("Nessun iscritto per questo evento.")
            return
        def _label(i):
            g = lambda k: (i.get(k) if hasattr(i, "get") else None)
            return f"{g('cognome_bambino') or ''} {g('nome_bambino') or ''} — {g('email') or ''}".strip()
        mappa = {_label(i): i for i in iscrizioni}
        scelto_iscr = st.selectbox("Iscritto", list(mappa.keys()), key="scr_iscritto_scelto")
        iscr = mappa[scelto_iscr]
        gid = lambda k: (iscr.get(k) if hasattr(iscr, "get") else None)
        if st.button("✅ Usa questo iscritto per lo screening", key="scr_usa_iscritto"):
            paz_id_esistente = gid("paziente_id")
            if paz_id_esistente:
                st.session_state["_paziente_attivo_id"] = paz_id_esistente
            else:
                nuovo_id = _crea_paziente_da_iscrizione(conn, iscr)
                if nuovo_id:
                    aggancia_paziente(conn, gid("id"), nuovo_id)
                    st.session_state["_paziente_attivo_id"] = nuovo_id
            st.success("Fatto — ricarico con questo paziente attivo.")
            st.rerun()


def render_screening(conn=None, paz_id=None, paziente=None) -> None:
    st.header("🩺 Screening rapido")
    st.caption("Scheda breve multi-area per una prima rilevazione — evento, scuola, "
               "\"Giornata del benessere\". Per il percorso clinico completo usa "
               "Valutazione PNEV.")
    st.info("📺 **Doppio monitor:** apri questa pagina anche sul secondo schermo rivolto "
            "verso il bambino — dove previsto trova qui sotto lo stimolo da leggere/guardare, "
            "identico a quello che vedi tu.")

    with st.expander("📋 Serve il protocollo completo (33 pagine, copia fedele del PDF)?"):
        st.caption("Screening resta la scheda breve per eventi/scuola. Per la valutazione clinica "
                   "completa con tutte le tabelle del protocollo, vai al menu a sinistra → "
                   "\"📋 Protocollo di valutazione (completo)\" (accanto a Eye tracking).")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    _selettore_da_evento(conn)

    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    operatore = st.text_input("Operatore", key="scr_operatore")

    t_ling, t_appr, t_vp, t_mio, t_osteo = st.tabs(
        ["🗣️ Linguaggio", "📚 Apprendimento", "👁️ Visuo-posturale",
         "💆 Miofunzionale", "🦴 Osteopatico"])

    with t_ling:
        st.caption("Segui l'ordine: è lo stesso del protocollo su carta, una parte dopo l'altra.")

        st.markdown("### PARTE 1 — Bilancio fonetico")
        _significato("per ogni fono, in posizione iniziale e intervocalica, chiedi al bambino di "
                     "dire la parola-stimolo (denominazione su figura o ripetizione) e segna l'esito: "
                     "✓ corretto, S sostituzione, O omissione, D distorsione, I instabile.")
        _LISTA_FONI = [
            ("Occlusivi", [("p", "pane", "lupo"), ("b", "barca", "tubo"), ("t", "tavolo", "moto"),
                            ("d", "dado", "nido"), ("k", "casa", "fuoco"), ("g", "gatto", "ago")]),
            ("Fricativi", [("f", "fiore", "telefono"), ("v", "vaso", "uva"), ("s", "sole", "sasso"),
                            ("sc [ʃ]", "sciarpa", "pesce")]),
            ("Affricati", [("z [ts]", "zampa", "pizza"), ("z [dz]", "zebra", "azzurro"),
                            ("ci [tʃ]", "cena", "braccio"), ("gi [dʒ]", "giraffa", "valigia")]),
            ("Nasali", [("m", "mano", "lumaca"), ("n", "naso", "luna"), ("gn [ɲ]", "gnomo", "bagno")]),
            ("Liquidi", [("l", "luna", "gelato"), ("gl [ʎ]", "gli occhi", "foglia"),
                          ("r (vibr.)", "rana", "faro"), ("r (tenuta)", "ferro", "arrotolare")]),
        ]
        esiti_opz = ["✓ corretto", "S sostituzione", "O omissione", "D distorsione", "I instabile", "NR"]
        bilancio_dati = {}
        import pandas as pd
        for categoria, foni in _LISTA_FONI:
            st.markdown(f"**{categoria}**")
            df_base = pd.DataFrame([
                {"Fono": fono, "Iniziale": parola_in, "Esito iniziale": "✓ corretto",
                 "Intervocalica": parola_interv, "Esito intervocalica": "✓ corretto", "Note": ""}
                for fono, parola_in, parola_interv in foni
            ])
            df_out = st.data_editor(
                df_base, key=f"scr_bf_tab_{categoria}", hide_index=True, use_container_width=True,
                column_config={
                    "Fono": st.column_config.TextColumn(disabled=True),
                    "Iniziale": st.column_config.TextColumn(disabled=True),
                    "Esito iniziale": st.column_config.SelectboxColumn(options=esiti_opz, required=True),
                    "Intervocalica": st.column_config.TextColumn(disabled=True),
                    "Esito intervocalica": st.column_config.SelectboxColumn(options=esiti_opz, required=True),
                },
            )
            for _, row in df_out.iterrows():
                bilancio_dati[row["Fono"]] = {"iniziale": row["Esito iniziale"],
                                               "intervocalica": row["Esito intervocalica"],
                                               "note": row["Note"]}

        st.markdown("**1.3 Prove di struttura**")
        st.markdown("_1.3.1 Gruppi consonantici_")
        df_gruppi = st.data_editor(pd.DataFrame([
            {"Tipo": "Muta + liquida", "Stimoli": "blu · treno · drago · prato · grande · fragola · clarinetto · fiocco", "Riduzioni osservate": ""},
            {"Tipo": "s + consonante", "Stimoli": "scala · spugna · stella · sveglia · smalto · scivolo", "Riduzioni osservate": ""},
            {"Tipo": "Nessi complessi", "Stimoli": "strada · scrivere · sprecare · splendere · struzzo", "Riduzioni osservate": ""},
            {"Tipo": "Nasale + cons.", "Stimoli": "campana · bambino · pianta · fungo · tenda", "Riduzioni osservate": ""},
        ]), key="scr_bf_gruppi", hide_index=True, use_container_width=True,
            column_config={"Tipo": st.column_config.TextColumn(disabled=True),
                           "Stimoli": st.column_config.TextColumn(disabled=True)})

        st.markdown("_1.3.2 Dittonghi e iati_")
        st.caption("uovo · piede · fiore · guanto · aiuola · aquilone · buio")
        note_dittonghi = st.text_input("Osservazioni dittonghi/iati", key="scr_bf_dittonghi")

        st.markdown("_1.3.3 Polisillabi (tenuta della struttura)_")
        df_polisillabi = st.data_editor(pd.DataFrame([
            {"Sillabe": "3", "Stimoli": "farfalla · ospedale · bicchiere", "Produzione del soggetto": ""},
            {"Sillabe": "4", "Stimoli": "cioccolato · apparecchio · termometro", "Produzione del soggetto": ""},
            {"Sillabe": "5", "Stimoli": "elicottero · rinoceronte · frigorifero · acquerello", "Produzione del soggetto": ""},
            {"Sillabe": "5+", "Stimoli": "televisione · automobilista · particolarmente", "Produzione del soggetto": ""},
        ]), key="scr_bf_polisillabi", hide_index=True, use_container_width=True,
            column_config={"Sillabe": st.column_config.TextColumn(disabled=True),
                           "Stimoli": st.column_config.TextColumn(disabled=True)})

        st.markdown("**Processi di semplificazione — frequenza**")
        st.caption("0 assente · 1 sporadico (<25%) · 2 frequente (25-75%) · 3 sistematico (>75%)")
        with st.expander("📅 A che età è normale (canovaccio per i genitori)"):
            st.markdown(
                "- **2;6–3 anni**: quasi tutte le semplificazioni sono normali "
                "(Stopping, Riduzione gruppi consonantici, Eliminazione sillaba debole, "
                "Riduzione dittonghi, Armonia consonantica/vocalica).\n"
                "- **3–3;6 anni**: si risolvono anche Affricazione, Desonorizzazione, "
                "Metatesi, Epentesi.\n"
                "- **3;6–4;6 anni**: Gliding e gruppi consonantici con /r/ (gli ultimi ad "
                "acquisirsi) restano normali fino a questa età.\n"
                "- **Dopo i 5 anni**: qualunque semplificazione ancora presente merita "
                "un approfondimento; dopo i 6 anni è un campanello d'allarme.\n"
                "- **Posteriorizzazione**: atipica a qualunque età, anche prima dei 3;6 anni."
            )
        _PROCESSI = [
            ("Stopping", "sole → «tole»", "3;6–4;0"), ("Fricazione", "cena → «sena»", "4;0"),
            ("Affricazione", "sole → «zole»", "4;0"), ("Anteriorizzazione", "casa → «tasa»", "4;0"),
            ("Posteriorizzazione", "tavolo → «cavolo»", "3;6"), ("Desonorizzazione", "barca → «parca»", "3;6"),
            ("Gliding", "rana → «jana»", "5;0"), ("Elim. sillaba debole", "elefante → «fante»", "4;0"),
            ("Armonia consonantica", "tavolo → «lavolo»", "3;6"), ("Armonia vocalica", "bambino → «bimbino»", "3;6"),
            ("Riduzione gruppi", "treno → «teno»", "4;6–5;0"), ("Riduzione dittonghi", "uovo → «ovo»", "4;0"),
            ("Metatesi", "ospedale → «opsedale»", "4;6"), ("Epentesi", "blu → «belu»", "4;0"),
            ("Cancellazione", "pane → «ane»", "3;6"),
        ]
        processi_dati = {}
        for nome, esempio, limite in _PROCESSI:
            cp1, cp2, cp3 = st.columns([2, 2, 1])
            cp1.markdown(f"**{nome}** — _{esempio}_")
            cp2.caption(f"Limite indicativo: {limite}")
            freq = cp3.selectbox(" ", [0, 1, 2, 3], key=f"scr_proc_{nome}", label_visibility="collapsed")
            processi_dati[nome] = freq

        st.markdown("---")
        st.markdown("### PARTE 2 — Linguaggio")
        _significato("osserva quante parole conosce e usa (lessico) e come costruisce "
                      "le frasi (grammatica) rispetto all'età.")
        with st.expander("📺 Materiale per la denominazione (schermo grande)"):
            _big("🐶 cane · 🚗 macchina · 🌳 albero · 🍎 mela")
            st.caption("Chiedi di nominare le immagini: osserva lessico e pronuncia dei suoni.")
            _finestra_bambino("🐶 cane &nbsp; 🚗 macchina &nbsp; 🌳 albero &nbsp; 🍎 mela", "linguaggio")
        livello_lex = st.text_area("Livello lessicale-semantico", key="scr_ling_lex", height=68)
        livello_morfo = st.text_area("Livello morfosintattico e narrativo", key="scr_ling_morfo", height=68)

        st.markdown("---")
        st.markdown("### PARTE 3 — Disturbi della fluenza")
        _significato("osserva se il bambino ripete, blocca o allunga suoni/parole mentre parla "
                     "(balbuzie) o parla troppo rapidamente in modo confuso (tachilalia/cluttering).")
        balbuzie = st.text_input("Balbuzie (familiarità, epoca insorgenza)", key="scr_ling_balbuzie")
        tachilalia = st.text_input("Tachilalia / cluttering", key="scr_ling_tachilalia")
        extra_verbale = st.text_input("Sintomatologia extra-verbale", key="scr_ling_extra")

        semp_sist = semp_strut = []
        ling_bilancio = ling_semp = ling_livelli = ling_fluenza = True
        bilancio_fonetico = {}

    with t_appr:
        appr_lettura = st.checkbox("Eseguito — Lettura", key="scr_appr_lettura_on")
        lett_parole = lett_nonparole = lett_brano = ""
        if appr_lettura:
            _significato("misura quanto velocemente e correttamente il bambino legge ad alta voce — "
                         "un indicatore chiave per la dislessia.")
            st.markdown("**Lettura — velocità e correttezza (numero errori)**")
            c1, c2, c3 = st.columns(3)
            lett_parole = c1.text_input("Parole", key="scr_appr_lett_parole")
            lett_nonparole = c2.text_input("Non parole", key="scr_appr_lett_nonparole")
            lett_brano = c3.text_input("Brano", key="scr_appr_lett_brano")
            with st.expander("📺 Testo da far leggere (schermo grande)", expanded=True):
                usa_cartaceo = st.checkbox("Uso le tavole IReST cartacee (non mostrare nulla a schermo)",
                                            value=True, key="scr_lettura_cartaceo")
                if usa_cartaceo:
                    _IREST_NORME = {
                        "Topi":    {"parole":138, "sillabe":299, "tempo_medio":46.4, "tempo_ds":5.2, "vel_media":181, "vel_ds":24},
                        "Castoro": {"parole":144, "sillabe":295, "tempo_medio":42.6, "tempo_ds":5.1, "vel_media":206, "vel_ds":29},
                        "Alberi":  {"parole":140, "sillabe":283, "tempo_medio":43.8, "tempo_ds":5.5, "vel_media":194, "vel_ds":24},
                        "Preda":   {"parole":134, "sillabe":299, "tempo_medio":44.1, "tempo_ds":5.5, "vel_media":185, "vel_ds":26},
                        "Deserto": {"parole":135, "sillabe":294, "tempo_medio":43.9, "tempo_ds":5.4, "vel_media":188, "vel_ds":26},
                        "Veleno":  {"parole":126, "sillabe":302, "tempo_medio":44.7, "tempo_ds":6.3, "vel_media":174, "vel_ds":29},
                        "Isola":   {"parole":134, "sillabe":298, "tempo_medio":42.5, "tempo_ds":5.8, "vel_media":193, "vel_ds":29},
                        "Ragni":   {"parole":134, "sillabe":260, "tempo_medio":43.4, "tempo_ds":5.2, "vel_media":188, "vel_ds":27},
                        "Inverno": {"parole":132, "sillabe":289, "tempo_medio":43.5, "tempo_ds":6.8, "vel_media":187, "vel_ds":34},
                        "Colori":  {"parole":131, "sillabe":297, "tempo_medio":44.7, "tempo_ds":6.4, "vel_media":179, "vel_ds":27},
                    }
                    tavola_scelta = st.selectbox("Tavola IReST utilizzata (cartacea)", list(_IREST_NORME.keys()),
                                                  key="scr_lettura_tavola")
                    norme = _IREST_NORME[tavola_scelta]
                    st.caption(f"Tavola \"{tavola_scelta}\" — {norme['parole']} parole, {norme['sillabe']} sillabe. "
                               f"Norma adulti: {norme['tempo_medio']}±{norme['tempo_ds']}s · "
                               f"{norme['vel_media']}±{norme['vel_ds']} par/min.")
                    ci1, ci2 = st.columns(2)
                    tempo_letto = ci1.number_input("Tempo di lettura (s)", min_value=0.1, step=0.1, key="scr_irest_tempo")
                    errori_letti = ci2.number_input("Errori (n.)", min_value=0, step=1, key="scr_irest_errori")
                    if tempo_letto > 0:
                        vel_parmin = norme["parole"] * 60 / tempo_letto
                        vel_sillsec = norme["sillabe"] / tempo_letto
                        z = (vel_parmin - norme["vel_media"]) / norme["vel_ds"] if norme["vel_ds"] else 0
                        accuratezza = (norme["parole"] - errori_letti) * 100 / norme["parole"]
                        cr1, cr2, cr3, cr4 = st.columns(4)
                        cr1.metric("Velocità", f"{vel_parmin:.0f} par/min")
                        cr2.metric("Sillabe/sec", f"{vel_sillsec:.2f}")
                        cr3.metric("z (vs adulti)", f"{z:+.2f}")
                        cr4.metric("Accuratezza", f"{accuratezza:.0f}%")
                        st.caption("⚠️ Le norme sono su adulti normolettori: lo z in età evolutiva va letto come "
                                   "misura ripetibile intra-soggetto (confronto pre/post), non come deviazione da "
                                   "una norma per età.")
                else:
                    nomi_testi = [b["nome"] for b in _TESTI_IREST]
                    scelto = st.selectbox("Scegli il testo originale da mostrare a schermo", nomi_testi,
                                           key="scr_lettura_scelta")
                    idx_t = nomi_testi.index(scelto)
                    brano = _TESTI_IREST[idx_t]
                    _big(brano["testo"])
                    st.caption(f"Testo di lettura originale · \"{brano['nome']}\" · {brano['parole']} parole "
                               f"— misura ripetibile intra-soggetto, non tarata su campione normativo.")
                    _finestra_bambino(brano["testo"], "lettura")

        appr_scrittura = st.checkbox("Eseguito — Scrittura (protocollo completo)", key="scr_appr_scrittura_on")
        dettato_parole_scr = omofone_scr = griglia_errori_scr = None
        dettato_esiti_scr = tempo_dettato_scr = profilo_prevalente_scr = ""
        if appr_scrittura:
            _significato("valuta gli errori ortografici sotto dettatura, per categoria — fonologici, "
                         "non fonologici/lessicali, fonetici — utile per individuare e classificare "
                         "la disortografia, secondo lo stesso standard usato nel protocollo completo.")
            st.markdown("**4.2a Dettato di parole e non parole** (tutte le fasce)")
            df_dett = pd.DataFrame([
                {"Serie": "P1 — parole regolari", "Item": "tavolo · fiume · pratica · salame · destino · burrone · mandorla · calamita", "Errori": ""},
                {"Serie": "P2 — digrammi/trigrammi", "Item": "chiodo · ghiaccio · scienza · guglia · sciopero · ciliegia · gnocco · quaglia", "Errori": ""},
                {"Serie": "P3 — doppie e accenti", "Item": "bicchiere · perché · attrezzo · città · raggruppare · virtù · soqquadro · lassù", "Errori": ""},
                {"Serie": "NP — non parole", "Item": "brastone · gliunfo · scenaglio · quortimo · sbicchera · zampruglio · ghialdo · trescimo", "Errori": ""},
            ])
            dettato_parole_scr = st.data_editor(df_dett, key="scr_scr_dettato_parole", hide_index=True,
                use_container_width=True,
                column_config={"Serie": st.column_config.TextColumn(disabled=True),
                               "Item": st.column_config.TextColumn(disabled=True)})

            with st.expander("📺 4.2b Dettato — Fascia A (infanzia/1ª primaria)"):
                st.caption("Prima le 8 sillabe, poi le 10 parole, poi le 2 frasi. Stampato maiuscolo ammesso.")
                st.markdown("Sillabe: *ma · le · si · ro · fu · ne · pi · to*")
                st.markdown("Parole: *luna · rana · dado · sole · vaso · mela · nido · pane · fumo · gatto*")
                st.markdown("Frasi: «Il gatto beve il latte.» — «La mamma apre la porta.»")
            with st.expander("📺 4.2c Dettato — Fascia B (2ª-5ª primaria) · «Il temporale d'agosto» (69 parole)"):
                st.markdown(
                    "Quel pomeriggio d'agosto il cielo si è fatto scuro all'improvviso. La nonna ha chiuso le "
                    "finestre e ha acceso la luce in cucina. Fuori l'acqua scendeva a scrosci e il vento faceva "
                    "sbattere la porta del garage. Gli uccelli si erano rifugiati sotto il tetto della legnaia. "
                    "Quando la pioggia è cessata, sull'aia c'erano pozzanghere grandi come specchi e un profumo "
                    "di terra bagnata saliva dal campo."
                )
                st.caption("Bersagli: apostrofo · h di avere · accento (è) · digrammi/trigrammi · qu · doppie · "
                           "gruppi consonantici.")
                _finestra_bambino(
                    "Quel pomeriggio d'agosto il cielo si è fatto scuro all'improvviso...", "dettato_b")
            with st.expander("📺 4.2d Dettato — Fascia C (secondaria) · «La biblioteca» (112 parole)"):
                st.markdown(
                    "Da quando l'anno scorso hanno ristrutturato la biblioteca, ci vado quasi ogni pomeriggio. "
                    "All'ingresso c'è un cartello che ricorda di non far rumore: qualcuno lo legge, altri no. Ieri "
                    "ho scelto un volume di scienze e mi sono seduto vicino alla finestra, dove d'inverno batte il "
                    "sole. A un certo punto è entrato un ragazzo con l'aria smarrita: cercava un'enciclopedia che "
                    "non aveva mai visto prima. Gliel'ho indicata sullo scaffale più alto, poi siamo rimasti a "
                    "chiacchierare finché la bibliotecaria non ci ha fatto cenno di uscire. Fuori pioveva ancora, "
                    "ma ormai non avevamo fretta: ci siamo dati appuntamento per giovedì."
                )
                st.caption("Bersagli: coppie omofone · apostrofo con articolo femminile/assenza con maschile · "
                           "clitico composto · accenti · sci/sce · chi · doppie e nessi complessi.")
            dettato_esiti_scr = st.text_area("Esiti dettato brano (errori, tempo, ripetizioni richieste)",
                                              key="scr_scr_dettato_esiti", height=68)

            st.markdown("**4.2e Dettato di coppie omofone non omografe** (B dalla 3ª · C)")
            df_omof = pd.DataFrame([
                {"#": 1, "Frase": "L'anno scorso hanno vinto loro.", "Bersaglio": "anno / hanno", "Esito": ""},
                {"#": 2, "Frase": "Ho comprato o un libro o un quaderno.", "Bersaglio": "ho / o", "Esito": ""},
                {"#": 3, "Frase": "Ha detto che va a casa a piedi.", "Bersaglio": "ha / a", "Esito": ""},
                {"#": 4, "Frase": "Ai bambini piace il gelato: hai visto?", "Bersaglio": "ai / hai", "Esito": ""},
                {"#": 5, "Frase": "Non c'è nessuno, ce ne andiamo.", "Bersaglio": "c'è / ce", "Esito": ""},
                {"#": 6, "Frase": "Un'amica mi ha prestato un ombrello.", "Bersaglio": "un' / un", "Esito": ""},
                {"#": 7, "Frase": "Ce l'ho in tasca, ma non l'ho portato.", "Bersaglio": "l'ho / lo", "Esito": ""},
                {"#": 8, "Frase": "Gliel'ha data lui, gliela riporterò domani.", "Bersaglio": "gliel'ha / gliela", "Esito": ""},
                {"#": 9, "Frase": "Dov'è andato? Dove abiti tu?", "Bersaglio": "dov'è / dove", "Esito": ""},
                {"#": 10, "Frase": "Se n'è andato senza dire niente.", "Bersaglio": "n'è / ne", "Esito": ""},
            ])
            omofone_scr = st.data_editor(df_omof, key="scr_scr_omofone", hide_index=True, use_container_width=True,
                column_config={"#": st.column_config.TextColumn(disabled=True),
                               "Frase": st.column_config.TextColumn(disabled=True),
                               "Bersaglio": st.column_config.TextColumn(disabled=True)})

            st.markdown("**4.2f Griglia di analisi degli errori**")
            df_grig = pd.DataFrame([
                {"Categoria": "Fonologici", "Sottotipo": "Scambio grafemi (f/v, t/d, p/b, m/n, s/z, r/l)", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Fonologici", "Sottotipo": "Omissione/aggiunta lettere o sillabe", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Fonologici", "Sottotipo": "Inversione di lettere o sillabe", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Fonologici", "Sottotipo": "Grafema inesatto (sci/sc, gn/ni, gli/li, ch/c, gh/g)", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Non fonologici", "Sottotipo": "Separazione illegale", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Non fonologici", "Sottotipo": "Fusione illegale", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Non fonologici", "Sottotipo": "Scambio grafema omofono (qu/cu/cq, h iniziale)", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Non fonologici", "Sottotipo": "Omofone non omografe", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Fonetici", "Sottotipo": "Doppie (omesse o aggiunte)", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Fonetici", "Sottotipo": "Accenti (omessi, aggiunti, mal collocati)", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Altri", "Sottotipo": "Punteggiatura, maiuscole", "Parole": "", "Non par.": "", "Brano": ""},
                {"Categoria": "Altri", "Sottotipo": "Autocorrezioni e cancellature", "Parole": "", "Non par.": "", "Brano": ""},
            ])
            griglia_errori_scr = st.data_editor(df_grig, key="scr_scr_griglia", hide_index=True, use_container_width=True,
                column_config={"Categoria": st.column_config.TextColumn(disabled=True),
                               "Sottotipo": st.column_config.TextColumn(disabled=True)})
            c_scr1, c_scr2 = st.columns(2)
            tempo_dettato_scr = c_scr1.text_input("Tempo totale dettato (' \")", key="scr_scr_tempo")
            profilo_prevalente_scr = c_scr2.selectbox("Profilo prevalente",
                ["", "Fonologico", "Non fonologico/lessicale", "Fonetico", "Misto"], key="scr_scr_profilo")

        # compatibilità con le vecchie chiavi del riepilogo/relazione
        scr_parole = scr_nonparole = scr_omofone = grafia = ""

        appr_calcolo = st.checkbox("Eseguito — Calcolo", key="scr_appr_calcolo_on")
        calc_scritto = enumerazione = fatti_proc = ""
        if appr_calcolo:
            _significato("valuta calcolo a mente/scritto, conteggio e memorizzazione dei fatti "
                         "numerici — utile per individuare la discalculia.")
            st.markdown("**Calcolo**")
            calc_scritto = st.text_area("Calcolo scritto e a mente", key="scr_appr_calc_scritto", height=68)
            enumerazione = st.text_input("Enumerazione", key="scr_appr_enum")
            fatti_proc = st.text_input("Fatti e procedure", key="scr_appr_fatti")
            with st.expander("📺 Problemi da mostrare (schermo grande)", expanded=True):
                if st.button("🔁 Nuovi problemi", key="scr_calcolo_nuovo"):
                    st.session_state["scr_calcolo_probl"] = random.sample(_PROBLEMI_CALCOLO, 3)
                probl = st.session_state.get("scr_calcolo_probl", _PROBLEMI_CALCOLO[:3])
                _big(" &nbsp;&nbsp; ".join(probl))
                _finestra_bambino(" &nbsp;&nbsp;&nbsp; ".join(probl), "calcolo")

    with t_vp:
        vp_cover = st.checkbox("Eseguito — Cover Test", key="scr_vp_cover_on")
        ct_lontano = ct_vicino = harmon = rrd = ppc = ppa = ""
        if vp_cover:
            _significato("verifica se gli occhi restano allineati o deviano quando uno viene "
                         "coperto — rileva forie/tropie (difetti di allineamento oculare).")
            st.markdown("**Cover Test**")
            c1, c2 = st.columns(2)
            ct_lontano = c1.text_input("Cover test lontano (XL)", key="scr_vp_ct_l")
            ct_vicino = c2.text_input("Cover test vicino (XV)", key="scr_vp_ct_v")
            c3, c4 = st.columns(2)
            harmon = c3.text_input("Harmon (cm)", key="scr_vp_harmon")
            rrd = c4.text_input("RRD (cm)", key="scr_vp_rrd")
            c5, c6 = st.columns(2)
            ppc = c5.text_input("PPC (rottura/recupero)", key="scr_vp_ppc")
            ppa = c6.text_input("PPA OD/OS", key="scr_vp_ppa")
            with st.expander("📺 Mira da mostrare (schermo grande)"):
                _big("➕")
                st.caption("Il bambino fissa la mira mentre l'operatore avvicina/copre alternativamente gli occhi.")
                _finestra_bambino("➕", "covertest")

        vp_nsuco = st.checkbox("Eseguito — NSUCO (Pursuit/Saccadi)", key="scr_vp_nsuco_on")
        nsuco_pursuit = nsuco_saccadi = ""
        if vp_nsuco:
            _significato("valuta il controllo del movimento oculare: inseguimento lento (pursuit) "
                         "e salti rapidi tra due punti (saccadi) — importanti per la lettura.")
            c7, c8 = st.columns(2)
            nsuco_pursuit = c7.selectbox("Pursuit (abilità 1-5)", ["", 1, 2, 3, 4, 5], key="scr_vp_nsuco_p")
            nsuco_saccadi = c8.selectbox("Saccadi (abilità 1-5)", ["", 1, 2, 3, 4, 5], key="scr_vp_nsuco_s")
            with st.expander("📺 Bersaglio da mostrare (schermo grande)"):
                _big("● &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ●")
                st.caption("Muovi/alterna la mira mentre il bambino la segue solo con gli occhi, testa ferma.")
                _finestra_bambino("● &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ●", "nsuco")

        vp_dem = st.checkbox("Eseguito — DEM / K-D Test / Clinical Fusion", key="scr_vp_dem_on")
        dem = kd = cft = ""
        if vp_dem:
            _significato("il bambino legge ad alta voce colonne di numeri il più velocemente "
                         "possibile: misura la velocità di scansione visiva legata alla lettura.")
            c9, c10, c11 = st.columns(3)
            dem = c9.text_input("DEM (A/B/C, sec, err)", key="scr_vp_dem")
            kd = c10.text_input("K-D Test (I/II/III, sec, err)", key="scr_vp_kd")
            cft = c11.text_input("Clinical Fusion Test", key="scr_vp_cft")
            with st.expander("📺 Numeri da leggere (schermo grande)", expanded=True):
                if st.button("🔁 Nuova scheda numeri", key="scr_dem_nuovo"):
                    st.session_state["scr_dem_righe"] = [
                        " ".join(str(random.randint(0, 9)) for _ in range(8)) for _ in range(3)
                    ]
                righe_numeri = st.session_state.get(
                    "scr_dem_righe",
                    [" ".join(str(random.randint(0, 9)) for _ in range(8)) for _ in range(3)],
                )
                for riga in righe_numeri:
                    _big(riga)
                _finestra_bambino("<br>".join(righe_numeri), "demkd")

        tb_eseguito = st.checkbox("Eseguito — Telebinocular", key="scr_vp_tb_eseguito")
        tb_serie = tb_occhiali = tb_collab = ""
        tb_test_risposte = {}
        if tb_eseguito:
            _significato("con lo strumento Telebinocular verifica visione simultanea, foria, "
                         "fusione, visione binoculare utilizzabile e stereopsi — usa le tavole "
                         "originali dello strumento, qui si registra solo il risultato.")
            tb_serie = st.selectbox("Serie di tavole utilizzata", [
                "Visual Skills (14 test)",
                "Peek-A-Boo (9 test — prescolari/non lettori)",
                "Screening rapido scuola",
                "Clinical Fusion — riserve prismatiche"], key="scr_vp_tb_serie")
            ctb0a, ctb0b = st.columns(2)
            tb_occhiali = ctb0a.selectbox("Occhiali durante l'esame", ["No", "Sì"], key="scr_vp_tb_occhiali")
            tb_collab = ctb0b.selectbox("Collaborazione", ["Buona", "Discontinua", "Insufficiente"],
                                         key="scr_vp_tb_collab")
            if tb_serie.startswith("Visual Skills"):
                st.caption("Icone originali (non riprodotte da alcuna scheda commerciale) — clicca "
                           "l'opzione osservata sotto ciascun test.")
                _VS_14 = [
                    ("1", "Visione simultanea", "L", ["Solo sinistro", "Solo destro", "Entrambe"]),
                    ("2", "Postura verticale", "L", ["Ipo dx", "Nei limiti", "Ipo sx"]),
                    ("3", "Postura laterale (foria orizz.)", "L", ["Exo", "Nei limiti", "Ottimale", "Eso"]),
                    ("4", "Fusione", "L", ["Exo", "Nei limiti", "Ottimale", "Eso", "Soppressione"]),
                    ("5", "Visione usabile — binoculare", "L", ["Nei limiti", "Ridotta"]),
                    ("6", "Visione usabile — sinistro", "L", ["Nei limiti", "Ridotta"]),
                    ("7", "Stereopsi", "L", ["Assente", "Ridotta", "Nei limiti", "Ottimale"]),
                    ("8", "Percezione colore — I", "L", ["Tutti", "Parziale", "Errata"]),
                    ("9", "Percezione colore — II", "L", ["Tutti", "Parziale", "Errata"]),
                    ("10", "Postura laterale (foria orizz.)", "V", ["Exo", "Nei limiti", "Ottimale", "Eso"]),
                    ("11", "Fusione", "V", ["Exo", "Nei limiti", "Ottimale", "Eso", "Soppressione"]),
                    ("12", "Visione usabile — binoculare", "V", ["Nei limiti", "Ridotta"]),
                    ("13", "Visione usabile — sinistro", "V", ["Nei limiti", "Ridotta"]),
                    ("14", "Visione usabile — destro", "V", ["Nei limiti", "Ridotta"]),
                ]
                for num, nome, dist, opzioni in _VS_14:
                    v = _riga_test_binoculare(num, nome, dist, opzioni, "scr_vp_vs")
                    tb_test_risposte[f"{num} {nome} ({dist})"] = v
                    st.markdown("---")
            elif tb_serie.startswith("Peek-A-Boo"):
                st.caption("Icone originali — batteria figurata per prescolari/non lettori. "
                           "Clicca l'opzione osservata sotto ciascun test.")
                _PAB_9 = [
                    ("1", "Acuità (denominazione)", "L", ["Identifica tutto", "Parziale", "Non identifica"]),
                    ("2", "Coordinazione laterale", "L", ["Convergenza insuff.", "Nei limiti", "Divergenza"]),
                    ("3", "Fusione", "L", ["1 clown (soppr.)", "2 clown (diplopia)", "Nei limiti"]),
                    ("4", "Stereopsi/colore (facoltativo)", "L", ["Assente", "Nei limiti"]),
                    ("5", "Coordinazione verticale", "L", ["Ipo dx", "Nei limiti", "Ipo sx"]),
                    ("6", "Coordinazione verticale", "V", ["Ipo dx", "Nei limiti", "Ipo sx"]),
                    ("7", "Fusione", "V", ["1 clown (soppr.)", "2 clown (diplopia)", "Nei limiti"]),
                    ("8", "Coordinazione laterale", "V", ["Convergenza insuff.", "Nei limiti", "Divergenza"]),
                    ("9", "Acuità (denominazione)", "V", ["Identifica tutto", "Parziale", "Non identifica"]),
                ]
                for num, nome, dist, opzioni in _PAB_9:
                    v = _riga_test_binoculare(num, nome, dist, opzioni, "scr_vp_pab")
                    tb_test_risposte[f"{num} {nome} ({dist})"] = v
                    st.markdown("---")
            else:
                st.caption("Per questa serie, annota qui l'esito sintetico (le tavole restano quelle "
                           "originali dello strumento).")
                tb_test_risposte["esito_sintetico"] = st.text_area(
                    "Esito", key="scr_vp_tb_altra_serie", height=90)

        vp_postura = st.checkbox("Eseguito — Postura (pedana stabilometrica)", key="scr_vp_postura_on")
        post_peso_sx = post_peso_dx = post_oscill_oa = post_oscill_oc = post_romberg = post_note_postura = ""
        post_superficie = post_lng = ""
        if vp_postura:
            _significato("misura come il bambino distribuisce il peso tra i due piedi e quanto oscilla "
                         "in equilibrio, a occhi aperti e chiusi — la differenza tra le due condizioni "
                         "(indice di Romberg) indica quanto si appoggia alla vista per stare in equilibrio.")
            cp1, cp2 = st.columns(2)
            post_peso_sx = cp1.text_input("Appoggio piede sinistro (%)", key="scr_vp_post_pesosx")
            post_peso_dx = cp2.text_input("Appoggio piede destro (%)", key="scr_vp_post_pesodx")
            cp3, cp4 = st.columns(2)
            post_oscill_oa = cp3.text_input("Oscillazione occhi aperti (mm o u.a.)", key="scr_vp_post_oa")
            post_oscill_oc = cp4.text_input("Oscillazione occhi chiusi (mm o u.a.)", key="scr_vp_post_oc")
            post_romberg = st.text_input("Indice di Romberg (OC/OA)", key="scr_vp_post_romberg")
            post_note_postura = st.text_input("Note posturali", key="scr_vp_post_note")
            with st.expander("Indici avanzati (se la pedana li fornisce)"):
                pc1, pc2 = st.columns(2)
                post_superficie = pc1.text_input("Superficie ellisse conf. 90% (mm²)", key="scr_vp_post_sup")
                post_lng = pc2.text_input("Lunghezza tracciato — LNG (mm)", key="scr_vp_post_lng")

    with t_mio:
        mio_anamnesi = st.checkbox("Eseguito — Anamnesi rapida", key="scr_mio_anamnesi_on")
        parto = allattamento = ""
        mio_flags = []
        if mio_anamnesi:
            _significato("raccoglie dalla voce del genitore le abitudini (respirazione, "
                         "suzione, deglutizione) che possono indicare uno squilibrio orofacciale.")
            st.markdown("**Anamnesi rapida**")
            c1, c2 = st.columns(2)
            parto = c1.selectbox("Parto", ["", "Eutocico", "Distocico", "Cesareo d'urgenza", "Cesareo programmato"],
                                  key="scr_mio_parto")
            allattamento = c2.text_input("Allattamento (seno/biberon, durata)", key="scr_mio_allatt")
            mio_flags = st.multiselect("Segnalazioni", [
                "Ha sofferto di coliche gassose", "Ha sofferto di otiti", "Ha sofferto di tonsille/adenoidi",
                "Soffre di mal di testa", "Ha dolori al collo/spalle/schiena", "Respira a bocca aperta",
                "Dorme a bocca aperta", "Russa", "Bruxa", "Succhia pollice/labbra/lingua",
                "Soffre di raffreddore allergico/asma"], key="scr_mio_flags")

        mio_valutazione = st.checkbox("Eseguito — Valutazione posturale/deglutizione", key="scr_mio_valutazione_on")
        postura_orale = postura_linguale = deglutizione = respirazione = ""
        if mio_valutazione:
            _significato("osserva direttamente postura di lingua/labbra a riposo e come il bambino "
                         "deglutisce — segnali di una funzione orofacciale scorretta.")
            st.markdown("**Valutazione**")
            postura_orale = st.text_input("Postura orale a riposo", key="scr_mio_postura_orale")
            postura_linguale = st.text_input("Postura linguale", key="scr_mio_postura_ling")
            deglutizione = st.text_input("Deglutizione", key="scr_mio_deglut")
            respirazione = st.selectbox("Meccanismo respiratorio", ["", "Nasale", "Orale", "Misto"],
                                         key="scr_mio_respiro")

    with t_osteo:
        osteo_anamnesi = st.checkbox("Eseguito — Anamnesi osteopatica", key="scr_osteo_anamnesi_on")
        gravidanza = crescita = patologie = ""
        if osteo_anamnesi:
            _significato("raccoglie la storia di gravidanza, parto e sviluppo motorio: eventi che "
                         "possono lasciare tensioni o asimmetrie corporee da valutare.")
            st.markdown("**Anamnesi**")
            gravidanza = st.text_area("Gravidanza / parto", key="scr_osteo_grav", height=68)
            crescita = st.text_input("Crescita e sviluppo (peso, tappe motorie)", key="scr_osteo_crescita")
            patologie = st.text_input("Patologie note / visite specialistiche", key="scr_osteo_patologie")

        osteo_indicazioni = st.checkbox("Eseguito — Indicazioni osteopatiche", key="scr_osteo_indic_on")
        indicazione = ""
        if osteo_indicazioni:
            _significato("valutazione manuale diretta dell'osteopata: sintetizza qui l'esito e "
                         "se è indicato un trattamento o un approfondimento.")
            st.markdown("**Indicazioni**")
            indicazione = st.radio("Esito", [
                "Nessuna restrizione significativa", "Possibile beneficio da trattamento osteopatico",
                "Suggerita valutazione pediatrica / specialistica"], key="scr_osteo_indic")

    note = st.text_area("Note generali", key="scr_note", height=68)

    sezioni = {
        "linguaggio": {
            "bilancio_fonetico_completo": bilancio_dati if ling_bilancio else None,
            "processi_semplificazione": processi_dati if ling_bilancio else None,
            "gruppi_consonantici": df_gruppi.to_dict("records"),
            "dittonghi_iati_note": note_dittonghi,
            "polisillabi": df_polisillabi.to_dict("records"),
            "semplificazioni_sistema": semp_sist, "semplificazioni_struttura": semp_strut,
            "livello_lessicale": livello_lex, "livello_morfosintattico": livello_morfo,
            "balbuzie": balbuzie, "tachilalia": tachilalia, "extra_verbale": extra_verbale,
            "bilancio_fonetico": bilancio_fonetico,
        },
        "apprendimento": {
            "lettura_parole": lett_parole, "lettura_nonparole": lett_nonparole,
            "lettura_brano": lett_brano, "scrittura_parole": scr_parole,
            "scrittura_nonparole": scr_nonparole, "scrittura_omofone": scr_omofone,
            "scrittura_dettato_parole": dettato_parole_scr.to_dict("records") if dettato_parole_scr is not None else None,
            "scrittura_dettato_esiti": dettato_esiti_scr,
            "scrittura_omofone_tabella": omofone_scr.to_dict("records") if omofone_scr is not None else None,
            "scrittura_griglia_errori": griglia_errori_scr.to_dict("records") if griglia_errori_scr is not None else None,
            "scrittura_tempo_dettato": tempo_dettato_scr, "scrittura_profilo_prevalente": profilo_prevalente_scr,
            "grafia": grafia, "calcolo_scritto": calc_scritto,
            "enumerazione": enumerazione, "fatti_procedure": fatti_proc,
        },
        "visuo_posturale": {
            "cover_test_lontano": ct_lontano, "cover_test_vicino": ct_vicino,
            "harmon": harmon, "rrd": rrd, "ppc": ppc, "ppa": ppa,
            "nsuco_pursuit": nsuco_pursuit, "nsuco_saccadi": nsuco_saccadi,
            "dem": dem, "kd": kd, "clinical_fusion_test": cft,
            "telebinocular_eseguito": tb_eseguito,
            "telebinocular_serie": tb_serie if tb_eseguito else None,
            "telebinocular_occhiali": tb_occhiali if tb_eseguito else None,
            "telebinocular_collaborazione": tb_collab if tb_eseguito else None,
            "telebinocular_risposte": tb_test_risposte if tb_eseguito else None,
            "postura_eseguito": vp_postura,
            "postura_peso_sx": post_peso_sx if vp_postura else None,
            "postura_peso_dx": post_peso_dx if vp_postura else None,
            "postura_oscillazione_oa": post_oscill_oa if vp_postura else None,
            "postura_oscillazione_oc": post_oscill_oc if vp_postura else None,
            "postura_indice_romberg": post_romberg if vp_postura else None,
            "postura_superficie_ellisse": post_superficie if vp_postura else None,
            "postura_lunghezza_tracciato": post_lng if vp_postura else None,
            "postura_note": post_note_postura if vp_postura else None,
        },
        "miofunzionale": {
            "parto": parto, "allattamento": allattamento, "segnalazioni": mio_flags,
            "postura_orale": postura_orale, "postura_linguale": postura_linguale,
            "deglutizione": deglutizione, "respirazione": respirazione,
        },
        "osteopatico": {
            "gravidanza_parto": gravidanza, "crescita_sviluppo": crescita,
            "patologie": patologie, "indicazione": indicazione,
        },
    }

    if st.button("💾 Salva screening", type="primary", key="scr_salva"):
        if _salva(conn, paz_id, operatore, sezioni, note):
            st.success("Screening salvato.")
            st.session_state["scr_ultima_sezioni"] = sezioni
            st.session_state["scr_ultima_note"] = note

    st.markdown("---")
    st.markdown("#### 📄 Relazione con consigli — generazione e invio")
    st.caption("Disponibile in ogni momento, anche senza salvare prima: usa i dati inseriti qui sopra "
               "(più privacy e questionari già firmati dal paziente). Se l'AI non è disponibile, "
               "genera comunque una relazione semplice basata sui dati.")
    if st.button("✉️ Genera relazione e invia al genitore", key="scr_genera_invia"):
        _genera_e_invia_relazione(conn, paz_id, sezioni, note)

    st.markdown("---")
    try:
        from .ui_relazione_screening import render_relazione
        render_relazione(conn, paz_id,
                         dati_valutazione={"sezioni": sezioni, "note": note},
                         fonte="screening_rapido", kp="scr_rel")
    except Exception as e:
        st.warning(f"Relazione funzionale non disponibile: {e}")

    st.markdown("---")
    st.markdown("#### Storico screening di questo paziente")
    righe = _storico(conn, paz_id)
    if not righe:
        st.caption("Nessuno screening registrato finora.")
    else:
        for r in righe:
            rid, data_s, op, nt = (r.get(k) if hasattr(r, "get") else r[i]
                                    for i, k in enumerate(["id", "data_screening", "operatore", "note"]))
            st.caption(f"📅 {data_s} · {op or '—'} · {nt or ''}")
