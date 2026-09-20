# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  PIANO DI TRATTAMENTO — l'individuo al centro                        ║
║                                                                      ║
║  Perche' esiste questo modulo. «Percorsi terapeutici» organizza il   ║
║  lavoro per metodo: scegli Vision Therapy, poi dentro trovi il       ║
║  paziente. Un bambino che fa Vision Therapy, MAPS e riflessi ha      ║
║  cosi' tre diari, tre elenchi di obiettivi e tre relazioni che non   ║
║  si parlano, e alla domanda «come sta andando» non c'e' risposta.    ║
║                                                                      ║
║  Qui l'ordine e' rovesciato: si apre la persona e si vede il suo     ║
║  piano, che attraversa i percorsi. L'approccio (visiva, uditiva,     ║
║  riflessi…) non e' piu' un posto dove entrare ma un'etichetta sulla  ║
║  riga, ricavata dalla colonna `terapia` che gia' esiste.             ║
║                                                                      ║
║  NON sostituisce terapia.py: gli si affianca. Legge le stesse        ║
║  tabelle senza filtrare per un solo percorso. L'unica cosa nuova e'  ║
║  `piani_trattamento`, un record per paziente con titolo, inizio,     ║
║  durata e data di rivalutazione.                                     ║
║                                                                      ║
║  Nessuna migrazione: tutto cio' che e' gia' stato inserito si legge  ║
║  com'e'.                                                             ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import datetime
import json
import re

import streamlit as st

# Soglia sotto la quale l'aderenza a casa diventa un avviso rosso.
SOGLIA_ADERENZA = 70

# I nove percorsi di terapia.py, tradotti nell'approccio che li descrive.
# Questa e' l'unica mappa da toccare per cambiare le etichette: gli
# obiettivi e le sedute restano salvati col nome del percorso, come oggi.
APPROCCIO = {
    "Vision Therapy": "VISIVA",
    "Sports Vision": "VISIVA",
    "MAPS": "UDITIVA",
    "Terapia riflessi primitivi": "RIFLESSI",
    "Terapia miofunzionale": "MIOFUNZIONALE",
    "Metodo Castagnini": "POSTURALE",
    "Osteopatia": "OSTEOPATICA",
    "Stanza del sale": "RESPIRATORIA",
    "Terapia psicologica / psicoterapia": "PSICOLOGICA",
}

STATO_OB = ["🟦 In corso", "🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"]

_TABELLE_PRONTE = False


# ══════════════════════════════════════════════════════════════════════
#  Tabelle
# ══════════════════════════════════════════════════════════════════════

