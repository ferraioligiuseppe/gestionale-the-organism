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

AREE_LAVORO_PSICO = ["Tono ed equilibrio", "Coordinazione dinamica generale",
                     "Coordinazione fine mano-dita", "Dominanza laterale",
                     "Percezione tempo/ritmo", "Percezione spaziale",
                     "Schema corporeo", "Aggiustamento/comportamento", "Altro"]
RISPOSTA_PSICO = ["—", "🟢 Buona", "🟡 Parziale", "🔴 Scarsa"]
STATO_OB_PSICO = ["🟦 In corso", "🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"]


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

    if not paz_id:
        st.info("Seleziona un paziente per iniziare.")
        return

    if paziente is None:
        try:
            from .paziente_attivo import paziente_attivo_record
            paziente = paziente_attivo_record()
        except Exception:
            paziente = None

    try:
        _ensure_table(conn)
        _assicura_tabella_sedute(conn)
        _assicura_tabella_obiettivi(conn)
    except Exception as e:
        st.error(f"Impossibile preparare le tabelle: {e}")
        return

    modo = st.radio("Sezione", ["📋 Valutazione (Analisi Psicomotoria Funzionale)",
                                "📅 Diario sedute", "🎯 Obiettivi & monitoraggio"],
                    horizontal=True, key=f"psico_modo_{paz_id}")
    if modo == "📅 Diario sedute":
        _render_diario_sedute(conn, paz_id)
        return
    if modo == "🎯 Obiettivi & monitoraggio":
        _render_obiettivi(conn, paz_id)
        return

    st.caption("Analisi Psicomotoria Funzionale: funzione energetico-affettiva e funzioni operative "
               "(aggiustamento, tono, equilibrio, coordinazione, dominanza laterale, percezione, "
               "schema corporeo). Percorso guidato a step, con note libere per area.")

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


# ═══════════════════════════════════════════════════════════════════════
#  DIARIO SEDUTE
# ═══════════════════════════════════════════════════════════════════════
def _assicura_tabella_sedute(conn):
    cur = conn.cursor()
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS psico_sedute(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data_seduta DATE, numero INT,
            aree TEXT, obiettivo TEXT, attivita TEXT,
            risposta TEXT, compiti TEXT, note TEXT,
            creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        try: cur.close()
        except Exception: pass


def _render_diario_sedute(conn, paz_id):
    st.caption("Quaderno di lavoro: registra ogni seduta di psicomotricità funzionale.")

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM psico_sedute WHERE paziente_id=%s", (paz_id,))
        n_fatte = cur.fetchone()[0] or 0
    except Exception:
        n_fatte = 0
        try: conn.rollback()
        except Exception: pass

    with st.expander("➕ Nuova seduta", expanded=True):
        with st.form("psico_seduta", clear_on_submit=True):
            c1, c2 = st.columns(2)
            data_s = c1.date_input("Data seduta", value=datetime.date.today(), key="psico_sd_data")
            numero = c2.number_input("N° seduta", min_value=1, step=1,
                                     value=int(n_fatte) + 1, key="psico_sd_num")
            aree = st.multiselect("Aree di lavoro", AREE_LAVORO_PSICO, key="psico_sd_aree")
            obiettivo = st.text_input("Obiettivo della seduta", key="psico_sd_ob")
            attivita = st.text_area("Attività svolte", height=90, key="psico_sd_att")
            c3, c4 = st.columns(2)
            risposta = c3.selectbox("Risposta del paziente", RISPOSTA_PSICO, key="psico_sd_risp")
            compiti = c4.text_input("Compiti a casa", key="psico_sd_comp")
            note = st.text_area("Note", height=70, key="psico_sd_note")
            if st.form_submit_button("💾 Salva seduta", type="primary"):
                if _salva_seduta(conn, paz_id, data_s, numero, aree, obiettivo,
                                 attivita, risposta, compiti, note):
                    st.success(f"Seduta n° {numero} salvata.")
                    st.rerun()
                else:
                    st.error("Salvataggio non riuscito.")

    st.markdown(f"#### Sedute registrate ({n_fatte})")
    _elenco_sedute(conn, paz_id)


def _salva_seduta(conn, paz_id, data_s, numero, aree, ob, att, risp, comp, note) -> bool:
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO psico_sedute(paziente_id, data_seduta, numero,
            aree, obiettivo, attivita, risposta, compiti, note)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, data_s, int(numero), ", ".join(aree), ob, att, risp, comp, note))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        try: cur.close()
        except Exception: pass


