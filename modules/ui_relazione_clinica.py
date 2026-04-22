# -*- coding: utf-8 -*-
"""
Relazione Clinica - The Organism
Tre destinatari: Genitori, Professionisti, Scuola
Basata sui modelli PNEV di Studio The Organism.
"""
from __future__ import annotations
import json, datetime
import streamlit as st


def _get_prof():
    u = st.session_state.get("user") or {}
    profilo = u.get("profilo",{}) or {}
    titolo = profilo.get("titolo","").strip()
    nome   = profilo.get("nome","").strip()
    if nome: return f"{titolo} {nome}".strip()
    return u.get("display_name","") or u.get("username","The Organism")

def _get_spec():
    u = st.session_state.get("user") or {}
    profilo = u.get("profilo",{}) or {}
    return profilo.get("specializzazioni","Neuropsicologo - Optometrista Comportamentale")

def _carica_dati_paziente(conn, paz_id):
    dati = {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if row:
            if isinstance(row, dict): dati["anagrafica"] = row
            else: dati["anagrafica"] = dict(zip([d[0] for d in cur.description], row))

        cur.execute(
            "SELECT anamnesi_json, pnev_summary, pnev_json FROM anamnesi "
            "WHERE paziente_id=%s ORDER BY created_at DESC LIMIT 1", (paz_id,))
        row = cur.fetchone()
        if row:
            def _parse(v):
                if not v: return {}
                return v if isinstance(v,dict) else json.loads(v)
            if isinstance(row,dict):
                dati["anamnesi"] = _parse(row.get("anamnesi_json"))
                dati["pnev_summary"] = row.get("pnev_summary","") or ""
                dati["pnev_json"] = _parse(row.get("pnev_json"))
            else:
                dati["anamnesi"] = _parse(row[0])
                dati["pnev_summary"] = row[1] or ""
                dati["pnev_json"] = _parse(row[2])

        cur.execute(
            "SELECT visita_json FROM valutazioni_visive "
            "WHERE paziente_id=%s ORDER BY id DESC LIMIT 1", (paz_id,))
        row = cur.fetchone()
        if row:
            raw = row["visita_json"] if isinstance(row,dict) else row[0]
            dati["visita_visiva"] = raw if isinstance(raw,dict) else json.loads(raw or "{}")
    except Exception as e:
        st.caption(f"Dati parziali: {e}")
    return dati

def _eta(dn_str):
    try:
        dn = datetime.date.fromisoformat(str(dn_str)[:10])
        anni = (datetime.date.today()-dn).days//365
        mesi = ((datetime.date.today()-dn).days%365)//30
        return anni, mesi
    except: return None, None

def _fmt_dn(dn_str):
    try: return datetime.date.fromisoformat(str(dn_str)[:10]).strftime("%d/%m/%Y")
    except: return str(dn_str or "")

def _f(v):
    try:
        fv=float(v or 0)
        return f"+{fv:.2f}" if fv>=0 else f"{fv:.2f}"
    except: return str(v or "n.d.")


# ══════════════════════════════════════════════════════════════════════
#  RELAZIONE GENITORI
# ══════════════════════════════════════════════════════════════════════

def _genera_genitori(dati, prof, spec, scuola="", ipotesi="", piano=""):
    paz = dati.get("anagrafica",{})
    nome_paz = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn = paz.get("Data_Nascita","")
    dn_fmt = _fmt_dn(dn)
    anni, mesi = _eta(dn)
    eta_str = f"{anni} anni e {mesi} mesi" if anni is not None else "n.d."
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    pnev = dati.get("pnev_summary","") or ""
    visiva = dati.get("visita_visiva",{})
    sez_g = visiva.get("sez_g",{})
    diag_vis = sez_g.get("diag","") or ""
    piano_vis = sez_g.get("piano","") or ""

    return f"""LETTERA AI GENITORI
Studio The Organism — Metodo PNEV
{oggi}

Gentili genitori di {nome_paz},

con la presente desideriamo condividere con voi le osservazioni emerse dalla valutazione \
del vostro bambino/a, svolta presso il nostro studio.

PERCHÉ SIAMO PARTITI DA QUI
Il vostro bambino/a ({nome_paz}, nato/a il {dn_fmt}, {eta_str}) è stato/a valutato/a \
attraverso un approccio integrato che considera lo sviluppo come un processo che coinvolge \
mente, corpo e sensi insieme. Questo è il cuore del Metodo PNEV (Processi NeuroEvolutivi).

COSA ABBIAMO OSSERVATO
{pnev if pnev else "Il profilo emerso dalla valutazione mostra alcune fragilità nelle aree della attenzione, dell elaborazione visiva e/o della regolazione sensoriale."}

{("VALUTAZIONE DELLA VISIONE FUNZIONALE\n" + diag_vis) if diag_vis else ""}

COSA SIGNIFICA IN PRATICA
Le difficoltà che osservate a casa e a scuola — come fatica nella lettura, difficoltà di \
concentrazione, stanchezza dopo i compiti — spesso non dipendono dalla volontà del bambino/a, \
ma da come il suo sistema nervoso elabora le informazioni che arrivano dall esterno.

COSA FAREMO INSIEME
{piano if piano else (piano_vis if piano_vis else "Il percorso terapeutico che proponiamo è pensato per sostenere il bambino/a nelle aree di fragilità emerse, attraverso attività mirate che coinvolgono la visione, l udito, il movimento e la regolazione.")}

Il percorso si svolge in un clima di gioco e collaborazione. \
La vostra presenza e partecipazione attiva sono fondamentali per il successo del trattamento.

COSA POTETE FARE A CASA
- Garantire un ambiente calmo e prevedibile durante i compiti
- Rispettare i ritmi del bambino/a senza pressioni eccessive
- Riferirci qualsiasi cambiamento — positivo o negativo — che osservate
- Seguire le indicazioni specifiche che vi forniremo di volta in volta

Siamo a vostra completa disposizione per qualsiasi chiarimento.

Con stima,

{prof}
{spec}
Studio The Organism
Via De Rosa, 46 - 84016 Pagani (SA) | Viale Marconi, 55 - 84013 Cava de' Tirreni SA
apstheorganism@gmail.com | Tel. 0815152334"""


# ══════════════════════════════════════════════════════════════════════
#  RELAZIONE PROFESSIONISTI
# ══════════════════════════════════════════════════════════════════════

def _genera_professionisti(dati, prof, spec, ipotesi="", piano=""):
    paz = dati.get("anagrafica",{})
    nome_paz = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn = paz.get("Data_Nascita","")
    dn_fmt = _fmt_dn(dn)
    anni, mesi = _eta(dn)
    eta_str = f"{anni} anni e {mesi} mesi" if anni is not None else "n.d."
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    pnev = dati.get("pnev_summary","") or ""
    pnev_json = dati.get("pnev_json",{}) or {}
    visiva = dati.get("visita_visiva",{})
    sez_a = visiva.get("sez_a",{}); sez_b = visiva.get("sez_b",{})
    sez_c = visiva.get("sez_c",{}); sez_d = visiva.get("sez_d",{})
    sez_e = visiva.get("sez_e",{}); sez_g = visiva.get("sez_g",{})
    rs_od = sez_a.get("rs_od",{}); rs_os = sez_a.get("rs_os",{})

    return f"""RELAZIONE CLINICA NEURO-PSICO-EVOLUTIVA — METODO PNEV
Ad uso dei professionisti sanitari

Professionista referente: {prof} — {spec}
Studio The Organism | Data: {oggi}

─────────────────────────────────────────────────────────
DATI IDENTIFICATIVI
─────────────────────────────────────────────────────────
Paziente:          {nome_paz}
Data di nascita:   {dn_fmt}
Età:               {eta_str}

─────────────────────────────────────────────────────────
ÉQUIPE MULTIDISCIPLINARE
─────────────────────────────────────────────────────────
La presa in carico avviene attraverso un'équipe integrata comprendente:
neuropsicologo, optometrista comportamentale, logopedista,
terapista miofunzionale, osteopata, psicomotricista.

─────────────────────────────────────────────────────────
INQUADRAMENTO CLINICO — METODO PNEV
─────────────────────────────────────────────────────────
Secondo il Metodo PNEV (Processi NeuroEvolutivi), lo sviluppo del bambino/a
viene rappresentato come una piramide funzionale in cui l organizzazione delle
funzioni superiori (apprendimento, linguaggio, attenzione) dipende dalla
stabilità dei livelli inferiori (regolazione sensoriale, integrazione
vestibolare, organizzazione posturale, praxis).

{pnev if pnev else "Profilo neuro-evolutivo: da integrare con i dati della valutazione."}

─────────────────────────────────────────────────────────
VALUTAZIONE OPTOMETRICO-COMPORTAMENTALE (notazione Skeffington/OEP)
─────────────────────────────────────────────────────────
Refrazione soggettiva:
  OD: {_f(rs_od.get("sf"))} / {_f(rs_od.get("cil"))} x {rs_od.get("ax",0)}°  Visus: {rs_od.get("acuita","n.d.")}
  OS: {_f(rs_os.get("sf"))} / {_f(rs_os.get("cil"))} x {rs_os.get("ax",0)}°  Visus: {rs_os.get("acuita","n.d.")}
  ADD vicino: {_f(sez_a.get("add_v"))}   ADD intermedia: {_f(sez_a.get("add_i"))}
  DP: {sez_a.get("dp","n.d.")} mm

Equilibrio binoculare:
  #3  Cover test lontano:    {sez_b.get("ct_l","n.d.")}  ({sez_b.get("ct_l_pr","n.d.")} dp)
  #13A Cover test vicino:    {sez_b.get("ct_v","n.d.")}  ({sez_b.get("ct_v_pr","n.d.")} dp)
  Maddox orizzontale lontano: {sez_b.get("madd_or_l","n.d.")} dp
  Maddox orizzontale vicino:  {sez_b.get("madd_or_v","n.d.")} dp
  #8  Vergenze BO lontano:   rot {sez_b.get("v8_bo",{}).get("rot","n.d.")} / rec {sez_b.get("v8_bo",{}).get("rec","n.d.")}
  #11 Vergenze BO vicino:    rot {sez_b.get("v11_bo",{}).get("rot","n.d.")} / rec {sez_b.get("v11_bo",{}).get("rec","n.d.")}
  #16 Jump vergenze 16BO/4BI: {sez_b.get("jv_16","n.d.")} c/min
  PPC accomodativo:  {sez_b.get("ppc_acc_rot","n.d.")} / {sez_b.get("ppc_acc_rec","n.d.")} cm
  PPC anaglífico:    {sez_b.get("ppc_an_rot","n.d.")} / {sez_b.get("ppc_an_rec","n.d.")} cm
  AC/A ratio:        {sez_b.get("aca","n.d.")}
  Worth lontano: {sez_b.get("worth_l","n.d.")}   vicino: {sez_b.get("worth_v","n.d.")}
  #7  Randot: {sez_b.get("randot","n.d.")} sec d arco
  Disparita fissazione lontano: {sez_b.get("disp_l","n.d.")} dp

Accomodazione:
  #14 Push-Up OD: {sez_c.get("pu_od","n.d.")} D   OS: {sez_c.get("pu_os","n.d.")} D
  #14B MEM OD:   {sez_c.get("mem_od","n.d.")} D   OS: {sez_c.get("mem_os","n.d.")} D
  Facilita accomodativa OD: {sez_c.get("fl_od","n.d.")} c/30sec   OS: {sez_c.get("fl_os","n.d.")} c/30sec
  Lag accomodativo OD: {sez_c.get("lag_od","n.d.")} D   OS: {sez_c.get("lag_os","n.d.")} D
  #20: {sez_c.get("t20","n.d.")}   #21: {sez_c.get("t21","n.d.")}

Oculomotricita (NSUCO):
  Saccadi H — Abilita: {sez_d.get("ns_or_ab","n.d.")} / Accuratezza: {sez_d.get("ns_or_ac","n.d.")}
  Saccadi V — Abilita: {sez_d.get("ns_ver_ab","n.d.")} / Accuratezza: {sez_d.get("ns_ver_ac","n.d.")}
  Pursuits H: {sez_d.get("pur_h","n.d.")}   V: {sez_d.get("pur_v","n.d.")}
  RRD: {sez_d.get("rrd","n.d.")}   IRD: {sez_d.get("ird","n.d.")}   Harmon: {sez_d.get("har","n.d.")}

Esame obiettivo:
  IOP OD: {sez_e.get("iop_od","n.d.")} mmHg   OS: {sez_e.get("iop_os","n.d.")} mmHg
  Pachimetria OD: {sez_e.get("pach_od","n.d.")} um   OS: {sez_e.get("pach_os","n.d.")} um

─────────────────────────────────────────────────────────
IPOTESI DIAGNOSTICA INTEGRATA
─────────────────────────────────────────────────────────
{ipotesi if ipotesi else (sez_g.get("diag","") or "Da completare.")}

─────────────────────────────────────────────────────────
PIANO TERAPEUTICO PROPOSTO
─────────────────────────────────────────────────────────
{piano if piano else (sez_g.get("piano","") or "Da definire.")}

─────────────────────────────────────────────────────────
ALLEGATI SCIENTIFICI DISPONIBILI
─────────────────────────────────────────────────────────
Su richiesta: scheda metodo PNEV, allegato disturbo uditivo centrale (CAPD),
allegato integrazione riflessi primitivi, allegato stimolazione multisensoriale.

Riferimenti: Ayres (2005), Kaplan (Seeing Through New Eyes),
Castagnini (Metodo FSC), Tomatis, Berard.

Luogo e data: {oggi}

Firma e timbro: ___________________________
{prof} — {spec}
Studio The Organism"""


# ══════════════════════════════════════════════════════════════════════
#  RELAZIONE SCUOLA
# ══════════════════════════════════════════════════════════════════════

def _genera_scuola(dati, prof, spec, scuola="", insegnante="", classe="", ipotesi="", piano=""):
    paz = dati.get("anagrafica",{})
    nome_paz = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn = paz.get("Data_Nascita","")
    dn_fmt = _fmt_dn(dn)
    anni, _ = _eta(dn)
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    pnev = dati.get("pnev_summary","") or ""
    visiva = dati.get("visita_visiva",{})
    sez_g = visiva.get("sez_g",{})
    diag_vis = sez_g.get("diag","") or ""

    scuola_str = scuola or "[Nome istituto scolastico]"
    ins_str = insegnante or "[Insegnante/Team docenti]"
    cl_str = classe or "[Classe]"

    return f"""COMUNICAZIONE ALLA SCUOLA — PERCORSO PNEV
Studio The Organism | {oggi}

Alla cortese attenzione di:
Dirigente Scolastico / Insegnanti referenti
{scuola_str}
{ins_str} — Classe {cl_str}

OGGETTO: Relazione clinica e indicazioni per il bambino/a {nome_paz}

─────────────────────────────────────────────────────────
DATI IDENTIFICATIVI
─────────────────────────────────────────────────────────
Alunno/a:         {nome_paz}
Data di nascita:  {dn_fmt}
Anno scolastico:  {datetime.date.today().year}/{datetime.date.today().year+1}

─────────────────────────────────────────────────────────
PERCORSO TERAPEUTICO IN CORSO
─────────────────────────────────────────────────────────
Il/la bambino/a è in carico presso lo Studio The Organism con un percorso
riabilitativo integrato basato sul Metodo PNEV (Processi NeuroEvolutivi).

Il Metodo PNEV è un approccio terapeutico che aiuta il bambino/a a migliorare
attenzione, apprendimento e comunicazione attraverso attività che coinvolgono
corpo, sensi e regolazione. Non è una terapia per il linguaggio o per i compiti,
ma un percorso che lavora sulle basi neuro-funzionali dello sviluppo.

─────────────────────────────────────────────────────────
PROFILO FUNZIONALE OSSERVATO
─────────────────────────────────────────────────────────
{pnev if pnev else "Il profilo funzionale evidenzia fragilità nelle aree dell attenzione, dell elaborazione sensoriale e/o della coordinazione visuo-motoria."}

{("Valutazione visiva: " + diag_vis) if diag_vis else ""}

─────────────────────────────────────────────────────────
COSA POTREBBE OSSERVARE IN CLASSE
─────────────────────────────────────────────────────────
Le difficolta osservate a scuola (affaticabilita, difficolta nel copiare dalla lavagna,
lentezza nella lettura e scrittura, difficolta di attenzione) possono essere ricondotte
alle fragilita neuro-funzionali rilevate nella valutazione e NON dipendono
dalla volonta o dall intelligenza del bambino/a.

─────────────────────────────────────────────────────────
INDICAZIONI PRATICHE PER LA CLASSE
─────────────────────────────────────────────────────────
Si raccomanda di:
- Posizionare il bambino/a nei banchi anteriori, con buona illuminazione
- Evitare testi in fotocopia di scarsa qualita o con font molto piccoli
- Concedere tempi aggiuntivi per le consegne scritte
- Preferire verifiche orali quando possibile
- Non richiedere lettura ad alta voce improvvisata davanti alla classe
- Segnalare qualsiasi variazione nel comportamento o nelle prestazioni

─────────────────────────────────────────────────────────
PIANO TERAPEUTICO E OBIETTIVI ATTESI
─────────────────────────────────────────────────────────
{piano if piano else "Il programma riabilitativo prevede sedute settimanali presso lo studio con attivita di stimolazione sensoriale integrata, visual training e stimolazione uditiva funzionale."}

Con il procedere del percorso ci aspettiamo miglioramenti progressivi in:
attenzione in classe, partecipazione, lettura e scrittura, autonomia organizzativa.

─────────────────────────────────────────────────────────
CERTIFICAZIONE DI FREQUENZA
─────────────────────────────────────────────────────────
Si certifica che {nome_paz} e attualmente inserito/a in un programma
riabilitativo continuativo presso lo Studio The Organism con frequenza
regolare alle sedute terapeutiche.

Rimaniamo a disposizione per un colloquio con il team docenti.

{oggi}

{prof}
{spec}
Studio The Organism
Via De Rosa, 46 - 84016 Pagani (SA) | Viale Marconi, 55 - 84013 Cava de' Tirreni SA
Tel. 0815152334 | apstheorganism@gmail.com

Firma e timbro: ___________________________"""


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
            f"📥 Scarica PDF",
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
    st.subheader("Relazione Clinica")
    st.caption("Metodo PNEV — Studio The Organism")

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

    def _label(r):
        if isinstance(r,dict): return f"{r.get('Cognome','')} {r.get('Nome','')}"
        return f"{r[1]} {r[2]}"
    def _get_id(r): return r["id"] if isinstance(r,dict) else r[0]
    def _get_dn(r): return (r.get("Data_Nascita","") if isinstance(r,dict) else (r[3] if len(r)>3 else ""))

    c1,c2 = st.columns([2,1])
    with c1:
        sel = st.selectbox("Paziente", pazienti, format_func=_label, key="rel_paz")
    paz_id = _get_id(sel)
    paz_label = _label(sel)
    dn = _get_dn(sel)
    try: dn_fmt = datetime.date.fromisoformat(str(dn)[:10]).strftime("%d/%m/%Y")
    except: dn_fmt = str(dn)
    paz_str = f"{paz_label}  |  Nato/a: {dn_fmt}"
    with c2:
        data_vis = st.date_input("Data relazione", value=datetime.date.today(), key="rel_data")
    data_str = data_vis.strftime("%d/%m/%Y")

    # Carica dati
    with st.spinner("Carico dati clinici..."):
        dati = _carica_dati_paziente(conn, paz_id)

    # Stato dati
    col1,col2,col3 = st.columns(3)
    col1.metric("Anamnesi", "✅" if dati.get("anamnesi") else "❌")
    col2.metric("Valutazione visiva", "✅" if dati.get("visita_visiva") else "❌")
    col3.metric("PNEV", "✅" if dati.get("pnev_summary") else "❌")

    st.markdown("---")

    prof = _get_prof()
    spec = _get_spec()

    # Campi comuni
    st.markdown("#### Ipotesi diagnostica e piano (opzionali — completano tutte le relazioni)")
    c3,c4 = st.columns(2)
    with c3:
        ipotesi = st.text_area("Ipotesi diagnostica integrata",
            height=100, key=f"rel_ipotesi_{paz_id}",
            placeholder="Es: Profilo compatibile con disturbo elaborazione visiva...")
    with c4:
        piano = st.text_area("Piano terapeutico",
            height=100, key=f"rel_piano_{paz_id}",
            placeholder="Es: Vision therapy 1x/settimana + stimolazione Hipérion...")

    st.markdown("---")

    tab_gen, tab_prof, tab_scuola = st.tabs([
        "👨‍👩‍👧 Genitori",
        "🏥 Professionisti (NPI/Logo/Medici)",
        "🏫 Scuola"
    ])

    # ── GENITORI ──────────────────────────────────────────────────────
    with tab_gen:
        testo_key = f"rel_gen_testo_{paz_id}"
        if st.button("📋 Genera lettera per i genitori",
                     key=f"rel_gen_btn_{paz_id}", type="primary"):
            st.session_state[testo_key] = _genera_genitori(
                dati, prof, spec, ipotesi=ipotesi, piano=piano)

        testo = st.text_area("Testo (modificabile prima di stampare)",
            value=st.session_state.get(testo_key,""),
            height=500, key=f"rel_gen_ta_{paz_id}")
        st.session_state[testo_key] = testo

        if testo:
            _pdf(testo, paz_str, data_str, prof, spec,
                 "LETTERA AI GENITORI", paz_id, "genitori")

    # ── PROFESSIONISTI ────────────────────────────────────────────────
    with tab_prof:
        testo_key2 = f"rel_prof_testo_{paz_id}"
        if st.button("📋 Genera relazione per professionisti",
                     key=f"rel_prof_btn_{paz_id}", type="primary"):
            st.session_state[testo_key2] = _genera_professionisti(
                dati, prof, spec, ipotesi=ipotesi, piano=piano)

        testo2 = st.text_area("Testo (modificabile prima di stampare)",
            value=st.session_state.get(testo_key2,""),
            height=500, key=f"rel_prof_ta_{paz_id}")
        st.session_state[testo_key2] = testo2

        if testo2:
            _pdf(testo2, paz_str, data_str, prof, spec,
                 "RELAZIONE CLINICA — AD USO DEI PROFESSIONISTI", paz_id, "professionisti")

    # ── SCUOLA ────────────────────────────────────────────────────────
    with tab_scuola:
        st.markdown("**Dati scolastici**")
        cs1,cs2,cs3 = st.columns(3)
        with cs1: scuola_nome = st.text_input("Nome istituto", key=f"rel_scuola_{paz_id}")
        with cs2: insegnante  = st.text_input("Insegnante/referente", key=f"rel_ins_{paz_id}")
        with cs3: classe      = st.text_input("Classe", key=f"rel_classe_{paz_id}")

        testo_key3 = f"rel_scuola_testo_{paz_id}"
        if st.button("📋 Genera comunicazione per la scuola",
                     key=f"rel_scuola_btn_{paz_id}", type="primary"):
            st.session_state[testo_key3] = _genera_scuola(
                dati, prof, spec,
                scuola=scuola_nome, insegnante=insegnante, classe=classe,
                ipotesi=ipotesi, piano=piano)

        testo3 = st.text_area("Testo (modificabile prima di stampare)",
            value=st.session_state.get(testo_key3,""),
            height=500, key=f"rel_scuola_ta_{paz_id}")
        st.session_state[testo_key3] = testo3

        if testo3:
            _pdf(testo3, paz_str, data_str, prof, spec,
                 "COMUNICAZIONE ALLA SCUOLA", paz_id, "scuola")
