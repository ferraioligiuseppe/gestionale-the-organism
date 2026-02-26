from __future__ import annotations
import datetime as dt
import json
from typing import Any, Dict, List
import streamlit as st
from vision_manager.db import get_conn, init_db
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"

ACUITA_VALUES = [
    "N.V. (Occhio non vedente)",
    "P.L. (Percezione luce)",
    "M.M. (Movimento mano)",
    "C.F. (Conta dita)",
    "1/50","1/20","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10",
    "12/10","14/10","16/10"
]

LENTI_OPTIONS = [
    "Progressive",
    "Per vicino/intermedio",
    "Monofocali lontano",
    "Monofocali intermedio",
    "Monofocali vicino",
    "Fotocromatiche",
    "Polarizzate",
    "Controllo miopia",
    "Trattamento antiriflesso",
    "Filtro luce blu",
]

def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


_pazienti_note_cache = None

def _pazienti_has_note(conn) -> bool:
    """Rileva una volta se la tabella pubblica 'pazienti' ha la colonna 'note' (PostgreSQL)."""
    global _pazienti_note_cache
    if _pazienti_note_cache is not None:
        return bool(_pazienti_note_cache)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='pazienti' AND column_name='note' LIMIT 1"
        )
        _pazienti_note_cache = bool(cur.fetchone())
        return bool(_pazienti_note_cache)
    except Exception:
        _pazienti_note_cache = False
        return False

def _ph(conn) -> str:
    return "%s" if _is_pg(conn) else "?"

def _dict_row(cur, row):
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    # Normalizza chiavi a lowercase per gestire DB diversi (Postgres/SQLite) e naming misto
    return {str(k).lower(): v for k, v in (d or {}).items()}

def _load_pazienti_vision(conn) -> List[Dict[str, Any]]:
    """Legacy: pazienti salvati nel DB Vision separato (pazienti_visivi)."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti_visivi ORDER BY cognome, nome")
        rows = cur.fetchall()
        return [_normalize_row(_dict_row(cur, r)) for r in rows]
    finally:
        try: cur.close()
        except Exception: pass


def _load_pazienti(conn) -> List[Dict[str, Any]]:
    """
    Carica i pazienti dal DB principale del gestionale.
    - Postgres (Neon): tabella public.pazienti con colonne snake_case: id, cognome, nome, data_nascita, note
    - SQLite locale: tabella Pazienti legacy: ID, Cognome, Nome, Data_Nascita, Note
    Fallback: usa pazienti_visivi se la tabella principale non esiste.
    """
    cur = conn.cursor()
    try:
        try:
            if _is_pg(conn):
                cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti ORDER BY cognome, nome") if _pazienti_has_note(conn) else cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti ORDER BY cognome, nome")
            else:
                cur.execute("SELECT ID, Cognome, Nome, Data_Nascita, Note FROM Pazienti ORDER BY Cognome, Nome")
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = _normalize_row(_dict_row(cur, r))
                out.append({
                    "id": d.get("id"),
                    "cognome": d.get("cognome"),
                    "nome": d.get("nome"),
                    "data_nascita": d.get("data_nascita"),
                    "note": d.get("note"),
                    "_source": "pazienti" if _is_pg(conn) else "Pazienti",
                })
            return out
        except Exception:
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass
            return _load_pazienti_vision(conn)
    finally:
        try:
            cur.close()
        except Exception:
            pass

def _insert_paziente(conn, nome, cognome, data_nascita, note=""):
    """
    Inserisce paziente nel DB centrale Neon (tabella pazienti)
    Gestisce:
    - colonne obbligatorie
    - stato_paziente NOT NULL
    - cursor dict / tuple
    - presenza o meno della colonna note
    """

    cognome = (cognome or "").strip()
    nome = (nome or "").strip()
    data_nascita = (data_nascita or "").strip()
    note = (note or "").strip()

    if not cognome:
        raise ValueError("Cognome obbligatorio")
    if not nome:
        raise ValueError("Nome obbligatorio")
    if not data_nascita:
        raise ValueError("Data nascita obbligatoria")

    cur = conn.cursor()

    # placeholder corretto
    ph = "%s"

    # controlla se esiste colonna note
    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='pazienti'
        AND column_name='note'
        LIMIT 1
    """)
    has_note = cur.fetchone() is not None

    if has_note:
        cur.execute(
            f"""
            INSERT INTO pazienti
            (cognome, nome, data_nascita, note, stato_paziente)
            VALUES ({ph},{ph},{ph},{ph},{ph})
            RETURNING id
            """,
            (cognome, nome, data_nascita, note, "ATTIVO"),
        )
    else:
        cur.execute(
            f"""
            INSERT INTO pazienti
            (cognome, nome, data_nascita, stato_paziente)
            VALUES ({ph},{ph},{ph},{ph})
            RETURNING id
            """,
            (cognome, nome, data_nascita, "ATTIVO"),
        )

    row = cur.fetchone()

    # compatibilità dict / tuple
    if isinstance(row, dict):
        pid = row["id"]
    else:
        pid = row[0]

    conn.commit()
    return pid

