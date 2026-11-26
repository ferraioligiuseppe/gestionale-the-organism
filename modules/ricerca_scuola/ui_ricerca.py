# -*- coding: utf-8 -*-
"""
modules/ricerca_scuola/ui_ricerca.py

🎓 PNEV Academy → 🏫 Ricerca scuola (giochi)

  1) Sperimentazioni   – crea il progetto (es. validazione PNEV Games in quinta primaria)
  2) Classi e codici   – crea le classi: il gestionale genera il codice classe da digitare
                         sul tablet e i codici alunno; scheda da stampare per l'insegnante
  3) Risultati         – partite arrivate dai tablet, sintesi per gioco, esportazione CSV

I dati sono anonimi e separati dall'archivio clinico (tabelle ric_*): qui non si
inseriscono mai nomi di bambini. La corrispondenza codice ↔ nome resta all'insegnante.
"""

import io

import streamlit as st

from .db_ricerca import (
    GRUPPI, init_ricerca_db, crea_sperimentazione, lista_sperimentazioni,
    crea_classe, aggiungi_alunni, lista_classi, lista_alunni,
    imposta_classe_attiva, sessioni_classe,
)

GIOCHI_URL = "https://giochi.pnev.it/classe.html"
GIOCHI_URL_PROVVISORIO = "https://giochi.91-134-106-98.sslip.io/classe.html"


def _fmt(dt):
    try:
        return dt.astimezone().strftime("%d/%m/%Y %H:%M") if dt else "—"
    except Exception:
        return str(dt or "—")


