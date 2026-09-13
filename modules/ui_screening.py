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
    """Relazione semplice senza AI — sempre disponibile anche se l'AI non
    è configurata o non risponde."""
    righe = [f"Risultati screening — {nome_completo}", ""]
    etichette = {
        "linguaggio": "Linguaggio", "apprendimento": "Apprendimento",
        "visuo_posturale": "Visuo-posturale", "miofunzionale": "Miofunzionale",
        "osteopatico": "Osteopatico",
    }
    for chiave, titolo in etichette.items():
        dati = {k: v for k, v in (sezioni.get(chiave) or {}).items() if v not in (None, "", [], False)}
        if not dati:
            continue
        righe.append(f"## {titolo}")
        for k, v in dati.items():
            righe.append(f"- {k.replace('_',' ').capitalize()}: {v}")
        righe.append("")
    if note:
        righe.append(f"Note dell'operatore: {note}")
        righe.append("")
    righe.append("Questo screening è una prima rilevazione orientativa, non una diagnosi. "
                  "Per un approfondimento vi consigliamo di prenotare una valutazione PNEV completa.")
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
                f"Scrivi una relazione sintetica e comprensibile per un genitore, a partire dai risultati "
                f"di uno screening rapido multidisciplinare svolto su {nome_completo}.\n\n"
                f"DATI RACCOLTI (per area):\n"
                f"Linguaggio: {sezioni.get('linguaggio')}\n"
                f"Apprendimento: {sezioni.get('apprendimento')}\n"
                f"Visuo-posturale: {sezioni.get('visuo_posturale')}\n"
                f"Miofunzionale: {sezioni.get('miofunzionale')}\n"
                f"Osteopatico: {sezioni.get('osteopatico')}\n"
                f"Note dell'operatore: {note or '—'}\n\n"
                f"Questionari già compilati dalla famiglia:\n{q_riassunto}\n\n"
                f"Scrivi in italiano semplice e diretto, senza tecnicismi non spiegati. Per ciascuna area "
                f"segnala se i risultati sono nella norma o se emerge un'area da approfondire, e chiudi con "
                f"3-5 consigli pratici concreti da poter già iniziare a casa. Non scrivere una diagnosi: "
                f"è uno screening orientativo, non una valutazione clinica completa."
            )
            sistema = ("Sei un assistente clinico dello Studio The Organism (Metodo PNEV). "
                       "Scrivi relazioni chiare per genitori non specialisti, mai allarmistiche, "
                       "sempre orientate a un'azione concreta successiva (valutazione o consigli pratici).")
            with st.spinner("Genero la relazione con l'AI…"):
                bozza = genera_testo(prompt, sistema)
            if not bozza.startswith("⚠️"):
                testo = bozza
    except Exception:
        pass

    if testo is None:
        st.info("AI non disponibile in questo momento: uso una relazione semplice basata sui dati inseriti.")
        testo = _relazione_template(nome_completo, sezioni, note)

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
                        testo_finale + "\n\n— Studio The Organism")
            for staff in ("aps@theorganism.com", "dr.ferraioligiuseppe@gmail.com"):
                try:
                    invia_email(staff, f"[Screening] Relazione inviata — {nome_completo}", testo_finale)
                except Exception:
                    pass
            st.success(f"Relazione inviata a {email_dest}.")
        except Exception as e:
            st.error(f"Errore invio: {e}")