def _assicura_tabelle(conn) -> None:
    """Crea la tabella del piano. Una volta per processo: il DDL a ogni
    render genera lock quando due ambienti puntano allo stesso Postgres."""
    global _TABELLE_PRONTE
    if _TABELLE_PRONTE:
        return
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS piani_trattamento(
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT UNIQUE,
            titolo TEXT,
            data_inizio DATE,
            settimane_totali INT,
            data_rivalutazione DATE,
            stato TEXT DEFAULT 'In corso',
            note TEXT,
            creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
        _TABELLE_PRONTE = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Lettura dati — tutti i percorsi insieme
# ══════════════════════════════════════════════════════════════════════

def _carica_piano(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT titolo, data_inizio, settimane_totali,
            data_rivalutazione, stato, note FROM piani_trattamento
            WHERE paziente_id=%s""", (paz_id,))
        row = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    if not row:
        return None
    return {"titolo": row[0], "data_inizio": row[1], "settimane_totali": row[2],
            "data_rivalutazione": row[3], "stato": row[4], "note": row[5]}


def _salva_piano(conn, paz_id, titolo, data_inizio, settimane, data_riv, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO piani_trattamento(paziente_id, titolo,
            data_inizio, settimane_totali, data_rivalutazione, note)
            VALUES(%s,%s,%s,%s,%s,%s)
            ON CONFLICT (paziente_id) DO UPDATE SET
                titolo=EXCLUDED.titolo, data_inizio=EXCLUDED.data_inizio,
                settimane_totali=EXCLUDED.settimane_totali,
                data_rivalutazione=EXCLUDED.data_rivalutazione,
                note=EXCLUDED.note""",
            (paz_id, titolo, data_inizio, int(settimane or 0), data_riv, note))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _carica_obiettivi(conn, paz_id):
    """Tutti gli obiettivi del paziente, di qualunque percorso, ordinati
    per quanto manca al target: prima quelli piu' lontani."""
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, terapia, descrizione, baseline, attuale,
            target, stato, data_rivalut FROM terapia_obiettivi
            WHERE paziente_id=%s ORDER BY creato DESC""", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    fuori = []
    for rid, terapia, descr, base, att, targ, stato, driv in righe:
        if stato == "🟢 Raggiunto":
            continue
        manca = (targ or 10) - (att or 0)
        fuori.append({"id": rid, "terapia": terapia or "—", "descrizione": descr or "",
                      "baseline": base or 0, "attuale": att or 0, "target": targ or 10,
                      "stato": stato or "🟦 In corso", "rivalut": driv, "manca": manca})
    fuori.sort(key=lambda o: -o["manca"])
    return fuori


def _carica_sedute(conn, paz_id, limite=12):
    """Registro unico: tutte le sedute del paziente, ogni percorso."""
    try:
        cur = conn.cursor()
        cur.execute("""SELECT data_seduta, terapia, numero, obiettivo, risposta,
            procedure_studio, procedure_casa FROM terapia_sedute
            WHERE paziente_id=%s ORDER BY data_seduta DESC, id DESC LIMIT %s""",
            (paz_id, limite))
        return cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _conta_sedute(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM terapia_sedute WHERE paziente_id=%s", (paz_id,))
        return cur.fetchone()[0] or 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return 0


def _ultima_assegnazione(conn, paz_id):
    """Le procedure dell'ultima seduta registrata: cosa e' stato fatto in
    studio e cosa e' stato lasciato per casa."""
    try:
        cur = conn.cursor()
        cur.execute("""SELECT data_seduta, procedure_studio, procedure_casa
            FROM terapia_sedute WHERE paziente_id=%s
            ORDER BY data_seduta DESC, id DESC LIMIT 1""", (paz_id,))
        row = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None, [], []
    if not row:
        return None, [], []
    data_s, p_studio, p_casa = row
    return data_s, _lista(p_studio), _lista(p_casa)


def _lista(valore):
    if not valore:
        return []
    if isinstance(valore, list):
        return valore
    try:
        out = json.loads(valore)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _aderenza_per_procedura(conn, paz_id, giorni=7):
    """Quante volte ogni procedura di casa e' stata segnata fatta nei
    giorni scorsi. Serve a distinguere «la famiglia non collabora» da
    «quel singolo esercizio non funziona»."""
    try:
        cur = conn.cursor()
        soglia = datetime.date.today() - datetime.timedelta(days=giorni)
        cur.execute("""SELECT procedura,
                COUNT(*) FILTER (WHERE fatto), COUNT(*)
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data >= %s
            GROUP BY procedura""", (paz_id, soglia))
        return {r[0]: (r[1] or 0, r[2] or 0) for r in cur.fetchall()}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}


# ══════════════════════════════════════════════════════════════════════
#  Etichette
# ══════════════════════════════════════════════════════════════════════

def _approccio(terapia: str) -> str:
    return APPROCCIO.get((terapia or "").strip(), (terapia or "—").upper()[:14])


def _approccio_procedura(voce: str) -> tuple[str, str]:
    """Le procedure sono salvate come «[Approccio] step · Nome».
    Ritorna (etichetta, nome pulito)."""
    voce = (voce or "").strip()
    m = re.match(r"^\[([^\]]+)\]\s*(.*)$", voce)
    if m:
        etichetta = _approccio(m.group(1)) if m.group(1) in APPROCCIO else m.group(1).upper()
        return etichetta[:14], m.group(2).strip() or voce
    return "—", voce


