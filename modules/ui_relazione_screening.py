# -*- coding: utf-8 -*-
"""Relazione di valutazione funzionale — generazione assistita dall'AI a
partire dai dati di uno screening/valutazione, sul modello cartaceo dello
Studio The Organism (5 pagine, carta intestata, riferimenti bibliografici).

Uso: chiamare `render_relazione(conn, paz_id, dati_valutazione, fonte)`
da qualunque modulo di valutazione — l'AI compila le sezioni descrittive
(3.1-3.4, 4 Lettura integrata, 5 Indicazioni), il resto è testo fisso del
modello. Output: anteprima modificabile + HTML stampabile A4 + salvataggio
in `relazioni_funzionali`.
"""
from __future__ import annotations
import datetime
import html as _html
import json
import streamlit as st
import streamlit.components.v1 as components


# ── Testo fisso del modello (invariante, non generato dall'AI) ──────────

_INTRO_CHI_SIAMO = (
    "Studio The Organism è un centro multidisciplinare con sedi a Pagani (SA) e Piano di Sorrento (NA). "
    "L'équipe riunisce competenze di psicologia e neuropsicologia, optometria comportamentale, logopedia, "
    "osteopatia e terapia miofunzionale, e lavora secondo il metodo PNEV.\n\n"
    "PNEV è l'acronimo di Psico-Neuro-Evolutivo. Indica un approccio che guarda il bambino come un sistema "
    "unico anziché come una somma di funzioni separate. Il riferimento teorico è l'integrazione sensoriale "
    "descritta da Jean Ayres: i sistemi di base — vestibolare, propriocettivo, uditivo, tattile, visivo — "
    "costituiscono il fondamento su cui si costruiscono controllo motorio, linguaggio, apprendimenti e "
    "funzioni esecutive. Quando uno di questi fondamenti è instabile, la difficoltà compare più in alto: "
    "nella lettura, nella scrittura, nell'attenzione, nel comportamento.\n\n"
    "A questo si affianca una lettura del sintomo che risale a Kurt Goldstein: ciò che chiamiamo deficit è "
    "spesso una soluzione che l'organismo ha trovato per far fronte all'ambiente con le risorse disponibili. "
    "Un bambino che inclina il capo mentre legge, che respira con la bocca, che evita la linea mediana, si "
    "sta adattando. La domanda clinica diventa allora a che cosa stia rispondendo, e con quale costo."
)

_MODELLO_LETTURA = (
    "Il nostro modo di guardare un bambino parte da un'idea semplice: le funzioni che vediamo in difficoltà "
    "— leggere, scrivere, stare attenti, parlare bene — non poggiano su sé stesse. Poggiano su sistemi più "
    "elementari che si sono costruiti molto prima: l'equilibrio, la percezione del corpo nello spazio, "
    "l'ascolto, la vista, il movimento degli occhi, la respirazione. Quando uno di questi fondamenti è "
    "instabile, la difficoltà non compare lì: compare più in alto, dove il bambino viene valutato. Si "
    "interviene allora dove il sintomo si vede, non dove si è formato.\n\n"
    "È il principio dell'integrazione sensoriale descritto da Jean Ayres. A questo affianchiamo una lettura "
    "del sintomo che risale a Kurt Goldstein: ciò che chiamiamo difficoltà è spesso una soluzione che "
    "l'organismo ha trovato per far fronte all'ambiente con le risorse di cui disponeva. La domanda non è "
    "che cosa abbia, ma a che cosa stia rispondendo e con quale costo.\n\n"
    "Per questo la valutazione guarda in un'unica sessione aree che di solito vengono esaminate da "
    "professionisti diversi in momenti diversi. Il valore non sta nel numero di prove, ma negli incroci: è "
    "mettendo insieme rilievi che presi singolarmente direbbero poco che si capisce da dove conviene cominciare."
)

