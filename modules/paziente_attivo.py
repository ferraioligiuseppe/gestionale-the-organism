# -*- coding: utf-8 -*-
"""Gestione del 'paziente attivo' globale in tutto il gestionale.

Il paziente attivo è memorizzato in st.session_state["paziente_attivo_id"]
e in st.session_state["paziente_attivo_record"] (dict completo).

Usage:
    from modules.paziente_attivo import header_paziente_attivo
    paz_id = header_paziente_attivo(conn)
    if not paz_id:
        return  # nessun paziente selezionato

In cima alla pagina compare un banner con i dati del paziente e un bottone
"Cambia paziente" che apre un dialog con la tabella ag-grid.
"""
from __future__ import annotations
import datetime
import streamlit as st


KEY_ID = "paziente_attivo_id"
KEY_REC = "paziente_attivo_record"


# ════════════════════════════════════════════════════════════════════
#  HELPERS DATI
# ════════════════════════════════════════════════════════════════════

def _fmt_dn(iso) -> str:
    if not iso:
        return ""
    try:
        return datetime.date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _eta_anni(dn):
    try:
        d = datetime.date.fromisoformat(str(dn)[:10])
        return (datetime.date.today() - d).days // 365
    except Exception:
        return None


def _badge_stato(stato: str) -> str:
    s = (stato or "ATTIVO").upper()
    if s == "ATTIVO":
        return "🟢"
    if s == "SOSPESO":
        return "🟡"
    return "⚫"


def _carica_paziente_record(conn, paz_id):
    """Carica il record completo di un paziente."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _carica_lista_pazienti(_conn):
    """Lista pazienti ATTIVI per il dialog di selezione."""
    conn = _conn
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cognome, nome, data_nascita, telefono, stato_paziente "
            "FROM pazienti "
            "WHERE COALESCE(stato_paziente, 'ATTIVO') = 'ATTIVO' "
            "ORDER BY cognome, nome"
        )
        rows = cur.fetchall() or []
        cols = [d[0] for d in cur.description] if cur.description else []
        return [r if isinstance(r, dict) else dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


# ════════════════════════════════════════════════════════════════════
#  API PUBBLICA
# ════════════════════════════════════════════════════════════════════

def paziente_attivo_id() -> int | None:
    """Ritorna l'ID del paziente attivo, o None."""
    pid = st.session_state.get(KEY_ID)
    if pid is None:
        return None
    try:
        return int(pid)
    except (ValueError, TypeError):
        return None


def paziente_attivo_record() -> dict | None:
    """Ritorna il record completo del paziente attivo, o None."""
    return st.session_state.get(KEY_REC)


def set_paziente_attivo(conn, paz_id: int) -> None:
    """Imposta il paziente attivo. Carica e cachea il record completo."""
    st.session_state[KEY_ID] = int(paz_id)
    rec = _carica_paziente_record(conn, paz_id)
    st.session_state[KEY_REC] = rec or {}


def reset_paziente_attivo() -> None:
    """Pulisce la selezione del paziente attivo."""
    st.session_state.pop(KEY_ID, None)
    st.session_state.pop(KEY_REC, None)


# ════════════════════════════════════════════════════════════════════
#  DIALOG SELEZIONE
# ════════════════════════════════════════════════════════════════════

