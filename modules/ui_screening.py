# -*- coding: utf-8 -*-
"""Screening rapido multi-area — per eventi/scuola (tipo "Giornata del
benessere del bambino"), separato dalla Valutazione PNEV completa.

Raccoglie in una scheda breve i test-chiave di linguaggio, apprendimento,
visuo-posturale, miofunzionale e osteopatico — pensata per una prima
rilevazione veloce, non per il percorso clinico completo del paziente.
"""
from __future__ import annotations
import datetime
import json
import streamlit as st


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


def render_screening(conn=None, paz_id=None, paziente=None) -> None:
    st.header("🩺 Screening rapido")
    st.caption("Scheda breve multi-area per una prima rilevazione — evento, scuola, "
               "\"Giornata del benessere\". Per il percorso clinico completo usa "
               "Valutazione PNEV.")

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
        livello_lex = st.text_area("Livello lessicale-semantico", key="scr_ling_lex", height=60)
        livello_morfo = st.text_area("Livello morfosintattico e narrativo", key="scr_ling_morfo", height=60)
        st.markdown("**Disturbi della fluenza**")
        balbuzie = st.text_input("Balbuzie (familiarità, epoca insorgenza)", key="scr_ling_balbuzie")
        tachilalia = st.text_input("Tachilalia / cluttering", key="scr_ling_tachilalia")
        extra_verbale = st.text_input("Sintomatologia extra-verbale", key="scr_ling_extra")

    with t_appr:
        st.markdown("**Lettura — velocità e correttezza (numero errori)**")
        c1, c2, c3 = st.columns(3)
        lett_parole = c1.text_input("Parole", key="scr_appr_lett_parole")
        lett_nonparole = c2.text_input("Non parole", key="scr_appr_lett_nonparole")
        lett_brano = c3.text_input("Brano", key="scr_appr_lett_brano")
        st.markdown("**Scrittura (errori)**")
        c4, c5, c6 = st.columns(3)
        scr_parole = c4.text_input("Parole", key="scr_appr_scr_parole")
        scr_nonparole = c5.text_input("Non parole", key="scr_appr_scr_nonparole")
        scr_omofone = c6.text_input("Omofone non omografe", key="scr_appr_scr_omofone")
        grafia = st.text_area("Grafia", key="scr_appr_grafia", height=50)
        st.markdown("**Calcolo**")
        calc_scritto = st.text_area("Calcolo scritto e a mente", key="scr_appr_calc_scritto", height=50)
        enumerazione = st.text_input("Enumerazione", key="scr_appr_enum")
        fatti_proc = st.text_input("Fatti e procedure", key="scr_appr_fatti")

    with t_vp:
        st.markdown("**Cover Test / Telebinocular**")
        c1, c2 = st.columns(2)
        ct_lontano = c1.text_input("Cover test lontano (XL)", key="scr_vp_ct_l")
        ct_vicino = c2.text_input("Cover test vicino (XV)", key="scr_vp_ct_v")
        c3, c4 = st.columns(2)
        harmon = c3.text_input("Harmon (cm)", key="scr_vp_harmon")
        rrd = c4.text_input("RRD (cm)", key="scr_vp_rrd")
        c5, c6 = st.columns(2)
        ppc = c5.text_input("PPC (rottura/recupero)", key="scr_vp_ppc")
        ppa = c6.text_input("PPA OD/OS", key="scr_vp_ppa")
        st.markdown("**NSUCO — Pursuit / Saccadi**")
        c7, c8 = st.columns(2)
        nsuco_pursuit = c7.selectbox("Pursuit (abilità 1-5)", ["", 1, 2, 3, 4, 5], key="scr_vp_nsuco_p")
        nsuco_saccadi = c8.selectbox("Saccadi (abilità 1-5)", ["", 1, 2, 3, 4, 5], key="scr_vp_nsuco_s")
        st.markdown("**DEM / K-D Test / Clinical Fusion**")
        c9, c10, c11 = st.columns(3)
        dem = c9.text_input("DEM (A/B/C, sec, err)", key="scr_vp_dem")
        kd = c10.text_input("K-D Test (I/II/III, sec, err)", key="scr_vp_kd")
        cft = c11.text_input("Clinical Fusion Test", key="scr_vp_cft")

    with t_mio:
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
        st.markdown("**Valutazione**")
        postura_orale = st.text_input("Postura orale a riposo", key="scr_mio_postura_orale")
        postura_linguale = st.text_input("Postura linguale", key="scr_mio_postura_ling")
        deglutizione = st.text_input("Deglutizione", key="scr_mio_deglut")
        respirazione = st.selectbox("Meccanismo respiratorio", ["", "Nasale", "Orale", "Misto"],
                                     key="scr_mio_respiro")

    with t_osteo:
        st.markdown("**Anamnesi**")
        gravidanza = st.text_area("Gravidanza / parto", key="scr_osteo_grav", height=50)
        crescita = st.text_input("Crescita e sviluppo (peso, tappe motorie)", key="scr_osteo_crescita")
        patologie = st.text_input("Patologie note / visite specialistiche", key="scr_osteo_patologie")
        st.markdown("**Indicazioni**")
        indicazione = st.radio("Esito", [
            "Nessuna restrizione significativa", "Possibile beneficio da trattamento osteopatico",
            "Suggerita valutazione pediatrica / specialistica"], key="scr_osteo_indic")

    note = st.text_area("Note generali", key="scr_note", height=70)

    if st.button("💾 Salva screening", type="primary", key="scr_salva"):
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
        if _salva(conn, paz_id, operatore, sezioni, note):
            st.success("Screening salvato.")
            st.rerun()

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
