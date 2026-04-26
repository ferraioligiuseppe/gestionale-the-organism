# -*- coding: utf-8 -*-
"""
Relazione Clinica PNEV - The Organism
Template fedeli allo stile clinico di Studio The Organism.
Tipi: Neuroevolutiva integrata, Follow-up, Scuola/ASL,
      Invio NPI, Sensori-motoria, SMOF, Genitori.
Fasce: 0-3, 3-6, 6-10, 10+ anni.
"""
from __future__ import annotations
import json, datetime
import streamlit as st

BIBLIO = """Ayres A.J. (2005). Sensory Integration and the Child. WPS.
Schaaf R.C. et al. (2014). Journal of Autism and Developmental Disorders.
Stein B.E., Stanford T.R. (2008). Nature Reviews Neuroscience.
Goddard Blythe S. (2005, 2012). Reflexes, Learning and Behavior.
Kaplan M. (2006). Seeing Through New Eyes. Jessica Kingsley.
Castagnini F. Metodo FSC.
Tomatis A. The Ear and the Voice.
Berard G. Hearing Equals Behavior.
Barkley R.A. (2015). ADHD Handbook.
Posner M.I., Rothbart M.K. (2007). Educating the Human Brain.
Diamond A. (2013). Annual Review of Psychology.
Musiek F.E., Chermak G.D. (2007). Handbook of CAPD. Plural Publishing.
McPhillips M., Jordan-Black J.A. (2007). Dev Med Child Neurol.
Pecuch A. et al. (2020). Frontiers in Neurology."""


def _get_prof():
    u = st.session_state.get("user") or {}
    p = u.get("profilo",{}) or {}
    t = p.get("titolo","").strip()
    n = p.get("nome","").strip()
    if n: return f"{t} {n}".strip()
    return u.get("display_name","") or u.get("username","The Organism")

def _get_spec():
    u = st.session_state.get("user") or {}
    p = u.get("profilo",{}) or {}
    return p.get("specializzazioni","Neuropsicologo – Optometrista Comportamentale")

