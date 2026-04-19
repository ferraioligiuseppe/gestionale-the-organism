# -*- coding: utf-8 -*-
"""
Valutazione Visuo-Percettiva - The Organism
8 tab: anamnesi visiva, esame obiettivo, refrazione,
oculomotricita, binocolarita/accomodazione,
percezione visiva, profilo funzionale, prescrizione/relazione.
"""
from __future__ import annotations
import json
import datetime
import streamlit as st


def _get_user() -> dict:
    return st.session_state.get("user") or {}

def _professionista_label() -> str:
    u = _get_user()
    return u.get("username", "The Organism Studio")

def _sk(sez, campo, paz_id):
    return f"vvp_{paz_id}_{sez}_{campo}"

def _carica(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT visita_json FROM valutazioni_visive "
            "WHERE paziente_id=%s ORDER BY id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if not row: return {}
        raw = row["visita_json"] if isinstance(row, dict) else row[0]
        if not raw: return {}
        return raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        return {}

def _salva_visita(conn, paz_id, dati):
    try:
        cur = conn.cursor()
        dump = json.dumps(dati, ensure_ascii=False, default=str)
        cur.execute(
            "SELECT id FROM valutazioni_visive WHERE paziente_id=%s ORDER BY id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if row:
            vid = int(row["id"] if isinstance(row, dict) else row[0])
            cur.execute(
                "UPDATE valutazioni_visive SET visita_json=%s::jsonb WHERE id=%s",
                (dump, vid)
            )
        else:
            cur.execute(
                "INSERT INTO valutazioni_visive "
                "(paziente_id, data_valutazione, professionista, visita_json) "
                "VALUES (%s,%s,%s,%s::jsonb)",
                (paz_id, datetime.date.today().isoformat(),
                 _professionista_label(), dump)
            )
        conn.commit()
        st.success("Salvato.")
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")

def _radio(label, opzioni, key, default=None):
    idx = opzioni.index(default) if default in opzioni else 0
    return st.radio(label, opzioni, index=idx, horizontal=True, key=key)

def _scala(label, key, default=3, mn="1 Deficit", mx="5 Norma"):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"**{label}**")
        st.caption(f"{mn}  -  {mx}")
    with col2:
        val = st.select_slider(label, options=[1,2,3,4,5],
                               value=default, key=key,
                               label_visibility="collapsed")
    ico = "verde" if val>=4 else ("giallo" if val==3 else "rosso")
    colore = "#22c55e" if val>=4 else ("#f59e0b" if val>=2 else "#ef4444")
    st.markdown(
        f'<span style="background:{colore}22;color:{colore};'
        f'padding:2px 8px;border-radius:8px;font-size:12px">{val}/5</span>',
        unsafe_allow_html=True)
    return val

def _txt(label, key, default="", height=None):
    if height:
        return st.text_area(label, value=default, key=key, height=height)
    return st.text_input(label, value=default, key=key)


# ══ TAB 1 — ANAMNESI VISIVA ══════════════════════════════════════════

def _t1_anamnesi(paz_id, d):
    st.markdown("### Anamnesi visiva")
    s = lambda c: _sk("t1", c, paz_id)
    a = d.get("anamnesi_visiva", {})

    motivo = _txt("Motivo della visita", s("motivo"), a.get("motivo",""), height=80)

    st.markdown("**Sintomi riferiti:**")
    sintomi_opts = [
        "Mal di testa frontale/orbitale", "Visione doppia (diplopia)",
        "Fatica visiva (astenopia)", "Bruciore/lacrimazione",
        "Visione sfocata vicino", "Visione sfocata lontano",
        "Evitamento della lettura", "Perdita del segno durante lettura",
        "Fotofobia", "Difficolta di concentrazione",
        "Chiude un occhio per vedere meglio", "Sbatte le palpebre spesso",
        "Mal di stomaco durante lettura", "Distanza ravvicinata al testo",
    ]
    sintomi = []
    cols = st.columns(2)
    for i, s_opt in enumerate(sintomi_opts):
        with cols[i%2]:
            if st.checkbox(s_opt, value=s_opt in a.get("sintomi",[]),
                           key=_sk("t1",f"sint_{i}",paz_id)):
                sintomi.append(s_opt)

    occhiali = _radio("Occhiali attuali",
        ["No","Si - monofocali","Si - progressivi","Si - bifocali"],
        s("occhiali"), a.get("occhiali"))
    lenti = _radio("Lenti a contatto",
        ["No","Si - morbide giornaliere","Si - morbide mensili","Si - RGP","Si - ortoK"],
        s("lenti"), a.get("lenti"))
    ultima_visita = _txt("Ultima visita oculistica/optometrica",
                         s("ultima_visita"), a.get("ultima_visita",""))
    note = _txt("Note anamnesi", s("note"), a.get("note",""), height=68)

    return {"anamnesi_visiva": {
        "motivo": motivo, "sintomi": sintomi, "occhiali": occhiali,
        "lenti": lenti, "ultima_visita": ultima_visita, "note": note,
    }}


# ══ TAB 2 — ESAME OBIETTIVO ══════════════════════════════════════════

def _t2_obiettivo(paz_id, d):
    st.markdown("### Esame obiettivo")
    s = lambda c: _sk("t2", c, paz_id)
    o = d.get("esame_obiettivo", {})

    st.markdown("#### Segmento anteriore")
    c1, c2 = st.columns(2)
    with c1:
        cornea_od  = _radio("Cornea OD", ["Nella norma","Anomalia"], s("cornea_od"), o.get("cornea_od","Nella norma"))
        cam_od     = _radio("Camera anteriore OD", ["Nella norma","Anomalia"], s("cam_od"), o.get("cam_od","Nella norma"))
        crist_od   = _radio("Cristallino OD", ["Nella norma","Anomalia"], s("crist_od"), o.get("crist_od","Nella norma"))
    with c2:
        cornea_os  = _radio("Cornea OS", ["Nella norma","Anomalia"], s("cornea_os"), o.get("cornea_os","Nella norma"))
        cam_os     = _radio("Camera anteriore OS", ["Nella norma","Anomalia"], s("cam_os"), o.get("cam_os","Nella norma"))
        crist_os   = _radio("Cristallino OS", ["Nella norma","Anomalia"], s("crist_os"), o.get("crist_os","Nella norma"))

    congiuntiva = _radio("Congiuntiva / Sclera",
        ["Nella norma","Iperemia","Pterigio","Altro"],
        s("congiuntiva"), o.get("congiuntiva","Nella norma"))

    st.markdown("#### Segmento posteriore")
    c3, c4 = st.columns(2)
    with c3:
        fondo_od  = _radio("Fondo OD", ["Nella norma","Anomalia","Non valutato"], s("fondo_od"), o.get("fondo_od","Nella norma"))
        vitreo_od = _radio("Vitreo OD", ["Nella norma","Anomalia","Non valutato"], s("vitreo_od"), o.get("vitreo_od","Nella norma"))
    with c4:
        fondo_os  = _radio("Fondo OS", ["Nella norma","Anomalia","Non valutato"], s("fondo_os"), o.get("fondo_os","Nella norma"))
        vitreo_os = _radio("Vitreo OS", ["Nella norma","Anomalia","Non valutato"], s("vitreo_os"), o.get("vitreo_os","Nella norma"))

    st.markdown("#### Pressione intraoculare (IOP)")
    c5, c6 = st.columns(2)
    with c5:
        iop_od = st.number_input("IOP OD (mmHg)", min_value=0.0, max_value=60.0, step=0.5,
                                  value=float(o.get("iop_od") or 0), key=s("iop_od"))
    with c6:
        iop_os = st.number_input("IOP OS (mmHg)", min_value=0.0, max_value=60.0, step=0.5,
                                  value=float(o.get("iop_os") or 0), key=s("iop_os"))

    note_ob = _txt("Note esame obiettivo", s("note"), o.get("note",""), height=68)

    anomalie = [x for x in [cornea_od, cornea_os, cam_od, cam_os, crist_od, crist_os,
                              fondo_od, fondo_os] if x == "Anomalia"]
    iop_alta = (iop_od > 21) or (iop_os > 21)
    if anomalie or iop_alta:
        st.error(
            f"Rilevate {len(anomalie)} anomalie" +
            (" + IOP elevata" if iop_alta else "") +
            " - INVIARE A VISITA OCULISTICA APPROFONDITA"
        )

    return {"esame_obiettivo": {
        "cornea_od": cornea_od, "cornea_os": cornea_os,
        "cam_od": cam_od, "cam_os": cam_os,
        "crist_od": crist_od, "crist_os": crist_os,
        "congiuntiva": congiuntiva,
        "fondo_od": fondo_od, "fondo_os": fondo_os,
        "vitreo_od": vitreo_od, "vitreo_os": vitreo_os,
        "iop_od": iop_od, "iop_os": iop_os,
        "note": note_ob, "anomalie_n": len(anomalie), "iop_alta": iop_alta,
    }}


# ══ TAB 3 — REFRAZIONE ═══════════════════════════════════════════════

def _t3_refrazione(paz_id, d):
    st.markdown("### Refrazione")
    s = lambda c: _sk("t3", c, paz_id)
    r = d.get("refrazione", {})

    def _riga_rx(occhio, stored, prefix):
        st.markdown(f"**{occhio}**")
        c1,c2,c3,c4 = st.columns(4)
        with c1: sf  = st.number_input("SF",  value=float(stored.get("sf")  or 0), step=0.25, format="%.2f", key=s(f"sf_{prefix}"))
        with c2: cil = st.number_input("CIL", value=float(stored.get("cil") or 0), step=0.25, format="%.2f", key=s(f"cil_{prefix}"))
        with c3: ax  = st.number_input("AX",  value=int(stored.get("ax")    or 0), step=1,    key=s(f"ax_{prefix}"))
        with c4: ac  = st.text_input("Acuita'", value=stored.get("acuita",""), key=s(f"ac_{prefix}"))
        return {"sf": sf, "cil": cil, "ax": ax, "acuita": ac}

    st.markdown("#### Refrazione oggettiva")
    obj_od = _riga_rx("OD (oggettiva)", r.get("obj_od",{}), "obj_od")
    obj_os = _riga_rx("OS (oggettiva)", r.get("obj_os",{}), "obj_os")

    st.markdown("#### Refrazione soggettiva finale")
    sog_od = _riga_rx("OD (soggettiva)", r.get("sog_od",{}), "sog_od")
    sog_os = _riga_rx("OS (soggettiva)", r.get("sog_os",{}), "sog_os")

    c1, c2 = st.columns(2)
    with c1:
        add = st.number_input("ADD vicino", value=float(r.get("add") or 0), step=0.25, format="%.2f", key=s("add"))
    with c2:
        dp = st.number_input("Distanza pupillare (mm)", value=float(r.get("dp") or 63), step=0.5, format="%.1f", key=s("dp"))

    note_rx = _txt("Note refrazione", s("note_rx"), r.get("note_rx",""), height=68)

    def _f(v): return f"+{v:.2f}" if (v or 0)>=0 else f"{v:.2f}"
    st.markdown("**Anteprima prescrizione:**")
    st.code(
        f"OD: {_f(sog_od['sf'])} / {_f(sog_od['cil'])} x {sog_od['ax']} gradi - Visus {sog_od['acuita']}\n"
        f"OS: {_f(sog_os['sf'])} / {_f(sog_os['cil'])} x {sog_os['ax']} gradi - Visus {sog_os['acuita']}\n"
        f"ADD: +{add:.2f}\nDP: {dp:.1f} mm",
        language="text"
    )

    return {"refrazione": {
        "obj_od": obj_od, "obj_os": obj_os,
        "sog_od": sog_od, "sog_os": sog_os,
        "add": add, "dp": dp, "note_rx": note_rx,
    }}


# ══ TAB 4 — OCULOMOTRICITA ═══════════════════════════════════════════

def _t4_oculomotori(paz_id, d):
    st.markdown("### Funzioni oculomotorie")
    s = lambda c: _sk("t4", c, paz_id)
    o = d.get("oculomotori", {})

    scale = {}
    for k, label in [
        ("saccadi",     "Saccadi"),
        ("pursuit_or",  "Inseguimento orizzontale"),
        ("pursuit_ver", "Inseguimento verticale"),
        ("fissazione",  "Fissazione"),
        ("vro",         "Riflesso vestibolo-oculomotore"),
    ]:
        scale[k] = _scala(label, s(k), o.get(k,3))

    comp_testa = st.checkbox("Compensazione con la testa", value=o.get("comp_testa",False), key=s("comp_testa"))
    sintomi_p  = _txt("Sintomi durante pursuit/saccadi", s("sintomi"), o.get("sintomi",""))
    note       = _txt("Note oculomotori", s("note"), o.get("note",""), height=68)

    return {"oculomotori": {**scale, "comp_testa": comp_testa, "sintomi": sintomi_p, "note": note}}


# ══ TAB 5 — BINOCOLARITA E ACCOMODAZIONE ════════════════════════════

def _t5_binocolarita(paz_id, d):
    st.markdown("### Binocolarita e Accomodazione")
    s = lambda c: _sk("t5", c, paz_id)
    b = d.get("binocolarita", {})

    c1, c2 = st.columns(2)
    with c1:
        ct_vl = _radio("Cover test lontano",
            ["Orto","Esoforia","Esotropia","Exoforia","Exotropia","Iperforia","Alternante"],
            s("ct_vl"), b.get("ct_vl","Orto"))
    with c2:
        ct_vv = _radio("Cover test vicino",
            ["Orto","Esoforia","Esotropia","Exoforia","Exotropia","Iperforia","Alternante"],
            s("ct_vv"), b.get("ct_vv","Orto"))

    c3, c4 = st.columns(2)
    with c3:
        ppc = st.number_input("PPC (cm)", value=float(b.get("ppc") or 0), min_value=0.0, max_value=50.0, step=0.5, key=s("ppc"))
        st.caption("Nella norma <= 5 cm" if ppc<=5 else "Ridotta > 5 cm")
    with c4:
        stereopsi = st.number_input("Stereopsi (sec d arco)", value=int(b.get("stereopsi") or 0), min_value=0, max_value=3000, step=10, key=s("stereopsi"))

    scale_b = {}
    for k, label in [
        ("convergenza",   "Convergenza"),
        ("divergenza",    "Divergenza"),
        ("fusione",       "Fusione binoculare"),
        ("stereopsi_sc",  "Stereopsi qualitativa"),
    ]:
        scale_b[k] = _scala(label, s(k), b.get(k,3))

    st.markdown("#### Accomodazione")
    c5, c6 = st.columns(2)
    with c5:
        amp_od = st.number_input("Ampiezza acc. OD (D)", value=float(b.get("amp_acc_od") or 0), step=0.5, key=s("amp_od"))
        amp_os = st.number_input("Ampiezza acc. OS (D)", value=float(b.get("amp_acc_os") or 0), step=0.5, key=s("amp_os"))
    with c6:
        facilita = st.number_input("Facilita accomodativa (cicli/min)", value=float(b.get("facilita") or 0), step=1.0, key=s("facilita"))
        lag      = st.number_input("Lag accomodativo (D)", value=float(b.get("lag") or 0), step=0.25, key=s("lag"))

    scale_a = {}
    for k, label in [
        ("amp_acc_sc",  "Ampiezza accomodativa"),
        ("facilita_sc", "Facilita accomodativa"),
        ("lag_sc",      "Lag accomodativo"),
    ]:
        scale_a[k] = _scala(label, s(k), b.get(k,3))

    note = _txt("Note binocolarita/accomodazione", s("note"), b.get("note",""), height=68)

    return {"binocolarita": {
        "ct_vl": ct_vl, "ct_vv": ct_vv, "ppc": ppc, "stereopsi": stereopsi,
        **scale_b, "amp_acc_od": amp_od, "amp_acc_os": amp_os,
        "facilita": facilita, "lag": lag, **scale_a, "note": note,
    }}


# ══ TAB 6 — PERCEZIONE VISIVA ════════════════════════════════════════

def _t6_percezione(paz_id, d):
    st.markdown("### Percezione Visiva")
    s = lambda c: _sk("t6", c, paz_id)
    p = d.get("percezione", {})

    scale = {}
    for k, label in [
        ("disc_forma",   "Discriminazione della forma"),
        ("mem_visiva",   "Memoria visiva"),
        ("coord_ocmano", "Coordinazione occhio-mano"),
        ("fig_sfondo",   "Figura-sfondo"),
        ("closure",      "Visual closure"),
        ("costanza",     "Costanza percettiva"),
        ("pos_spazio",   "Posizione nello spazio"),
        ("rel_spaziali", "Relazioni spaziali"),
    ]:
        scale[k] = _scala(label, s(k), p.get(k,3))

    note = _txt("Note percezione visiva", s("note"), p.get("note",""), height=68)
    return {"percezione": {**scale, "note": note}}


# ══ TAB 7 — PROFILO FUNZIONALE ═══════════════════════════════════════

def _t7_profilo(paz_id, d):
    st.markdown("### Profilo Funzionale Visuo-Percettivo")

    oculo = d.get("oculomotori", {})
    bino  = d.get("binocolarita", {})
    perc  = d.get("percezione", {})

    domini = [
        ("Oculomotricita", [
            (oculo.get("saccadi",3),     "Saccadi"),
            (oculo.get("pursuit_or",3),  "Inseguimento"),
            (oculo.get("fissazione",3),  "Fissazione"),
            (oculo.get("vro",3),         "VRO"),
        ]),
        ("Binocolarita", [
            (bino.get("convergenza",3),  "Convergenza"),
            (bino.get("fusione",3),      "Fusione"),
            (bino.get("stereopsi_sc",3), "Stereopsi"),
        ]),
        ("Accomodazione", [
            (bino.get("amp_acc_sc",3),   "Ampiezza"),
            (bino.get("facilita_sc",3),  "Facilita"),
            (bino.get("lag_sc",3),       "Lag"),
        ]),
        ("Percezione visiva", [
            (perc.get("disc_forma",3),   "Discriminazione"),
            (perc.get("mem_visiva",3),   "Memoria"),
            (perc.get("coord_ocmano",3), "Coord. occhio-mano"),
            (perc.get("fig_sfondo",3),   "Figura-sfondo"),
            (perc.get("closure",3),      "Closure"),
        ]),
    ]

    tutti = []
    for nome_dom, voci in domini:
        st.markdown(f"**{nome_dom}**")
        for val, label in voci:
            col1, col2, col3 = st.columns([3,5,1])
            with col1: st.caption(label)
            with col2:
                pct = int(val/5*100)
                c = "#22c55e" if val>=4 else ("#f59e0b" if val>=2 else "#ef4444")
                st.markdown(
                    f'<div style="background:var(--color-background-secondary);border-radius:8px;height:14px">' +
                    f'<div style="width:{pct}%;height:100%;background:{c};border-radius:8px"></div></div>',
                    unsafe_allow_html=True)
            with col3:
                bc = "#dcfce7" if val>=4 else ("#fef3c7" if val>=2 else "#fee2e2")
                tc = "#166534" if val>=4 else ("#92400e" if val>=2 else "#991b1b")
                st.markdown(f'<span style="background:{bc};color:{tc};padding:2px 6px;border-radius:8px;font-size:11px">{val}/5</span>', unsafe_allow_html=True)
            tutti.append(val)
        st.markdown("")

    media = sum(tutti)/len(tutti) if tutti else 0
    cg = "#22c55e" if media>=4 else ("#f59e0b" if media>=2 else "#ef4444")
    bt = "Nella norma" if media>=4 else ("Borderline" if media>=2 else "Deficitario")
    st.markdown("---")
    st.markdown(
        f'**Indice funzionale globale:** ' +
        f'<span style="font-size:1.2rem;font-weight:600;color:{cg}">{media:.1f}/5</span> ' +
        f'&nbsp;<span style="background:{cg}22;color:{cg};padding:3px 10px;border-radius:10px;font-size:13px">{bt}</span>',
        unsafe_allow_html=True)


# ══ TAB 8 — PRESCRIZIONE ═════════════════════════════════════════════

def _t8_prescrizione(conn, paz_id, d, paziente):
    st.markdown("### Prescrizione e Relazione clinica")
    s = lambda c: _sk("t8", c, paz_id)
    rx = d.get("refrazione", {})
    ob = d.get("esame_obiettivo", {})
    prof = _professionista_label()
    cog  = paziente.get("Cognome","") if isinstance(paziente, dict) else ""
    nom  = paziente.get("Nome","")    if isinstance(paziente, dict) else ""
    dn   = paziente.get("Data_Nascita","") if isinstance(paziente, dict) else ""

    diagnosi = _txt("Diagnosi visiva", s("diagnosi"), d.get("diagnosi",""), height=80)
    racc     = _txt("Raccomandazioni", s("racc"), d.get("raccomandazioni",""), height=80)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Genera Ricetta PDF", key=s("btn_rx"), type="primary"):
            _genera_ricetta_pdf(paz_id, cog, nom, dn, rx, prof)
    with c2:
        if ob.get("anomalie_n",0) > 0 or ob.get("iop_alta"):
            if st.button("Lettera invio oculista", key=s("btn_inv")):
                _genera_lettera_invio(paz_id, cog, nom, dn, ob, prof)
    with c3:
        if st.button("Relazione completa PDF", key=s("btn_rel")):
            _genera_relazione(paz_id, cog, nom, dn, d, prof)

    return {"diagnosi": diagnosi, "raccomandazioni": racc}


def _genera_ricetta_pdf(paz_id, cognome, nome, dn, rx, prof):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=56, leftMargin=56, topMargin=56, bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t", fontSize=16, fontName="Helvetica-Bold", textColor=VERDE, alignment=TA_CENTER, spaceAfter=4)
        sS = ParagraphStyle("s", fontSize=9,  fontName="Helvetica", textColor=colors.gray, alignment=TA_CENTER, spaceAfter=2)
        sH = ParagraphStyle("h", fontSize=12, fontName="Helvetica-Bold", textColor=VERDE, spaceAfter=4, spaceBefore=8)
        sB = ParagraphStyle("b", fontSize=10, fontName="Helvetica", spaceAfter=4, leading=14)

        def _f(v): return f"+{v:.2f}" if (v or 0)>=0 else f"{v:.2f}"
        sod = rx.get("sog_od",{}); sos = rx.get("sog_os",{})

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Paragraph(f"Professionista: {prof}", sS),
            Spacer(1,15),
            HRFlowable(width="100%", thickness=1, color=VERDE),
            Spacer(1,10),
            Paragraph("PRESCRIZIONE OTTICA", sH),
            Paragraph(f"Paziente: <b>{cognome} {nome}</b> | Data nascita: {dn} | Data: {datetime.date.today().strftime('%d/%m/%Y')}", sB),
            Spacer(1,12),
        ]
        tbl = Table([
            ["","SF","CIL","AX","Acuita"],
            ["OD", _f(sod.get("sf")), _f(sod.get("cil")), str(sod.get("ax") or 0)+"g", sod.get("acuita","—")],
            ["OS", _f(sos.get("sf")), _f(sos.get("cil")), str(sos.get("ax") or 0)+"g", sos.get("acuita","—")],
        ], colWidths=[50,70,70,60,80])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),VERDE),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("FONTSIZE",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#D3D1C7")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F1EFE8")]),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(tbl)
        if rx.get("add"):
            story.append(Spacer(1,6))
            story.append(Paragraph(f"ADD vicino: +{rx['add']:.2f} D", sB))
        if rx.get("dp"):
            story.append(Paragraph(f"Distanza pupillare: {rx['dp']:.1f} mm", sB))
        story.append(Spacer(1,30))
        story.append(Paragraph(f"Firma: _______________________  {prof}", sB))
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Ricetta PDF", data=buf,
            file_name=f"ricetta_{cognome}_{nome}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_rx_{paz_id}")
    except Exception as e:
        st.error(f"Errore generazione ricetta: {e}")


