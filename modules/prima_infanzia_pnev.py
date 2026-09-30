# -*- coding: utf-8 -*-
"""Valutazione PNEV — prima infanzia (0;0–2;11).

Fascia «0» del Protocollo di valutazione. Sotto i 3 anni non si somministrano
prove di linguaggio strutturato, fluenza o apprendimento: si osservano i
fondamenti su cui quelle funzioni si costruiranno — riflessi, tono e
motricità, visione, udito e comunicazione, regolazione, gioco e relazione.

Ogni voce ha un'età di riferimento: il modulo segnala una voce solo quando
l'età del bambino l'ha superata (un Moro presente a 2 mesi è fisiologico,
a 8 mesi no). Le età sono criteri clinici di riferimento, non norme tarate:
si modificano nelle tabelle qui sotto.

Primo nucleo della valutazione PNEV per la prima infanzia: da arricchire.
"""
from __future__ import annotations

import datetime

import streamlit as st

# Riflessi primitivi: (chiave, nome, età in mesi entro cui dovrebbe integrarsi)
PRIMITIVI = [
    ("moro", "Moro", 6),
    ("rooting", "Ricerca (rooting) e suzione", 4),
    ("palmare", "Prensione palmare", 6),
    ("plantare", "Prensione plantare", 12),
    ("atnr", "ATNR — tonico asimmetrico del collo", 6),
    ("tlr", "TLR — tonico labirintico", 4),
    ("stnr", "STNR — tonico simmetrico del collo", 11),
    ("galant", "Galant spinale", 9),
    ("babinski", "Babinski", 24),
]
# Reazioni posturali: (chiave, nome, età in mesi entro cui dovrebbe comparire)
POSTURALI = [
    ("landau", "Landau", 6),
    ("raddr", "Raddrizzamento del capo", 6),
    ("parac_ant", "Paracadute anteriore", 9),
    ("parac_lat", "Paracadute laterale", 10),
]
OPZ_RIFL = ["", "assente", "presente", "esagerato", "asimmetrico", "non valutato"]

# Tappe: (chiave, nome, età in mesi oltre cui l'assenza è un segnale)
TAPPE_MOTORIE = [
    ("capo", "Controllo del capo", 4),
    ("prono", "Da prono si appoggia sugli avambracci", 4),
    ("rotola", "Rotola", 7),
    ("seduto", "Sta seduto senza appoggio", 9),
    ("striscia", "Striscia o gattona", 11),
    ("in_piedi", "Sta in piedi con appoggio", 12),
    ("cammina", "Cammina da solo", 18),
    ("corre", "Corre, sale un gradino con appoggio", 24),
]
TAPPE_COM = [
    ("sorriso", "Sorriso sociale", 3),
    ("orienta", "Si gira verso un suono", 6),
    ("lalla", "Lallazione (ba-ba, da-da)", 10),
    ("nome", "Risponde al proprio nome", 12),
    ("indica", "Indica per chiedere o mostrare", 12),
    ("gesti", "Fa ciao, batte le mani, imita gesti", 12),
    ("parole", "Almeno 3–5 parole", 18),
    ("capisce", "Esegue un ordine semplice senza gesti", 18),
    ("att_cond", "Attenzione condivisa (guarda dove indichi)", 18),
    ("frasi", "Frasi di due parole", 24),
    ("finta", "Gioco del «far finta»", 24),
]
OPZ_TAPPA = ["", "acquisita", "emergente", "non ancora", "non valutata"]


