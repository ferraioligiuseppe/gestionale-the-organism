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
        c = st.columns(2)
        presc["rx_od"] = c[0].text_input("Correzione ottica da associare — OD", key=f"{px}_pr_rxod",
                                         placeholder="es. +0,50 −0,25 × 90")
        presc["rx_os"] = c[1].text_input("Correzione ottica da associare — OS", key=f"{px}_pr_rxos")
        c = st.columns(2)
        presc["uso"] = c[0].selectbox("Uso", ["", "tutto il giorno", "almeno 8 ore al giorno",
                                              "solo per lettura e schermo", "solo in movimento"], key=f"{px}_pr_uso")
        presc["ottico"] = c[1].text_input("Indicazioni per l'ottico", key=f"{px}_pr_ott",
                                          placeholder="es. centratura sulla pupilla, prisma sul lato interno")
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
                st.success("Salvato. La prescrizione da stampare è nella scheda «Storico».")
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
                    if _testo_prisma(r["prescrizione"]):
                        try:
                            pdf = pdf_prescrizione(conn, paz_id, r)
                            st.download_button("📄 Prescrizione su carta intestata (PDF)", pdf,
                                               file_name=f"prescrizione_prismi_{str(r['data'])[:10]}.pdf",
                                               mime="application/pdf", key=f"pp_pdf_{r['id']}")
                        except Exception as e:
                            st.caption(f"PDF non disponibile: {e}")
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


def _orientamento(occhio, base, gradi):
    """Gradi della base secondo lo schema TABO (0° a destra dell'esaminatore)."""
    if base == "obliqua":
        return f"{gradi}°" if gradi else "—"
    if base == "su (BS)":
        return "90°"
    if base == "giù (BI)":
        return "270°"
    if base == "interna (BN)":
        return "0°" if occhio == "OD" else "180°"
    if base == "esterna (BT)":
        return "180°" if occhio == "OD" else "0°"
    return "—"


def _paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT cognome, nome, data_nascita FROM pazienti WHERE id=%s", (int(paz_id),))
        r = cur.fetchone()
        if not r:
            return "", ""
        if isinstance(r, dict):
            return f"{r.get('cognome') or ''} {r.get('nome') or ''}".strip(), str(r.get("data_nascita") or "")[:10]
        return f"{r[0] or ''} {r[1] or ''}".strip(), str(r[2] or "")[:10]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return "", ""


def _it(d):
    d = str(d or "")[:10]
    return f"{d[8:10]}/{d[5:7]}/{d[0:4]}" if len(d) == 10 and d[4] == "-" else d


def pdf_prescrizione(conn, paz_id, riga) -> bytes:
    """Prescrizione dei prismi su carta intestata dello studio (A4)."""
    import io
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from .pdf_templates import A4, draw_intestazione, draw_footer, _carta_intestata_bytes
    W, H = A4
    verde = colors.HexColor("#1D6B44")
    p = riga["prescrizione"]
    nome, dn = _paziente(conn, paz_id)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    draw_intestazione(c, "", "")
    x0, x1 = 2.0 * cm, W - 2.0 * cm
    y = H - 5.4 * cm
    c.setFont("Helvetica-Bold", 14); c.setFillColor(verde)
    c.drawCentredString(W / 2, y, "Prescrizione di prismi posturali")
    y -= 1.0 * cm
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "Paziente:"); c.setFont("Helvetica", 10); c.drawString(x0 + 2.0 * cm, y, nome)
    c.setFont("Helvetica-Bold", 10); c.drawString(x1 - 5.2 * cm, y, "Data:")
    c.setFont("Helvetica", 10); c.drawString(x1 - 4.0 * cm, y, _it(riga.get("data")))
    if dn:
        y -= 0.55 * cm
        c.setFont("Helvetica-Bold", 10); c.drawString(x0, y, "Nato il:")
        c.setFont("Helvetica", 10); c.drawString(x0 + 2.0 * cm, y, _it(dn))

    # Tabella dei prismi
    y -= 1.1 * cm
    col = [x0, x0 + 2.2 * cm, x0 + 6.2 * cm, x0 + 10.4 * cm, x1]
    intest = ["Occhio", "Diottrie prismatiche", "Base", "Orientamento (TABO)"]
    c.setFillColor(verde); c.rect(x0, y - 0.25 * cm, x1 - x0, 0.75 * cm, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 10)
    for i, t in enumerate(intest):
        c.drawString(col[i] + 0.2 * cm, y, t)
    c.setFillColor(colors.black); c.setFont("Helvetica", 11)
    for occhio in ("OD", "OS"):
        y -= 0.9 * cm
        b, d, g = p.get(f"{occhio}_base") or "", p.get(f"{occhio}_dt") or "", p.get(f"{occhio}_gradi") or ""
        vals = [occhio, f"{d} Δ" if d else "—", b or "—", _orientamento(occhio, b, g) if b else "—"]
        for i, t in enumerate(vals):
            c.drawString(col[i] + 0.2 * cm, y, t)
        c.setStrokeColor(colors.HexColor("#C9D2DD")); c.setLineWidth(0.5)
        c.line(x0, y - 0.3 * cm, x1, y - 0.3 * cm)

    righe = []
    if p.get("rx_od") or p.get("rx_os"):
        righe.append(("Correzione ottica da associare", f"OD {p.get('rx_od') or '—'}   ·   OS {p.get('rx_os') or '—'}"))
    if p.get("montaggio"):
        righe.append(("Montaggio", p["montaggio"]))
    if p.get("uso"):
        righe.append(("Uso", p["uso"]))
    if p.get("ottico"):
        righe.append(("Indicazioni per l'ottico", p["ottico"]))
    if riga.get("prossimo"):
        righe.append(("Controllo", f"entro il {_it(riga['prossimo'])}"))
    y -= 1.0 * cm
    for et, v in righe:
        c.setFont("Helvetica-Bold", 10); c.drawString(x0, y, et + ":")
        c.setFont("Helvetica", 10)
        testo, riga_w = v, x1 - (x0 + 5.2 * cm)
        parole, linea = testo.split(), ""
        for w in parole:
            prova = (linea + " " + w).strip()
            if c.stringWidth(prova, "Helvetica", 10) > riga_w:
                c.drawString(x0 + 5.2 * cm, y, linea); y -= 0.5 * cm; linea = w
            else:
                linea = prova
        c.drawString(x0 + 5.2 * cm, y, linea)
        y -= 0.7 * cm

    y -= 0.4 * cm
    c.setFont("Helvetica-Oblique", 9); c.setFillColor(colors.HexColor("#54606D"))
    c.drawString(x0, y, "Prismi posturali secondo il metodo Martins da Cunha / Alves da Silva. "
                        "Base espressa rispetto all'occhio indicato.")
    c.setFillColor(colors.black)
    yf = 6.5 * cm if _carta_intestata_bytes() else 5.5 * cm
    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
    c.line(x1 - 6.5 * cm, yf, x1, yf)
    c.setFont("Helvetica", 9); c.drawCentredString(x1 - 3.25 * cm, yf - 0.4 * cm, "Timbro e firma")
    draw_footer(c)
    c.showPage(); c.save()
    return buf.getvalue()
