# -*- coding: utf-8 -*-
"""Apprendimenti — strumenti ad accesso libero.

Catalogo ragionato e registrazione dei punteggi per le prove di lettura,
scrittura, calcolo, linguaggio e attenzione disponibili gratuitamente con
taratura italiana (DeCoNe/Padova, Fondazione Santa Lucia, AIRIPA, COST).

PERCHÉ ESISTE QUESTA AREA
Gli strumenti open coprono bene lettura e prerequisiti, male il calcolo,
pochissimo il linguaggio, per niente il livello cognitivo. Servono a
individuare chi è a rischio e a misurare i progressi nel tempo, non a
certificare. Ogni scheda dice cosa quello strumento può e non può
sostenere: è la differenza fra usarli bene e usarli male.

LIMITE DA NON AGGIRARE
Nessun test di livello cognitivo è libero e tarato in italiano. Poiché il
funzionamento cognitivo nella norma è criterio diagnostico per i DSA, una
certificazione non può poggiare su questi materiali. Screening sì,
monitoraggio sì, diagnosi no.
"""
from __future__ import annotations

import base64
import json

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

try:
    import psycopg2
except Exception:
    psycopg2 = None

# ── Catalogo ─────────────────────────────────────────────────────────
# "puo": cosa lo strumento sostiene legittimamente
# "non_puo": l'uso scorretto da cui mettere in guardia
STRUMENTI = {
    "🔤 Prerequisiti (ultimo anno infanzia · 1ª primaria)": [
        {
            "nome": "RAN — Denominazione rapida automatizzata",
            "bibliografia": "Denckla M.B., Rudel R.G. (1976). Rapid automatized naming (R.A.N.): dyslexia differentiated from other learning disabilities. *Neuropsychologia*, 14(4), 471-479. · Materiali e tarature: Laboratorio DeCoNe, Dipartimento di Psicologia dello Sviluppo, Università di Padova.",
            "fonte": "DeCoNe, Università di Padova",
            "eta": "5-7 anni", "durata": "5 min",
            "norme": "Taratura italiana DeCoNe",
            "misura": "Velocità di accesso al lessico: lettere e colori da denominare "
                      "il più rapidamente possibile.",
            "puo": "È il predittore singolo più solido della futura fluenza di lettura: "
                   "un RAN lento all'ultimo anno di infanzia segnala rischio prima che "
                   "la lettura sia insegnata.",
            "non_puo": "Non è una diagnosi di dislessia e non si somministra a chi legge già bene: "
                       "a quel punto misuri la lettura direttamente.",
            "link": "https://dpg.unipd.it/en/deconelab/materiali",
            "campi": ["Lettere forma O (sec)", "Lettere forma V (sec)",
                      "Colori forma O (sec)", "Colori forma V (sec)", "Errori"],
        },
        {
            "nome": "RAN e Ricerca visiva — versione Santa Lucia",
            "bibliografia": "Fondazione Santa Lucia IRCCS, Laboratorio di Dislessia (2016). *RAN e Ricerca visiva: manuale e norme*. Roma.",
            "fonte": "Fondazione Santa Lucia, Lab. Dislessia",
            "eta": "6-11 anni", "durata": "8 min",
            "norme": "Norme italiane 2016",
            "misura": "RAN più prova di ricerca visiva: separa la lentezza di denominazione "
                      "da quella di scansione visiva.",
            "puo": "Distinguere se il rallentamento nasce dall'accesso lessicale o dall'esplorazione "
                   "dello spazio — due strade terapeutiche diverse.",
            "non_puo": "Non sostituisce una valutazione oculomotoria: se sospetti un problema di "
                       "motilità, serve l'esame visivo.",
            "link": "https://www.hsantalucia.it/it/lab-dislessia",
            "campi": ["RAN tempo (sec)", "RAN errori",
                      "Ricerca visiva tempo (sec)", "Ricerca visiva errori"],
        },
    ],
    "📖 Lettura (primaria)": [
        {
            "nome": "Batteria DeCoNe — Lettura",
            "bibliografia": "Batteria DeCoNe per la lettura — manuale del somministratore e tarature. Laboratorio DeCoNe, Università di Padova.",
            "fonte": "DeCoNe, Università di Padova",
            "eta": "1ª-5ª primaria", "durata": "15 min",
            "norme": "Tarature per classe scolastica",
            "misura": "Lettura di parole, non parole e brano: rapidità e correttezza.",
            "puo": "È la prova open più vicina alle batterie commerciali per struttura e "
                   "tarature. Regge come misura principale in uno screening scolastico "
                   "e come verifica pre/post trattamento.",
            "non_puo": "Le tarature non sostituiscono le MT o la DDE-2 in sede di certificazione: "
                       "servono i test che la commissione riconosce.",
            "link": "https://dpg.unipd.it/en/deconelab/materiali",
            "campi": ["Parole: sec", "Parole: errori", "Non parole: sec", "Non parole: errori",
                      "Brano: sec", "Brano: errori", "Sillabe/sec"],
        },
        {
            "nome": "Lettura di parole e non parole — Santa Lucia",
            "bibliografia": "Fondazione Santa Lucia IRCCS, Laboratorio di Dislessia. *Lettura di parole e non parole: manuale, test e foglio di notazione*. Roma.",
            "fonte": "Fondazione Santa Lucia",
            "eta": "6-13 anni", "durata": "10 min",
            "norme": "Norme italiane",
            "misura": "Liste di parole e non parole, tempo ed errori.",
            "puo": "Il confronto parole/non parole separa la via lessicale da quella fonologica: "
                   "è il dato che orienta il trattamento più di ogni altro.",
            "non_puo": "Da sola non descrive la comprensione: un bambino può leggere veloce e "
                       "non capire nulla.",
            "link": "https://www.hsantalucia.it/it/lab-dislessia",
            "campi": ["Parole: sec", "Parole: errori",
                      "Non parole: sec", "Non parole: errori", "Rapporto P/NP"],
        },
        {
            "nome": "PLS — Prova di Lettura Sublessicale",
            "bibliografia": "Calgaro A., Toffalini E., Cornoldi C. (2018). La Prova di Lettura Sublessicale (PLS) per la prima primaria. *Dislessia*, AIRIPA.",
            "fonte": "Calgaro, Toffalini, Cornoldi (2018) · AIRIPA",
            "eta": "1ª primaria", "durata": "5 min",
            "norme": "Tarature nell'articolo di riferimento",
            "misura": "Lettura di sillabe e gruppi sublessicali a inizio percorso.",
            "puo": "Intercettare in prima primaria chi non ha ancora automatizzato la conversione "
                   "grafema-fonema, quando intervenire costa poco.",
            "non_puo": "In prima primaria nessuna prova può porre diagnosi di dislessia: "
                       "la diagnosi di lettura si fa da fine seconda.",
            "link": "https://www.airipa.it/materiali/strumenti-e-software/",
            "campi": ["Sillabe lette in 60s", "Errori"],
        },
    ],
    "✍️ Scrittura e ortografia": [
        {
            "nome": "Batteria COST",
            "bibliografia": "Batteria COST — prove di lettura e scrittura con tarature. Progetto COST.",
            "fonte": "Progetto COST",
            "eta": "primaria e secondaria I grado", "durata": "20 min",
            "norme": "Tarature incluse nel materiale",
            "misura": "Dettato di brano e prove di lettura con analisi degli errori ortografici.",
            "puo": "Classificare gli errori per tipo — fonologici, non fonologici, fonetici — "
                   "che è ciò che determina il piano di lavoro.",
            "non_puo": "La grafia (tratto, velocità, leggibilità) non è valutata: per la disgrafia "
                       "serve altro.",
            "link": "https://www.sbilf.eu",
            "campi": ["Errori fonologici", "Errori non fonologici", "Errori fonetici",
                      "Tempo dettato (min)", "Parole/min"],
        },
    ],
    "🔢 Calcolo": [
        {
            "nome": "Numeracy Screener",
            "bibliografia": "Nosworthy N., Bugden S., Archibald L., Evans B., Ansari D. (2013). A two-minute paper-and-pencil test of symbolic and nonsymbolic numerical magnitude processing explains variability in primary school children's arithmetic competence. *PLoS ONE*, 8(7), e67918. ⚠️ Dati normativi canadesi.",
            "fonte": "Numerical Cognition Lab, Western University",
            "eta": "5-9 anni", "durata": "2 min",
            "norme": "⚠️ Dati canadesi (658 bambini, Ontario) — riferimento orientativo, "
                     "NON taratura italiana",
            "misura": "Confronto di quantità simboliche e non simboliche.",
            "puo": "Screening collettivo rapido e non verbale, utile anche con bambini "
                   "non italofoni.",
            "non_puo": "I percentili canadesi non sono trasferibili: usalo per ordinare una "
                       "classe dal più al meno fragile, mai per dire «sotto la norma».",
            "link": "https://www.numeracyscreener.org",
            "campi": ["Simbolico: corretti", "Non simbolico: corretti", "Tempo (min)"],
        },
        {
            "nome": "Intervention Central — generatori di prove",
            "bibliografia": "Wright J. *Intervention Central* — Curriculum-Based Measurement generators. interventioncentral.org. Misure a criterio, senza norme.",
            "fonte": "interventioncentral.org",
            "eta": "tutte", "durata": "variabile",
            "norme": "Nessuna — misura a criterio",
            "misura": "Genera prove di calcolo, fluenza di lettura, produzione scritta.",
            "puo": "Misure ripetute sullo stesso bambino: la stessa prova ogni due settimane "
                   "mostra la curva di apprendimento meglio di qualunque percentile.",
            "non_puo": "Nessuna soglia di rischio: senza norme non esiste un «sotto la media».",
            "link": "https://www.interventioncentral.org",
            "campi": ["Prova somministrata", "Risultato", "Data confronto precedente"],
        },
    ],
    "🗣️ Linguaggio": [
        {
            "nome": "MAIN — abilità narrative",
            "bibliografia": "Gagarina N., Klop D., Kunnari S., Tantele K., Välimaa T., Bohnacker U., Walters J. *Multilingual Assessment Instrument for Narratives (MAIN)*. ZAS Papers in Linguistics, Leibniz-ZAS Berlino. Versione italiana 2020 revised.",
            "fonte": "Leibniz-ZAS · versione italiana 2020",
            "eta": "3-10 anni", "durata": "15 min",
            "norme": "Riferimenti di ricerca europei",
            "misura": "Racconto su sequenze di 6 immagini: macrostruttura e comprensione. "
                      "Quattro storie parallele.",
            "puo": "È l'unico strumento che valuta il linguaggio senza penalizzare i bambini "
                   "bilingui, e permette di valutare nella lingua madre.",
            "non_puo": "Non copre fonologia né morfosintassi: per quelle servono le batterie "
                       "commerciali (BVL, TCGB) o i marcatori LITMUS.",
            "link": "https://main.leibniz-zas.de",
            "campi": ["Macrostruttura (0-17)", "Comprensione (0-10)", "Storia usata"],
        },
        {
            "nome": "Fluenze verbali (fonemica e semantica)",
            "bibliografia": "Novelli G. et al. (1986). Tre test clinici di ricerca e produzione lessicale: taratura su soggetti normali. *Archivio di Psicologia, Neurologia e Psichiatria*, 47(4), 477-506. · Carlesimo G.A. et al. (1996). The Mental Deterioration Battery: normative data. *European Neurology*, 36(6), 378-384.",
            "fonte": "Novelli et al. 1986 · Carlesimo et al. 1996",
            "eta": "adulti", "durata": "3 min",
            "norme": "Norme italiane per età e scolarità",
            "misura": "Parole prodotte in 60 secondi per lettera e per categoria.",
            "puo": "L'unica misura di linguaggio adulto a costo zero con norme italiane vere. "
                   "Non serve alcun materiale.",
            "non_puo": "Misura accesso lessicale e funzioni esecutive, non comprensione "
                       "né produzione frasale.",
            "link": "",
            "campi": ["Fonemica F", "Fonemica A", "Fonemica S",
                      "Semantica animali", "Semantica cibi", "Perseverazioni", "Intrusioni"],
        },
    ],
    "🎯 Attenzione e comportamento": [
        {
            "nome": "COM-R — questionario insegnanti",
            "bibliografia": "Scala COM-R per insegnanti, con percentili. AIRIPA — Associazione Italiana per la Ricerca e l'Intervento nella Psicopatologia dell'Apprendimento.",
            "fonte": "AIRIPA",
            "eta": "primaria e secondaria", "durata": "10 min",
            "norme": "Percentili inclusi",
            "misura": "Osservazione strutturata di attenzione e comportamento in classe.",
            "puo": "Portare in valutazione lo sguardo di chi vede il bambino otto ore al giorno: "
                   "un dato che in studio non puoi raccogliere.",
            "non_puo": "Un questionario per insegnanti non diagnostica l'ADHD: serve il quadro "
                       "multi-informante e la valutazione clinica.",
            "link": "https://www.airipa.it/materiali/strumenti-e-software/",
            "campi": ["Punteggio disattenzione", "Punteggio iperattività", "Percentile"],
        },
        {
            "nome": "ASRS-5 — adulti (OMS)",
            "bibliografia": "Kessler R.C. et al. (2005). The World Health Organization Adult ADHD Self-Report Scale (ASRS): a short screening scale for use in the general population. *Psychological Medicine*, 35(2), 245-256. Versione italiana ASRS-5.",
            "fonte": "Organizzazione Mondiale della Sanità",
            "eta": "adulti", "durata": "5 min",
            "norme": "Cut-off validato",
            "misura": "Screening dei sintomi ADHD nell'adulto.",
            "puo": "Aprire il discorso con un adulto che sospetta un ADHD non riconosciuto "
                   "in infanzia.",
            "non_puo": "È uno screening autosomministrato: positivo significa «approfondire», "
                       "non «è ADHD».",
            "link": "",
            "campi": ["Punteggio totale", "Sopra cut-off"],
        },
        {
            "nome": "Batteria DeCoNe — Attenzione",
            "bibliografia": "Batteria DeCoNe per l'attenzione — manuale del somministratore e tarature. Laboratorio DeCoNe, Università di Padova.",
            "fonte": "DeCoNe, Università di Padova",
            "eta": "primaria", "durata": "15 min",
            "norme": "Tarature per classe",
            "misura": "Prove carta-matita di attenzione selettiva e mantenuta.",
            "puo": "Misurare l'attenzione con una prestazione, non con un questionario.",
            "non_puo": "Non distingue disattenzione primaria da quella secondaria alla fatica "
                       "di lettura: va letta insieme alle prove di apprendimento.",
            "link": "https://dpg.unipd.it/en/deconelab/materiali",
            "campi": ["Attenzione selettiva: corretti", "Errori", "Tempo (sec)"],
        },
    ],
    "🧩 Complementari": [
        {
            "nome": "QAD — Questionario Adattamento Dislessia",
            "bibliografia": "Viola. *QAD — Questionario di Adattamento alla Dislessia*. AIRIPA.",
            "fonte": "AIRIPA",
            "eta": "primaria e secondaria", "durata": "10 min",
            "norme": "Riferimenti AIRIPA",
            "misura": "Vissuto e adattamento psicologico del ragazzo con dislessia.",
            "puo": "Intercettare il costo emotivo del disturbo, che spesso pesa più del "
                   "disturbo stesso e non compare in nessuna prova di lettura.",
            "non_puo": "Non misura la dislessia: presuppone che la diagnosi ci sia già.",
            "link": "https://www.airipa.it/materiali/strumenti-e-software/",
            "campi": ["Punteggio adattamento", "Aree critiche"],
        },
        {
            "nome": "Span associativo / memoria fonologica",
            "bibliografia": "Antonello. *Span associativo e memoria fonologica (MLFA)*. AIRIPA.",
            "fonte": "AIRIPA",
            "eta": "primaria", "durata": "8 min",
            "norme": "Riferimenti AIRIPA",
            "misura": "Memoria di lavoro fonologica.",
            "puo": "Spiegare perché un bambino perde il filo mentre legge: se la memoria "
                   "fonologica è satura, la comprensione crolla anche con decodifica corretta.",
            "non_puo": "Non è una misura di intelligenza né di memoria generale.",
            "link": "https://www.airipa.it/materiali/strumenti-e-software/",
            "campi": ["Span diretto", "Span inverso"],
        },
    ],
}



