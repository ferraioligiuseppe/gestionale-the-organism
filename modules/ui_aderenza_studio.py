# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  ADERENZA DELLO STUDIO — una lista sola, la peggiore in cima         ║
║                                                                      ║
║  L'aderenza al lavoro a casa si calcolava gia', ma si guardava un    ║
║  paziente per volta: per sapere chi sta mollando bisognava aprire    ║
║  trenta schede. Cosi' non lo si sa, e il momento in cui intervenire  ║
║  passa.                                                              ║
║                                                                      ║
║  Qui la domanda e' rovesciata: non «come va Martina» ma «di chi mi   ║
║  devo occupare oggi». Due cose diverse, tenute separate perche'      ║
║  chiedono risposte diverse:                                          ║
║                                                                      ║
║    • ADERENZA BASSA — la famiglia segna, ma fa poco. Si sa cosa      ║
║      non funziona e su cosa intervenire.                             ║
║    • SILENZIO — non segna piu' niente da giorni. Non sai se hanno    ║
║      smesso di fare gli esercizi o solo di registrarli, e queste     ║
║      due cose si risolvono in modi opposti.                          ║
║                                                                      ║
║  Nessuna tabella nuova: legge programma_casa_feedback e              ║
║  programma_casa, quelle che il portale famiglia riempie gia'.        ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import datetime

import streamlit as st

SOGLIA_DEFAULT = 70
FINESTRA_DEFAULT = 30
SILENZIO_DEFAULT = 7


# ══════════════════════════════════════════════════════════════════════
#  Letture
# ══════════════════════════════════════════════════════════════════════