def _insert_visita(conn, paziente_id: int, data_visita: str, dati_json: str) -> int:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        if _is_pg(conn):
            cur.execute(
                f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json) VALUES ({ph},{ph},{ph}) RETURNING id",
                (paziente_id, data_visita, dati_json),
            )
            row = cur.fetchone()
            vid = (row.get("id") if hasattr(row, "get") else row[0])
        else:
            cur.execute(
                f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json) VALUES ({ph},{ph},{ph})",
                (paziente_id, data_visita, dati_json),
            )
            vid = cur.lastrowid
        conn.commit()
        return int(vid)
    finally:
        try: cur.close()
        except Exception: pass


def _update_visita(conn, visita_id: int, dati_json: str):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}", (dati_json, visita_id))
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass

def _soft_delete_visita(conn, visita_id: int):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(f"UPDATE visite_visive SET is_deleted={ph}, deleted_at={ph} WHERE id={ph}",
                        (1, dt.datetime.now().isoformat(timespec="seconds"), visita_id))
        except Exception:
            cur.execute(f"SELECT dati_json FROM visite_visive WHERE id={ph}", (visita_id,))
            row = cur.fetchone()
            dj = row[0] if row else ""
            try:
                obj = json.loads(dj) if dj else {}
            except Exception:
                obj = {"raw": dj}
            obj["_deleted"] = True
            obj["_deleted_at"] = dt.datetime.now().isoformat(timespec="seconds")
            cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}",
                        (json.dumps(obj, ensure_ascii=False), visita_id))
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass

def _restore_visita(conn, visita_id: int):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(f"UPDATE visite_visive SET is_deleted={ph}, deleted_at={ph} WHERE id={ph}",
                        (0, None, visita_id))
        except Exception:
            cur.execute(f"SELECT dati_json FROM visite_visive WHERE id={ph}", (visita_id,))
            row = cur.fetchone()
            dj = row[0] if row else ""
            try:
                obj = json.loads(dj) if dj else {}
            except Exception:
                obj = {"raw": dj}
            obj["_deleted"] = False
            obj["_deleted_at"] = None
            cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}",
                        (json.dumps(obj, ensure_ascii=False), visita_id))
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass


def _list_visite(conn, paziente_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            # Proviamo prima con colonne soft-delete (se esistono)
            if include_deleted:
                cur.execute(
                    f"SELECT id, data_visita, dati_json, is_deleted, deleted_at "
                    f"FROM visite_visive WHERE paziente_id={ph} "
                    f"ORDER BY data_visita DESC, id DESC LIMIT 200",
                    (paziente_id,),
                )
            else:
                cur.execute(
                    f"SELECT id, data_visita, dati_json, is_deleted, deleted_at "
                    f"FROM visite_visive WHERE paziente_id={ph} AND COALESCE(is_deleted,0)<>1 "
                    f"ORDER BY data_visita DESC, id DESC LIMIT 200",
                    (paziente_id,),
                )
        except Exception:
            # IMPORTANTISSIMO: su Postgres, se una query fallisce la transazione entra in aborted.
            # Prima di fare una nuova query bisogna fare rollback.
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass

            # fallback se la tabella non ha ancora le colonne
            cur.execute(
                f"SELECT id, data_visita, dati_json "
                f"FROM visite_visive WHERE paziente_id={ph} "
                f"ORDER BY data_visita DESC, id DESC LIMIT 200",
                (paziente_id,),
            )

        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass
def _parse_json(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {"raw": s}

def _format_paz(p) -> str:
    dn = p.get("data_nascita") or ""
    return f"{p['cognome']} {p['nome']} (ID {p['id']}) {dn}".strip()

def _rx_input(label: str, key_prefix: str):
    c1, c2, c3 = st.columns([1, 1, 1])
    sf = c1.number_input(f"{label} SF", value=0.00, step=0.25, format="%0.2f", key=f"{key_prefix}_sf")
    cyl = c2.number_input(f"{label} CIL", value=0.00, step=0.25, format="%0.2f", key=f"{key_prefix}_cyl")
    ax = c3.number_input(f"{label} AX (0-180)", min_value=0, max_value=180, value=0, step=1, key=f"{key_prefix}_ax")
    return {"sf": float(sf), "cyl": float(cyl), "ax": int(ax)}

def ui_visita_visiva():
    st.subheader("🩺 Visita oculistica — Dr. Cirillo (Vision Manager)")

    conn = get_conn()
    init_db(conn)

    tab_paz, tab_vis = st.tabs(["👤 Anagrafica (Gestionale)", "🗓️ Visita oculistica"])

    with tab_paz:
        st.markdown("### Aggiungi paziente (DB Gestionale)")
        c1, c2, c3 = st.columns([1, 1, 1])
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        data_nascita = c3.text_input("Data nascita (YYYY-MM-DD)", value="")
        note = st.text_area("Note", height=90, key="note_anagrafica")

        if st.button("💾 Salva paziente"):
            if not nome.strip() or not cognome.strip():
                st.error("Nome e cognome sono obbligatori.")
            else:
                try:
                    pid = _insert_paziente(conn, nome.strip(), cognome.strip(), data_nascita.strip(), note.strip())
                except ValueError as ve:
                    st.error(str(ve))
                    return
                st.success(f"Paziente salvato (ID {pid}).")
                st.session_state["vision_last_pid"] = pid
                st.rerun()

        st.markdown("### Elenco pazienti")
        paz = _load_pazienti(conn)
        st.dataframe(paz, use_container_width=True)

        st.markdown("### Modifica anagrafica paziente")
        psel_edit = st.selectbox("Seleziona paziente da modificare", paz, format_func=_format_paz, key="paz_edit_sel")
        if psel_edit:
            e1, e2, e3 = st.columns([1,1,1])
            new_nome = e1.text_input("Nome (modifica)", value=str(psel_edit.get("nome") or ""), key="edit_nome")
            new_cognome = e2.text_input("Cognome (modifica)", value=str(psel_edit.get("cognome") or ""), key="edit_cognome")
            new_dn = e3.text_input("Data nascita (YYYY-MM-DD) (modifica)", value=str(psel_edit.get("data_nascita") or ""), key="edit_dn")
            if st.button("✏️ Salva modifiche anagrafiche", key="save_edit_anag"):
                cur2 = conn.cursor()
                ph = _ph(conn)
                try:
                    try:
                        cur2.execute(
                            f"UPDATE pazienti SET cognome={ph}, nome={ph}, data_nascita={ph} WHERE id={ph}" if _is_pg(conn) else f"UPDATE Pazienti SET Cognome={ph}, Nome={ph}, Data_Nascita={ph} WHERE ID={ph}",
                            (new_cognome.strip(), new_nome.strip(), new_dn.strip() or None, int(psel_edit.get('id'))),
                        )
                        conn.commit()
                        st.success("Anagrafica aggiornata.")
                        st.rerun()
                    except Exception as e:
                        if _is_pg(conn):
                            try: conn.rollback()
                            except Exception: pass
                        st.error(f"Impossibile aggiornare anagrafica su tabella Pazienti: {e}")
                finally:
                    try: cur2.close()
                    except Exception: pass

    with tab_vis:
        paz = _load_pazienti(conn)
        if not paz:
            st.info("Prima crea almeno un paziente nella tab 'Anagrafica (Gestionale)'.")
            return

        # Preseleziona l’ultimo paziente creato (se presente)
        default_idx = 0
        last_pid = st.session_state.get("vision_last_pid")
        if last_pid is not None:
            for i, p in enumerate(paz):
                try:
                    if int(p.get("id") or 0) == int(last_pid):
                        default_idx = i
                        break
                except Exception:
                    pass

        psel = st.selectbox("Seleziona paziente", paz, format_func=_format_paz, index=default_idx)
        paziente_id = int(psel["id"])
        paziente_label = f"{psel.get('cognome','')} {psel.get('nome','')}".strip()

        data_visita = st.date_input("Data visita", value=dt.date.today())
        anamnesi = st.text_area("Anamnesi", height=110)

        st.markdown("### Acuità visiva (decimi)")
        col = st.columns(3)
        with col[0]:
            st.caption("Naturale")
            avn_od = st.selectbox("OD (naturale)", ACUITA_VALUES, index=11, key="avn_od")
            avn_os = st.selectbox("OS (naturale)", ACUITA_VALUES, index=11, key="avn_os")
            avn_oo = st.selectbox("OO (naturale)", ACUITA_VALUES, index=11, key="avn_oo")
        with col[1]:
            st.caption("Abituale")
            ava_od = st.selectbox("OD (abituale)", ACUITA_VALUES, index=11, key="ava_od")
            ava_os = st.selectbox("OS (abituale)", ACUITA_VALUES, index=11, key="ava_os")
            ava_oo = st.selectbox("OO (abituale)", ACUITA_VALUES, index=11, key="ava_oo")
        with col[2]:
            st.caption("Corretta")
            avc_od = st.selectbox("OD (corretta)", ACUITA_VALUES, index=11, key="avc_od")
            avc_os = st.selectbox("OS (corretta)", ACUITA_VALUES, index=11, key="avc_os")
            avc_oo = st.selectbox("OO (corretta)", ACUITA_VALUES, index=11, key="avc_oo")

        st.markdown("### Esame obiettivo")
        c1, c2 = st.columns(2)
        with c1:
            congiuntiva = st.text_input("Congiuntiva (OD/OS)", value="")
            cornea = st.text_input("Cornea (OD/OS)", value="")
            camera_anteriore = st.text_input("Camera anteriore (OD/OS)", value="")
        with c2:
            cristallino = st.text_input("Cristallino (OD/OS)", value="")
            vitreo = st.text_input("Vitreo (OD/OS)", value="")
            fondo_oculare = st.text_input("Fondo oculare (OD/OS)", value="")

        st.markdown("### Correzione abituale (lontano)")
        rx_ab_od = _rx_input("OD abituale", "rx_ab_od")
        rx_ab_os = _rx_input("OS abituale", "rx_ab_os")
        add_ab = st.number_input("Addizione da vicino (abituale)", value=0.00, step=0.25, format="%0.2f", key="add_ab")

        st.markdown("### Correzione finale (lontano)")
        rx_fin_od = _rx_input("OD finale", "rx_fin_od")
        rx_fin_os = _rx_input("OS finale", "rx_fin_os")
        add_fin = st.number_input("Addizione da vicino (finale)", value=0.00, step=0.25, format="%0.2f", key="add_fin")

        def _near(rx, add):
            return {"sf": float(rx["sf"]) + float(add), "cyl": float(rx["cyl"]), "ax": int(rx["ax"])}

        vicino_od = _near(rx_fin_od, add_fin)
        vicino_os = _near(rx_fin_os, add_fin)
        inter_od = _near(rx_fin_od, float(add_fin)/2.0)
        inter_os = _near(rx_fin_os, float(add_fin)/2.0)

        lenti_sel = st.multiselect("Lenti consigliate (mostra solo selezionate)", LENTI_OPTIONS, default=[])

        note_v = st.text_area("Note visita", height=100)


        payload = {
            "tipo_visita": "oculistica",
            "data": str(data_visita),
            "paziente": {"id": paziente_id, "nome": psel.get("nome"), "cognome": psel.get("cognome"), "data_nascita": psel.get("data_nascita")},
            "anamnesi": anamnesi,
            "acuita": {
                "naturale": {"od": avn_od, "os": avn_os, "oo": avn_oo},
                "abituale": {"od": ava_od, "os": ava_os, "oo": ava_oo},
                "corretta": {"od": avc_od, "os": avc_os, "oo": avc_oo},
            },
            "esame_obiettivo": {
                "congiuntiva": congiuntiva,
                "cornea": cornea,
                "camera_anteriore": camera_anteriore,
                "cristallino": cristallino,
                "vitreo": vitreo,
                "fondo_oculare": fondo_oculare,
            },
            "correzione_abituale": {"od": rx_ab_od, "os": rx_ab_os, "add": float(add_ab)},
            "correzione_finale": {"od": rx_fin_od, "os": rx_fin_os, "add": float(add_fin)},
            "prescrizione": {
                "lontano": {"od": rx_fin_od, "os": rx_fin_os},
                "intermedio": {"od": inter_od, "os": inter_os},
                "vicino": {"od": vicino_od, "os": vicino_os},
                "lenti": lenti_sel,
            },
            "note": note_v,
        }
        payload_str = json.dumps(payload, ensure_ascii=False)

        csave, cpdf1, cpdf2 = st.columns([1,1,1])
        with csave:
            if st.button("💾 Salva visita (DB)"):
                vid = _insert_visita(conn, paziente_id, str(data_visita), payload_str)
                st.success(f"Visita salvata (ID {vid}).")
        with cpdf1:
            if st.button("🧾 Genera PDF Referto A4"):
                pdf_bytes = build_referto_oculistico_a4({**payload, "data": str(data_visita), "paziente": paziente_label}, LETTERHEAD)
                st.download_button("⬇️ Scarica Referto A4", data=pdf_bytes, file_name=f"referto_oculistico_{paziente_id}_{data_visita}.pdf", mime="application/pdf")
        with cpdf2:
            if st.button("👓 Genera PDF Prescrizione A4"):
                pr = payload["prescrizione"]
                pdf_bytes = build_prescrizione_occhiali_a4(
                    {
                        "data": str(data_visita),
                        "paziente": paziente_label,
                        "lontano": pr["lontano"],
                        "intermedio": pr["intermedio"],
                        "vicino": pr["vicino"],
                        "lenti": pr["lenti"],
                    },
                    LETTERHEAD
                )
                st.download_button("⬇️ Scarica Prescrizione A4", data=pdf_bytes, file_name=f"prescrizione_occhiali_{paziente_id}_{data_visita}.pdf", mime="application/pdf")

        st.markdown("---")
        st.markdown("---")
        st.markdown("### Storico visite")
        show_deleted = st.checkbox("Mostra anche le visite eliminate", value=False)
        visite = _list_visite(conn, paziente_id, include_deleted=show_deleted)

        for v in visite:
            vid = int(v["id"])
            with st.expander(f"Visita #{vid} — {v.get('data_visita','')}"):
                pj = _parse_json(v.get("dati_json") or "")
                is_del = False
                if isinstance(pj, dict) and pj.get("_deleted") is True:
                    is_del = True
                if "is_deleted" in v and int(v.get("is_deleted") or 0) == 1:
                    is_del = True

                if is_del:
                    st.warning(f"VISITA ELIMINATA (soft) — {v.get('deleted_at') or pj.get('_deleted_at','')}")

                st.json(pj)

                c1, c2, c3 = st.columns([1,1,1])
                if c1.button("✏️ Modifica", key=f"edit_{vid}"):
                    st.session_state[f"edit_mode_{vid}"] = True

                if (not is_del) and c2.button("🗑️ Elimina", key=f"del_{vid}"):
                    _soft_delete_visita(conn, vid)
                    st.rerun()

                if is_del and c3.button("♻️ Ripristina", key=f"restore_{vid}"):
                    _restore_visita(conn, vid)
                    st.rerun()

                if st.session_state.get(f"edit_mode_{vid}", False):
                    new_json = st.text_area(
                        "Modifica payload (JSON)",
                        value=json.dumps(pj, ensure_ascii=False, indent=2),
                        height=260,
                        key=f"edit_ta_{vid}",
                    )
                    cc1, cc2 = st.columns([1,1])
                    if cc1.button("✅ Salva modifiche", key=f"save_{vid}"):
                        _update_visita(conn, vid, new_json)
                        st.session_state[f"edit_mode_{vid}"] = False
                        st.success("Modifiche salvate.")
                        st.rerun()
                    if cc2.button("❌ Annulla", key=f"cancel_{vid}"):
                        st.session_state[f"edit_mode_{vid}"] = False
                        st.rerun()

                st.divider()

                try:
                    pdf_ref = build_referto_oculistico_a4({**pj, "data": v.get("data_visita",""), "paziente": paziente_label}, LETTERHEAD)
                    st.download_button("⬇️ Referto A4", data=pdf_ref, file_name=f"referto_oculistico_{paziente_id}_{vid}.pdf", mime="application/pdf", key=f"r{vid}")
                except Exception:
                    st.warning("Referto non generabile da storico (payload non compatibile).")

                try:
                    pr = (pj.get("prescrizione") or {})
                    if pr:
                        pdf_pr = build_prescrizione_occhiali_a4(
                            {
                                "data": v.get("data_visita",""),
                                "paziente": paziente_label,
                                "lontano": pr.get("lontano"),
                                "intermedio": pr.get("intermedio"),
                                "vicino": pr.get("vicino"),
                                "lenti": pr.get("lenti") or [],
                            },
                            LETTERHEAD
                        )
                        st.download_button("⬇️ Prescrizione A4", data=pdf_pr, file_name=f"prescrizione_occhiali_{paziente_id}_{vid}.pdf", mime="application/pdf", key=f"p{vid}")
                except Exception:
                    pass

# redeploy
