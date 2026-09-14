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


def _pdf_diario_crisi(nome_paziente, righe) -> bytes:
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                             leftMargin=14*mm, rightMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    titolo = ParagraphStyle("titolo", parent=styles["Heading1"], textColor=colors.HexColor("#1D6B44"), fontSize=16)
    normale = ParagraphStyle("normale", parent=styles["Normal"], fontSize=8, leading=10)

    elementi = [
        Paragraph("Diario delle crisi epilettiche", titolo),
        Paragraph(f"Paziente: {nome_paziente or '—'}", styles["Normal"]),
        Spacer(1, 8),
    ]
    intestazione = ["Data", "Ora", "Durata", "Tipo", "Descrizione", "Fattore scat.", "Farmaco", "Post-critico", "Note"]
    dati_tabella = [intestazione]
    for r in righe:
        dati_tabella.append([Paragraph(str(c or "—"), normale) for c in r])

    tabella = Table(dati_tabella, repeatRows=1)
    tabella.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D6B44")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8F6")]),
    ]))
    elementi.append(tabella)
    doc.build(elementi)
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
    if not righe:
        st.caption("Nessun episodio registrato finora.")
        return

    st.dataframe(righe, use_container_width=True,
                 column_config=None, hide_index=True)

    nome_paziente = ""
    if paziente:
        nome_paziente = f"{paziente.get('cognome','') if hasattr(paziente,'get') else ''} " \
                         f"{paziente.get('nome','') if hasattr(paziente,'get') else ''}".strip()
    pdf_bytes = _pdf_diario_crisi(nome_paziente, righe)
    st.download_button("🖨️ Scarica diario delle crisi in PDF", data=pdf_bytes,
                        file_name="diario_crisi_epilessia.pdf", mime="application/pdf",
                        key="pe_diario_pdf_btn")


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
