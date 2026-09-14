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


def _pdf_diario_crisi(nome_paziente, righe, professionista="") -> bytes:
    """Diario clinico delle crisi — un blocco per episodio, con intestazione
    The Organism/PNEV, leggibile e stampabile (non una tabella compressa)."""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as rl_canvas
    from .pdf_templates import draw_intestazione, VERDE, GRIGIO, GRIGIO_L, W, H

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    def nuova_pagina(sottotitolo="Diario delle crisi epilettiche"):
        draw_intestazione(c, professionista, sottotitolo)
        y = H - 5.2*cm
        c.setFont("Helvetica-Bold", 14); c.setFillColor(VERDE)
        c.drawString(1.8*cm, y, sottotitolo)
        c.setFont("Helvetica", 10); c.setFillColor(colors.black)
        c.drawString(1.8*cm, y - 0.6*cm, f"Paziente: {nome_paziente or '—'}")
        c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
        c.line(1.8*cm, y - 0.9*cm, W - 1.8*cm, y - 0.9*cm)
        return y - 1.6*cm

    y = nuova_pagina()
    c.setFont("Helvetica-Bold", 11); c.setFillColor(VERDE)
    c.drawString(1.8*cm, y, f"Totale episodi registrati: {len(righe)}")
    y -= 0.9*cm

    margine = 1.8*cm
    larghezza = W - 2*margine
    campi = [
        ("Data", lambda r: str(r[0] or "—")),
        ("Ora", lambda r: r[1] or "—"),
        ("Durata", lambda r: r[2] or "—"),
        ("Tipo di crisi", lambda r: r[3] or "—"),
        ("Descrizione", lambda r: r[4] or "—"),
        ("Fattore scatenante", lambda r: r[5] or "—"),
        ("Farmaco al bisogno", lambda r: r[6] or "—"),
        ("Stato post-critico", lambda r: r[7] or "—"),
        ("Note", lambda r: r[8] or "—"),
    ]

    from reportlab.pdfbase.pdfmetrics import stringWidth

    def wrap_text(testo, font, size, max_width):
        parole = str(testo).split()
        righe_w, corrente = [], ""
        for parola in parole:
            prova = (corrente + " " + parola).strip()
            if stringWidth(prova, font, size) <= max_width:
                corrente = prova
            else:
                if corrente:
                    righe_w.append(corrente)
                corrente = parola
        if corrente:
            righe_w.append(corrente)
        return righe_w or ["—"]

    for idx, r in enumerate(righe, start=1):
        blocco_altezza = 0.7*cm
        valori_wrap = {}
        for etichetta, getter in campi:
            testo = getter(r)
            righe_testo = wrap_text(testo, "Helvetica", 9, larghezza - 4.5*cm)
            valori_wrap[etichetta] = righe_testo
            blocco_altezza += max(1, len(righe_testo)) * 0.38*cm + 0.05*cm
        blocco_altezza += 0.3*cm

        if y - blocco_altezza < 2.5*cm:
            c.showPage()
            y = nuova_pagina()

        c.setFillColor(colors.HexColor("#F4F8F6"))
        c.rect(margine, y - blocco_altezza + 0.3*cm, larghezza, blocco_altezza - 0.3*cm, fill=1, stroke=0)
        c.setStrokeColor(GRIGIO_L)
        c.rect(margine, y - blocco_altezza + 0.3*cm, larghezza, blocco_altezza - 0.3*cm, fill=0, stroke=1)

        c.setFont("Helvetica-Bold", 10); c.setFillColor(VERDE)
        c.drawString(margine + 0.25*cm, y - 0.15*cm, f"Episodio {idx} — {campi[0][1](r)}")
        yy = y - 0.75*cm
        for etichetta, _ in campi[1:]:
            c.setFont("Helvetica-Bold", 8.5); c.setFillColor(colors.HexColor("#2f4b3d"))
            c.drawString(margine + 0.25*cm, yy, f"{etichetta}:")
            c.setFont("Helvetica", 8.5); c.setFillColor(colors.black)
            for j, riga_testo in enumerate(valori_wrap[etichetta]):
                c.drawString(margine + 3.4*cm, yy - j*0.38*cm, riga_testo)
            yy -= max(1, len(valori_wrap[etichetta])) * 0.38*cm + 0.05*cm

        y -= blocco_altezza + 0.35*cm

    c.showPage()
    c.save()
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
        pdf_bytes = _pdf_diario_crisi(nome_paziente, righe, st.session_state.get("utente_nome") or "Studio The Organism")
        st.download_button("🖨️ Scarica diario delle crisi in PDF", data=pdf_bytes,
                            file_name="diario_crisi_epilessia.pdf", mime="application/pdf",
                            key="pe_diario_pdf_btn")

    st.markdown("##### 📅 Calendario mensile")
    import datetime as _dt
    oggi = _dt.date.today()
    cc1, cc2 = st.columns(2)
    mese_sel = cc1.selectbox("Mese", list(range(1, 13)), index=oggi.month - 1,
                              format_func=lambda m: ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
                                                      "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"][m-1],
                              key="pe_cal_mese")
    anno_sel = cc2.number_input("Anno", min_value=2020, max_value=2100, value=oggi.year, step=1, key="pe_cal_anno")
    professionista = st.session_state.get("utente_nome") or "Studio The Organism"
    pdf_calendario = _pdf_calendario_crisi(nome_paziente, righe, int(anno_sel), int(mese_sel), professionista)
    st.download_button("🖨️ Scarica calendario del mese in PDF (con intestazione)", data=pdf_calendario,
                        file_name=f"calendario_crisi_{anno_sel}_{mese_sel:02d}.pdf", mime="application/pdf",
                        key="pe_cal_pdf_btn")


def _pdf_calendario_crisi(nome_paziente, righe, anno, mese, professionista="") -> bytes:
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

    giorni_settimana = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    griglia_top = y_tit - 1.6*cm
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
            link = f"https://gestionale-the-organism.streamlit.app/diario_crisi_pubblico?t={token}"
            st.success("Link generato — valido 9 giorni, poi vanne generato uno nuovo.")
            st.code(link)
        except Exception as e:
            st.error(f"Errore generazione link: {e}")
