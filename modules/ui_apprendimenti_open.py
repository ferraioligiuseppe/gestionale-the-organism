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

import json
import streamlit as st
import pandas as pd

# ── Catalogo ─────────────────────────────────────────────────────────
# "puo": cosa lo strumento sostiene legittimamente
# "non_puo": l'uso scorretto da cui mettere in guardia
STRUMENTI = {
    "🔤 Prerequisiti (ultimo anno infanzia · 1ª primaria)": [
        {
            "nome": "RAN — Denominazione rapida automatizzata",
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

    t_cat, t_somm, t_stor = st.tabs(
        ["📋 Catalogo", "✏️ Somministra e registra", "📈 Storico paziente"])

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