_PREMESSE_AREE = {
    "linguaggio": (
        "Il linguaggio è il sistema su cui si costruiscono la lettura e la scrittura. Prima ancora del "
        "vocabolario contano due capacità meno visibili: tenere in mente una sequenza di suoni abbastanza a "
        "lungo da riprodurla, e organizzare le parole in frasi complesse. Sono le abilità che mettiamo alla "
        "prova chiedendo di ripetere frasi e parole senza significato, perché non si possono superare con un "
        "vocabolario ricco o con un ambiente familiare favorevole. Accanto a queste osserviamo come vengono "
        "prodotti i suoni, quanto il bambino risulta comprensibile a chi non lo conosce, e come racconta un "
        "fatto dall'inizio alla fine."),
    "visione": (
        "Vedere bene non significa leggere bene. Un bambino può avere dieci decimi e faticare moltissimo, "
        "perché la lettura richiede altro: che i due occhi lavorino insieme sulla stessa parola, che riescano "
        "a mantenere la messa a fuoco da vicino per il tempo necessario, e che si spostino lungo la riga con "
        "movimenti precisi senza trascinarsi dietro la testa. Sono funzioni che nessuna visita di controllo "
        "dell'acuità visiva indaga, e che quando sono deboli si manifestano come stanchezza, salti di riga, "
        "riletture, rifiuto del compito scritto — cioè come un problema di impegno."),
    "riflessi": (
        "Nei primi mesi di vita alcuni schemi motori automatici guidano il movimento del bambino e poi si "
        "integrano, lasciando il posto al controllo volontario. Quando qualcuno di questi schemi resta attivo "
        "oltre il tempo previsto, continua a interferire: la posizione del capo influenza quella del braccio, "
        "stare seduti composti costa fatica, il gesto grafico non diventa automatico e consuma attenzione che "
        "servirebbe al contenuto. Osserviamo la loro persistenza insieme all'equilibrio, alla coordinazione "
        "dei due lati del corpo e alla capacità di attraversare la linea mediana."),
    "altre": (
        "A seconda del quadro sono state valutate anche la respirazione e l'assetto oro-facciale, l'assetto "
        "posturale e le abilità di apprendimento. Di seguito i rilievi che meritano di essere riportati."),
}

_DISCLAIMER_INDICAZIONI = (
    "Questa valutazione è funzionale: descrive come il bambino funziona nelle aree esaminate e indica da dove "
    "conviene partire. Non è una diagnosi e non la sostituisce. Quando emergono elementi che richiedono un "
    "inquadramento diagnostico — per i disturbi dell'apprendimento la procedura è definita dalla Legge "
    "170/2010 e dalla Consensus Conference dell'Istituto Superiore di Sanità — l'indicazione è di rivolgersi "
    "a chi è titolato a formularlo, con strumenti tarati.\n\n"
    "Perché l'approfondimento conta. Una prima osservazione, per quanto accurata, dura poche decine di minuti "
    "e fotografa una mattina. Serve a capire dove guardare, non a dire tutto. L'approfondimento aggiunge tre "
    "cose che qui mancano: il tempo, che fa emergere l'affaticabilità e le strategie di compenso; gli "
    "strumenti tarati, che dicono dove si colloca il bambino rispetto ai suoi coetanei e non rispetto a un "
    "criterio interno; e la ripetizione nel tempo, che distingue una difficoltà stabile da un momento. "
    "Rinviare non rende il quadro più chiaro: rende solo più lungo il periodo in cui il bambino affronta la "
    "scuola con un carico che nessuno ha ancora misurato."
)

_OPZIONI_APPROFONDIMENTO = [
    "Approfondimento neuropsicologico", "Approfondimento logopedico",
    "Approfondimento optometrico funzionale", "Valutazione oftalmologica",
    "Approfondimento miofunzionale", "Valutazione ORL / audiologica",
    "Approfondimento osteopatico e posturale", "Integrazione dei riflessi dello sviluppo",
    "Training visuo-percettivo", "Stimolazione multisensoriale (protocollo MAPS)",
    "Parent training", "Nessun approfondimento al momento",
]