def _genera_lettera_invio(paz_id, cognome, nome, dn, ob, prof):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=56, leftMargin=56, topMargin=56, bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t", fontSize=16, fontName="Helvetica-Bold", textColor=VERDE, alignment=TA_CENTER, spaceAfter=4)
        sS = ParagraphStyle("s", fontSize=9,  fontName="Helvetica", textColor=colors.gray, alignment=TA_CENTER, spaceAfter=2)
        sB = ParagraphStyle("b", fontSize=10, fontName="Helvetica", spaceAfter=6, leading=16)

        anom = []
        for campo, label in [("cornea_od","Cornea OD"),("cornea_os","Cornea OS"),
                               ("fondo_od","Fondo OD"),("fondo_os","Fondo OS"),
                               ("crist_od","Cristallino OD"),("crist_os","Cristallino OS")]:
            if ob.get(campo) == "Anomalia": anom.append(label)
        if ob.get("iop_alta"): anom.append(f"IOP elevata (OD:{ob.get('iop_od')} / OS:{ob.get('iop_os')} mmHg)")

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Spacer(1,15), HRFlowable(width="100%", thickness=1, color=VERDE), Spacer(1,12),
            Paragraph("LETTERA DI INVIO A VISITA OCULISTICA", sB), Spacer(1,8),
            Paragraph(f"Egregio Collega,<br/><br/>Le invio in visita il/la paziente <b>{cognome} {nome}</b> "
                      f"(nato/a il {dn}), per approfondimento oculistico a seguito della nostra "
                      f"valutazione visuo-percettiva.<br/><br/>Anomalie rilevate:", sB),
        ]
        for a in anom:
            story.append(Paragraph(f"- {a}", sB))
        story.append(Spacer(1,8))
        story.append(Paragraph(
            f"Si richiede visita oculistica completa.<br/><br/>"
            f"{datetime.date.today().strftime('%d/%m/%Y')}<br/><br/>"
            f"<b>{prof}</b><br/>The Organism Studio", sB))
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Lettera Invio PDF", data=buf,
            file_name=f"invio_oculista_{cognome}_{nome}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_lettera_{paz_id}")
    except Exception as e:
        st.error(f"Errore generazione lettera: {e}")


