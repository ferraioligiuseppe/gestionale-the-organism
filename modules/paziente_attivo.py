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

# Flag di sessione per le colonne aggiunte al volo. Senza questo, ogni
# cambio paziente e ogni scadenza della cache lanciavano quattro ALTER
# TABLE: DDL sulle tabelle piu' lette dell'app, con produzione e staging
# sullo stesso Postgres. E' la ricetta per lock e timeout. Le colonne o
# ci sono gia' o si creano al primo giro della sessione.
KEY_SCHEMA_OK = "_paziente_attivo_schema_ok"


def _assicura_colonne(conn) -> None:
    """Crea le colonne accessorie se mancano. Una volta per sessione."""
    if st.session_state.get(KEY_SCHEMA_OK):
        return
    # Prima si guarda se le colonne ci sono già. «ALTER TABLE … IF NOT EXISTS»
    # chiede comunque il blocco esclusivo della tabella pazienti anche quando
    # non deve cambiare niente: se un'altra postazione ha una lettura aperta
    # su pazienti, l'ALTER resta in attesa e con lui la finestra «Seleziona
    # paziente», che si apriva vuota e non si caricava più. Ora l'ALTER parte
    # solo se una colonna manca davvero, e non aspetta più di 3 secondi.
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE (table_name='pazienti' AND column_name IN ('creato_il','ultimo_accesso')) "
            "OR (table_name='auth_users' AND column_name='ultimo_paziente_id')")
        ci = {(r[0], r[1]) if not isinstance(r, dict) else (r["table_name"], r["column_name"])
              for r in (cur.fetchall() or [])}
        mancanti = [sql for chiave, sql in (
            (("pazienti", "creato_il"), "ALTER TABLE pazienti ADD COLUMN IF NOT EXISTS creato_il TIMESTAMPTZ DEFAULT NOW();"),
            (("pazienti", "ultimo_accesso"), "ALTER TABLE pazienti ADD COLUMN IF NOT EXISTS ultimo_accesso TIMESTAMPTZ;"),
            (("auth_users", "ultimo_paziente_id"), "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS ultimo_paziente_id BIGINT;"),
        ) if chiave not in ci]
        if mancanti:
            cur.execute("SET LOCAL lock_timeout = '3s'")
            for sql in mancanti:
                cur.execute(sql)
        conn.commit()
        st.session_state[KEY_SCHEMA_OK] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


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
        try: conn.rollback()
        except Exception: pass
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _carica_lista_pazienti(_conn):
    """Lista pazienti ATTIVI per il dialog di selezione."""
    conn = _conn
    _assicura_colonne(conn)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cognome, nome, data_nascita, telefono, stato_paziente, creato_il "
            "FROM pazienti "
            "WHERE COALESCE(stato_paziente, 'ATTIVO') = 'ATTIVO' "
            "ORDER BY cognome, nome"
        )
        rows = cur.fetchall() or []
        cols = [d[0] for d in cur.description] if cur.description else []
        # Chiude la lettura: una transazione lasciata aperta tiene un blocco
        # sulla tabella pazienti e fa aspettare le altre postazioni.
        try:
            conn.commit()
        except Exception:
            pass
        # Forza dict Python puri (non DictRow / RealDictRow / sqlite Row)
        # altrimenti st.cache_data fallisce con UnserializableReturnValueError
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append({k: (v if not hasattr(v, 'isoformat') else v.isoformat())
                               for k, v in r.items()})
            else:
                result.append({c: (v if not hasattr(v, 'isoformat') else v.isoformat())
                               for c, v in zip(cols, r)})
        return result
    except Exception:
        try: conn.rollback()
        except Exception: pass
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
    """Imposta il paziente attivo. Carica e cachea il record completo.
    Aggiorna anche 'ultimo_accesso' (quando l'anagrafica è stata aperta
    l'ultima volta), creando la colonna al volo se non esiste ancora."""
    st.session_state[KEY_ID] = int(paz_id)
    rec = _carica_paziente_record(conn, paz_id)
    st.session_state[KEY_REC] = rec or {}
    _assicura_colonne(conn)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pazienti SET ultimo_accesso=NOW() WHERE id=%s", (int(paz_id),))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    _salva_ultimo_paziente_utente(conn, paz_id)
    try:
        from .registro_attivita import registra
        registra(conn, paz_id, "Scheda aperta", st.session_state.get("_voce_corrente") or "", ogni_minuti=30)
    except Exception:
        pass