def _carica_dati(conn, paz_id):
    dati = {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if row:
            dati["paz"] = dict(zip([d[0] for d in cur.description],row)) if not isinstance(row,dict) else row
        cur.execute(
            "SELECT anamnesi_json, pnev_summary, pnev_json FROM anamnesi "
            "WHERE paziente_id=%s ORDER BY created_at DESC LIMIT 1", (paz_id,))
        row = cur.fetchone()
        if row:
            def _j(v): return v if isinstance(v,dict) else json.loads(v or "{}")
            if isinstance(row,dict):
                dati["anamnesi"] = _j(row.get("anamnesi_json"))
                dati["pnev_summary"] = row.get("pnev_summary","") or ""
            else:
                dati["anamnesi"] = _j(row[0])
                dati["pnev_summary"] = row[1] or ""
        cur.execute(
            "SELECT visita_json FROM valutazioni_visive "
            "WHERE paziente_id=%s ORDER BY id DESC LIMIT 1", (paz_id,))
        row = cur.fetchone()
        if row:
            raw = row["visita_json"] if isinstance(row,dict) else row[0]
            dati["visiva"] = raw if isinstance(raw,dict) else json.loads(raw or "{}")
    except Exception as e:
        st.caption(f"Dati parziali: {e}")
    return dati

def _fmt_dn(s):
    try: return datetime.date.fromisoformat(str(s)[:10]).strftime("%d/%m/%Y")
    except: return str(s or "")

def _eta_str(dn):
    try:
        d = datetime.date.fromisoformat(str(dn)[:10])
        anni = (datetime.date.today()-d).days//365
        mesi = ((datetime.date.today()-d).days%365)//30
        return f"{anni} anni e {mesi} mesi"
    except: return ""

def _f(v):
    try:
        fv=float(v or 0)
        return f"+{fv:.2f}" if fv>=0 else f"{fv:.2f}"
    except: return str(v or "nd")

def _oggi(): return datetime.date.today().strftime("%d/%m/%Y")

def _intestazione(prof, spec):
    return f"""STUDIO THE ORGANISM
{prof}
{spec}

"""

def _firma(prof, spec, luogo="Pagani"):
    return f"""


{luogo}, {_oggi()}

{prof}
{spec}
Studio The Organism
Via De Rosa, 46 – 84016 Pagani (SA) | Viale Marconi, 55 – 84013 Cava de' Tirreni SA
Tel. 0815152334 – 3935817157 | apstheorganism@gmail.com | www.theorganism.it

Firma e timbro: ___________________________"""


# ══════════════════════════════════════════════════════════════════════
#  TEMPLATE RELAZIONI
# ══════════════════════════════════════════════════════════════════════

def _tpl_neuroevolutiva(dati, prof, spec, fascia, note, biblio, scuola, data_val):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")
    pnev = dati.get("pnev_summary","") or ""
    visiva = dati.get("visita_visiva",{}) or dati.get("visiva",{})
    sez_g  = visiva.get("sez_g",{})
    diag   = sez_g.get("diag","") or ""

    return _intestazione(prof,spec) + f"""RELAZIONE NEUROEVOLUTIVA INTEGRATA ({fascia})
{"BIBLIOGRAFIA E RIFERIMENTI CLINICO-SCIENTIFICI" if biblio else ""}
{BIBLIO if biblio else ""}

DATI ANAGRAFICI
Nome e Cognome:    {nome}
Data di nascita:   {_fmt_dn(dn)}
Età:               {_eta_str(dn)}
Scuola/Contesto:   {scuola or "___________________________"}
Data valutazione:  {data_val or _oggi()}
Data relazione:    {_oggi()}

OGGETTO
Relazione clinica in ambito neuro-psico-evolutivo secondo il Metodo PNEV
(Processi NeuroEvolutivi) — Studio The Organism.

ÉQUIPE MULTIDISCIPLINARE
La presa in carico avviene attraverso un'équipe integrata comprendente:
neuropsicologo, optometrista comportamentale, logopedista,
terapista miofunzionale, psicomotricista, osteopata, fisioterapista.

PROFILO INTEGRATO
{pnev if pnev else "Maturazione disomogenea tra linguaggio, sensorialità, motricità e regolazione."}

LINGUAGGIO E COMUNICAZIONE
Fragilità espressive e/o recettive con variabilità nella comprensione di consegne
complesse. Il profilo linguistico risulta condizionato dalla qualità dell'integrazione
neuro-funzionale e dalla capacità di regolazione attentiva e sensoriale.

SENSORIALITÀ E MOTRICITÀ
Modulazione sensoriale in fase di maturazione con possibili difficoltà di soglia
(iper/iporeattività) in uno o più canali (tattile, propriocettivo, vestibolare, uditivo,
visivo). Coordinazione motoria e prassie da valutare in relazione al profilo evolutivo.

VALUTAZIONE VISUO-PERCETTIVA
{("Diagnosi visiva: " + diag) if diag else "Valutazione optometrico-comportamentale in corso/completata."}

REGOLAZIONE E FUNZIONI ESECUTIVE
Variabilità nella qualità attentiva con fluttuazioni legate al livello di attivazione
del sistema nervoso. Le funzioni esecutive risultano in sviluppo con possibili
difficoltà di pianificazione, inibizione e flessibilità cognitiva.

INQUADRAMENTO SECONDO IL METODO PNEV
Il profilo osservato viene interpretato secondo il Metodo PNEV, che considera
il funzionamento della persona come espressione emergente dall'integrazione tra
sistemi sensoriali, motori, posturali, uditivi, visivi ed emotivo-relazionali.
L'intervento si fonda su modelli di integrazione sensoriale, stimolazione visiva
comportamentale, riorganizzazione neuro-motoria, stimolazione uditiva funzionale
e integrazione dei riflessi primitivi, all'interno di un approccio multisensoriale
personalizzato.

NOTE CLINICHE
{note or "___________________________"}

INDICAZIONI
Si ritiene indicata la continuazione/avvio del percorso terapeutico integrato PNEV
con frequenza di 2 sedute/settimana, home program strutturato (80 min/die),
e rivalutazione dopo il primo step di 10 settimane.
""" + _firma(prof,spec)


def _tpl_followup(dati, prof, spec, fascia, note, biblio, scuola, periodo, progressi, difficolta):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")

    # Fallback con newline pre-calcolati (Python 3.11 non supporta \n in f-string expr)
    _progressi_default = "Nel periodo considerato si evidenziano progressi in:\n- ___________________________\n- ___________________________"
    _difficolta_default = "Permangono difficoltà in:\n- ___________________________\n- ___________________________"
    _progressi_txt = progressi if progressi else _progressi_default
    _difficolta_txt = difficolta if difficolta else _difficolta_default

    return _intestazione(prof,spec) + f"""RELAZIONE DI FOLLOW-UP ({fascia})
{"BIBLIOGRAFIA E RIFERIMENTI CLINICO-SCIENTIFICI" if biblio else ""}
{BIBLIO if biblio else ""}

DATI ANAGRAFICI
Nome e Cognome:       {nome}
Data di nascita:      {_fmt_dn(dn)}
Età:                  {_eta_str(dn)}
Scuola/Contesto:      {scuola or "___________________________"}
Periodo di follow-up: {periodo or "___________________________"}
Data relazione:       {_oggi()}

MOTIVO
Monitoraggio evolutivo nel periodo considerato nell'ambito del percorso
terapeutico PNEV — Studio The Organism.

AREE DI OSSERVAZIONE
- Linguaggio e comunicazione
- Area sensori-motoria
- Regolazione e attenzione
- Funzione visiva e oculomotricità
- Integrazione riflessi primitivi

PROGRESSI OSSERVATI
{_progressi_txt}

AREE CON MAGGIORI DIFFICOLTÀ
{_difficolta_txt}

CONSIDERAZIONI CLINICHE
L'evoluzione osservata è coerente con il percorso terapeutico in atto.
Il profilo neuroevolutivo mostra variazioni significative in relazione
alla continuità del trattamento e all'impegno nel home program.

NOTE CLINICHE
{note or "___________________________"}

INDICAZIONI
{("Proseguire il percorso con le seguenti indicazioni: " + note) if note else "Proseguire il percorso terapeutico con eventuale rimodulazione degli obiettivi in base all'evoluzione clinica osservata."}
Rivalutazione prevista: ___________________________.
""" + _firma(prof,spec)


def _tpl_scuola(dati, prof, spec, fascia, note, scuola, insegnante, classe):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")
    pnev = dati.get("pnev_summary","") or ""

    return _intestazione(prof,spec) + f"""RELAZIONE PER LA SCUOLA / ASL ({fascia})

All'attenzione di: {insegnante or "Dirigente Scolastico / Team docenti"}
Istituto: {scuola or "___________________________"}
Classe: {classe or "___________________________"}

OGGETTO: Relazione clinica e indicazioni per l'alunno/a {nome}

DATI ANAGRAFICI
Nome e Cognome:   {nome}
Data di nascita:  {_fmt_dn(dn)}
Età:              {_eta_str(dn)}
Data relazione:   {_oggi()}

PERCORSO TERAPEUTICO IN CORSO
Il/la bambino/a è inserito/a in un percorso terapeutico integrato PNEV
(Processi NeuroEvolutivi) presso lo Studio The Organism, con équipe
multidisciplinare: neuropsicologo, optometrista, logopedista,
terapista miofunzionale, osteopata, psicomotricista.

PROFILO FUNZIONALE OSSERVATO
{pnev if pnev else "Il profilo funzionale evidenzia fragilità nelle aree dell'attenzione, dell'elaborazione sensoriale e/o della coordinazione visuo-motoria."}

PUNTI DI ATTENZIONE IN CLASSE
- Linguaggio e comprensione delle consegne
- Attenzione e partecipazione al compito
- Coordinazione grafo-motoria e organizzazione spaziale
- Regolazione emotiva e fatica cognitiva
- Elaborazione visiva durante lettura e copia dalla lavagna

INDICAZIONI OPERATIVE
- Posizionare il bambino/a nei banchi anteriori con buona illuminazione
- Consegnare le istruzioni in step brevi e sequenziali
- Privilegiare supporti visivi (immagini, schemi, colori)
- Concedere tempi aggiuntivi per le consegne scritte
- Preferire verifiche orali quando possibile
- Non richiedere lettura ad alta voce improvvisata
- Garantire pause strutturate durante le attività
- Segnalare allo studio qualsiasi variazione nel comportamento

NOTE PER LA SCUOLA
{note or "___________________________"}

CERTIFICAZIONE DI FREQUENZA
Si certifica che {nome} è attualmente inserito/a in un programma
riabilitativo continuativo con frequenza regolare alle sedute terapeutiche.

Siamo a disposizione per un colloquio con il team docenti.
""" + _firma(prof,spec)


def _tpl_npi(dati, prof, spec, fascia, note, biblio, scuola, data_val, diagnosi_ipotetica):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")
    pnev = dati.get("pnev_summary","") or ""

    return _intestazione(prof,spec) + f"""RELAZIONE NEUROPSICOLOGICA – INVIO OSPEDALIERO ({fascia})
{"BIBLIOGRAFIA E RIFERIMENTI CLINICO-SCIENTIFICI" if biblio else ""}
{BIBLIO if biblio else ""}

DATI ANAGRAFICI
Nome e Cognome:    {nome}
Data di nascita:   {_fmt_dn(dn)}
Età:               {_eta_str(dn)}
Scuola/Contesto:   {scuola or "___________________________"}
Data valutazione:  {data_val or _oggi()}
Data relazione:    {_oggi()}

EGREGIO COLLEGA,
Le invio in valutazione il/la paziente {nome} (nato/a il {_fmt_dn(dn)}),
attualmente in carico presso il nostro studio nell'ambito di un percorso
terapeutico integrato secondo il Metodo PNEV.

MOTIVO DELL'INVIO
{diagnosi_ipotetica if diagnosi_ipotetica else "Invio per approfondimento neuropsichiatrico infantile in presenza di difficoltà su attenzione, autoregolazione e funzionamento adattivo con impatto significativo sul piano scolastico e relazionale."}

PROFILO NEUROEVOLUTIVO OSSERVATO (METODO PNEV)
{pnev if pnev else "Il profilo evidenzia immaturità neuroevolutiva globale con coinvolgimento dei processi di regolazione attentiva, sensoriale e motoria."}

OSSERVAZIONE CLINICA
Variabilità attentiva con difficoltà nell'organizzazione e nel completamento
del compito. Si rilevano fragilità nei processi di inibizione comportamentale
e di regolazione emotiva. L'area sensoriale mostra modulazione disomogenea
con possibile coinvolgimento dell'area uditiva (CAPD) e/o visiva funzionale.

FUNZIONI ESECUTIVE
Pianificazione, flessibilità cognitiva e memoria di lavoro risultano in sviluppo
con variabilità legata al livello di attivazione e alla complessità del compito.

STRUMENTI UTILIZZATI
Questionario PNEV (Profilo Neuro-Evolutivo) — somministrazione a genitori/insegnanti.
Osservazione clinica strutturata. Valutazione optometrico-comportamentale.
{("Valutazione neuropsicologica standardizzata." if fascia in ("6-10 anni","10+ anni") else "")}

NOTE CLINICHE
{note or "___________________________"}

SI RICHIEDE
Valutazione neuropsichiatrica infantile completa con eventuale:
- Approfondimento diagnostico (DSM-5)
- Valutazione audiologica e/o ortottico-oftalmologica
- Coordinamento terapeutico per progetto integrato

Rimango a disposizione per qualsiasi informazione.
""" + _firma(prof,spec)


def _tpl_sensori(dati, prof, spec, fascia, note, biblio, scuola, data_val):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")

    return _intestazione(prof,spec) + f"""RELAZIONE SENSORI-MOTORIA E NEURO-PSICO-MOTORIA ({fascia})
{"BIBLIOGRAFIA E RIFERIMENTI CLINICO-SCIENTIFICI" if biblio else ""}
{BIBLIO if biblio else ""}

DATI ANAGRAFICI
Nome e Cognome:    {nome}
Data di nascita:   {_fmt_dn(dn)}
Età:               {_eta_str(dn)}
Scuola/Contesto:   {scuola or "___________________________"}
Data valutazione:  {data_val or _oggi()}
Data relazione:    {_oggi()}

PROFILO SENSORI-MOTORIO
Integrazione sensori-motoria in fase di maturazione con coinvolgimento
dei sistemi propriocettivo, vestibolare e/o tattile. Si rilevano difficoltà
nella modulazione degli input sensoriali con ricadute sul tono muscolare,
sull'equilibrio e sulla qualità della motricità globale e fine.

RIFLESSI PRIMITIVI
Presenza di riflessi primitivi non integrati (MORO, RTAC, TTS, STNL)
che interferiscono con lo sviluppo della coordinazione motoria,
dell'attenzione e dell'organizzazione percettiva.

MOTRICITÀ E PRASSIE
Coordinazione e sequenzialità motoria in via di consolidamento.
Difficoltà nelle attività bilaterali e nelle prassie costruttive
con impatto sulle competenze grafo-motorie.

AREA ORO-MIOFUNZIONALE
{("Osservate alterazioni nelle funzioni miofunzionali oro-facciali con possibile impatto su respirazione, deglutizione e articolazione." if "6-10" in fascia or "10+" in fascia else "Da valutare in relazione allo sviluppo del linguaggio.")}

NOTE CLINICHE
{note or "___________________________"}

INDICAZIONI
- Valutazione TNPEE e presa in carico psicomotoria
- Integrazione riflessi primitivi (INPP/Blomberg/Vojta)
- Coordinamento con équipe PNEV per progetto integrato
- Eventuale valutazione posturologica e osteopatica
""" + _firma(prof,spec)


def _tpl_genitori(dati, prof, spec, note, progressi, piano):
    paz = dati.get("paz",{})
    nome = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn   = paz.get("Data_Nascita","")
    pnev = dati.get("pnev_summary","") or ""
    visiva = dati.get("visita_visiva",{}) or dati.get("visiva",{})
    sez_g  = visiva.get("sez_g",{})
    diag   = sez_g.get("diag","") or ""

    # Pre-calcolo la sezione visione (no backslash in f-string expr per Python 3.11)
    _visione_txt = ("VISIONE FUNZIONALE\n" + diag) if diag else ""

    return _intestazione(prof,spec) + f"""LETTERA AI GENITORI
Relazione clinica — Metodo PNEV
{_oggi()}

Gentili genitori di {nome},

con la presente desideriamo condividere con voi le osservazioni emerse
dalla valutazione del vostro bambino/a svolta presso il nostro studio.

CHI È {nome.upper()}
Nato/a il {_fmt_dn(dn)} ({_eta_str(dn)}), il/la vostro/a bambino/a è stato/a
valutato/a attraverso il Metodo PNEV (Processi NeuroEvolutivi), un approccio
integrato che considera lo sviluppo come un processo che coinvolge mente,
corpo e sensi insieme.

COSA ABBIAMO OSSERVATO
{pnev if pnev else "Il profilo emerso evidenzia alcune fragilità nelle aree della regolazione sensoriale, dell'attenzione e/o della coordinazione visuo-motoria."}

{_visione_txt}

COSA SIGNIFICA IN PRATICA
Le difficoltà che osservate a casa e a scuola — come fatica nella lettura,
difficoltà di concentrazione, stanchezza dopo i compiti, agitazione o
evitamento — spesso non dipendono dalla volontà del vostro bambino/a,
ma da come il suo sistema nervoso elabora le informazioni che arrivano
dall'esterno. È una questione di organizzazione neuro-funzionale,
non di intelligenza o impegno.

PROGRESSI OSSERVATI
{progressi if progressi else "Nel corso del percorso stiamo lavorando su diverse aree. Vi aggiorneremo sui progressi a ogni ciclo di trattamento (ogni 10 settimane)."}

IL PERCORSO TERAPEUTICO
{piano if piano else "Il percorso PNEV prevede sedute bisettimanali presso lo studio e un home program giornaliero di 80 minuti distribuiti tra le diverse aree di intervento."}

Il percorso ha una durata minima di 12 mesi, con un primo step di 10 settimane
al termine del quale valuteremo insieme i progressi e ridefiniremo gli obiettivi.

LA STIMOLAZIONE UDITIVA
Se indicata, la stimolazione uditiva (metodo Hipérion/PNEV) prevede
30 minuti al giorno per 84 giorni consecutivi, seguiti da una pausa di
15 giorni, e poi ripetuta in base all'evoluzione clinica.

COSA POTETE FARE A CASA
- Garantire un ambiente calmo e prevedibile, specialmente durante i compiti
- Rispettare i tempi del bambino/a senza pressioni eccessive
- Eseguire regolarmente il home program concordato (80 min/die)
- Segnalarci qualsiasi cambiamento — positivo o negativo — che osservate
- Portare a ogni seduta le vostre osservazioni quotidiane

NOTE CLINICHE
{note or "___________________________"}

Siamo a vostra completa disposizione per qualsiasi chiarimento.
Con stima,
""" + _firma(prof,spec)


# ══════════════════════════════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════════════════════════════

def _pdf(testo, paz_str, data_str, prof, spec, titolo_doc, pid, suffix):
    try:
        from modules.pdf_templates import genera_carta_intestata
        pdf_bytes = genera_carta_intestata(
            professionista=prof, titolo=spec,
            paziente=paz_str, data=data_str,
            titolo_doc=titolo_doc, corpo_testo=testo,
        )
        st.download_button(
            "📥 Scarica PDF",
            data=pdf_bytes,
            file_name=f"relazione_{suffix}_{paz_str.split()[0]}_{data_str.replace('/','-')}.pdf",
            mime="application/pdf",
            key=f"dl_{suffix}_{pid}"
        )
    except Exception as e:
        st.error(f"Errore PDF: {e}")


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def render_relazione_clinica(conn):
    st.subheader("Relazione Clinica PNEV")
    st.caption("Studio The Organism — Metodo Psico-Neuro-Evolutivo")

    # Selettore paziente
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome, Data_Nascita FROM Pazienti "
            "WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' ORDER BY Cognome, Nome"
        )
        pazienti = cur.fetchall() or []
    except Exception as e:
        st.error(f"Errore: {e}"); return

    if not pazienti:
        st.info("Nessun paziente registrato."); return

    def _label(r): return f"{r.get('Cognome','') if isinstance(r,dict) else r[1]} {r.get('Nome','') if isinstance(r,dict) else r[2]}"
    def _get_id(r): return r["id"] if isinstance(r,dict) else r[0]
    def _get_dn(r): return r.get("Data_Nascita","") if isinstance(r,dict) else (r[3] if len(r)>3 else "")

    c1,c2,c3 = st.columns([2,1,1])
    with c1:
        sel = st.selectbox("Paziente", pazienti, format_func=_label, key="rel_paz")
    paz_id = _get_id(sel)
    paz_label = _label(sel)
    dn = _get_dn(sel)
    dn_fmt = _fmt_dn(dn)
    paz_str = f"{paz_label}  |  Nato/a: {dn_fmt}"

    with c2:
        data_vis = st.date_input("Data relazione", value=datetime.date.today(), key="rel_data")
    data_str = data_vis.strftime("%d/%m/%Y")

    with c3:
        # Fascia automatica
        try:
            anni = (datetime.date.today() - datetime.date.fromisoformat(str(dn)[:10])).days // 365
            if anni < 3: fascia_default = "0-3 anni"
            elif anni < 7: fascia_default = "3-6 anni"
            elif anni < 11: fascia_default = "6-10 anni"
            else: fascia_default = "10+ anni"
        except: fascia_default = "3-6 anni"
        fascia = st.selectbox("Fascia età", ["0-3 anni","3-6 anni","6-10 anni","10+ anni"],
                              index=["0-3 anni","3-6 anni","6-10 anni","10+ anni"].index(fascia_default),
                              key="rel_fascia")

    with st.spinner("Carico dati clinici..."):
        dati = _carica_dati(conn, paz_id)

    # Indicatori
    col1,col2,col3 = st.columns(3)
    col1.metric("Anamnesi", "✅" if dati.get("anamnesi") else "❌")
    col2.metric("Val. visiva", "✅" if dati.get("visiva") else "❌")
    col3.metric("PNEV", "✅" if dati.get("pnev_summary") else "❌")

    prof = _get_prof()
    spec = _get_spec()

    st.markdown("---")

    TIPI = [
        "🧠 Neuroevolutiva integrata",
        "🔄 Follow-up",
        "🏫 Scuola / ASL",
        "🏥 Invio NPI/ospedaliero",
        "🏃 Sensori-motoria",
        "👨‍👩‍👧 Lettera ai genitori",
    ]

    tipo = st.selectbox("Tipo di relazione", TIPI, key="rel_tipo")

    # Campi comuni
    st.markdown("#### Campi clinici")
    with st.expander("Compila i dati specifici", expanded=True):
        scuola = st.text_input("Scuola / Contesto", key=f"rel_scuola_{paz_id}")
        data_val = st.text_input("Data valutazione (se diversa da oggi)", key=f"rel_datav_{paz_id}")
        biblio = st.checkbox("Includi bibliografia scientifica", value=True, key=f"rel_biblio_{paz_id}")
        note = st.text_area("Note cliniche specifiche", height=100, key=f"rel_note_{paz_id}",
                             placeholder="Inserisci le osservazioni cliniche specifiche per questo paziente...")

        if "Follow-up" in tipo:
            periodo = st.text_input("Periodo di follow-up (es. gennaio–aprile 2026)", key=f"rel_periodo_{paz_id}")
            progressi = st.text_area("Progressi osservati", height=80, key=f"rel_prog_{paz_id}")
            difficolta = st.text_area("Aree con maggiori difficoltà", height=80, key=f"rel_diff_{paz_id}")
        elif "Invio" in tipo:
            diagnosi_ip = st.text_area("Ipotesi diagnostica / motivo invio", height=80, key=f"rel_diagip_{paz_id}",
                                        placeholder="Es: Disturbo dello spettro autistico / ADHD / DSA...")
        elif "Scuola" in tipo:
            insegnante = st.text_input("Insegnante / referente scolastico", key=f"rel_ins_{paz_id}")
            classe = st.text_input("Classe", key=f"rel_cl_{paz_id}")
        elif "genitori" in tipo.lower():
            progressi_g = st.text_area("Progressi osservati (per i genitori)", height=80, key=f"rel_progg_{paz_id}")
            piano_g = st.text_area("Piano terapeutico (per i genitori)", height=80, key=f"rel_piang_{paz_id}")

    # Generazione
    testo_key = f"rel_testo_{paz_id}_{tipo}"
    if st.button("📋 Genera relazione", key=f"rel_gen_{paz_id}", type="primary"):
        if "Neuroevolutiva" in tipo:
            testo = _tpl_neuroevolutiva(dati, prof, spec, fascia, note, biblio, scuola, data_val)
        elif "Follow-up" in tipo:
            testo = _tpl_followup(dati, prof, spec, fascia, note, biblio, scuola,
                                   locals().get("periodo",""),
                                   locals().get("progressi",""),
                                   locals().get("difficolta",""))
        elif "Scuola" in tipo:
            testo = _tpl_scuola(dati, prof, spec, fascia, note, scuola,
                                 locals().get("insegnante",""),
                                 locals().get("classe",""))
        elif "Invio" in tipo:
            testo = _tpl_npi(dati, prof, spec, fascia, note, biblio, scuola, data_val,
                              locals().get("diagnosi_ip",""))
        elif "Sensori" in tipo:
            testo = _tpl_sensori(dati, prof, spec, fascia, note, biblio, scuola, data_val)
        elif "genitori" in tipo.lower():
            testo = _tpl_genitori(dati, prof, spec, note,
                                   locals().get("progressi_g",""),
                                   locals().get("piano_g",""))
        else:
            testo = "Tipo di relazione non riconosciuto."
        st.session_state[testo_key] = testo

    testo = st.text_area(
        "Testo relazione (modificabile prima di stampare)",
        value=st.session_state.get(testo_key,""),
        height=600,
        key=f"rel_ta_{paz_id}_{tipo}"
    )
    st.session_state[testo_key] = testo

    if testo:
        titolo_doc = tipo.replace("🧠","").replace("🔄","").replace("🏫","").replace("🏥","").replace("🏃","").replace("👨‍👩‍👧","").strip().upper()
        suffix = tipo.split()[1].lower() if len(tipo.split())>1 else "relazione"
        _pdf(testo, paz_str, data_str, prof, spec, titolo_doc, paz_id, suffix)
