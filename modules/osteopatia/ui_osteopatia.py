import datetime as dt
import streamlit as st

from .db_osteopatia import (
    insert_anamnesi, list_anamnesi, get_anamnesi,
    insert_seduta, list_sedute, get_seduta,
    update_anamnesi, soft_delete_anamnesi, restore_anamnesi,
    update_seduta, soft_delete_seduta, restore_seduta
)
from .pdf_osteopatia import build_pdf_osteopatia_referto_a4
from .pdf_relazione_osteopatia import build_pdf_relazione_osteopatia_a4
from .dashboard_osteopatia import render_dashboard_osteo

TECNICHE_LIST = [
    "Cranio-sacrale", "Fasciale", "Viscerale", "Strutturale",
    "HVLA", "Miofasciale", "Trigger points", "Normalizzazione posturale",
    "Tecniche respiratorie", "ATM"
]

def ui_osteopatia(paziente_id: int, get_conn, paziente_label: str = ""):
    """
    Integrazione rapida:
      ui_osteopatia(paziente_id, get_conn=get_conn, paziente_label=nome_cognome)

    get_conn: funzione del tuo gestionale che ritorna conn psycopg2 (Neon/Postgres)
    """
    st.subheader("🦴 Osteopatia")

    # stato UI (edit)
    st.session_state.setdefault('osteo_edit_mode', None)  # 'anamnesi' | 'seduta'
    st.session_state.setdefault('osteo_edit_id', None)

    tab1, tab2, tab3, tab4 = st.tabs(["➕ Anamnesi", "➕ Seduta", "📚 Storico", "📊 Dashboard"])

    # -------------------------
    # TAB 1 - ANAMNESI
    # -------------------------
    with tab1:
        if st.session_state.get('osteo_edit_mode') == 'anamnesi':
            st.markdown("### ✏️ Modifica anamnesi")
        else:
            st.markdown("### Nuova anamnesi osteopatica")
        current_anam = None
        if st.session_state.get('osteo_edit_mode') == 'anamnesi' and st.session_state.get('osteo_edit_id'):
            conn = get_conn()
            current_anam = get_anamnesi(conn, int(st.session_state['osteo_edit_id']))

        with st.form("osteo_anamnesi_form", clear_on_submit=False):
            colA, colB = st.columns(2)
            with colA:
                data_anamnesi = st.date_input("Data anamnesi", value=(current_anam.get('data_anamnesi') if current_anam else dt.date.today()))
                dolore_sede = st.text_input("Dolore – sede", value=(current_anam.get('dolore_sede') or "") if current_anam else "")
                dolore_intensita = st.slider("Dolore – intensità (0-10)", 0, 10, int(current_anam.get('dolore_intensita') or 0) if current_anam else 0)
            with colB:
                dolore_durata = st.text_input("Dolore – durata")
                aggravanti = st.text_area("Fattori aggravanti", height=80)
                allevianti = st.text_area("Fattori allevianti", height=80)

            motivo = st.text_area("Motivo della consulenza", height=80, value=(current_anam.get('motivo') or "") if current_anam else "")

            st.markdown("#### Storia clinica (spuntabili + note)")
            sc_col1, sc_col2, sc_col3 = st.columns(3)
            storia = {}
            with sc_col1:
                storia["traumi"] = st.checkbox("Traumi")
                storia["incidenti"] = st.checkbox("Incidenti")
                storia["chirurgia"] = st.checkbox("Interventi chirurgici")
            with sc_col2:
                storia["fratture"] = st.checkbox("Fratture")
                storia["protesi"] = st.checkbox("Protesi")
                storia["patologie_croniche"] = st.checkbox("Patologie croniche")
            with sc_col3:
                storia["farmaci"] = st.checkbox("Terapie farmacologiche")
                storia["altro"] = st.checkbox("Altro")
            storia["note"] = st.text_area("Note storia clinica", height=80)

            st.markdown("#### Area neuro-posturale (PNEV)")
            neuro = {}
            n1, n2, n3 = st.columns(3)
            with n1:
                neuro["cefalea"] = st.checkbox("Cefalea")
                neuro["vertigini"] = st.checkbox("Vertigini")
                neuro["disturbi_equilibrio"] = st.checkbox("Disturbi equilibrio")
            with n2:
                neuro["disturbi_visivi"] = st.checkbox("Disturbi visivi")
                neuro["atm"] = st.checkbox("ATM / click / dolore")
                neuro["bruxismo"] = st.checkbox("Bruxismo")
            with n3:
                neuro["acufeni"] = st.checkbox("Acufeni")
                neuro["respirazione"] = st.checkbox("Disturbi respiratori")
                neuro["altro"] = st.checkbox("Altro (neuro-post)")
            neuro["note"] = st.text_area("Note neuro-posturali", height=80)

            st.markdown("#### Stile di vita")
            stile = {
                "attivita_fisica": st.text_input("Attività fisica"),
                "sport": st.text_input("Sport praticati"),
                "lavoro_postura": st.text_input("Lavoro / postura"),
                "stress": st.slider("Stress percepito (0-10)", 0, 10, 0),
                "note": st.text_area("Note stile di vita", height=80)
            }

            st.markdown("#### Area pediatrica (se minore) – opzionale")
            pedi = {
                "tipo_parto": st.text_input("Tipo parto"),
                "traumi_neonatali": st.text_input("Traumi neonatali"),
                "sviluppo": st.text_input("Sviluppo / tappe motorie"),
                "note": st.text_area("Note pediatriche", height=80)
            }

            valutazione = st.text_area("Valutazione osteopatica (test / riscontri)", height=110, value=(current_anam.get('valutazione') or "") if current_anam else "")
            ipotesi = st.text_area("Ipotesi osteopatica", height=90, value=(current_anam.get('ipotesi') or "") if current_anam else "")

            submitted = st.form_submit_button("💾 Salva")
            if submitted:
                conn = get_conn()
                if st.session_state.get('osteo_edit_mode') == 'anamnesi' and current_anam:
                    update_anamnesi(conn, int(current_anam['id']), {
                        'data_anamnesi': data_anamnesi,
                        'motivo': motivo,
                        'dolore_sede': dolore_sede,
                        'dolore_intensita': dolore_intensita,
                        'dolore_durata': dolore_durata,
                        'aggravanti': aggravanti,
                        'allevianti': allevianti,
                        'storia_clinica': storia,
                        'area_neuro_post': neuro,
                        'stile_vita': stile,
                        'area_pediatrica': pedi,
                        'valutazione': valutazione,
                        'ipotesi': ipotesi,
                    }, updated_by=None)
                    st.session_state['osteo_edit_mode'] = None
                    st.session_state['osteo_edit_id'] = None
                    st.success("Anamnesi aggiornata.")
                    st.experimental_rerun()
                else:
                    anamnesi_id = insert_anamnesi(conn, paziente_id, {
                    "data_anamnesi": data_anamnesi,
                    "motivo": motivo,
                    "dolore_sede": dolore_sede,
                    "dolore_intensita": dolore_intensita,
                    "dolore_durata": dolore_durata,
                    "aggravanti": aggravanti,
                    "allevianti": allevianti,
                    "storia_clinica": storia,
                    "area_neuro_post": neuro,
                    "stile_vita": stile,
                    "area_pediatrica": pedi,
                    "valutazione": valutazione,
                    "ipotesi": ipotesi,
                })
                st.success(f"Anamnesi salvata (ID {anamnesi_id}).")

        if st.session_state.get('osteo_edit_mode') == 'anamnesi':
            if st.button("↩️ Annulla modifica anamnesi", key="osteo_cancel_anam"):
                st.session_state['osteo_edit_mode'] = None
                st.session_state['osteo_edit_id'] = None
                st.experimental_rerun()

    # -------------------------
    # TAB 2 - SEDUTA
    # -------------------------
    with tab2:
        if st.session_state.get('osteo_edit_mode') == 'seduta':
            st.markdown("### ✏️ Modifica seduta osteopatica")
        else:
            st.markdown("### Nuova seduta osteopatica")

        conn = get_conn()
        anam_list = list_anamnesi(conn, paziente_id)
        anam_options = ["(nessuna)"] + [f"#{a['id']} — {a['data_anamnesi']} — {(a.get('motivo') or '')[:50]}" for a in anam_list]
        anam_map = {anam_options[i+1]: anam_list[i]["id"] for i in range(len(anam_list))}

        current_sed = None
        if st.session_state.get('osteo_edit_mode') == 'seduta' and st.session_state.get('osteo_edit_id'):
            current_sed = get_seduta(conn, int(st.session_state['osteo_edit_id']))

        with st.form("osteo_seduta_form", clear_on_submit=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                data_seduta = st.date_input("Data seduta", value=(current_sed.get('data_seduta') if current_sed else dt.date.today()))
                tipo_seduta = st.selectbox("Tipo seduta", ["Prima visita", "Controllo", "Follow-up"])
            with col2:
                operatore = st.text_input("Operatore", value=(current_sed.get('operatore') or "") if current_sed else "")
                dolore_pre = st.slider("Dolore pre (0-10)", 0, 10, int(current_sed.get('dolore_pre') or 0) if current_sed else 0)
            with col3:
                dolore_post = st.slider("Dolore post (0-10)", 0, 10, int(current_sed.get('dolore_post') or 0) if current_sed else 0)
                anam_sel = st.selectbox("Collega ad anamnesi", anam_options)

            note_pre = st.text_area("Note pre-trattamento", height=80)

            st.markdown("#### Tecniche")
            tech_cols = st.columns(3)
            tecniche = {}
            for i, t in enumerate(TECNICHE_LIST):
                with tech_cols[i % 3]:
                    tecniche[t] = st.checkbox(t)

            descrizione = st.text_area("Descrizione trattamento", height=130, value=(current_sed.get('descrizione') or "") if current_sed else "")
            risposta = st.text_area("Risposta al trattamento", height=80)
            reazioni = st.text_area("Reazioni / note post-seduta", height=80)
            indicazioni = st.text_area("Indicazioni domiciliari / esercizi", height=110, value=(current_sed.get('indicazioni') or "") if current_sed else "")
            prossimo_step = st.text_area("Piano / prossimo step", height=80)

            submitted = st.form_submit_button("💾 Salva")
            if submitted:
                conn = get_conn()
                anamnesi_id = None if anam_sel == "(nessuna)" else anam_map.get(anam_sel)
                if st.session_state.get('osteo_edit_mode') == 'seduta' and current_sed:
                    update_seduta(conn, int(current_sed['id']), {
                        'anamnesi_id': anamnesi_id,
                        'data_seduta': data_seduta,
                        'operatore': operatore,
                        'tipo_seduta': tipo_seduta,
                        'dolore_pre': dolore_pre,
                        'note_pre': note_pre,
                        'tecniche': tecniche,
                        'descrizione': descrizione,
                        'risposta': risposta,
                        'dolore_post': dolore_post,
                        'reazioni': reazioni,
                        'indicazioni': indicazioni,
                        'prossimo_step': prossimo_step,
                    }, updated_by=None)
                    st.session_state['osteo_edit_mode'] = None
                    st.session_state['osteo_edit_id'] = None
                    st.success("Seduta aggiornata.")
                    st.experimental_rerun()
                else:
                    seduta_id = insert_seduta(conn, paziente_id, {
                    "anamnesi_id": anamnesi_id,
                    "data_seduta": data_seduta,
                    "operatore": operatore,
                    "tipo_seduta": tipo_seduta,
                    "dolore_pre": dolore_pre,
                    "note_pre": note_pre,
                    "tecniche": tecniche,
                    "descrizione": descrizione,
                    "risposta": risposta,
                    "dolore_post": dolore_post,
                    "reazioni": reazioni,
                    "indicazioni": indicazioni,
                    "prossimo_step": prossimo_step,
                })
                st.success(f"Seduta salvata (ID {seduta_id}).")

        if st.session_state.get('osteo_edit_mode') == 'seduta':
            if st.button("↩️ Annulla modifica seduta", key="osteo_cancel_sed"):
                st.session_state['osteo_edit_mode'] = None
                st.session_state['osteo_edit_id'] = None
                st.experimental_rerun()

    # -------------------------
    # TAB 3 - STORICO + PDF
    # -------------------------
    with tab3:
        st.markdown("### Storico osteopatia")
        conn = get_conn()
        sedute = list_sedute(conn, paziente_id)
        anamnesi = list_anamnesi(conn, paziente_id)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Anamnesi")
            if not anamnesi:
                st.info("Nessuna anamnesi.")
            else:
                for a in anamnesi[:10]:
                    with st.expander(f"Anamnesi #{a['id']} — {a['data_anamnesi']}"):
                        full = get_anamnesi(conn, a["id"])
                        st.write(full.get("motivo", ""))
                        st.caption(f"Dolore: {full.get('dolore_sede','')} — {full.get('dolore_intensita','')}/10")

        with c2:
            st.markdown("#### Sedute")
            if not sedute:
                st.info("Nessuna seduta.")
            else:
                for s in sedute[:15]:
                    with st.expander(f"Seduta #{s['id']} — {s['data_seduta']} — {s.get('tipo_seduta','')}"):
                        full = get_seduta(conn, s["id"])
                        st.caption(f"Operatore: {full.get('operatore','')}")
                        st.write(full.get("descrizione", ""))
                        st.caption(f"Dolore pre/post: {full.get('dolore_pre','')} → {full.get('dolore_post','')}")

                        colb1, colb2, colb3 = st.columns(3)
                        with colb1:
                            if st.button("✏️ Modifica", key=f"edit_s_{s['id']}"):
                                st.session_state['osteo_edit_mode'] = 'seduta'
                                st.session_state['osteo_edit_id'] = s['id']
                                st.experimental_rerun()
                        with colb2:
                            if st.button("🗑️ Elimina", key=f"del_s_{s['id']}"):
                                soft_delete_seduta(conn, s['id'], deleted_by=full.get('operatore'))
                                st.success("Seduta spostata nel cestino.")
                                st.experimental_rerun()
                        with colb3:
                            if st.button(f"📄 PDF A4", key=f"pdf_btn_{s['id']}"):
                                pdf_bytes = build_pdf_osteopatia_referto_a4(
                                    paziente_label=paziente_label or f"Paziente ID {paziente_id}",
                                    seduta=full
                                )
                                st.download_button(
                                    "⬇️ Scarica PDF",
                                    data=pdf_bytes,
                                    file_name=f"referto_osteopatia_seduta_{s['id']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{s['id']}"
                                )

                        # (vecchio bottone rimosso)

                            pdf_bytes = build_pdf_osteopatia_referto_a4(
                                paziente_label=paziente_label or f"Paziente ID {paziente_id}",
                                seduta=full
                            )
                            st.download_button(
                                "⬇️ Scarica PDF",
                                data=pdf_bytes,
                                file_name=f"referto_osteopatia_seduta_{s['id']}.pdf",
                                mime="application/pdf"
                            )

        st.markdown("---")
        st.markdown("### Relazione osteopatia (A4)")
        colr1, colr2, colr3 = st.columns(3)
        with colr1:
            date_from = st.date_input("Da", value=dt.date.today() - dt.timedelta(days=90), key="osteo_rel_da")
        with colr2:
            date_to = st.date_input("A", value=dt.date.today(), key="osteo_rel_a")
        with colr3:
            rel_anam = st.selectbox(
                "Anamnesi di riferimento",
                ["(nessuna)"] + [f"#{a['id']} — {a['data_anamnesi']}" for a in anamnesi],
                key="osteo_rel_anam"
            )
        if st.button("🖨️ Genera relazione A4", key="osteo_rel_btn"):
            # carica sedute nel periodo (solo non cancellate)
            all_sed = list_sedute(conn, paziente_id, include_deleted=False)
            sed_periodo = []
            for s in all_sed:
                try:
                    ds = s.get('data_seduta')
                    if isinstance(ds, str):
                        ds = dt.date.fromisoformat(ds)
                    if ds and date_from <= ds <= date_to:
                        sed_periodo.append(get_seduta(conn, s['id']))
                except Exception:
                    sed_periodo.append(get_seduta(conn, s['id']))

            anam_obj = None
            if rel_anam != "(nessuna)":
                try:
                    anam_id = int(rel_anam.split('#')[1].split('—')[0].strip())
                    anam_obj = get_anamnesi(conn, anam_id)
                except Exception:
                    anam_obj = None

            periodo_label = f"{date_from} → {date_to}"
            pdf_bytes = build_pdf_relazione_osteopatia_a4(
                paziente_label=paziente_label or f"Paziente ID {paziente_id}",
                anamnesi=anam_obj,
                sedute=[s for s in sed_periodo if s],
                periodo_label=periodo_label
            )
            st.download_button(
                "⬇️ Scarica Relazione A4",
                data=pdf_bytes,
                file_name=f"relazione_osteopatia_{paziente_id}_{date_from}_{date_to}.pdf",
                mime="application/pdf",
                key="osteo_rel_dl"
            )

        st.markdown("---")
        st.markdown("### Cestino (record eliminati)")
        show_bin = st.checkbox("Mostra cestino", value=False, key="osteo_show_bin")
        if show_bin:
            # sedute eliminate
            sedute_all = list_sedute(conn, paziente_id, include_deleted=True)
            sed_del = [s for s in sedute_all if str(s.get('id')) and True]
            # filtriamo solo se la colonna esiste in SELECT completo: facciamo un tentativo con get_seduta
            deleted_s = []
            for s in sedute_all:
                full = get_seduta(conn, s['id'])
                if full and full.get('is_deleted'):
                    deleted_s.append(full)
            if deleted_s:
                for full in deleted_s:
                    with st.expander(f"🗑️ Seduta #{full.get('id')} — {full.get('data_seduta')}"):
                        st.write((full.get('descrizione') or '')[:500])
                        if st.button("♻️ Ripristina seduta", key=f"res_s_{full.get('id')}"):
                            restore_seduta(conn, full.get('id'))
                            st.success("Seduta ripristinata.")
                            st.experimental_rerun()
            else:
                st.caption("Nessuna seduta nel cestino.")

            deleted_a = []
            for a in anamnesi:
                full = get_anamnesi(conn, a['id'])
                if full and full.get('is_deleted'):
                    deleted_a.append(full)
            if deleted_a:
                for full in deleted_a:
                    with st.expander(f"🗑️ Anamnesi #{full.get('id')} — {full.get('data_anamnesi')}"):
                        st.write((full.get('motivo') or '')[:300])
                        if st.button("♻️ Ripristina anamnesi", key=f"res_a_{full.get('id')}"):
                            restore_anamnesi(conn, full.get('id'))
                            st.success("Anamnesi ripristinata.")
                            st.experimental_rerun()
            else:
                st.caption("Nessuna anamnesi nel cestino.")

    # -------------------------
    # TAB 4 - DASHBOARD
    # -------------------------
    with tab4:
        conn = get_conn()
        sedute = list_sedute(conn, paziente_id)
        render_dashboard_osteo(sedute)