def _genera_relazione(paz_id, cognome, nome, dn, d, prof):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=56, leftMargin=56, topMargin=56, bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t", fontSize=16, fontName="Helvetica-Bold", textColor=VERDE, alignment=TA_CENTER, spaceAfter=4)
        sS = ParagraphStyle("s", fontSize=9,  fontName="Helvetica", textColor=colors.gray, alignment=TA_CENTER)
        sH = ParagraphStyle("h", fontSize=12, fontName="Helvetica-Bold", textColor=VERDE, spaceAfter=4, spaceBefore=8)
        sB = ParagraphStyle("b", fontSize=10, fontName="Helvetica", spaceAfter=4, leading=15)

        rx   = d.get("refrazione", {})
        bino = d.get("binocolarita", {})
        ob   = d.get("esame_obiettivo", {})
        diag = d.get("diagnosi","")
        racc = d.get("raccomandazioni","")

        def _f(v): return f"+{v:.2f}" if (v or 0)>=0 else f"{v:.2f}"
        sod = rx.get("sog_od",{}); sos = rx.get("sog_os",{})

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Paragraph(f"Professionista: {prof}", sS),
            Spacer(1,15), HRFlowable(width="100%", thickness=1.5, color=VERDE), Spacer(1,8),
            Paragraph("RELAZIONE CLINICA VISUO-PERCETTIVA", sH),
            Paragraph(f"Paziente: <b>{cognome} {nome}</b> | Nato/a: {dn} | Visita: {datetime.date.today().strftime('%d/%m/%Y')}", sB),
            Spacer(1,10),
            Paragraph("1. Refrazione", sH),
            Paragraph(f"OD: {_f(sod.get('sf'))} / {_f(sod.get('cil'))} x {sod.get('ax',0)} gradi - Visus {sod.get('acuita','nd')}<br/>"
                      f"OS: {_f(sos.get('sf'))} / {_f(sos.get('cil'))} x {sos.get('ax',0)} gradi - Visus {sos.get('acuita','nd')}", sB),
            Paragraph("2. Binocolarita e accomodazione", sH),
            Paragraph(f"Cover test lontano: {bino.get('ct_vl','nd')} | Cover test vicino: {bino.get('ct_vv','nd')}<br/>"
                      f"PPC: {bino.get('ppc','nd')} cm | Stereopsi: {bino.get('stereopsi','nd')} sec d arco", sB),
            Paragraph("3. Esame obiettivo", sH),
            Paragraph(f"IOP OD: {ob.get('iop_od','nd')} / OS: {ob.get('iop_os','nd')} mmHg | "
                      f"Anomalie: {'nessuna' if not ob.get('anomalie_n') else str(ob.get('anomalie_n'))+' (vedi lettera)' }", sB),
        ]
        if diag:
            story += [Paragraph("4. Diagnosi", sH), Paragraph(diag, sB)]
        if racc:
            story += [Paragraph("5. Raccomandazioni", sH), Paragraph(racc, sB)]

        story += [
            Spacer(1,30), HRFlowable(width="100%", thickness=0.5, color=colors.gray), Spacer(1,8),
            Paragraph(f"Firma: _______________________  {prof}<br/>The Organism Studio - {datetime.date.today().strftime('%d/%m/%Y')}", sB),
        ]
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Relazione PDF", data=buf,
            file_name=f"relazione_vvp_{cognome}_{nome}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_rel_{paz_id}")
    except Exception as e:
        st.error(f"Errore generazione relazione: {e}")