def _eta_mesi(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT data_nascita FROM pazienti WHERE id=%s", (int(paz_id),))
        r = cur.fetchone()
        dn = (r.get("data_nascita") if isinstance(r, dict) else r[0]) if r else None
        if isinstance(dn, str):
            dn = datetime.date.fromisoformat(dn[:10])
        if dn:
            o = datetime.date.today()
            return max(0, (o.year - dn.year) * 12 + (o.month - dn.month) - (1 if o.day < dn.day else 0))
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    return None


def _scelta(label, opzioni, key):
    return st.selectbox(label, opzioni, key=key) or ""


def render_prima_infanzia(conn, paz_id) -> dict:
    """Disegna la valutazione 0;0–2;11 e restituisce i dati raccolti."""
    px = f"pv0_{paz_id}"
    st.markdown("## PRIMA INFANZIA — SVILUPPO NEUROEVOLUTIVO (0;0–2;11)")
    st.caption("Osservazione e domande ai genitori. Una voce viene segnalata solo quando l'età del "
               "bambino supera l'età di riferimento indicata tra parentesi.")

    m0 = _eta_mesi(conn, paz_id)
    c1, c2 = st.columns([1, 3])
    mesi = c1.number_input("Età (mesi)", 0, 47, value=min(m0, 47) if m0 is not None else 0,
                           key=f"{px}_mesi", help="Calcolata dalla data di nascita; correggi se serve "
                           "(per i nati pretermine usa l'età corretta fino ai 24 mesi).")
    c2.caption(f"Età dalla scheda paziente: {m0} mesi." if m0 is not None else
               "Data di nascita non disponibile: inserisci l'età a mano.")
    dati: dict = {"eta_mesi": mesi}
    segnali: list[str] = []

    st.markdown("### 1 · Riflessi primitivi")
    cols = st.columns(3)
    for i, (k, nome, lim) in enumerate(PRIMITIVI):
        v = cols[i % 3].selectbox(f"{nome} (entro {lim} m)", OPZ_RIFL, key=f"{px}_r_{k}")
        dati[f"riflesso_{k}"] = v
        if v == "asimmetrico" or (v in ("presente", "esagerato") and mesi > lim):
            segnali.append(f"{nome} {v} a {mesi} mesi")

    st.markdown("### 2 · Reazioni posturali")
    cols = st.columns(4)
    for i, (k, nome, lim) in enumerate(POSTURALI):
        v = cols[i % 4].selectbox(f"{nome} (da {lim} m)", OPZ_RIFL, key=f"{px}_p_{k}")
        dati[f"postura_{k}"] = v
        if v == "asimmetrico" or (v == "assente" and mesi >= lim):
            segnali.append(f"{nome} {v} a {mesi} mesi")

    st.markdown("### 3 · Tono e motricità")
    c = st.columns(3)
    tono = c[0].selectbox("Tono", ["", "normale", "ipotonico", "ipertonico", "misto", "asimmetrico"], key=f"{px}_tono")
    simm = c[1].selectbox("Simmetria dei movimenti", ["", "simmetrici", "preferenza di un lato", "asimmetria marcata"], key=f"{px}_simm")
    qual = c[2].selectbox("Qualità del movimento", ["", "fluido e vario", "povero o ripetitivo", "a scatti", "rigido"], key=f"{px}_qual")
    dati.update(tono=tono, simmetria=simm, qualita_movimento=qual)
    if tono and tono != "normale":
        segnali.append(f"tono {tono}")
    if simm == "asimmetria marcata" or (simm == "preferenza di un lato" and mesi < 12):
        segnali.append(f"movimenti: {simm}")
    if qual in ("povero o ripetitivo", "rigido"):
        segnali.append(f"qualità del movimento: {qual}")
    cols = st.columns(4)
    for i, (k, nome, lim) in enumerate(TAPPE_MOTORIE):
        v = cols[i % 4].selectbox(f"{nome} (entro {lim} m)", OPZ_TAPPA, key=f"{px}_m_{k}")
        dati[f"tappa_{k}"] = v
        if v == "non ancora" and mesi > lim:
            segnali.append(f"{nome.lower()}: non ancora a {mesi} mesi")
    c = st.columns(3)
    gatt = c[0].selectbox("Schema del gattonamento", ["", "crociato", "omolaterale", "strisciamento", "a sedere (shuffling)", "saltato"], key=f"{px}_gatt")
    punte = c[1].selectbox("Cammina sulle punte", ["", "no", "a volte", "spesso"], key=f"{px}_punte")
    cadute = c[2].selectbox("Cadute", ["", "nella norma", "frequenti"], key=f"{px}_cadute")
    dati.update(gattonamento=gatt, punte=punte, cadute=cadute)
    if gatt in ("omolaterale", "saltato"):
        segnali.append(f"gattonamento {gatt}")
    if punte == "spesso" and mesi >= 24:
        segnali.append("cammino frequente sulle punte")

    st.markdown("### 4 · Visione")
    c = st.columns(4)
    vis = {
        "aggancio": c[0].selectbox("Aggancio visivo", ["", "presente", "incerto", "assente"], key=f"{px}_v_agg"),
        "insegue_oriz": c[1].selectbox("Inseguimento orizzontale", ["", "fluido", "a scatti", "non segue"], key=f"{px}_v_io"),
        "insegue_vert": c[2].selectbox("Inseguimento verticale", ["", "fluido", "a scatti", "non segue"], key=f"{px}_v_iv"),
        "convergenza": c[3].selectbox("Convergenza su un oggetto", ["", "presente", "parziale", "assente"], key=f"{px}_v_conv"),
    }
    c = st.columns(4)
    vis.update({
        "cover": c[0].selectbox("Cover test", ["", "nessun movimento", "rifissazione", "non collabora"], key=f"{px}_v_cov"),
        "deviazione": c[1].selectbox("Deviazione di un occhio", ["", "no", "intermittente", "costante"], key=f"{px}_v_dev"),
        "riflessi_corneali": c[2].selectbox("Riflessi corneali (Hirschberg)", ["", "simmetrici", "asimmetrici"], key=f"{px}_v_hir"),
        "fotofobia": c[3].selectbox("Fastidio per la luce", ["", "no", "sì"], key=f"{px}_v_foto"),
    })
    dati.update({f"visione_{k}": v for k, v in vis.items()})
    if vis["aggancio"] == "assente" or (vis["aggancio"] == "incerto" and mesi >= 3):
        segnali.append(f"aggancio visivo {vis['aggancio']}")
    for k in ("insegue_oriz", "insegue_vert"):
        if vis[k] == "non segue" and mesi >= 3:
            segnali.append(f"{k.replace('_', ' ').replace('oriz', 'orizzontale').replace('vert', 'verticale')}: non segue")
    if vis["convergenza"] == "assente" and mesi >= 6:
        segnali.append("convergenza assente")
    if vis["cover"] == "rifissazione" or vis["deviazione"] in ("intermittente", "costante") and (vis["deviazione"] == "costante" or mesi >= 6):
        segnali.append("possibile strabismo: visita ortottica")
    if vis["riflessi_corneali"] == "asimmetrici":
        segnali.append("riflessi corneali asimmetrici")

    st.markdown("### 5 · Udito, comunicazione e relazione")
    cols = st.columns(4)
    for i, (k, nome, lim) in enumerate(TAPPE_COM):
        v = cols[i % 4].selectbox(f"{nome} (entro {lim} m)", OPZ_TAPPA, key=f"{px}_c_{k}")
        dati[f"com_{k}"] = v
        if v == "non ancora" and mesi > lim:
            segnali.append(f"{nome.lower()}: non ancora a {mesi} mesi")
    c = st.columns(3)
    occhi = c[0].selectbox("Contatto oculare", ["", "buono", "ridotto", "sfuggente"], key=f"{px}_occhi")
    perdita = c[1].selectbox("Ha perso parole o abilità", ["", "no", "sì"], key=f"{px}_perdita")
    npar = c[2].number_input("Parole che usa (circa)", 0, 500, 0, key=f"{px}_npar")
    dati.update(contatto_oculare=occhi, perdita_abilita=perdita, parole_numero=npar or "")
    if occhi in ("ridotto", "sfuggente"):
        segnali.append(f"contatto oculare {occhi}")
    if perdita == "sì":
        segnali.append("perdita di parole o abilità: approfondimento prioritario")

    st.markdown("### 6 · Regolazione")
    c = st.columns(3)
    reg = {
        "sonno": c[0].selectbox("Sonno", ["", "regolare", "fatica ad addormentarsi", "risvegli frequenti", "russa o respira a bocca aperta"], key=f"{px}_sonno"),
        "alimentazione": c[1].selectbox("Alimentazione", ["", "regolare", "suzione debole", "rifiuta consistenze", "selettiva", "rigurgiti o reflusso"], key=f"{px}_alim"),
        "pianto": c[2].selectbox("Pianto e consolabilità", ["", "si consola", "fatica a consolarsi", "inconsolabile"], key=f"{px}_pianto"),
    }
    c = st.columns(3)
    reg.update({
        "tatto": c[0].selectbox("Reazione al contatto", ["", "nella norma", "evita il contatto", "cerca molto il contatto"], key=f"{px}_tatto"),
        "suoni": c[1].selectbox("Reazione ai suoni", ["", "nella norma", "eccessiva", "scarsa"], key=f"{px}_suoni"),
        "movimento": c[2].selectbox("Reazione al movimento (dondolio, altalena)", ["", "nella norma", "lo teme", "lo cerca in continuazione"], key=f"{px}_movim"),
    })
    dati.update({f"regolazione_{k}": v for k, v in reg.items()})
    for k, bad in (("sonno", ("risvegli frequenti", "russa o respira a bocca aperta")),
                   ("alimentazione", ("suzione debole", "rifiuta consistenze", "selettiva")),
                   ("pianto", ("inconsolabile",)),
                   ("tatto", ("evita il contatto",)), ("suoni", ("eccessiva", "scarsa")),
                   ("movimento", ("lo teme", "lo cerca in continuazione"))):
        if reg[k] in bad:
            segnali.append(f"{k}: {reg[k]}")

    note = st.text_area("Osservazioni cliniche sulla prima infanzia", key=f"{px}_note", height=68)
    dati["osservazioni"] = note

    st.markdown("#### Segnali emersi")
    if segnali:
        for s in segnali:
            st.markdown(f"- {s}")
        st.caption(f"{len(segnali)} segnali. Non è una diagnosi: indica dove guardare con più attenzione.")
    else:
        st.caption("Nessun segnale con i dati inseriti.")
    dati["segnali"] = "; ".join(segnali)
    return dati
