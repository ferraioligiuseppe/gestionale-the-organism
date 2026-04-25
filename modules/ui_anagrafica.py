# -*- coding: utf-8 -*-
"""Anagrafica Pazienti v2.0 - The Organism.

Layout a due colonne fisse: lista cliccabile a sinistra, form a destra.
Click diretto sulla riga del paziente per aprire la scheda.
Tasto Elimina con conferma a doppio step.
Generatore + validatore Codice Fiscale integrati.
Sezione Privacy/GDPR completa (consensi, canali, tutore minore, marketing).
"""
from __future__ import annotations
import datetime
import streamlit as st


# ════════════════════════════════════════════════════════════════════
#  HELPERS GENERICI
# ════════════════════════════════════════════════════════════════════

def _parse_data(s: str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _fmt_dn(iso) -> str:
    if not iso:
        return ""
    try:
        return datetime.date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _eta(dn) -> str:
    try:
        anni = (datetime.date.today() - datetime.date.fromisoformat(str(dn)[:10])).days // 365
        return f"{anni}a"
    except Exception:
        return ""


def _cap_lookup(cap: str) -> dict:
    if len(cap) != 5 or not cap.isdigit():
        return {}
    try:
        import requests
        r = requests.get(f"https://api.zippopotam.us/it/{cap}", timeout=3)
        if r.status_code == 200:
            places = r.json().get("places", [])
            if places:
                return {
                    "citta": places[0].get("place name", "").title(),
                    "provincia": places[0].get("state abbreviation", "").upper(),
                }
    except Exception:
        pass
    return {}


def _safe_get(rec, key, default=""):
    """Legge un campo da dict-row o tuple-row in modo robusto."""
    if rec is None:
        return default
    if isinstance(rec, dict):
        # Tenta varianti maiuscole/minuscole
        for k in (key, key.lower(), key.upper(), key.title()):
            if k in rec:
                return rec[k] if rec[k] is not None else default
    return default


# ════════════════════════════════════════════════════════════════════
#  CF: import lazy delle funzioni da app_core
# ════════════════════════════════════════════════════════════════════

def _cf_helpers():
    """Importa lazy le funzioni CF da app_core. Ritorna (genera, valida) o (None, None)."""
    try:
        from modules.app_core import genera_codice_fiscale, valida_codice_fiscale
        return genera_codice_fiscale, valida_codice_fiscale
    except Exception:
        return None, None


# ════════════════════════════════════════════════════════════════════
#  QUERY DB
# ════════════════════════════════════════════════════════════════════

def _carica_pazienti(conn, cerca: str = "", filtro_stato: str = "Attivi"):
    """Lista pazienti con filtro ricerca + filtro stato."""
    try:
        cur = conn.cursor()
        params: list = []
        where = []

        # Filtro stato
        if filtro_stato == "Attivi":
            where.append("(stato_paziente IS NULL OR stato_paziente = 'ATTIVO')")
        elif filtro_stato == "Sospesi":
            where.append("stato_paziente = 'SOSPESO'")
        elif filtro_stato == "Archiviati":
            where.append("stato_paziente = 'ARCHIVIATO'")
        # "Tutti" → nessun filtro

        # Filtro ricerca
        if cerca.strip():
            q = f"%{cerca.strip().upper()}%"
            where.append(
                "(UPPER(cognome) LIKE %s OR UPPER(nome) LIKE %s "
                "OR UPPER(COALESCE(codice_fiscale,'')) LIKE %s "
                "OR CAST(id AS TEXT) = %s)"
            )
            params.extend([q, q, q, cerca.strip()])

        sql = (
            "SELECT id, cognome, nome, data_nascita, telefono, "
            "stato_paziente, codice_fiscale "
            "FROM pazienti"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY cognome, nome LIMIT 500"

        cur.execute(sql, params)
        rows = cur.fetchall() or []
        result = []
        cols = [d[0] for d in cur.description] if cur.description else []
        for r in rows:
            result.append(r if isinstance(r, dict) else dict(zip(cols, r)))
        return result
    except Exception as e:
        st.error(f"Errore lista: {e}")
        return []


def _carica_paziente(conn, paz_id):
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


def _carica_ultimo_consenso(conn, paz_id):
    """Carica l'ultimo record di consenso privacy del paziente. None se non esiste."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM consensi_privacy WHERE paziente_id=%s "
            "ORDER BY data_ora DESC NULLS LAST, id DESC LIMIT 1",
            (paz_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    except Exception:
        return None


def _conta_pazienti(conn) -> int:
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pazienti")
        row = cur.fetchone()
        if isinstance(row, dict):
            return int(list(row.values())[0])
        return int(row[0])
    except Exception:
        return 0


def _salva_nuovo(conn, d: dict):
    """Inserisce nuovo paziente + record consenso iniziale. Ritorna paz_id o None."""
    try:
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data nascita non valida. Usa GG/MM/AAAA")
                return None
            data_iso = parsed.isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pazienti
            (cognome, nome, data_nascita, sesso, telefono, email,
             indirizzo, cap, citta, provincia, codice_fiscale, stato_paziente)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ATTIVO')
            RETURNING id
        """, (
            d["cognome"].strip().upper(), d["nome"].strip().title(),
            data_iso, d["sesso"],
            d["tel"].strip(), d["email"].strip().lower(),
            d["indirizzo"].strip(), d["cap"].strip(),
            d["citta"].strip().title(), d["prov"].strip().upper(),
            d["cf"].strip().upper() or None,
        ))
        row = cur.fetchone()
        paz_id = int(row["id"] if isinstance(row, dict) else row[0])

        # Record consenso iniziale
        try:
            cur.execute("""
                INSERT INTO consensi_privacy
                (paziente_id, tipo, consenso_trattamento,
                 consenso_comunicazioni, canale_email, canale_whatsapp,
                 data_ora)
                VALUES (%s,%s,1,1,1,1,NOW())
            """, (paz_id, d.get("tipo_privacy", "adulto")))
        except Exception:
            pass

        conn.commit()
        return paz_id
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore salvataggio: {e}")
        return None


def _salva_modifica(conn, paz_id, d: dict) -> bool:
    """Aggiorna i dati anagrafici di un paziente esistente."""
    try:
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data nascita non valida. Usa GG/MM/AAAA")
                return False
            data_iso = parsed.isoformat()

        cur = conn.cursor()
        cur.execute("""
            UPDATE pazienti SET
                cognome=%s, nome=%s, data_nascita=%s, sesso=%s,
                telefono=%s, email=%s, indirizzo=%s, cap=%s,
                citta=%s, provincia=%s, codice_fiscale=%s,
                stato_paziente=%s
            WHERE id=%s
        """, (
            d["cognome"].strip().upper(), d["nome"].strip().title(),
            data_iso, d["sesso"],
            d["tel"].strip(), d["email"].strip().lower(),
            d["indirizzo"].strip(), d["cap"].strip(),
            d["citta"].strip().title(), d["prov"].strip().upper(),
            d["cf"].strip().upper() or None,
            d["stato"], paz_id,
        ))
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore: {e}")
        return False


def _salva_consenso(conn, paz_id, c: dict) -> bool:
    """Inserisce un nuovo record di consenso (storico immutabile)."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO consensi_privacy
            (paziente_id, data_ora, tipo,
             tutore_nome, tutore_cf, tutore_telefono, tutore_email,
             consenso_trattamento, consenso_comunicazioni, consenso_marketing,
             canale_email, canale_sms, canale_whatsapp,
             usa_klaviyo, note)
            VALUES (%s,NOW(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            paz_id, c.get("tipo", "adulto"),
            c.get("tutore_nome", "") or None,
            c.get("tutore_cf", "") or None,
            c.get("tutore_tel", "") or None,
            c.get("tutore_email", "") or None,
            1 if c.get("consenso_tratt") else 0,
            1 if c.get("consenso_com") else 0,
            1 if c.get("consenso_mkt") else 0,
            1 if c.get("can_email") else 0,
            1 if c.get("can_sms") else 0,
            1 if c.get("can_wa") else 0,
            1 if c.get("usa_klaviyo") else 0,
            c.get("note", "") or None,
        ))
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore consenso: {e}")
        return False


def _archivia(conn, paz_id) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pazienti SET stato_paziente='ARCHIVIATO' WHERE id=%s", (paz_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore archiviazione: {e}")
        return False


def _riattiva(conn, paz_id) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pazienti SET stato_paziente='ATTIVO' WHERE id=%s", (paz_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore riattivazione: {e}")
        return False


def _elimina_definitivo(conn, paz_id) -> bool:
    """Cancella paziente + tutti i dati associati. Operazione irreversibile."""
    cur = conn.cursor()
    # Tabelle correlate: tento ogni cancellazione separatamente.
    # Se una tabella non esiste o non ha record, ignoro l'errore e continuo.
    tabelle_correlate = [
        "consensi_privacy", "anamnesi", "valutazioni_visive",
        "sedute", "coupons", "relazioni_cliniche",
        "valutazioni_neuropsicologiche", "stimolazioni_uditive",
        "calibrazioni_cuffie", "test_audiologici", "pnev_risposte",
        "tokens_pnev",
    ]
    for tab in tabelle_correlate:
        try:
            cur.execute(f"DELETE FROM {tab} WHERE paziente_id=%s", (paz_id,))
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    # Eliminazione finale paziente
    try:
        cur.execute("DELETE FROM pazienti WHERE id=%s", (paz_id,))
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore eliminazione: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
#  FORM CAMPI ANAGRAFICI
# ════════════════════════════════════════════════════════════════════

def _form_anagrafici(key: str, r: dict | None = None) -> dict:
    """Renderizza i campi anagrafici. r=None per nuovo, r=dict per modifica."""
    is_nuovo = r is None
    r = r or {}

    # Riga 1: cognome, nome
    c1, c2 = st.columns(2)
    with c1:
        cognome = st.text_input(
            "Cognome *",
            value=r.get("cognome", "") or "",
            key=f"{key}_cog",
        )
    with c2:
        nome = st.text_input(
            "Nome *",
            value=r.get("nome", "") or "",
            key=f"{key}_nom",
        )

    # Riga 2: data nascita, sesso, CF
    c3, c4, c5 = st.columns([2, 1, 2])
    with c3:
        data_str = st.text_input(
            "Data nascita",
            value=_fmt_dn(r.get("data_nascita", "")),
            key=f"{key}_dn",
            placeholder="GG/MM/AAAA",
        )
    with c4:
        sesso_opts = ["M", "F", "Altro"]
        sesso_val = r.get("sesso", "M") or "M"
        sesso = st.selectbox(
            "Sesso",
            sesso_opts,
            index=sesso_opts.index(sesso_val) if sesso_val in sesso_opts else 0,
            key=f"{key}_sex",
        )
    with c5:
        # Se è stato generato un CF dal tool, lo prendo dal session_state
        cf_default = st.session_state.pop(f"{key}_cf_generato", None)
        if cf_default is None:
            cf_default = r.get("codice_fiscale", "") or ""
        cf = st.text_input(
            "Codice fiscale",
            value=cf_default,
            key=f"{key}_cf",
            placeholder="Lascia vuoto se non disponibile",
        ).upper()

    # Validazione CF live
    if cf.strip():
        _, valida = _cf_helpers()
        if valida is not None:
            if valida(cf.strip()):
                st.markdown(
                    "<div style='color:var(--color-text-success);font-size:11px;margin-top:-8px'>"
                    "✓ Codice fiscale valido</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='color:var(--color-text-warning);font-size:11px;margin-top:-8px'>"
                    "⚠️ Codice fiscale non riconosciuto dall'algoritmo (puoi salvarlo comunque)</div>",
                    unsafe_allow_html=True,
                )

    # Tool generatore CF
    _genera_cf_expander(key, cognome, nome, data_str, sesso)

    # Riga 3: telefono, email
    c6, c7 = st.columns(2)
    with c6:
        tel = st.text_input(
            "Telefono",
            value=r.get("telefono", "") or "",
            key=f"{key}_tel",
        )
    with c7:
        email = st.text_input(
            "Email",
            value=r.get("email", "") or "",
            key=f"{key}_email",
        )

    # Riga 4: indirizzo
    indirizzo = st.text_input(
        "Indirizzo (via, civico)",
        value=r.get("indirizzo", "") or "",
        key=f"{key}_ind",
    )

    # Riga 5: CAP, città, provincia con lookup automatico
    c8, c9, c10 = st.columns([1, 2, 1])
    with c8:
        cap = st.text_input(
            "CAP",
            value=r.get("cap", "") or "",
            key=f"{key}_cap",
            max_chars=5,
        )
    with c9:
        citta_default = st.session_state.pop(f"{key}_citta_v", None)
        if citta_default is None:
            citta_default = r.get("citta", "") or ""
        citta = st.text_input(
            "Città",
            value=citta_default,
            key=f"{key}_citta",
        )
    with c10:
        prov_default = st.session_state.pop(f"{key}_prov_v", None)
        if prov_default is None:
            prov_default = r.get("provincia", "") or ""
        prov = st.text_input(
            "Prov.",
            value=prov_default,
            key=f"{key}_prov",
            max_chars=2,
        )

    # Lookup CAP automatico (solo se CAP cambia)
    last_cap_key = f"{key}_last_cap"
    if cap and cap != st.session_state.get(last_cap_key, ""):
        info = _cap_lookup(cap)
        if info:
            st.session_state[f"{key}_citta_v"] = info["citta"]
            st.session_state[f"{key}_prov_v"] = info["provincia"]
            st.session_state[last_cap_key] = cap
            st.rerun()
        st.session_state[last_cap_key] = cap

    # Stato paziente (solo in modifica)
    if not is_nuovo:
        stati = ["ATTIVO", "SOSPESO", "ARCHIVIATO"]
        stato_val = r.get("stato_paziente", "ATTIVO") or "ATTIVO"
        stato = st.selectbox(
            "Stato",
            stati,
            index=stati.index(stato_val) if stato_val in stati else 0,
            key=f"{key}_stato",
        )
    else:
        stato = "ATTIVO"

    return {
        "cognome": cognome, "nome": nome, "data_str": data_str,
        "sesso": sesso, "cf": cf, "tel": tel, "email": email,
        "indirizzo": indirizzo, "cap": cap, "citta": citta, "prov": prov,
        "stato": stato,
        "_is_nuovo": is_nuovo,
    }


def _genera_cf_expander(key: str, cognome: str, nome: str,
                         data_str: str, sesso: str) -> None:
    """Expander con il generatore di codice fiscale di supporto."""
    genera, _ = _cf_helpers()
    if genera is None:
        return

    with st.expander("🛠️ Genera codice fiscale (se il paziente non lo ricorda)"):
        st.caption(
            "Usa cognome, nome, data e sesso dal form sopra. "
            "Aggiungi qui comune e provincia di nascita."
        )
        c1, c2 = st.columns([2, 1])
        with c1:
            comune = st.text_input(
                "Comune di nascita",
                key=f"{key}_cf_comune",
                placeholder="Es. Pagani",
            )
        with c2:
            prov_n = st.text_input(
                "Sigla prov.",
                key=f"{key}_cf_prov",
                placeholder="Es. SA",
                max_chars=2,
            )

        if st.button("Genera CF", key=f"{key}_cf_btn", use_container_width=True):
            cf_gen = genera(
                cognome=cognome, nome=nome,
                data_nascita_str=data_str, sesso=sesso,
                comune_nascita=comune, provincia_nascita=prov_n,
            )
            if cf_gen is None:
                st.error(
                    "Impossibile generare il CF. Controlla i dati anagrafici "
                    "e che il comune sia presente in archivio."
                )
            else:
                # Salvo il CF generato in session_state perché il form
                # lo riprenda al prossimo render
                st.session_state[f"{key}_cf_generato"] = cf_gen
                st.success(f"CF generato: **{cf_gen}** — inserito automaticamente nel campo.")
                st.rerun()


# ════════════════════════════════════════════════════════════════════
#  FORM PRIVACY E CONSENSI
# ════════════════════════════════════════════════════════════════════

def _form_privacy(key: str, c: dict | None = None) -> dict:
    """Sezione consensi privacy/GDPR. c=None per nuovo, c=dict ultimo consenso per modifica."""
    c = c or {}

    # Tipo soggetto
    tipo_val = (c.get("tipo") or "adulto").lower()
    tipo = st.radio(
        "Tipo soggetto",
        ["Adulto", "Minore"],
        index=0 if tipo_val == "adulto" else 1,
        horizontal=True,
        key=f"{key}_priv_tipo",
    )

    # Dati tutore (solo se Minore)
    tutore_nome = tutore_cf = tutore_tel = tutore_email = ""
    if tipo == "Minore":
        st.markdown("**Dati genitore / tutore**")
        ct1, ct2 = st.columns(2)
        with ct1:
            tutore_nome = st.text_input(
                "Nome e cognome tutore",
                value=c.get("tutore_nome", "") or "",
                key=f"{key}_tut_n",
            )
            tutore_tel = st.text_input(
                "Telefono tutore",
                value=c.get("tutore_telefono", "") or "",
                key=f"{key}_tut_t",
            )
        with ct2:
            tutore_cf = st.text_input(
                "CF tutore",
                value=c.get("tutore_cf", "") or "",
                key=f"{key}_tut_cf",
            ).upper()
            tutore_email = st.text_input(
                "Email tutore",
                value=c.get("tutore_email", "") or "",
                key=f"{key}_tut_e",
            )

    st.markdown("**Consensi**")
    consenso_tratt = st.checkbox(
        "Consenso al trattamento dati per finalità cliniche/gestionali (obbligatorio)",
        value=bool(c.get("consenso_trattamento", 1)) if c else False,
        key=f"{key}_c_tratt",
    )
    consenso_com = st.checkbox(
        "Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)",
        value=bool(c.get("consenso_comunicazioni", 1)) if c else True,
        key=f"{key}_c_com",
    )

    st.markdown("**Canali autorizzati**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        can_email = st.checkbox(
            "Email",
            value=bool(c.get("canale_email", 1)) if c else True,
            key=f"{key}_can_e",
        )
    with cc2:
        can_sms = st.checkbox(
            "SMS",
            value=bool(c.get("canale_sms", 0)) if c else False,
            key=f"{key}_can_s",
        )
    with cc3:
        can_wa = st.checkbox(
            "WhatsApp",
            value=bool(c.get("canale_whatsapp", 1)) if c else True,
            key=f"{key}_can_w",
        )

    st.markdown("**Marketing (facoltativo)**")
    consenso_mkt = st.checkbox(
        "Consenso a comunicazioni promozionali e contenuti informativi",
        value=bool(c.get("consenso_marketing", 0)) if c else False,
        key=f"{key}_c_mkt",
    )
    usa_klaviyo = st.checkbox(
        "Autorizzo l'uso di Klaviyo per newsletter/SMS marketing",
        value=bool(c.get("usa_klaviyo", 0)) if c else False,
        key=f"{key}_klav",
    )

    note = st.text_area(
        "Note privacy (facoltative)",
        value=c.get("note", "") or "",
        key=f"{key}_note",
        height=68,
    )

    return {
        "tipo": tipo.lower(),
        "tutore_nome": tutore_nome, "tutore_cf": tutore_cf,
        "tutore_tel": tutore_tel, "tutore_email": tutore_email,
        "consenso_tratt": consenso_tratt,
        "consenso_com": consenso_com,
        "consenso_mkt": consenso_mkt,
        "can_email": can_email, "can_sms": can_sms, "can_wa": can_wa,
        "usa_klaviyo": usa_klaviyo,
        "note": note,
    }


# ════════════════════════════════════════════════════════════════════
#  CARDS LISTA
# ════════════════════════════════════════════════════════════════════

def _label_card(p: dict) -> str:
    """Etichetta del bottone-card paziente nella lista a sinistra."""
    cog = p.get("cognome", "") or ""
    nom = p.get("nome", "") or ""
    dn = p.get("data_nascita", "")
    tel = p.get("telefono", "") or ""
    stato = p.get("stato_paziente", "ATTIVO") or "ATTIVO"

    badge = "🟢" if stato == "ATTIVO" else ("🟡" if stato == "SOSPESO" else "⚫")
    eta = _eta(dn)
    riga2_parts = []
    if dn:
        riga2_parts.append(_fmt_dn(dn))
    if eta:
        riga2_parts.append(eta)
    if tel:
        riga2_parts.append(tel)
    riga2 = " · ".join(riga2_parts)

    # I bottoni Streamlit supportano \n\n nel label per andare a capo
    label = f"{badge} {cog} {nom}"
    if riga2:
        label += f"\n\n{riga2}"
    return label


# ════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════

def render_anagrafica(conn) -> None:
    """Render principale dell'anagrafica pazienti v2.0."""

    # ── Stato navigazione ─────────────────────────────────────────
    st.session_state.setdefault("ana_sel", None)        # paz_id selezionato
    st.session_state.setdefault("ana_nuovo", False)     # modalità nuovo paziente
    st.session_state.setdefault("ana_filtro", "Attivi") # filtro stato lista
    st.session_state.setdefault("ana_conf_del", None)   # paz_id da confermare elimina

    # ── CSS leggero per compattare i bottoni-card della lista ─────
    st.markdown("""
        <style>
        /* Bottoni nella prima colonna: aspetto card compatto */
        div[data-testid="column"]:first-child div.stButton > button {
            text-align: left;
            justify-content: flex-start;
            padding: 8px 12px;
            min-height: 0;
            line-height: 1.3;
            font-weight: 500;
            white-space: pre-wrap;
        }
        div[data-testid="column"]:first-child div.stButton > button p {
            text-align: left;
            margin: 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.subheader("Anagrafica Pazienti")
    with h2:
        if st.button("➕ Nuovo paziente", type="primary",
                     key="ana_btn_nuovo", use_container_width=True):
            st.session_state["ana_nuovo"] = True
            st.session_state["ana_sel"] = None
            st.session_state["ana_conf_del"] = None
            st.rerun()

    # ── Layout principale 2 colonne ───────────────────────────────
    col_l, col_r = st.columns([1, 2], gap="medium")

    # ════════════════════════════════════════════════════════════
    #  COLONNA SINISTRA: ricerca + filtro + lista
    # ════════════════════════════════════════════════════════════
    with col_l:
        cerca = st.text_input(
            "Cerca",
            placeholder="🔍 Cognome, nome, ID o CF...",
            key="ana_cerca",
            label_visibility="collapsed",
        )

        filtro = st.segmented_control(
            "Stato",
            ["Attivi", "Sospesi", "Archiviati", "Tutti"],
            default=st.session_state["ana_filtro"],
            key="ana_filtro_sc",
            label_visibility="collapsed",
        )
        if filtro and filtro != st.session_state["ana_filtro"]:
            st.session_state["ana_filtro"] = filtro
            st.rerun()

        pazienti = _carica_pazienti(conn, cerca, st.session_state["ana_filtro"])
        st.caption(f"{len(pazienti)} paziente/i")

        # Container scrollabile per la lista
        for p in pazienti:
            pid = p.get("id")
            is_sel = (st.session_state.get("ana_sel") == pid
                      and not st.session_state.get("ana_nuovo"))
            if st.button(
                _label_card(p),
                key=f"ana_card_{pid}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state["ana_sel"] = pid
                st.session_state["ana_nuovo"] = False
                st.session_state["ana_conf_del"] = None
                # Pulisci campi del form precedente
                for k in list(st.session_state.keys()):
                    if k.startswith("mp_") and (
                        "_citta_v" in k or "_prov_v" in k or "_last_cap" in k
                    ):
                        del st.session_state[k]
                st.rerun()

    # ════════════════════════════════════════════════════════════
    #  COLONNA DESTRA: form (nuovo / modifica / vuoto)
    # ════════════════════════════════════════════════════════════
    with col_r:

        # ── NUOVO PAZIENTE ────────────────────────────────────────
        if st.session_state.get("ana_nuovo"):
            st.markdown("#### ➕ Nuovo paziente")
            st.markdown("---")

            dati = _form_anagrafici("np")

            st.markdown("##### Privacy e consensi")
            consenso_dati = _form_privacy("np_priv")

            st.markdown("---")
            cs1, cs2 = st.columns([1, 1])
            with cs1:
                salva = st.button(
                    "💾 Salva paziente",
                    type="primary", key="np_salva",
                    use_container_width=True,
                )
            with cs2:
                if st.button("✕ Annulla", key="np_annulla",
                              use_container_width=True):
                    st.session_state["ana_nuovo"] = False
                    # Pulisco i campi
                    for k in list(st.session_state.keys()):
                        if k.startswith("np_") or k.startswith("np_priv_"):
                            del st.session_state[k]
                    st.rerun()

            if salva:
                if not dati["cognome"].strip() or not dati["nome"].strip():
                    st.error("Cognome e Nome sono obbligatori.")
                elif not consenso_dati["consenso_tratt"]:
                    st.error("Il consenso al trattamento dati è obbligatorio.")
                else:
                    dati["tipo_privacy"] = consenso_dati["tipo"]
                    paz_id = _salva_nuovo(conn, dati)
                    if paz_id:
                        # Sostituisco il record consenso minimal con quello completo
                        _salva_consenso(conn, paz_id, consenso_dati)
                        st.success(f"✅ {dati['cognome']} {dati['nome']} salvato")
                        st.session_state["ana_nuovo"] = False
                        st.session_state["ana_sel"] = paz_id
                        for k in list(st.session_state.keys()):
                            if k.startswith("np_"):
                                del st.session_state[k]
                        import time
                        time.sleep(0.3)
                        st.rerun()

        # ── MODIFICA PAZIENTE ─────────────────────────────────────
        elif st.session_state.get("ana_sel"):
            paz_id = st.session_state["ana_sel"]
            rec = _carica_paziente(conn, paz_id)

            if not rec:
                st.warning("Paziente non trovato.")
                st.session_state["ana_sel"] = None
                return

            cog = rec.get("cognome", "")
            nom = rec.get("nome", "")
            dn = rec.get("data_nascita", "")
            eta = _eta(dn)

            # Header paziente
            st.markdown(f"#### {cog} {nom}")
            st.caption(f"ID: {paz_id} · {_fmt_dn(dn)}{(' · '+eta) if eta else ''}")

            # Conferma eliminazione (in cima, ben visibile)
            if st.session_state.get("ana_conf_del") == paz_id:
                st.error(
                    "⚠️ **Eliminazione definitiva**\n\n"
                    f"Stai per cancellare **{cog} {nom}** e TUTTI i dati associati: "
                    "anamnesi, valutazioni, sedute, coupon, consensi privacy, relazioni cliniche. "
                    "**L'operazione è irreversibile.**"
                )
                cd1, cd2 = st.columns(2)
                with cd1:
                    if st.button(
                        "🗑️ SÌ, ELIMINA DEFINITIVAMENTE",
                        key=f"conf_del_{paz_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if _elimina_definitivo(conn, paz_id):
                            st.success(f"Paziente {cog} {nom} eliminato.")
                            st.session_state["ana_sel"] = None
                            st.session_state["ana_conf_del"] = None
                            import time
                            time.sleep(0.5)
                            st.rerun()
                with cd2:
                    if st.button("✕ Annulla", key=f"ann_del_{paz_id}",
                                  use_container_width=True):
                        st.session_state["ana_conf_del"] = None
                        st.rerun()
                return

            st.markdown("---")

            # Form anagrafici
            dati = _form_anagrafici(f"mp_{paz_id}", rec)

            # Sezione privacy collassabile
            ultimo = _carica_ultimo_consenso(conn, paz_id)
            with st.expander(
                "🔒 Privacy e consensi",
                expanded=False,
            ):
                if ultimo and ultimo.get("data_ora"):
                    st.caption(f"Ultimo aggiornamento: {ultimo.get('data_ora')}")
                consenso_dati = _form_privacy(f"mp_priv_{paz_id}", ultimo)
                salva_priv = st.button(
                    "💾 Salva consenso",
                    key=f"mp_priv_save_{paz_id}",
                    use_container_width=True,
                )
                if salva_priv:
                    if not consenso_dati["consenso_tratt"]:
                        st.error("Il consenso al trattamento dati è obbligatorio.")
                    elif _salva_consenso(conn, paz_id, consenso_dati):
                        st.success("✅ Consenso aggiornato.")
                        import time
                        time.sleep(0.3)
                        st.rerun()

            st.markdown("---")

            # Bottoni azione
            ba1, ba2, ba3, ba4 = st.columns([2, 1, 1, 1])
            with ba1:
                salva = st.button(
                    "💾 Salva modifiche",
                    type="primary",
                    key=f"mp_salva_{paz_id}",
                    use_container_width=True,
                )
            with ba2:
                if st.button("✕ Chiudi", key=f"mp_close_{paz_id}",
                              use_container_width=True):
                    st.session_state["ana_sel"] = None
                    st.rerun()
            with ba3:
                stato_corrente = (rec.get("stato_paziente") or "ATTIVO")
                if stato_corrente == "ARCHIVIATO":
                    if st.button("♻️ Riattiva", key=f"mp_riatt_{paz_id}",
                                  use_container_width=True):
                        if _riattiva(conn, paz_id):
                            st.success("Paziente riattivato.")
                            st.rerun()
                else:
                    if st.button("🗃️ Archivia", key=f"mp_arch_{paz_id}",
                                  use_container_width=True):
                        if _archivia(conn, paz_id):
                            st.success("Paziente archiviato.")
                            st.rerun()
            with ba4:
                if st.button("🗑️ Elimina", key=f"mp_del_{paz_id}",
                              use_container_width=True):
                    st.session_state["ana_conf_del"] = paz_id
                    st.rerun()

            # Salvataggio modifiche
            if salva:
                if not dati["cognome"].strip() or not dati["nome"].strip():
                    st.error("Cognome e Nome sono obbligatori.")
                elif _salva_modifica(conn, paz_id, dati):
                    st.success("✅ Modifiche salvate.")
                    import time
                    time.sleep(0.2)
                    st.rerun()

        # ── NESSUNA SELEZIONE ─────────────────────────────────────
        else:
            n = _conta_pazienti(conn)
            st.markdown(
                f"""<div style="display:flex;flex-direction:column;
                    align-items:center;justify-content:center;
                    height:400px;color:var(--color-text-secondary)">
                <div style="font-size:3rem;margin-bottom:1rem">👥</div>
                <div style="font-size:1.2rem;font-weight:500;margin-bottom:0.5rem">
                {n} pazienti registrati</div>
                <div style="font-size:0.9rem;text-align:center">
                Clicca un paziente nella lista a sinistra<br>
                oppure crea un nuovo paziente</div>
                </div>""",
                unsafe_allow_html=True,
            )
