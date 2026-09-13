# -*- coding: utf-8 -*-
"""Protocollo di valutazione — replica fedele del documento PDF Studio The
Organism (Anamnesi · Bilancio fonetico · Linguaggio · Fluenza ·
Apprendimento · Miofunzionale · Osteopatica · Visuo-posturale).

Ogni tabella qui dentro riproduce esattamente stimoli, colonne e struttura
del PDF — stesso ordine, stessa sequenza di somministrazione. Costruito in
PARTI, come il documento originale (PARTE 1, 2, 3, ...).
"""
from __future__ import annotations
import json
import streamlit as st
import pandas as pd


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS protocollo_valutazione (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_valutazione DATE,
                esaminatore TEXT,
                dati JSONB,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva(conn, paz_id, esaminatore, dati) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO protocollo_valutazione (paziente_id, data_valutazione, esaminatore, dati)
            VALUES (%s, CURRENT_DATE, %s, %s)
        """, (paz_id, esaminatore, json.dumps(dati, default=str)))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def _tabella(nome, righe, colonne_fisse, key, altezza=None):
    """Data editor con le colonne indicate come fisse (disabled=True, il
    testo dello stimolo) e le restanti libere per la compilazione."""
    df = pd.DataFrame(righe)
    cfg = {c: st.column_config.TextColumn(disabled=True) for c in colonne_fisse}
    return st.data_editor(df, key=key, hide_index=True, use_container_width=True,
                           column_config=cfg, height=altezza)


def render_protocollo_valutazione(conn=None, paz_id=None, paziente=None) -> None:
    st.header("📋 Protocollo di valutazione — Studio The Organism")
    st.caption("Replica del documento su carta, parte per parte, nello stesso ordine di somministrazione.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    st.markdown("### Dati generali")
    c1, c2 = st.columns(2)
    esaminatore = c1.text_input("Esaminatore", key="pv_esaminatore")
    inviato_da = c2.text_input("Inviato da", key="pv_inviato_da")
    motivo = st.text_area("Motivo della richiesta", key="pv_motivo", height=68)
    fascia = st.radio("Fascia applicata", ["A 3;0–5;11 prescolare", "B 6;0–10;11 primaria", "C 11 anni e oltre"],
                       key="pv_fascia", horizontal=True)

    st.markdown("### Anamnesi gravidica, parto e neonatale")
    gravidanza = st.text_area("Gravidanza (decorso, terapie, eventi)", key="pv_gravidanza", height=60)
    c3, c4 = st.columns(2)
    parto_tipo = c3.selectbox("Parto", ["", "Eutocico", "Distocico", "Cesareo programmato", "Cesareo d'urgenza"],
                               key="pv_parto_tipo")
    giro_cordone = c4.checkbox("Giro di cordone", key="pv_giro_cordone")
    c5, c6, c7 = st.columns(3)
    peso_nascita = c5.text_input("Peso alla nascita (g)", key="pv_peso")
    apgar = c6.text_input("Apgar (___/___)", key="pv_apgar")
    tin_ittero = c7.multiselect("Segnalazioni", ["TIN", "Ittero", "Altro"], key="pv_tin")
    periodo_neonatale = st.text_area("Periodo neonatale (allattamento, suzione, coliche, sonno, pianto)",
                                      key="pv_neonatale", height=60)
    c8, c9 = st.columns(2)
    tappe_motorie = c8.text_input("Tappe motorie (controllo capo, seduta, gattonamento, cammino)", key="pv_tappe")
    prime_parole = c9.text_input("Prime parole — prime frasi", key="pv_prime_parole")
    otiti = st.text_input("Otiti, tubi timpanici, screening uditivo", key="pv_otiti")
    familiarita = st.text_input("Familiarità per DSA, disturbi di linguaggio, balbuzie", key="pv_familiarita")
    bilinguismo = st.text_input("Bilinguismo / lingua prevalente in casa", key="pv_bilinguismo")
    patologie_note = st.text_area("Patologie note, interventi, terapie in corso", key="pv_patologie", height=60)
    trattamenti_pregressi = st.text_area("Trattamenti pregressi ed esiti", key="pv_trattamenti", height=60)
    valutazione_visiva_pregressa = st.text_input("Valutazione visiva/optometrica pregressa", key="pv_visiva_preg")
    hobby = st.text_input("Hobby, sport, attività extrascolastiche", key="pv_hobby")

    st.markdown("---")
    st.markdown("## PARTE 1 — BILANCIO FONETICO")

    st.markdown("**1.2 Lista stimoli per fono e posizione**")
    st.caption("Codifica: ✓ corretto · S sostituzione · O omissione · D distorsione · I instabile · NR non valutabile.")
    _ESITI = ["✓ corretto", "S sostituzione", "O omissione", "D distorsione", "I instabile", "NR"]
    _FONI_CLASSI = [
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
    bilancio_fonetico = {}
    for classe, foni in _FONI_CLASSI:
        st.markdown(f"_{classe}_")
        df = pd.DataFrame([
            {"Fono": f, "Iniziale": p_in, "Esito ": "✓ corretto", "Intervocalica": p_iv,
             "Esito  ": "✓ corretto", "Fono prodotto / note": ""}
            for f, p_in, p_iv in foni
        ])
        out = st.data_editor(df, key=f"pv_bf_{classe}", hide_index=True, use_container_width=True,
                              column_config={
                                  "Fono": st.column_config.TextColumn(disabled=True),
                                  "Iniziale": st.column_config.TextColumn(disabled=True),
                                  "Esito ": st.column_config.SelectboxColumn(options=_ESITI, required=True),
                                  "Intervocalica": st.column_config.TextColumn(disabled=True),
                                  "Esito  ": st.column_config.SelectboxColumn(options=_ESITI, required=True),
                              })
        bilancio_fonetico[classe] = out.to_dict("records")

    st.markdown("**1.3 Prove di struttura**")
    st.markdown("_1.3.1 Gruppi consonantici_")
    gruppi = _tabella("gruppi", [
        {"Tipo": "Muta + liquida", "Stimoli": "blu · treno · drago · prato · grande · fragola · clarinetto · fiocco", "Riduzioni osservate": ""},
        {"Tipo": "s + consonante", "Stimoli": "scala · spugna · stella · sveglia · smalto · scivolo", "Riduzioni osservate": ""},
        {"Tipo": "Nessi complessi", "Stimoli": "strada · scrivere · sprecare · splendere · struzzo", "Riduzioni osservate": ""},
        {"Tipo": "Nasale + cons.", "Stimoli": "campana · bambino · pianta · fungo · tenda", "Riduzioni osservate": ""},
    ], ["Tipo", "Stimoli"], "pv_gruppi")

    st.markdown("_1.3.2 Dittonghi e iati_")
    st.caption("uovo · piede · fiore · guanto · aiuola · aquilone · buio")
    dittonghi_note = st.text_input("Osservazioni", key="pv_dittonghi")

    st.markdown("_1.3.3 Polisillabi (tenuta della struttura)_")
    polisillabi = _tabella("polisillabi", [
        {"Sillabe": "3", "Stimoli": "farfalla · ospedale · bicchiere", "Produzione del soggetto": ""},
        {"Sillabe": "4", "Stimoli": "cioccolato · apparecchio · termometro", "Produzione del soggetto": ""},
        {"Sillabe": "5", "Stimoli": "elicottero · rinoceronte · frigorifero · acquerello", "Produzione del soggetto": ""},
        {"Sillabe": "5+", "Stimoli": "televisione · automobilista · particolarmente", "Produzione del soggetto": ""},
    ], ["Sillabe", "Stimoli"], "pv_polisillabi")

    st.markdown("_1.3.4 Logatomi complessi_ (C · B dalla 3ª)")
    st.caption("strafulgo · pesciantro · gnaviglio · trasbricchi · sclorendo · zampigliastro · ricchiaffronto")
    st.caption("Somministrare 2 volte: velocità libera, poi «il più veloce possibile». Annotare se l'accuratezza "
               "crolla sotto carico di velocità (da incrociare con Parte 3 — cluttering).")
    logatomi_note = st.text_area("Osservazioni logatomi", key="pv_logatomi", height=60)

    st.markdown("**1.4 Inventario fonetico — griglia di sintesi**")
    st.caption("P presente e stabile · I instabile · A assente. Compilare le tre colonne di contesto.")
    inventario = _tabella("inventario", [
        {"Fono": "p / b", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "t / d", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "k / g", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "f / v", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "s", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "sc [ʃ]", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "z [ts]/[dz]", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "ci / gi", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "m", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "n", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "gn [ɲ]", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "l", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "gl [ʎ]", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
        {"Fono": "r (vibrante)", "Iniziale": "", "Intervocalica": "", "Gruppo": ""},
    ], ["Fono"], "pv_inventario")

    st.markdown("**1.5 Processi di semplificazione**")
    st.caption("Frequenza: 0 assente · 1 sporadico (<25%) · 2 frequente (25–75%) · 3 sistematico (>75%). "
               "Il «limite indicativo» è l'età oltre la quale il processo non è più fisiologico — riferimento "
               "orientativo, non una soglia diagnostica.")
    st.markdown("_Semplificazioni di sistema_")
    semp_sistema = _tabella("semp_sistema", [
        {"Processo": "Stopping", "Descrizione": "Fricativo/affricato → occlusivo", "Esempio": "sole → «tole»", "Limite indic.": "3;6–4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Fricazione", "Descrizione": "Occlusivo/affricato → fricativo", "Esempio": "cena → «sena»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Affricazione", "Descrizione": "Fricativo → affricato", "Esempio": "sole → «zole»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Anteriorizzazione", "Descrizione": "Punto spostato avanti (velare→dentale)", "Esempio": "casa → «tasa»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Posteriorizzazione", "Descrizione": "Punto spostato indietro (dentale→velare)", "Esempio": "tavolo → «cavolo»", "Limite indic.": "3;6", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Desonorizzazione", "Descrizione": "Sonoro→sordo (o viceversa)", "Esempio": "barca → «parca»", "Limite indic.": "3;6", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Gliding", "Descrizione": "Liquido → semivocale/approssimante", "Esempio": "rana → «jana»", "Limite indic.": "5;0", "Freq.": "", "Esempi rilevati": ""},
    ], ["Processo", "Descrizione", "Esempio", "Limite indic."], "pv_semp_sistema")
    st.markdown("_Semplificazioni di struttura_")
    semp_struttura = _tabella("semp_struttura", [
        {"Processo": "Elim. sillaba debole", "Descrizione": "Caduta della sillaba atona", "Esempio": "elefante → «fante»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Armonia consonantica", "Descrizione": "Una consonante assimila l'altra", "Esempio": "tavolo → «lavolo»", "Limite indic.": "3;6", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Armonia vocalica", "Descrizione": "Assimilazione tra vocali", "Esempio": "bambino → «bimbino»", "Limite indic.": "3;6", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Riduzione gruppi", "Descrizione": "Nesso ridotto a un elemento", "Esempio": "treno → «teno»", "Limite indic.": "4;6–5;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Riduzione dittonghi", "Descrizione": "Dittongo → vocale singola", "Esempio": "uovo → «ovo»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Metatesi", "Descrizione": "Inversione di suoni/sillabe", "Esempio": "ospedale → «opsedale»", "Limite indic.": "4;6", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Epentesi", "Descrizione": "Inserimento di un suono", "Esempio": "blu → «belu»", "Limite indic.": "4;0", "Freq.": "", "Esempi rilevati": ""},
        {"Processo": "Cancellazione", "Descrizione": "Caduta di consonante e/o vocale", "Esempio": "pane → «ane»", "Limite indic.": "3;6", "Freq.": "", "Esempi rilevati": ""},
    ], ["Processo", "Descrizione", "Esempio", "Limite indic."], "pv_semp_struttura")

    st.markdown("**1.6 Indici quantitativi**")
    indici_fonetici = _tabella("indici_fonetici", [
        {"Indice": "PCC — % consonanti corrette", "Calcolo": "(cons. corrette ÷ cons. bersaglio) × 100", "Risultato": "", "Riferimento": ">85 lieve · 65–85 lieve-moderato · 50–65 moderato-grave · <50 grave"},
        {"Indice": "Inventario fonetico", "Calcolo": "n. foni presenti ÷ 23", "Risultato": "", "Riferimento": "Completo entro 5;0–5;6"},
        {"Indice": "Processi attivi oltre il limite", "Calcolo": "conteggio righe con freq. ≥2", "Risultato": "", "Riferimento": "0 = atteso"},
        {"Indice": "Intelligibilità", "Calcolo": "scala 1–5 e % parole comprese", "Risultato": "", "Riferimento": "1 = sempre intelligibile · 5 = mai"},
        {"Indice": "Discrepanza ripetizione vs spontaneo", "Calcolo": "qualitativa", "Risultato": "", "Riferimento": "Se lo spontaneo è nettamente peggiore → carico esecutivo/prosodico"},
    ], ["Indice", "Calcolo", "Riferimento"], "pv_indici_fonetici")

    st.markdown("---")
    st.markdown("## PARTE 2 — LINGUAGGIO")

    st.markdown("**2.1.1 Denominazione su figura / su definizione**")
    st.caption("Fascia A e B: denominazione su immagine. Fascia C: denominazione su definizione orale. "
               "Annotare latenza >3\" e tipo di errore.")
    st.caption("**A**: cane · scarpa · forchetta · albero · chiave · finestra · farfalla · ombrello · bicicletta · "
               "pettine · tamburo · scala · candela · guanto · bottone · annaffiatoio")
    st.caption("**B**: gomito · imbuto · bussola · ancora · clessidra · binocolo · piramide · termometro · faro · "
               "cactus · igloo · ruspa · elica · staccionata · incudine · cavalletto")
    st.caption("**C**: tenaglia · cornice · ringhiera · guglia · setaccio · pergolato · carrucola · arcobaleno · "
               "molo · trivella · stalattite · abaco · timone · vetrata · mappamondo · tornio")
    errori_denominazione = _tabella("errori_denom", [
        {"Tipo di errore": "Circonlocuzione («quello che serve per…»)", "N.": "", "Esempi": ""},
        {"Tipo di errore": "Parafasia semantica (coordinato/sovraordinato)", "N.": "", "Esempi": ""},
        {"Tipo di errore": "Parafasia fonologica", "N.": "", "Esempi": ""},
        {"Tipo di errore": "Termine passe-partout («coso», «quello lì»)", "N.": "", "Esempi": ""},
        {"Tipo di errore": "Anomia con TOT (facilitazione fonemica)", "N.": "", "Esempi": ""},
        {"Tipo di errore": "Non risposta", "N.": "", "Esempi": ""},
    ], ["Tipo di errore"], "pv_errori_denom")
    c10, c11, c12 = st.columns(3)
    corretti_spontanei = c10.text_input("Totale corretti spontanei (___/16)", key="pv_corretti_spont")
    corretti_facilitazione = c11.text_input("Corretti su facilitazione fonemica", key="pv_corretti_facil")
    latenza_media = c12.text_input("Latenza media (\")", key="pv_latenza_media")

    st.markdown("**2.1.2 Comprensione lessicale**")
    st.caption("Scelta tra 4 figure/definizioni. Distrattori: 1 semantico, 1 fonologico, 1 non correlato. "
               "Stessi item del 2.1.1 in ordine diverso, a distanza di almeno 10 minuti.")
    c13, c14 = st.columns(2)
    corretti_compr_lex = c13.text_input("Corretti (___/16)", key="pv_corretti_compr")
    errori_prevalenti = c14.selectbox("Errori prevalentemente", ["", "Semantici", "Fonologici", "Casuali"],
                                       key="pv_errori_prev")

    st.markdown("**2.1.3 Fluenza verbale** (60\" per categoria, cronometro)")
    fluenza_verbale = _tabella("fluenza_verbale", [
        {"Prova": "Semantica — animali", "Totale": "", "Ripetizioni": "", "Intrusioni": "", "Note": ""},
        {"Prova": "Semantica — cibi", "Totale": "", "Ripetizioni": "", "Intrusioni": "", "Note": ""},
        {"Prova": "Fonemica — F (B dagli 8 anni)", "Totale": "", "Ripetizioni": "", "Intrusioni": "", "Note": ""},
        {"Prova": "Fonemica — A", "Totale": "", "Ripetizioni": "", "Intrusioni": "", "Note": ""},
        {"Prova": "Fonemica — S", "Totale": "", "Ripetizioni": "", "Intrusioni": "", "Note": ""},
    ], ["Prova"], "pv_fluenza_verbale")
    st.caption("Il dato più informativo è il rapporto semantica/fonemica e la curva di produzione nei 4 "
               "quarti di minuto (annotare i tempi di lap a 15-30-45-60\").")

    st.markdown("**2.1.4 Relazioni semantiche** (B · C)")
    relazioni_semantiche = _tabella("relazioni_sem", [
        {"Compito": "Somiglianze", "Item": "mela–pera · cane–gatto · tavolo–sedia · braccio–gamba · rabbia–gioia · libertà–giustizia", "Corretti": ""},
        {"Compito": "Categorizzazione (intruso)", "Item": "rosa-tulipano-quercia-margherita · martello-pinza-cacciavite-tavolo · corsa-nuoto-scacchi-salto", "Corretti": ""},
        {"Compito": "Definizioni (C)", "Item": "isola · coraggio · sciopero · promessa · ereditare · ambiguo", "Corretti": ""},
        {"Compito": "Modi di dire (C)", "Item": "«avere la testa fra le nuvole» · «tagliare la corda» · «acqua in bocca»", "Corretti": ""},
    ], ["Compito", "Item"], "pv_relazioni_sem")

    st.markdown("**2.2.1 Ripetizione di frasi** (complessità crescente)")
    st.caption("Leggere una sola volta, ritmo naturale. Codifica: 2 esatta · 1 con 1 errore/semplificazione · "
               "0 ≥2 errori o omissione.")
    ripetizione_frasi = _tabella("ripet_frasi", [
        {"#": 1, "Frase": "Il gatto dorme sul divano.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 2, "Frase": "La bambina ha perso il suo cappello rosso.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 3, "Frase": "Marco non ha ancora finito i compiti di matematica.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 4, "Frase": "Il cane che abbaia è del vicino di casa.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 5, "Frase": "Glielo hanno regalato i nonni per il compleanno.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 6, "Frase": "La finestra è stata chiusa dal maestro prima della lezione.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 7, "Frase": "Se avessi saputo che pioveva, avrei portato l'ombrello.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 8, "Frase": "Il libro che mi hai prestato l'ho lasciato a scuola ieri.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 9, "Frase": "Mentre la mamma cucinava, i bambini apparecchiavano la tavola.", "Punti": "", "Produzione del soggetto": ""},
        {"#": 10, "Frase": "Nonostante fosse stanco, continuò a correre fino al traguardo.", "Punti": "", "Produzione del soggetto": ""},
    ], ["#", "Frase"], "pv_ripet_frasi")
    totale_ripet_frasi = st.text_input("Totale (___/20)", key="pv_tot_ripet_frasi")
    aree_errore = st.multiselect("Gli errori si concentrano su",
                                  ["Clitici", "Passive", "Relative", "Subordinate", "Morfologia verbale",
                                   "Lunghezza (memoria di lavoro)"], key="pv_aree_errore")

    st.markdown("**2.2.2 Comprensione di frasi**")
    comprensione_frasi = _tabella("compr_frasi", [
        {"#": 1, "Struttura": "Attiva semplice", "Frase": "Il bambino spinge la bambina.", "Esito": ""},
        {"#": 2, "Struttura": "Passiva reversibile", "Frase": "Il bambino è spinto dalla bambina.", "Esito": ""},
        {"#": 3, "Struttura": "Dativa", "Frase": "La maestra dà il libro al bambino.", "Esito": ""},
        {"#": 4, "Struttura": "Negazione", "Frase": "Il cane che non corre è nero.", "Esito": ""},
        {"#": 5, "Struttura": "Relativa sul soggetto", "Frase": "La bambina che abbraccia il nonno ha il cappello.", "Esito": ""},
        {"#": 6, "Struttura": "Relativa sull'oggetto", "Frase": "La bambina che il nonno abbraccia ha il cappello.", "Esito": ""},
        {"#": 7, "Struttura": "Locativa complessa", "Frase": "Metti la matita sotto il libro, a destra della gomma.", "Esito": ""},
        {"#": 8, "Struttura": "Temporale invertita", "Frase": "Prima di prendere la penna, tocca il quaderno.", "Esito": ""},
        {"#": 9, "Struttura": "Comparativa", "Frase": "Il gatto è meno grande del cane ma più grande del topo.", "Esito": ""},
        {"#": 10, "Struttura": "Ipotetica", "Frase": "Se il cerchio è rosso, indica il quadrato; altrimenti indica il triangolo.", "Esito": ""},
    ], ["#", "Struttura", "Frase"], "pv_compr_frasi")
    totale_compr_frasi = st.text_input("Totale (___/10)", key="pv_tot_compr_frasi")

    st.markdown("**2.2.3 Produzione elicitata — morfologia**")
    morfologia = _tabella("morfologia", [
        {"Bersaglio": "Plurali regolari e irregolari", "Item": "un albero → due… · un uovo → due… · un uomo → due… · un braccio → due… · una moglie → due…", "Corretti": ""},
        {"Bersaglio": "Accordo nome–aggettivo", "Item": "le scarpe (nuovo)… · i problemi (difficile)… · le città (grande)…", "Corretti": ""},
        {"Bersaglio": "Tempi verbali", "Item": "Oggi vado, ieri… · Domani (venire, io)… · Se potessi, (andare, io)… · Ieri (fare, loro)…", "Corretti": ""},
        {"Bersaglio": "Clitici", "Item": "Dai la palla a Luca → Gliela… · Hai visto Anna? → Sì, …", "Corretti": ""},
        {"Bersaglio": "Preposizioni articolate", "Item": "Il libro è ___ zaino · Vado ___ mare · Il quaderno ___ amici", "Corretti": ""},
        {"Bersaglio": "Connettivi (B·C)", "Item": "Non è uscito ___ pioveva · Studia molto, ___ non prende bei voti", "Corretti": ""},
    ], ["Bersaglio", "Item"], "pv_morfologia")

    st.markdown("**2.3 Livello narrativo**")
    st.caption("Tre modalità, scegliere almeno due: (a) racconto su sequenza di 5-6 figure; (b) racconto di un "
               "evento personale; (c) retelling di una storia letta dall'esaminatore.")
    narrativa_macro = _tabella("narrativa_macro", [
        {"Macrostruttura": "Ambientazione (chi, dove, quando)", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Evento iniziale / problema", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Tentativo / azione", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Conseguenza e conclusione", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Stati interni dei personaggi", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Sequenza temporale corretta", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Coesione: connettivi e anafore", "Valore (0-2)": "", "Note": ""},
        {"Macrostruttura": "Informatività per un ascoltatore ingenuo", "Valore (0-2)": "", "Note": ""},
    ], ["Macrostruttura"], "pv_narrativa_macro")
    totale_narrativa = st.text_input("Totale (___/16)", key="pv_tot_narrativa")
    c15, c16 = st.columns(2)
    with c15:
        n_enunciati = st.text_input("N. enunciati totali", key="pv_n_enunciati")
        lme = st.text_input("LME (parole ÷ enunciati)", key="pv_lme")
        enunciati_completi = st.text_input("Enunciati completi (%)", key="pv_enunciati_completi")
    with c16:
        n_subordinate = st.text_input("N. subordinate / totale enunciati", key="pv_n_subordinate")
        errori_morfosint = st.text_input("Errori morfosintattici (n.)", key="pv_errori_morfosint")
        type_token = st.text_input("Tipi lessicali diversi (type/token)", key="pv_type_token")
    trascrizione_narrativa = st.text_area("Trascrizione / osservazioni", key="pv_trascriz_narrativa", height=80)

    st.markdown("---")
    st.markdown("## PARTE 3 — DISTURBI DELLA FLUENZA")

    st.markdown("**3.1 Anamnesi specifica**")
    familiarita_fluenza = st.text_input("Familiarità (grado parentela, esito: persistenza/remissione)", key="pv_fam_fluenza")
    c17, c18 = st.columns(2)
    epoca_insorgenza = c17.text_input("Epoca di insorgenza (età, modalità)", key="pv_epoca_insorg")
    evento_esordio = c18.text_input("Evento concomitante all'esordio", key="pv_evento_esordio")
    andamento = st.text_input("Andamento (costante, fluttuante, remissioni – durata)", key="pv_andamento")
    c19, c20 = st.columns(2)
    tempo_esordio = c19.text_input("Tempo trascorso dall'esordio", key="pv_tempo_esordio")
    consapevolezza = c20.text_input("Consapevolezza e vissuto riferito", key="pv_consapevolezza")
    reazione_ambiente = st.text_input("Reazione dell'ambiente (famiglia, scuola, pari)", key="pv_reazione_amb")
    trattamenti_fluenza = st.text_area("Trattamenti pregressi ed esiti", key="pv_trattamenti_fluenza", height=60)

    st.markdown("**3.2 Campionamento dell'eloquio**")
    st.caption("Registrare audio-video. Tre campioni di almeno 300 sillabe ciascuno. "
               "%SS = (sillabe balbettate ÷ sillabe totali) × 100.")
    campionamento = _tabella("campionamento", [
        {"Campione": "Conversazione spontanea", "Durata": "", "Sillabe totali": "", "Sillabe balbettate": "", "%SS": "", "Note di contesto": ""},
        {"Campione": "Narrazione / monologo", "Durata": "", "Sillabe totali": "", "Sillabe balbettate": "", "%SS": "", "Note di contesto": ""},
        {"Campione": "Lettura ad alta voce (B·C)", "Durata": "", "Sillabe totali": "", "Sillabe balbettate": "", "%SS": "", "Note di contesto": ""},
    ], ["Campione"], "pv_campionamento")

    st.markdown("**3.3 Tipologia delle disfluenze**")
    c21, c22 = st.columns(2)
    with c21:
        st.markdown("_Disfluenze tipiche della balbuzie (SLD)_")
        sld = _tabella("sld", [
            {"Tipo": "Ripetizione di suono (p-p-palla)", "N.": ""},
            {"Tipo": "Ripetizione di sillaba (pa-pa-palla)", "N.": ""},
            {"Tipo": "Ripetizione di monosillabo (io-io-io)", "N.": ""},
            {"Tipo": "Prolungamento (ssssole)", "N.": ""},
            {"Tipo": "Blocco (arresto udibile o silente)", "N.": ""},
        ], ["Tipo"], "pv_sld")
        totale_sld = st.text_input("Totale SLD", key="pv_tot_sld")
    with c22:
        st.markdown("_Altre disfluenze (OD)_")
        od = _tabella("od", [
            {"Tipo": "Ripetizione di parola plurisillabica", "N.": ""},
            {"Tipo": "Ripetizione di frase / sintagma", "N.": ""},
            {"Tipo": "Revisioni e riformulazioni", "N.": ""},
            {"Tipo": "Interiezioni / riempitivi (ehm, cioè)", "N.": ""},
            {"Tipo": "Pause piene e incomplete", "N.": ""},
        ], ["Tipo"], "pv_od")
        totale_od = st.text_input("Totale OD", key="pv_tot_od")
    c23, c24 = st.columns(2)
    n_medio_iterazioni = c23.text_input("N. medio di iterazioni per unità di ripetizione", key="pv_n_iter")
    durata_blocchi = c24.text_input("Durata dei 3 blocchi più lunghi (\" \" \" → media)", key="pv_durata_blocchi")

    st.markdown("**3.4 Indice di gravità clinica** (griglia interna, 0-4 per dimensione)")
    st.caption("Fasce indicative: 0-4 lieve · 5-9 lieve-moderata · 10-14 moderata · 15-20 grave.")
    gravita = _tabella("gravita", [
        {"Dimensione": "Frequenza (%SS)", "Scala": "<1=0 · 1-2,9=1 · 3-6,9=2 · 7-14,9=3 · ≥15=4", "Punti": ""},
        {"Dimensione": "Durata media dei 3 blocchi", "Scala": "<0,5\"=0 · 0,5-0,9\"=1 · 1-1,9\"=2 · 2-4,9\"=3 · ≥5\"=4", "Punti": ""},
        {"Dimensione": "Tensione / sforzo udibile", "Scala": "assente=0 · minima=1 · percepibile=2 · marcata=3 · estrema=4", "Punti": ""},
        {"Dimensione": "Concomitanti motori", "Scala": "assenti=0 · appena visibili=1 · evidenti=2 · vistosi=3 · invalidanti=4", "Punti": ""},
        {"Dimensione": "Evitamento", "Scala": "assente=0 · raro=1 · occasionale=2 · frequente=3 · pervasivo=4", "Punti": ""},
    ], ["Dimensione", "Scala"], "pv_gravita")
    totale_gravita = st.text_input("Totale (0-20)", key="pv_tot_gravita")

    st.markdown("**3.5 Concomitanti fisici e respiratori**")
    concomitanti = st.multiselect("Segnalazioni", [
        "Serramento labiale/mandibolare", "Ammiccamento, chiusura oculare", "Smorfie facciali",
        "Apnea / blocco fonatorio", "Respirazione costale alta", "Ipertono cervico-scapolare",
        "Movimenti del capo", "Movimenti di arti/tronco", "Perdita del contatto oculare",
        "Inspirazione rumorosa o insufficiente", "Fonazione su volume residuo", "Attacco vocale duro",
    ], key="pv_concomitanti")

    st.markdown("**3.6 Tachilalia e cluttering**")
    c25, c26 = st.columns(2)
    velocita_globale = c25.text_input("Velocità di eloquio globale (sill/min)", key="pv_vel_globale")
    velocita_articolatoria = c26.text_input("Velocità articolatoria (sill/sec) — rif. adulto ~4-6", key="pv_vel_artic")
    c27, c28 = st.columns(2)
    velocita_lettura = c27.text_input("Velocità in lettura (parole/min) — vedi 4.1c", key="pv_vel_lettura")
    rapporto_lettura_eloquio = c28.text_input("Rapporto lettura/eloquio", key="pv_rapp_lett_eloq")
    indicatori_cluttering = st.multiselect("Indicatori di cluttering", [
        "Collasso/telescoping sillabico", "Coarticolazione eccessiva, articolazione imprecisa",
        "Pause in punti sintatticamente inadeguati", "Numerose revisioni, false partenze, interiezioni",
        "Disorganizzazione del discorso, digressioni", "Scarsa consapevolezza del problema",
        "Migliora se gli si chiede di rallentare/parlare con cura"], key="pv_indic_cluttering")

    st.markdown("**3.7 Sintomatologia extra-verbale e profilo PNEV**")
    vissuto_emotivo = st.text_area("Vissuto emotivo (ansia anticipatoria, vergogna, frustrazione)", key="pv_vissuto", height=60)
    evitamento = st.text_area("Evitamento di parole/situazioni/interlocutori; strategie di sostituzione", key="pv_evitamento", height=60)
    impatto_funzionale = st.text_input("Impatto funzionale (scuola, amicizie, telefono, lettura ad alta voce)", key="pv_impatto")
    postura_tono = st.text_input("Postura e tono (asse, cingolo scapolare, appoggio, tenuta del capo)", key="pv_postura_tono")
    pattern_respiratorio = st.text_input("Pattern respiratorio a riposo e in fonazione", key="pv_pattern_resp")
    profilo_uditivo = st.text_input("Profilo uditivo (lateralità, tenuta attentiva dx/sx, ipersensibilità)", key="pv_profilo_udit")
    profilo_visivo = st.text_input("Profilo visivo (motilità, convergenza, accomodazione, coord. occhio-voce)", key="pv_profilo_vis")
    riflessi_rilevati = st.text_input("Riflessi primitivi rilevati", key="pv_riflessi_rilevati")

    st.markdown("---")
    st.markdown("## PARTE 4 — APPRENDIMENTO")
    st.markdown("### 4.1 Lettura")

    st.markdown("**4.1a Lettura di parole** — 4 liste × 16 item")
    st.caption("Cronometrare ogni lista separatamente. Errori: sostituzione, omissione, aggiunta, "
               "inversione, autocorrezione (AC).")
    st.caption("**L1 — corte, alta frequenza**: mano · casa · pane · sole · nave · dito · sedia · fuoco · "
               "gatto · tempo · strada · libro · acqua · sera · lume · notte")
    st.caption("**L2 — lunghe, alta frequenza**: bicicletta · finestra · maestra · telefono · ospedale · "
               "giornale · pomeriggio · macchina · televisione · ombrello · montagna · compagno · "
               "attenzione · magazzino · biblioteca · passeggiata")
    st.caption("**L3 — corte, bassa frequenza**: gelo · nesso · tino · vaglio · lembo · rogo · scafo · "
               "tregua · ghiro · falda · sponda · zolla · greggio · incudine · tomo · guglia")
    st.caption("**L4 — lunghe, bassa frequenza**: clessidra · sopraffazione · imperscrutabile · propaggine · "
               "scalpellino · stravaganza · circonvallazione · sconquasso · quadrifoglio · ragguaglio · "
               "svogliatezza · intraprendenza · accigliato · chiacchiericcio · rimpatriata · sbigottimento")
    lettura_parole = _tabella("lettura_parole", [
        {"Lista": "L1 — corte, alta frequenza", "Tempo": "", "Errori": "", "Sill/sec": ""},
        {"Lista": "L2 — lunghe, alta frequenza", "Tempo": "", "Errori": "", "Sill/sec": ""},
        {"Lista": "L3 — corte, bassa frequenza", "Tempo": "", "Errori": "", "Sill/sec": ""},
        {"Lista": "L4 — lunghe, bassa frequenza", "Tempo": "", "Errori": "", "Sill/sec": ""},
    ], ["Lista"], "pv_lett_parole")

    st.markdown("**4.1b Lettura di non parole** — 2 liste × 16 item")
    st.caption("**NP1 — struttura semplice**: lomo · tefa · dinu · sapre · velto · mudo · fanti · resalo · "
               "bipo · calse · nuto · gremo · sadi · porfa · tenu · lavri")
    st.caption("**NP2 — struttura complessa**: strafulgo · gnaviglio · pesciantro · zampiglia · sclorendo · "
               "chiarottine · sbrugnale · trasbricchi · squagliento · rimpocciato · glinturbo · scervignano · "
               "spraviglio · quorbiaccio · ghiandrelpo · strullaggine")
    lettura_nonparole = _tabella("lettura_nonparole", [
        {"Lista": "NP1 — struttura semplice", "Tempo": "", "Errori": "", "Sill/sec": ""},
        {"Lista": "NP2 — struttura complessa", "Tempo": "", "Errori": "", "Sill/sec": ""},
    ], ["Lista"], "pv_lett_nonparole")
    indice_discrepanza = st.text_input(
        "Indice di discrepanza parole/non parole (sill/sec L1+L2 ÷ sill/sec NP1+NP2)", key="pv_indice_discr")

    st.markdown("**4.1c Lettura di brano — tavole IReST**")
    st.caption("Le 10 tavole IReST sono materiale editoriale protetto: si usano le copie originali in "
               "dotazione allo studio, non riprodotte qui. Sotto solo i parametri/norme per il calcolo.")
    tavole_irest = _tabella("tavole_irest", [
        {"N.": 1, "Nome": "Topi", "Categoria": "CD", "Parole": 138, "Sillabe": 299, "Lettere": 675, "Tempo medio±DS (s)": "46,4 ± 5,2", "Velocità media±DS (par/min)": "181 ± 24", "Usata il": ""},
        {"N.": 2, "Nome": "Castoro", "Categoria": "A", "Parole": 144, "Sillabe": 295, "Lettere": 677, "Tempo medio±DS (s)": "42,6 ± 5,1", "Velocità media±DS (par/min)": "206 ± 29", "Usata il": ""},
        {"N.": 3, "Nome": "Alberi", "Categoria": "B", "Parole": 140, "Sillabe": 283, "Lettere": 674, "Tempo medio±DS (s)": "43,8 ± 5,5", "Velocità media±DS (par/min)": "194 ± 24", "Usata il": ""},
        {"N.": 4, "Nome": "Preda", "Categoria": "BC", "Parole": 134, "Sillabe": 299, "Lettere": 687, "Tempo medio±DS (s)": "44,1 ± 5,5", "Velocità media±DS (par/min)": "185 ± 26", "Usata il": ""},
        {"N.": 5, "Nome": "Deserto", "Categoria": "BC", "Parole": 135, "Sillabe": 294, "Lettere": 687, "Tempo medio±DS (s)": "43,9 ± 5,4", "Velocità media±DS (par/min)": "188 ± 26", "Usata il": ""},
        {"N.": 6, "Nome": "Veleno", "Categoria": "D", "Parole": 126, "Sillabe": 302, "Lettere": 689, "Tempo medio±DS (s)": "44,7 ± 6,3", "Velocità media±DS (par/min)": "174 ± 29", "Usata il": ""},
        {"N.": 7, "Nome": "Isola", "Categoria": "B", "Parole": 134, "Sillabe": 298, "Lettere": 684, "Tempo medio±DS (s)": "42,5 ± 5,8", "Velocità media±DS (par/min)": "193 ± 29", "Usata il": ""},
        {"N.": 8, "Nome": "Ragni", "Categoria": "BC", "Parole": 134, "Sillabe": 260, "Lettere": 688, "Tempo medio±DS (s)": "43,4 ± 5,2", "Velocità media±DS (par/min)": "188 ± 27", "Usata il": ""},
        {"N.": 9, "Nome": "Inverno", "Categoria": "BC", "Parole": 132, "Sillabe": 289, "Lettere": 688, "Tempo medio±DS (s)": "43,5 ± 6,8", "Velocità media±DS (par/min)": "187 ± 34", "Usata il": ""},
        {"N.": 10, "Nome": "Colori", "Categoria": "CD", "Parole": 131, "Sillabe": 297, "Lettere": 684, "Tempo medio±DS (s)": "44,7 ± 6,4", "Velocità media±DS (par/min)": "179 ± 27", "Usata il": ""},
    ], ["N.", "Nome", "Categoria", "Parole", "Sillabe", "Lettere", "Tempo medio±DS (s)", "Velocità media±DS (par/min)"], "pv_tavole_irest")
    st.caption("Calcolo per la/e tavola/e usate: Tempo (cronometro) · Velocità par/min = parole×60÷tempo · "
               "Velocità sill/sec = sillabe÷tempo · z = (par/min − media)÷DS · Errori (conteggio su registrazione) "
               "· Accuratezza % = (parole−errori)×100÷parole. In età evolutiva lo z non è una norma per età: "
               "usare come misura ripetibile intra-soggetto.")
    esiti_irest = _tabella("esiti_irest", [
        {"Tavola usata": "", "Tempo (s)": "", "Velocità (par/min)": "", "z": "", "Errori": "", "Accuratezza %": ""},
        {"Tavola usata": "", "Tempo (s)": "", "Velocità (par/min)": "", "z": "", "Errori": "", "Accuratezza %": ""},
        {"Tavola usata": "", "Tempo (s)": "", "Velocità (par/min)": "", "z": "", "Errori": "", "Accuratezza %": ""},
    ], [], "pv_esiti_irest")

    st.markdown("**4.1d Comprensione del brano**")
    st.caption("6 domande per tavola (3 letterali, 2 inferenziali, 1 lessicale), orali a testo chiuso. "
               "Punteggio: 2 completa/corretta · 1 parziale/dopo richiesta di precisazione · 0 errata/assente. "
               "Totale 0-12 (2 tavole) — le domande specifiche per ciascuna delle 10 tavole sono nel documento "
               "cartaceo originale, da consultare durante la somministrazione.")
    compr_irest = _tabella("compr_irest", [
        {"Tavola": "", "L1": "", "L2": "", "L3": "", "I1": "", "I2": "", "X1": "", "Totale (0-12)": ""},
        {"Tavola": "", "L1": "", "L2": "", "L3": "", "I1": "", "I2": "", "X1": "", "Totale (0-12)": ""},
    ], ["Tavola"], "pv_compr_irest")

    st.markdown("**4.1g Osservazione qualitativa durante la lettura**")
    oss_lettura = st.multiselect("Osservazioni", [
        "Perdita del rigo / salti di riga", "Riletture e ritorni indietro", "Lettura sillabica / a scatti",
        "Anticipazione con errore lessicale", "Prosodia assente o inadeguata", "Uso del dito o del segnarighe",
        "Avvicinamento eccessivo al testo", "Ammiccamento, lacrimazione, sfregamento occhi",
        "Affaticamento progressivo (ultimo terzo del brano)", "Inclinazione del capo / occlusione di un occhio",
    ], key="pv_oss_lettura")

    st.markdown("### 4.2 Scrittura")
    st.caption("Foglio a righe di classe, penna abituale. Dettatura a voce naturale, un'unica ripetizione "
               "per segmento su richiesta. Cronometrare l'intero dettato.")
    st.markdown("**4.2a Dettato di parole e non parole** (tutte le fasce)")
    dettato_parole = _tabella("dettato_parole", [
        {"Serie": "P1 — parole regolari", "Item": "tavolo · fiume · pratica · salame · destino · burrone · mandorla · calamita", "Errori": ""},
        {"Serie": "P2 — digrammi/trigrammi", "Item": "chiodo · ghiaccio · scienza · guglia · sciopero · ciliegia · gnocco · quaglia", "Errori": ""},
        {"Serie": "P3 — doppie e accenti", "Item": "bicchiere · perché · attrezzo · città · raggruppare · virtù · soqquadro · lassù", "Errori": ""},
        {"Serie": "NP — non parole", "Item": "brastone · gliunfo · scenaglio · quortimo · sbicchera · zampruglio · ghialdo · trescimo", "Errori": ""},
    ], ["Serie", "Item"], "pv_dettato_parole")

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
    dettato_esiti = st.text_area("Esiti dettato brano (errori, tempo, ripetizioni richieste)",
                                  key="pv_dettato_esiti", height=68)

    st.markdown("**4.2e Dettato di coppie omofone non omografe** (B dalla 3ª · C)")
    omofone = _tabella("omofone", [
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
    ], ["#", "Frase", "Bersaglio"], "pv_omofone")

    st.markdown("**4.2f Griglia di analisi degli errori**")
    griglia_errori = _tabella("griglia_errori", [
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
    ], ["Categoria", "Sottotipo"], "pv_griglia_errori")
    c29, c30, c31 = st.columns(3)
    tempo_dettato = c29.text_input("Tempo totale dettato (' \")", key="pv_tempo_dettato")
    parole_min_scrittura = c30.text_input("Parole/min in scrittura", key="pv_par_min_scrittura")
    profilo_prevalente = c31.selectbox("Profilo prevalente",
                                        ["", "Fonologico", "Non fonologico/lessicale", "Fonetico", "Misto"],
                                        key="pv_profilo_prevalente")

    st.markdown("### 4.3 Grafia")
    st.markdown("**4.3a Prove di automatismo grafico** (cronometrate)")
    grafia_automatismo = _tabella("grafia_autom", [
        {"#": "1", "Prova": "Sequenza «le le le» in corsivo (30\")", "Indice": "grafemi/30\"", "Valore": ""},
        {"#": "2", "Prova": "Alfabeto corsivo minuscolo a memoria", "Indice": "lettere/min", "Valore": ""},
        {"#": "3", "Prova": "Numeri da 1 a 20", "Indice": "cifre/min", "Valore": ""},
        {"#": "4a", "Prova": "Frase ripetuta 60\" — velocità spontanea (Vspont)", "Indice": "n. grafemi", "Valore": ""},
        {"#": "4b", "Prova": "Stessa frase — massima velocità (Vmax)", "Indice": "n. grafemi", "Valore": ""},
        {"#": "4c", "Prova": "Stessa frase — massima accuratezza (Vacc)", "Indice": "n. grafemi", "Valore": ""},
        {"#": "5", "Prova": "Copia ravvicinata (120\")", "Indice": "grafemi/min", "Valore": ""},
        {"#": "6", "Prova": "Copia da lontano/lavagna (120\")", "Indice": "grafemi/min", "Valore": ""},
    ], ["#", "Prova", "Indice"], "pv_grafia_autom")
    indici_derivati = _tabella("indici_derivati", [
        {"Indice derivato": "Riserva di velocità", "Calcolo": "Vmax ÷ Vspont", "Valore": "", "Lettura": "<1,2 → costo attentivo elevato"},
        {"Indice derivato": "Costo dell'accuratezza", "Calcolo": "Vacc ÷ Vspont", "Valore": "", "Lettura": "Molto <1 → automatizzazione incompleta"},
        {"Indice derivato": "Divario copia vicina/lontana", "Calcolo": "prova 5 ÷ prova 6", "Valore": "", "Lettura": ">1,3 → verificare accomodazione/memoria visiva"},
        {"Indice derivato": "Divario copia/dettato", "Calcolo": "prova 5 ÷ par-min 4.2f", "Valore": "", "Lettura": "Dettato molto più lento → carico ortografico"},
        {"Indice derivato": "Decadimento", "Calcolo": "grafemi 2ª metà ÷ 1ª metà (prova 4a)", "Valore": "", "Lettura": "<0,85 → affaticabilità"},
    ], ["Indice derivato", "Calcolo", "Lettura"], "pv_indici_derivati")

    st.markdown("**4.3b Griglia qualitativa dei parametri grafici**")
    st.caption("0 assente/adeguato · 1 lieve · 2 marcato. Valutare sulla prova 4a e sul brano dettato.")
    grafia_qualit = _tabella("grafia_qualit", [
        {"Parametro": "Scrittura troppo grande/piccola", "0-1-2": ""},
        {"Parametro": "Disomogeneità dimensionale tra lettere", "0-1-2": ""},
        {"Parametro": "Ondulazione/deriva rispetto al rigo", "0-1-2": ""},
        {"Parametro": "Spaziatura inter-lettera irregolare", "0-1-2": ""},
        {"Parametro": "Spaziatura inter-parola irregolare/assente", "0-1-2": ""},
        {"Parametro": "Inclinazione variabile", "0-1-2": ""},
        {"Parametro": "Mancato rispetto dei margini", "0-1-2": ""},
        {"Parametro": "Sovrapposizione di lettere o parole", "0-1-2": ""},
        {"Parametro": "Legature assenti o scorrette", "0-1-2": ""},
        {"Parametro": "Forme ambigue o non riconoscibili", "0-1-2": ""},
        {"Parametro": "Ritocchi, ripassi, correzioni sul tratto", "0-1-2": ""},
        {"Parametro": "Pressione eccessiva", "0-1-2": ""},
        {"Parametro": "Pressione insufficiente/tratto evanescente", "0-1-2": ""},
        {"Parametro": "Tratto tremolante, spezzato o angoloso", "0-1-2": ""},
        {"Parametro": "Mescolanza corsivo/stampato", "0-1-2": ""},
        {"Parametro": "Peggioramento nell'ultimo terzo della pagina", "0-1-2": ""},
    ], ["Parametro"], "pv_grafia_qualit")
    totale_grafia_qualit = st.text_input("Totale (0-32) — 0-6 adeguata · 7-14 immatura · 15-22 disgrafica "
                                          "lieve-moderata · ≥23 marcata", key="pv_tot_grafia_qualit")
    c32, c33 = st.columns(2)
    presa_strumento = c32.selectbox("Presa dello strumento",
                                     ["", "Tripode dinamico", "Tripode statico", "Quadripode", "A pugno",
                                      "Pollice sovrapposto", "Altro"], key="pv_presa")
    postura_grafia = c33.selectbox("Postura del tronco e del capo",
                                    ["", "Eretta", "Iperflessione", "Rotazione", "Inclinazione", "Appoggio sul braccio"],
                                    key="pv_postura_grafia")

    st.markdown("### 4.4 Calcolo")
    st.markdown("**4.4a Enumerazione e conteggio**")
    enumerazione_tab = _tabella("enumerazione_tab", [
        {"Prova": "Avanti", "Fascia A": "1→10/1→20", "Fascia B": "1→50", "Fascia C": "1→100", "Tempo": "", "Errori": ""},
        {"Prova": "Indietro", "Fascia A": "da 10", "Fascia B": "da 20/da 50", "Fascia C": "da 100", "Tempo": "", "Errori": ""},
        {"Prova": "A salti di 2", "Fascia A": "—", "Fascia B": "avanti da 0", "Fascia C": "avanti e indietro", "Tempo": "", "Errori": ""},
        {"Prova": "A salti di 3 e 5", "Fascia A": "—", "Fascia B": "di 5 avanti", "Fascia C": "di 3 avanti/indietro", "Tempo": "", "Errori": ""},
        {"Prova": "Avanti da un numero dato", "Fascia A": "da 4", "Fascia B": "da 27, da 68", "Fascia C": "da 197, da 1096", "Tempo": "", "Errori": ""},
    ], ["Prova", "Fascia A", "Fascia B", "Fascia C"], "pv_enumerazione")

    st.markdown("**4.4b Transcodifica**")
    transcodifica = _tabella("transcodifica", [
        {"Compito": "Lettura di numeri", "Item": "7 · 15 · 30 · 108 · 250 · 1.005 · 3.070 · 12.400 · 105.000 · 1.203.000", "Corretti": ""},
        {"Compito": "Scrittura sotto dettato", "Item": "9 · 13 · 40 · 207 · 380 · 2.004 · 5.060 · 17.300 · 204.000 · 3.012.000", "Corretti": ""},
        {"Compito": "Confronto di numerosità", "Item": "37/73 · 109/91 · 1.020/1.002 · 0,7/0,25 (C) · 3/4 vs 2/3 (C)", "Corretti": ""},
        {"Compito": "Ordinamento crescente", "Item": "408 · 84 · 480 · 48 · 804", "Corretti": ""},
        {"Compito": "Valore posizionale", "Item": "In 3.507, quante decine? · Cifra delle centinaia in 24.960?", "Corretti": ""},
    ], ["Compito", "Item"], "pv_transcodifica")

    st.markdown("**4.4c Fatti aritmetici e tabelline**")
    fatti_aritmetici = _tabella("fatti_aritm", [
        {"Prova": "Entro il 10", "Item": "3+4 · 5+2 · 6+3 · 9−4 · 8−5 · 7−3 · 2+7 · 10−6", "Corretti": ""},
        {"Prova": "Entro il 20", "Item": "8+7 · 9+6 · 14−8 · 17−9 · 12−5 · 6+9 · 15−7 · 8+8", "Corretti": ""},
        {"Prova": "Tabelline in ordine (B)", "Item": "del 3 · del 6 · del 7 · dell'8", "Corretti": ""},
        {"Prova": "Tabelline a salto", "Item": "7×8 · 6×9 · 4×7 · 8×8 · 9×7 · 6×6 · 3×9 · 8×4", "Corretti": ""},
    ], ["Prova", "Item"], "pv_fatti_aritm")
    recupero_diretto = st.text_input("Item risolti entro 3\" (recupero diretto) — ___/32", key="pv_recupero_diretto")

    st.markdown("**4.4d Calcolo a mente** (max 30\" per item)")
    calcolo_mente = _tabella("calcolo_mente", [
        {"#": 1, "Item": "17 + 8", "Risposta": "", "Tempo": ""}, {"#": 2, "Item": "34 − 9", "Risposta": "", "Tempo": ""},
        {"#": 3, "Item": "25 + 25", "Risposta": "", "Tempo": ""}, {"#": 4, "Item": "48 + 30", "Risposta": "", "Tempo": ""},
        {"#": 5, "Item": "62 − 17", "Risposta": "", "Tempo": ""}, {"#": 6, "Item": "7 × 12", "Risposta": "", "Tempo": ""},
        {"#": 7, "Item": "135 + 48", "Risposta": "", "Tempo": ""}, {"#": 8, "Item": "200 − 47", "Risposta": "", "Tempo": ""},
        {"#": 9, "Item": "15 × 4", "Risposta": "", "Tempo": ""}, {"#": 10, "Item": "96 ÷ 8", "Risposta": "", "Tempo": ""},
        {"#": 11, "Item": "25% di 80 (C)", "Risposta": "", "Tempo": ""}, {"#": 12, "Item": "1,5 + 0,75 (C)", "Risposta": "", "Tempo": ""},
    ], ["#", "Item"], "pv_calcolo_mente")

    st.markdown("**4.4e Calcolo scritto**")
    calcolo_scritto_tab = _tabella("calcolo_scritto_tab", [
        {"Operazione": "Addizione con riporto", "Item": "468 + 275 · 3.947 + 1.868", "Corretti": ""},
        {"Operazione": "Sottrazione con prestito", "Item": "704 − 268 · 5.003 − 1.847", "Corretti": ""},
        {"Operazione": "Moltiplicazione a due cifre", "Item": "46 × 27 · 308 × 45", "Corretti": ""},
        {"Operazione": "Divisione", "Item": "936 ÷ 4 · 1.428 ÷ 12", "Corretti": ""},
        {"Operazione": "Con decimali (C)", "Item": "12,7 + 5,48 · 8,4 × 2,5", "Corretti": ""},
    ], ["Operazione", "Item"], "pv_calcolo_scritto_tab")

    st.markdown("**4.4f Problemi** (B · C)")
    st.caption("P1. In una classe ci sono 24 alunni. Ogni alunno porta 3 quaderni. Quanti quaderni in tutto?")
    st.caption("P2. Luca aveva 50 euro. Ha comprato un libro da 18 euro e una penna da 4 euro. Quanto gli resta?")
    st.caption("P3. Un pullman ha 52 posti. Partono 3 pullman pieni e un quarto con 29 passeggeri. Quante "
               "persone in viaggio?")
    st.caption("P4 (C). Un negozio applica uno sconto del 20% su un articolo da 75 euro, poi aggiunge 3,50 "
               "euro di spedizione. Quanto si paga?")
    problemi_tab = _tabella("problemi_tab", [
        {"Problema": "P1", "Comprensione testo (0-2)": "", "Rappresentazione (0-2)": "", "Piano risolutivo (0-2)": "", "Esecuzione (0-2)": "", "Note": ""},
        {"Problema": "P2", "Comprensione testo (0-2)": "", "Rappresentazione (0-2)": "", "Piano risolutivo (0-2)": "", "Esecuzione (0-2)": "", "Note": ""},
        {"Problema": "P3", "Comprensione testo (0-2)": "", "Rappresentazione (0-2)": "", "Piano risolutivo (0-2)": "", "Esecuzione (0-2)": "", "Note": ""},
        {"Problema": "P4", "Comprensione testo (0-2)": "", "Rappresentazione (0-2)": "", "Piano risolutivo (0-2)": "", "Esecuzione (0-2)": "", "Note": ""},
    ], ["Problema"], "pv_problemi_tab")

    st.markdown("---")
    st.markdown("## PARTE 5 — SINTESI DEL PROFILO")
    st.caption("Giudizio: N nella norma attesa · B borderline · D prestazione deficitaria · NV non valutabile.")
    sintesi_profilo = _tabella("sintesi_profilo", [
        {"Area": "Fonologia", "Prova": "PCC / Inventario / Processi oltre limite", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Linguaggio", "Prova": "Lessicale-semantico / Morfosintattico / Narrativo", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Fluenza", "Prova": "%SS e tipologia SLD / Indice gravità", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Lettura", "Prova": "Parole/non parole / Brano IReST / Comprensione", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Scrittura", "Prova": "Errori per categoria / Omofone non omografe", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Grafia", "Prova": "Velocità e riserva / Griglia qualitativa", "Dato grezzo": "", "Giudizio": "", "Note": ""},
        {"Area": "Calcolo", "Prova": "Fatti aritmetici / Calcolo scritto / Transcodifica", "Dato grezzo": "", "Giudizio": "", "Note": ""},
    ], ["Area", "Prova"], "pv_sintesi_profilo")
    st.markdown("**Osservazioni integrate (profilo PNEV)**")
    oss_visione = st.text_input("Visione (motilità, convergenza, accomodazione, coord. occhio-mano/voce)", key="pv_oss_visione")
    oss_ascolto = st.text_input("Ascolto (lateralità, tenuta attentiva, discriminazione, ipersensibilità)", key="pv_oss_ascolto")
    oss_riflessi = st.text_input("Riflessi primitivi e schema motorio", key="pv_oss_riflessi")
    oss_postura = st.text_input("Postura, respiro, tono", key="pv_oss_postura")
    ipotesi_lavoro = st.text_area("Ipotesi di lavoro e indicazioni", key="pv_ipotesi_lavoro", height=68)
    c34, c35 = st.columns(2)
    data_restituzione = c34.text_input("Data della restituzione — presenti", key="pv_data_restituzione")
    proposta_intervento = c35.text_input("Proposta di intervento", key="pv_proposta_intervento")
    rivalutazione_prevista = st.text_input("Rivalutazione prevista — prove da ripetere", key="pv_rivalutazione")


    st.markdown("---")
    st.markdown("## PARTE 6 — VALUTAZIONE MIOFUNZIONALE")
    st.markdown("**6.1 Anamnesi miofunzionale**")
    mio_anamnesi_tab = _tabella("mio_anamnesi_tab", [
        {"#": 1, "Domanda": "Parto", "Risposta": ""},
        {"#": 2, "Domanda": "Allattamento esclusivo al seno (sì/no, per quanto tempo)", "Risposta": ""},
        {"#": 3, "Domanda": "Biberon — ciucciotto", "Risposta": ""},
        {"#": 4, "Domanda": "Coliche gassose", "Risposta": ""},
        {"#": 5, "Domanda": "Età dello svezzamento", "Risposta": ""},
        {"#": 6, "Domanda": "Passaggio ai cibi solidi", "Risposta": ""},
        {"#": 7, "Domanda": "Tappe: cammino / linguaggio / gattonamento", "Risposta": ""},
        {"#": 8, "Domanda": "Otiti (frequenza/età)", "Risposta": ""},
        {"#": 9, "Domanda": "Sintomi uditivi", "Risposta": ""},
        {"#": 10, "Domanda": "Tonsille / adenoidi (operato, quando)", "Risposta": ""},
        {"#": 11, "Domanda": "Mal di testa (regione, frequenza, insorgenza)", "Risposta": ""},
        {"#": 12, "Domanda": "Dolori muscolo-scheletrici", "Risposta": ""},
        {"#": 13, "Domanda": "Apparato digerente e modalità del pasto", "Risposta": ""},
        {"#": 14, "Domanda": "Ciclo irregolare / dismenorrea (se pertinente)", "Risposta": ""},
        {"#": 15, "Domanda": "Bocca aperta davanti alla TV", "Risposta": ""},
        {"#": 16, "Domanda": "Sonno (bocca aperta, russa, bruxismo, apnee)", "Risposta": ""},
        {"#": 17, "Domanda": "Abitudine a succhiare (pollice/labbra/lingua/nocche/oggetti)", "Risposta": ""},
        {"#": 18, "Domanda": "Onicofagia", "Risposta": ""},
        {"#": 19, "Domanda": "Problemi ortopedici", "Risposta": ""},
        {"#": 20, "Domanda": "Difficoltà di pronuncia (riportare in Parte 1)", "Risposta": ""},
        {"#": 21, "Domanda": "Allergie respiratorie / asma", "Risposta": ""},
        {"#": 22, "Domanda": "Altro che potrebbe influire sul trattamento", "Risposta": ""},
    ], ["#", "Domanda"], "pv_mio_anamnesi")

    st.markdown("**6.2 Squilibrio muscolare orofacciale**")
    c36, c37 = st.columns(2)
    mecc_respiratorio = c36.selectbox("Meccanismo respiratorio", ["", "Nasale", "Orale", "Misto"], key="pv_mecc_resp")
    orl_pregresse = c37.text_input("Problematiche ORL pregresse e attuali", key="pv_orl_pregresse")
    abitudini_viziate = st.text_input("Abitudini viziate pregresse e attuali", key="pv_abit_viziate")
    c38, c39 = st.columns(2)
    masticazione = c38.selectbox("Masticazione", ["", "Bilaterale alternata", "Monolaterale dx", "Monolaterale sx", "Anteriore"], key="pv_masticazione")
    masticazione_rumorosa = c39.selectbox("Masticazione rumorosa", ["", "Sì", "No"], key="pv_masticazione_rum")
    postura_orale_riposo = st.selectbox("Postura orale a riposo",
        ["", "Labbra competenti", "Incompetenza labiale", "Interposizione linguale", "Ipotonia periorale"], key="pv_postura_orale_riposo")
    postura_linguale_pv = st.selectbox("Postura linguale",
        ["", "Al palato (spot)", "Bassa", "Interdentale", "Interposta lateralmente"], key="pv_postura_linguale")
    c40, c41 = st.columns(2)
    frenulo_linguale = c40.selectbox("Frenulo linguale", ["", "Normale", "Corto", "Anteriore"], key="pv_frenulo_ling")
    frenulo_labiale = c41.selectbox("Frenulo labiale superiore", ["", "Normale", "Ipertrofico"], key="pv_frenulo_lab")
    palato = st.selectbox("Palato", ["", "Normoconformato", "Ogivale", "Stretto", "Morso crociato/aperto/profondo"], key="pv_palato")
    st.caption("Prassie oro-bucco-facciali (0 assente · 1 imprecisa · 2 adeguata)")
    prassie = _tabella("prassie", [
        {"Distretto": "Labbra", "0-1-2": ""}, {"Distretto": "Lingua", "0-1-2": ""},
        {"Distretto": "Guance", "0-1-2": ""}, {"Distretto": "Mandibola", "0-1-2": ""},
        {"Distretto": "Velo", "0-1-2": ""},
    ], ["Distretto"], "pv_prassie")
    deglutizione_pv = st.selectbox("Deglutizione",
        ["", "Fisiologica", "Atipica con spinta anteriore", "Atipica con spinta laterale",
         "Con contrazione periorale", "Con interposizione"], key="pv_deglutizione_pv")
    tono_simmetria = st.text_input("Tono e simmetria facciale", key="pv_tono_simmetria")
    c42, c43 = st.columns(2)
    atm = c42.multiselect("ATM", ["Clic dx", "Clic sx", "Dolore", "Deviazione in apertura"], key="pv_atm")
    apertura_max = c43.text_input("Apertura massima (mm)", key="pv_apertura_max")
    sintesi_miofunzionale = st.text_area("Sintesi miofunzionale", key="pv_sintesi_mio", height=68)

    st.markdown("---")
    st.markdown("## PARTE 7 — VALUTAZIONE OSTEOPATICA")
    hobby_osteo = st.text_input("Hobby / sport praticati", key="pv_hobby_osteo")
    st.markdown("**7.1 Anamnesi**")
    c44, c45 = st.columns(2)
    osteo_gravidanza = c44.text_input("Gravidanza / parto", key="pv_osteo_gravidanza")
    osteo_crescita = c45.text_input("Crescita e sviluppo (peso, tappe motorie)", key="pv_osteo_crescita")
    c46, c47 = st.columns(2)
    osteo_allattamento = c46.text_input("Allattamento / alimentazione", key="pv_osteo_allattamento")
    osteo_sonno = c47.text_input("Sonno / pianto", key="pv_osteo_sonno")
    c48, c49 = st.columns(2)
    osteo_patologie = c48.text_input("Patologie note / visite specialistiche", key="pv_osteo_patologie")
    osteo_traumi = c49.text_input("Traumi, cadute, interventi", key="pv_osteo_traumi")

    st.markdown("**7.2 Test osteopatici**")
    st.caption("L libero · R restrizione · RR restrizione marcata. Indicare lato e direzione.")
    test_osteopatici = _tabella("test_osteopatici", [
        {"Distretto": "Cranio", "Test": "Motilità MRP / ampiezza e ritmo / SSB, occipite, temporali, mascellari", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Cervicale", "Test": "OAA, rotazione, flesso-estensione", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Dorsale e coste", "Test": "Mobilità segmentaria, giunzione cervico-dorsale", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Diaframma", "Test": "Escursione, cupole, giunzione dorso-lombare", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Lombare e bacino", "Test": "Iliaci, sacro, sinfisi", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Arti inferiori", "Test": "Anche, ginocchia, caviglie, appoggio plantare", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Viscerale", "Test": "Mobilità addominale, tensioni sovradiaframmatiche", "L/R/RR": "", "Rilievo": ""},
        {"Distretto": "Catene e postura", "Test": "Asse, rotazioni, test di Fukuda, appoggi", "L/R/RR": "", "Rilievo": ""},
    ], ["Distretto", "Test"], "pv_test_osteopatici")
    sintesi_osteopatica = st.text_area("7.3 Sintesi / note", key="pv_sintesi_osteo", height=68)
    indicazioni_osteo = st.radio("7.4 Indicazioni", [
        "Nessuna restrizione significativa", "Possibile beneficio da trattamento osteopatico",
        "Suggerita valutazione pediatrica / specialistica"], key="pv_indic_osteo")

    st.markdown("---")
    st.markdown("## PARTE 8 — VALUTAZIONE VISUO-POSTURALE E OPTOMETRICA")
    st.markdown("**8.1 Acuità visiva e allineamento**")
    acuita_visiva = _tabella("acuita_visiva", [
        {"Misura": "AV naturale — lontano", "OD": "", "OS": "", "OO": "", "Note": ""},
        {"Misura": "AV naturale — vicino", "OD": "", "OS": "", "OO": "", "Note": ""},
        {"Misura": "AV con correzione", "OD": "", "OS": "", "OO": "", "Note": ""},
    ], ["Misura"], "pv_acuita_visiva")
    correzione_in_uso = st.text_input("Correzione in uso", key="pv_correzione_uso")
    cover_test_pv = _tabella("cover_test_pv", [
        {"Cover test": "Cover / uncover", "XL (lontano)": "", "XV (vicino)": "", "Tipo/direzione/recupero": ""},
        {"Cover test": "Cover alternato", "XL (lontano)": "", "XV (vicino)": "", "Tipo/direzione/recupero": ""},
    ], ["Cover test"], "pv_cover_test_pv")

    st.markdown("**8.2 Distanze, prossimali e accomodazione**")
    c50, c51, c52 = st.columns(3)
    harmon_pv = c50.text_input("HARMON (cm)", key="pv_harmon_pv")
    rrd_pv = c51.text_input("RRD (cm)", key="pv_rrd_pv")
    diff_harmon_rrd = c52.text_input("Differenza Harmon−RRD (cm)", key="pv_diff_harmon")
    c53, c54 = st.columns(2)
    ppc_rottura = c53.text_input("PPC rottura (cm)", key="pv_ppc_rottura")
    rec_recupero = c54.text_input("REC recupero (cm)", key="pv_rec_recupero")
    c55, c56, c57 = st.columns(3)
    ppa_od = c55.text_input("PPA OD (cm)", key="pv_ppa_od")
    ppa_os = c56.text_input("PPA OS (cm)", key="pv_ppa_os")
    ppa_oo = c57.text_input("PPA OO (cm)", key="pv_ppa_oo")
    flessibilita = _tabella("flessibilita", [
        {"Flessibilità": "Accomodativa ±2,00D (atteso 10 c)", "Cicli/30\"": "", "Difficoltà prevalente": ""},
        {"Flessibilità": "Fusionale 10 BI/BO (atteso 10 c)", "Cicli/30\"": "", "Difficoltà prevalente": ""},
        {"Flessibilità": "Acc./vergenza 2,5/10 (atteso 16 c)", "Cicli/30\"": "", "Difficoltà prevalente": ""},
        {"Flessibilità": "Acc./vergenza 28/10 (atteso 12 c)", "Cicli/30\"": "", "Difficoltà prevalente": ""},
    ], ["Flessibilità"], "pv_flessibilita")

    st.markdown("**8.4 Motilità oculare — scale NSUCO**")
    st.caption("Cerchiare/selezionare il livello osservato, separatamente per inseguimenti e saccadi "
               "(1-5 per Abilità, Precisione, Movimento della testa, Movimento del corpo).")
    c58, c59 = st.columns(2)
    with c58:
        st.markdown("_Inseguimenti (pursuit)_")
        nsuco_ins = _tabella("nsuco_ins", [
            {"Parametro": "Abilità (1-5)", "Valore": ""}, {"Parametro": "Precisione (1-5)", "Valore": ""},
            {"Parametro": "Movimento testa (1-5)", "Valore": ""}, {"Parametro": "Movimento corpo (1-5)", "Valore": ""},
        ], ["Parametro"], "pv_nsuco_ins")
        risultato_ins = st.text_input("Risultato inseguimenti (___/20)", key="pv_risultato_ins")
    with c59:
        st.markdown("_Saccadi_")
        nsuco_sac = _tabella("nsuco_sac", [
            {"Parametro": "Abilità (1-5)", "Valore": ""}, {"Parametro": "Precisione (1-5)", "Valore": ""},
            {"Parametro": "Movimento testa (1-5)", "Valore": ""}, {"Parametro": "Movimento corpo (1-5)", "Valore": ""},
        ], ["Parametro"], "pv_nsuco_sac")
        risultato_sac = st.text_input("Risultato saccadi (___/20)", key="pv_risultato_sac")

    st.markdown("**8.5 Saccadi in lettura e integrazione visivo-verbale**")
    dem_pv = _tabella("dem_pv", [
        {"Prova": "DEM — sottotest A", "Tempo (sec)": "", "Errori": "", "Tipo di errore": ""},
        {"Prova": "DEM — sottotest B", "Tempo (sec)": "", "Errori": "", "Tipo di errore": ""},
        {"Prova": "DEM — sottotest C (orizzontale)", "Tempo (sec)": "", "Errori": "", "Tipo di errore": ""},
    ], ["Prova"], "pv_dem_pv")
    rapporto_dem = st.text_input("Rapporto C ÷ (A+B)", key="pv_rapporto_dem")
    kd_pv = _tabella("kd_pv", [
        {"Prova": "King-Devick — I", "Tempo (sec)": "", "Errori": ""},
        {"Prova": "King-Devick — II", "Tempo (sec)": "", "Errori": ""},
        {"Prova": "King-Devick — III", "Tempo (sec)": "", "Errori": ""},
    ], ["Prova"], "pv_kd_pv")
    c60, c61 = st.columns(2)
    groffman_linee = c60.text_input("Groffman — linee corrette (___/5)", key="pv_groffman_linee")
    groffman_tempo = c61.text_input("Groffman — tempo totale (s)", key="pv_groffman_tempo")

    st.markdown("**8.6 Fusione**")
    clinical_fusion = _tabella("clinical_fusion", [
        {"Test": "Test 1", "Esito": ""}, {"Test": "Test 2", "Esito": ""},
        {"Test": "Test 3", "Esito": ""}, {"Test": "Test 4", "Esito": ""},
    ], ["Test"], "pv_clinical_fusion")
    c62, c63 = st.columns(2)
    progression_fusion_xl = c62.text_input("Progression of fusion — XL (lontano)", key="pv_prog_fus_xl")
    progression_fusion_xv = c63.text_input("Progression of fusion — XV (vicino)", key="pv_prog_fus_xv")

    st.markdown("**8.7 Dominanza oculare e uditiva**")
    st.markdown("_8.7a Dominanza oculare_")
    dominanza_oculare = _tabella("dominanza_oculare", [
        {"Test": "Foro (Miles)", "OD": "", "OS": "", "Note": ""},
        {"Test": "Puntamento (Porta)", "OD": "", "OS": "", "Note": ""},
        {"Test": "Cannocchiale", "OD": "", "OS": "", "Note": ""},
    ], ["Test"], "pv_dominanza_oculare")
    c64, c65 = st.columns(2)
    esito_dom_oculare = c64.selectbox("Esito dominanza oculare", ["", "OD", "OS", "Alternante"], key="pv_esito_dom_oc")
    coerenza_dom_oculare = c65.selectbox("Coerenza tra i tre test", ["", "Piena (3/3)", "Parziale (2/3)", "Assente"], key="pv_coerenza_dom_oc")

    st.markdown("_8.7b Dominanza uditiva_")
    st.caption("Voce da dietro: 5 prove ripetute, frase diversa ogni volta, pausa ≥15s. Dominanza netta se ≥4/5 dallo stesso lato.")
    voce_da_dietro = _tabella("voce_da_dietro", [
        {"Prova": 1, "Lato di rotazione": ""}, {"Prova": 2, "Lato di rotazione": ""},
        {"Prova": 3, "Lato di rotazione": ""}, {"Prova": 4, "Lato di rotazione": ""}, {"Prova": 5, "Lato di rotazione": ""},
    ], ["Prova"], "pv_voce_da_dietro")
    c66, c67 = st.columns(2)
    tot_dx = c66.text_input("Totale Dx (___/5)", key="pv_tot_dx")
    tot_sx = c67.text_input("Totale Sx (___/5)", key="pv_tot_sx")
    c68, c69 = st.columns(2)
    esito_dom_uditiva = c68.selectbox("Esito dominanza uditiva", ["", "Dx", "Sx", "Alternante"], key="pv_esito_dom_ud")
    coerenza_dom_uditiva = c69.selectbox("Coerenza tra le prove", ["", "Piena", "Parziale", "Assente"], key="pv_coerenza_dom_ud")

    st.markdown("_8.7c Quadro di lateralità e congruenze_")
    lateralita = _tabella("lateralita", [
        {"": "Occhio", "Dx": "", "Sx": ""}, {"": "Orecchio", "Dx": "", "Sx": ""},
        {"": "Mano", "Dx": "", "Sx": ""}, {"": "Piede", "Dx": "", "Sx": ""},
    ], [""], "pv_lateralita")
    profilo_lateralita = st.selectbox("Profilo", ["", "Omogeneo", "Crociato", "Misto"], key="pv_profilo_lateral")
    st.caption("Annotare in particolare la congruenza occhio-orecchio e orecchio-mano: pesano di più sulla "
               "lettura ad alta voce e sulla stimolazione uditiva.")

    st.markdown("**8.8 Postura e organizzazione visuo-motoria**")
    postura_ortostatismo = st.text_input("Postura in ortostatismo (asse, spalle, bacino, appoggi)", key="pv_postura_ortostatismo")
    postura_seduta = st.text_input("Postura seduta al compito (distanza, inclinazione capo, torsione)", key="pv_postura_seduta")
    fukuda_romberg = st.text_input("Test di Fukuda / Romberg", key="pv_fukuda_romberg")
    riflessi_primitivi_88 = st.multiselect("Riflessi primitivi", ["ATNR", "STNR", "Moro", "TLR", "Galant"], key="pv_riflessi_88")
    coord_occhio_mano = st.text_input("Coordinazione occhio-mano", key="pv_coord_occhio_mano")

    st.markdown("**8.9 Valutazione posturale strumentale — pedana stabilometrica**")
    c70, c71, c72 = st.columns(3)
    strumento_pedana = c70.text_input("Strumento / software", key="pv_strumento_pedana")
    freq_campionamento = c71.text_input("Frequenza campionamento (Hz)", key="pv_freq_camp")
    durata_acq = c72.selectbox("Durata acquisizione", ["", "51,2 s", "30 s", "Altro"], key="pv_durata_acq")

    st.markdown("_8.9a Prova di base — occhi aperti / occhi chiusi_")
    prova_base_pedana = _tabella("prova_base_pedana", [
        {"Parametro": "Superficie ellisse conf. 90% (mm²)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
        {"Parametro": "Lunghezza tracciato — LNG (mm)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
        {"Parametro": "LFS (mm⁻¹)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
        {"Parametro": "Velocità media oscillazione (mm/s)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
        {"Parametro": "Posizione media CoP — X (mm)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
        {"Parametro": "Posizione media CoP — Y (mm)", "Occhi aperti": "", "Occhi chiusi": "", "Quoziente OC/OA": ""},
    ], ["Parametro"], "pv_prova_base_pedana")
    st.caption("Quoziente di Romberg = superficie OC ÷ superficie OA. ~1-2,5 = contributo visivo nella norma; "
               "molto superiore = dipendenza visiva; ≤1 = sistema che non usa l'informazione visiva.")

    st.markdown("_8.9b Test di manipolazione (entrate posturali)_")
    st.caption("Variazione % = (superficie condizione − superficie base) × 100 ÷ superficie base. "
               "Significativa oltre ±30% (soglia interna).")
    manipolazione_pedana = _tabella("manip_pedana", [
        {"Entrata": "Visiva", "Condizione": "Occlusione OD", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Visiva", "Condizione": "Occlusione OS", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Visiva", "Condizione": "Con correzione ottica", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Orale", "Condizione": "Denti a contatto (serramento)", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Orale", "Condizione": "Lingua allo spot palatino", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Cervicale", "Condizione": "Capo ruotato dx/sx", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Podalica", "Condizione": "Appoggio modificato", "Superficie (mm²)": "", "Effetto": ""},
        {"Entrata": "Uditiva", "Condizione": "Occlusione di un orecchio", "Superficie (mm²)": "", "Effetto": ""},
    ], ["Entrata", "Condizione"], "pv_manip_pedana")

    st.markdown("_8.9d Lettura integrata_")
    sistema_prevalente = st.selectbox("Sistema prevalente nel controllo posturale",
        ["", "Visivo", "Podalico", "Oro-mandibolare", "Cervicale/vestibolare", "Equilibrato"], key="pv_sistema_prevalente")
    entrata_efficace = st.text_input("Entrata più efficace nel ridurre l'oscillazione", key="pv_entrata_efficace")
    coerenza_optometrica = st.text_area("Coerenza con i rilievi optometrici e miofunzionali", key="pv_coerenza_optom", height=60)

    st.markdown("**8.10 Sintesi optometrica, posturale e indicazioni**")
    sintesi_optometrica = st.radio("Indicazione", [
        "Nessun rilievo significativo", "Indicato training visuo-percettivo",
        "Indicata valutazione oftalmologica"], key="pv_sintesi_optom")
    rivalutazione_mesi = st.text_input("Rivalutazione a ___ mesi", key="pv_rivalutazione_mesi")

    st.info("📄 **PARTE 9 (Informativa privacy e consenso)**: già gestita dal modulo dedicato "
            "\"Consenso privacy\" del gestionale — non duplicata qui per evitare due copie del consenso.")

    note_generali = st.text_area("Note generali (PARTE 1-8)", key="pv_note_generali_full", height=68)

    dati = {
        "generali": {"esaminatore": esaminatore, "inviato_da": inviato_da, "motivo": motivo, "fascia": fascia},
        "anamnesi": {
            "gravidanza": gravidanza, "parto_tipo": parto_tipo, "giro_cordone": giro_cordone,
            "peso_nascita": peso_nascita, "apgar": apgar, "tin_ittero": tin_ittero,
            "periodo_neonatale": periodo_neonatale, "tappe_motorie": tappe_motorie,
            "prime_parole": prime_parole, "otiti": otiti, "familiarita": familiarita,
            "bilinguismo": bilinguismo, "patologie_note": patologie_note,
            "trattamenti_pregressi": trattamenti_pregressi,
            "valutazione_visiva_pregressa": valutazione_visiva_pregressa, "hobby": hobby,
        },
        "parte1_bilancio_fonetico": {
            "per_fono": bilancio_fonetico, "gruppi_consonantici": gruppi.to_dict("records"),
            "dittonghi_note": dittonghi_note, "polisillabi": polisillabi.to_dict("records"),
            "logatomi_note": logatomi_note, "inventario": inventario.to_dict("records"),
            "semplificazioni_sistema": semp_sistema.to_dict("records"),
            "semplificazioni_struttura": semp_struttura.to_dict("records"),
            "indici": indici_fonetici.to_dict("records"),
        },
        "parte2_linguaggio": {
            "errori_denominazione": errori_denominazione.to_dict("records"),
            "corretti_spontanei": corretti_spontanei, "corretti_facilitazione": corretti_facilitazione,
            "latenza_media": latenza_media, "corretti_compr_lex": corretti_compr_lex,
            "errori_prevalenti": errori_prevalenti, "fluenza_verbale": fluenza_verbale.to_dict("records"),
            "relazioni_semantiche": relazioni_semantiche.to_dict("records"),
            "ripetizione_frasi": ripetizione_frasi.to_dict("records"), "totale_ripet_frasi": totale_ripet_frasi,
            "aree_errore": aree_errore, "comprensione_frasi": comprensione_frasi.to_dict("records"),
            "totale_compr_frasi": totale_compr_frasi, "morfologia": morfologia.to_dict("records"),
            "narrativa_macro": narrativa_macro.to_dict("records"), "totale_narrativa": totale_narrativa,
            "n_enunciati": n_enunciati, "lme": lme, "enunciati_completi": enunciati_completi,
            "n_subordinate": n_subordinate, "errori_morfosint": errori_morfosint, "type_token": type_token,
            "trascrizione_narrativa": trascrizione_narrativa,
        },
        "note_generali": note_generali,
        "parte3_fluenza": {
            "familiarita": familiarita_fluenza, "epoca_insorgenza": epoca_insorgenza,
            "evento_esordio": evento_esordio, "andamento": andamento, "tempo_esordio": tempo_esordio,
            "consapevolezza": consapevolezza, "reazione_ambiente": reazione_ambiente,
            "trattamenti": trattamenti_fluenza, "campionamento": campionamento.to_dict("records"),
            "sld": sld.to_dict("records"), "totale_sld": totale_sld,
            "od": od.to_dict("records"), "totale_od": totale_od,
            "n_medio_iterazioni": n_medio_iterazioni, "durata_blocchi": durata_blocchi,
            "gravita": gravita.to_dict("records"), "totale_gravita": totale_gravita,
            "concomitanti": concomitanti, "velocita_globale": velocita_globale,
            "velocita_articolatoria": velocita_articolatoria, "velocita_lettura": velocita_lettura,
            "rapporto_lettura_eloquio": rapporto_lettura_eloquio,
            "indicatori_cluttering": indicatori_cluttering, "vissuto_emotivo": vissuto_emotivo,
            "evitamento": evitamento, "impatto_funzionale": impatto_funzionale,
            "postura_tono": postura_tono, "pattern_respiratorio": pattern_respiratorio,
            "profilo_uditivo": profilo_uditivo, "profilo_visivo": profilo_visivo,
            "riflessi_rilevati": riflessi_rilevati,
        },
        "parte4_apprendimento": {
            "lettura_parole": lettura_parole.to_dict("records"),
            "lettura_nonparole": lettura_nonparole.to_dict("records"),
            "indice_discrepanza": indice_discrepanza, "tavole_irest": tavole_irest.to_dict("records"),
            "esiti_irest": esiti_irest.to_dict("records"), "compr_irest": compr_irest.to_dict("records"),
            "oss_lettura": oss_lettura, "dettato_parole": dettato_parole.to_dict("records"),
            "dettato_esiti": dettato_esiti, "omofone": omofone.to_dict("records"),
            "griglia_errori": griglia_errori.to_dict("records"), "tempo_dettato": tempo_dettato,
            "parole_min_scrittura": parole_min_scrittura, "profilo_prevalente": profilo_prevalente,
            "grafia_automatismo": grafia_automatismo.to_dict("records"),
            "indici_derivati": indici_derivati.to_dict("records"),
            "grafia_qualitativa": grafia_qualit.to_dict("records"),
            "totale_grafia_qualit": totale_grafia_qualit, "presa_strumento": presa_strumento,
            "postura_grafia": postura_grafia, "enumerazione": enumerazione_tab.to_dict("records"),
            "transcodifica": transcodifica.to_dict("records"), "fatti_aritmetici": fatti_aritmetici.to_dict("records"),
            "recupero_diretto": recupero_diretto, "calcolo_mente": calcolo_mente.to_dict("records"),
            "calcolo_scritto": calcolo_scritto_tab.to_dict("records"), "problemi": problemi_tab.to_dict("records"),
        },
        "parte5_sintesi": {
            "profilo": sintesi_profilo.to_dict("records"), "oss_visione": oss_visione,
            "oss_ascolto": oss_ascolto, "oss_riflessi": oss_riflessi, "oss_postura": oss_postura,
            "ipotesi_lavoro": ipotesi_lavoro, "data_restituzione": data_restituzione,
            "proposta_intervento": proposta_intervento, "rivalutazione_prevista": rivalutazione_prevista,
        },
        "parte6_miofunzionale": {
            "anamnesi": mio_anamnesi_tab.to_dict("records"), "meccanismo_respiratorio": mecc_respiratorio,
            "orl_pregresse": orl_pregresse, "abitudini_viziate": abitudini_viziate,
            "masticazione": masticazione, "masticazione_rumorosa": masticazione_rumorosa,
            "postura_orale_riposo": postura_orale_riposo, "postura_linguale": postura_linguale_pv,
            "frenulo_linguale": frenulo_linguale, "frenulo_labiale": frenulo_labiale, "palato": palato,
            "prassie": prassie.to_dict("records"), "deglutizione": deglutizione_pv,
            "tono_simmetria": tono_simmetria, "atm": atm, "apertura_max": apertura_max,
            "sintesi": sintesi_miofunzionale,
        },
        "parte7_osteopatica": {
            "hobby": hobby_osteo, "gravidanza": osteo_gravidanza, "crescita": osteo_crescita,
            "allattamento": osteo_allattamento, "sonno": osteo_sonno, "patologie": osteo_patologie,
            "traumi": osteo_traumi, "test_osteopatici": test_osteopatici.to_dict("records"),
            "sintesi": sintesi_osteopatica, "indicazioni": indicazioni_osteo,
        },
        "parte8_visuo_posturale": {
            "acuita_visiva": acuita_visiva.to_dict("records"), "correzione_in_uso": correzione_in_uso,
            "cover_test": cover_test_pv.to_dict("records"), "harmon": harmon_pv, "rrd": rrd_pv,
            "diff_harmon_rrd": diff_harmon_rrd, "ppc_rottura": ppc_rottura, "rec_recupero": rec_recupero,
            "ppa_od": ppa_od, "ppa_os": ppa_os, "ppa_oo": ppa_oo,
            "flessibilita": flessibilita.to_dict("records"),
            "nsuco_inseguimenti": nsuco_ins.to_dict("records"), "risultato_inseguimenti": risultato_ins,
            "nsuco_saccadi": nsuco_sac.to_dict("records"), "risultato_saccadi": risultato_sac,
            "dem": dem_pv.to_dict("records"), "rapporto_dem": rapporto_dem, "kd": kd_pv.to_dict("records"),
            "groffman_linee": groffman_linee, "groffman_tempo": groffman_tempo,
            "clinical_fusion": clinical_fusion.to_dict("records"),
            "progression_fusion_xl": progression_fusion_xl, "progression_fusion_xv": progression_fusion_xv,
            "dominanza_oculare": dominanza_oculare.to_dict("records"), "esito_dom_oculare": esito_dom_oculare,
            "coerenza_dom_oculare": coerenza_dom_oculare, "voce_da_dietro": voce_da_dietro.to_dict("records"),
            "tot_dx": tot_dx, "tot_sx": tot_sx, "esito_dom_uditiva": esito_dom_uditiva,
            "coerenza_dom_uditiva": coerenza_dom_uditiva, "lateralita": lateralita.to_dict("records"),
            "profilo_lateralita": profilo_lateralita, "postura_ortostatismo": postura_ortostatismo,
            "postura_seduta": postura_seduta, "fukuda_romberg": fukuda_romberg,
            "riflessi_primitivi": riflessi_primitivi_88, "coord_occhio_mano": coord_occhio_mano,
            "strumento_pedana": strumento_pedana, "freq_campionamento": freq_campionamento,
            "durata_acquisizione": durata_acq, "prova_base_pedana": prova_base_pedana.to_dict("records"),
            "manipolazione_pedana": manipolazione_pedana.to_dict("records"),
            "sistema_prevalente": sistema_prevalente, "entrata_efficace": entrata_efficace,
            "coerenza_optometrica": coerenza_optometrica, "sintesi_optometrica": sintesi_optometrica,
            "rivalutazione_mesi": rivalutazione_mesi,
        },
    }

    if st.button("💾 Salva protocollo completo (PARTE 1-8)", type="primary", key="pv_salva"):
        if _salva(conn, paz_id, esaminatore, dati):
            st.success("Salvato. Protocollo completo — PARTE 1-8 (PARTE 9 gestita dal modulo Consenso privacy).")
