# -*- coding: utf-8 -*-
"""Prismi posturali — metodo Martins da Cunha / Alves da Silva.

Valutazione posturale con e senza prisma di prova, prescrizione dei prismi
(occhio, base, diottrie) e controlli nel tempo. Ogni valutazione o controllo
è una riga della tabella «prismi_posturali»: lo storico confronta test per
test il primo rilievo con l'ultimo.

La stessa sintesi compare nella Valutazione adulti funzionale (Posturologia)
e nel Protocollo di valutazione dei bambini (Parte 8), così i dati si
inseriscono una volta sola.

Strumenti: sinottoforo, bacchetta di Maddox con la scala tangente digitale
(static_protocollo/Maddox_digitale.html, calibrata sullo schermo), pedana.
"""
from __future__ import annotations

import datetime
import json
import os

import streamlit as st
import streamlit.components.v1 as components

BASI = ["", "su (BS)", "giù (BI)", "interna (BN)", "esterna (BT)", "obliqua"]
DIOTTRIE = ["", "0,5", "1", "1,5", "2", "2,5", "3", "4", "5", "6"]

# (chiave, test, esiti possibili)
TEST = [
    ("maddox_v", "Maddox verticale", ["", "orto", "iperforia OD", "iperforia OS"]),
    ("maddox_h", "Maddox orizzontale", ["", "orto", "esoforia", "exoforia"]),
    ("rotatori", "Test dei rotatori", ["", "simmetrici", "ipertono dx", "ipertono sx"]),
    ("conv_oc", "Convergenza oculare", ["", "simmetrica", "OD non converge", "OS non converge", "entrambi insufficienti"]),
    ("conv_pod", "Convergenza podalica", ["", "simmetrica", "asimmetrica dx", "asimmetrica sx"]),
    ("romberg", "Romberg", ["", "stabile", "oscilla", "anteriore", "posteriore", "dx", "sx"]),
    ("fukuda", "Fukuda — rotazione e verso", ["", "entro 30°", "30–45° dx", "30–45° sx", "oltre 45° dx", "oltre 45° sx"]),
    ("indici", "Test degli indici (braccia tese)", ["", "allineati", "deviano a dx", "deviano a sx", "uno più alto"]),
    ("rot_capo", "Rotazione del capo", ["", "simmetrica", "ridotta a dx", "ridotta a sx"]),
    ("spalle", "Spalle", ["", "allineate", "dx più alta", "sx più alta"]),
    ("creste", "Creste iliache", ["", "allineate", "dx più alta", "sx più alta"]),
    ("pedana", "Pedana — superficie (mm²)", None),
]


