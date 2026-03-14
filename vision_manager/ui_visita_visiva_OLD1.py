from __future__ import annotations
import datetime as dt
import json
from typing import Any, Dict, List
from collections.abc import Mapping
import streamlit as st
import matplotlib.pyplot as plt

import pandas as pd
from vision_manager.ui_kit import inject_ui, topbar, card_open, card_close, badge, callout, cta_button
# ---------- Apple-like (lightweight) CSS ----------
def _load_payload_into_form(pj: dict):
    """Carica un payload visita nel form (session_state). Deve essere chiamata PRIMA di creare i widget."""
    if not isinstance(pj, dict):
        return

    # Data visita: per default oggi (così quando salvi crei una nuova visita)
    st.session_state.setdefault("data_visita", dt.date.today())

    st.session_state["anamnesi"] = pj.get("anamnesi") or ""
    st.session_state["note_visita"] = pj.get("note") or pj.get("note_visita") or ""

    # Acuità
    ac = pj.get("acuita") or {}
    nat = ac.get("naturale") or {}
    cor = ac.get("corretta") or {}

    for k_src, key in [("od","avn_od"),("os","avn_os"),("oo","avn_oo")]:
        if k_src in nat:
            st.session_state[key] = nat.get(k_src) or st.session_state.get(key)
    for k_src, key in [("od","avc_od"),("os","avc_os"),("oo","avc_oo")]:
        if k_src in cor:
            st.session_state[key] = cor.get(k_src) or st.session_state.get(key)

    # Esame obiettivo
    eo = pj.get("esame_obiettivo") or {}
    for field in ("congiuntiva","cornea","camera_anteriore","cristallino","vitreo","fondo_oculare","pressione_endoculare","pressione_endoculare_od","pressione_endoculare_os","pachimetria","pachimetria_od","pachimetria_os"):
        if field in eo:
            st.session_state[field] = eo.get(field) or ""

    # Retrocompatibilità: se mancano i nuovi campi, prova a derivarli dai campi legacy "OD/OS"
    try:
        if not st.session_state.get("pressione_endoculare_od") and not st.session_state.get("pressione_endoculare_os"):
            od_iop, os_iop = _parse_pair_values(st.session_state.get("pressione_endoculare") or "")
            if od_iop is not None:
                st.session_state["pressione_endoculare_od"] = str(od_iop).rstrip("0").rstrip(".")
            if os_iop is not None:
                st.session_state["pressione_endoculare_os"] = str(os_iop).rstrip("0").rstrip(".")
        if not st.session_state.get("pachimetria_od") and not st.session_state.get("pachimetria_os"):
            od_cct, os_cct = _parse_pair_values(st.session_state.get("pachimetria") or "")
            if od_cct is not None:
                st.session_state["pachimetria_od"] = str(int(od_cct)) if float(od_cct).is_integer() else str(od_cct)
            if os_cct is not None:
                st.session_state["pachimetria_os"] = str(int(os_cct)) if float(os_cct).is_integer() else str(os_cct)
    except Exception:
        pass

    # Correzione abituale
    ca = pj.get("correzione_abituale") or {}
    od_ab = ca.get("od") or {}
    os_ab = ca.get("os") or {}
    st.session_state["rx_ab_od_sf"] = float(od_ab.get("sf", 0.0) or 0.0)
    st.session_state["rx_ab_od_cyl"] = float(od_ab.get("cyl", 0.0) or 0.0)
    st.session_state["rx_ab_od_ax"] = int(od_ab.get("ax", 0) or 0)

    st.session_state["rx_ab_os_sf"] = float(os_ab.get("sf", 0.0) or 0.0)
    st.session_state["rx_ab_os_cyl"] = float(os_ab.get("cyl", 0.0) or 0.0)
    st.session_state["rx_ab_os_ax"] = int(os_ab.get("ax", 0) or 0)

    st.session_state["add_ab"] = float(ca.get("add", 0.0) or 0.0)

    # Correzione finale
    cf = pj.get("correzione_finale") or {}
    od = cf.get("od") or {}
    os_ = cf.get("os") or {}
    st.session_state["rx_fin_od_sf"] = float(od.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_od_cyl"] = float(od.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_od_ax"] = int(od.get("ax", 0) or 0)

    st.session_state["rx_fin_os_sf"] = float(os_.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_os_cyl"] = float(os_.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_os_ax"] = int(os_.get("ax", 0) or 0)

    st.session_state["add_fin"] = float(cf.get("add", 0.0) or 0.0)

    # Lenti consigliate
    pr = pj.get("prescrizione") or {}
    st.session_state["lenti_sel"] = pr.get("lenti") or []