_RIFERIMENTI = [
    ("Fonologia", "Shriberg, L.D., Kwiatkowski, J. (1982). Phonological disorders III: A procedure for assessing severity of involvement. Journal of Speech and Hearing Disorders, 47, 256–270."),
    ("Linguaggio", "Conti-Ramsden, G., Botting, N., Faragher, B. (2001). Psycholinguistic markers for specific language impairment (SLI). Journal of Child Psychology and Psychiatry, 42(6), 741–748."),
    ("Linguaggio", "Bishop, D.V.M., North, T., Donlan, C. (1996). Nonword repetition as a behavioural marker for inherited language impairment. Journal of Child Psychology and Psychiatry, 37, 391–403."),
    ("Linguaggio", "Bortolini, U., Caselli, M.C., Deevy, P., Leonard, L.B. (2002). Specific language impairment in Italian. International Journal of Language & Communication Disorders, 37(1)."),
    ("Fluenza", "Yairi, E., Ambrose, N.G. (2005). Early Childhood Stuttering. Austin: Pro-Ed."),
    ("Lettura", "Trauzettel-Klosinski, S., Dietz, K., IReST Study Group (2012). Standardized assessment of reading performance: the New International Reading Speed Texts IReST. Investigative Ophthalmology & Visual Science, 53(9), 5452–5461. Versione italiana a cura di G. Stella."),
    ("Apprendimenti", "Istituto Superiore di Sanità (2011). Consensus Conference sui Disturbi Specifici dell'Apprendimento. Sistema Nazionale Linee Guida. Legge 170/2010."),
    ("Grafia", "Graham, S., Berninger, V.W. et al. (1997). Role of mechanics in composing of elementary school students. Journal of Educational Psychology, 89, 170–182."),
    ("Grafia", "Rosenblum, S., Weiss, P.L., Parush, S. (2003). Product and process evaluation of handwriting difficulties. Educational Psychology Review, 15, 41–81."),
    ("Oculomotorio", "Maples, W.C., Atchley, J., Ficklin, T. (1992). Northeastern State University College of Optometry's oculomotor norms. Journal of Behavioral Optometry, 3, 143–150."),
    ("Visivo", "Scheiman, M., Wick, B. Clinical Management of Binocular Vision. Philadelphia: Lippincott Williams & Wilkins."),
    ("Postura", "Gagey, P.M., Weber, B. Posturologie: régulation et dérèglements de la station debout. Paris: Masson."),
    ("Neuromotorio", "Ayres, A.J. (2005). Sensory Integration and the Child. Los Angeles: Western Psychological Services."),
    ("Neuromotorio", "Goddard Blythe, S. Attention, Balance and Coordination: The A.B.C. of Learning Success. Chichester: Wiley."),
]


# ── Database ───────────────────────────────────────────────────────────

def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS relazioni_funzionali (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_relazione DATE,
                fonte TEXT,
                sezioni JSONB,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva(conn, paz_id, fonte, sezioni) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO relazioni_funzionali (paziente_id, data_relazione, fonte, sezioni)
            VALUES (%s, CURRENT_DATE, %s, %s)
        """, (paz_id, fonte, json.dumps(sezioni, default=str)))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio relazione: {e}")
        return False


def _dati_paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT "Cognome", "Nome", "DataNascita", scuola, classe
                       FROM pazienti WHERE id=%s""", (paz_id,))
        r = cur.fetchone()
        if not r:
            return {}
        if hasattr(r, "get"):
            r = dict(r)
            return {"cognome": r.get("Cognome", ""), "nome": r.get("Nome", ""),
                    "dn": r.get("DataNascita"), "scuola": r.get("scuola", ""),
                    "classe": r.get("classe", "")}
        return {"cognome": r[0] or "", "nome": r[1] or "", "dn": r[2],
                "scuola": r[3] or "", "classe": r[4] or ""}
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return {}


# ── Generazione AI ─────────────────────────────────────────────────────

_SISTEMA = (
    "Sei il neuropsicologo dello Studio The Organism e scrivi la relazione di valutazione funzionale "
    "secondo il metodo PNEV. Stile: italiano clinico ma leggibile da un genitore, frasi piene, nessun "
    "elenco puntato, nessun tecnicismo non spiegato, mai allarmistico. Descrivi prestazioni osservate, "
    "non diagnosi: non usare mai etichette diagnostiche (dislessia, DSA, disprassia, ADHD) e non scrivere "
    "che il bambino 'ha' un disturbo. Se per un'area non ci sono dati, scrivi una sola frase che dichiara "
    "che l'area non è stata esaminata in questa sessione. Non inventare dati che non ti sono stati forniti."
)