@st.dialog("👤 Seleziona paziente", width="large")
def _dialog_seleziona(conn):
    pazienti = _carica_lista_pazienti(conn)
    if not pazienti:
        st.info("Nessun paziente attivo registrato.")
        if st.button("Chiudi"):
            st.rerun()
        return

    # Filtro testuale rapido
    cerca = st.text_input(
        "Cerca",
        placeholder="🔍 Cognome, nome, ID o telefono...",
        key="paz_attivo_cerca",
        label_visibility="collapsed",
    )

    if cerca.strip():
        q = cerca.strip().upper()
        pazienti = [
            p for p in pazienti
            if q in (p.get("cognome", "") or "").upper()
            or q in (p.get("nome", "") or "").upper()
            or q in (p.get("telefono", "") or "")
            or q in str(p.get("id", ""))
        ]

    st.caption(f"{len(pazienti)} paziente/i")

    # Tabella ag-grid
    try:
        from st_aggrid import (
            AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode,
        )
        import pandas as pd
    except ImportError:
        # Fallback: selectbox
        st.warning("Tabella avanzata non disponibile, uso selettore semplice.")
        opts = [
            f"{p['id']} - {p.get('cognome', '')} {p.get('nome', '')} "
            f"· {_fmt_dn(p.get('data_nascita'))}"
            for p in pazienti
        ]
        sel = st.selectbox("Paziente", opts, key="paz_attivo_fb")
        if st.button("Conferma", type="primary", use_container_width=True):
            try:
                pid = int(sel.split(" - ", 1)[0])
                set_paziente_attivo(conn, pid)
                st.rerun()
            except Exception:
                st.error("Selezione non valida.")
        return

    rows_df = []
    for p in pazienti:
        rows_df.append({
            "_id": p.get("id"),
            "Stato": _badge_stato(p.get("stato_paziente")),
            "Cognome": p.get("cognome", "") or "",
            "Nome": p.get("nome", "") or "",
            "Data nasc.": _fmt_dn(p.get("data_nascita")),
            "Età": _eta_anni(p.get("data_nascita")) or "",
            "Telefono": p.get("telefono", "") or "",
        })
    df = pd.DataFrame(rows_df)

    gob = GridOptionsBuilder.from_dataframe(df)
    gob.configure_default_column(filter=True, sortable=True, resizable=True)
    gob.configure_column("_id", hide=True)
    gob.configure_column("Stato", width=70, pinned="left")
    gob.configure_column("Cognome", width=170, pinned="left", sort="asc")
    gob.configure_column("Nome", width=140)
    gob.configure_column("Data nasc.", width=110)
    gob.configure_column("Età", width=70, type=["numericColumn"])
    gob.configure_column("Telefono", width=130)
    gob.configure_selection(selection_mode="single", use_checkbox=False)
    gob.configure_grid_options(
        rowHeight=32, headerHeight=34,
        suppressCellFocus=True, domLayout="normal",
    )

    grid_response = AgGrid(
        df,
        gridOptions=gob.build(),
        height=400,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=False,
        theme="balham",
        fit_columns_on_grid_load=False,
        key=f"aggrid_paz_attivo_{cerca}",
    )

    selected = grid_response.get("selected_rows", [])
    if hasattr(selected, "to_dict"):
        try:
            selected = selected.to_dict("records")
        except Exception:
            selected = []

    if selected:
        try:
            pid = int(selected[0].get("_id"))
            set_paziente_attivo(conn, pid)
            st.rerun()
        except Exception:
            st.error("Selezione non valida.")


# ════════════════════════════════════════════════════════════════════
#  HEADER PAZIENTE ATTIVO
# ════════════════════════════════════════════════════════════════════

def header_paziente_attivo(conn) -> int | None:
    """Mostra l'header del paziente attivo (banner + bottone Cambia).

    Se non c'è un paziente attivo, mostra solo il bottone 'Seleziona paziente'
    e ritorna None. Altrimenti ritorna l'id del paziente attivo.

    Va chiamato all'inizio di ogni pagina che richiede un paziente.
    """
    pid = paziente_attivo_id()
    rec = paziente_attivo_record()

    # Se ho l'id ma non il record (cache pulita o sessione nuova) → ricarico
    if pid and not rec:
        rec = _carica_paziente_record(conn, pid)
        if rec:
            st.session_state[KEY_REC] = rec
        else:
            # Paziente non più esistente → reset
            reset_paziente_attivo()
            pid = None

    if not pid or not rec:
        # Nessun paziente attivo: bottone per selezionarne uno
        c1, c2 = st.columns([3, 1])
        with c1:
            st.warning("⚠️ Nessun paziente selezionato. Selezionane uno per continuare.")
        with c2:
            if st.button("👤 Seleziona paziente", type="primary",
                          key="hpa_select", use_container_width=True):
                _dialog_seleziona(conn)
        return None

    # Banner paziente attivo
    cog = rec.get("cognome", "") or ""
    nom = rec.get("nome", "") or ""
    dn = rec.get("data_nascita", "")
    eta = _eta_anni(dn)
    badge = _badge_stato(rec.get("stato_paziente", "ATTIVO"))

    info_parts = []
    if dn:
        info_parts.append(_fmt_dn(dn))
    if eta is not None:
        info_parts.append(f"{eta} anni")
    info_str = " · ".join(info_parts)

    c1, c2 = st.columns([4, 1])
    with c1:
        st.markdown(
            f"""<div style="
                padding: 10px 14px;
                background: var(--color-background-info);
                border-left: 3px solid var(--color-text-info);
                border-radius: var(--border-radius-md, 6px);
                margin-bottom: 8px;">
                <div style="font-size: 11px; color: var(--color-text-secondary); margin-bottom: 2px;">
                    PAZIENTE IN LAVORAZIONE
                </div>
                <div style="font-size: 15px; font-weight: 600;">
                    {badge} {cog} {nom}
                </div>
                <div style="font-size: 12px; color: var(--color-text-secondary); margin-top: 2px;">
                    ID {pid}{(" · " + info_str) if info_str else ""}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cambia paziente", key="hpa_change",
                      use_container_width=True):
            _dialog_seleziona(conn)

    return pid