def _tabella_esiste(conn, nome) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (nome,))
        row = cur.fetchone()
        return bool(row[0]) if row else False
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _riepilogo(conn, finestra_giorni: int):
    """Una riga per paziente seguito a casa: aderenza nella finestra,
    aderenza della settimana corrente e di quella precedente (per il
    verso in cui sta andando), ultimo segno di vita."""
    oggi = datetime.date.today()
    da_finestra = oggi - datetime.timedelta(days=finestra_giorni)
    da_7 = oggi - datetime.timedelta(days=7)
    da_14 = oggi - datetime.timedelta(days=14)

    # Chi ha davvero del lavoro a casa assegnato. Se programma_casa non
    # esiste ancora (nessun invio mai fatto), si ripiega su chi ha almeno
    # un feedback: meglio una lista parziale che una schermata vuota.
    if _tabella_esiste(conn, "programma_casa"):
        sorgente = ("SELECT DISTINCT paziente_id FROM programma_casa "
                    "WHERE tipo='casa' AND inviato = TRUE")
    else:
        sorgente = "SELECT DISTINCT paziente_id FROM programma_casa_feedback"

    sql = f"""
        WITH seguiti AS ({sorgente})
        SELECT p.id, p.cognome, p.nome, p.data_nascita,
               COUNT(*) FILTER (WHERE f.fatto)                          AS fatti,
               COUNT(f.id)                                              AS totali,
               AVG(f.valutazione)                                       AS media,
               MAX(f.data)                                              AS ultimo,
               COUNT(*) FILTER (WHERE f.fatto AND f.data >= %s)         AS fatti7,
               COUNT(*) FILTER (WHERE f.data >= %s)                     AS tot7,
               COUNT(*) FILTER (WHERE f.fatto AND f.data >= %s AND f.data < %s) AS fatti14,
               COUNT(*) FILTER (WHERE f.data >= %s AND f.data < %s)     AS tot14
        FROM pazienti p
        JOIN seguiti s ON s.paziente_id = p.id
        LEFT JOIN programma_casa_feedback f
               ON f.paziente_id = p.id AND f.data >= %s
        WHERE COALESCE(p.stato_paziente, 'ATTIVO') = 'ATTIVO'
        GROUP BY p.id, p.cognome, p.nome, p.data_nascita
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (da_7, da_7, da_14, da_7, da_14, da_7, da_finestra))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None

    out = []
    for r in righe:
        (pid, cog, nom, dn, fatti, totali, media, ultimo,
         fatti7, tot7, fatti14, tot14) = r
        pct = round(100 * fatti / totali) if totali else None
        pct7 = round(100 * fatti7 / tot7) if tot7 else None
        pct14 = round(100 * fatti14 / tot14) if tot14 else None
        silenzio = (oggi - ultimo).days if ultimo else None
        out.append({
            "id": pid,
            "nome": f"{(cog or '').strip()} {(nom or '').strip()}".strip() or f"ID {pid}",
            "pct": pct, "fatti": fatti or 0, "totali": totali or 0,
            "media": round(media, 1) if media else None,
            "ultimo": ultimo, "silenzio": silenzio,
            "pct7": pct7, "pct14": pct14,
            "delta": (pct7 - pct14) if (pct7 is not None and pct14 is not None) else None,
        })
    return out


def _procedure_deboli(conn, paz_id, giorni=21, soglia_frazione=0.34):
    """Le procedure che questo paziente sta saltando, con quante volte su
    quante. Serve a capire se il problema e' la famiglia o l'esercizio."""
    try:
        cur = conn.cursor()
        da = datetime.date.today() - datetime.timedelta(days=giorni)
        cur.execute("""SELECT procedura,
                COUNT(*) FILTER (WHERE fatto) AS fatti, COUNT(*) AS totali
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data >= %s
            GROUP BY procedura ORDER BY procedura""", (paz_id, da))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return [], []
    deboli, tengono = [], []
    for proc, fatti, totali in righe:
        if not totali:
            continue
        voce = (proc, fatti or 0, totali)
        (deboli if (fatti or 0) / totali < soglia_frazione else tengono).append(voce)
    return deboli, tengono


def _nome_pulito(proc: str) -> str:
    import re
    p = re.sub(r"^\[[^\]]*\]\s*", "", (proc or "").strip())
    p = re.sub(r"^S\d+\s*·\s*", "", p)
    p = re.sub(r"\s*\([^)]*\)\s*$", "", p)
    return p.strip() or proc


# ══════════════════════════════════════════════════════════════════════
#  Azioni
# ══════════════════════════════════════════════════════════════════════

def _apri_piano(conn, paz_id):
    """Rende attivo quel paziente e salta al suo piano di trattamento."""
    try:
        from .paziente_attivo import set_paziente_attivo
        set_paziente_attivo(conn, int(paz_id))
    except Exception:
        st.session_state["paziente_attivo_id"] = int(paz_id)
    try:
        from .app_menu import AREA_TERAPIA_PNEV
        st.session_state["goto_area"] = AREA_TERAPIA_PNEV
    except Exception:
        pass
    st.session_state["goto_sotto"] = "🎯 Piano di trattamento"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  Schermata
# ══════════════════════════════════════════════════════════════════════

def render_aderenza_studio(conn=None, is_admin: bool = False) -> None:
    st.header("📊 Aderenza dello studio")
    st.caption("Di chi mi devo occupare oggi. Tutti i pazienti seguiti a casa, "
               "dal peggiore. Nessun paziente da selezionare: questa è la vista d'insieme.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    if not _tabella_esiste(conn, "programma_casa_feedback"):
        st.info("Il portale famiglia non ha ancora registrato nessun feedback. "
                "Questa schermata si popola da sola appena le famiglie iniziano "
                "a segnare cosa hanno fatto.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        soglia = st.number_input("Soglia di aderenza (%)", 0, 100, SOGLIA_DEFAULT, 5,
                                 key="ad_soglia")
    with c2:
        finestra = st.number_input("Finestra (giorni)", 7, 180, FINESTRA_DEFAULT, 1,
                                   key="ad_finestra")
    with c3:
        giorni_silenzio = st.number_input("Silenzio dopo (giorni)", 2, 60, SILENZIO_DEFAULT, 1,
                                          key="ad_silenzio")

    dati = _riepilogo(conn, int(finestra))
    if dati is None:
        st.error("Non riesco a leggere i dati di aderenza. Se è la prima volta che "
                 "apri questa schermata, assegna prima delle procedure di casa da "
                 "«🧘 Percorsi terapeutici → Diario sedute → Invia su pnev.it».")
        return
    if not dati:
        st.info("Nessun paziente con lavoro a casa assegnato.")
        return

    # Chi non segna piu' niente e' un problema diverso da chi segna poco:
    # tenerli nella stessa lista li confonde.
    muti = [d for d in dati if d["silenzio"] is None or d["silenzio"] >= giorni_silenzio]
    parlanti = [d for d in dati if d not in muti]
    sotto = sorted([d for d in parlanti if d["pct"] is not None and d["pct"] < soglia],
                   key=lambda d: d["pct"])
    ok = sorted([d for d in parlanti if d["pct"] is not None and d["pct"] >= soglia],
                key=lambda d: -d["pct"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Pazienti seguiti a casa", len(dati))
    m2.metric("Sotto soglia", len(sotto),
              f"su {len(parlanti)} che registrano" if parlanti else None,
              delta_color="off")
    m3.metric("In silenzio", len(muti),
              f"da {giorni_silenzio}+ giorni" if muti else None,
              delta_color="inverse" if muti else "off")

    st.divider()

    if muti:
        st.markdown("#### 🔇 In silenzio")
        st.caption("Nessun feedback da giorni. Non sai se hanno smesso di fare gli "
                   "esercizi o solo di registrarli: è la prima cosa da chiedere.")
        for d in sorted(muti, key=lambda x: -(x["silenzio"] or 9999)):
            c1, c2 = st.columns([5, 1])
            if d["silenzio"] is None:
                testo = "mai nessun feedback"
            else:
                testo = f"ultimo segno {d['silenzio']} giorni fa ({d['ultimo']:%d/%m/%Y})"
            c1.markdown(f"**{d['nome']}** — {testo}")
            if c2.button("Apri il piano", key=f"ad_mut_{d['id']}", use_container_width=True):
                _apri_piano(conn, d["id"])
        st.divider()

    if sotto:
        st.markdown(f"#### ⚠️ Sotto il {soglia}%")
        st.caption("Registrano, ma fanno poco. Qui si vede su cosa intervenire.")
        for d in sotto:
            freccia = ""
            if d["delta"] is not None:
                if d["delta"] <= -10:
                    freccia = f" · in calo ({d['delta']:+d} punti sull'ultima settimana)"
                elif d["delta"] >= 10:
                    freccia = f" · in ripresa ({d['delta']:+d} punti)"
            titolo = (f"{d['nome']} — {d['pct']}%  ·  {d['fatti']}/{d['totali']} "
                      f"in {finestra} giorni{freccia}")
            with st.expander(titolo):
                deboli, tengono = _procedure_deboli(conn, d["id"])
                if deboli:
                    st.markdown("**Procedure ferme**")
                    for proc, fatti, totali in deboli:
                        st.markdown(f"- {_nome_pulito(proc)} — {fatti} su {totali}")
                if tengono:
                    st.markdown("**Procedure che reggono**")
                    for proc, fatti, totali in tengono:
                        st.caption(f"{_nome_pulito(proc)} — {fatti} su {totali}")
                if deboli and tengono:
                    st.info("Alcune procedure reggono e altre no: più che la "
                            "collaborazione della famiglia, conviene guardare se "
                            "sono quelle ferme a non funzionare.")
                elif deboli and not tengono:
                    st.warning("Nessuna procedura regge: qui il problema è "
                               "probabilmente il carico complessivo, non il "
                               "singolo esercizio. Vale la pena ridurre.")
                if d["media"]:
                    st.caption(f"Voto medio del genitore: {d['media']}/5")
                if st.button("Apri il piano di trattamento",
                             key=f"ad_sotto_{d['id']}", type="primary"):
                    _apri_piano(conn, d["id"])
        st.divider()

    if ok:
        st.markdown(f"#### ✅ Sopra il {soglia}%")
        try:
            import pandas as pd
            st.dataframe(pd.DataFrame([{
                "Paziente": d["nome"],
                "Aderenza": f"{d['pct']}%",
                "Fatte": f"{d['fatti']}/{d['totali']}",
                "Voto genitore": f"{d['media']}/5" if d["media"] else "—",
                "Ultimo feedback": d["ultimo"].strftime("%d/%m/%Y") if d["ultimo"] else "—",
            } for d in ok]), hide_index=True, use_container_width=True)
        except Exception:
            for d in ok:
                st.caption(f"{d['nome']} — {d['pct']}% ({d['fatti']}/{d['totali']})")

    st.divider()
    st.caption("Promemoria automatici: Streamlit non esegue nulla se nessuno apre "
               "l'app, quindi le mail non possono partire da qui. Servono o un "
               "controllo al primo accesso della giornata, o un cron esterno "
               "(GitHub Actions / cron-job.org). Da decidere.")