# ── Materiali caricati una volta e poi sempre a portata ──────────────
# I PDF delle prove restano quelli originali: le tarature valgono per
# quegli stimoli, non per versioni rigenerate. Quello che si può evitare
# è di ripescarli dal disco a ogni somministrazione — si caricano una
# volta nel gestionale e da lì si aprono a schermo, anche sul secondo
# monitor rivolto al bambino.

def _assicura_tabella_materiali(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apprendimenti_open_materiali (
                id         BIGSERIAL PRIMARY KEY,
                studio_id  BIGINT NOT NULL DEFAULT 1,
                strumento  TEXT NOT NULL,
                nome_file  TEXT NOT NULL,
                mime       TEXT,
                dati       BYTEA NOT NULL,
                caricato_il TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (studio_id, strumento, nome_file)
            );
        """)
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False


def _salva_materiale(conn, studio_id, strumento, nome_file, mime, dati):
    if not _assicura_tabella_materiali(conn):
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO apprendimenti_open_materiali
                (studio_id, strumento, nome_file, mime, dati)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (studio_id, strumento, nome_file) DO UPDATE
               SET dati = EXCLUDED.dati, mime = EXCLUDED.mime,
                   caricato_il = now();
        """, (studio_id, strumento, nome_file, mime, psycopg2.Binary(dati)
              if psycopg2 else dati))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore caricamento: {e}")
        return False


