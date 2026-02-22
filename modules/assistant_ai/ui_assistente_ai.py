from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List
import streamlit as st

from .ai_client import generate_relazione_json
from .prompt_templates import PROFESSIONALI, build_system_instructions, build_user_prompt, relazione_schema
from .pdf_relazione_ai import build_pdf_relazione_ai_a4
from .gather_context import AVAILABLE_SOURCES, gather_dataset

def ui_assistente_ai(get_conn, fetch_pazienti_for_select):
    st.subheader("🤖 Assistente IA — Relazioni personalizzate (multi-modulo)")

    model = st.text_input("Modello", value="gpt-5")
    professionista = st.selectbox("Professionista", PROFESSIONALI, index=0)
    custom_profile = ""
    if professionista == "Altro (custom)":
        custom_profile = st.text_area("Profilo custom (tono, sezioni, focus)", height=110)

    anon = st.checkbox("Anonimizza (non inviare nome/cognome)", value=True)
    note_libere = st.text_area("Istruzioni extra (facoltative)", height=90)

    conn = get_conn()
    paz_list, _, _ = fetch_pazienti_for_select(conn)
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
    paziente_id = int(sel[0])
    cognome = sel[1] if len(sel) > 1 else ""
    nome = sel[2] if len(sel) > 2 else ""
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

    st.markdown("### Sorgenti dati da includere")
    src_labels = [label for (label, key) in AVAILABLE_SOURCES]
    src_defaults = [True if key == "osteopatia" else False for (label, key) in AVAILABLE_SOURCES]
    chosen = []
    for (label, key), default in zip(AVAILABLE_SOURCES, src_defaults):
        if st.checkbox(label, value=default, key=f"src_{key}"):
            chosen.append(key)
    if not chosen:
        st.warning("Seleziona almeno una sorgente dati (es. Osteopatia).")
        return

    dataset = gather_dataset(conn, paziente_id, date_from, date_to, chosen, include_deleted=include_deleted)

    with st.expander("Mostra dati inviati all'IA (debug)"):
        st.json(dataset)

    st.markdown("---")
    if st.button("✨ Genera relazione con IA"):
        try:
            system = build_system_instructions(professionista, custom_profile=custom_profile)
            prompt = build_user_prompt(
                professionista=professionista,
                paziente_label=paziente_label_for_ai,
                periodo=f"{date_from} → {date_to}",
                dataset=dataset,
                note_libere=note_libere,
            )
            rel = generate_relazione_json(
                model=model,
                system_instructions=system,
                user_prompt=prompt,
                response_schema=relazione_schema()
            )
        except Exception as e:
            st.error("Errore IA. Verifica OPENAI_API_KEY e che 'openai' sia installato in requirements.txt.")
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