def _genera_sezioni_ai(dati_valutazione, paziente, motivo):
    """Chiede all'AI le sole sezioni descrittive. Ritorna dict con chiavi
    linguaggio/visione/riflessi/altre/integrata/priorita, o None se l'AI
    non è disponibile."""
    try:
        from .ai_estrazione import genera_testo, ai_disponibile
        if not ai_disponibile():
            return None
    except Exception:
        return None

    nome = f"{paziente.get('nome','')} {paziente.get('cognome','')}".strip() or "il bambino"
    prompt = (
        f"Scrivi le sezioni descrittive della relazione di valutazione funzionale di {nome}.\n"
        f"Motivo della richiesta: {motivo or 'non specificato'}\n\n"
        f"DATI RACCOLTI NELLA VALUTAZIONE (JSON):\n{json.dumps(dati_valutazione, default=str, ensure_ascii=False)[:12000]}\n\n"
        "Produci esattamente sei blocchi, ciascuno introdotto dal suo marcatore su una riga da sola, "
        "senza altri titoli:\n"
        "@@LINGUAGGIO@@ — che cosa è emerso su fonologia, ripetizione, lessico, morfosintassi, narrazione, fluenza.\n"
        "@@VISIONE@@ — che cosa è emerso su binocularità, accomodazione, motilità oculare, saccadi in lettura.\n"
        "@@RIFLESSI@@ — che cosa è emerso su riflessi dello sviluppo, equilibrio, coordinazione bilaterale, linea mediana.\n"
        "@@ALTRE@@ — rilievi su respirazione e assetto oro-facciale, postura, apprendimenti (lettura, scrittura, grafia, calcolo).\n"
        "@@INTEGRATA@@ — lettura integrata del profilo: quali rilievi si sostengono a vicenda, quale sembra "
        "venire prima degli altri, che cosa spiega ciò che famiglia e insegnanti osservano ogni giorno. "
        "Questa è la parte più importante: due o tre paragrafi.\n"
        "@@PRIORITA@@ — priorità e ordine suggerito degli interventi/approfondimenti, con una breve "
        "motivazione clinica dell'ordine proposto.\n"
    )
    with st.spinner("Genero la relazione con l'AI…"):
        testo = genera_testo(prompt, _SISTEMA)
    if not testo or testo.startswith("⚠️"):
        return None

    out, corrente = {}, None
    mappa = {"@@LINGUAGGIO@@": "linguaggio", "@@VISIONE@@": "visione", "@@RIFLESSI@@": "riflessi",
             "@@ALTRE@@": "altre", "@@INTEGRATA@@": "integrata", "@@PRIORITA@@": "priorita"}
    for riga in testo.splitlines():
        chiave = riga.strip()
        if chiave in mappa:
            corrente = mappa[chiave]
            out[corrente] = ""
        elif corrente:
            out[corrente] += riga + "\n"
    return {k: v.strip() for k, v in out.items()} or None


# ── HTML stampabile A4 ─────────────────────────────────────────────────

def _p(testo):
    """Paragrafi HTML da testo con righe vuote come separatore."""
    blocchi = [b.strip() for b in (testo or "").split("\n\n") if b.strip()]
    if not blocchi:
        return "<p class='vuoto'>—</p>"
    return "".join(f"<p>{_html.escape(b).replace(chr(10), '<br>')}</p>" for b in blocchi)