def _pdf_codici(titolo, classe, codice_classe, alunni):
    """Scheda per l'insegnante: codice classe, istruzioni e tabella codice ↔ nome da compilare a mano."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    ss = getSampleStyleSheet()
    verde = colors.HexColor("#1D6B44")
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"Codici classe {classe}")
    el = [
        Paragraph(f"<font color='#1D6B44'><b>{titolo}</b></font>", ss["Title"]),
        Paragraph(f"Classe <b>{classe}</b> — codice classe da digitare sul tablet: "
                  f"<font size=16><b>{codice_classe}</b></font>", ss["Normal"]),
        Spacer(1, 8),
        Paragraph("Come si usa: sul tablet aprire <b>giochi.pnev.it/classe.html</b>, digitare una sola volta "
                  "il codice classe; poi ogni bambino tocca il proprio codice prima di giocare e, alla fine, "
                  "si preme «Fine turno». I risultati arrivano da soli, in forma anonima.", ss["Normal"]),
        Spacer(1, 6),
        Paragraph("<b>Riservato all'insegnante.</b> Questa scheda, con i nomi scritti a mano, resta a scuola "
                  "e non va consegnata né fotografata: è l'unico collegamento tra codici e bambini.", ss["Normal"]),
        Spacer(1, 12),
    ]
    dati = [["Codice", "Nome e cognome (a mano)", "Note"]] + [[a, "", ""] for a in alunni]
    t = Table(dati, colWidths=[3 * cm, 9 * cm, 5 * cm], rowHeights=[20] + [24] * len(alunni))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), verde), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa5ae")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el.append(t)
    doc.build(el)
    return buf.getvalue()


def render_ricerca_scuola(conn):
    st.header("🏫 Ricerca scuola · giochi in classe")
    st.caption("Dati anonimi, separati dai pazienti: solo codici classe e codici alunno. "
               "I nomi dei bambini non entrano mai nel gestionale.")
    try:
        init_ricerca_db(conn)
    except Exception as e:
        st.error(f"Non riesco a preparare le tabelle della ricerca: {e}")
        return

    sper = lista_sperimentazioni(conn)
    t1, t2, t3 = st.tabs(["🧪 Sperimentazioni", "🏷️ Classi e codici", "📊 Risultati"])

    # ── 1. Sperimentazioni ──────────────────────────────────────────────
    with t1:
        with st.form("ric_nuova_sper", clear_on_submit=True):
            st.subheader("Nuova sperimentazione")
            titolo = st.text_input("Titolo", placeholder="Validazione PNEV Games – quinta primaria")
            scuola = st.text_input("Scuola / istituto")
            referenti = st.text_input("Referenti", placeholder="Prof. Todino, ricercatori, insegnanti")
            descr = st.text_area("Descrizione e piano", height=100)
            if st.form_submit_button("Crea sperimentazione", type="primary"):
                if not titolo.strip():
                    st.warning("Serve un titolo.")
                else:
                    crea_sperimentazione(conn, titolo, descr or None, scuola or None, referenti or None)
                    st.success("Sperimentazione creata.")
                    st.rerun()
        if sper:
            st.subheader("Elenco")
            for s in sper:
                st.markdown(f"**{s['titolo']}** — {s['scuola'] or 'scuola da indicare'} · "
                            f"{s['n_classi']} classi · creata il {_fmt(s['creato_il'])}")
                if s["referenti"]:
                    st.caption(f"Referenti: {s['referenti']}")
        else:
            st.info("Nessuna sperimentazione ancora: creane una qui sopra.")

    if not sper:
        with t2: st.info("Crea prima una sperimentazione.")
        with t3: st.info("Crea prima una sperimentazione.")
        return

    nomi = {s["id"]: s["titolo"] for s in sper}

    # ── 2. Classi e codici ──────────────────────────────────────────────
    with t2:
        sid = st.selectbox("Sperimentazione", list(nomi), format_func=nomi.get, key="ric_sper_classi")
        with st.form("ric_nuova_classe", clear_on_submit=True):
            st.subheader("Nuova classe")
            c1, c2, c3 = st.columns([2, 1, 2])
            nome = c1.text_input("Nome classe", placeholder="5A")
            n = c2.number_input("Alunni", min_value=1, max_value=40, value=22)
            gruppo = c3.selectbox("Gruppo", GRUPPI, index=0)
            ins = st.text_input("Insegnante di riferimento (facoltativo)")
            if st.form_submit_button("Crea classe e codici", type="primary"):
                if not nome.strip():
                    st.warning("Serve il nome della classe.")
                else:
                    _, cod = crea_classe(conn, sid, nome, n, gruppo, ins or None)
                    st.success(f"Classe creata. Codice classe: **{cod}**")
                    st.rerun()

        classi = lista_classi(conn, sid)
        st.markdown(f"Sul tablet si apre **{GIOCHI_URL}** "
                    f"(finché il dominio non è pronto: {GIOCHI_URL_PROVVISORIO}).")
        for c in classi:
            stato = "attiva" if c["attiva"] else "chiusa"
            with st.expander(f"{c['nome']} · codice {c['codice_classe']} · {c['gruppo']} · "
                             f"{c['n_alunni']} alunni · {c['n_sessioni']} partite · {stato}"):
                st.markdown(f"### Codice classe: `{c['codice_classe']}`")
                st.caption(f"Ultima partita ricevuta: {_fmt(c['ultima'])}")
                alunni = [a["codice"] for a in lista_alunni(conn, c["id"])]
                st.write(" · ".join(alunni))
                k1, k2, k3 = st.columns(3)
                k1.download_button("📄 Scheda per l'insegnante (PDF)",
                                   _pdf_codici(nomi[sid], c["nome"], c["codice_classe"], alunni),
                                   file_name=f"codici_{c['nome']}_{c['codice_classe']}.pdf",
                                   mime="application/pdf", key=f"ric_pdf_{c['id']}")
                agg = k2.number_input("Aggiungi alunni", 1, 10, 1, key=f"ric_agg_{c['id']}")
                if k2.button("Aggiungi", key=f"ric_aggb_{c['id']}"):
                    aggiungi_alunni(conn, c["id"], agg); st.rerun()
                if k3.button("Chiudi la classe" if c["attiva"] else "Riapri la classe", key=f"ric_att_{c['id']}"):
                    imposta_classe_attiva(conn, c["id"], not c["attiva"]); st.rerun()
                st.caption("Una classe chiusa non accetta più partite dai tablet.")

    # ── 3. Risultati ────────────────────────────────────────────────────
    with t3:
        sid3 = st.selectbox("Sperimentazione", list(nomi), format_func=nomi.get, key="ric_sper_ris")
        classi3 = lista_classi(conn, sid3)
        if not classi3:
            st.info("Nessuna classe in questa sperimentazione.")
            return
        scelte = st.multiselect("Classi", [c["id"] for c in classi3],
                                default=[c["id"] for c in classi3],
                                format_func={c["id"]: f"{c['nome']} ({c['gruppo']})" for c in classi3}.get)
        righe = sessioni_classe(conn, scelte)
        if not righe:
            st.info("Ancora nessuna partita ricevuta dai tablet.")
            return
        import pandas as pd
        df = pd.DataFrame(righe)
        df["err_pct"] = pd.to_numeric(df["err_pct"], errors="coerce")
        m1, m2, m3 = st.columns(3)
        m1.metric("Partite", len(df))
        m2.metric("Alunni con almeno una partita", df["codice_alunno"].nunique())
        m3.metric("Giochi usati", df["gioco"].nunique())

        st.subheader("Sintesi per classe e gioco")
        sint = (df.groupby(["classe", "gruppo", "gioco"])
                  .agg(partite=("gioco", "size"), alunni=("codice_alunno", "nunique"),
                       errori_medi_pct=("err_pct", "mean"))
                  .round(1).reset_index())
        st.dataframe(sint, use_container_width=True, hide_index=True)

        st.subheader("Tutte le partite")
        vis = df.drop(columns=["metriche"])
        st.dataframe(vis, use_container_width=True, hide_index=True)
        csv = df.assign(metriche=df["metriche"].astype(str)).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Esporta CSV per i ricercatori", csv,
                           file_name="ricerca_scuola_partite.csv", mime="text/csv")
