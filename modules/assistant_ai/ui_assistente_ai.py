from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Optional
import streamlit as st

from .ai_client import generate_relazione_json
from .prompt_templates import PROFESSIONALI, build_system_instructions, build_user_prompt, relazione_schema
from .pdf_relazione_ai import build_pdf_relazione_ai_a4

def ui_assistente_ai(get_conn, fetch_pazienti_for_select, get_anamnesi_fn, get_seduta_fn, list_anamnesi_fn, list_sedute_fn):
    """
    get_conn: funzione conn DB (la tua get_connection)
    fetch_pazienti_for_select: funzione già presente nel gestionale (per select pazienti)
    get_anamnesi_fn/get_seduta_fn/list_*: funzioni del modulo osteopatia (o wrapper)

    Questa UI:
    - seleziona paziente
    - seleziona professionista
    - seleziona periodo + anamnesi
    - legge i campi dal DB (solo paziente selezionato)
    - genera JSON relazione con Responses API
    - stampa PDF A4
    """
    st.subheader("🤖 Assistente IA — Relazioni personalizzate")

    # Config modello
    model = st.text_input("Modello (OpenAI)", value="gpt-5", help="Puoi cambiare modello se necessario.")
    professionista = st.selectbox("Professionista", PROFESSIONALI, index=0)

    anon = st.checkbox("Anonimizza (non inviare nome/cognome al modello)", value=True)
    note_libere = st.text_area("Istruzioni extra (facoltative)", height=90, placeholder="Es. tono più tecnico, includi obiettivi SMART, ecc.")

    conn = get_conn()
    paz_list, paz_table, paz_colmap = fetch_pazienti_for_select(conn)
    if not paz_list:
        st.error("Nessun paziente trovato.")
        return

    def _label(p):
        pid, cogn, nome, dn, scuola, eta = p
        dn_s = dn or ""
        extra = ""
        if eta: extra += f" • {eta} anni"
        if scuola: extra += f" • {scuola}"
        return f"{cogn} {nome} (ID {pid}) {dn_s}{extra}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)
    try:
        paziente_id = int(sel[0])
        cognome = sel[1] if len(sel) > 1 else ""
        nome = sel[2] if len(sel) > 2 else ""
    except Exception:
        st.error("Impossibile determinare paziente.")
        return

    paziente_label = f"{cognome} {nome}".strip() or f"Paziente ID {paziente_id}"
    paziente_label_for_ai = f"Paziente ID {paziente_id}" if anon else paziente_label

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        date_from = st.date_input("Da", value=dt.date.today() - dt.timedelta(days=90))
    with c2:
        date_to = st.date_input("A", value=dt.date.today())
    with c3:
        include_deleted = st.checkbox("Includi record eliminati", value=False)

    anam_list = list_anamnesi_fn(conn, paziente_id, include_deleted=include_deleted)
    anam_options = ["(nessuna)"] + [f"#{a['id']} — {a.get('data_anamnesi')}" for a in anam_list]
    anam_sel = st.selectbox("Anamnesi di riferimento", anam_options)

    anam_obj = None
    if anam_sel != "(nessuna)":
        try:
            anam_id = int(anam_sel.split("#")[1].split("—")[0].strip())
            anam_obj = get_anamnesi_fn(conn, anam_id)
        except Exception:
            anam_obj = None

    # Sedute nel periodo
    sed_brief = list_sedute_fn(conn, paziente_id, include_deleted=include_deleted)
    sedute: List[Dict[str, Any]] = []
    for s in sed_brief:
        sid = s["id"]
        full = get_seduta_fn(conn, sid)
        if not full:
            continue
        ds = full.get("data_seduta")
        try:
            if isinstance(ds, str):
                ds_date = dt.date.fromisoformat(ds)
            else:
                ds_date = ds
            if ds_date and date_from <= ds_date <= date_to:
                sedute.append(full)
        except Exception:
            sedute.append(full)

    # Contesto "minimo" (puoi estenderlo con altri moduli)
    contesto = {
        "fonte": "Gestionale The Organism",
        "modulo": "Osteopatia",
        "nota_privacy": "Dati limitati al paziente selezionato e al periodo richiesto."
    }

    st.markdown("### Anteprima dati inviati all'IA")
    with st.expander("Mostra JSON (debug)"):
        st.json({
            "professionista": professionista,
            "paziente": paziente_label_for_ai,
            "periodo": f"{date_from} → {date_to}",
            "anamnesi": anam_obj,
            "sedute_count": len(sedute),
            "sedute_first": sedute[0] if sedute else None,
        })

    st.markdown("---")
    if st.button("✨ Genera relazione con IA"):
        try:
            system = build_system_instructions(professionista)
            prompt = build_user_prompt(
                professionista=professionista,
                paziente_label=paziente_label_for_ai,
                contesto=contesto,
                anamnesi=anam_obj,
                sedute=sedute,
                note_libere=note_libere,
            )
            schema = relazione_schema()
            rel = generate_relazione_json(model=model, system_instructions=system, user_prompt=prompt, response_schema=schema)
        except Exception as e:
            st.error("Errore durante la generazione IA. Verifica OPENAI_API_KEY e dipendenze.")
            st.exception(e)
            return

        st.success("Relazione generata.")
        st.json(rel)

        pdf_bytes = build_pdf_relazione_ai_a4(rel)
        st.download_button(
            "⬇️ Scarica Relazione IA (A4)",
            data=pdf_bytes,
            file_name=f"relazione_ai_{professionista.replace('/','_')}_{paziente_id}_{date_from}_{date_to}.pdf",
            mime="application/pdf"
        )
