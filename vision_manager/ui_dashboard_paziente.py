from __future__ import annotations

import json
import datetime as dt
from typing import Any, Dict, List, Optional
from collections.abc import Mapping

import matplotlib.pyplot as plt
import streamlit as st

from vision_manager.db import get_conn, init_db


# =========================================================
# HELPERS
# =========================================================

def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def _ph(conn) -> str:
    return "%s" if _is_pg(conn) else "?"


def _dict_row(cur, row):
    if isinstance(row, Mapping):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _normalize_row(d: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).lower(): v for k, v in (d or {}).items()}


def _parse_json(s: Any) -> Dict[str, Any]:
    try:
        obj = json.loads(s) if isinstance(s, str) else s
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _coerce_date(value) -> Optional[dt.date]:
    if isinstance(value, dt.date):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if value in (None, ""):
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return None


def _to_float(value) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace(",", ".")
        if not s:
            return None
        return float(s)
    except Exception:
        return None


def _parse_pair_values(s: Any):
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


def _calc_age(birth_date: Any) -> Optional[int]:
    b = _coerce_date(birth_date)
    if not b:
        return None
    today = dt.date.today()
    years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    return years if years >= 0 else None


def _fmt_rx_value(x: Any, is_ax: bool = False) -> str:
    if x in (None, ""):
        return "-"
    try:
        if is_ax:
            return str(int(round(float(x))))
        v = float(x)
        if abs(v) < 1e-9:
            return "0.00"
        return f"{v:+.2f}"
    except Exception:
        return str(x)


def _fmt_rx_pair(rx: Dict[str, Any], eye: str) -> str:
    eye_rx = (rx or {}).get(eye) or {}
    return f"SF {_fmt_rx_value(eye_rx.get('sf'))} · CIL {_fmt_rx_value(eye_rx.get('cyl'))} · AX {_fmt_rx_value(eye_rx.get('ax'), is_ax=True)}"


# =========================================================
# DB LOADERS
# =========================================================

def _pazienti_has_note(conn) -> bool:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='pazienti' AND column_name='note' LIMIT 1"
        )
        return bool(cur.fetchone())
    except Exception:
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass


def load_pazienti(conn) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    try:
        try:
            if _is_pg(conn):
                if _pazienti_has_note(conn):
                    cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti ORDER BY cognome, nome")
                else:
                    cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti ORDER BY cognome, nome")
            else:
                cur.execute("SELECT ID, Cognome, Nome, Data_Nascita, Note FROM Pazienti ORDER BY Cognome, Nome")
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = _normalize_row(_dict_row(cur, r))
                out.append(
                    {
                        "id": d.get("id"),
                        "cognome": d.get("cognome"),
                        "nome": d.get("nome"),
                        "data_nascita": d.get("data_nascita"),
                        "note": d.get("note"),
                    }
                )
            return out
        except Exception:
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass
            cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti_visivi ORDER BY cognome, nome")
            rows = cur.fetchall()
            return [_normalize_row(_dict_row(cur, r)) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def list_visite(conn, paziente_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(
                f"SELECT id, data_visita, dati_json, is_deleted, deleted_at FROM visite_visive WHERE paziente_id={ph} AND COALESCE(is_deleted,0)<>1 ORDER BY data_visita DESC, id DESC LIMIT 500",
                (paziente_id,),
            )
        except Exception:
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass
            cur.execute(
                f"SELECT id, data_visita, dati_json FROM visite_visive WHERE paziente_id={ph} ORDER BY data_visita DESC, id DESC LIMIT 500",
                (paziente_id,),
            )
        rows = cur.fetchall()
        return [_normalize_row(_dict_row(cur, r)) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =========================================================
# EXTRACTION
# =========================================================

def _patient_label(p: Dict[str, Any]) -> str:
    name = f"{(p.get('cognome') or '').strip()} {(p.get('nome') or '').strip()}".strip()
    age = _calc_age(p.get("data_nascita"))
    if age is not None:
        return f"{name} • {age} anni"
    return name or "Paziente"


def _extract_iop_cct(visite: List[Dict[str, Any]]):
    trend = []
    for row in visite:
        pj = _parse_json(row.get("dati_json") or "")
        if not pj:
            continue
        eo = pj.get("esame_obiettivo") or {}
        iop_od = _to_float(eo.get("pressione_endoculare_od"))
        iop_os = _to_float(eo.get("pressione_endoculare_os"))
        if iop_od is None and iop_os is None:
            od_old, os_old = _parse_pair_values(eo.get("pressione_endoculare") or "")
            iop_od, iop_os = _to_float(od_old), _to_float(os_old)

        cct_od = _to_float(eo.get("pachimetria_od"))
        cct_os = _to_float(eo.get("pachimetria_os"))
        if cct_od is None and cct_os is None:
            od_old, os_old = _parse_pair_values(eo.get("pachimetria") or "")
            cct_od, cct_os = _to_float(od_old), _to_float(os_old)

        d = _coerce_date(row.get("data_visita") or pj.get("data") or pj.get("data_visita"))
        if not d:
            continue
        if any(v is not None for v in [iop_od, iop_os, cct_od, cct_os]):
            trend.append({"date": d, "iop_od": iop_od, "iop_os": iop_os, "cct_od": cct_od, "cct_os": cct_os})
    trend.sort(key=lambda x: x["date"])
    return trend


def _extract_rx_trend(visite: List[Dict[str, Any]]):
    trend = []
    for row in visite:
        pj = _parse_json(row.get("dati_json") or "")
        if not pj:
            continue
        rx = pj.get("correzione_finale") or {}
        d = _coerce_date(row.get("data_visita") or pj.get("data") or pj.get("data_visita"))
        if not d:
            continue
        od = rx.get("od") or {}
        os_ = rx.get("os") or {}
        trend.append(
            {
                "date": d,
                "od_sf": _to_float(od.get("sf")),
                "od_cyl": _to_float(od.get("cyl")),
                "os_sf": _to_float(os_.get("sf")),
                "os_cyl": _to_float(os_.get("cyl")),
            }
        )
    trend.sort(key=lambda x: x["date"])
    return trend


def _extract_latest_prescription(visite: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for row in visite:
        pj = _parse_json(row.get("dati_json") or "")
        pr = pj.get("prescrizione") or {}
        if pr:
            return {
                "date": row.get("data_visita") or pj.get("data") or pj.get("data_visita") or "",
                "payload": pr,
                "visit": pj,
            }

        cf = pj.get("correzione_finale") or {}
        if isinstance(cf, dict) and (cf.get("od") or cf.get("os")):
            return {
                "date": row.get("data_visita") or pj.get("data") or pj.get("data_visita") or "",
                "payload": {
                    "lontano": cf,
                    "intermedio": {},
                    "vicino": {},
                    "lenti": [],
                },
                "visit": pj,
            }
    return None


# =========================================================
# RENDER
# =========================================================

def _render_info_card(title: str, lines: List[str]):
    st.markdown(f"### {title}")
    for line in lines:
        if line and str(line).strip():
            st.write(line)


def _render_iop_chart(trend: List[Dict[str, Any]]):
    if not trend:
        st.info("Nessun dato IOP presente nello storico.")
        return
    dates = [t["date"] for t in trend]
    od_vals = [t["iop_od"] for t in trend]
    os_vals = [t["iop_os"] for t in trend]

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


def _render_cct_chart(trend: List[Dict[str, Any]]):
    cct_trend = [t for t in trend if t.get("cct_od") is not None or t.get("cct_os") is not None]
    if not cct_trend:
        st.info("Nessun dato pachimetria presente nello storico.")
        return
    dates = [t["date"] for t in cct_trend]
    od_vals = [t["cct_od"] for t in cct_trend]
    os_vals = [t["cct_os"] for t in cct_trend]

    fig, ax = plt.subplots()
    ax.plot(dates, od_vals, marker="o", label="Pachimetria OD")
    ax.plot(dates, os_vals, marker="o", label="Pachimetria OS")
    ax.set_ylabel("µm")
    ax.set_xlabel("Data visita")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)


def _render_rx_chart(trend: List[Dict[str, Any]]):
    valid = [t for t in trend if any(v is not None for v in [t.get("od_sf"), t.get("os_sf"), t.get("od_cyl"), t.get("os_cyl")])]
    if not valid:
        st.info("Nessun dato di refrazione finale presente nello storico.")
        return

    dates = [t["date"] for t in valid]
    fig, ax = plt.subplots()
    ax.plot(dates, [t["od_sf"] for t in valid], marker="o", label="OD SF")
    ax.plot(dates, [t["os_sf"] for t in valid], marker="o", label="OS SF")
    ax.plot(dates, [t["od_cyl"] for t in valid], marker="o", linestyle=":", label="OD CIL")
    ax.plot(dates, [t["os_cyl"] for t in valid], marker="o", linestyle=":", label="OS CIL")
    ax.set_ylabel("Diottrie")
    ax.set_xlabel("Data visita")
    ax.legend(ncol=2)
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    st.pyplot(fig, clear_figure=True)


def _render_latest_visit(visite: List[Dict[str, Any]]):
    if not visite:
        st.info("Nessuna visita disponibile.")
        return
    row = visite[0]
    pj = _parse_json(row.get("dati_json") or "")
    eo = pj.get("esame_obiettivo") or {}
    ac = pj.get("acuita") or {}
    nat = ac.get("naturale") or {}
    cor = ac.get("corretta") or {}
    st.markdown("### Ultima visita")
    st.write(f"**Data visita:** {row.get('data_visita') or pj.get('data') or pj.get('data_visita') or '-'}")
    if str(pj.get("anamnesi") or "").strip():
        st.write(f"**Anamnesi:** {pj.get('anamnesi')}")

    info_cols = st.columns(2)
    with info_cols[0]:
        st.write(f"**AV naturale:** OD {nat.get('od','-')} · OS {nat.get('os','-')}")
        st.write(f"**AV corretta:** OD {cor.get('od','-')} · OS {cor.get('os','-')}")
        st.write(f"**IOP:** OD {eo.get('pressione_endoculare_od','-')} · OS {eo.get('pressione_endoculare_os','-')}")
        st.write(f"**Pachimetria:** OD {eo.get('pachimetria_od','-')} · OS {eo.get('pachimetria_os','-')}")
    with info_cols[1]:
        rx_fin = pj.get("correzione_finale") or {}
        if rx_fin:
            st.write(f"**RX finale OD:** {_fmt_rx_pair(rx_fin, 'od')}")
            st.write(f"**RX finale OS:** {_fmt_rx_pair(rx_fin, 'os')}")
            add_val = rx_fin.get("add")
            if add_val not in (None, ""):
                st.write(f"**Addizione:** {_fmt_rx_value(add_val)}")
        note = pj.get("note") or ""
        if str(note).strip():
            st.write(f"**Note cliniche:** {note}")



def _render_latest_prescription(latest_pr: Optional[Dict[str, Any]]):
    st.markdown("### Ultima prescrizione")
    if not latest_pr:
        st.info("Nessuna prescrizione disponibile.")
        return

    pr = latest_pr["payload"]
    st.write(f"**Data:** {latest_pr.get('date') or '-'}")
    lontano = pr.get("lontano") or {}
    intermedio = pr.get("intermedio") or {}
    vicino = pr.get("vicino") or {}

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Lontano**")
        st.write(f"OD: {_fmt_rx_pair(lontano, 'od')}")
        st.write(f"OS: {_fmt_rx_pair(lontano, 'os')}")
        if intermedio:
            st.write("**Intermedio**")
            st.write(f"OD: {_fmt_rx_pair(intermedio, 'od')}")
            st.write(f"OS: {_fmt_rx_pair(intermedio, 'os')}")
    with col2:
        if vicino:
            st.write("**Vicino**")
            st.write(f"OD: {_fmt_rx_pair(vicino, 'od')}")
            st.write(f"OS: {_fmt_rx_pair(vicino, 'os')}")
        lenti = pr.get("lenti") or []
        if lenti:
            st.write("**Lenti consigliate:**")
            for lente in lenti:
                st.write(f"- {lente}")


def ui_dashboard_paziente():
    st.title("Dashboard Paziente")

    try:
        conn = get_conn()
        init_db(conn)
    except Exception as e:
        st.error("Impossibile connettersi al database.")
        st.exception(e)
        st.stop()

    pazienti = load_pazienti(conn)
    if not pazienti:
        st.warning("Nessun paziente presente nel database.")
        return

    def _fmt_paziente(p: Dict[str, Any]) -> str:
        label = f"{(p.get('cognome') or '').strip()} {(p.get('nome') or '').strip()}".strip()
        dn = p.get("data_nascita") or ""
        age = _calc_age(dn)
        extra = []
        if dn:
            extra.append(str(dn))
        if age is not None:
            extra.append(f"{age} anni")
        return f"{label} ({' · '.join(extra)})" if extra else label

    default_index = 0
    last_pid = st.session_state.get("vision_last_pid")
    if last_pid is not None:
        for i, p in enumerate(pazienti):
            if str(p.get("id")) == str(last_pid):
                default_index = i
                break

    paziente = st.selectbox(
        "Seleziona paziente",
        pazienti,
        index=default_index,
        format_func=_fmt_paziente,
        key="dashboard_paziente_sel",
    )

    paziente_id = int(paziente["id"])
    st.session_state["vision_last_pid"] = paziente_id

    title_col, meta_col = st.columns([2, 1])
    with title_col:
        st.subheader(_patient_label(paziente))
    with meta_col:
        dn = paziente.get("data_nascita") or "-"
        eta = _calc_age(paziente.get("data_nascita"))
        st.write(f"**Data nascita:** {dn}")
        if eta is not None:
            st.write(f"**Età:** {eta} anni")

    note = (paziente.get("note") or "").strip()
    if note:
        st.info(note)

    visite = list_visite(conn, paziente_id)
    iop_cct_trend = _extract_iop_cct(visite)
    rx_trend = _extract_rx_trend(visite)
    latest_pr = _extract_latest_prescription(visite)

    t1, t2, t3, t4 = st.tabs(["📊 Dashboard clinica", "👁 Visione", "📄 Documenti", "🗂 Storico sintetico"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            _render_info_card(
                "Anagrafica",
                [
                    f"**Paziente:** {(paziente.get('cognome') or '').strip()} {(paziente.get('nome') or '').strip()}",
                    f"**Data nascita:** {paziente.get('data_nascita') or '-'}",
                    f"**Età:** {_calc_age(paziente.get('data_nascita'))} anni" if _calc_age(paziente.get('data_nascita')) is not None else "",
                ],
            )
        with c2:
            st.markdown("### Riepilogo")
            st.write(f"**Numero visite:** {len(visite)}")
            if visite:
                st.write(f"**Ultima visita:** {visite[0].get('data_visita') or '-'}")
                st.write(f"**Prima visita disponibile:** {visite[-1].get('data_visita') or '-'}")

        st.markdown("---")
        _render_latest_visit(visite)
        st.markdown("---")
        _render_latest_prescription(latest_pr)

    with t2:
        st.markdown("### Pressione oculare nel tempo")
        _render_iop_chart(iop_cct_trend)
        st.markdown("### Pachimetria nel tempo")
        _render_cct_chart(iop_cct_trend)
        st.markdown("### Refrazione finale nel tempo")
        _render_rx_chart(rx_trend)

    with t3:
        _render_latest_prescription(latest_pr)
        st.markdown("---")
        _render_latest_visit(visite)

    with t4:
        if not visite:
            st.info("Nessuna visita disponibile.")
        else:
            for row in visite:
                pj = _parse_json(row.get("dati_json") or "")
                with st.expander(f"Visita #{row.get('id')} - {row.get('data_visita') or '-'}"):
                    st.write(f"**Anamnesi:** {pj.get('anamnesi') or '-'}")
                    eo = pj.get("esame_obiettivo") or {}
                    st.write(
                        f"**IOP:** OD {eo.get('pressione_endoculare_od','-')} · OS {eo.get('pressione_endoculare_os','-')}"
                    )
                    st.write(
                        f"**Pachimetria:** OD {eo.get('pachimetria_od','-')} · OS {eo.get('pachimetria_os','-')}"
                    )
                    rx_fin = pj.get("correzione_finale") or {}
                    if rx_fin:
                        st.write(f"**RX finale OD:** {_fmt_rx_pair(rx_fin, 'od')}")
                        st.write(f"**RX finale OS:** {_fmt_rx_pair(rx_fin, 'os')}")
                    note = pj.get("note") or ""
                    if str(note).strip():
                        st.write(f"**Note:** {note}")


if __name__ == "__main__":
    ui_dashboard_paziente()