# ══ ENTRY POINT ══════════════════════════════════════════════════════

def render_valutazione_visuo_percettiva(conn, paz_id, paziente=None):
    st.subheader("Valutazione Visuo-Percettiva")
    st.caption("Optometria comportamentale | Refrazione | Esame obiettivo | Profilo funzionale")

    stored = _carica(conn, paz_id)
    dati   = dict(stored)

    tabs = st.tabs([
        "1. Anamnesi visiva",
        "2. Esame obiettivo",
        "3. Refrazione",
        "4. Oculomotricita",
        "5. Binocolarita",
        "6. Percezione visiva",
        "7. Profilo funzionale",
        "8. Prescrizione",
    ])

    with tabs[0]:
        dati.update(_t1_anamnesi(paz_id, stored))
        if st.button("Salva anamnesi visiva", key=f"sv_t1_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[1]:
        dati.update(_t2_obiettivo(paz_id, stored))
        if st.button("Salva esame obiettivo", key=f"sv_t2_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[2]:
        dati.update(_t3_refrazione(paz_id, stored))
        if st.button("Salva refrazione", key=f"sv_t3_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[3]:
        dati.update(_t4_oculomotori(paz_id, stored))
        if st.button("Salva oculomotricita", key=f"sv_t4_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[4]:
        dati.update(_t5_binocolarita(paz_id, stored))
        if st.button("Salva binocolarita", key=f"sv_t5_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[5]:
        dati.update(_t6_percezione(paz_id, stored))
        if st.button("Salva percezione visiva", key=f"sv_t6_{paz_id}"):
            _salva_visita(conn, paz_id, dati)

    with tabs[6]:
        _t7_profilo(paz_id, dati)

    with tabs[7]:
        extra = _t8_prescrizione(conn, paz_id, dati, paziente or {})
        dati.update(extra)
        if st.button("Salva diagnosi e raccomandazioni", key=f"sv_t8_{paz_id}", type="primary"):
            _salva_visita(conn, paz_id, dati)
