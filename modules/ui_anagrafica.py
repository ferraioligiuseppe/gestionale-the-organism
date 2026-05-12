# -*- coding: utf-8 -*-
"""Anagrafica Pazienti v3.0 - The Organism.

Tabella full-width con st_aggrid (ordinamento, filtri, scroll virtualizzato).
Click su riga → dialog modale di modifica paziente.
Bottone "Nuovo paziente" → dialog nuovo paziente.
Bottone "Esporta Excel" → dialog password → download .xlsx.
Eliminazione → dialog di conferma.

Generatore + validatore Codice Fiscale, lookup CAP automatico,
sezione Privacy/GDPR completa restano dentro il dialog di modifica.
"""
from __future__ import annotations
import datetime
import io
import streamlit as st


# ════════════════════════════════════════════════════════════════════
#  HELPERS
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


def _cf_helpers():
    try:
        from modules.app_core import genera_codice_fiscale, valida_codice_fiscale
        return genera_codice_fiscale, valida_codice_fiscale
    except Exception:
        return None, None


# ════════════════════════════════════════════════════════════════════
#  QUERY DB
# ════════════════════════════════════════════════════════════════════

def _row_to_plain_dict(row, cols):
    """Converte una riga DB (DictRow/RealDictRow/tuple) in dict Python serializzabile.

    Necessario perché st.cache_data usa pickle e i tipi nativi del driver
    (psycopg2 DictRow, sqlite Row) non sempre sono pickle-friendly.
    Inoltre converte date/datetime in ISO string per la stessa ragione.
    """
    if row is None:
        return None
    d = row if isinstance(row, dict) else dict(zip(cols, row))
    out = {}
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray, memoryview)):
            try:
                out[k] = bytes(v).decode("utf-8", errors="replace")
            except Exception:
                out[k] = None
        else:
            out[k] = v
    return out


@st.cache_data(ttl=30, show_spinner=False)
def _carica_pazienti_full(_conn, filtro_stato: str = "Attivi"):
    conn = _conn
    try:
        cur = conn.cursor()
        where = []
        if filtro_stato == "Attivi":
            where.append("(stato_paziente IS NULL OR stato_paziente = 'ATTIVO')")
        elif filtro_stato == "Sospesi":
            where.append("stato_paziente = 'SOSPESO'")
        elif filtro_stato == "Archiviati":
            where.append("stato_paziente = 'ARCHIVIATO'")
        sql = (
            "SELECT id, cognome, nome, data_nascita, telefono, email, "
            "stato_paziente, codice_fiscale, citta "
            "FROM pazienti"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY cognome, nome"
        cur.execute(sql)
        rows = cur.fetchall() or []
        cols = [d[0] for d in cur.description] if cur.description else []
        return [_row_to_plain_dict(r, cols) for r in rows]
    except Exception as e:
        st.error(f"Errore lista: {e}")
        return []


@st.cache_data(ttl=30, show_spinner=False)
def _carica_paziente(_conn, paz_id):
    conn = _conn
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description] if cur.description else []
        return _row_to_plain_dict(row, cols)
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _carica_ultimo_consenso(_conn, paz_id):
    conn = _conn
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
        cols = [d[0] for d in cur.description] if cur.description else []
        return _row_to_plain_dict(row, cols)
    except Exception:
        return None


def _invalida_cache():
    try:
        _carica_pazienti_full.clear()
        _carica_paziente.clear()
        _carica_ultimo_consenso.clear()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════
#  SCRITTURE
# ════════════════════════════════════════════════════════════════════

def _salva_nuovo(conn, d: dict):
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
        try:
            cur.execute("""
                INSERT INTO consensi_privacy
                (paziente_id, tipo, consenso_trattamento,
                 consenso_comunicazioni, canale_email, canale_whatsapp, data_ora)
                VALUES (%s,%s,1,1,1,1,NOW())
            """, (paz_id, d.get("tipo_privacy", "adulto")))
        except Exception:
            pass
        conn.commit()
        _invalida_cache()
        return paz_id
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore salvataggio: {e}")
        return None


