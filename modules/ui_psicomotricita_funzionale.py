# -*- coding: utf-8 -*-
"""
Psicomotricità funzionale — percorso guidato a step per l'Analisi Psicomotoria
Funzionale (funzione energetico-affettiva + funzioni operative).
Note libere per area, filtrate per età del paziente, con relazione finale
salvata in Documenti clinici e voce automatica nel Diario clinico.
"""
from __future__ import annotations
import datetime
import io
import streamlit as st

SEZIONI = [
    {
        "chiave": "energetico_affettiva",
        "titolo": "1 · Funzione energetico-affettiva",
        "eta_min": None,
        "guida": [
            "Interesse per l'ambiente: globale, verso una persona, verso un oggetto proposto, "
            "spontaneo verso persone o oggetti (gioco con intenzionalità).",
            "Comunicazione cinesica (postura, gesti, sguardo), prossemica (uso dello spazio) "
            "e paraverbale (tono, ritmo, volume della voce).",
        ],
    },
    {
        "chiave": "aggiustamento_comportamento",
        "titolo": "2 · Aggiustamento — comportamento globale",
        "eta_min": None,
        "guida": [
            "Aggiustamento raggiunto: senso-motorio/percettivo-motorio, impulsivo o autoregolato.",
            "Comportamento: passivo · attivo impulsivo sui compagni/ambiente · attivo ma non "
            "controllato (fatica a fermarsi su richiesta) · attivo e controllato.",
        ],
    },
    {
        "chiave": "tono_fondo",
        "titolo": "3 · Tono di fondo",
        "eta_min": 3,
        "guida": [
            "Paratonie di fondo (assenza di flessibilità tonica) e di azione (frenaggio tonico oltre "
            "una certa ampiezza di movimento).",
            "Attitudine alla distensione: in piedi 10\" occhi aperti/chiusi (dai 4 anni), disteso "
            "10\" occhi aperti/chiusi (dai 3-4 anni).",
            "Ballant, bilanciamento (caduta passiva dei segmenti), estensibilità articolare.",
            "Movimenti passivi guidati (braccio, ginocchio, tronco) e dinamismo respiratorio "
            "(profondità, frequenza, ritmo).",
        ],
    },
    {
        "chiave": "tono_azione",
        "titolo": "4 · Tono d'azione — sincinesie",
        "eta_min": 3,
        "guida": [
            "Sincinesie imitative (si diffondono orizzontalmente, es. mano-mano): fisiologiche fino "
            "a 9 anni, si attenuano fino a sparire verso i 12.",
            "Sincinesie assiali o toniche (asse verticale, es. bocca-mani): poco frequenti, oltre gli "
            "8-9 anni possono essere considerate patologiche.",
        ],
    },
    {
        "chiave": "equilibrio",
        "titolo": "5 · Equilibrio statico e dinamico",
        "eta_min": 4,
        "guida": [
            "Statico: piè pari, un piede, punta di piedi (occhi aperti/chiusi per età), linea a terra, "
            "asse di equilibrio, scale, percorso sinuoso, resistenza alla spinta.",
            "Parametri per età: 4a occhi aperti/mani sui fianchi · 5a percorso su riga, occhi chiusi · "
            "6a un piede/altro · 7a stesse prove occhi chiusi, asse · 8-9a mani dietro la schiena, "
            "punta di piedi · 10-11a flessione busto occhi chiusi.",
            "Dinamico: correre/camminare e stabilizzarsi (cerchio, asse), fermarsi al segnale, "
            "saltare e riequilibrarsi.",
        ],
    },
    {
        "chiave": "oculo_manuale",
        "titolo": "6 · Coordinazione oculo-manuale e sistema visivo",
        "eta_min": 2,
        "guida": [
            "Afferrare palla/pallina (quale mano), lanciare con precisione tra cerchi a distanza variata.",
            "Parametri: 2a prende palla rotolata a due mani · 4a afferra palla a due mani · 5a lanci "
            "di precisione · 6-7a afferra pallina con una mano (lateralizzazione).",
            "Analisi visiva: sguardo destra/sinistra senza muovere la testa, convergenza (pennarello "
            "verso il naso), inseguimento orizzontale e verticale (movimenti saccadici).",
        ],
    },
    {
        "chiave": "oculo_segmentaria",
        "titolo": "7 · Coordinazione oculo-segmentaria",
        "eta_min": 3,
        "guida": [
            "Calciare/dirigere la palla verso un punto preciso da circa 3 metri (quale piede, dopo "
            "6-7 anni si chiede quale).",
            "Respingere la palla con la parte del corpo richiesta dall'operatore.",
        ],
    },
    {
        "chiave": "dissociazione_movimenti",
        "titolo": "8 · Dissociazione dei movimenti",
        "eta_min": 2,
        "guida": [
            "2a battere piedi/mani alternativamente · 3-4a mano omolaterale sulla gamba che avanza · "
            "5a mano opposta · 6a mani in alternanza con i piedi (crociato) · 7-8a roteare le mani in "
            "sensi opposti · 9-10a roteare le braccia in sensi opposti.",
        ],
    },
    {
        "chiave": "coordinazione_dinamica",
        "titolo": "9 · Coordinazione dinamica generale",
        "eta_min": 3,
        "guida": [
            "3-5a salto libero e con consegna (cerchi a 20cm) · 6-7a cerchi a 40cm, salto elastico "
            "30cm · 7-8a cerchi 50cm, elastico 40cm · 8-9a cerchi 60cm, elastico 50cm.",
            "Percorso di agilità (salti, equilibrio, lanci, passaggi quadrupedici): mostrato fino a 6 "
            "anni, spiegato verbalmente 6-8, proposto graficamente da 9, memorizzato da 10-11.",
        ],
    },
    {
        "chiave": "coordinazione_fine",
        "titolo": "10 · Coordinazione fine mano e dita",
        "eta_min": 3,
        "guida": [
            "Prensione: afferrare/infilare perle (3a solo mano preferita, dopo 4-5a con entrambe).",
            "Ritaglio: 4-6a ritagliare all'interno di due righe, dopo 7-8a lungo le linee.",
            "Dissociazione dita: opposizione al pollice (3a), abduzione pollice (4a), biscottare le "
            "dita (4a), pianotage (5a, anulare più difficile dopo 7a), modellare con filo (6a).",
        ],
    },
    {
        "chiave": "dominanza_laterale",
        "titolo": "11 · Dominanza laterale",
        "eta_min": 2,
        "guida": [
            "Dominanza spontanea/tonica (neurologica) vs dominanza di utilizzazione (prassica).",
            "Manuale: mimo, lanci di forza/precisione, appallottolare, pontillage, scrittura con "
            "l'una e l'altra mano.",
            "Piede: calciare, schiacciare, raccogliere biglie con le dita, infilare i pantaloni.",
            "Oculare: foro su cartoncino, mira col dito/penna; dopo 7a prove di lettura a occhio coperto.",
            "Acustica: ascoltare da una porta, orologio all'orecchio, conchiglia, gesto di ascolto.",
        ],
    },
    {
        "chiave": "percezione_tempo_spazio",
        "titolo": "12 · Percezione tempo, ritmo, spazio, spazio-tempo",
        "eta_min": 3,
        "guida": [
            "Tempo: riprodurre cadenze lento/moderato/veloce — 3-4a con vista sulle mani, 5-6a solo "
            "uditivo, dopo 6a riproduzione grafica.",
            "Ritmo: riprodurre strutture ritmiche battendo le mani — 5a prime 3 strutture, 6a prime "
            "8, 7a tutte.",
            "Spazio: topologico (dopo 3a: dentro/fuori/sopra/sotto), euclideo (dopo 4a: forme "
            "geometriche), rappresentato (5-6a disegno copiato, 7a a memoria).",
            "Orientamento: egocentrico (avanti/indietro/lato), spaziale con destra/sinistra (dopo 8a "
            "anche su altre persone, lettura di un percorso grafico).",
            "Spazio-tempo: percorso motorio in sequenza su indicazioni verbali (5-6a), destra/sinistra "
            "rispetto a un riferimento (6-7a), riempimento del tempo e successione temporale (6-7a: "
            "giorno/notte, giorni, mesi, stagioni).",
        ],
    },
    {
        "chiave": "schema_corporeo",
        "titolo": "13 · Percezione propriocettiva e schema corporeo",
        "eta_min": 3,
        "guida": [
            "Riconoscimento delle parti del corpo e riconoscimento digitale (mano visibile/non "
            "visibile, due dita simultanee).",
            "Imitazione di gesti, posture singole e serie complesse con tutto il corpo (aggiustamento "
            "speculare o orientato).",
            "Rappresentazione grafica della figura umana (eretta, in movimento, sdraiata).",
            "Lateralizzazione: riconoscere le due metà corporee, alzare mano/toccare piede "
            "sinistro-destro, girarsi a sinistra/destra.",
        ],
    },
]