def _costruisci_html(paziente, campi, sez, approfondimenti, equipe, firme):
    rif_righe = "".join(
        f"<tr><td class='ambito'>{_html.escape(a)}</td><td>{_html.escape(t)}</td></tr>"
        for a, t in _RIFERIMENTI)
    appr_celle = "".join(
        f"<div class='chk'>{'☒' if o in approfondimenti else '☐'} {_html.escape(o)}</div>"
        for o in _OPZIONI_APPROFONDIMENTO)
    firme_righe = "".join(
        f"<div class='firma'><span>{_html.escape(f) if f else '__________________________________'}</span>"
        f"<span>Firma ______________________________</span></div>"
        for f in (firme or [""] * 3))

    return f"""<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<title>Relazione di valutazione funzionale</title>
<style>
@page {{ size: A4; margin: 17mm 15mm 20mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Georgia, 'Times New Roman', serif; font-size: 9.6pt; line-height: 1.5;
        color: #1a1a1a; margin: 0; }}
.intestazione {{ border-bottom: 1.5px solid #14502F; padding-bottom: 5px; margin-bottom: 14px; }}
.intestazione .dott {{ font-size: 9.6pt; font-weight: bold; color: #14502F; }}
h1 {{ font-size: 15pt; color: #14502F; margin: 12px 0 2px; letter-spacing: .3px; }}
.sub {{ font-size: 9.2pt; font-style: italic; color: #4a5a52; margin: 0 0 16px; }}
h2 {{ font-size: 10.6pt; color: #14502F; margin: 18px 0 6px; padding-bottom: 3px;
      border-bottom: .8px solid #c9d6cf; text-transform: uppercase; letter-spacing: .4px; }}
h3 {{ font-size: 10pt; color: #14502F; margin: 13px 0 4px; }}
p {{ margin: 0 0 7px; text-align: justify; }}
.premessa {{ font-size: 8.8pt; color: #46564e; font-style: italic; background: #f4f8f6;
             border-left: 2.5px solid #1D6B44; padding: 7px 10px; margin: 0 0 8px; }}
.premessa p {{ margin: 0 0 4px; }}
.vuoto {{ color: #9aa8a1; }}
table.dati {{ width: 100%; border-collapse: collapse; margin-bottom: 6px; }}
table.dati td {{ border: .8px solid #c9d6cf; padding: 5px 7px; font-size: 9.2pt; }}
table.dati td.et {{ background: #f4f8f6; font-variant: small-caps; color: #14502F;
                    font-weight: bold; width: 21%; }}
.chkgrid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3px 14px; margin: 8px 0 10px;
            font-size: 9.2pt; }}
.chk {{ padding: 1px 0; }}
table.rif {{ width: 100%; border-collapse: collapse; font-size: 7.8pt; }}
table.rif td {{ border-bottom: .5px solid #dde6e1; padding: 3px 5px; vertical-align: top; }}
table.rif td.ambito {{ width: 16%; color: #14502F; font-weight: bold; }}
.firma {{ display: flex; justify-content: space-between; margin-top: 16px; font-size: 9.2pt; }}
.pie {{ border-top: .8px solid #c9d6cf; margin-top: 20px; padding-top: 5px;
        font-size: 7.4pt; color: #5b6b63; text-align: center; }}
.noprint {{ margin-bottom: 12px; }}
@media print {{ .noprint {{ display: none !important; }} }}
button {{ background: #1D6B44; color: #fff; border: 0; border-radius: 4px; padding: 7px 14px;
          font-size: 12px; font-family: sans-serif; cursor: pointer; }}
</style></head><body>

<div class="noprint"><button onclick="window.print()">🖨️ Stampa / Salva come PDF</button></div>

<div class="intestazione">
  <div class="dott">Dott. Giuseppe Ferraioli — Psicologo, Neuropsicologo, Optometrista comportamentale</div>
</div>

<h1>Relazione di valutazione funzionale</h1>
<p class="sub">Screening multidisciplinare secondo il metodo PNEV (Psico-Neuro-Evolutivo)</p>

<h2>Chi siamo e che cosa facciamo</h2>
{_p(_INTRO_CHI_SIAMO)}

<h2>1. Dati del bambino</h2>
<table class="dati">
  <tr><td class="et">Nome</td><td>{_html.escape(paziente.get('nome',''))}</td>
      <td class="et">Cognome</td><td>{_html.escape(paziente.get('cognome',''))}</td></tr>
  <tr><td class="et">Data di nascita</td><td>{_html.escape(campi.get('dn',''))}</td>
      <td class="et">Età</td><td>{_html.escape(campi.get('eta',''))}</td></tr>
  <tr><td class="et">Scuola / classe</td><td>{_html.escape(campi.get('scuola',''))}</td>
      <td class="et">Data valutazione</td><td>{_html.escape(campi.get('data',''))}</td></tr>
  <tr><td class="et">Inviato da</td><td>{_html.escape(campi.get('inviato_da',''))}</td>
      <td class="et">Motivo</td><td>{_html.escape(campi.get('motivo',''))}</td></tr>
  <tr><td class="et">Équipe</td><td colspan="3">{_html.escape(equipe or '')}</td></tr>
</table>

<h2>2. Il modello di lettura: l'integrazione sensoriale</h2>
{_p(_MODELLO_LETTURA)}

<h2>3. Che cosa abbiamo osservato</h2>

<h3>3.1 Linguaggio</h3>
<div class="premessa">{_p(_PREMESSE_AREE['linguaggio'])}</div>
{_p(sez.get('linguaggio'))}

<h3>3.2 Visione</h3>
<div class="premessa">{_p(_PREMESSE_AREE['visione'])}</div>
{_p(sez.get('visione'))}

<h3>3.3 Riflessi dello sviluppo e organizzazione motoria</h3>
<div class="premessa">{_p(_PREMESSE_AREE['riflessi'])}</div>
{_p(sez.get('riflessi'))}

<h3>3.4 Altre aree esaminate</h3>
<div class="premessa">{_p(_PREMESSE_AREE['altre'])}</div>
{_p(sez.get('altre'))}

<h2>4. Lettura integrata del profilo</h2>
{_p(sez.get('integrata'))}

<h2>5. Indicazioni e approfondimento</h2>
{_p(_DISCLAIMER_INDICAZIONI)}
<div class="chkgrid">{appr_celle}</div>
<h3>Priorità e ordine suggerito</h3>
{_p(sez.get('priorita'))}

<h2>7. Riferimenti</h2>
<p style="font-size:8pt;font-style:italic;color:#5b6b63">Riferimenti dei criteri adottati nelle prove
impiegate. Citare il lavoro di riferimento di un criterio non equivale a dichiarare che la prova
somministrata sia tarata: le prove costruite per questo protocollo restano criteriali e clinico-osservative.</p>
<table class="rif">{rif_righe}</table>

<h2>8. Firme</h2>
<p>Cordiali saluti,</p>
<div class="firma"><span>Dott. Giuseppe Ferraioli</span><span>Firma ______________________________</span></div>
{firme_righe}
<p style="margin-top:14px">Pagani, lì {_html.escape(campi.get('data',''))}</p>

<div class="pie">
  Studio Associato The Organism — Via De Rosa, 46 — Pagani (SA) — Tel. 081 5152334 · 393 581 7157 —
  dr.ferraioligiuseppe@gmail.com<br>
  www.pnev.it · www.theorganism.it · www.ferraioligiuseppe.it
</div>

</body></html>"""


