# -*- coding: utf-8 -*-
"""
Relazione Clinica - The Organism
Genera relazioni specifiche e globali con AI.
"""
from __future__ import annotations
import json, datetime
import streamlit as st


def _get_prof():
    u = st.session_state.get("user") or {}
    profilo = u.get("profilo",{}) or {}
    titolo = profilo.get("titolo","").strip()
    nome   = profilo.get("nome","").strip()
    if nome:
        return f"{titolo} {nome}".strip()
    return u.get("display_name","") or u.get("username","The Organism")

def _get_spec():
    u = st.session_state.get("user") or {}
    profilo = u.get("profilo",{}) or {}
    return profilo.get("specializzazioni","Optometrista Comportamentale")

def _carica_dati_paziente(conn, paz_id: int) -> dict:
    """Raccoglie tutti i dati clinici disponibili per il paziente."""
    dati = {}
    try:
        cur = conn.cursor()
        # Anagrafica
        cur.execute("SELECT * FROM Pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if row:
            dati["anagrafica"] = dict(zip(
                [d[0] for d in cur.description], row
            )) if not isinstance(row, dict) else row

        # Ultima anamnesi
        cur.execute(
            "SELECT anamnesi_json FROM anamnesi "
            "WHERE paziente_id=%s ORDER BY created_at DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if row:
            raw = row["anamnesi_json"] if isinstance(row,dict) else row[0]
            if raw:
                dati["anamnesi"] = raw if isinstance(raw,dict) else json.loads(raw)

        # Ultima valutazione visiva
        cur.execute(
            "SELECT visita_json FROM valutazioni_visive "
            "WHERE paziente_id=%s ORDER BY id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if row:
            raw = row["visita_json"] if isinstance(row,dict) else row[0]
            if raw:
                dati["visita_visiva"] = raw if isinstance(raw,dict) else json.loads(raw)

        # Ultima visita PNEV
        cur.execute(
            "SELECT pnev_summary, pnev_json FROM anamnesi "
            "WHERE paziente_id=%s AND pnev_summary IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if row:
            dati["pnev_summary"] = (row["pnev_summary"] if isinstance(row,dict) else row[0]) or ""
            raw = (row["pnev_json"] if isinstance(row,dict) else row[1]) or {}
            dati["pnev_json"] = raw if isinstance(raw,dict) else json.loads(raw or "{}")

    except Exception as e:
        st.caption(f"Attenzione dati parziali: {e}")

    return dati


def _ai_genera(prompt: str) -> str:
    """Chiama OpenAI per generare il testo della relazione."""
    try:
        import openai, streamlit as _st
        api_key = (
            _st.secrets.get("OPENAI_API_KEY","") or
            _st.secrets.get("db",{}).get("OPENAI_API_KEY","")
        )
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[{"role":"user","content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Errore AI: {e}]"


def _build_prompt_specifica(tipo: str, dati: dict, prof: str, spec: str) -> str:
    anag = dati.get("anamnesi",{})
    visiva = dati.get("visita_visiva",{})
    paz = dati.get("anagrafica",{})
    nome_paz = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn = paz.get("Data_Nascita","")

    if tipo == "Optometrica":
        sez_a = visiva.get("sez_a",{})
        sez_b = visiva.get("sez_b",{})
        sez_c = visiva.get("sez_c",{})
        sez_d = visiva.get("sez_d",{})
        return f"""Sei {prof}, {spec}.
Genera una relazione clinica optometrico-comportamentale professionale in italiano per:
Paziente: {nome_paz}, nato/a il {dn}

DATI VALUTAZIONE VISIVO-PERCETTIVA:
Refrazione soggettiva OD: {sez_a.get("rs_od",{})}
Refrazione soggettiva OS: {sez_a.get("rs_os",{})}
ADD vicino: {sez_a.get("add_v","")} ADD intermedia: {sez_a.get("add_i","")}
Cover test lontano: {sez_b.get("ct_l","")} vicino: {sez_b.get("ct_v","")}
PPC: {sez_b.get("ppc_acc_rot","")} / {sez_b.get("ppc_acc_rec","")} cm
AC/A: {sez_b.get("aca","")}
Worth lontano: {sez_b.get("worth_l","")} vicino: {sez_b.get("worth_v","")}
Randot: {sez_b.get("randot","")} sec
Push-Up OD: {sez_c.get("pu_od","")} OS: {sez_c.get("pu_os","")}
MEM OD: {sez_c.get("mem_od","")} OS: {sez_c.get("mem_os","")}
NSUCO saccadi H: {sez_d.get("ns_or_ab","")} V: {sez_d.get("ns_ver_ab","")}
Diagnosi inserita: {visiva.get("sez_g",{}).get("diag","")}
Piano terapeutico inserito: {visiva.get("sez_g",{}).get("piano","")}

Struttura la relazione con:
1. Dati identificativi
2. Motivo della valutazione
3. Esame optometrico (refrazione, binocolarita, accomodazione, oculomotricita)
4. Diagnosi funzionale visiva
5. Piano terapeutico consigliato
6. Conclusioni

Usa un linguaggio professionale ma comprensibile. Non inventare dati non presenti."""

    elif tipo == "Neuropsicologica":
        pnev = dati.get("pnev_summary","")
        return f"""Sei {prof}, {spec}.
Genera una relazione neuropsicologica professionale in italiano per:
Paziente: {nome_paz}, nato/a il {dn}

PROFILO PNEV:
{pnev or "Dati PNEV non disponibili"}

Struttura la relazione con:
1. Dati identificativi
2. Motivo dell invio
3. Strumenti utilizzati
4. Profilo neuropsicologico emerso
5. Conclusioni e raccomandazioni

Usa un linguaggio professionale."""

    return f"Genera una relazione clinica {tipo} per {nome_paz}."


def _build_prompt_globale(dati: dict, ipotesi: str, piano: str, prof: str, spec: str) -> str:
    paz = dati.get("anagrafica",{})
    nome_paz = f"{paz.get('Cognome','')} {paz.get('Nome','')}".strip()
    dn = paz.get("Data_Nascita","")
    pnev = dati.get("pnev_summary","")
    visiva = dati.get("visita_visiva",{})
    sez_g = visiva.get("sez_g",{})

    return f"""Sei {prof}, {spec}.
Genera una relazione clinica multidisciplinare globale professionale in italiano per:
Paziente: {nome_paz}, nato/a il {dn}
Data: {datetime.date.today().strftime("%d/%m/%Y")}

PROFILO PNEV (questionario genitore/insegnante):
{pnev or "Non disponibile"}

VALUTAZIONE VISUO-PERCETTIVA:
Diagnosi visiva: {sez_g.get("diag","Non disponibile")}
Piano visivo: {sez_g.get("piano","Non disponibile")}

IPOTESI DIAGNOSTICA (inserita dal clinico):
{ipotesi or "Non specificata"}

PIANO TERAPEUTICO (inserito dal clinico):
{piano or "Non specificato"}

Struttura la relazione con:
1. Dati identificativi e motivo dell invio
2. Strumenti e metodi di valutazione utilizzati
3. Profilo funzionale integrato (visivo, neuropsicologico, comportamentale)
4. Ipotesi diagnostica integrata
5. Piano terapeutico multimodale proposto
6. Raccomandazioni per famiglia e scuola
7. Conclusioni e follow-up

Usa un linguaggio professionale ma accessibile anche ai genitori."""


def _pdf_relazione(testo: str, paziente: str, data: str, prof: str, spec: str, titolo_doc: str) -> bytes:
    try:
        from modules.pdf_templates import genera_carta_intestata
        return genera_carta_intestata(
            professionista=prof,
            titolo=spec,
            paziente=paziente,
            data=data,
            titolo_doc=titolo_doc,
            corpo_testo=testo,
        )
    except Exception as e:
        st.error(f"Errore PDF: {e}")
        return b""


def render_relazione_clinica(conn) -> None:
    st.subheader("Relazione Clinica")
    st.caption("Genera relazioni specifiche o globali basate sui dati inseriti")

    # Selettore paziente
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome, Data_Nascita FROM Pazienti "
            "WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' ORDER BY Cognome, Nome"
        )
        pazienti = cur.fetchall() or []
    except Exception as e:
        st.error(f"Errore caricamento pazienti: {e}")
        return

    if not pazienti:
        st.info("Nessun paziente registrato.")
        return

    def _label(r):
        if isinstance(r, dict):
            return f"{r.get('Cognome','')} {r.get('Nome','')}"
        return f"{r[1]} {r[2]}"

    def _get_id(r):
        return r["id"] if isinstance(r, dict) else r[0]

    col1, col2 = st.columns([2,1])
    with col1:
        sel = st.selectbox("Paziente", pazienti,
                           format_func=_label, key="rel_paz_sel")
    paz_id = _get_id(sel)
    paz_label = _label(sel)

    if isinstance(sel, dict):
        dn = sel.get("Data_Nascita","")
    else:
        dn = sel[3] if len(sel)>3 else ""

    try:
        dn_fmt = datetime.date.fromisoformat(str(dn)[:10]).strftime("%d/%m/%Y")
    except Exception:
        dn_fmt = str(dn)

    paz_str = f"{paz_label}  |  Nato/a: {dn_fmt}"

    with col2:
        data_vis = st.date_input("Data relazione",
                                  value=datetime.date.today(),
                                  key="rel_data")
    data_str = data_vis.strftime("%d/%m/%Y")

    # Carica dati
    with st.spinner("Carico dati clinici..."):
        dati = _carica_dati_paziente(conn, paz_id)

    # Indicatore dati disponibili
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Anamnesi", "✅" if dati.get("anamnesi") else "❌")
    with col_b:
        st.metric("Valutazione visiva", "✅" if dati.get("visita_visiva") else "❌")
    with col_c:
        st.metric("PNEV", "✅" if dati.get("pnev_summary") else "❌")

    st.markdown("---")

    tab_spec, tab_glob = st.tabs(["📋 Relazione specifica", "🌐 Relazione globale"])

    prof = _get_prof()
    spec = _get_spec()

    # ── TAB SPECIFICA ─────────────────────────────────────────────────
    with tab_spec:
        st.markdown("#### Seleziona area")
        tipo = st.radio("Tipo relazione", [
            "Optometrica",
            "Neuropsicologica",
            "Uditiva",
        ], horizontal=True, key="rel_tipo")

        testo_spec = st.session_state.get(f"rel_testo_spec_{paz_id}", "")

        if st.button("🤖 Genera con AI", key="rel_btn_spec", type="primary"):
            if tipo in ("Uditiva",):
                st.info("Relazione uditiva in arrivo — per ora usa il campo manuale.")
            else:
                with st.spinner("L AI sta generando la relazione..."):
                    prompt = _build_prompt_specifica(tipo, dati, prof, spec)
                    testo_spec = _ai_genera(prompt)
                    st.session_state[f"rel_testo_spec_{paz_id}"] = testo_spec

        testo_spec = st.text_area(
            "Testo relazione (modificabile)",
            value=testo_spec,
            height=400,
            key=f"rel_ta_spec_{paz_id}"
        )
        st.session_state[f"rel_testo_spec_{paz_id}"] = testo_spec

        if testo_spec:
            titolo_doc = f"RELAZIONE CLINICA {tipo.upper()}"
            pdf_bytes = _pdf_relazione(testo_spec, paz_str, data_str,
                                        prof, spec, titolo_doc)
            if pdf_bytes:
                st.download_button(
                    f"📥 Scarica PDF — Relazione {tipo}",
                    data=pdf_bytes,
                    file_name=f"relazione_{tipo.lower()}_{paz_label.replace(' ','_')}_{data_vis}.pdf",
                    mime="application/pdf",
                    key=f"rel_dl_spec_{paz_id}",
                    type="primary"
                )

    # ── TAB GLOBALE ───────────────────────────────────────────────────
    with tab_glob:
        st.markdown("#### Ipotesi diagnostica e piano terapeutico")
        st.caption("Puoi inserire manualmente o lasciare che l AI li generi dai dati")

        ipotesi = st.text_area(
            "Ipotesi diagnostica integrata",
            value=st.session_state.get(f"rel_ipotesi_{paz_id}",""),
            height=120,
            placeholder="Es: Profilo compatibile con disturbo dell elaborazione visiva associato a difficolta attentive...",
            key=f"rel_ipotesi_ta_{paz_id}"
        )
        piano = st.text_area(
            "Piano terapeutico multimodale",
            value=st.session_state.get(f"rel_piano_{paz_id}",""),
            height=120,
            placeholder="Es: Vision therapy 1 seduta/settimana per 6 mesi + stimolazione uditiva Hipérion...",
            key=f"rel_piano_ta_{paz_id}"
        )

        testo_glob = st.session_state.get(f"rel_testo_glob_{paz_id}", "")

        if st.button("🤖 Genera relazione globale con AI",
                      key="rel_btn_glob", type="primary"):
            with st.spinner("L AI sta integrando tutti i dati..."):
                prompt = _build_prompt_globale(dati, ipotesi, piano, prof, spec)
                testo_glob = _ai_genera(prompt)
                st.session_state[f"rel_testo_glob_{paz_id}"] = testo_glob

        testo_glob = st.text_area(
            "Testo relazione globale (modificabile)",
            value=testo_glob,
            height=500,
            key=f"rel_ta_glob_{paz_id}"
        )
        st.session_state[f"rel_testo_glob_{paz_id}"] = testo_glob

        if testo_glob:
            pdf_bytes = _pdf_relazione(
                testo_glob, paz_str, data_str, prof, spec,
                "RELAZIONE CLINICA MULTIDISCIPLINARE"
            )
            if pdf_bytes:
                st.download_button(
                    "📥 Scarica PDF — Relazione Globale",
                    data=pdf_bytes,
                    file_name=f"relazione_globale_{paz_label.replace(' ','_')}_{data_vis}.pdf",
                    mime="application/pdf",
                    key=f"rel_dl_glob_{paz_id}",
                    type="primary"
                )