def _nome_pulito(voce: str) -> str:
    return _approccio_procedura(voce)[1]


# ══════════════════════════════════════════════════════════════════════
#  Blocchi di schermata
# ══════════════════════════════════════════════════════════════════════

def _blocco_intestazione(conn, paz_id, piano):
    """Titolo del piano, da quando, a che settimana siamo, rivalutazione."""
    oggi = datetime.date.today()
    if piano and piano.get("data_inizio"):
        giorni = (oggi - piano["data_inizio"]).days
        sett_corrente = max(1, giorni // 7 + 1)
    else:
        sett_corrente = None

    if piano and piano.get("titolo"):
        tot = piano.get("settimane_totali") or 0
        riga_sett = f"settimana {sett_corrente}" + (f" di {tot}" if tot else "")
        inizio = piano["data_inizio"].strftime("%d/%m/%Y") if piano.get("data_inizio") else "—"
        st.markdown(
            "<div style='background:var(--color-background-info);"
            "border-left:3px solid var(--color-text-info);border-radius:6px;"
            "padding:11px 15px;margin-bottom:12px'>"
            "<div style='font-size:11px;letter-spacing:.06em;"
            "color:var(--color-text-secondary)'>PIANO DI TRATTAMENTO</div>"
            f"<div style='font-size:16px;font-weight:600;margin-top:3px'>{piano['titolo']}</div>"
            f"<div style='font-size:12.5px;color:var(--color-text-secondary);margin-top:2px'>"
            f"dal {inizio} · {riga_sett}</div></div>",
            unsafe_allow_html=True)
    else:
        st.info("Questo paziente non ha ancora un piano. Compilalo qui sotto: "
                "serve a dare un nome e una scadenza al lavoro che stai già facendo.")

    with st.expander("✏️ Piano — titolo, durata, rivalutazione",
                     expanded=not (piano and piano.get("titolo"))):
        with st.form("piano_intestazione"):
            titolo = st.text_input(
                "Obiettivo generale del piano",
                value=(piano or {}).get("titolo") or "",
                placeholder="es. Integrazione visuo-uditiva e controllo posturale")
            c1, c2, c3 = st.columns(3)
            with c1:
                data_inizio = st.date_input(
                    "Inizio", value=(piano or {}).get("data_inizio") or oggi)
            with c2:
                settimane = st.number_input(
                    "Durata (settimane)", min_value=0, max_value=104, step=1,
                    value=int((piano or {}).get("settimane_totali") or 20))
            with c3:
                data_riv = st.date_input(
                    "Rivalutazione",
                    value=(piano or {}).get("data_rivalutazione")
                    or oggi + datetime.timedelta(weeks=10))
            note = st.text_area("Note", value=(piano or {}).get("note") or "", height=70)
            if st.form_submit_button("💾 Salva piano", type="primary"):
                if not titolo.strip():
                    st.warning("Dai un titolo al piano.")
                elif _salva_piano(conn, paz_id, titolo.strip(), data_inizio,
                                  settimane, data_riv, note):
                    st.success("Piano salvato.")
                    st.rerun()
                else:
                    st.error("Salvataggio non riuscito.")


def _blocco_metriche(obiettivi, n_sedute, aderenza, piano, ultima_seduta):
    approcci = len({_approccio(o["terapia"]) for o in obiettivi})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Obiettivi attivi", len(obiettivi),
              f"{approcci} approcc{'io' if approcci == 1 else 'i'}" if approcci else None)
    c2.metric("Sedute totali", n_sedute,
              ultima_seduta.strftime("ultima il %d/%m") if ultima_seduta else None)
    pct = aderenza.get("pct")
    c3.metric("Aderenza a casa", f"{pct}%" if pct is not None else "—",
              "sotto soglia" if (pct is not None and pct < SOGLIA_ADERENZA) else None,
              delta_color="inverse")
    if piano and piano.get("data_rivalutazione"):
        mancano = (piano["data_rivalutazione"] - datetime.date.today()).days
        c4.metric("Rivalutazione", piano["data_rivalutazione"].strftime("%d/%m"),
                  f"fra {mancano} giorni" if mancano >= 0 else f"{abs(mancano)} giorni fa",
                  delta_color="off")
    else:
        c4.metric("Rivalutazione", "—")