from vision_manager.db import get_conn, init_db
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"

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


def _reset_visita_form_state():
    """Azzera il form visita quando si cambia paziente."""
    prefixes = (
        "avn_", "ava_", "avc_",
        "rx_ab_", "add_ab",
        "rx_fin_", "add_fin",
        "anamnesi", "note_visita",
        "congiuntiva", "cornea", "camera_anteriore",
        "cristallino", "vitreo", "fondo_oculare",
        "pressione_endoculare", "pressione_endoculare_od", "pressione_endoculare_os",
        "pachimetria", "pachimetria_od", "pachimetria_os",
        "lenti_sel",
        "data_visita",
        "vm_last_loaded_visita_id",
    )
    to_del = [k for k in list(st.session_state.keys()) if k.startswith(prefixes)]
    for k in to_del:
        del st.session_state[k]


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
    if isinstance(row, Mapping):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).lower(): v for k, v in (d or {}).items()}


def _load_pazienti_vision(conn) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti_visivi ORDER BY cognome, nome")
        rows = cur.fetchall()
        return [_normalize_row(_dict_row(cur, r)) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _load_pazienti(conn) -> List[Dict[str, Any]]:
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
    ph = "%s"

    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='pazienti'
        AND column_name='note'
        LIMIT 1
        """
    )
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
    pid = row["id"] if isinstance(row, dict) else row[0]
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
        try:
            cur.close()
        except Exception:
            pass


def _update_visita(conn, visita_id: int, dati_json: str):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}", (dati_json, visita_id))
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _soft_delete_visita(conn, visita_id: int):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(f"UPDATE visite_visive SET is_deleted={ph}, deleted_at={ph} WHERE id={ph}", (1, dt.datetime.now().isoformat(timespec="seconds"), visita_id))
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
            cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}", (json.dumps(obj, ensure_ascii=False), visita_id))
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _restore_visita(conn, visita_id: int):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(f"UPDATE visite_visive SET is_deleted={ph}, deleted_at={ph} WHERE id={ph}", (0, None, visita_id))
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
            cur.execute(f"UPDATE visite_visive SET dati_json={ph} WHERE id={ph}", (json.dumps(obj, ensure_ascii=False), visita_id))
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _list_visite(conn, paziente_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            if include_deleted:
                cur.execute(
                    f"SELECT id, data_visita, dati_json, is_deleted, deleted_at FROM visite_visive WHERE paziente_id={ph} ORDER BY data_visita DESC, id DESC LIMIT 200",
                    (paziente_id,),
                )
            else:
                cur.execute(
                    f"SELECT id, data_visita, dati_json, is_deleted, deleted_at FROM visite_visive WHERE paziente_id={ph} AND COALESCE(is_deleted,0)<>1 ORDER BY data_visita DESC, id DESC LIMIT 200",
                    (paziente_id,),
                )
        except Exception:
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass
            cur.execute(
                f"SELECT id, data_visita, dati_json FROM visite_visive WHERE paziente_id={ph} ORDER BY data_visita DESC, id DESC LIMIT 200",
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


def _parse_pair_values(s: str):
    if not s:
        return (None, None)
    txt = str(s).strip().replace(",", "/").replace(";", "/").replace("\\", "/")
    parts = [p.strip() for p in txt.split("/") if p.strip()]
    if len(parts) == 1:
        try:
            v = float(parts[0])
            return (v, v)
        except Exception:
            return (None, None)
    try:
        od = float(parts[0])
    except Exception:
        od = None
    try:
        os_ = float(parts[1])
    except Exception:
        os_ = None
    return (od, os_)


def _iop_adjusted(iop, cct, ref_cct: float = 540.0):
    if iop is None or cct is None:
        return None
    delta = (ref_cct - cct) / 10.0 * 0.7
    return float(iop + delta)


def _clinical_attention(iop_od, iop_os, cct_od, cct_os):
    out = {
        "od": {"flag": False, "reason": "", "adj": None},
        "os": {"flag": False, "reason": "", "adj": None},
    }
    for eye in ("od", "os"):
        iop = iop_od if eye == "od" else iop_os
        cct = cct_od if eye == "od" else cct_os
        adj = _iop_adjusted(iop, cct)

        reasons = []
        flag = False

        if iop is not None and iop >= 21:
            flag = True
            reasons.append("IOP ≥ 21 mmHg")

        if cct is not None and cct < 500 and iop is not None and iop >= 18:
            flag = True
            reasons.append("CCT < 500 µm con IOP ≥ 18 (possibile sottostima)")

        if adj is not None and adj >= 21:
            flag = True
            reasons.append(f"IOP stimata (da CCT) ≈ {adj:.1f} mmHg")

        out[eye]["flag"] = flag
        out[eye]["reason"] = "; ".join(reasons)
        out[eye]["adj"] = adj
    return out


def _format_paz(p) -> str:
    dn = p.get("data_nascita") or ""
    return f"{p['cognome']} {p['nome']} (ID {p['id']}) {dn}".strip()


def _rx_input(label: str, key_prefix: str):
    c1, c2, c3 = st.columns([1, 1, 1])

    k_sf = f"{key_prefix}_sf"
    k_cyl = f"{key_prefix}_cyl"
    k_ax = f"{key_prefix}_ax"

    st.session_state.setdefault(k_sf, 0.0)
    st.session_state.setdefault(k_cyl, 0.0)
    st.session_state.setdefault(k_ax, 0)

    sf = c1.number_input(f"{label} SF", step=0.25, format="%0.2f", key=k_sf)
    cyl = c2.number_input(f"{label} CIL", step=0.25, format="%0.2f", key=k_cyl)
    ax = c3.number_input(f"{label} AX (0-180)", min_value=0, max_value=180, step=1, key=k_ax)
    return {"sf": float(sf), "cyl": float(cyl), "ax": int(ax)}


def ui_visita_visiva():
    # Carica la visita richiesta dallo storico con doppio passaggio controllato.
    # 1° pass: applica il payload al session_state e rilancia.
    if st.session_state.get("vm_pending_payload") is not None and not st.session_state.get("vm_payload_loaded_pass"):
        pj_pending = st.session_state.pop("vm_pending_payload")
        st.session_state["vm_last_loaded_visita_id"] = st.session_state.pop("vm_pending_visita_id", None)
        st.session_state["vm_skip_reset_once"] = True
        _load_payload_into_form(pj_pending if isinstance(pj_pending, dict) else {})
        st.session_state["vm_payload_loaded_pass"] = True
        st.rerun()

    # 2° pass: i widget vengono costruiti leggendo i valori già presenti.
    if st.session_state.pop("vm_payload_loaded_pass", False):
        st.session_state["vm_skip_reset_once"] = True

    inject_ui("assets/ui.css")
    topbar("Vision Manager", "Visita oculistica • The Organism", right="Dr. Cirillo")

    try:
        with st.spinner("Connessione al database..."):
            conn = get_conn()
        init_db(conn)
    except Exception as e:
        st.error("Impossibile connettersi al database. Controlla DATABASE_URL nei Secrets di Streamlit Cloud.")
        st.exception(e)
        st.stop()

    tab_paz, tab_vis = st.tabs(["👤 Anagrafica (Gestionale)", "🗓️ Visita oculistica"])

    with tab_paz:
        card_open("Anagrafica paziente", "Crea / aggiorna pazienti nel DB gestionale", "👤")
        st.markdown("### Aggiungi paziente (DB Gestionale)")
        c1, c2, c3 = st.columns([1, 1, 1])
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        data_nascita = c3.text_input("Data nascita (YYYY-MM-DD)", value="")
        note = st.text_area("Note", height=90, key="note_anagrafica")

        if cta_button("💾 Salva paziente", key="save_paziente", use_container_width=False):
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
        df_paz = pd.DataFrame(paz)

        try:
            evt = st.dataframe(
                df_paz,
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
            )
            sel_rows = evt.selection.rows
        except Exception:
            sel_rows = []

        if sel_rows:
            r = df_paz.iloc[sel_rows[0]].to_dict()
            try:
                st.session_state["vision_last_pid"] = int(r.get("id"))
                st.success(f"Paziente selezionato: {r.get('cognome','')} {r.get('nome','')} (ID {r.get('id')})")
            except Exception:
                pass
        else:
            st.caption("Se la tabella non è selezionabile (versione Streamlit), usa il menu qui sotto.")
            psel_quick = st.selectbox("Selezione rapida paziente", paz, format_func=_format_paz, key="paz_quick_sel")
            if psel_quick:
                st.session_state["vision_last_pid"] = int(psel_quick.get("id") or 0)

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
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                        st.error(f"Impossibile aggiornare anagrafica su tabella Pazienti: {e}")
                finally:
                    try:
                        cur2.close()
                    except Exception:
                        pass

        card_close()

    with tab_vis:
        paz = _load_pazienti(conn)
        if not paz:
            st.info("Prima crea almeno un paziente nella tab 'Anagrafica (Gestionale)'.")
            return

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

        if "vm_paz_sel_prev" not in st.session_state and paz:
            try:
                st.session_state["vm_paz_sel_prev"] = int(paz[default_idx].get("id") or 0)
            except Exception:
                st.session_state["vm_paz_sel_prev"] = None

        def _on_change_paziente():
            sel = st.session_state.get("vm_paz_sel")
            new_pid = None
            try:
                if isinstance(sel, dict):
                    new_pid = int(sel.get("id") or 0)
            except Exception:
                new_pid = None

            if st.session_state.pop("vm_skip_reset_once", False):
                st.session_state["vm_paz_sel_prev"] = new_pid
                if new_pid is not None:
                    st.session_state["vision_last_pid"] = new_pid
                return

            old_pid = st.session_state.get("vm_paz_sel_prev")
            if old_pid != new_pid:
                _reset_visita_form_state()
                st.session_state["vm_paz_sel_prev"] = new_pid
                if new_pid is not None:
                    st.session_state["vision_last_pid"] = new_pid

        psel = st.selectbox(
            "Seleziona paziente",
            paz,
            format_func=_format_paz,
            index=default_idx,
            key="vm_paz_sel",
            on_change=_on_change_paziente,
        )
        paziente_id = int(psel["id"])
        paziente_label = f"{psel.get('cognome','')} {psel.get('nome','')}".strip()
        badge(f"Paziente: {paziente_label} • ID {paziente_id}")

        st.session_state.setdefault("data_visita", dt.date.today())
        data_visita = st.date_input("Data visita", key="data_visita")
        st.session_state.setdefault("anamnesi", "")
        anamnesi = st.text_area(
            "Anamnesi",
            height=110,
            key="anamnesi",
        )

        card_open("Acuità visiva", "Naturale • Corretta", "👁️")
        st.markdown("### Acuità visiva")
        col = st.columns(2)
        with col[0]:
            st.caption("Naturale")
            st.session_state.setdefault("avn_od", "")
            st.session_state.setdefault("avn_os", "")
            st.session_state.setdefault("avn_oo", "")
            avn_od = st.text_input("OD (naturale)", key="avn_od")
            avn_os = st.text_input("OS (naturale)", key="avn_os")
            avn_oo = st.text_input("OO (naturale)", key="avn_oo")
        with col[1]:
            st.caption("Corretta")
            st.session_state.setdefault("avc_od", "")
            st.session_state.setdefault("avc_os", "")
            st.session_state.setdefault("avc_oo", "")
            avc_od = st.text_input("OD (corretta)", key="avc_od")
            avc_os = st.text_input("OS (corretta)", key="avc_os")
            avc_oo = st.text_input("OO (corretta)", key="avc_oo")
        card_close()

        card_open("Esame obiettivo", "Campi descrittivi OD/OS", "🧾")
        st.markdown("### Esame obiettivo")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.setdefault("congiuntiva","")
            congiuntiva = st.text_input("Congiuntiva (OD/OS)", key="congiuntiva")
            st.session_state.setdefault("cornea","")
            cornea = st.text_input("Cornea (OD/OS)", key="cornea")
            st.session_state.setdefault("camera_anteriore","")
            camera_anteriore = st.text_input("Camera anteriore (OD/OS)", key="camera_anteriore")
        with c2:
            st.session_state.setdefault("cristallino","")
            cristallino = st.text_input("Cristallino (OD/OS)", key="cristallino")
            st.session_state.setdefault("vitreo","")
            vitreo = st.text_input("Vitreo (OD/OS)", key="vitreo")
            st.session_state.setdefault("fondo_oculare","")
            fondo_oculare = st.text_input("Fondo oculare (OD/OS)", key="fondo_oculare")
        card_close()

        card_open("IOP e Pachimetria", "Pressione endoculare e spessore corneale separati OD/OS", "🧿")
        st.markdown("### IOP e Pachimetria")
        st.caption("Inserisci i valori separati per OD e OS. Se hai dati storici '16/15' o '520/505' verranno letti in automatico.")

        ci1, ci2 = st.columns(2)
        with ci1:
            st.session_state.setdefault("pressione_endoculare_od", "")
            st.text_input("IOP OD (mmHg)", key="pressione_endoculare_od", placeholder="es. 16")
        with ci2:
            st.session_state.setdefault("pressione_endoculare_os", "")
            st.text_input("IOP OS (mmHg)", key="pressione_endoculare_os", placeholder="es. 15")

        cp1, cp2 = st.columns(2)
        with cp1:
            st.session_state.setdefault("pachimetria_od", "")
            st.text_input("Pachimetria OD (µm)", key="pachimetria_od", placeholder="es. 520")
        with cp2:
            st.session_state.setdefault("pachimetria_os", "")
            st.text_input("Pachimetria OS (µm)", key="pachimetria_os", placeholder="es. 505")

        def _to_float(x):
            try:
                return float(str(x).replace(",", ".").strip())
            except Exception:
                return None

        iop_od = _to_float(st.session_state.get("pressione_endoculare_od", ""))
        iop_os = _to_float(st.session_state.get("pressione_endoculare_os", ""))
        if iop_od is None and iop_os is None:
            iop_od, iop_os = _parse_pair_values(st.session_state.get("pressione_endoculare", ""))

        cct_od = _to_float(st.session_state.get("pachimetria_od", ""))
        cct_os = _to_float(st.session_state.get("pachimetria_os", ""))
        if cct_od is None and cct_os is None:
            cct_od, cct_os = _parse_pair_values(st.session_state.get("pachimetria", ""))

        att = _clinical_attention(iop_od, iop_os, cct_od, cct_os)

        with st.expander("🔎 Rapporto IOP / Pachimetria (screening)", expanded=False):
            st.caption("Indicatore di attenzione clinica (screening). Non sostituisce la valutazione specialistica.")
            cA, cB = st.columns(2)
            with cA:
                st.write("**OD**")
                if att["od"].get("adj") is not None:
                    st.write(f"IOP stimata (da CCT): **{att['od']['adj']:.1f} mmHg**")
                if att["od"]["flag"]:
                    st.warning(att["od"]["reason"] or "Possibile attenzione clinica.")
                else:
                    st.success("Nessun flag (con i dati inseriti).")
            with cB:
                st.write("**OS**")
                if att["os"].get("adj") is not None:
                    st.write(f"IOP stimata (da CCT): **{att['os']['adj']:.1f} mmHg**")
                if att["os"]["flag"]:
                    st.warning(att["os"]["reason"] or "Possibile attenzione clinica.")
                else:
                    st.success("Nessun flag (con i dati inseriti).")
        card_close()

        card_open("Correzione abituale", "Lontano", "🕶️")
        st.markdown("### Correzione abituale (lontano)")
        rx_ab_od = _rx_input("OD abituale", "rx_ab_od")
        rx_ab_os = _rx_input("OS abituale", "rx_ab_os")
        add_ab = st.number_input("Addizione da vicino (abituale)", step=0.25, format="%0.2f", key="add_ab")
        card_close()

        card_open("Correzione finale", "Lontano • Intermedio • Vicino", "✅")
        st.markdown("### Correzione finale (lontano)")
        rx_fin_od = _rx_input("OD finale", "rx_fin_od")
        rx_fin_os = _rx_input("OS finale", "rx_fin_os")
        add_fin = st.number_input("Addizione da vicino (finale)", step=0.25, format="%0.2f", key="add_fin")

        def _near(rx, add):
            return {"sf": float(rx["sf"]) + float(add), "cyl": float(rx["cyl"]), "ax": int(rx["ax"])}

        vicino_od = _near(rx_fin_od, add_fin)
        vicino_os = _near(rx_fin_os, add_fin)
        inter_od = _near(rx_fin_od, float(add_fin) / 2.0)
        inter_os = _near(rx_fin_os, float(add_fin) / 2.0)
        card_close()

        card_open("Note e lenti consigliate", "Seleziona solo ciò che vuoi stampare", "📝")
        st.session_state.setdefault("lenti_sel", [])
        lenti_sel = st.multiselect("Lenti consigliate (mostra solo selezionate)", LENTI_OPTIONS, key="lenti_sel")
        st.session_state.setdefault("note_visita", "")
        note_v = st.text_area("Note visita", height=100, key="note_visita")
        card_close()

        payload = {
            "tipo_visita": "oculistica",
            "data": str(data_visita),
            "paziente": {"id": paziente_id, "nome": psel.get("nome"), "cognome": psel.get("cognome"), "data_nascita": psel.get("data_nascita")},
            "anamnesi": anamnesi,
            "acuita": {
                "naturale": {"od": avn_od, "os": avn_os, "oo": avn_oo},
                "corretta": {"od": avc_od, "os": avc_os, "oo": avc_oo},
            },
            "esame_obiettivo": {
                "congiuntiva": congiuntiva,
                "cornea": cornea,
                "camera_anteriore": camera_anteriore,
                "cristallino": cristallino,
                "vitreo": vitreo,
                "fondo_oculare": fondo_oculare,
                "pressione_endoculare": f"{st.session_state.get('pressione_endoculare_od','')}/{st.session_state.get('pressione_endoculare_os','')}".strip("/"),
                "pressione_endoculare_od": st.session_state.get("pressione_endoculare_od", ""),
                "pressione_endoculare_os": st.session_state.get("pressione_endoculare_os", ""),
                "pachimetria": f"{st.session_state.get('pachimetria_od','')}/{st.session_state.get('pachimetria_os','')}".strip("/"),
                "pachimetria_od": st.session_state.get("pachimetria_od", ""),
                "pachimetria_os": st.session_state.get("pachimetria_os", ""),
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

        card_open("Azioni", "Salvataggio e documenti", "⚡")
        csave, cpdf1, cpdf2 = st.columns([1,1,1])
        with csave:
            if cta_button("💾 Salva visita (DB)", key="save_visita", use_container_width=True):
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
                    LETTERHEAD,
                )
                st.download_button("⬇️ Scarica Prescrizione A4", data=pdf_bytes, file_name=f"prescrizione_occhiali_{paziente_id}_{data_visita}.pdf", mime="application/pdf")
        card_close()

        st.markdown("---")
        st.markdown("---")
        card_open("Storico visite", "Richiama, duplica e visualizza trend clinici", "🗓️")
        st.markdown("### Storico visite")
        show_deleted = st.checkbox("Mostra anche le visite eliminate", value=False)
        visite = _list_visite(conn, paziente_id, include_deleted=show_deleted)

        def _to_float_local(x):
            try:
                if x is None:
                    return None
                if isinstance(x, (int, float)):
                    return float(x)
                s = str(x).strip().replace(",", ".")
                if s == "":
                    return None
                return float(s)
            except Exception:
                return None

        trend = []
        for v0 in visite:
            pj0 = _parse_json(v0.get("dati_json") or "")
            if not isinstance(pj0, dict):
                continue

            eo0 = pj0.get("esame_obiettivo") or {}
            iop_od0 = _to_float_local(eo0.get("pressione_endoculare_od"))
            iop_os0 = _to_float_local(eo0.get("pressione_endoculare_os"))

            if iop_od0 is None and iop_os0 is None:
                od_old, os_old = _parse_pair_values(eo0.get("pressione_endoculare") or "")
                iop_od0 = _to_float_local(od_old)
                iop_os0 = _to_float_local(os_old)

            if iop_od0 is None and iop_os0 is None:
                continue

            d_raw = v0.get("data_visita") or pj0.get("data") or pj0.get("data_visita") or ""
            try:
                d0 = dt.date.fromisoformat(str(d_raw)[:10])
            except Exception:
                continue

            trend.append((d0, iop_od0, iop_os0))

        if trend:
            trend.sort(key=lambda x: x[0])
            dates = [t[0] for t in trend]
            od_vals = [t[1] for t in trend]
            os_vals = [t[2] for t in trend]

            st.markdown("#### 📈 Andamento IOP (OD/OS) nel tempo")
            fig, ax = plt.subplots()
            ax.plot(dates, od_vals, marker="o", label="IOP OD")
            ax.plot(dates, os_vals, marker="o", label="IOP OS")
            ax.axhline(21, linestyle="--", linewidth=1, label="Soglia 21 mmHg")
            ax.set_ylabel("mmHg")
            ax.set_xlabel("Data visita")
            ax.legend()
            ax.grid(True, alpha=0.25)
            fig.autofmt_xdate()
            st.pyplot(fig, clear_figure=True)
        else:
            st.info("Nessun dato IOP presente nello storico (compila IOP OD/OS e salva almeno una visita).")

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

                a1, a2, a3, a4 = st.columns([1.2,1.6,1,1])
                if a1.button("📥 Carica nel form", key=f"load_{vid}"):
                    st.session_state["vm_skip_reset_once"] = True
                    st.session_state["vm_pending_payload"] = pj if isinstance(pj, dict) else {}
                    st.session_state["vm_pending_visita_id"] = vid
                    st.rerun()
                if a2.button("🧬 Duplica come nuova visita", key=f"dup_{vid}"):
                    try:
                        pj2 = dict(pj) if isinstance(pj, dict) else {"raw": pj}
                        _insert_visita(conn, paziente_id, dt.date.today().isoformat(), json.dumps(pj2, ensure_ascii=False))
                        st.success("Duplicata come nuova visita (data odierna).")
                        st.rerun()
                    except Exception as e:
                        st.error("Errore durante duplicazione.")
                        st.exception(e)

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
                            LETTERHEAD,
                        )
                        st.download_button("⬇️ Prescrizione A4", data=pdf_pr, file_name=f"prescrizione_occhiali_{paziente_id}_{vid}.pdf", mime="application/pdf", key=f"p{vid}")
                except Exception:
                    pass

        card_close()
