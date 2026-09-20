# -*- coding: utf-8 -*-
"""Protocollo Epilessia — raccolta anamnestica e clinica standard per
pazienti con crisi epilettiche/sospetta epilessia, ad uso multidisciplinare
dello Studio The Organism."""
from __future__ import annotations
import json
import streamlit as st
import pandas as pd


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS protocollo_epilessia (
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
            INSERT INTO protocollo_epilessia (paziente_id, data_valutazione, esaminatore, dati)
            VALUES (%s, CURRENT_DATE, %s, %s)
        """, (paz_id, esaminatore, json.dumps(dati, default=str)))
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
            SELECT data_valutazione, esaminatore FROM protocollo_epilessia
            WHERE paziente_id=%s ORDER BY creato_il DESC LIMIT %s
        """, (paz_id, limit))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


def _tabella(righe, colonne_fisse, key):
    df = pd.DataFrame(righe)
    cfg = {c: st.column_config.TextColumn(disabled=True) for c in colonne_fisse}
    return st.data_editor(df, key=key, hide_index=True, use_container_width=True, column_config=cfg)


def _assicura_tabella_diario(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crisi_epilessia_diario (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_crisi DATE,
                ora_crisi TEXT,
                durata_min TEXT,
                tipo TEXT,
                descrizione TEXT,
                fattore_scatenante TEXT,
                farmaco_soccorso TEXT,
                stato_postcritico TEXT,
                note TEXT,
                creato_il TIMESTAMPTZ DEFAULT now()
            )
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass


def _salva_crisi(conn, paz_id, data_crisi, ora_crisi, durata_min, tipo, descrizione,
                  fattore_scatenante, farmaco_soccorso, stato_postcritico, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crisi_epilessia_diario
            (paziente_id, data_crisi, ora_crisi, durata_min, tipo, descrizione,
             fattore_scatenante, farmaco_soccorso, stato_postcritico, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (paz_id, data_crisi, ora_crisi, durata_min, tipo, descrizione,
              fattore_scatenante, farmaco_soccorso, stato_postcritico, note))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def _elenco_crisi(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT data_crisi, ora_crisi, durata_min, tipo, descrizione,
                   fattore_scatenante, farmaco_soccorso, stato_postcritico, note
            FROM crisi_epilessia_diario WHERE paziente_id=%s
            ORDER BY data_crisi DESC, ora_crisi DESC
        """, (paz_id,))
        return cur.fetchall() or []
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []


def _pdf_diario_crisi(nome_paziente, righe, professionista="", data_nascita="") -> bytes:
    """Diario delle crisi epilettiche — stesso formato del modulo cartaceo
    PNEV: intestazione pnev.it, istruzioni, tabella Data/Ora/Durata/Note."""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY

    VERDE = colors.HexColor("#1D6B44")
    GRIGIO = colors.HexColor("#5b6b63")

    def _header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.setFillColor(VERDE)
        canvas_obj.drawString(1.8*cm, 28.3*cm, "Metodo Psico-Neuro-Evolutivo")
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(1.8*cm, 27.85*cm, "pnev.it")
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(GRIGIO)
        canvas_obj.drawString(1.8*cm, 27.4*cm,
            "Via De Rosa 46, Pagani (SA) · Piano di Sorrento (NA) · WhatsApp 391 3598767 · "
            f"apstheorganism@gmail.com · theorganism.it · pnev.it   pag. {doc.page}")
        canvas_obj.setStrokeColor(VERDE); canvas_obj.setLineWidth(0.6)
        canvas_obj.line(1.8*cm, 27.2*cm, 19.4*cm, 27.2*cm)
        canvas_obj.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=4.0*cm, bottomMargin=1.6*cm)
    styles = getSampleStyleSheet()
    s_titolo = ParagraphStyle("titolo", fontName="Helvetica-Bold", fontSize=14, textColor=VERDE, spaceAfter=4)
    s_sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=GRIGIO, spaceAfter=10)
    s_info = ParagraphStyle("info", fontName="Helvetica", fontSize=9.5, spaceAfter=10)
    s_istr = ParagraphStyle("istr", fontName="Helvetica", fontSize=8.3, leading=11.5, alignment=TA_JUSTIFY, spaceAfter=8)
    s_cella = ParagraphStyle("cella", fontName="Helvetica", fontSize=8.3, leading=10.5)
    s_cella_hdr = ParagraphStyle("cella_hdr", fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)

    elementi = [
        Paragraph("Diario delle crisi epilettiche", s_titolo),
        Paragraph("Modulo di automonitoraggio · Dott. Giuseppe Ferraioli — Psicologo, Neuropsicologo", s_sub),
        Paragraph(f"<b>Nome e cognome:</b> {nome_paziente or '—'} &nbsp;&nbsp;&nbsp; "
                  f"<b>Data di nascita:</b> {data_nascita or '—'}", s_info),
        Paragraph(
            "Compila subito dopo ogni crisi. La durata è il tempo dall'inizio alla fine dei sintomi, non il "
            "recupero: se puoi usa il cronometro del telefono, altrimenti scrivi una stima. Registra anche gli "
            "episodi brevissimi o dubbi. Se qualcuno ha assistito, annota cosa ha visto. "
            "<b>Chiama il 112</b> se la crisi supera i 5 minuti, si ripete senza ripresa di coscienza, compaiono "
            "difficoltà respiratorie, avviene in acqua, c'è un trauma, o è la prima crisi.", s_istr),
    ]

    intestazione = [Paragraph(t, s_cella_hdr) for t in ["Data", "Ora d'inizio", "Durata", "Note"]]
    dati_tabella = [intestazione]
    for r in righe:
        nota_completa = " · ".join([x for x in [
            f"Tipo: {r[3]}" if r[3] else "", f"Fattore: {r[5]}" if r[5] else "",
            f"Farmaco: {r[6]}" if r[6] else "", f"Post-crisi: {r[7]}" if r[7] else "",
            r[8] or "",
        ] if x])
        dati_tabella.append([
            Paragraph(str(r[0] or "—"), s_cella),
            Paragraph(r[1] or "—", s_cella),
            Paragraph(r[2] or "—", s_cella),
            Paragraph(nota_completa or "—", s_cella),
        ])
    righe_vuote_min = 3 if righe else 12
    for _ in range(righe_vuote_min):
        dati_tabella.append([Paragraph("&nbsp;", s_cella)]*1 + [Paragraph("", s_cella)]*3)

    tabella = Table(dati_tabella, colWidths=[2.3*cm, 2.6*cm, 2.2*cm, None], repeatRows=1)
    tabella.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d6cf")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWHEIGHT", (0, 1), (-1, -1), 0.9*cm),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8F6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementi.append(tabella)
    doc.build(elementi, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def _render_diario_crisi(conn, paz_id, paziente):
    st.markdown("### 📔 Diario delle crisi")
    st.caption("Registra ogni episodio: utile sia in seduta sia da stampare per il neurologo.")
    _assicura_tabella_diario(conn)

    with st.form("pe_form_diario", clear_on_submit=True):
        cd1, cd2, cd3 = st.columns(3)
        data_crisi = cd1.date_input("Data", key="pe_diario_data")
        ora_crisi = cd2.text_input("Ora (es. 14:30)", key="pe_diario_ora")
        durata_min = cd3.text_input("Durata (es. 2 min)", key="pe_diario_durata")
        tipo_diario = st.text_input("Tipo di crisi osservata", key="pe_diario_tipo")
        descrizione_diario = st.text_area("Descrizione dell'episodio", key="pe_diario_descrizione", height=68)
        cd4, cd5 = st.columns(2)
        fattore_diario = cd4.text_input("Fattore scatenante sospetto", key="pe_diario_fattore")
        farmaco_diario = cd5.text_input("Farmaco al bisogno somministrato", key="pe_diario_farmaco")
        stato_post = st.text_input("Stato post-critico (confusione, sonno, tempo di recupero)", key="pe_diario_postcritico")
        note_diario = st.text_area("Note", key="pe_diario_note", height=68)
        if st.form_submit_button("➕ Aggiungi episodio", type="primary"):
            if _salva_crisi(conn, paz_id, data_crisi, ora_crisi, durata_min, tipo_diario,
                             descrizione_diario, fattore_diario, farmaco_diario, stato_post, note_diario):
                st.success("Episodio registrato.")
                st.rerun()

    righe = _elenco_crisi(conn, paz_id)

    nome_paziente = ""
    if paziente:
        nome_paziente = f"{paziente.get('cognome','') if hasattr(paziente,'get') else ''} " \
                         f"{paziente.get('nome','') if hasattr(paziente,'get') else ''}".strip()

    if not righe:
        st.caption("Nessun episodio registrato finora.")
    else:
        st.dataframe(righe, use_container_width=True, column_config=None, hide_index=True)
        pdf_bytes = _pdf_diario_crisi(nome_paziente, righe, st.session_state.get("utente_nome") or "Studio The Organism",
                                       (paziente.get("data_nascita") if paziente and hasattr(paziente, "get") else "") or "")
        st.download_button("🖨️ Scarica diario delle crisi in PDF", data=pdf_bytes,
                            file_name="diario_crisi_epilessia.pdf", mime="application/pdf",
                            key="pe_diario_pdf_btn")

    st.markdown("##### 📅 Calendario mensile")
    st.caption("Una griglia di giorni si legge a colpo d'occhio: è il formato da "
               "mandare alla famiglia. Vuoto lo compilano loro, pieno serve a te "
               "per vedere come si distribuiscono le crisi nel mese.")
    import datetime as _dt
    oggi = _dt.date.today()
    cc0, cc1, cc2 = st.columns([2, 1, 1])
    _tipo_cal = cc0.radio(
        "Versione", ["Vuoto da compilare (per la famiglia)",
                     "Con le crisi già registrate (per te)"],
        key="pe_cal_tipo", label_visibility="collapsed")
    mese_sel = cc1.selectbox("Mese", list(range(1, 13)), index=oggi.month - 1,
                              format_func=lambda m: ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
                                                      "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"][m-1],
                              key="pe_cal_mese")
    anno_sel = cc2.number_input("Anno", min_value=2020, max_value=2100,
                                 value=oggi.year, step=1, key="pe_cal_anno")
    professionista = st.session_state.get("utente_nome") or "Studio The Organism"
    _vuoto = _tipo_cal.startswith("Vuoto")
    pdf_calendario = _pdf_calendario_crisi(
        nome_paziente, [] if _vuoto else righe,
        int(anno_sel), int(mese_sel), professionista, vuoto=_vuoto)
    st.download_button(
        "🖨️ Scarica il calendario del mese in PDF",
        data=pdf_calendario,
        file_name=f"calendario_crisi_{anno_sel}_{mese_sel:02d}.pdf",
        mime="application/pdf", key="pe_cal_pdf_btn")


def _pdf_calendario_crisi(nome_paziente, righe, anno, mese, professionista="",
                           vuoto=False) -> bytes:
    """Calendario mensile con intestazione The Organism / PNEV — giorni con
    crisi evidenziati, elenco sintetico sotto il mese."""
    import io
    import calendar
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as rl_canvas
    from .pdf_templates import draw_intestazione, VERDE, GRIGIO, GRIGIO_L, W, H

    giorni_con_crisi = {}
    for r in righe:
        data_c = r[0]
        if data_c and data_c.month == mese and data_c.year == anno:
            giorni_con_crisi.setdefault(data_c.day, []).append(r)

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    draw_intestazione(c, professionista, "Calendario delle crisi — pnev.it")

    mesi_it = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
               "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    y_tit = H - 5.2*cm
    c.setFont("Helvetica-Bold", 14); c.setFillColor(VERDE)
    c.drawCentredString(W/2, y_tit, f"{mesi_it[mese]} {anno}")
    c.setFont("Helvetica", 10); c.setFillColor(colors.black)
    c.drawCentredString(W/2, y_tit - 0.6*cm, f"Paziente: {nome_paziente or '—'}")

    # Sul foglio vuoto le istruzioni devono stare sulla pagina: chi compila
    # a casa, settimane dopo la consegna, non ha nessun altro riferimento.
    if vuoto:
        c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor("#555555"))
        c.drawCentredString(
            W/2, y_tit - 1.05*cm,
            "Nel giorno in cui c'è una crisi scrivi: ORA d'inizio · DURATA "
            "(dall'inizio alla fine dei sintomi) · cosa l'ha preceduta e come si è ripreso.")
        c.drawCentredString(
            W/2, y_tit - 1.42*cm,
            "Segna anche gli episodi brevissimi o dubbi. Chiama il 112 se la crisi supera "
            "i 5 minuti, si ripete senza ripresa di coscienza, o è la prima.")
        c.setFillColor(colors.black)

    giorni_settimana = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    griglia_top = y_tit - (2.1*cm if vuoto else 1.6*cm)
    margine_lat = 1.8*cm
    larghezza_cella = (W - 2*margine_lat) / 7
    altezza_cella = 3.1*cm

    c.setFont("Helvetica-Bold", 9); c.setFillColor(colors.white)
    for i, g in enumerate(giorni_settimana):
        x = margine_lat + i*larghezza_cella
        c.setFillColor(VERDE)
        c.rect(x, griglia_top, larghezza_cella, 0.7*cm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.drawCentredString(x + larghezza_cella/2, griglia_top + 0.22*cm, g)

    cal = calendar.Calendar(firstweekday=0)
    settimane = cal.monthdayscalendar(anno, mese)
    y_riga = griglia_top - altezza_cella
    for settimana in settimane:
        for i, giorno in enumerate(settimana):
            x = margine_lat + i*larghezza_cella
            c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.4)
            c.rect(x, y_riga, larghezza_cella, altezza_cella, fill=0, stroke=1)
            if giorno != 0:
                ha_crisi = giorno in giorni_con_crisi
                if ha_crisi:
                    c.setFillColor(colors.HexColor("#FBEFEA"))
                    c.rect(x, y_riga, larghezza_cella, altezza_cella, fill=1, stroke=0)
                    c.setStrokeColor(GRIGIO_L)
                    c.rect(x, y_riga, larghezza_cella, altezza_cella, fill=0, stroke=1)
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(colors.HexColor("#C8453A") if ha_crisi else colors.black)
                c.drawString(x + 0.15*cm, y_riga + altezza_cella - 0.35*cm, str(giorno))
                if ha_crisi:
                    c.setFont("Helvetica", 6.5)
                    c.setFillColor(colors.HexColor("#8b3a2e"))
                    riga_y = y_riga + altezza_cella - 0.75*cm
                    for r in giorni_con_crisi[giorno][:2]:
                        ora_c = r[1] or "—"
                        durata_c = r[2] or "—"
                        tipo_c = (r[3] or "")[:12]
                        note_c = (r[8] or "")[:22]
                        c.drawString(x + 0.13*cm, riga_y, f"⚡ {ora_c} · {durata_c}")
                        riga_y -= 0.28*cm
                        if tipo_c:
                            c.drawString(x + 0.13*cm, riga_y, tipo_c)
                            riga_y -= 0.26*cm
                        if note_c:
                            c.drawString(x + 0.13*cm, riga_y, note_c)
                            riga_y -= 0.26*cm
                        riga_y -= 0.05*cm
        y_riga -= altezza_cella

    # Elenco sintetico sotto il calendario
    y_elenco = y_riga - 0.8*cm
    c.setFont("Helvetica-Bold", 11); c.setFillColor(VERDE)
    c.drawString(margine_lat, y_elenco, f"Episodi del mese: {sum(len(v) for v in giorni_con_crisi.values())}")
    y_elenco -= 0.6*cm
    c.setFont("Helvetica", 8); c.setFillColor(colors.black)
    for giorno in sorted(giorni_con_crisi.keys()):
        for r in giorni_con_crisi[giorno]:
            if y_elenco < 2*cm:
                c.showPage()
                draw_intestazione(c, professionista, "Calendario delle crisi — pnev.it")
                y_elenco = H - 5.5*cm
            testo = f"{giorno}/{mese}/{anno} · {r[1] or '—'} · {r[3] or '—'} · durata {r[2] or '—'} · note: {r[8] or '—'}"
            c.drawString(margine_lat, y_elenco, testo[:140])
            y_elenco -= 0.42*cm

    c.showPage()
    c.save()
    return buf.getvalue()



# ── Diario delle crisi: modulo cartaceo per la famiglia ──────────────
# Non una schermata da compilare in studio, ma un foglio da stampare e
# lasciare a casa: le crisi vanno annotate nel momento in cui accadono,
# non ricostruite a memoria al controllo successivo.

_DIARIO_CRISI_HTML = """<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<title>Diario delle crisi epilettiche</title>
<style>
  @page {{ size: A4; margin: 14mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: Georgia, 'Times New Roman', serif; color:#1c2a24;
         font-size:10pt; }}
  .barra {{ display:flex; justify-content:space-between; align-items:center;
            padding:8px 0 12px; font-family:Arial,sans-serif; font-size:9pt;
            color:#555; border-bottom:1px solid #ddd; margin-bottom:10px; }}
  .barra button {{ background:#14502F; color:#fff; border:0; border-radius:4px;
                   padding:7px 16px; font-size:9pt; cursor:pointer; }}
  .pagina {{ page-break-after: always; }}
  .pagina:last-child {{ page-break-after: auto; }}
  .testata {{ display:flex; justify-content:space-between; align-items:flex-start;
              border-bottom:1.5px solid #14502F; padding-bottom:4px; margin-bottom:8px; }}
  .testata .m {{ font-family:Arial,sans-serif; font-size:8.5pt; color:#14502F;
                 font-weight:bold; letter-spacing:.03em; }}
  .testata .s {{ font-family:Arial,sans-serif; font-size:7pt; color:#6B7C74;
                 text-align:right; line-height:1.4; }}
  h1 {{ font-size:15pt; color:#14502F; margin:6px 0 1px; }}
  .sub {{ font-family:Arial,sans-serif; font-size:8.5pt; color:#5b6b63;
          margin-bottom:8px; }}
  .anag {{ display:flex; gap:10px; margin:8px 0 10px; }}
  .anag div {{ flex:1; border-bottom:1px solid #999; padding-bottom:2px; }}
  .anag .et {{ font-family:Arial,sans-serif; font-size:7.5pt; color:#6B7C74;
               display:block; }}
  .anag .vl {{ font-size:10pt; min-height:14px; display:block; }}
  .istr {{ background:#F4F8F6; border:1px solid #d8e5de; border-radius:3px;
           padding:7px 10px; font-size:8.5pt; line-height:1.5; margin-bottom:6px; }}
  .urg {{ background:#FBEFEA; border:1px solid #e3b7a8; border-radius:3px;
          padding:7px 10px; font-size:8.5pt; line-height:1.5; margin-bottom:9px;
          color:#7a2a1e; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ background:#14502F; color:#fff; font-family:Arial,sans-serif; font-size:8pt;
        padding:4px 6px; text-align:left; font-weight:bold; }}
  th .h {{ display:block; font-weight:normal; font-size:7pt; opacity:.85; }}
  td {{ border:1px solid #c9d6cf; height:{ALTEZZA}mm; vertical-align:top; padding:2px; }}
  .np {{ font-family:Arial,sans-serif; font-size:7pt; color:#6B7C74;
         text-align:right; margin-top:4px; }}
  @media print {{ .barra {{ display:none; }} }}
</style></head><body>

<div class="barra">
  <span>Diario delle crisi — {NOME} · {RIGHE} righe su {PAGINE} pagine</span>
  <button onclick="window.print()">Stampa / Salva come PDF</button>
</div>

{PAGINE_HTML}

</body></html>"""

_TESTATA = """  <div class="testata">
    <div class="m">Metodo Psico-Neuro-Evolutivo<br><span style="font-weight:normal">pnev.it</span></div>
    <div class="s">Via De Rosa 46, Pagani (SA) · Piano di Sorrento (NA)<br>
      WhatsApp 391 3598767 · apstheorganism@gmail.com · theorganism.it</div>
  </div>"""

_INTESTAZIONE_TABELLA = """    <tr>
      <th style="width:16%">Data<span class="h">gg/mm/aaaa</span></th>
      <th style="width:14%">Ora d'inizio<span class="h">hh:mm</span></th>
      <th style="width:14%">Durata<span class="h">min / sec</span></th>
      <th>Note<span class="h">com'è stata la crisi, cosa c'era prima (sonno, febbre,
        stress, dose saltata), come si è ripreso, chi ha assistito</span></th>
    </tr>"""


def _html_diario_crisi(nome="", data_nascita="", periodo="", pagine=3,
                       righe_prima=7, righe_dopo=11, codice=""):
    """Modulo di automonitoraggio da stampare.

    Il codice paziente è stampato su ogni pagina: un diario che torna
    senza nome — capita, la famiglia fotocopia o riusa il foglio — resta
    comunque attribuibile.
    """
    blocchi = []
    for p in range(1, pagine + 1):
        prima = (p == 1)
        n_righe = righe_prima if prima else righe_dopo
        corpo = "".join(
            "<tr><td></td><td></td><td></td><td></td></tr>" for _ in range(n_righe))
        testa = f"""
  <h1>Diario delle crisi epilettiche{'' if prima else ' — segue'}</h1>"""
        if not prima:
            testa += f"""
  <p class="sub">{nome or ''} · codice {codice}</p>"""
        if prima:
            testa += """
  <p class="sub">Modulo di automonitoraggio da compilare a casa e portare al controllo ·
     Dott. Giuseppe Ferraioli — Psicologo, Neuropsicologo</p>
  <div class="anag">
    <div><span class="et">Nome e cognome</span><span class="vl">{NOME}</span></div>
    <div><span class="et">Data di nascita</span><span class="vl">{DN}</span></div>
    <div><span class="et">Periodo dal / al</span><span class="vl">{PER}</span></div>
    <div style="flex:0 0 90px;text-align:right;border:0">
      <span class="et">Codice</span>
      <span class="vl" style="font-family:monospace;font-weight:bold">{COD}</span></div>
  </div>
  <div class="istr">
    Compila <b>subito dopo ogni crisi</b>. La durata è il tempo dall'inizio alla fine dei
    sintomi, non il recupero: se puoi usa il cronometro del telefono, altrimenti scrivi una
    stima. Registra anche gli episodi brevissimi o dubbi — servono. Se qualcuno ha assistito,
    annota cosa ha visto: spesso è l'informazione più utile.
  </div>
  <div class="urg">
    <b>Chiama il 112</b> se la crisi supera i 5 minuti, si ripete senza ripresa di coscienza,
    compaiono difficoltà respiratorie, avviene in acqua, c'è un trauma, oppure è la prima crisi.
  </div>""".replace("{NOME}", nome or "").replace("{DN}", data_nascita or "") \
             .replace("{PER}", periodo or "").replace("{COD}", codice or "—")

        blocchi.append(f"""<div class="pagina">
{_TESTATA}{testa}
  <table>
{_INTESTAZIONE_TABELLA}
    {corpo}
  </table>
  <div class="np">pag. {p} di {pagine}</div>
</div>""")

    totale = righe_prima + righe_dopo * (pagine - 1)
    return (_DIARIO_CRISI_HTML
            .replace("{ALTEZZA}", "16")
            .replace("{NOME}", nome or "—")
            .replace("{RIGHE}", str(totale))
            .replace("{PAGINE}", str(pagine))
            .replace("{PAGINE_HTML}", "\n".join(blocchi)))


def render_protocollo_epilessia(conn=None, paz_id=None, paziente=None) -> None:
    st.header("⚡ Protocollo Epilessia")
    st.caption("Raccolta anamnestica e clinica per paziente con crisi epilettiche/sospetta epilessia.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return

    _assicura_tabella(conn)

    c1, c2 = st.columns(2)
    esaminatore = c1.text_input("Esaminatore", key="pe_esaminatore")
    inviato_da = c2.text_input("Inviato da (neurologo/pediatra)", key="pe_inviato_da")

    st.markdown("### 1. Anamnesi generale")
    c3, c4 = st.columns(2)
    eta_esordio = c3.text_input("Età di esordio delle crisi", key="pe_eta_esordio")
    familiarita = c4.text_input("Familiarità per epilessia/convulsioni febbrili", key="pe_familiarita")
    anamnesi_perinatale = st.text_area("Anamnesi perinatale (gravidanza, parto, sofferenza neonatale)",
                                        key="pe_anamnesi_perinatale", height=68)
    sviluppo_psicomotorio = st.text_area("Sviluppo psicomotorio (tappe, eventuale regressione)",
                                          key="pe_sviluppo", height=68)
    c5, c6 = st.columns(2)
    convulsioni_febbrili = c5.selectbox("Convulsioni febbrili in anamnesi", ["", "No", "Sì semplici", "Sì complesse"],
                                         key="pe_convuls_febbrili")
    diagnosi_associate = c6.text_input("Diagnosi neurologiche/genetiche associate", key="pe_diagnosi_assoc")

    st.markdown("### 2. Descrizione delle crisi")
    st.caption("Classificazione semplificata ILAE: focale, generalizzata, esordio ignoto.")
    tipo_crisi = st.multiselect("Tipo di crisi osservate", [
        "Focale — consapevolezza conservata", "Focale — consapevolezza alterata",
        "Focale con evoluzione bilaterale tonico-clonica",
        "Generalizzata — tonico-clonica", "Generalizzata — assenza",
        "Generalizzata — mioclonica", "Generalizzata — atonica", "Generalizzata — tonica",
        "Spasmi epilettici", "Esordio ignoto", "Stato di male epilettico (anamnesi)",
    ], key="pe_tipo_crisi")
    descrizione_semeiologica = st.text_area(
        "Descrizione semeiologica (aura, automatismi, versione capo/occhi, componente motoria, "
        "durata, stato post-critico)", key="pe_semeiologia", height=80)
    c7, c8, c9 = st.columns(3)
    frequenza_crisi = c7.text_input("Frequenza attuale", key="pe_frequenza")
    durata_media = c8.text_input("Durata media", key="pe_durata_media")
    ultima_crisi = c9.text_input("Data ultima crisi", key="pe_ultima_crisi")
    fattori_scatenanti = st.multiselect("Fattori scatenanti riferiti", [
        "Febbre", "Deprivazione di sonno", "Stimoli luminosi/fotosensibilità", "Stress emotivo",
        "Mancata assunzione farmaco", "Alcol", "Ciclo mestruale", "Iperventilazione", "Nessuno identificato",
    ], key="pe_fattori_scatenanti")

    st.markdown("### 3. Indagini strumentali")
    indagini = _tabella([
        {"Indagine": "EEG standard veglia", "Data": "", "Esito": ""},
        {"Indagine": "EEG sonno/poligrafia", "Data": "", "Esito": ""},
        {"Indagine": "Video-EEG", "Data": "", "Esito": ""},
        {"Indagine": "RM encefalo", "Data": "", "Esito": ""},
        {"Indagine": "Esami genetici/metabolici", "Data": "", "Esito": ""},
    ], ["Indagine"], "pe_indagini")
    diagnosi_sindromica = st.text_input("Diagnosi sindromica (se posta)", key="pe_diagnosi_sindromica")

    st.markdown("### 4. Terapia farmacologica")
    terapia_farmaci = _tabella([
        {"Farmaco": "", "Dose": "", "Da quando": "", "Efficacia/effetti collaterali": ""},
        {"Farmaco": "", "Dose": "", "Da quando": "", "Efficacia/effetti collaterali": ""},
        {"Farmaco": "", "Dose": "", "Da quando": "", "Efficacia/effetti collaterali": ""},
    ], [], "pe_terapia_farmaci")
    farmaci_precedenti = st.text_area("Farmaci precedenti sospesi e motivo", key="pe_farmaci_precedenti", height=68)
    aderenza_terapeutica = st.selectbox("Aderenza terapeutica", ["", "Buona", "Parziale", "Scarsa"],
                                         key="pe_aderenza")

    st.markdown("### 5. Piano di gestione della crisi (emergenza)")
    farmaco_emergenza = st.text_input("Farmaco al bisogno (es. midazolam, diazepam) e dose", key="pe_farmaco_emergenza")
    istruzioni_emergenza = st.text_area(
        "Istruzioni per chi assiste alla crisi (posizione laterale di sicurezza, tempo oltre il quale "
        "chiamare il 118, cosa NON fare)", key="pe_istruzioni_emergenza", height=70)
    scuola_informata = st.selectbox("Scuola/insegnanti informati e istruiti", ["", "Sì", "No", "Parzialmente"],
                                     key="pe_scuola_informata")

    st.markdown("### 6. Impatto funzionale e quotidiano")
    impatto_scolastico = st.text_area("Impatto su apprendimento, attenzione, memoria", key="pe_impatto_scolastico", height=68)
    impatto_psicologico = st.text_area("Impatto emotivo/psicologico (paziente e famiglia)", key="pe_impatto_psic", height=68)
    limitazioni = st.multiselect("Limitazioni/precauzioni indicate", [
        "Attività in acqua solo con supervisione", "Evitare altezze", "Restrizioni sportive specifiche",
        "Attenzione a deprivazione di sonno", "Restrizioni alla guida (se pertinente)", "Nessuna limitazione particolare",
    ], key="pe_limitazioni")

    st.markdown("### 7. Sintesi e follow-up")
    sintesi_clinica = st.text_area("Sintesi clinica", key="pe_sintesi", height=80)
    prossimo_controllo = st.text_input("Prossimo controllo neurologico/EEG previsto", key="pe_prossimo_controllo")

    dati = {
        "generali": {"esaminatore": esaminatore, "inviato_da": inviato_da},
        "anamnesi": {
            "eta_esordio": eta_esordio, "familiarita": familiarita,
            "anamnesi_perinatale": anamnesi_perinatale, "sviluppo_psicomotorio": sviluppo_psicomotorio,
            "convulsioni_febbrili": convulsioni_febbrili, "diagnosi_associate": diagnosi_associate,
        },
        "crisi": {
            "tipo_crisi": tipo_crisi, "descrizione_semeiologica": descrizione_semeiologica,
            "frequenza": frequenza_crisi, "durata_media": durata_media, "ultima_crisi": ultima_crisi,
            "fattori_scatenanti": fattori_scatenanti,
        },
        "indagini": {"tabella": indagini.to_dict("records"), "diagnosi_sindromica": diagnosi_sindromica},
        "terapia": {
            "farmaci": terapia_farmaci.to_dict("records"), "farmaci_precedenti": farmaci_precedenti,
            "aderenza": aderenza_terapeutica,
        },
        "emergenza": {
            "farmaco_emergenza": farmaco_emergenza, "istruzioni": istruzioni_emergenza,
            "scuola_informata": scuola_informata,
        },
        "impatto": {
            "scolastico": impatto_scolastico, "psicologico": impatto_psicologico,
            "limitazioni": limitazioni,
        },
        "sintesi": {"testo": sintesi_clinica, "prossimo_controllo": prossimo_controllo},
    }

    if st.button("💾 Salva protocollo epilessia", type="primary", key="pe_salva"):
        if _salva(conn, paz_id, esaminatore, dati):
            st.success("Protocollo salvato.")

    st.markdown("---")
    st.markdown("#### 🖨️ Diario delle crisi da dare alla famiglia")
    st.caption("Un foglio da stampare e tenere a casa: le crisi si annotano quando "
               "accadono, non si ricostruiscono a memoria al controllo dopo.")

    _nome_p = ""
    if isinstance(paziente, dict):
        _nome_p = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()
    _dn_p = paziente.get("data_nascita") if isinstance(paziente, dict) else None
    _dn_txt = _dn_p.strftime("%d/%m/%Y") if hasattr(_dn_p, "strftime") else str(_dn_p or "")

    dc1, dc2, dc3 = st.columns(3)
    _nome_d = dc1.text_input("Nome sul modulo", value=_nome_p, key="pe_dc_nome")
    _dn_d = dc2.text_input("Data di nascita", value=_dn_txt, key="pe_dc_dn")
    _per_d = dc3.text_input("Periodo dal / al", key="pe_dc_periodo",
                             placeholder="es. 01/10 — 31/12")
    _pag = st.slider("Pagine (circa 7 crisi la prima, 11 le successive)",
                      1, 6, 3, key="pe_dc_pagine")

    # Codice stabile e leggibile: iniziali + id paziente. Serve perché un
    # diario che torna in studio senza nome resti comunque attribuibile.
    _iniz = "".join(p[0] for p in (_nome_d or "XX").split()[:2]).upper() or "XX"
    _codice = f"{_iniz}-{paz_id}"
    st.caption(f"Codice stampato su ogni pagina: **{_codice}** — se il foglio torna "
               "senza nome, sai comunque di chi è.")

    if st.button("🖨️ Genera il diario", key="pe_dc_gen"):
        _h = _html_diario_crisi(_nome_d, _dn_d, _per_d, pagine=_pag, codice=_codice)
        st.session_state["pe_dc_html"] = _h

    if st.session_state.get("pe_dc_html"):
        st.components.v1.html(st.session_state["pe_dc_html"], height=900, scrolling=True)
        st.download_button(
            "⬇️ Scarica (poi Stampa dal browser per il PDF)",
            data=st.session_state["pe_dc_html"].encode("utf-8"),
            file_name=f"diario_crisi_{(_nome_d or 'paziente').replace(' ','_')}.html",
            mime="text/html", key="pe_dc_dl")

    st.markdown("---")
    st.markdown("#### Storico")
    righe = _storico(conn, paz_id)
    if not righe:
        st.caption("Nessuna valutazione registrata finora.")
    else:
        for data_v, op in righe:
            st.caption(f"📅 {data_v} · {op or '—'}")

    st.markdown("---")
    _render_diario_crisi(conn, paz_id, paziente)

    st.markdown("---")
    st.markdown("#### 🔗 Link diario crisi per i genitori")
    st.caption("Genera un link personale: il genitore lo apre da telefono e registra l'episodio "
               "direttamente, senza bisogno di credenziali. Arriva qui nel diario e via email allo studio.")
    if st.button("🔗 Genera link diario crisi", key="pe_genera_link_diario"):
        try:
            from modules.pnev_pubblico import db_pnev_pubblico as db_link
            cog = (paziente.get("cognome") if paziente and hasattr(paziente, "get") else "") or ""
            nom = (paziente.get("nome") if paziente and hasattr(paziente, "get") else "") or ""
            email_paz = (paziente.get("email") if paziente and hasattr(paziente, "get") else "") or f"paziente{paz_id}@theorganism.local"
            utente_id = db_link.crea_utente(conn, nome=f"{nom} {cog}".strip() or f"Paziente {paz_id}", email=email_paz)
            token = db_link.crea_magic_link(conn, utente_id)
            st.session_state["pe_link_generato"] = (
                f"https://gestionale-the-organism.streamlit.app/diario_crisi_pubblico?t={token}")
        except Exception as e:
            st.session_state["pe_link_generato"] = None
            st.session_state["pe_link_errore"] = str(e)

    if st.session_state.get("pe_link_generato"):
        st.success("Link generato — valido 9 giorni, poi va rigenerato.")
        st.code(st.session_state["pe_link_generato"])
    elif st.session_state.get("pe_link_errore"):
        st.error(f"Errore generazione link: {st.session_state['pe_link_errore']}")
