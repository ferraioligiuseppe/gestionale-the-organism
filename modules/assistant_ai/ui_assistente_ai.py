from __future__ import annotations
import datetime as dt
import json
from typing import Any, Dict, List
import streamlit as st

from .ai_client import generate_relazione_json
from .prompt_templates import PROFESSIONALI, build_system_instructions, build_user_prompt, relazione_schema
from .pdf_relazione_ai import build_pdf_relazione_ai_a4
from .gather_context import AVAILABLE_SOURCES, gather_dataset


def _salva_relazione(conn, paziente_id, rel, pdf_bytes, professionista, fonti, stato="bozza"):
    cur = conn.cursor()
    titolo = rel.get("titolo", f"Relazione {professionista}")
    contenuto = json.dumps(rel, ensure_ascii=False)
    fonte_str = ", ".join(fonti)
    for ph, ret in [("%s", " RETURNING id"), ("?", "")]:
        try:
            cur.execute(f"""
                INSERT INTO relazioni_cliniche
                  (paziente_id, tipo, titolo, data_relazione, docx_path, pdf_path,
                   stato, contenuto_json, pdf_bytes, professionista, fonte_dati, created_at)
                VALUES ({ph},{ph},{ph},{ph},'','',{ph},{ph},{ph},{ph},{ph}, NOW(){ret})
            """, (paziente_id, professionista, titolo, dt.date.today().isoformat(),
                  stato, contenuto, pdf_bytes, professionista, fonte_str))
            if ret:
                row = cur.fetchone()
                conn.commit()
                return int(row[0]) if row else 0
            conn.commit()
            return getattr(cur, 'lastrowid', 0) or 0
        except Exception:
            try: conn.rollback()
            except Exception: pass
    return 0


def _aggiorna_stato(conn, rel_id, nuovo_stato):
    cur = conn.cursor()
    now = dt.datetime.now().isoformat()
    for ph in ["%s", "?"]:
        try:
            cur.execute(
                f"UPDATE relazioni_cliniche SET stato={ph}, approvata_il={ph} WHERE id={ph}",
                (nuovo_stato, now if nuovo_stato == "approvata" else None, rel_id)
            )
            conn.commit(); return
        except Exception:
            try: conn.rollback()
            except Exception: pass


def _carica_relazioni(conn, paziente_id):
    cur = conn.cursor()
    for ph in ["%s", "?"]:
        try:
            cur.execute(f"""
                SELECT id, tipo, titolo, data_relazione, stato, professionista, fonte_dati, created_at
                FROM relazioni_cliniche WHERE paziente_id={ph} ORDER BY created_at DESC LIMIT 50
            """, (paziente_id,))
            rows = cur.fetchall()
            return [{"id":r[0],"tipo":r[1],"titolo":r[2],"data":str(r[3]),
                     "stato":r[4] or "bozza","professionista":r[5],"fonti":r[6],"ts":str(r[7])} for r in rows]
        except Exception: pass
    return []


def _carica_detail(conn, rel_id):
    cur = conn.cursor()
    for ph in ["%s", "?"]:
        try:
            cur.execute(f"""
                SELECT id, titolo, stato, contenuto_json, pdf_bytes, professionista
                FROM relazioni_cliniche WHERE id={ph}
            """, (rel_id,))
            r = cur.fetchone()
            if r:
                return {"id":r[0],"titolo":r[1],"stato":r[2],
                        "contenuto":json.loads(r[3]) if r[3] else {},
                        "pdf_bytes":bytes(r[4]) if r[4] else None,
                        "professionista":r[5]}
        except Exception: pass
    return {}