# ── UI ─────────────────────────────────────────────────────────────────

def render_relazione(conn, paz_id, dati_valutazione=None, fonte="screening", kp="rel"):
    """Blocco riusabile: genera la relazione con l'AI dai dati passati,
    permette di correggerla, la stampa in A4 e la salva nel fascicolo."""
    st.markdown("#### 📄 Relazione di valutazione funzionale")
    st.caption("L'AI compila le parti descrittive dai dati della valutazione; le premesse teoriche, "
               "il disclaimer e i riferimenti sono testo fisso del modello. Rileggi e correggi prima di stampare.")

    if conn is None or not paz_id:
        st.info("Serve un paziente selezionato.")
        return
    _assicura_tabella(conn)

    paziente = _dati_paziente(conn, paz_id)
    dn_txt = ""
    eta_txt = ""
    if paziente.get("dn"):
        try:
            dn = paziente["dn"]
            if isinstance(dn, str):
                dn = datetime.date.fromisoformat(dn[:10])
            dn_txt = dn.strftime("%d/%m/%Y")
            oggi = datetime.date.today()
            anni = oggi.year - dn.year - ((oggi.month, oggi.day) < (dn.month, dn.day))
            mesi = (oggi.month - dn.month) % 12
            eta_txt = f"{anni} anni e {mesi} mesi"
        except Exception:
            pass

    c1, c2 = st.columns(2)
    inviato_da = c1.text_input("Inviato da", key=f"{kp}_inviato_da")
    motivo = c2.text_input("Motivo della richiesta", key=f"{kp}_motivo")
    c3, c4 = st.columns(2)
    scuola_classe = c3.text_input("Scuola / classe",
                                   value=f"{paziente.get('scuola','')} {paziente.get('classe','')}".strip(),
                                   key=f"{kp}_scuola")
    data_val = c4.text_input("Data valutazione",
                              value=datetime.date.today().strftime("%d/%m/%Y"), key=f"{kp}_data")
    equipe = st.text_input("Équipe che ha valutato", key=f"{kp}_equipe")

    if st.button("🤖 Genera la relazione con l'AI", key=f"{kp}_genera", type="primary"):
        sez = _genera_sezioni_ai(dati_valutazione or {}, paziente, motivo)
        if sez is None:
            st.warning("AI non disponibile o non configurata: compila i campi a mano qui sotto.")
            sez = {}
        st.session_state[f"{kp}_sez"] = sez

    sez = st.session_state.get(f"{kp}_sez", {})

    st.markdown("##### Testi della relazione (modificabili)")
    sez["linguaggio"] = st.text_area("3.1 Linguaggio — che cosa è emerso",
                                      value=sez.get("linguaggio", ""), height=130, key=f"{kp}_t_ling")
    sez["visione"] = st.text_area("3.2 Visione — che cosa è emerso",
                                   value=sez.get("visione", ""), height=130, key=f"{kp}_t_vis")
    sez["riflessi"] = st.text_area("3.3 Riflessi dello sviluppo — che cosa è emerso",
                                    value=sez.get("riflessi", ""), height=130, key=f"{kp}_t_rifl")
    sez["altre"] = st.text_area("3.4 Altre aree — rilievi",
                                 value=sez.get("altre", ""), height=110, key=f"{kp}_t_altre")
    sez["integrata"] = st.text_area("4. Lettura integrata del profilo",
                                     value=sez.get("integrata", ""), height=170, key=f"{kp}_t_integr")
    sez["priorita"] = st.text_area("5. Priorità e ordine suggerito",
                                    value=sez.get("priorita", ""), height=130, key=f"{kp}_t_prior")

    approfondimenti = st.multiselect("Approfondimenti indicati", _OPZIONI_APPROFONDIMENTO,
                                      key=f"{kp}_appr")
    rivalutazione = st.text_input("Rivalutazione a ___ mesi", key=f"{kp}_rival")
    firme_extra = st.text_area("Altri professionisti firmatari (uno per riga)", height=68, key=f"{kp}_firme")

    campi = {"dn": dn_txt, "eta": eta_txt, "scuola": scuola_classe, "data": data_val,
             "inviato_da": inviato_da, "motivo": motivo}
    appr_finali = list(approfondimenti)
    if rivalutazione.strip():
        appr_finali.append(f"Rivalutazione a {rivalutazione.strip()} mesi")
    firme = [f.strip() for f in (firme_extra or "").splitlines() if f.strip()] or [""] * 3

    html_rel = _costruisci_html(paziente, campi, sez, appr_finali, equipe, firme)

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("💾 Salva nel fascicolo", key=f"{kp}_salva"):
            payload = {"campi": campi, "sezioni": sez, "approfondimenti": appr_finali,
                       "equipe": equipe, "firme": firme}
            if _salva(conn, paz_id, fonte, payload):
                st.success("Relazione salvata nel fascicolo del paziente.")
    with cb2:
        st.download_button("⬇️ Scarica la relazione (HTML stampabile)", data=html_rel,
                            file_name=f"relazione_{paziente.get('cognome','paziente')}_{data_val.replace('/','-')}.html",
                            mime="text/html", key=f"{kp}_dl")

    with st.expander("👁️ Anteprima stampabile (A4)", expanded=False):
        components.html(html_rel, height=900, scrolling=True)