def _elenco_sedute(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, data_seduta, numero, aree, obiettivo, attivita,
            risposta, compiti, note FROM psico_sedute
            WHERE paziente_id=%s ORDER BY data_seduta DESC, numero DESC""", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try: conn.rollback()
        except Exception: pass
    if not righe:
        st.caption("Nessuna seduta registrata per ora.")
        return
    for rid, ds, num, aree, ob, att, risp, comp, note in righe:
        ds_str = ds.strftime("%d/%m/%Y") if ds else ""
        titolo = f"**Seduta n° {num}** — {ds_str}"
        if risp and risp != "—":
            titolo += f"  ·  {risp}"
        st.markdown(titolo)
        if aree:
            st.caption("Aree: " + aree)
        if ob:
            st.markdown(f"🎯 {ob}")
        if att:
            st.markdown(att)
        det = []
        if comp:
            det.append(f"📝 Compiti: {comp}")
        if note:
            det.append(note)
        if det:
            st.caption(" · ".join(det))
        if st.button("🗑 Elimina", key=f"psico_sd_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM psico_sedute WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try: conn.rollback()
                except Exception: pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  OBIETTIVI & MONITORAGGIO
# ═══════════════════════════════════════════════════════════════════════
def _assicura_tabella_obiettivi(conn):
    cur = conn.cursor()
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS psico_obiettivi(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            area TEXT, descrizione TEXT,
            baseline INT, attuale INT, target INT,
            stato TEXT, data_inizio DATE, data_rivalut DATE,
            note TEXT, creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        try: cur.close()
        except Exception: pass


def _render_obiettivi(conn, paz_id):
    st.caption("Definisci gli obiettivi terapeutici e aggiornane il livello nel tempo "
               "(scala 0–10). Alla chiusura, l'esito confluisce nell'apprendimento PNEV.")

    with st.expander("➕ Nuovo obiettivo", expanded=True):
        with st.form("psico_ob_new", clear_on_submit=True):
            area = st.selectbox("Area", AREE_LAVORO_PSICO, key="psico_ob_area")
            descr = st.text_input("Obiettivo (in positivo, osservabile)",
                                  placeholder="es. Equilibrio statico su un piede a occhi chiusi",
                                  key="psico_ob_descr")
            c1, c2, c3 = st.columns(3)
            baseline = c1.slider("Livello iniziale", 0, 10, 2, key="psico_ob_base")
            target = c2.slider("Target", 0, 10, 8, key="psico_ob_targ")
            data_riv = c3.date_input("Rivalutazione prevista",
                                     value=datetime.date.today() + datetime.timedelta(weeks=10),
                                     key="psico_ob_riv")
            if st.form_submit_button("💾 Crea obiettivo", type="primary"):
                if descr.strip():
                    if _salva_obiettivo(conn, paz_id, area, descr, baseline, target, data_riv):
                        st.success("Obiettivo creato.")
                        st.rerun()
                    else:
                        st.error("Salvataggio non riuscito.")
                else:
                    st.warning("Scrivi l'obiettivo.")

    st.markdown("#### Obiettivi del paziente")
    _elenco_obiettivi(conn, paz_id)


def _salva_obiettivo(conn, paz_id, area, descr, baseline, target, data_riv) -> bool:
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO psico_obiettivi(paziente_id, area, descrizione,
            baseline, attuale, target, stato, data_inizio, data_rivalut)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, area, descr, int(baseline), int(baseline), int(target),
             "🟦 In corso", datetime.date.today(), data_riv))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        try: cur.close()
        except Exception: pass


def _elenco_obiettivi(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, area, descrizione, baseline, attuale, target,
            stato, data_inizio, data_rivalut FROM psico_obiettivi
            WHERE paziente_id=%s ORDER BY creato DESC""", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try: conn.rollback()
        except Exception: pass
    if not righe:
        st.caption("Nessun obiettivo definito per ora.")
        return
    for rid, area, descr, base, attuale, target, stato, dini, driv in righe:
        st.markdown(f"**{descr}**  ·  _{area}_")
        rng = max(1, (target or 10) - (base or 0))
        prog = min(1.0, max(0.0, ((attuale or 0) - (base or 0)) / rng))
        st.progress(prog, text=f"{stato}  ·  {attuale}/{target} (partenza {base})")
        c1, c2, c3 = st.columns([2, 2, 1])
        nuovo = c1.slider("Livello attuale", 0, 10, int(attuale or 0), key=f"psico_ob_upd_{rid}")
        nuovo_stato = c2.selectbox("Stato", STATO_OB_PSICO,
                                   index=STATO_OB_PSICO.index(stato) if stato in STATO_OB_PSICO else 0,
                                   key=f"psico_ob_st_{rid}")
        with c3:
            st.write("")
            st.write("")
            if st.button("💾", key=f"psico_ob_save_{rid}", help="Aggiorna"):
                _aggiorna_obiettivo(conn, rid, nuovo, nuovo_stato, paz_id, descr, area)
                st.rerun()
        if driv:
            st.caption(f"Rivalutazione prevista: {driv.strftime('%d/%m/%Y') if hasattr(driv,'strftime') else driv}")
        if st.button("🗑 Elimina", key=f"psico_ob_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM psico_obiettivi WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try: conn.rollback()
                except Exception: pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)


def _aggiorna_obiettivo(conn, rid, attuale, stato, paz_id, descr, area):
    cur = conn.cursor()
    try:
        cur.execute("UPDATE psico_obiettivi SET attuale=%s, stato=%s WHERE id=%s",
                    (int(attuale), stato, rid))
        conn.commit()
        if stato in ("🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"):
            esito = {"🟢 Raggiunto": "🟢 Migliorato", "🟡 Parziale": "🟡 Stabile / fermo",
                     "⏸️ Sospeso": "⚪ Non valutabile"}.get(stato, "⚪ Non valutabile")
            try:
                cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
                    id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
                    data TIMESTAMP DEFAULT NOW(),
                    intervento TEXT, esito TEXT, note TEXT);""")
                cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                            "VALUES(%s,%s,%s,%s)",
                            (paz_id, f"Psicomotricità funzionale — {area}: {descr}", esito,
                             "Da obiettivo psicomotorio"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        try: cur.close()
        except Exception: pass