def _blocco_obiettivi(conn, paz_id, obiettivi):
    st.markdown("#### 🎯 Obiettivi")
    if not obiettivi:
        st.caption("Nessun obiettivo aperto. Si creano da «🧘 Percorsi terapeutici → "
                   "Obiettivi & monitoraggio»: qui compaiono tutti insieme, "
                   "di qualunque percorso.")
        return
    st.caption("Tutti i percorsi insieme, dal più lontano dal target. "
               "L'etichetta a destra dice l'approccio, non è una cartella.")

    for o in obiettivi:
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"**{o['descrizione']}**")
        with c2:
            st.markdown(
                f"<div style='text-align:right;font-size:11px;letter-spacing:.06em;"
                f"color:var(--color-text-secondary);padding-top:4px'>"
                f"{_approccio(o['terapia'])}</div>", unsafe_allow_html=True)

        rng = max(1, o["target"] - o["baseline"])
        prog = min(1.0, max(0.0, (o["attuale"] - o["baseline"]) / rng))
        testo = f"{o['stato']}  ·  {o['attuale']}/{o['target']} (partenza {o['baseline']})"
        if o["rivalut"]:
            try:
                testo += f"  ·  rivaluta il {o['rivalut'].strftime('%d/%m/%Y')}"
            except Exception:
                pass
        st.progress(prog, text=testo)

        with st.expander("Aggiorna", expanded=False):
            a1, a2, a3 = st.columns([2, 2, 1])
            with a1:
                nuovo = st.slider("Livello attuale", 0, 10, int(o["attuale"]),
                                  key=f"pt_ob_val_{o['id']}")
            with a2:
                nuovo_stato = st.selectbox(
                    "Stato", STATO_OB,
                    index=STATO_OB.index(o["stato"]) if o["stato"] in STATO_OB else 0,
                    key=f"pt_ob_st_{o['id']}")
            with a3:
                st.write("")
                st.write("")
                if st.button("💾", key=f"pt_ob_save_{o['id']}", help="Salva"):
                    _aggiorna_obiettivo(conn, o["id"], nuovo, nuovo_stato,
                                        paz_id, o["descrizione"], o["terapia"])
                    st.rerun()
        st.markdown("<hr style='margin:6px 0;border:none;"
                    "border-top:1px solid rgba(128,128,128,.18)'>",
                    unsafe_allow_html=True)