def _salva_ultimo_paziente_utente(conn, paz_id: int) -> None:
    """Ricorda per l'utente loggato l'ultimo paziente aperto, così al prossimo
    accesso (anche dopo un riavvio dell'app) si ripresenta da solo."""
    try:
        u = st.session_state.get("user") or {}
        uid = u.get("id")
        if not uid:
            return
        _assicura_colonne(conn)
        cur = conn.cursor()
        cur.execute("UPDATE auth_users SET ultimo_paziente_id=%s WHERE id=%s",
                    (int(paz_id), int(uid)))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def ripristina_ultimo_paziente(conn) -> None:
    """Se non c'è ancora un paziente attivo in questa sessione, ricarica
    l'ultimo aperto dall'utente loggato (persistito su DB)."""
    if st.session_state.get(KEY_ID):
        return
    try:
        u = st.session_state.get("user") or {}
        uid = u.get("id")
        if not uid:
            return
        _assicura_colonne(conn)
        cur = conn.cursor()
        cur.execute("SELECT ultimo_paziente_id FROM auth_users WHERE id=%s", (int(uid),))
        row = cur.fetchone()
        conn.commit()
        pid = row[0] if row and not isinstance(row, dict) else (row.get("ultimo_paziente_id") if row else None)
        if pid:
            set_paziente_attivo(conn, int(pid))
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def reset_paziente_attivo() -> None:
    """Pulisce la selezione del paziente attivo."""
    st.session_state.pop(KEY_ID, None)
    st.session_state.pop(KEY_REC, None)


# ════════════════════════════════════════════════════════════════════
#  CREAZIONE RAPIDA PAZIENTE (inline nel dialog)
# ════════════════════════════════════════════════════════════════════

def _parse_dn(s):
    """Prova a interpretare una data digitata. Ritorna (date|None, errore|None)."""
    s = (s or "").strip()
    if not s:
        return None, None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s, fmt).date(), None
        except Exception:
            pass
    return None, "Data nascita non valida (usa GG/MM/AAAA)"


def _crea_paziente_rapido(conn, cognome, nome, dn_str, sesso, telefono):
    """Crea un paziente con i campi minimi. Ritorna (id|None, errore|None)."""
    data_iso = None
    if (dn_str or "").strip():
        d, err = _parse_dn(dn_str)
        if err:
            return None, err
        data_iso = d.isoformat() if d else None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pazienti (cognome, nome, data_nascita, sesso, telefono, stato_paziente) "
            "VALUES (%s,%s,%s,%s,%s,'ATTIVO') RETURNING id",
            (cognome.strip().upper(), nome.strip().upper(), data_iso,
             (sesso or None), (telefono.strip() or None)),
        )
        row = cur.fetchone()
        pid = int(row["id"] if isinstance(row, dict) else row[0])
        conn.commit()
        try:
            _carica_lista_pazienti.clear()
        except Exception:
            pass
        return pid, None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return None, f"Errore nella creazione: {e}"