def ui_assistente_ai(get_conn, fetch_pazienti_for_select):
    st.subheader("🤖 Assistente IA — Relazioni Cliniche")
    conn = get_conn()

    try:
        from modules.app_core import _ensure_relazioni_cliniche_table
        _ensure_relazioni_cliniche_table(conn)
    except Exception: pass

    paz_list, _, _ = fetch_pazienti_for_select(conn)
    if not paz_list:
        st.error("Nessun paziente trovato."); return

    def _label(p):
        return f"{p[1]} {p[2]} (ID {p[0]})" + (f" • {p[5]} anni" if p[5] else "")

    sel = st.selectbox("Paziente", paz_list, format_func=_label)
    paz_id = int(sel[0])
    paz_nome = f"{sel[1]} {sel[2]}".strip()

    tab_gen, tab_stor = st.tabs(["✨ Genera relazione", "📋 Storico"])

    # ── GENERA ───────────────────────────────────────────────────────────────
    with tab_gen:
        c1, c2 = st.columns(2)
        with c1: prof = st.selectbox("Profilo", PROFESSIONALI)
        with c2: model = st.selectbox("Modello AI",
                                       ["claude-sonnet-4-20250514","gpt-4o","gpt-4o-mini"])

        custom = ""
        if prof == "Altro (custom)":
            custom = st.text_area("Profilo custom", height=68)

        anon = st.checkbox("Anonimizza paziente", value=True)
        note_extra = st.text_area("Istruzioni extra", height=68)

        c3, c4 = st.columns(2)
        with c3: df = st.date_input("Dal", dt.date.today()-dt.timedelta(days=180))
        with c4: dt_ = st.date_input("Al", dt.date.today())

        st.markdown("**Sorgenti:**")
        chosen = []
        cols = st.columns(2)
        for i, (lbl, key) in enumerate(AVAILABLE_SOURCES):
            default = key in ("pnev","visiva_funzionale","osteopatia")
            with cols[i%2]:
                if st.checkbox(lbl, value=default, key=f"src_{key}"): chosen.append(key)

        if chosen and st.button("✨ Genera", type="primary", key=f"gen_{paz_id}"):
            with st.spinner("AI in elaborazione..."):
                try:
                    dataset = gather_dataset(conn, paz_id, df, dt_, chosen)
                    paz_ai = f"Paziente ID {paz_id}" if anon else paz_nome
                    rel = generate_relazione_json(
                        model=model,
                        system_instructions=build_system_instructions(prof, custom_profile=custom),
                        user_prompt=build_user_prompt(prof, paz_ai, f"{df}→{dt_}", dataset, note_extra),
                        response_schema=relazione_schema(),
                    )
                    pdf = build_pdf_relazione_ai_a4(rel)
                    st.session_state[f"rel_{paz_id}"] = {"rel":rel,"pdf":pdf,"prof":prof,"fonti":chosen}
                except Exception as e:
                    st.error(f"Errore AI: {e}"); st.exception(e)

        gen = st.session_state.get(f"rel_{paz_id}")
        if gen:
            rel = gen["rel"]; pdf = gen["pdf"]
            st.markdown("---")
            st.markdown("### 📝 Revisione — modifica se necessario")
            rel_mod = dict(rel)
            for sez in ["sintesi","valutazione_iniziale","intervento_e_progressione",
                        "risultati","indicazioni","piano_followup"]:
                if sez in rel:
                    rel_mod[sez] = st.text_area(sez.replace("_"," ").title(),
                                                 str(rel.get(sez,"")), height=90,
                                                 key=f"sez_{sez}_{paz_id}")

            note_cl = st.text_area("Note clinico", height=68, key=f"note_cl_{paz_id}",
                                   placeholder="Osservazioni/integrazioni del clinico...")
            if note_cl: rel_mod["note_clinico"] = note_cl

            pdf_fin = build_pdf_relazione_ai_a4(rel_mod)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button("⬇️ Scarica PDF", pdf_fin,
                                   f"relazione_{paz_id}_{dt.date.today()}.pdf",
                                   "application/pdf", key=f"dl_{paz_id}")
            with col2:
                if st.button("💾 Salva Bozza", key=f"bozza_{paz_id}"):
                    rid = _salva_relazione(conn, paz_id, rel_mod, pdf_fin,
                                          gen["prof"], gen["fonti"], "bozza")
                    if rid:
                        st.success(f"✅ Bozza salvata (ID {rid})")
                        del st.session_state[f"rel_{paz_id}"]
            with col3:
                if st.button("✅ Approva e Salva", type="primary", key=f"appr_{paz_id}"):
                    rid = _salva_relazione(conn, paz_id, rel_mod, pdf_fin,
                                          gen["prof"], gen["fonti"], "approvata")
                    if rid:
                        st.success(f"✅ Relazione approvata e salvata (ID {rid})")
                        st.balloons()
                        del st.session_state[f"rel_{paz_id}"]

    # ── STORICO ──────────────────────────────────────────────────────────────
    with tab_stor:
        st.markdown(f"### Relazioni salvate — {paz_nome}")
        rels = _carica_relazioni(conn, paz_id)

        if not rels:
            st.info("Nessuna relazione salvata per questo paziente.")
        else:
            for r in rels:
                ico = {"approvata":"✅","bozza":"📝","inviata":"📤"}.get(r["stato"],"📄")
                with st.expander(f"{ico} {r['data']} — {r['titolo']} [{r['stato'].upper()}]"):
                    st.caption(f"Professionista: {r['professionista'] or '—'} | Fonti: {r['fonti'] or '—'}")

                    if st.button("📖 Apri", key=f"apri_{r['id']}"):
                        st.session_state[f"open_{paz_id}"] = r["id"]

                    if st.session_state.get(f"open_{paz_id}") == r["id"]:
                        det = _carica_detail(conn, r["id"])
                        cont = det.get("contenuto", {})
                        for sez, lbl in [("sintesi","Sintesi"),("risultati","Risultati"),
                                         ("indicazioni","Indicazioni"),("piano_followup","Piano")]:
                            if cont.get(sez):
                                st.markdown(f"**{lbl}:** {cont[sez]}")
                        if det.get("pdf_bytes"):
                            st.download_button("⬇️ PDF", det["pdf_bytes"],
                                               f"rel_{r['id']}.pdf", "application/pdf",
                                               key=f"dl_stor_{r['id']}")

                    c1, c2 = st.columns(2)
                    if r["stato"] == "bozza":
                        with c1:
                            if st.button("✅ Approva", key=f"appr_stor_{r['id']}"):
                                _aggiorna_stato(conn, r["id"], "approvata")
                                st.rerun()
                    if r["stato"] in ("bozza","approvata"):
                        with c2:
                            if st.button("📤 Inviata", key=f"inv_stor_{r['id']}"):
                                _aggiorna_stato(conn, r["id"], "inviata")
                                st.rerun()