def _materiali_di(conn, studio_id, strumento):
    if not _assicura_tabella_materiali(conn):
        return []
    try:
        cur = conn.cursor()
        cur.execute("""SELECT nome_file, mime, dati FROM apprendimenti_open_materiali
                        WHERE studio_id=%s AND strumento=%s ORDER BY nome_file;""",
                    (studio_id, strumento))
        righe = cur.fetchall() or []
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []
    fuori = []
    for r in righe:
        if hasattr(r, "get"):
            fuori.append(dict(r))
        else:
            fuori.append({"nome_file": r[0], "mime": r[1], "dati": r[2]})
    return fuori


def _elimina_materiale(conn, studio_id, strumento, nome_file):
    try:
        cur = conn.cursor()
        cur.execute("""DELETE FROM apprendimenti_open_materiali
                        WHERE studio_id=%s AND strumento=%s AND nome_file=%s;""",
                    (studio_id, strumento, nome_file))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False


def _mostra_materiale(dati, nome_file, mime, chiave):
    """PDF a schermo pieno nella pagina, più il bottone per il secondo monitor."""
    b64 = base64.b64encode(bytes(dati)).decode()
    if (mime or "").endswith("pdf") or nome_file.lower().endswith(".pdf"):
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" '
            f'width="100%" height="780" style="border:1px solid #d8e5de;'
            f'border-radius:8px"></iframe>',
            unsafe_allow_html=True)
    else:
        st.image(bytes(dati), use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button("⬇️ Scarica", data=bytes(dati), file_name=nome_file,
                            mime=mime or "application/octet-stream",
                            key=f"dl_{chiave}", use_container_width=True)
    with c2:
        # Stessa finestra usata dagli altri test: si sposta una volta sul
        # secondo schermo e resta lì.
        if st.button("🖥️ Apri sul secondo monitor", key=f"sm_{chiave}",
                     use_container_width=True):
            components.html(f"""<script>
              var w = window.open('', 'finestra_screening_bambino');
              if (w) {{
                w.document.open();
                w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8">'
                  + '<title>{nome_file}</title><style>html,body{{margin:0;height:100%}}'
                  + 'iframe{{border:0;width:100%;height:100%}}</style></head><body>'
                  + '<iframe src="data:{mime or "application/pdf"};base64,{b64}"></iframe>'
                  + '</body></html>');
                w.document.close(); w.focus();
              }} else {{
                alert('Il browser ha bloccato la finestra: consenti i popup.');
              }}
            </script>""", height=0)


def _assicura_tabella(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apprendimenti_open (
                id            BIGSERIAL PRIMARY KEY,
                paziente_id   BIGINT NOT NULL,
                data_prova    DATE NOT NULL DEFAULT CURRENT_DATE,
                area          TEXT,
                strumento     TEXT NOT NULL,
                punteggi      JSONB,
                osservazioni  TEXT,
                operatore     TEXT,
                creato_il     TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False


def _salva(conn, paz_id, area, strumento, punteggi, note, operatore):
    if not _assicura_tabella(conn):
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO apprendimenti_open
                (paziente_id, area, strumento, punteggi, osservazioni, operatore)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (paz_id, area, strumento, json.dumps(punteggi), note, operatore))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def _storico(conn, paz_id, strumento=None):
    if not _assicura_tabella(conn):
        return []
    try:
        cur = conn.cursor()
        if strumento:
            cur.execute("""SELECT data_prova, strumento, punteggi, osservazioni
                             FROM apprendimenti_open
                            WHERE paziente_id=%s AND strumento=%s
                         ORDER BY data_prova DESC, id DESC;""", (paz_id, strumento))
        else:
            cur.execute("""SELECT data_prova, strumento, punteggi, osservazioni
                             FROM apprendimenti_open WHERE paziente_id=%s
                         ORDER BY data_prova DESC, id DESC LIMIT 30;""", (paz_id,))
        righe = cur.fetchall() or []
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []
    fuori = []
    for r in righe:
        if hasattr(r, "get"):
            fuori.append(dict(r))
        else:
            fuori.append({"data_prova": r[0], "strumento": r[1],
                          "punteggi": r[2], "osservazioni": r[3]})
    return fuori


def _bibliografia(strumenti_usati) -> str:
    """Riferimenti dei soli strumenti somministrati.

    Una bibliografia generica non serve a nessuno: qui compaiono le fonti
    delle prove che quel paziente ha effettivamente svolto, così chi legge
    la relazione può risalire a norme e materiali.
    """
    voci = []
    for elenco in STRUMENTI.values():
        for s in elenco:
            if s["nome"] in strumenti_usati and s.get("bibliografia"):
                voci.append((s["nome"], s["bibliografia"]))
    if not voci:
        return ""
    righe = ["", "─" * 64, "", "RIFERIMENTI BIBLIOGRAFICI E FONTI DEGLI STRUMENTI", ""]
    for nome, bib in sorted(voci):
        righe.append(f"· {nome}")
        righe.append(f"  {bib}")
        righe.append("")
    righe.append("Criteri di riferimento per la valutazione della lettura:")
    righe.append("Cornoldi C., Perini N., Tressoldi P.E. Criteri per la diagnosi e la "
                 "valutazione dei disturbi di lettura. AIRIPA.")
    righe.append("")
    righe.append("Tutti gli strumenti impiegati sono ad accesso libero e resi disponibili "
                 "dagli enti indicati per uso clinico e di ricerca.")
    return "\n".join(righe)


def render_apprendimenti_open(conn=None, paz_id=None, paziente=None) -> None:
    st.header("📚 Apprendimenti — strumenti open")
    st.caption("Prove di lettura, scrittura, calcolo, linguaggio e attenzione ad accesso "
               "libero, con taratura italiana dove esiste.")

    st.warning(
        "**Fin dove arrivano questi strumenti.** Individuano chi è a rischio e misurano "
        "i progressi nel tempo: per questo valgono. Non sostengono una certificazione DSA, "
        "e non per una questione di qualità delle prove — manca il tassello cognitivo. "
        "Nessun test di livello intellettivo è libero e tarato in italiano, e il "
        "funzionamento cognitivo nella norma è criterio diagnostico. WISC, WAIS, Leiter e "
        "Raven restano necessari, e commerciali.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    t_cat, t_mat, t_somm, t_stor, t_rel = st.tabs(
        ["📋 Catalogo", "📂 Materiali", "✏️ Somministra e registra",
         "📈 Storico paziente", "📄 Relazione"])

    # ── Catalogo ─────────────────────────────────────────────────────
    with t_cat:
        st.caption("Per ogni strumento: cosa misura, cosa può sostenere e cosa no. "
                   "La seconda parte conta quanto la prima.")
        for area, elenco in STRUMENTI.items():
            with st.expander(f"{area} — {len(elenco)} strument{'o' if len(elenco)==1 else 'i'}"):
                for s in elenco:
                    st.markdown(f"**{s['nome']}**")
                    st.caption(f"{s['fonte']} · {s['eta']} · {s['durata']} · {s['norme']}")
                    st.markdown(s["misura"])
                    st.markdown(f"✅ **Può:** {s['puo']}")
                    st.markdown(f"⛔ **Non può:** {s['non_puo']}")
                    if s.get("link"):
                        st.markdown(f"[Scarica il materiale]({s['link']})")
                    st.divider()

    # ── Materiali ────────────────────────────────────────────────────
    with t_mat:
        st.caption("Carica una volta i PDF scaricati dai siti di Padova, Santa Lucia e "
                   "AIRIPA: restano qui e si aprono a schermo, anche sul monitor "
                   "rivolto al bambino. Niente più ricerca nel Finder a paziente seduto.")
        st.info("Le tavole vanno usate **nella versione originale**: le tarature valgono "
                "per quegli stimoli esatti. Per questo il gestionale conserva i tuoi PDF "
                "invece di generare prove equivalenti.")

        _studio = st.session_state.get("studio_id", 1)
        _tutti = [s["nome"] for elenco in STRUMENTI.values() for s in elenco]
        _str_sel = st.selectbox("Strumento", _tutti, key="ao_mat_strumento")

        _f = st.file_uploader("Aggiungi un PDF o un'immagine",
                               type=["pdf", "png", "jpg", "jpeg"], key="ao_mat_up")
        if _f is not None and st.button("💾 Carica", key="ao_mat_save", type="primary"):
            if _salva_materiale(conn, _studio, _str_sel, _f.name,
                                 _f.type, _f.getvalue()):
                st.success(f"«{_f.name}» caricato per {_str_sel}.")
                st.rerun()

        _mat = _materiali_di(conn, _studio, _str_sel)
        if not _mat:
            _link = next((s.get("link") for e in STRUMENTI.values() for s in e
                          if s["nome"] == _str_sel), "")
            st.caption("Nessun materiale caricato per questo strumento." +
                       (f" [Scaricalo qui]({_link}) e poi caricalo sopra." if _link else ""))
        else:
            for _i, _m in enumerate(_mat):
                with st.expander(_m["nome_file"], expanded=(len(_mat) == 1)):
                    _mostra_materiale(_m["dati"], _m["nome_file"], _m["mime"],
                                      f"{_str_sel}_{_i}")
                    if st.button("🗑 Rimuovi", key=f"ao_mat_del_{_i}"):
                        _elimina_materiale(conn, _studio, _str_sel, _m["nome_file"])
                        st.rerun()

    # ── Somministrazione ─────────────────────────────────────────────
    with t_somm:
        if not paz_id:
            st.info("Seleziona un paziente qui sopra per registrare una prova.")
        else:
            area_sel = st.selectbox("Area", list(STRUMENTI.keys()), key="ao_area")
            elenco = STRUMENTI[area_sel]
            nomi = [s["nome"] for s in elenco]
            nome_sel = st.selectbox("Strumento", nomi, key="ao_strumento")
            s = next(x for x in elenco if x["nome"] == nome_sel)

            st.caption(f"{s['eta']} · {s['durata']} · {s['norme']}")
            with st.expander("Cosa può e non può sostenere"):
                st.markdown(f"✅ {s['puo']}")
                st.markdown(f"⛔ {s['non_puo']}")

            # Il materiale della prova, apribile senza cambiare scheda:
            # durante la somministrazione non si esce dalla pagina.
            _mat_s = _materiali_di(conn, st.session_state.get("studio_id", 1), nome_sel)
            if _mat_s:
                with st.expander(f"📂 Materiale della prova ({len(_mat_s)})"):
                    for _i, _m in enumerate(_mat_s):
                        st.markdown(f"**{_m['nome_file']}**")
                        _mostra_materiale(_m["dati"], _m["nome_file"], _m["mime"],
                                          f"somm_{nome_sel}_{_i}")
            else:
                st.caption("📂 Nessun materiale caricato: lo carichi una volta dalla "
                           "scheda **Materiali** e da lì in poi lo apri da qui.")

            # Le ultime due somministrazioni accanto ai campi: il senso di
            # queste prove è il confronto nel tempo, non il singolo numero.
            precedenti = _storico(conn, paz_id, nome_sel)[:2]
            if precedenti:
                st.markdown("**Somministrazioni precedenti**")
                _tab = []
                for p in precedenti:
                    _p = p.get("punteggi") or {}
                    if isinstance(_p, str):
                        try: _p = json.loads(_p)
                        except Exception: _p = {}
                    _tab.append({"Data": p["data_prova"], **_p})
                st.dataframe(pd.DataFrame(_tab), hide_index=True, use_container_width=True)

            st.markdown("**Punteggi**")
            valori = {}
            colonne = st.columns(min(3, len(s["campi"])))
            for i, campo in enumerate(s["campi"]):
                with colonne[i % len(colonne)]:
                    valori[campo] = st.text_input(campo, key=f"ao_c_{nome_sel}_{campo}")

            note = st.text_area("Osservazioni qualitative", key="ao_note", height=68,
                                 placeholder="Come ha affrontato la prova, strategie, "
                                             "affaticamento, collaborazione…")
            operatore = st.text_input("Operatore", key="ao_op")

            if st.button("💾 Registra la prova", type="primary", key="ao_salva"):
                compilati = {k: v.strip() for k, v in valori.items() if v.strip()}
                if not compilati:
                    st.warning("Inserisci almeno un punteggio.")
                elif _salva(conn, paz_id, area_sel, nome_sel, compilati, note, operatore):
                    st.success(f"«{nome_sel}» registrata.")
                    st.rerun()

    # ── Storico ──────────────────────────────────────────────────────
    with t_stor:
        if not paz_id:
            st.info("Seleziona un paziente qui sopra.")
        else:
            righe = _storico(conn, paz_id)
            if not righe:
                st.caption("Nessuna prova registrata per questo paziente.")
            else:
                for r in righe:
                    p = r.get("punteggi") or {}
                    if isinstance(p, str):
                        try: p = json.loads(p)
                        except Exception: p = {}
                    with st.expander(f"{r['data_prova']} — {r['strumento']}"):
                        if p:
                            st.dataframe(pd.DataFrame([p]), hide_index=True,
                                         use_container_width=True)
                        if r.get("osservazioni"):
                            st.caption(r["osservazioni"])

    # ── Relazione ────────────────────────────────────────────────────
    with t_rel:
        if not paz_id:
            st.info("Seleziona un paziente qui sopra.")
        else:
            st.caption("Legge tutte le prove registrate per questo paziente e ne scrive "
                       "una lettura d'insieme, con la carta intestata dello studio.")
            st.warning(
                "**Cosa può essere questa relazione.** Un profilo di screening: dove il "
                "bambino è fragile, dove regge, come si è mosso nel tempo, e quali "
                "approfondimenti valutare. **Non è una certificazione DSA** e non va "
                "presentata come tale — manca il livello cognitivo, che è criterio "
                "diagnostico e non esiste in versione libera con norme italiane. "
                "Il testo lo dice da sé, così non ci sono equivoci con la famiglia "
                "o con la scuola.")

            prove = _storico(conn, paz_id)
            if not prove:
                st.info("Nessuna prova registrata: la relazione si costruisce su quelle.")
            else:
                st.caption(f"{len(prove)} prove registrate · "
                           f"dalla più recente ({prove[0]['data_prova']}) "
                           f"alla più vecchia ({prove[-1]['data_prova']})")

                _dom = st.text_area(
                    "Domanda che ha portato alla valutazione",
                    key="ao_rel_domanda", height=68,
                    placeholder="Es. la maestra segnala lettura lenta e fatica a copiare "
                                "dalla lavagna; i genitori riferiscono rifiuto dei compiti.")
                _oss = st.text_area("Osservazioni cliniche da includere",
                                     key="ao_rel_oss", height=68,
                                     placeholder="Collaborazione, affaticabilità, strategie, "
                                                 "differenze fra prove…")

                if st.button("✍️ Scrivi la relazione", type="primary", key="ao_rel_gen"):
                    _righe_dati = []
                    for p in prove:
                        _pt = p.get("punteggi") or {}
                        if isinstance(_pt, str):
                            try: _pt = json.loads(_pt)
                            except Exception: _pt = {}
                        _righe_dati.append(
                            f"- {p['data_prova']} · {p['strumento']}: "
                            + ", ".join(f"{k} = {v}" for k, v in _pt.items())
                            + (f" · note: {p['osservazioni']}" if p.get("osservazioni") else ""))

                    _nome = ""
                    if isinstance(paziente, dict):
                        _nome = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()
                    _nome = _nome or f"paziente #{paz_id}"

                    _testo = None
                    try:
                        from .ai_estrazione import genera_testo, ai_disponibile
                        if ai_disponibile():
                            _prompt = (
                                f"Scrivi la lettura d'insieme di uno screening degli apprendimenti "
                                f"su {_nome}.\n\n"
                                f"MOTIVO DELLA VALUTAZIONE: {_dom or 'non specificato'}\n\n"
                                f"PROVE SOMMINISTRATE (dalla più recente):\n"
                                + "\n".join(_righe_dati) + "\n\n"
                                f"OSSERVAZIONI DELL'OPERATORE: {_oss or '—'}\n\n"
                                "Struttura il testo così: (1) perché è stato fatto lo screening; "
                                "(2) che cosa è stato somministrato; (3) i risultati area per area, "
                                "spiegando cosa significano in termini concreti — non elencando numeri; "
                                "(4) se ci sono più somministrazioni della stessa prova, come si è "
                                "mosso nel tempo, che è il dato più informativo; (5) conclusioni e "
                                "passi successivi.\n\n"
                                "VINCOLI NON NEGOZIABILI:\n"
                                "- Sono strumenti ad accesso libero: valgono come screening e "
                                "monitoraggio, NON come certificazione DSA. Dillo esplicitamente "
                                "nelle conclusioni, spiegando che manca la valutazione del livello "
                                "cognitivo, criterio diagnostico per cui servono strumenti "
                                "commerciali (WISC-V o equivalenti).\n"
                                "- Non usare mai le parole «diagnosi di dislessia/disortografia/"
                                "discalculia»: scrivi «profilo compatibile con», «indicatori di "
                                "rischio per», «merita approfondimento».\n"
                                "- Il Numeracy Screener ha norme canadesi: se compare, precisa che "
                                "il confronto è orientativo.\n"
                                "- Italiano piano, per genitori e insegnanti. Mai allarmistico, mai "
                                "rassicurante a vuoto. Massimo 600 parole."
                            )
                            _sistema = (
                                "Sei un assistente clinico dello Studio The Organism. Scrivi "
                                "relazioni di screening oneste sui propri limiti: dici cosa i dati "
                                "mostrano e cosa non possono mostrare, senza mai far passare uno "
                                "screening per una diagnosi.")
                            with st.spinner("Scrivo la relazione…"):
                                _b = genera_testo(_prompt, _sistema)
                            if not _b.startswith("⚠️"):
                                _testo = _b
                    except Exception:
                        pass

                    if _testo is None:
                        st.info("AI non disponibile: preparo una relazione essenziale "
                                "coi dati raccolti, da completare a mano.")
                        _testo = ("PROVE SOMMINISTRATE\n\n" + "\n".join(_righe_dati)
                                  + ("\n\nMOTIVO: " + _dom if _dom else "")
                                  + ("\n\nOSSERVAZIONI: " + _oss if _oss else "")
                                  + "\n\nCONCLUSIONI\n[da completare]\n\n"
                                  "Gli strumenti impiegati sono ad accesso libero: il presente "
                                  "profilo ha valore di screening e di monitoraggio, non di "
                                  "certificazione diagnostica. Per un inquadramento diagnostico "
                                  "è necessaria la valutazione del livello cognitivo con "
                                  "strumenti standardizzati.")

                    _usati = {p["strumento"] for p in prove}
                    _testo = _testo.rstrip() + "\n" + _bibliografia(_usati)

                    try:
                        from .intestazione_relazioni import incornicia
                        _dn = paziente.get("data_nascita") if isinstance(paziente, dict) else None
                        _testo = incornicia(
                            _testo, "Screening degli apprendimenti",
                            nome_paziente=_nome,
                            data_nascita=(_dn.strftime("%d/%m/%Y")
                                          if hasattr(_dn, "strftime") else str(_dn or "")),
                            metodo_in_apertura=True)
                    except Exception:
                        pass

                    st.session_state["ao_rel_testo"] = _testo

                if st.session_state.get("ao_rel_testo"):
                    _finale = st.text_area("Relazione (correggila prima di consegnarla)",
                                            value=st.session_state["ao_rel_testo"],
                                            height=460, key="ao_rel_out")
                    st.download_button(
                        "⬇️ Scarica in formato testo", data=_finale.encode("utf-8"),
                        file_name=f"screening_apprendimenti_{paz_id}.txt",
                        mime="text/plain", key="ao_rel_dl")