def _form_nuovo_paziente(conn, key_suffix=None):
    """Form compatto per creare al volo un paziente e renderlo attivo.
    key_suffix rende univoche le chiavi quando il form compare in più punti
    nello stesso run (es. schermata coupon + dialog selezione)."""
    if key_suffix is None:
        key_suffix = "default"
    ks = key_suffix
    with st.form(f"form_nuovo_paziente_rapido_{ks}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        cognome = c1.text_input("Cognome *", key=f"np_cognome_{ks}")
        nome = c2.text_input("Nome *", key=f"np_nome_{ks}")
        c3, c4 = st.columns(2)
        dn = c3.text_input("Data nascita (GG/MM/AAAA)", key=f"np_dn_{ks}")
        sesso = c4.selectbox("Sesso", ["", "M", "F"], key=f"np_sesso_{ks}")
        tel = st.text_input("Telefono", key=f"np_tel_{ks}")
        ok = st.form_submit_button("➕ Crea e seleziona", type="primary",
                                   use_container_width=True)
    if ok:
        if not cognome.strip() or not nome.strip():
            st.error("Cognome e Nome sono obbligatori.")
            return
        pid, err = _crea_paziente_rapido(conn, cognome, nome, dn, sesso, tel)
        if err:
            st.error(err)
            return
        set_paziente_attivo(conn, pid)
        st.rerun()


# ════════════════════════════════════════════════════════════════════
#  DIALOG SELEZIONE
# ════════════════════════════════════════════════════════════════════

@st.dialog("👤 Seleziona paziente", width="large")
def _dialog_seleziona(conn):
    # La finestra "large" di Streamlit e' larga circa 750 px: troppo poco
    # per la tabella. La si porta quasi a tutto schermo.
    st.markdown(
        "<style>div[data-testid='stDialog'] div[role='dialog']"
        "{width:min(1200px,94vw)!important;max-width:94vw!important}</style>",
        unsafe_allow_html=True,
    )
    _corpo_seleziona(conn)


def _corpo_seleziona(conn, ns="default"):
    with st.spinner("Carico l'elenco dei pazienti…"):
        pazienti = _carica_lista_pazienti(conn)
    if not pazienti:
        st.warning("L'elenco dei pazienti non si è caricato. Se succede di nuovo, chiudi la finestra "
                   "e riprova tra qualche secondo: di solito è un'altra postazione che sta salvando.")
        _carica_lista_pazienti.clear()
        st.info("Nessun paziente registrato. Puoi aggiungerne uno qui sotto.")
        st.markdown("##### ➕ Nuovo paziente")
        _form_nuovo_paziente(conn, key_suffix="empty")
        if st.button("Chiudi"):
            st.rerun()
        return

    # Filtro testuale rapido — chiave FISSA (non legata a ns/contatore di render):
    # se la chiave cambia da un rerun all'altro (es. ns che varia perché questo
    # popover viene aperto da punti diversi della pagina), Streamlit tratta il
    # campo come un widget nuovo e perde il testo appena digitato, mostrando
    # sempre la lista intera invece del risultato filtrato.
    cerca = st.text_input(
        "Cerca",
        placeholder="🔍 Cognome, nome, ID o telefono...",
        key=f"paz_attivo_cerca_box_{ns}",
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

    # Filtro per età della scheda aperta: in Screening 0-4 anni si vedono solo
    # i bambini di quell'età, in WHODAS solo gli adulti, e così via. Le fasce
    # sono le stesse del menu (filtro_eta.REGOLE_ETA). Si può togliere.
    voce = st.session_state.get("_voce_corrente") or ""
    try:
        from .filtro_eta import REGOLE_ETA
        e_min, e_max = REGOLE_ETA.get(voce, (None, None))
    except Exception:
        e_min, e_max = None, None
    if e_min is not None or e_max is not None:
        fascia_txt = (f"da {e_min} a {e_max} anni" if e_min is not None and e_max is not None
                      else f"da {e_min} anni in su" if e_min is not None else f"fino a {e_max} anni")
        if st.toggle(f"🎯 Solo pazienti {fascia_txt} — {voce}", value=True,
                     key=f"paz_attivo_eta_tgl_{ns}"):
            prima = len(pazienti)
            senza_dn = 0
            tenuti = []
            for p in pazienti:
                a = _eta_anni(p.get("data_nascita"))
                if a is None:
                    senza_dn += 1
                    continue
                if (e_min is None or a >= e_min) and (e_max is None or a <= e_max):
                    tenuti.append(p)
            pazienti = tenuti
            nascosti = prima - len(pazienti)
            if nascosti:
                st.caption(f"{nascosti} pazienti nascosti perché fuori fascia"
                           + (f" ({senza_dn} senza data di nascita)" if senza_dn else "")
                           + ": togli il filtro per vederli.")

    st.caption(f"{len(pazienti)} paziente/i")

    ordina_recenti = False
    if not cerca.strip():
        ordina_recenti = st.checkbox("🕓 Ordina per ultimi registrati", key=f"paz_attivo_recenti_box_{ns}")
        if ordina_recenti:
            pazienti = sorted(pazienti, key=lambda p: str(p.get("creato_il") or ""), reverse=True)

    # Tabella nativa di Streamlit con selezione di riga. Prima era AgGrid:
    # dentro la finestra il clic sulla riga a volte non arrivava al programma
    # (componente esterno in un iframe, rieseguito a pezzi) e il paziente non
    # veniva selezionato. st.dataframe con on_select è parte di Streamlit e
    # funziona anche dentro le finestre di dialogo.
    import pandas as pd
    righe_tab = []
    for p in pazienti:
        righe_tab.append({
            "_id": p.get("id"),
            "": _badge_stato(p.get("stato_paziente")),
            "Paziente": f"{(p.get('cognome') or '').strip()} {(p.get('nome') or '').strip()}".strip(),
            "Nato il": _fmt_dn(p.get("data_nascita")),
            "Età": _eta_anni(p.get("data_nascita")),
            "Telefono": p.get("telefono", "") or "",
            "Registrato il": _fmt_dn(p.get("creato_il")) if p.get("creato_il") else "",
        })
    df = pd.DataFrame(righe_tab)
    if df.empty:
        st.info("Nessun paziente corrisponde alla ricerca.")
    else:
        if "Età" in df.columns:
            df["Età"] = pd.to_numeric(df["Età"], errors="coerce").astype("Int64")
        st.caption("Clicca la casella a sinistra del paziente per selezionarlo.")
        ev = st.dataframe(
            df.drop(columns=["_id"]),
            hide_index=True, use_container_width=True, height=480,
            on_select="rerun", selection_mode="single-row",
            column_config={
                "": st.column_config.TextColumn("", width="small"),
                "Paziente": st.column_config.TextColumn("Paziente", width="large"),
                "Età": st.column_config.NumberColumn("Età", format="%d", width="small"),
            },
            key=f"paz_df_{ns}_{st.session_state.get('_pa_grid_nonce', 0)}_{cerca}",
        )
        sel_rows = []
        try:
            sel_rows = list(ev.selection.rows)
        except Exception:
            try:
                sel_rows = list((ev or {}).get("selection", {}).get("rows", []))
            except Exception:
                sel_rows = []
        if sel_rows:
            try:
                pid = int(df.iloc[sel_rows[0]]["_id"])
                set_paziente_attivo(conn, pid)
                st.session_state["_pa_grid_nonce"] = st.session_state.get("_pa_grid_nonce", 0) + 1
                st.rerun()
            except Exception as e:
                st.error(f"Selezione non riuscita: {e}")

    # Nuovo paziente: sotto l'elenco e chiuso. Si apre solo se serve; dopo
    # «Crea e seleziona» il paziente diventa attivo e la finestra si chiude.
    st.markdown("")
    if st.toggle("➕ Il paziente non è in elenco: crea una nuova anagrafica",
                 key=f"paz_attivo_nuovo_tgl_{ns}"):
        st.caption("Compila Cognome e Nome (gli altri campi sono facoltativi): "
                   "il paziente viene creato e selezionato subito.")
        _form_nuovo_paziente(conn, key_suffix=f"inline_{ns}")


# ════════════════════════════════════════════════════════════════════
#  HEADER PAZIENTE ATTIVO
# ════════════════════════════════════════════════════════════════════

def get_paziente_attivo(conn, show_warning: bool = True) -> int | None:
    """Solo lettura: ritorna l'id del paziente attivo o None.

    Da usare nei moduli che vengono raggiunti DOPO che il router ha già
    mostrato l'header. Non mostra alcuna UI tranne (opzionalmente) un
    warning se nessun paziente è selezionato.
    """
    pid = paziente_attivo_id()
    if pid:
        # Verifico che il record sia caricato (cache miss recuperata)
        if not paziente_attivo_record():
            rec = _carica_paziente_record(conn, pid)
            if rec:
                st.session_state[KEY_REC] = rec
            else:
                reset_paziente_attivo()
                pid = None
    if not pid and show_warning:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.warning(
                "⚠️ Nessun paziente selezionato. "
                "Selezionane uno per continuare."
            )
        with c2:
            # Finestra grande invece del popover: il popover stava in una
            # colonna stretta e la tabella dei pazienti era illeggibile.
            if st.button("👤 Seleziona paziente", key="gpa_apri_sel",
                         type="primary", use_container_width=True):
                _dialog_seleziona(conn)
    return pid


def _mostra_moduli_pnev_attivi(conn, pid):
    """Riga compatta, sempre visibile sotto il banner paziente in ogni scheda:
    quali moduli della Terapia PNEV (stimolazione multisensoriale) sta
    seguendo — evita di doverlo andare a cercare dentro Terapia."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT terapia, COUNT(*), MAX(data_seduta)
            FROM terapia_sedute WHERE paziente_id=%s
            GROUP BY terapia ORDER BY MAX(data_seduta) DESC
        """, (pid,))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try: conn.rollback()
        except Exception: pass
    if not righe:
        return
    chips = " &nbsp; ".join(
        f"<span style='background:var(--color-background-info);border-radius:999px;padding:3px 10px;font-size:12px;white-space:nowrap;'>"
        f"🧘 {t} · {n} sedut{'a' if n==1 else 'e'}</span>"
        for t, n, _ in righe
    )
    st.markdown(
        f"<div style='margin:2px 0 10px;line-height:2.1'>{chips}</div>",
        unsafe_allow_html=True,
    )


def _indice_header() -> int:
    """Numero stabile per le chiavi dei bottoni dell'header.

    Prima era un contatore che cresceva a OGNI caricamento della pagina: il
    bottone «Seleziona paziente» cambiava chiave fra il clic e il caricamento
    successivo, e Streamlit perdeva il clic. Per questo a volte la finestra
    dei pazienti non si apriva. Ora il numero riparte da 1 a ogni caricamento
    e sale solo se l'header compare più volte nella stessa pagina: stessa
    chiave a ogni giro, nessun duplicato."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        usate = get_script_run_ctx().widget_user_keys_this_run
        n = 1
        while f"nopid_apri_sel_{n}" in usate or f"hdr_apri_sel_{n}" in usate:
            n += 1
        return n
    except Exception:
        st.session_state["_hpa_render_n"] = st.session_state.get("_hpa_render_n", 0) + 1
        return st.session_state["_hpa_render_n"]


def header_paziente_attivo(conn) -> int | None:
    """Mostra l'header del paziente attivo (banner + bottone Cambia).

    Se non c'è un paziente attivo, mostra solo il bottone 'Seleziona paziente'
    e ritorna None. Altrimenti ritorna l'id del paziente attivo.

    Va chiamato all'inizio di ogni pagina che richiede un paziente.
    """
    pid = paziente_attivo_id()
    rec = paziente_attivo_record()
    # Questo header può essere richiamato più volte nello stesso caricamento
    # da punti diversi del codice (router + modulo specifico): rendo ogni
    # chiave dei suoi widget sempre unica per evitare "duplicate element key".
    _hpa_n = _indice_header()
    # Niente ripristino automatico dell'ultimo paziente: si lavorava per
    # sbaglio sulla scheda di chi era stato aperto l'ultima volta. Il
    # paziente si sceglie sempre dall'elenco.

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
            if st.button("👤 Seleziona paziente", key=f"nopid_apri_sel_{_hpa_n}",
                         type="primary", use_container_width=True):
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

    # Questo header viene richiamato più volte nello stesso caricamento da
    # punti diversi del codice (router + modulo specifico): rendo la chiave
    # del bottone sempre unica per evitare "duplicate element key".
    _hpa_key = f"hpa_change_{_hpa_n}"

    # Date sempre visibili: quando e' stato registrato e quando la scheda e'
    # stata aperta l'ultima volta prima di adesso (da chi).
    _date_scheda = ""
    try:
        from .registro_attivita import data_registrazione, _q as _rq, _fmt as _rfmt
        _reg, _ok = data_registrazione(conn, rec)
        _ap = _rq(conn, "SELECT quando, utente FROM registro_attivita WHERE paziente_id=%s "
                        "AND azione='Scheda aperta' ORDER BY quando DESC LIMIT 2", (int(pid),))
        _parti = [f"registrato il {_reg}" if _ok else "data di registrazione non disponibile"]
        if len(_ap) > 1:
            _parti.append(f"aperto in precedenza il {_rfmt(_ap[1]['quando'], ora=True)}"
                          + (f" da {_ap[1]['utente']}" if _ap[1].get("utente") else ""))
        _date_scheda = " · ".join(_parti)
    except Exception:
        _date_scheda = ""

    c1, c2 = st.columns([3, 2])
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
                    ID {pid}{(" · " + info_str) if info_str else ""}{(" · " + _date_scheda) if _date_scheda else ""}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cambia paziente", key=f"hdr_apri_sel_{_hpa_n}",
                     use_container_width=True):
            _dialog_seleziona(conn)

    _mostra_moduli_pnev_attivi(conn, pid)

    with st.expander("✏️ Modifica rapida anagrafica (senza uscire da qui)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            n_cog = st.text_input("Cognome", value=cog, key=f"hpa_edit_cog_{pid}_{_hpa_n}")
            n_nom = st.text_input("Nome", value=nom, key=f"hpa_edit_nom_{pid}_{_hpa_n}")
        with c2:
            n_dn = st.text_input("Data nascita (GG/MM/AAAA)",
                                 value=_fmt_dn(dn) if dn else "",
                                 key=f"hpa_edit_dn_{pid}_{_hpa_n}")
            n_tel = st.text_input("Telefono", value=rec.get("telefono", "") or "",
                                  key=f"hpa_edit_tel_{pid}_{_hpa_n}")
        with c3:
            n_ind = st.text_input("Indirizzo", value=rec.get("indirizzo", "") or "",
                                  key=f"hpa_edit_ind_{pid}_{_hpa_n}")
            n_email = st.text_input("Email", value=rec.get("email", "") or "",
                                    key=f"hpa_edit_email_{pid}_{_hpa_n}")
        if st.button("💾 Salva modifiche", key=f"hpa_edit_save_{pid}_{_hpa_n}", type="primary"):
            errore = _salva_modifica_rapida(conn, pid, n_cog, n_nom, n_dn, n_tel,
                                            n_ind, n_email)
            if errore:
                st.error(errore)
            else:
                st.session_state[KEY_REC] = _carica_paziente_record(conn, pid)
                st.success("Anagrafica aggiornata.")
                st.rerun()

    return pid


def _salva_modifica_rapida(conn, pid, cognome, nome, dn_str, telefono, indirizzo, email):
    """Aggiorna i campi base dell'anagrafica dal riquadro rapido dell'header.
    Ritorna un messaggio d'errore, o None se tutto ok."""
    cognome = (cognome or "").strip()
    nome = (nome or "").strip()
    if not cognome or not nome:
        return "Cognome e Nome sono obbligatori."
    data_iso = None
    if (dn_str or "").strip():
        d, err = _parse_dn(dn_str)
        if err:
            return err
        data_iso = d.isoformat() if d else None
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE pazienti SET cognome=%s, nome=%s, data_nascita=%s, "
            "telefono=%s, indirizzo=%s, email=%s WHERE id=%s",
            (cognome, nome, data_iso, telefono.strip(), indirizzo.strip(),
             email.strip(), int(pid)))
        conn.commit()
        return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return f"Salvataggio non riuscito: {e}"