# Testi IReST (International Reading Speed Texts, versione italiana) — 10 brani
# calibrati e omogenei per lunghezza, con norme di riferimento (tempo/velocità)
_TESTI_IREST = [
    {"nome": "Topi", "testo": "In una cittadina c'era un negozio di frutta e verdura che si trovava sopra una grande cantina. Ogni notte i topi uscivano dalla cantina ed entravano nel negozio, dove mangiavano mele e pere, uva e noci, senza risparmiare nemmeno le patate o altre verdure. Niente nel negozio si salvava da quei molesti roditori. Alla sera, finché c'erano rumori per la strada e le auto circolavano, i topi se ne restavano buoni in cantina. Ma appena il vecchio orologio sulla torre del palazzo comunale suonava la mezzanotte, e calava il silenzio sulla città, i topi uscivano a frotte e si gettavano sulla frutta, con dei veri e propri festini i cui resti riempivano il proprietario di disperazione quando, alla mattina, entrava in negozio. Il fruttivendolo aveva provato in vari modi a difendersi dai topi. All'inizio aveva messo delle trappole.", "parole": 138, "tempo_medio": "46.4 ± 5.2 s", "velocita_media": "181 ± 24 parole/min"},
    {"nome": "Castoro", "testo": "Il castoro è un ottimo nuotatore, che in acqua può raggiungere la velocità di dieci chilometri all'ora. Per proteggersi dal freddo è ricoperto da uno spesso strato di grasso e da una pelle con migliaia di peli. Grazie ai suoi grandi polmoni può restare sott'acqua senza problemi per oltre venti minuti. Il castoro è in grado di abbattere gli alberi ed è anche un abile costruttore di dighe. Per far cadere un albero rode il tronco in modo da lasciare solo una piccola giuntura tra la parte superiore e quella inferiore: quando il legno è abbastanza sottile e il castoro è stanco, sarà il vento a completare il lavoro. I rami più piccoli vengono poi tagliati e ammucchiati vicino alla tana, che si trova di solito su un isolotto. I rami più grandi, invece, vengono selezionati accuratamente e sono utilizzati per fabbricare le dighe.", "parole": 144, "tempo_medio": "42.6 ± 5.1 s", "velocita_media": "206 ± 29 parole/min"},
    {"nome": "Alberi", "testo": "Gli alberi crescono praticamente ovunque, tranne che tra i ghiacci perenni, sulle montagne più alte o nei deserti. Se un terreno viene abbandonato per un certo tempo, prima o poi inizieranno a crescere degli alberi. Dapprima la terra si ricopre di piante più basse. Crescono poi dei cespugli, che con la loro ombra fanno morire la maggior parte delle altre piante. Dopo un po', iniziano a crescere gli alberi. Quando diventano grandi, la loro ombra copre i cespugli, facendone morire una parte. È così che nel tempo si forma una foresta. Molti alberi crescono lentamente e possono diventare anche molto vecchi. Quando muoiono gli alberi più vecchi, gli altri più giovani prendono il loro posto. La foresta è un habitat che può rimanere stabile per molto tempo. Il clima determina il tipo di alberi che si possono trovare in un'area.", "parole": 140, "tempo_medio": "43.8 ± 5 s", "velocita_media": "194 ± 24 parole/min"},
    {"nome": "Preda", "testo": "Tutti gli animali che si cibano di altri animali hanno il problema di come catturare le loro prede. Alcuni le seguono e le attaccano, altri rimangono fermi aspettando che una vittima gli passi vicino. Un sistema molto diffuso per procurarsi cibo senza troppe difficoltà è quello di costruire una trappola. I ragni sono l'esempio più noto di animali che ne catturano altri mediante trappole. Le loro tele appiccicose sono così fini da risultare quasi invisibili: di solito un insetto se ne accorge solo quando vi resta impigliato, così che il ragno non deve fare altro che avvicinarsi. L'insetto viene mangiato direttamente sul posto oppure viene avvolto con filamenti appiccicosi per essere consumato in seguito. Altre creature che vivono tra le rocce o sui fondali marini si cibano di animaletti e piante che trovano nell'acqua.", "parole": 134, "tempo_medio": "44.1 ± 5.5 s", "velocita_media": "185 ± 26 parole/min"},
    {"nome": "Deserto", "testo": "Nelle zone calde e aride le piante e gli animali devono adattarsi all'ambiente. Diverse piante superano periodi di siccità in forma di semi, che possono rimanere sotto terra per anni prima che la pioggia cada facendoli germogliare. Quando ciò accade, le piante crescono rapidamente, producendo fiori e semi da cui nascerà la generazione successiva. Lo stesso accade ad alcuni animali: ad esempio ci sono rane che si seppelliscono sotto terra formando una capsula che le protegge dal secco, ed escono in superficie solo quando cade la prima pioggia; in questo periodo in cui l'acqua è disponibile riescono a riprodursi e far crescere i piccoli. Molte piante del deserto si sono adattate alla siccità in altri modi. Alcune hanno lunghe radici che assorbono l'acqua da un'area molto ampia o che scendono nel suolo a grande profondità.", "parole": 135, "tempo_medio": "43.9 ± 5.4 s", "velocita_media": "188 ± 26 parole/min"},
    {"nome": "Veleno", "testo": "Una delle principali minacce per la vita di animali e piante è il rischio di essere mangiati. Alcuni animali risolvono il problema mimetizzandosi, altri nascondendosi. Parecchi riescono a volare via, mentre altri scappano correndo davanti ai loro nemici. Le piante, come è noto, non sono capaci di correre: esse riescono a proteggersi in altri modi, ad esempio coprendosi di spine o con una robusta scorza. Altre piante, ma anche molti animali, si proteggono con il veleno, che non deve essere necessariamente mortale, ma deve solo impedire ad altri animali di ingerirli. Alcuni animali si difendono semplicemente assomigliando ad altri che contengono sostanze velenose. Nel regno animale, un colore particolarmente intenso segnala di solito che l'animale non è commestibile e ciò è sufficiente per scoraggiare eventuali predatori.", "parole": 126, "tempo_medio": "44.7 ± 6.3 s", "velocita_media": "174 ± 29 parole/min"},
    {"nome": "Isola", "testo": "Si chiamano 'isole' le aree di terra circondate dal mare su tutti i lati. Le isole si possono formare da vulcani sorti dal fondo del mare, oppure in seguito a innalzamenti o abbassamenti del livello delle acque. Molte isole si sono formate alla fine dell'ultima era glaciale: il ghiaccio, sciogliendosi in acqua, ha alzato il livello dei mari, che hanno così invaso vaste aree di terre costiere, lasciando scoperti solo i punti più alti, che oggi emergono come isole. Gli animali e le piante che riescono in qualche modo a raggiungere un'isola remota di solito non possono più lasciarla. Se vogliono sopravvivere devono adattarsi molto rapidamente al nuovo ambiente. Le creature native di un'isola rischiano sempre di estinguersi quando arrivano nuovi animali o quando gli esseri umani iniziano a interferire con il loro habitat.", "parole": 134, "tempo_medio": "42.5 ± 5.8 s", "velocita_media": "193 ± 29 parole/min"},
    {"nome": "Ragni", "testo": "In passato si credeva che i ragni fossero capaci di proteggersi in qualche modo dalla sostanza appiccicosa di cui sono fatte le ragnatele, mentre le mosche e gli altri insetti fossero privi di tale protezione. Ricerche più recenti hanno però dimostrato che ciò non è vero: anche un ragno resterebbe prigioniero della sua rete se non usasse uno stratagemma. I ragni infatti producono due tipi di filamento. Prima costruiscono una rete di fili non appiccicosi. Quando questa è finita, il ragno vi tesse sopra il materiale vischioso. Solo questa seconda rete riesce a catturare gli insetti che vi cadono. Per non restare lui stesso impigliato, il ragno lascia alcune parti della tela senza la sostanza vischiosa. Queste aree sono posizionate in modo che il ragno possa raggiungere ogni punto della ragnatela senza rimanere invischiato.", "parole": 134, "tempo_medio": "43.4 ± 5.2 s", "velocita_media": "188 ± 27 parole/min"},
    {"nome": "Inverno", "testo": "Gli animali e le piante che vivono in zone a clima freddo o temperato devono trovare modi per superare i mesi invernali. Molte piante passano l'inverno sotto forma di semi che in primavera germoglieranno per dare nuove piante. Altre piante lasciano seccare le parti sopra il livello del suolo, per formare nuovi getti quando l'aria si fa più mite in primavera. Molti alberi e cespugli perdono le foglie in autunno e trascorrono un periodo di riposo durante l'inverno. Gli animali, dovendo muoversi sempre, consumano molta più energia delle piante. La maggior parte di loro non cambia significativamente le proprie abitudini durante l'inverno. Altri però devono mettere in atto varie strategie per non morire congelati. Ad esempio, alcuni uccelli risolvono il problema migrando in autunno verso zone più piacevoli nel Sud del mondo.", "parole": 132, "tempo_medio": "43.5 ± 6.8 s", "velocita_media": "187 ± 34 parole/min"},
    {"nome": "Colori", "testo": "I colori di un animale o una pianta di solito hanno una funzione. Dato che negli uccelli la percezione visiva è ben sviluppata, in molte specie i maschi hanno un aspetto variopinto per piacere di più alle femmine. Anche le piante spesso producono fiori colorati per attrarre gli insetti, attraverso i quali avviene la loro riproduzione. Alcuni animali velenosi o disgustosi portano colori sgargianti come avvertimento. Le vespe, ad esempio, si riconoscono facilmente per le strisce gialle e nere, e gli uccelli imparano presto che verranno punti se attaccano insetti con queste strisce. Ma non tutti gli animali colorati sono velenosi: alcune mosche, infatti, imitano le vespe pur non avendo il pungiglione. Altri animali si difendono rendendosi quasi invisibili, mimetizzandosi tra le foglie, il terreno o le rocce su cui vivono.", "parole": 131, "tempo_medio": "44.7 ± 6.4 s", "velocita_media": "179 ± 27 parole/min"},
]
_PROBLEMI_CALCOLO = ["7 + 5 =", "12 − 4 =", "6 × 3 =", "20 ÷ 4 =", "15 + 8 ="]