def _aggiorna_obiettivo(conn, rid, attuale, stato, paz_id, descr, terapia):
    """Stesso comportamento di terapia.py: alla chiusura l'esito confluisce
    nell'Apprendimento PNEV, cosi' i due schermi restano coerenti."""
    try:
        cur = conn.cursor()
        cur.execute("UPDATE terapia_obiettivi SET attuale=%s, stato=%s WHERE id=%s",
                    (int(attuale), stato, rid))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return
    if stato not in ("🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"):
        return
    esito = {"🟢 Raggiunto": "🟢 Migliorato", "🟡 Parziale": "🟡 Stabile / fermo",
             "⏸️ Sospeso": "⚪ Non valutabile"}.get(stato, "⚪ Non valutabile")
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data TIMESTAMP DEFAULT NOW(),
            intervento TEXT, esito TEXT, note TEXT);""")
        cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                    "VALUES(%s,%s,%s,%s)",
                    (paz_id, f"{terapia}: {descr}", esito, "Da piano di trattamento"))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _blocco_settimana(conn, paz_id, data_ultima, studio, casa):
    st.markdown("#### 📋 Questa settimana")
    if not studio and not casa:
        st.caption("Nessuna procedura assegnata nell'ultima seduta. "
                   "Si assegnano da «🧘 Percorsi terapeutici → Diario sedute».")
        return

    quando = data_ultima.strftime("%d/%m/%Y") if data_ultima else "—"
    st.caption(f"Da quanto assegnato nella seduta del {quando}, tutti gli approcci insieme.")

    per_proc = _aderenza_per_procedura(conn, paz_id, giorni=7)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**🏥 In studio**")
        if studio:
            for voce in studio:
                etichetta, nome = _approccio_procedura(voce)
                st.markdown(
                    f"<div style='display:flex;gap:10px;align-items:baseline;margin:4px 0'>"
                    f"<span style='font-size:10.5px;letter-spacing:.06em;"
                    f"color:var(--color-text-secondary);min-width:12ch'>{etichetta}</span>"
                    f"<span style='font-size:14px'>{nome}</span></div>",
                    unsafe_allow_html=True)
        else:
            st.caption("—")

    with c2:
        st.markdown("**🏠 A casa** <span style='font-size:11px;color:gray'>"
                    "(ultimi 7 giorni)</span>", unsafe_allow_html=True)
        if casa:
            for voce in casa:
                etichetta, nome = _approccio_procedura(voce)
                fatti, tot = per_proc.get(voce, per_proc.get(nome, (None, None)))
                if tot:
                    quota = f"{fatti}/{tot}"
                    colore = ("var(--color-text-error)" if fatti / tot < 0.5
                              else "var(--color-text-success)")
                else:
                    quota, colore = "—", "var(--color-text-secondary)"
                st.markdown(
                    f"<div style='display:flex;gap:10px;align-items:baseline;margin:4px 0'>"
                    f"<span style='font-size:10.5px;letter-spacing:.06em;"
                    f"color:var(--color-text-secondary);min-width:12ch'>{etichetta}</span>"
                    f"<span style='font-size:14px;flex:1'>{nome}</span>"
                    f"<span style='font-size:12px;color:{colore}'>{quota}</span></div>",
                    unsafe_allow_html=True)
        else:
            st.caption("—")


def _blocco_aderenza(conn, paz_id, aderenza, casa):
    st.markdown("#### 🏠 Aderenza al lavoro a casa")
    pct = aderenza.get("pct")
    if pct is None:
        st.caption("Nessun feedback ancora registrato dalla famiglia. "
                   "Le credenziali del portale si impostano da "
                   "«🧘 Percorsi terapeutici → Portale famiglia».")
        return

    if pct < SOGLIA_ADERENZA:
        deboli = _procedure_deboli(conn, paz_id, casa)
        messaggio = (f"⚠️ **Aderenza al {pct}%**, sotto la soglia del {SOGLIA_ADERENZA}%.")
        if deboli:
            elenco = ", ".join(f"«{d}»" for d in deboli[:3])
            messaggio += (f" Le procedure ferme sono {elenco}: le altre reggono. "
                          "Vale la pena chiedere se è l'esercizio a non funzionare, "
                          "prima di insistere.")
        st.warning(messaggio)

    m1, m2, m3 = st.columns(3)
    m1.metric("Fatte", f"{pct}%", f"{aderenza['fatti']}/{aderenza['totali']} in 30 giorni",
              delta_color="off")
    m2.metric("Come è andata", f"{aderenza['media_valutazione'] or '—'}/5",
              "voto del genitore", delta_color="off")
    ultimo = _ultimo_video(conn, paz_id)
    m3.metric("Ultimo video", ultimo or "—", "caricato dalla famiglia", delta_color="off")


def _procedure_deboli(conn, paz_id, casa, giorni=21):
    """Le procedure di casa segnate fatte meno di una volta su tre."""
    per_proc = _aderenza_per_procedura(conn, paz_id, giorni=giorni)
    deboli = []
    for voce in casa:
        nome = _nome_pulito(voce)
        fatti, tot = per_proc.get(voce, per_proc.get(nome, (None, None)))
        if tot and fatti / tot < 0.34:
            deboli.append(nome)
    return deboli


def _ultimo_video(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT MAX(data) FROM programma_casa_feedback
            WHERE paziente_id=%s AND video_bambino_url IS NOT NULL""", (paz_id,))
        row = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    if not row or not row[0]:
        return None
    giorni = (datetime.date.today() - row[0]).days
    if giorni == 0:
        return "oggi"
    if giorni == 1:
        return "ieri"
    return f"{giorni} gg fa"