def _salva_modifica(conn, paz_id, d: dict) -> bool:
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
        _invalida_cache()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore: {e}")
        return False


def _salva_consenso(conn, paz_id, c: dict) -> bool:
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
        _invalida_cache()
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
        _invalida_cache()
        return True
    except Exception as e:
        st.error(f"Errore archiviazione: {e}")
        return False


def _riattiva(conn, paz_id) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pazienti SET stato_paziente='ATTIVO' WHERE id=%s", (paz_id,))
        conn.commit()
        _invalida_cache()
        return True
    except Exception as e:
        st.error(f"Errore riattivazione: {e}")
        return False


def _elimina_definitivo(conn, paz_id) -> bool:
    cur = conn.cursor()
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
    try:
        cur.execute("DELETE FROM pazienti WHERE id=%s", (paz_id,))
        conn.commit()
        _invalida_cache()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore eliminazione: {e}")
        return False


# ════════════════════════════════════════════════════════════════════
#  EXPORT EXCEL
# ════════════════════════════════════════════════════════════════════

def _genera_excel(pazienti: list) -> bytes:
    import pandas as pd
    rows = []
    for p in pazienti:
        rows.append({
            "ID": p.get("id"),
            "Stato": p.get("stato_paziente") or "ATTIVO",
            "Cognome": p.get("cognome", ""),
            "Nome": p.get("nome", ""),
            "Data nascita": _fmt_dn(p.get("data_nascita")),
            "Età": _eta_anni(p.get("data_nascita")) or "",
            "Telefono": p.get("telefono", ""),
            "Email": p.get("email", ""),
            "CF": p.get("codice_fiscale", "") or "",
            "Città": p.get("citta", "") or "",
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Pazienti", index=False)
    buf.seek(0)
    return buf.getvalue()


def _password_export() -> str:
    try:
        return st.secrets.get("EXPORT_PASSWORD", "theorganism2026")
    except Exception:
        return "theorganism2026"


# ════════════════════════════════════════════════════════════════════
#  FORM ANAGRAFICI (riusabile in dialog nuovo + modifica)
# ════════════════════════════════════════════════════════════════════

def _form_anagrafici(key: str, r: dict | None = None) -> dict:
    is_nuovo = r is None
    r = r or {}

    c1, c2 = st.columns(2)
    with c1:
        cognome = st.text_input("Cognome *", value=r.get("cognome", "") or "",
                                  key=f"{key}_cog")
    with c2:
        nome = st.text_input("Nome *", value=r.get("nome", "") or "",
                              key=f"{key}_nom")

    c3, c4, c5 = st.columns([2, 1, 2])
    with c3:
        data_str = st.text_input("Data nascita",
                                   value=_fmt_dn(r.get("data_nascita", "")),
                                   key=f"{key}_dn",
                                   placeholder="GG/MM/AAAA")
    with c4:
        sesso_opts = ["M", "F", "Altro"]
        sesso_val = r.get("sesso", "M") or "M"
        sesso = st.selectbox("Sesso", sesso_opts,
                              index=sesso_opts.index(sesso_val) if sesso_val in sesso_opts else 0,
                              key=f"{key}_sex")
    with c5:
        cf_default = st.session_state.pop(f"{key}_cf_generato", None)
        if cf_default is None:
            cf_default = r.get("codice_fiscale", "") or ""
        cf = st.text_input("Codice fiscale", value=cf_default,
                            key=f"{key}_cf",
                            placeholder="Lascia vuoto se non disponibile").upper()

    if cf.strip():
        _, valida = _cf_helpers()
        if valida is not None:
            if valida(cf.strip()):
                st.markdown(
                    "<div style='color:var(--color-text-success);font-size:11px;margin-top:-8px'>"
                    "✓ Codice fiscale valido</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div style='color:var(--color-text-warning);font-size:11px;margin-top:-8px'>"
                    "⚠️ Non riconosciuto dall'algoritmo (puoi salvarlo comunque)</div>",
                    unsafe_allow_html=True)

    _genera_cf_expander(key, cognome, nome, data_str, sesso)

    c6, c7 = st.columns(2)
    with c6:
        tel = st.text_input("Telefono", value=r.get("telefono", "") or "",
                             key=f"{key}_tel")
    with c7:
        email = st.text_input("Email", value=r.get("email", "") or "",
                                key=f"{key}_email")

    indirizzo = st.text_input("Indirizzo (via, civico)",
                                value=r.get("indirizzo", "") or "",
                                key=f"{key}_ind")

    c8, c9, c10 = st.columns([1, 2, 1])
    with c8:
        cap = st.text_input("CAP", value=r.get("cap", "") or "",
                             key=f"{key}_cap", max_chars=5)

    # Chiavi di session_state per Città / Prov
    # Regola Streamlit: session_state[key_widget] può essere modificato SOLO
    # prima che il widget con quella chiave sia istanziato. Quindi facciamo
    # il CAP lookup PRIMA di renderizzare Città e Prov.
    citta_key = f"{key}_citta"
    prov_key = f"{key}_prov"
    last_cap_key = f"{key}_last_cap"

    if citta_key not in st.session_state:
        st.session_state[citta_key] = r.get("citta", "") or ""
    if prov_key not in st.session_state:
        st.session_state[prov_key] = r.get("provincia", "") or ""
    if not is_nuovo and last_cap_key not in st.session_state:
        st.session_state[last_cap_key] = r.get("cap", "") or ""

    prev_cap = st.session_state.get(last_cap_key, "")
    if cap and cap != prev_cap:
        info = _cap_lookup(cap)
        if info:
            st.session_state[citta_key] = info["citta"]
            st.session_state[prov_key] = info["provincia"]
        st.session_state[last_cap_key] = cap

    with c9:
        citta = st.text_input("Città", key=citta_key)
    with c10:
        prov = st.text_input("Prov.", key=prov_key, max_chars=2)

    if not is_nuovo:
        stati = ["ATTIVO", "SOSPESO", "ARCHIVIATO"]
        stato_val = r.get("stato_paziente", "ATTIVO") or "ATTIVO"
        stato = st.selectbox("Stato", stati,
                              index=stati.index(stato_val) if stato_val in stati else 0,
                              key=f"{key}_stato")
    else:
        stato = "ATTIVO"

    return {
        "cognome": cognome, "nome": nome, "data_str": data_str,
        "sesso": sesso, "cf": cf, "tel": tel, "email": email,
        "indirizzo": indirizzo, "cap": cap, "citta": citta, "prov": prov,
        "stato": stato, "_is_nuovo": is_nuovo,
    }


def _genera_cf_expander(key: str, cognome: str, nome: str,
                         data_str: str, sesso: str) -> None:
    genera, _ = _cf_helpers()
    if genera is None:
        return
    with st.expander("🛠️ Genera codice fiscale (se il paziente non lo ricorda)"):
        st.caption("Usa cognome, nome, data e sesso dal form sopra. Aggiungi qui comune e provincia di nascita.")
        c1, c2 = st.columns([2, 1])
        with c1:
            comune = st.text_input("Comune di nascita", key=f"{key}_cf_comune",
                                     placeholder="Es. Pagani")
        with c2:
            prov_n = st.text_input("Sigla prov.", key=f"{key}_cf_prov",
                                     placeholder="Es. SA", max_chars=2)
        if st.button("Genera CF", key=f"{key}_cf_btn", use_container_width=True):
            cf_gen = genera(cognome=cognome, nome=nome,
                             data_nascita_str=data_str, sesso=sesso,
                             comune_nascita=comune, provincia_nascita=prov_n)
            if cf_gen is None:
                st.error("Impossibile generare il CF. Controlla i dati anagrafici e che il comune sia presente in archivio.")
            else:
                st.session_state[f"{key}_cf_generato"] = cf_gen
                st.success(f"CF generato: **{cf_gen}**")
                st.rerun()


# ════════════════════════════════════════════════════════════════════
#  FORM PRIVACY
# ════════════════════════════════════════════════════════════════════

def _form_privacy(key: str, c: dict | None = None) -> dict:
    c = c or {}
    tipo_val = (c.get("tipo") or "adulto").lower()
    tipo = st.radio("Tipo soggetto", ["Adulto", "Minore"],
                     index=0 if tipo_val == "adulto" else 1,
                     horizontal=True, key=f"{key}_priv_tipo")

    tutore_nome = tutore_cf = tutore_tel = tutore_email = ""
    if tipo == "Minore":
        st.markdown("**Dati genitore / tutore**")
        ct1, ct2 = st.columns(2)
        with ct1:
            tutore_nome = st.text_input("Nome e cognome tutore",
                                          value=c.get("tutore_nome", "") or "",
                                          key=f"{key}_tut_n")
            tutore_tel = st.text_input("Telefono tutore",
                                         value=c.get("tutore_telefono", "") or "",
                                         key=f"{key}_tut_t")
        with ct2:
            tutore_cf = st.text_input("CF tutore",
                                        value=c.get("tutore_cf", "") or "",
                                        key=f"{key}_tut_cf").upper()
            tutore_email = st.text_input("Email tutore",
                                           value=c.get("tutore_email", "") or "",
                                           key=f"{key}_tut_e")

    st.markdown("**Consensi**")
    consenso_tratt = st.checkbox(
        "Consenso al trattamento dati per finalità cliniche/gestionali (obbligatorio)",
        value=bool(c.get("consenso_trattamento", 1)) if c else False,
        key=f"{key}_c_tratt")
    consenso_com = st.checkbox(
        "Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)",
        value=bool(c.get("consenso_comunicazioni", 1)) if c else True,
        key=f"{key}_c_com")

    st.markdown("**Canali autorizzati**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        can_email = st.checkbox("Email",
                                  value=bool(c.get("canale_email", 1)) if c else True,
                                  key=f"{key}_can_e")
    with cc2:
        can_sms = st.checkbox("SMS",
                                value=bool(c.get("canale_sms", 0)) if c else False,
                                key=f"{key}_can_s")
    with cc3:
        can_wa = st.checkbox("WhatsApp",
                                value=bool(c.get("canale_whatsapp", 1)) if c else True,
                                key=f"{key}_can_w")

    st.markdown("**Marketing (facoltativo)**")
    consenso_mkt = st.checkbox(
        "Consenso a comunicazioni promozionali e contenuti informativi",
        value=bool(c.get("consenso_marketing", 0)) if c else False,
        key=f"{key}_c_mkt")
    usa_klaviyo = st.checkbox(
        "Autorizzo l'uso di Klaviyo per newsletter/SMS marketing",
        value=bool(c.get("usa_klaviyo", 0)) if c else False,
        key=f"{key}_klav")

    note = st.text_area("Note privacy (facoltative)",
                          value=c.get("note", "") or "",
                          key=f"{key}_note", height=68)

    return {
        "tipo": tipo.lower(),
        "tutore_nome": tutore_nome, "tutore_cf": tutore_cf,
        "tutore_tel": tutore_tel, "tutore_email": tutore_email,
        "consenso_tratt": consenso_tratt, "consenso_com": consenso_com,
        "consenso_mkt": consenso_mkt, "can_email": can_email,
        "can_sms": can_sms, "can_wa": can_wa, "usa_klaviyo": usa_klaviyo,
        "note": note,
    }


# ════════════════════════════════════════════════════════════════════
#  DIALOGS
# ════════════════════════════════════════════════════════════════════

@st.dialog("Modifica paziente", width="large")
def _dialog_modifica(conn, paz_id: int):
    rec = _carica_paziente(conn, paz_id)
    if not rec:
        st.error("Paziente non trovato.")
        if st.button("Chiudi"):
            st.rerun()
        return

    cog = rec.get("cognome", "")
    nom = rec.get("nome", "")
    dn = rec.get("data_nascita", "")
    eta = _eta_anni(dn)

    info_text = f"**ID:** {paz_id} · {_fmt_dn(dn)}"
    if eta is not None:
        info_text += f" · {eta} anni"
    st.caption(info_text)
    st.markdown(f"### {cog} {nom}")

    dati = _form_anagrafici(f"mp_{paz_id}", rec)

    ultimo = _carica_ultimo_consenso(conn, paz_id)
    with st.expander("🔒 Privacy e consensi"):
        if ultimo and ultimo.get("data_ora"):
            st.caption(f"Ultimo aggiornamento: {ultimo.get('data_ora')}")
        consenso_dati = _form_privacy(f"mp_priv_{paz_id}", ultimo)
        if st.button("💾 Salva consenso", key=f"mp_priv_save_{paz_id}",
                       use_container_width=True):
            if not consenso_dati["consenso_tratt"]:
                st.error("Il consenso al trattamento dati è obbligatorio.")
            elif _salva_consenso(conn, paz_id, consenso_dati):
                st.success("✅ Consenso aggiornato.")
                import time
                time.sleep(0.3)
                st.rerun()

    st.markdown("---")

    ba1, ba2, ba3, ba4 = st.columns([2, 1, 1, 1])
    with ba1:
        salva = st.button("💾 Salva modifiche", type="primary",
                            key=f"mp_salva_{paz_id}", use_container_width=True)
    with ba2:
        chiudi = st.button("✕ Chiudi", key=f"mp_close_{paz_id}",
                             use_container_width=True)
    with ba3:
        stato_corrente = (rec.get("stato_paziente") or "ATTIVO")
        if stato_corrente == "ARCHIVIATO":
            arch = st.button("♻️ Riattiva", key=f"mp_riatt_{paz_id}",
                                use_container_width=True)
        else:
            arch = st.button("🗃️ Archivia", key=f"mp_arch_{paz_id}",
                                use_container_width=True)
    with ba4:
        elim = st.button("🗑️ Elimina", key=f"mp_del_{paz_id}",
                            use_container_width=True)

    if chiudi:
        st.rerun()
    if salva:
        if not dati["cognome"].strip() or not dati["nome"].strip():
            st.error("Cognome e Nome sono obbligatori.")
        elif _salva_modifica(conn, paz_id, dati):
            st.success("✅ Modifiche salvate.")
            import time
            time.sleep(0.3)
            st.rerun()
    if arch:
        ok = (_riattiva(conn, paz_id) if stato_corrente == "ARCHIVIATO"
                else _archivia(conn, paz_id))
        if ok:
            st.rerun()
    if elim:
        st.session_state["ana_da_eliminare"] = paz_id
        st.session_state["ana_da_eliminare_nome"] = f"{cog} {nom}"
        st.rerun()


@st.dialog("Nuovo paziente", width="large")
def _dialog_nuovo(conn):
    st.markdown("Inserisci i dati del nuovo paziente.")
    dati = _form_anagrafici("np")
    st.markdown("##### Privacy e consensi")
    consenso_dati = _form_privacy("np_priv")
    st.markdown("---")
    cs1, cs2 = st.columns(2)
    with cs1:
        salva = st.button("💾 Salva paziente", type="primary",
                            key="np_salva", use_container_width=True)
    with cs2:
        annulla = st.button("✕ Annulla", key="np_annulla",
                              use_container_width=True)
    if annulla:
        for k in list(st.session_state.keys()):
            if k.startswith("np_"):
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
                _salva_consenso(conn, paz_id, consenso_dati)
                st.session_state["ana_msg_success"] = (
                    f"✅ {dati['cognome']} {dati['nome']} salvato."
                )
                for k in list(st.session_state.keys()):
                    if k.startswith("np_"):
                        del st.session_state[k]
                import time
                time.sleep(0.3)
                st.rerun()


@st.dialog("⚠️ Conferma eliminazione")
def _dialog_elimina(conn, paz_id: int, nome_completo: str):
    st.error(
        f"Stai per cancellare **{nome_completo}** e TUTTI i dati associati: "
        "anamnesi, valutazioni, sedute, coupon, consensi privacy, relazioni cliniche. "
        "**L'operazione è irreversibile.**"
    )
    cd1, cd2 = st.columns(2)
    with cd1:
        if st.button("🗑️ SÌ, ELIMINA DEFINITIVAMENTE",
                       key=f"conf_del_{paz_id}", type="primary",
                       use_container_width=True):
            if _elimina_definitivo(conn, paz_id):
                st.session_state.pop("ana_da_eliminare", None)
                st.session_state.pop("ana_da_eliminare_nome", None)
                st.session_state["ana_msg_success"] = (
                    f"Paziente {nome_completo} eliminato."
                )
                import time
                time.sleep(0.4)
                st.rerun()
    with cd2:
        if st.button("✕ Annulla", key=f"ann_del_{paz_id}",
                       use_container_width=True):
            st.session_state.pop("ana_da_eliminare", None)
            st.session_state.pop("ana_da_eliminare_nome", None)
            st.rerun()


@st.dialog("📥 Esporta in Excel")
def _dialog_export(pazienti: list, totale: int):
    st.markdown(
        f"Stai per esportare **{totale} pazienti** (filtro corrente). "
        "Inserisci la password di esportazione per procedere."
    )
    pwd = st.text_input("Password", type="password", key="exp_pwd")
    c1, c2 = st.columns(2)
    with c1:
        ok = st.button("📥 Genera file", type="primary", key="exp_ok",
                         use_container_width=True)
    with c2:
        if st.button("✕ Annulla", key="exp_ann", use_container_width=True):
            st.rerun()
    if ok:
        if pwd != _password_export():
            st.error("Password errata.")
        else:
            try:
                xlsx_bytes = _genera_excel(pazienti)
                st.success("✅ File generato. Clicca per scaricarlo.")
                st.download_button(
                    "⬇️ Scarica pazienti.xlsx",
                    data=xlsx_bytes,
                    file_name=f"pazienti_export_{datetime.date.today().isoformat()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_dl",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Errore generazione file: {e}")


# ════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPALE
# ════════════════════════════════════════════════════════════════════

def render_anagrafica(conn) -> None:
    """Render principale anagrafica v3.0 - aggrid + dialog."""

    st.session_state.setdefault("ana_filtro", "Attivi")

    # Messaggio post-rerun
    if msg := st.session_state.pop("ana_msg_success", None):
        st.success(msg)

    # Header
    h1, h2, h3 = st.columns([3, 1, 1])
    with h1:
        st.subheader("Anagrafica Pazienti")
    with h2:
        if st.button("➕ Nuovo paziente", type="primary",
                       key="btn_nuovo", use_container_width=True):
            st.session_state["ana_apri_nuovo"] = True
    with h3:
        if st.button("📥 Esporta Excel", key="btn_export",
                       use_container_width=True):
            st.session_state["ana_apri_export"] = True

    # Filtro stato
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

    # Carico dati
    pazienti = _carica_pazienti_full(conn, st.session_state["ana_filtro"])
    st.caption(f"{len(pazienti)} paziente/i")

    if not pazienti:
        st.info("Nessun paziente nel filtro corrente.")
        # Anche con lista vuota, se l'utente clicca "Nuovo paziente" devo gestirlo
        if st.session_state.pop("ana_apri_nuovo", False):
            _dialog_nuovo(conn)
        return

    # DataFrame per aggrid
    import pandas as pd
    rows_df = []
    for p in pazienti:
        rows_df.append({
            "_id": p.get("id"),
            "Stato": _badge_stato(p.get("stato_paziente")),
            "Cognome": p.get("cognome", "") or "",
            "Nome": p.get("nome", "") or "",
            "Data nascita": _fmt_dn(p.get("data_nascita")),
            "Età": _eta_anni(p.get("data_nascita")) or "",
            "Telefono": p.get("telefono", "") or "",
        })
    df = pd.DataFrame(rows_df)

    # Import lazy aggrid
    try:
        from st_aggrid import (
            AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode,
        )
    except ImportError:
        st.error(
            "La libreria `streamlit-aggrid` non è installata. "
            "Aggiungila al requirements.txt e riavvia l'app."
        )
        return

    gob = GridOptionsBuilder.from_dataframe(df)
    gob.configure_default_column(
        filter=True, sortable=True, resizable=True, floatingFilter=True,
    )
    gob.configure_column("_id", hide=True)
    gob.configure_column("Stato", width=80, pinned="left",
                          filter="agTextColumnFilter", floatingFilter=False)
    gob.configure_column("Cognome", width=180, pinned="left", sort="asc")
    gob.configure_column("Nome", width=160)
    gob.configure_column("Data nascita", width=130)
    gob.configure_column("Età", width=80, type=["numericColumn"],
                          floatingFilter=False)
    gob.configure_column("Telefono", width=140, floatingFilter=False)
    gob.configure_selection(selection_mode="single", use_checkbox=False)
    gob.configure_grid_options(
        rowHeight=34, headerHeight=36, floatingFiltersHeight=32,
        suppressCellFocus=True, domLayout="normal",
    )

    # Nonce per resettare la selezione AgGrid dopo apertura del dialog.
    # Senza questo, AgGrid mantiene la riga selezionata anche dopo la chiusura
    # del dialog: ri-cliccare la stessa riga non triggera selection_changed e
    # il dialog non si riapre più.
    sel_nonce_key = f"ana_sel_nonce_{st.session_state['ana_filtro']}"
    if sel_nonce_key not in st.session_state:
        st.session_state[sel_nonce_key] = 0

    grid_response = AgGrid(
        df,
        gridOptions=gob.build(),
        height=560,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=False,
        theme="balham",
        fit_columns_on_grid_load=False,
        key=f"aggrid_pazienti_{st.session_state['ana_filtro']}_{st.session_state[sel_nonce_key]}",
    )

    # Selezione → apri dialog modifica
    selected = grid_response.get("selected_rows", [])
    if hasattr(selected, "to_dict"):
        try:
            selected = selected.to_dict("records")
        except Exception:
            selected = []
    if selected:
        try:
            paz_id = int(selected[0].get("_id"))
            # Incrementa il nonce: al prossimo rerun la grid si ricostruisce
            # senza selezione, così cliccare di nuovo lo stesso paziente
            # riaprirà correttamente il dialog.
            st.session_state[sel_nonce_key] += 1
            _dialog_modifica(conn, paz_id)
        except Exception:
            pass

    # Dialog conferma eliminazione
    if st.session_state.get("ana_da_eliminare"):
        _dialog_elimina(
            conn,
            st.session_state["ana_da_eliminare"],
            st.session_state.get("ana_da_eliminare_nome", "questo paziente"),
        )

    # Dialog nuovo paziente
    if st.session_state.pop("ana_apri_nuovo", False):
        _dialog_nuovo(conn)

    # Dialog export
    if st.session_state.pop("ana_apri_export", False):
        _dialog_export(pazienti, len(pazienti))