def render_screening(conn=None, paz_id=None, paziente=None) -> None:
    st.header("🩺 Screening rapido")
    st.caption("Scheda breve multi-area per una prima rilevazione — evento, scuola, "
               "\"Giornata del benessere\". Per il percorso clinico completo usa "
               "Valutazione PNEV.")
    st.info("📺 **Doppio monitor:** apri questa pagina anche sul secondo schermo rivolto "
            "verso il bambino — dove previsto trova qui sotto lo stimolo da leggere/guardare, "
            "identico a quello che vedi tu.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    operatore = st.text_input("Operatore", key="scr_operatore")

    t_ling, t_appr, t_vp, t_mio, t_osteo = st.tabs(
        ["🗣️ Linguaggio", "📚 Apprendimento", "👁️ Visuo-posturale",
         "💆 Miofunzionale", "🦴 Osteopatico"])

    with t_ling:
        ling_semp = st.checkbox("Eseguito — Semplificazioni fonologiche", key="scr_ling_semp_on")
        semp_sist = semp_strut = []
        if ling_semp:
            _significato("valuta come il bambino semplifica i suoni difficili nel parlato "
                          "spontaneo — normale fino a una certa età, un campanello d'allarme se persiste.")
            st.markdown("**Semplificazioni di sistema**")
            semp_sist = st.multiselect("Semplificazioni", [
                "Stopping", "Fricazione", "Affricazione", "Anteriorizzazione",
                "Posteriorizzazione", "Desonorizzazione", "Gliding"],
                key="scr_ling_semp_sist")
            st.markdown("**Semplificazioni di struttura**")
            semp_strut = st.multiselect("Semplificazioni", [
                "Eliminazione sillaba debole", "Armonia consonantica", "Armonia vocalica",
                "Riduzione gruppi consonantici", "Riduzione dittonghi", "Metatesi",
                "Epentesi", "Cancellazione consonante e/o vocale"],
                key="scr_ling_semp_strut")
            with st.expander("📺 Materiale da mostrare al bambino"):
                _big("🐶 cane · 🚗 macchina · 🌳 albero · 🍎 mela")
                st.caption("Chiedi di nominare le immagini/parole: osserva come pronuncia i suoni.")
                _finestra_bambino("🐶 cane &nbsp; 🚗 macchina &nbsp; 🌳 albero &nbsp; 🍎 mela", "linguaggio")

        ling_livelli = st.checkbox("Eseguito — Livello lessicale/morfosintattico", key="scr_ling_livelli_on")
        livello_lex = livello_morfo = ""
        if ling_livelli:
            _significato("osserva quante parole conosce e usa (lessico) e come costruisce "
                          "le frasi (grammatica) rispetto all'età.")
            livello_lex = st.text_area("Livello lessicale-semantico", key="scr_ling_lex", height=68)
            livello_morfo = st.text_area("Livello morfosintattico e narrativo", key="scr_ling_morfo", height=68)

        ling_fluenza = st.checkbox("Eseguito — Disturbi della fluenza", key="scr_ling_fluenza_on")
        balbuzie = tachilalia = extra_verbale = ""
        if ling_fluenza:
            _significato("osserva se il bambino ripete, blocca o allunga suoni/parole mentre parla "
                         "(balbuzie) o parla troppo rapidamente in modo confuso (tachilalia/cluttering).")
            balbuzie = st.text_input("Balbuzie (familiarità, epoca insorgenza)", key="scr_ling_balbuzie")
            tachilalia = st.text_input("Tachilalia / cluttering", key="scr_ling_tachilalia")
            extra_verbale = st.text_input("Sintomatologia extra-verbale", key="scr_ling_extra")

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
            with st.expander("📺 Testo da far leggere (schermo grande — IReST)", expanded=True):
                if st.button("🔁 Nuovo testo", key="scr_lettura_nuovo"):
                    st.session_state["scr_lettura_idx"] = random.randrange(len(_TESTI_IREST))
                idx_t = st.session_state.get("scr_lettura_idx", 0)
                brano = _TESTI_IREST[idx_t]
                _big(brano["testo"])
                st.caption(f"IReST · \"{brano['nome']}\" · {brano['parole']} parole · "
                           f"norma tempo: {brano['tempo_medio']} · norma velocità: {brano['velocita_media']}")
                _finestra_bambino(brano["testo"], "lettura")

        appr_scrittura = st.checkbox("Eseguito — Scrittura", key="scr_appr_scrittura_on")
        scr_parole = scr_nonparole = scr_omofone = grafia = ""
        if appr_scrittura:
            _significato("valuta gli errori ortografici sotto dettatura — utile per individuare "
                         "difficoltà di scrittura (disortografia).")
            st.markdown("**Scrittura (errori)**")
            c4, c5, c6 = st.columns(3)
            scr_parole = c4.text_input("Parole", key="scr_appr_scr_parole")
            scr_nonparole = c5.text_input("Non parole", key="scr_appr_scr_nonparole")
            scr_omofone = c6.text_input("Omofone non omografe", key="scr_appr_scr_omofone")
            grafia = st.text_area("Grafia", key="scr_appr_grafia", height=68)

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
        tb_fus_per = tb_fus_cen = tb_sopp_od = tb_sopp_os = tb_stereo = ""
        if tb_eseguito:
            _significato("con lo strumento Telebinocular verifica fusione, soppressione di un occhio "
                         "e percezione della profondità (stereopsi) — usa le schede standard dello strumento.")
            ctb1, ctb2, ctb3 = st.columns(3)
            tb_fus_per = ctb1.selectbox("Fusione periferica", ["Presente", "Assente", "Instabile"],
                                         key="scr_vp_tb_fusper")
            tb_fus_cen = ctb2.selectbox("Fusione centrale", ["Presente", "Assente", "Instabile"],
                                         key="scr_vp_tb_fuscen")
            tb_stereo = ctb3.text_input("Stereopsi (scheda)", key="scr_vp_tb_stereo")
            ctb4, ctb5 = st.columns(2)
            tb_sopp_od = ctb4.checkbox("Soppressione OD", key="scr_vp_tb_soppod")
            tb_sopp_os = ctb5.checkbox("Soppressione OS", key="scr_vp_tb_soppos")

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
            "semplificazioni_sistema": semp_sist, "semplificazioni_struttura": semp_strut,
            "livello_lessicale": livello_lex, "livello_morfosintattico": livello_morfo,
            "balbuzie": balbuzie, "tachilalia": tachilalia, "extra_verbale": extra_verbale,
        },
        "apprendimento": {
            "lettura_parole": lett_parole, "lettura_nonparole": lett_nonparole,
            "lettura_brano": lett_brano, "scrittura_parole": scr_parole,
            "scrittura_nonparole": scr_nonparole, "scrittura_omofone": scr_omofone,
            "grafia": grafia, "calcolo_scritto": calc_scritto,
            "enumerazione": enumerazione, "fatti_procedure": fatti_proc,
        },
        "visuo_posturale": {
            "cover_test_lontano": ct_lontano, "cover_test_vicino": ct_vicino,
            "harmon": harmon, "rrd": rrd, "ppc": ppc, "ppa": ppa,
            "nsuco_pursuit": nsuco_pursuit, "nsuco_saccadi": nsuco_saccadi,
            "dem": dem, "kd": kd, "clinical_fusion_test": cft,
            "telebinocular_eseguito": tb_eseguito,
            "telebinocular_fusione_periferica": tb_fus_per if tb_eseguito else None,
            "telebinocular_fusione_centrale": tb_fus_cen if tb_eseguito else None,
            "telebinocular_soppressione_od": tb_sopp_od if tb_eseguito else None,
            "telebinocular_soppressione_os": tb_sopp_os if tb_eseguito else None,
            "telebinocular_stereopsi": tb_stereo if tb_eseguito else None,
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
    st.markdown("#### Storico screening di questo paziente")
    righe = _storico(conn, paz_id)
    if not righe:
        st.caption("Nessuno screening registrato finora.")
    else:
        for r in righe:
            rid, data_s, op, nt = (r.get(k) if hasattr(r, "get") else r[i]
                                    for i, k in enumerate(["id", "data_screening", "operatore", "note"]))
            st.caption(f"📅 {data_s} · {op or '—'} · {nt or ''}")