def _blocco_sedute(conn, paz_id):
    st.markdown("#### 📅 Sedute")
    righe = _carica_sedute(conn, paz_id)
    if not righe:
        st.caption("Nessuna seduta registrata. Si registrano da "
                   "«🧘 Percorsi terapeutici → Diario sedute».")
        return
    st.caption("Un registro solo, in ordine di data, di tutti i percorsi.")

    try:
        import pandas as pd
        tabella = pd.DataFrame([{
            "Data": ds.strftime("%d/%m/%Y") if ds else "—",
            "Percorso": f"{terapia or '—'} · n°{num or '?'}",
            "Approccio": _approccio(terapia),
            "Obiettivo della seduta": ob or "—",
            "Risposta": risp or "—",
        } for ds, terapia, num, ob, risp, _ps, _pc in righe])
        st.dataframe(tabella, hide_index=True, use_container_width=True)
    except Exception:
        for ds, terapia, num, ob, risp, _ps, _pc in righe:
            data_str = ds.strftime("%d/%m/%Y") if ds else "—"
            st.markdown(f"**{data_str}** · {terapia} n°{num} — {ob or '—'} · {risp or '—'}")


def _blocco_azioni():
    st.markdown("#### Azioni")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ Nuova seduta", use_container_width=True, type="primary",
                     key="pt_go_seduta"):
            _vai("🧘 Percorsi terapeutici")
    with c2:
        if st.button("📚 Libreria procedure", use_container_width=True,
                     key="pt_go_libreria"):
            _vai("🧩 Programma PNEV")
    with c3:
        if st.button("📈 Esiti / Follow-up", use_container_width=True,
                     key="pt_go_esiti"):
            _vai("📈 Esiti / Follow-up", area="👥 Pazienti")


def _vai(sotto, area=None):
    """Salta a un'altra voce del menu, come fanno i link della Dashboard."""
    try:
        from .app_menu import AREA_TERAPIA_PNEV
        st.session_state["goto_area"] = area or AREA_TERAPIA_PNEV
    except Exception:
        if area:
            st.session_state["goto_area"] = area
    st.session_state["goto_sotto"] = sotto
    st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  Schermata
# ══════════════════════════════════════════════════════════════════════

def render_piano_trattamento(conn=None, paz_id=None, paziente=None):
    st.header("🎯 Piano di trattamento")
    st.caption("Gli obiettivi, il lavoro di questa settimana e l'aderenza — "
               "di tutti i percorsi insieme, per questa persona.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    # Il paziente attivo lo seleziona gia' il router (VOCI_CON_PAZIENTE):
    # richiamare qui header_paziente_attivo duplicherebbe il box.
    if not paz_id:
        st.info("Seleziona un paziente qui sopra per vedere il suo piano.")
        return

    _assicura_tabelle(conn)

    piano = _carica_piano(conn, paz_id)
    obiettivi = _carica_obiettivi(conn, paz_id)
    n_sedute = _conta_sedute(conn, paz_id)
    data_ultima, studio, casa = _ultima_assegnazione(conn, paz_id)

    aderenza = {"fatti": 0, "totali": 0, "pct": None, "media_valutazione": None}
    try:
        from modules import db_portale_famiglia as dbf
        dbf.init_db(conn)
        aderenza = dbf.get_aderenza_riepilogo(conn, paz_id, giorni=30)
    except Exception:
        pass

    _blocco_intestazione(conn, paz_id, piano)
    _blocco_metriche(obiettivi, n_sedute, aderenza, piano, data_ultima)
    st.divider()
    _blocco_obiettivi(conn, paz_id, obiettivi)
    st.divider()
    _blocco_settimana(conn, paz_id, data_ultima, studio, casa)
    st.divider()
    _blocco_aderenza(conn, paz_id, aderenza, casa)
    st.divider()
    _blocco_sedute(conn, paz_id)
    st.divider()
    _blocco_azioni()
