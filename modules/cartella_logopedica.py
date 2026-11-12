# -*- coding: utf-8 -*-
"""Cartella logopedica dell'eta' evolutiva — la struttura portante dell'area logopedica.

Organizzazione (stessa logica delle cartelle logopediche in uso nei servizi:
frontespizio → quadro generale → linguaggio per livelli → funzioni collegate
→ sezioni per patologia → test → piano di lavoro). Le voci sono scritte per
questo gestionale: dei test pubblicati si registrano solo nome, data,
punteggio ed esito, mai il modulo dell'editore.

Una cartella VIVA per paziente (tabella cartella_logopedica, una riga, dati
in JSON): si aggiorna nel tempo e SI SALVA DA SOLA a ogni modifica.
La valutazione SMOF, il diario delle sedute, gli obiettivi e la relazione
restano in modules/logopedia.py, come sezioni accanto a questa.
"""
from __future__ import annotations

import datetime as dt
import json

import streamlit as st

LIVELLI = ["—", "1 · adeguato", "2 · lievemente inadeguato", "3 · inadeguato", "4 · gravemente inadeguato"]

MOTIVI = ["Ritardo o disturbo del linguaggio", "Difficoltà di pronuncia (articolazione)",
          "Difficoltà di comprensione", "Balbuzie o disfluenza", "Disturbo della voce",
          "Deglutizione atipica / squilibrio oro-facciale", "Difficoltà di alimentazione o disfagia",
          "Ipoacusia o sordità", "Difficoltà di lettura e scrittura", "Difficoltà di comunicazione e relazione",
          "Esiti di lesione neurologica", "Malformazione (es. palatoschisi)", "Altro"]

QUADRO = [("comportamento", "Comportamento"), ("abilita_comunicative", "Abilità comunicative"),
          ("interazione", "Interazione e regole della conversazione"),
          ("buccali", "Abilità buccali e deglutitorie"), ("voce", "Voce")]

# (chiave, titolo, cosa osservare, scelte multiple facoltative)
LINGUAGGIO = [
    ("fonologico", "Fonetico-fonologico", "Suoni presenti e assenti, intelligibilità, stabilità delle produzioni.",
     ("Processi osservati", ["Omissione di suoni o sillabe", "Sostituzione di suoni", "Semplificazione dei gruppi consonantici",
                             "Assimilazioni / armonie", "Inversioni (metatesi)", "Desonorizzazione o sonorizzazione",
                             "Anteriorizzazione o posteriorizzazione", "Distorsioni (es. sigmatismo, rotacismo)",
                             "Produzioni instabili della stessa parola"])),
    ("lessicale", "Semantico-lessicale", "Ampiezza del vocabolario in comprensione e in produzione, accesso alle parole.",
     ("Osservazioni", ["Vocabolario ridotto in comprensione", "Vocabolario ridotto in produzione",
                       "Difficoltà a trovare le parole", "Parole generiche o passe-partout", "Parafasie",
                       "Difficoltà con categorie e relazioni tra parole"])),
    ("morfosintattico", "Morfosintattico", "Lunghezza e struttura della frase, uso di articoli, preposizioni, accordi, verbi.",
     ("Osservazioni", ["Parola singola", "Combinazioni di due parole", "Frase semplice senza funtori",
                       "Frase semplice completa", "Frasi complesse (coordinate, subordinate)",
                       "Errori di accordo", "Omissione di articoli o preposizioni", "Difficoltà con i tempi verbali",
                       "Comprensione di frasi difficoltosa"])),
    ("pragmatico", "Pragmatico", "Uso del linguaggio con gli altri: intenzione, turni, sguardo, adeguatezza al contesto.",
     ("Osservazioni", ["Scarsa intenzionalità comunicativa", "Poco contatto di sguardo", "Fatica a rispettare i turni",
                       "Fatica a mantenere l'argomento", "Uso prevalente di gesti", "Poche richieste spontanee",
                       "Comprensione letterale (ironia, modi di dire)", "Ecolalie o linguaggio ripetitivo"])),
    ("testuale", "Testuale e narrativo", "Comprendere e raccontare una storia o un fatto: ordine, legami, completezza.",
     ("Osservazioni", ["Comprensione di racconto difficoltosa", "Racconto povero o frammentato",
                       "Ordine degli eventi confuso", "Mancano i legami (perché, poi, quindi)",
                       "Fatica a spiegare un fatto vissuto"])),
]