def _assicura(conn):
    if st.session_state.get("_prismi_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS prismi_posturali ("
            " id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL, data DATE NOT NULL,"
            " tipo TEXT, dati TEXT, prescrizione TEXT, prossimo DATE, note TEXT,"
            " creato_da TEXT, creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        st.session_state["_prismi_schema_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _righe(conn, paz_id):
    _assicura(conn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, data, tipo, dati, prescrizione, prossimo, note FROM prismi_posturali "
                    "WHERE paziente_id=%s ORDER BY data, id", (int(paz_id),))
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            nomi = [c[0] for c in cur.description]
            r = [dict(zip(nomi, x)) for x in r]
        for x in r:
            x["dati"] = json.loads(x.get("dati") or "{}")
            x["prescrizione"] = json.loads(x.get("prescrizione") or "{}")
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _testo_prisma(p: dict) -> str:
    parti = []
    for occhio in ("OD", "OS"):
        b, d, g = p.get(f"{occhio}_base"), p.get(f"{occhio}_dt"), p.get(f"{occhio}_gradi")
        if b and d:
            parti.append(f"{occhio} {d} Δ base {b}" + (f" a {g}°" if b == "obliqua" and g else ""))
    return " · ".join(parti)


def sintesi_prismi(conn, paz_id) -> list[str]:
    """Righe leggibili per le altre valutazioni: ultima valutazione e prescrizione."""
    if conn is None or not paz_id:
        return []
    r = _righe(conn, paz_id)
    if not r:
        return []
    u = r[-1]
    out = [f"Prismi posturali — {u.get('tipo') or 'valutazione'} del {str(u.get('data'))[:10]}"
           + (f" ({len(r)} rilievi in tutto)" if len(r) > 1 else "")]
    presc = _testo_prisma(u["prescrizione"])
    if presc:
        out.append(f"Prescrizione: {presc}" + (f", controllo il {str(u.get('prossimo'))[:10]}" if u.get("prossimo") else ""))
    for k, nome, _o in TEST:
        s, c = u["dati"].get(f"{k}_senza"), u["dati"].get(f"{k}_con")
        if s or c:
            out.append(f"{nome}: senza prisma {s or '—'} · con prisma {c or '—'}")
    return out


def _maddox_html() -> str:
    for base in ("static_protocollo", os.path.join(os.path.dirname(__file__), "..", "static_protocollo")):
        try:
            with open(os.path.join(base, "Maddox_digitale.html"), encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def render_prismi_posturali(conn, paz_id) -> None:
    st.subheader("🔺 Prismi posturali")
    st.caption("Metodo Martins da Cunha / Alves da Silva: test posturali senza e con prisma di prova, "
               "prescrizione e controlli nel tempo.")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    righe = _righe(conn, paz_id)
    t_nuova, t_storico, t_maddox = st.tabs(["➕ Valutazione o controllo", f"📈 Storico ({len(righe)})", "📏 Scala di Maddox digitale"])

    with t_nuova:
        px = f"pp_{paz_id}"
        c1, c2, c3 = st.columns(3)
        data = c1.date_input("Data", datetime.date.today(), key=f"{px}_data")
        tipo = c2.selectbox("Tipo", ["prima valutazione", "controllo", "cambio prisma"],
                            index=1 if righe else 0, key=f"{px}_tipo")
        c3.caption(f"Ultimo rilievo: {str(righe[-1]['data'])[:10]}" if righe else "Nessun rilievo precedente.")

        st.markdown("**Prisma di prova**")
        cp = st.columns(6)
        prova = {}
        for i, occhio in enumerate(("OD", "OS")):
            prova[f"{occhio}_base"] = cp[i * 3].selectbox(f"{occhio} base", BASI, key=f"{px}_pv_{occhio}_b")
            prova[f"{occhio}_dt"] = cp[i * 3 + 1].selectbox(f"{occhio} Δ", DIOTTRIE, key=f"{px}_pv_{occhio}_d")
            prova[f"{occhio}_gradi"] = cp[i * 3 + 2].text_input(f"{occhio} gradi (obliqua)", key=f"{px}_pv_{occhio}_g")

        st.markdown("**Test posturali**")
        h = st.columns([3, 3, 3])
        h[0].caption("Test")
        h[1].caption("Senza prisma")
        h[2].caption("Con prisma di prova")
        dati = {"prisma_prova": prova}
        for k, nome, opz in TEST:
            c = st.columns([3, 3, 3], vertical_alignment="center")
            c[0].markdown(nome)
            if opz is None:
                dati[f"{k}_senza"] = c[1].text_input(nome, key=f"{px}_{k}_s", label_visibility="collapsed")
                dati[f"{k}_con"] = c[2].text_input(nome, key=f"{px}_{k}_c", label_visibility="collapsed")
            else:
                dati[f"{k}_senza"] = c[1].selectbox(nome, opz, key=f"{px}_{k}_s", label_visibility="collapsed")
                dati[f"{k}_con"] = c[2].selectbox(nome, opz, key=f"{px}_{k}_c", label_visibility="collapsed")

        with st.expander("Sinottoforo e misure di Maddox in Δ"):
            s = st.columns(4)
            dati["sin_ogg_h"] = s[0].text_input("Angolo oggettivo orizzontale (Δ)", key=f"{px}_so_h")
            dati["sin_ogg_v"] = s[1].text_input("Angolo oggettivo verticale (Δ)", key=f"{px}_so_v")
            dati["sin_sog_h"] = s[2].text_input("Angolo soggettivo orizzontale (Δ)", key=f"{px}_ss_h")
            dati["sin_sog_v"] = s[3].text_input("Angolo soggettivo verticale (Δ)", key=f"{px}_ss_v")
            s = st.columns(4)
            dati["sin_fus_conv"] = s[0].text_input("Fusione — convergenza (Δ)", key=f"{px}_sf_c")
            dati["sin_fus_div"] = s[1].text_input("Fusione — divergenza (Δ)", key=f"{px}_sf_d")
            dati["maddox_dig_h"] = s[2].text_input("Maddox digitale orizzontale", key=f"{px}_md_h",
                                                   help="Il risultato copiato dalla scheda «Scala di Maddox digitale».")
            dati["maddox_dig_v"] = s[3].text_input("Maddox digitale verticale", key=f"{px}_md_v")

        st.markdown("**Prescrizione**")
        cp = st.columns(6)
        presc = {}
        for i, occhio in enumerate(("OD", "OS")):
            presc[f"{occhio}_base"] = cp[i * 3].selectbox(f"{occhio} base", BASI, key=f"{px}_pr_{occhio}_b")
            presc[f"{occhio}_dt"] = cp[i * 3 + 1].selectbox(f"{occhio} Δ", DIOTTRIE, key=f"{px}_pr_{occhio}_d")
            presc[f"{occhio}_gradi"] = cp[i * 3 + 2].text_input(f"{occhio} gradi (obliqua)", key=f"{px}_pr_{occhio}_g")
        c = st.columns(3)
        presc["montaggio"] = c[0].selectbox("Montaggio", ["", "press-on (Fresnel)", "incorporato nella lente", "occhiale di prova"], key=f"{px}_pr_m")
        sett = c[1].number_input("Controllo tra (settimane)", 0, 52, 6, key=f"{px}_pr_s")
        prossimo = data + datetime.timedelta(weeks=int(sett)) if sett else None
        c[2].caption(f"Prossimo controllo: {prossimo.strftime('%d/%m/%Y')}" if prossimo else "")
        note = st.text_area("Note", key=f"{px}_note", height=68)

        if st.button("💾 Salva", type="primary", key=f"{px}_salva"):
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO prismi_posturali (paziente_id, data, tipo, dati, prescrizione, prossimo, note, creato_da) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                            (int(paz_id), data, tipo, json.dumps(dati, ensure_ascii=False),
                             json.dumps(presc, ensure_ascii=False), prossimo, note,
                             str(st.session_state.get("username") or "")))
                conn.commit()
                st.success("Salvato.")
                st.rerun()
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Non salvato: {e}")

    with t_storico:
        if not righe:
            st.info("Nessun rilievo salvato.")
        else:
            prossimo = righe[-1].get("prossimo")
            if prossimo:
                st.caption(f"Prossimo controllo previsto: {str(prossimo)[:10]}")
            for r in reversed(righe):
                with st.expander(f"{str(r['data'])[:10]} · {r.get('tipo') or ''} · {_testo_prisma(r['prescrizione']) or 'nessuna prescrizione'}"):
                    for k, nome, _o in TEST:
                        s, c = r["dati"].get(f"{k}_senza"), r["dati"].get(f"{k}_con")
                        if s or c:
                            st.markdown(f"- **{nome}**: senza {s or '—'} · con {c or '—'}")
                    if r.get("note"):
                        st.caption(r["note"])
            if len(righe) > 1:
                st.markdown("**Primo rilievo → ultimo, senza prisma**")
                a, b = righe[0]["dati"], righe[-1]["dati"]
                cambi = [f"- {nome}: {a.get(f'{k}_senza') or '—'} → {b.get(f'{k}_senza') or '—'}"
                         for k, nome, _o in TEST if a.get(f"{k}_senza") != b.get(f"{k}_senza")]
                st.markdown("\n".join(cambi) if cambi else "Nessuna differenza tra il primo e l'ultimo rilievo.")

    with t_maddox:
        html = _maddox_html()
        if not html:
            st.error("File static_protocollo/Maddox_digitale.html non trovato.")
        else:
            st.caption("Calibra lo schermo una volta, imposta la distanza, poi usa «Schermo intero». "
                       "Copia il risultato nel campo «Maddox digitale» della valutazione.")
            components.html(html, height=720, scrolling=True)


def riquadro_sintesi(conn, paz_id, titolo="🔺 Prismi posturali") -> None:
    """Per il Protocollo di valutazione: mostra l'ultimo rilievo."""
    righe = sintesi_prismi(conn, paz_id)
    with st.expander(titolo, expanded=False):
        if righe:
            for r in righe:
                st.markdown(f"- {r}")
        else:
            st.caption("Nessun rilievo. Si compila nel modulo «🔺 Prismi posturali».")