TIPO_DOCUMENTO = "Esame funzionale"


def _eta_anni(dn) -> int | None:
    if not dn:
        return None
    try:
        d = datetime.date.fromisoformat(str(dn)[:10])
    except Exception:
        return None
    oggi = datetime.date.today()
    return oggi.year - d.year - ((oggi.month, oggi.day) < (d.month, d.day))


def _sezioni_pertinenti(eta):
    if eta is None:
        return SEZIONI
    return [s for s in SEZIONI if s["eta_min"] is None or eta >= s["eta_min"]]


def _ensure_table(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS valutazioni_psicomotorie (
                id BIGSERIAL PRIMARY KEY,
                studio_id BIGINT,
                paziente_id BIGINT NOT NULL,
                eta_paziente INT,
                note_sezioni JSONB,
                riepilogo TEXT,
                creato_il TIMESTAMP DEFAULT now()
            );
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _studio_id():
    return st.session_state.get("studio_id", 1)


def _componi_relazione(paziente_nome, eta, note, sezioni_mostrate):
    righe = [f"ANALISI PSICOMOTORIA FUNZIONALE — {paziente_nome}",
             f"Età al momento della valutazione: {eta if eta is not None else 'n.d.'} anni",
             f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", ""]
    for s in sezioni_mostrate:
        testo = (note.get(s["chiave"]) or "").strip()
        if testo:
            righe.append(s["titolo"])
            righe.append(testo)
            righe.append("")
    return "\n".join(righe).strip()


def _salva_documento_pdf(conn, paz_id, studio_id, nome_file, corpo_testo, paziente_nome):
    try:
        from .pdf_templates import genera_carta_intestata
        professionista = st.session_state.get("utente_nome") or "Studio The Organism"
        pdf_bytes = genera_carta_intestata(
            professionista, "Analisi Psicomotoria Funzionale",
            paziente_nome, datetime.date.today().strftime("%d/%m/%Y"),
            "Analisi Psicomotoria Funzionale", corpo_testo=corpo_testo,
        )
    except Exception:
        pdf_bytes = None

    if not pdf_bytes:
        return None, None

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO documenti_clinici
                (paziente_id, studio_id, tipo, nome_file, mime, dati, note, estratto)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
        """, (paz_id, studio_id, TIPO_DOCUMENTO, nome_file, "application/pdf",
              pdf_bytes, "Analisi Psicomotoria Funzionale", corpo_testo[:2000]))
        nuovo_id = cur.fetchone()[0]
        conn.commit()
        return nuovo_id, pdf_bytes
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return None, pdf_bytes
    finally:
        try: cur.close()
        except Exception: pass


def render_psicomotricita_funzionale(conn, paz_id=None, paziente=None):
    st.header("🤸 Psicomotricità funzionale")
    st.caption("Analisi Psicomotoria Funzionale: funzione energetico-affettiva e funzioni operative "
               "(aggiustamento, tono, equilibrio, coordinazione, dominanza laterale, percezione, "
               "schema corporeo). Percorso guidato a step, con note libere per area.")

    if not paz_id:
        st.info("Seleziona un paziente per iniziare la valutazione.")
        return

    if paziente is None:
        try:
            from .paziente_attivo import paziente_attivo_record
            paziente = paziente_attivo_record()
        except Exception:
            paziente = None

    try:
        _ensure_table(conn)
    except Exception as e:
        st.error(f"Impossibile preparare la tabella: {e}")
        return

    dn = (paziente or {}).get("data_nascita") if paziente else None
    eta = _eta_anni(dn)
    paziente_nome = ""
    if paziente:
        paziente_nome = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()

    sezioni = _sezioni_pertinenti(eta)
    if eta is not None:
        st.caption(f"Età del paziente: {eta} anni — mostrate {len(sezioni)} aree su {len(SEZIONI)} "
                   "pertinenti a questa fascia d'età.")
    else:
        st.warning("Data di nascita del paziente non disponibile: mostrate tutte le aree, "
                   "senza filtro per età.")

    chiave_note = f"psico_note_{paz_id}"
    chiave_step = f"psico_step_{paz_id}"
    if chiave_note not in st.session_state:
        st.session_state[chiave_note] = {}
    if chiave_step not in st.session_state:
        st.session_state[chiave_step] = 0

    note = st.session_state[chiave_note]
    step = st.session_state[chiave_step]
    n_step = len(sezioni) + 1  # +1 per la schermata di riepilogo finale
    step = max(0, min(step, n_step - 1))
    st.session_state[chiave_step] = step

    st.progress((step + 1) / n_step)

    if step < len(sezioni):
        sezione = sezioni[step]
        st.subheader(sezione["titolo"])
        for punto in sezione["guida"]:
            st.markdown(f"- {punto}")
        note[sezione["chiave"]] = st.text_area(
            "Note dell'osservazione", value=note.get(sezione["chiave"], ""),
            height=140, key=f"psico_txt_{paz_id}_{sezione['chiave']}")

        c1, c2, c3 = st.columns([1, 1, 3])
        if step > 0 and c1.button("◀ Indietro", key=f"psico_prev_{paz_id}"):
            st.session_state[chiave_step] = step - 1
            st.rerun()
        if c2.button("Avanti ▶", type="primary", key=f"psico_next_{paz_id}"):
            st.session_state[chiave_step] = step + 1
            st.rerun()
        c3.caption(f"Area {step + 1} di {len(sezioni)}")
    else:
        st.subheader("📝 Riepilogo e salvataggio")
        compilate = [s for s in sezioni if (note.get(s["chiave"]) or "").strip()]
        if not compilate:
            st.info("Nessuna area compilata ancora: torna indietro per aggiungere osservazioni.")
        else:
            for s in compilate:
                with st.expander(s["titolo"], expanded=False):
                    st.write(note[s["chiave"]])

        c1, c2 = st.columns([1, 2])
        if c1.button("◀ Indietro", key=f"psico_prev_final_{paz_id}"):
            st.session_state[chiave_step] = len(sezioni) - 1
            st.rerun()

        if c2.button("✅ Genera e salva relazione", type="primary",
                     use_container_width=True, key=f"psico_save_{paz_id}", disabled=not compilate):
            corpo = _componi_relazione(paziente_nome or f"Paziente #{paz_id}", eta, note, sezioni)
            studio_id = _studio_id()

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO valutazioni_psicomotorie
                        (studio_id, paziente_id, eta_paziente, note_sezioni, riepilogo)
                    VALUES (%s,%s,%s,%s,%s) RETURNING id;
                """, (studio_id, paz_id, eta,
                      __import__("json").dumps(note), corpo))
                valutazione_id = cur.fetchone()[0]
                conn.commit()
            except Exception as e:
                try: conn.rollback()
                except Exception: pass
                st.error(f"Errore nel salvataggio della valutazione: {e}")
                valutazione_id = None
            finally:
                try: cur.close()
                except Exception: pass

            nome_file = f"analisi-psicomotoria-{paz_id}-{datetime.date.today().isoformat()}.pdf"
            _, pdf_bytes = _salva_documento_pdf(conn, paz_id, studio_id, nome_file, corpo,
                                                 paziente_nome or f"Paziente #{paz_id}")

            try:
                from .diario_clinico import registra_voce_diario
                if valutazione_id:
                    autore = st.session_state.get("utente_nome") or st.session_state.get("username")
                    registra_voce_diario(
                        conn, studio_id, paz_id, "valutazione",
                        "psicomotricita_funzionale", valutazione_id,
                        riassunto="Analisi Psicomotoria Funzionale completata.",
                        testo=corpo, titolo="Analisi Psicomotoria Funzionale", autore=autore)
            except Exception:
                pass

            st.success("Relazione salvata. Trovi il PDF in Documenti clinici e la voce nel Diario "
                       "clinico del paziente." if pdf_bytes else
                       "Valutazione salvata (il PDF non è stato generato: verifica i template).")
            if pdf_bytes:
                st.download_button("⬇️ Scarica il PDF", data=pdf_bytes, file_name=nome_file,
                                   mime="application/pdf", key=f"psico_dl_{paz_id}")