# funzioni che il gestionale valuta già altrove: qui solo il livello e il rimando
COLLEGATE = [("percezione_uditiva", "Percezione uditiva", "📊 Audiometria funzionale"),
             ("percezione_visiva", "Percezione visiva", "👁️ Valutazione visuo-percettiva"),
             ("motricita", "Motricità generale e prassie", "🧬 Profilo Neuro-Evolutivo"),
             ("mano_grafismo", "Mano e grafismo", None),
             ("attenzione_memoria", "Attenzione e memoria", None),
             ("apprendimenti", "Lettura, scrittura, calcolo", "📚 DSA — Apprendimento"),
             ("relazione_autonomie", "Relazione e autonomie", None)]

SI_NO = ["—", "Sì", "No", "In parte"]

# sezioni per patologia: chiave → (titolo, [(campo, etichetta, tipo, opzioni)])
#   tipo: "t" testo breve · "a" testo lungo · "s" scelta · "m" scelta multipla · "l" livello 1-4
PATOLOGIE = {
    "voce": ("Voce", [
        ("esordio", "Da quando e come è iniziato", "t", None),
        ("qualita", "Qualità della voce", "m", ["Rauca", "Soffiata", "Sforzata", "Debole", "Nasale", "Con rotture", "Afona a tratti"]),
        ("uso", "Uso vocale", "m", ["Urla spesso", "Parla molto e a lungo", "Parla in ambienti rumorosi", "Schiarisce spesso la gola", "Canto"]),
        ("respirazione", "Respirazione durante la voce", "s", ["—", "Costo-diaframmatica", "Alta / clavicolare", "Mista", "Incoordinata"]),
        ("fatica", "Fatica o fastidio dopo aver parlato", "s", SI_NO),
        ("orl", "Visita ORL / foniatrica (data ed esito)", "t", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
    "fluenza": ("Balbuzie e fluenza", [
        ("esordio", "Età e circostanze di esordio", "t", None),
        ("familiarita", "Familiarità", "s", SI_NO),
        ("tipo", "Disfluenze osservate", "m", ["Ripetizioni di suoni o sillabe", "Ripetizioni di parole", "Prolungamenti", "Blocchi", "Interiezioni e riempitivi", "Revisioni della frase"]),
        ("associati", "Comportamenti associati", "m", ["Tensione del volto o del corpo", "Movimenti associati", "Evita parole o situazioni", "Sguardo che si interrompe", "Alterazione del respiro"]),
        ("variabilita", "Quando va meglio e quando peggio", "a", None),
        ("vissuto", "Come la vive il bambino e la famiglia", "a", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
    "deglutizione": ("Deglutizione atipica e squilibrio oro-facciale", [
        ("riposo", "Postura della lingua a riposo", "s", ["—", "Sul palato", "Bassa", "Interdentale", "Non valutabile"]),
        ("labbra", "Labbra a riposo", "s", ["—", "Chiuse", "Socchiuse", "Aperte"]),
        ("respirazione", "Respirazione", "s", ["—", "Nasale", "Orale", "Mista"]),
        ("spinta", "Spinta linguale in deglutizione", "s", ["—", "Assente", "Anteriore", "Laterale", "Anteriore e laterale"]),
        ("vizi", "Abitudini orali", "m", ["Suzione del dito", "Ciuccio prolungato", "Biberon prolungato", "Onicofagia", "Morde oggetti o labbra", "Bruxismo"]),
        ("occlusione", "Occlusione e ortodonzia (apparecchio, indicazioni)", "t", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
    "disfagia": ("Alimentazione e disfagia", [
        ("modalita", "Modalità di alimentazione", "s", ["—", "Per bocca, dieta libera", "Per bocca, consistenze modificate", "Mista", "Non per bocca (sondino / PEG)"]),
        ("consistenze", "Consistenze accettate", "m", ["Liquidi", "Semiliquidi", "Semisolidi", "Solidi morbidi", "Solidi"]),
        ("segni", "Segni durante il pasto", "m", ["Tosse", "Voce gorgogliante", "Scolo di cibo o saliva", "Residui in bocca", "Tempi molto lunghi", "Rifiuto del cibo", "Affaticamento"]),
        ("svezzamento", "Svezzamento e passaggio alle consistenze", "t", None),
        ("selettivita", "Selettività alimentare", "s", SI_NO),
        ("autonomia", "Autonomia a tavola", "t", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note (e indicazioni mediche ricevute)", "a", None)]),
    "sordita": ("Ipoacusia, sordità e protesi", [
        ("tipo", "Tipo di ipoacusia", "s", ["—", "Trasmissiva", "Neurosensoriale", "Mista", "Non definita"]),
        ("grado", "Grado", "s", ["—", "Lieve", "Media", "Grave", "Profonda"]),
        ("lato", "Lato", "s", ["—", "Bilaterale", "Destra", "Sinistra"]),
        ("epoca", "Epoca di insorgenza e di diagnosi", "t", None),
        ("ausilio", "Ausilio", "m", ["Protesi acustica", "Impianto cocleare", "Sistema FM / microfono", "Nessuno"]),
        ("uso", "Uso quotidiano dell'ausilio", "t", None),
        ("modalita", "Modalità comunicativa", "m", ["Orale", "Lettura labiale", "Gesti", "Lingua dei segni", "Bimodale"]),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
    "palatoschisi": ("Palatoschisi e insufficienza velare", [
        ("quadro", "Quadro e interventi chirurgici (con date)", "a", None),
        ("risonanza", "Risonanza", "s", ["—", "Nella norma", "Ipernasale", "Iponasale", "Mista"]),
        ("fuga", "Fuga d'aria nasale", "s", SI_NO),
        ("compensi", "Articolazioni compensatorie", "m", ["Colpi di glottide", "Fricative faringee", "Posteriorizzazioni", "Smorfie nasali"]),
        ("udito", "Udito e otiti ricorrenti", "t", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
    "disartria": ("Disartria e disturbo motorio del linguaggio", [
        ("quadro", "Quadro neurologico di riferimento", "t", None),
        ("aspetti", "Aspetti coinvolti", "m", ["Respirazione", "Voce", "Risonanza", "Articolazione", "Ritmo e prosodia"]),
        ("tono", "Tono e controllo oro-facciale", "t", None),
        ("scialorrea", "Scialorrea", "s", SI_NO),
        ("intelligibilita", "Intelligibilità", "l", None),
        ("caa", "Comunicazione aumentativa in uso", "t", None),
        ("note", "Note", "a", None)]),
    "neurologico": ("Esiti di trauma cranico o lesione acquisita", [
        ("evento", "Evento e data", "t", None),
        ("vigilanza", "Vigilanza e contatto con l'ambiente", "t", None),
        ("comunicazione", "Comunicazione attuale", "a", None),
        ("alimentazione", "Alimentazione attuale", "t", None),
        ("scale", "Scale somministrate ed esito", "t", None),
        ("livello", "Compromissione complessiva", "l", None),
        ("note", "Note", "a", None)]),
}

TEST_NOMI = ["", "PVB / MacArthur", "Peabody (PPVT)", "TROG / comprensione grammaticale", "TVL", "BVL 4-12", "TFL / fono-lessicale",
             "Prove di articolazione", "ITPA", "LAP", "Bender", "WISC", "Leiter", "Batteria lettura-scrittura", "SSI (balbuzie)", "Altro"]


# ── Archivio ────────────────────────────────────────────────────
def _assicura(conn) -> None:
    if st.session_state.get("_cartella_logo_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS cartella_logopedica ("
                    "paziente_id BIGINT PRIMARY KEY, dati JSONB NOT NULL DEFAULT '{}'::jsonb, "
                    "aggiornato_il TIMESTAMPTZ NOT NULL DEFAULT now(), aggiornato_da TEXT)")
        conn.commit()
        st.session_state["_cartella_logo_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def carica(conn, paz_id) -> dict:
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati FROM cartella_logopedica WHERE paziente_id=%s", (int(paz_id),))
        r = cur.fetchone()
        if not r:
            return {}
        d = r[0] if not isinstance(r, dict) else r.get("dati")
        return d if isinstance(d, dict) else json.loads(d or "{}")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}


def _salva(conn, paz_id, dati) -> str:
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO cartella_logopedica (paziente_id, dati, aggiornato_il, aggiornato_da) "
                    "VALUES (%s, %s::jsonb, now(), %s) ON CONFLICT (paziente_id) DO UPDATE SET "
                    "dati = EXCLUDED.dati, aggiornato_il = now(), aggiornato_da = EXCLUDED.aggiornato_da",
                    (int(paz_id), json.dumps(dati, ensure_ascii=False, default=str),
                     str(st.session_state.get("username") or st.session_state.get("user") or "")))
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _pieno(v) -> bool:
    if isinstance(v, dict):
        return any(_pieno(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(_pieno(x) for x in v)
    return v not in (None, "", "—", False)


# ── Campi ───────────────────────────────────────────────────────
class _Modulo:
    """Disegna i campi partendo dai dati salvati e raccoglie i valori nuovi."""

    def __init__(self, paz_id, salvati):
        self.px, self.salvati = f"cl_{paz_id}", salvati or {}

    def _k(self, *p):
        return self.px + "_" + "_".join(p)

    def _v(self, *p, default=None):
        d = self.salvati
        for x in p:
            d = d.get(x) if isinstance(d, dict) else None
            if d is None:
                return default
        return d

    def testo(self, etichetta, *p, lungo=False, aiuto=None):
        k = self._k(*p)
        if k not in st.session_state:
            st.session_state[k] = self._v(*p, default="") or ""
        return (st.text_area(etichetta, key=k, height=90, placeholder=aiuto) if lungo
                else st.text_input(etichetta, key=k, placeholder=aiuto))

    def scelta(self, etichetta, opzioni, *p):
        k = self._k(*p)
        if k not in st.session_state:
            v = self._v(*p, default=opzioni[0])
            st.session_state[k] = v if v in opzioni else opzioni[0]
        return st.selectbox(etichetta, opzioni, key=k)

    def multipla(self, etichetta, opzioni, *p):
        k = self._k(*p)
        if k not in st.session_state:
            st.session_state[k] = [x for x in (self._v(*p, default=[]) or []) if x in opzioni]
        return st.multiselect(etichetta, opzioni, key=k, placeholder="Scegli una o più voci")

    def livello(self, etichetta, *p):
        return self.scelta(etichetta, LIVELLI, *p)

    def tabella(self, colonne, *p, config=None):
        k = self._k(*p)
        # La base della tabella si fissa alla prima apertura: se cambiasse a ogni
        # salvataggio, Streamlit riapplicherebbe le modifiche e raddoppierebbe le righe.
        kb = k + "_base"
        if kb not in st.session_state:
            righe = self._v(*p, default=[]) or []
            st.session_state[kb] = ([{c: (r.get(c) or "") for c in colonne} for r in righe if isinstance(r, dict)]
                                    or [{c: "" for c in colonne}])
        base = st.session_state[kb]
        out = st.data_editor(base, num_rows="dynamic", use_container_width=True, hide_index=True,
                             key=k, column_config=config or {})
        try:
            out = out.to_dict("records")
        except Exception:
            pass
        puliti = []
        for r in out or []:
            r = {c: ("" if r.get(c) is None else str(r.get(c)).strip()) for c in colonne}
            if any(r.values()):
                puliti.append(r)
        return puliti


def render_cartella(conn, paz_id) -> None:
    """La cartella logopedica del paziente: sei schede, salvataggio automatico."""
    _assicura(conn)
    k_sal = f"cl_{paz_id}_salvato"
    if k_sal not in st.session_state:
        st.session_state[k_sal] = carica(conn, paz_id)
    m = _Modulo(paz_id, st.session_state[k_sal])
    d = {}

    st.caption("Cartella unica del paziente: si aggiorna nel tempo e si salva da sola a ogni modifica. "
               "Compila solo quello che serve: tutti i campi sono facoltativi.")
    avviso = st.empty()
    t1, t2, t3, t4, t5, t6 = st.tabs(["1 · Frontespizio", "2 · Quadro generale", "3 · Linguaggio",
                                      "4 · Aree collegate", "5 · Per patologia", "6 · Test e piano di lavoro"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            d["logopedista"] = m.testo("Logopedista di riferimento", "logopedista")
            d["inviante"] = m.testo("Inviato da", "inviante", aiuto="pediatra, scuola, famiglia, altro specialista")
        with c2:
            d["presa_in_carico"] = m.scelta("Presa in carico", ["—", "Solo valutazione", "Valutazione e trattamento",
                                                               "Trattamento", "Monitoraggio / controlli"], "presa_in_carico")
            d["modalita"] = m.scelta("Modalità del trattamento", ["—", "Diretta con il bambino", "Indiretta (guida ai genitori)",
                                                                  "Mista"], "modalita")
        st.markdown("**Diagnosi nel tempo**")
        d["diagnosi_ingresso"] = m.testo("Diagnosi d'ingresso (con data e chi l'ha posta)", "diagnosi_ingresso", lungo=True)
        st.caption("Diagnosi successive: una riga per ogni aggiornamento.")
        d["diagnosi_successive"] = m.tabella(["data", "diagnosi", "posta da"], "diagnosi_successive")
        d["diagnosi_conclusiva"] = m.testo("Diagnosi conclusiva o alla dimissione", "diagnosi_conclusiva", lungo=True)

    with t2:
        d["motivi"] = m.multipla("Motivo dell'invio", MOTIVI, "motivi")
        d["motivo_parole"] = m.testo("Con le parole della famiglia", "motivo_parole", lungo=True)
        st.markdown("**Quadro generale** — un livello per area, da 1 (adeguato) a 4 (gravemente inadeguato)")
        d["quadro"] = {}
        for chiave, titolo in QUADRO:
            a, b = st.columns([1, 2])
            with a:
                liv = m.livello(titolo, "quadro", chiave, "livello")
            with b:
                nota = m.testo(f"Nota — {titolo.lower()}", "quadro", chiave, "nota")
            d["quadro"][chiave] = {"livello": liv, "nota": nota}

    with t3:
        st.caption("Un riquadro per ogni livello del linguaggio. Il bilancio fonetico suono per suono resta nella "
                   "sezione «Valutazione + SMOF».")
        d["linguaggio"] = {}
        for chiave, titolo, cosa, (et_multi, opzioni) in LINGUAGGIO:
            with st.expander(titolo, expanded=_pieno(m._v("linguaggio", chiave))):
                st.caption(cosa)
                a, b = st.columns(2)
                with a:
                    comp = m.livello("Comprensione", "linguaggio", chiave, "comprensione")
                with b:
                    prod = m.livello("Produzione", "linguaggio", chiave, "produzione")
                oss = m.multipla(et_multi, opzioni, "linguaggio", chiave, "osservazioni")
                nota = m.testo("Esempi e note", "linguaggio", chiave, "nota", lungo=True)
                d["linguaggio"][chiave] = {"comprensione": comp, "produzione": prod, "osservazioni": oss, "nota": nota}
        d["campione"] = m.testo("Campione di linguaggio spontaneo (frasi dette dal bambino, così come le dice)",
                                "campione", lungo=True)

    with t4:
        st.caption("Aree che il gestionale valuta nei loro moduli: qui basta il livello e una riga, "
                   "per avere il quadro logopedico completo in una pagina.")
        d["collegate"] = {}
        for chiave, titolo, voce in COLLEGATE:
            a, b, c = st.columns([1.2, 2.2, 1])
            with a:
                liv = m.livello(titolo, "collegate", chiave, "livello")
            with b:
                nota = m.testo(f"Nota — {titolo.lower()}", "collegate", chiave, "nota")
            d["collegate"][chiave] = {"livello": liv, "nota": nota}
            if voce:
                c.markdown("&nbsp;", unsafe_allow_html=True)
                if c.button("Apri il modulo", key=f"cl_{paz_id}_vai_{chiave}", use_container_width=True):
                    try:
                        from .fascicolo_paziente import _area_di
                        area = _area_di(voce)
                    except Exception:
                        area = None
                    if area:
                        st.session_state["goto_area"], st.session_state["goto_sotto"] = area, voce
                        st.session_state["paziente_attivo_id"] = paz_id
                        st.rerun()

    with t5:
        attive = m.multipla("Sezioni da aprire per questo paziente",
                            [v[0] for v in PATOLOGIE.values()], "sezioni_attive")
        d["sezioni_attive"] = attive
        d["patologie"] = dict(m._v("patologie", default={}) or {})     # le sezioni chiuse restano in archivio
        if not attive:
            st.info("Scegli qui sopra le sezioni che servono: voce, balbuzie, deglutizione, disfagia, "
                    "sordità, palatoschisi, disartria, esiti neurologici.")
        for chiave, (titolo, campi) in PATOLOGIE.items():
            if titolo not in attive:
                continue
            with st.expander(titolo, expanded=True):
                sez = {}
                for campo, etichetta, tipo, opzioni in campi:
                    if tipo == "t":
                        sez[campo] = m.testo(etichetta, "patologie", chiave, campo)
                    elif tipo == "a":
                        sez[campo] = m.testo(etichetta, "patologie", chiave, campo, lungo=True)
                    elif tipo == "s":
                        sez[campo] = m.scelta(etichetta, opzioni, "patologie", chiave, campo)
                    elif tipo == "m":
                        sez[campo] = m.multipla(etichetta, opzioni, "patologie", chiave, campo)
                    else:
                        sez[campo] = m.livello(etichetta, "patologie", chiave, campo)
                d["patologie"][chiave] = sez

    with t6:
        st.markdown("**Test somministrati** — solo nome, data, punteggio ed esito")
        d["test"] = m.tabella(["data", "test", "punteggio", "esito / nota"], "test", config={
            "test": st.column_config.SelectboxColumn("test", options=TEST_NOMI, required=False)})
        st.caption("Se il test non è in elenco scegli «Altro» e scrivi il nome nella colonna «esito / nota».")
        st.markdown("**Piano di lavoro**")
        d["sintesi"] = m.testo("Sintesi logopedica (in due righe: cosa c'è e cosa pesa di più)", "sintesi", lungo=True)
        d["piano"] = m.testo("Piano di lavoro (aree su cui si lavora, frequenza, durata prevista)", "piano", lungo=True)
        d["consegne"] = m.testo("Indicazioni a famiglia e scuola", "consegne", lungo=True)
        st.caption("Monitoraggi: una riga per ogni verifica periodica. Gli obiettivi misurabili e il diario "
                   "delle sedute restano nelle sezioni «Obiettivi & monitoraggio» e «Diario sedute».")
        d["monitoraggi"] = m.tabella(["data", "cosa è cambiato", "prossima verifica"], "monitoraggi")

    # ── Salvataggio automatico ──
    prima = st.session_state[k_sal]
    if json.dumps(d, sort_keys=True, default=str) != json.dumps(prima, sort_keys=True, default=str):
        if _pieno(d) or _pieno(prima):
            err = _salva(conn, paz_id, d)
            if err:
                avviso.error(f"⚠️ Salvataggio automatico non riuscito: {err}. Non uscire dalla pagina.")
            else:
                st.session_state[k_sal] = d
                st.session_state.pop(f"diag_storico_{paz_id}", None)
                avviso.caption("✅ Salvato automaticamente alle "
                               + dt.datetime.now(dt.timezone.utc).astimezone(_roma()).strftime("%H:%M:%S"))
    elif _pieno(prima):
        avviso.caption("✅ Cartella salvata.")


def _roma():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Rome")
    except Exception:
        return dt.timezone(dt.timedelta(hours=1))


# ── Per la Diagnosi assistita ─────────────────────────────────────────
def _liv(v) -> str:
    return "" if v in (None, "", "—") else str(v).split(" · ", 1)[-1]


def sintesi_cartella(conn, paz_id) -> list[str]:
    """La cartella logopedica in righe di testo, solo le parti compilate."""
    d = carica(conn, paz_id)
    if not _pieno(d):
        return []
    out = []

    def riga(et, v):
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v if x)
        if v not in (None, "", "—"):
            out.append(f"- {et}: {' '.join(str(v).split())}")

    riga("Presa in carico", d.get("presa_in_carico"))
    riga("Motivo dell'invio", d.get("motivi"))
    riga("Con le parole della famiglia", d.get("motivo_parole"))
    riga("Diagnosi d'ingresso", d.get("diagnosi_ingresso"))
    for x in d.get("diagnosi_successive") or []:
        riga(f"Diagnosi successiva ({x.get('data') or 's.d.'})", f"{x.get('diagnosi', '')} {('— ' + x['posta da']) if x.get('posta da') else ''}")
    riga("Diagnosi conclusiva", d.get("diagnosi_conclusiva"))
    for chiave, titolo in QUADRO:
        q = (d.get("quadro") or {}).get(chiave) or {}
        if _liv(q.get("livello")) or q.get("nota"):
            riga(f"Quadro generale – {titolo}", " — ".join(x for x in (_liv(q.get("livello")), q.get("nota")) if x))
    for chiave, titolo, _c, _m in LINGUAGGIO:
        q = (d.get("linguaggio") or {}).get(chiave) or {}
        pezzi = []
        if _liv(q.get("comprensione")):
            pezzi.append("comprensione " + _liv(q["comprensione"]))
        if _liv(q.get("produzione")):
            pezzi.append("produzione " + _liv(q["produzione"]))
        if q.get("osservazioni"):
            pezzi.append("; ".join(q["osservazioni"]))
        if q.get("nota"):
            pezzi.append(q["nota"])
        if pezzi:
            riga(f"Linguaggio – livello {titolo.lower()}", " — ".join(pezzi))
    riga("Campione di linguaggio spontaneo", d.get("campione"))
    for chiave, titolo, _v in COLLEGATE:
        q = (d.get("collegate") or {}).get(chiave) or {}
        if _liv(q.get("livello")) or q.get("nota"):
            riga(titolo, " — ".join(x for x in (_liv(q.get("livello")), q.get("nota")) if x))
    for chiave, (titolo, campi) in PATOLOGIE.items():
        if titolo not in (d.get("sezioni_attive") or []):
            continue
        sez = (d.get("patologie") or {}).get(chiave) or {}
        pezzi = []
        for campo, etichetta, tipo, _o in campi:
            v = sez.get(campo)
            if isinstance(v, list):
                v = ", ".join(v)
            v = _liv(v) if tipo == "l" else v
            if v not in (None, "", "—"):
                pezzi.append(f"{etichetta.lower()}: {v}")
        if pezzi:
            riga(f"Sezione {titolo}", "; ".join(pezzi))
    for x in d.get("test") or []:
        riga(f"Test {x.get('test') or ''} ({x.get('data') or 's.d.'})",
             " — ".join(v for v in (x.get("punteggio"), x.get("esito / nota")) if v))
    riga("Sintesi logopedica", d.get("sintesi"))
    riga("Piano di lavoro", d.get("piano"))
    riga("Indicazioni a famiglia e scuola", d.get("consegne"))
    for x in d.get("monitoraggi") or []:
        riga(f"Monitoraggio ({x.get('data') or 's.d.'})", x.get("cosa è cambiato"))
    return out
