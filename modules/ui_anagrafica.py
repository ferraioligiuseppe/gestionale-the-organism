# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  UI ANAGRAFICA PAZIENTE                                             ║
║                                                                     ║
║  Migliorie rispetto all'originale:                                  ║
║  • Ordine tab naturale: Cognome → Nome → Data → ...                 ║
║  • Data nascita: GG/MM/AAAA con validazione                        ║
║  • CAP → auto-fill Città e Provincia (API comuni italiani)          ║
║  • SMS pre-selezionato                                              ║
║  • Link privacy direttamente in fondo al form                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
import datetime
import json
import re
import streamlit as st

# ══════════════════════════════════════════════════════════════════════
#  UTILITY
# ══════════════════════════════════════════════════════════════════════

def _parse_data(s: str) -> datetime.date | None:
    """Accetta GG/MM/AAAA oppure AAAA-MM-GG."""
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _fmt_data_it(iso: str | None) -> str:
    """Converte YYYY-MM-DD → GG/MM/AAAA."""
    if not iso:
        return ""
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _cap_lookup(cap: str) -> dict:
    """
    Cerca CAP italiano via API pubblica.
    Ritorna {"citta": "...", "provincia": "..."} o {} se non trovato.
    """
    cap = cap.strip()
    if len(cap) != 5 or not cap.isdigit():
        return {}
    try:
        import requests
        r = requests.get(
            f"https://api.zippopotam.us/it/{cap}",
            timeout=3
        )
        if r.status_code == 200:
            data = r.json()
            places = data.get("places", [])
            if places:
                city  = places[0].get("place name", "")
                state = places[0].get("state abbreviation", "")
                return {"citta": city.title(), "provincia": state.upper()}
    except Exception:
        pass
    return {}


# ══════════════════════════════════════════════════════════════════════
#  FORM NUOVO PAZIENTE
# ══════════════════════════════════════════════════════════════════════

def render_form_nuovo_paziente(conn) -> None:
    """Form inserimento nuovo paziente con tutte le migliorie."""

    st.subheader("➕ Nuovo paziente")

    # ── CAP lookup (fuori dal form per usare session_state) ───────────
    if "cap_lookup_result" not in st.session_state:
        st.session_state["cap_lookup_result"] = {}

    # ── Sezione dati anagrafici ───────────────────────────────────────
    with st.container():
        # Riga 1: Cognome | Nome
        c1, c2 = st.columns(2)
        with c1:
            cognome = st.text_input("Cognome *", key="np_cognome",
                                    placeholder="Rossi")
        with c2:
            nome = st.text_input("Nome *", key="np_nome",
                                 placeholder="Mario")

        # Riga 2: Data nascita | Sesso | Codice fiscale
        c3, c4, c5 = st.columns([2, 1, 2])
        with c3:
            data_str = st.text_input(
                "Data di nascita",
                key="np_data",
                placeholder="GG/MM/AAAA",
                help="Formato: giorno/mese/anno — es. 15/03/1990"
            )
            if data_str:
                d = _parse_data(data_str)
                if d:
                    anni = (datetime.date.today() - d).days // 365
                    st.caption(f"✅ {d.strftime('%d %b %Y')} — {anni} anni")
                else:
                    st.caption("⚠️ Formato non valido — usa GG/MM/AAAA")

        with c4:
            sesso = st.selectbox("Sesso", ["", "M", "F", "Altro"],
                                 key="np_sesso")
        with c5:
            cf = st.text_input("Codice fiscale", key="np_cf",
                               placeholder="RSSMRA90A15...").upper()

        # Riga 3: Indirizzo
        indirizzo = st.text_input("Indirizzo", key="np_indirizzo",
                                  placeholder="Via Roma, 1")

        # Riga 4: CAP → auto-fill Città + Provincia
        c6, c7, c8 = st.columns([1, 2, 1])
        with c6:
            cap_val = st.text_input(
                "CAP",
                key="np_cap",
                placeholder="84100",
                max_chars=5,
            )
            # Auto-lookup quando CAP è 5 cifre
            if len(cap_val) == 5 and cap_val.isdigit():
                if st.session_state.get("_last_cap") != cap_val:
                    st.session_state["_last_cap"] = cap_val
                    with st.spinner(""):
                        result = _cap_lookup(cap_val)
                        st.session_state["cap_lookup_result"] = result

        lookup = st.session_state.get("cap_lookup_result", {})

        with c7:
            citta_default = lookup.get("citta", "")
            citta = st.text_input("Città", key="np_citta",
                                  value=citta_default,
                                  placeholder="Salerno")
        with c8:
            prov_default = lookup.get("provincia", "")
            provincia = st.text_input("Provincia", key="np_prov",
                                      value=prov_default,
                                      placeholder="SA",
                                      max_chars=2).upper()

        # Riga 5: Telefono | Email
        c9, c10 = st.columns(2)
        with c9:
            telefono = st.text_input("Telefono", key="np_tel",
                                     placeholder="+39 089 000000")
        with c10:
            email = st.text_input("Email", key="np_email",
                                  placeholder="mario.rossi@email.it")

    # ── Sezione privacy ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔒 Privacy e Consensi (GDPR)")
    st.caption(
        "I consensi vengono registrati nel gestionale. "
        "Puoi generare il link per la firma digitale dopo il salvataggio."
    )

    tipo_privacy = st.radio("Tipo", ["Adulto", "Minore"],
                            horizontal=True, key="np_tipo_privacy")

    tutore_nome = tutore_cf = tutore_tel = tutore_email = ""
    if tipo_privacy == "Minore":
        st.markdown("**Dati genitore / tutore**")
        t1, t2 = st.columns(2)
        with t1:
            tutore_nome = st.text_input("Nome e cognome tutore", key="np_t_nome")
            tutore_tel  = st.text_input("Telefono tutore", key="np_t_tel")
        with t2:
            tutore_cf    = st.text_input("CF tutore", key="np_t_cf").upper()
            tutore_email = st.text_input("Email tutore", key="np_t_email")

    st.markdown("**Consensi**")
    consenso_dati  = st.checkbox(
        "✅ Consenso al trattamento dei dati per finalità cliniche (obbligatorio)",
        value=False, key="np_cons_dati"
    )
    consenso_comm  = st.checkbox(
        "Consenso a comunicazioni di servizio (appuntamenti, promemoria)",
        value=True, key="np_cons_comm"
    )
    consenso_mkt   = st.checkbox(
        "Consenso a comunicazioni promozionali / offerte",
        value=False, key="np_cons_mkt"
    )

    st.markdown("**Canali di comunicazione**")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        canale_email = st.checkbox("📧 Email",    value=True,  key="np_ch_email")
    with cc2:
        canale_sms   = st.checkbox("💬 SMS",      value=True,  key="np_ch_sms")   # ← pre-selezionato
    with cc3:
        canale_wa    = st.checkbox("📱 WhatsApp", value=True,  key="np_ch_wa")

    note_priv = st.text_area("Note privacy (facoltative)", key="np_note_priv",
                              height=60)

    # ── Salvataggio ───────────────────────────────────────────────────
    st.markdown("---")
    if st.button("💾 Salva paziente", type="primary", key="np_salva"):
        _salva_nuovo_paziente(
            conn=conn,
            cognome=cognome, nome=nome,
            data_str=data_str, sesso=sesso, cf=cf,
            indirizzo=indirizzo, cap=cap_val, citta=citta,
            provincia=provincia, telefono=telefono, email=email,
            tipo_privacy=tipo_privacy,
            tutore_nome=tutore_nome, tutore_cf=tutore_cf,
            tutore_tel=tutore_tel, tutore_email=tutore_email,
            consenso_dati=consenso_dati, consenso_comm=consenso_comm,
            consenso_mkt=consenso_mkt,
            canale_email=canale_email, canale_sms=canale_sms,
            canale_wa=canale_wa, note_priv=note_priv,
        )


def _salva_nuovo_paziente(conn, *, cognome, nome, data_str, sesso, cf,
                          indirizzo, cap, citta, provincia, telefono, email,
                          tipo_privacy, tutore_nome, tutore_cf,
                          tutore_tel, tutore_email, consenso_dati,
                          consenso_comm, consenso_mkt, canale_email,
                          canale_sms, canale_wa, note_priv) -> None:

    if not cognome.strip() or not nome.strip():
        st.error("Cognome e Nome sono obbligatori.")
        return
    if not consenso_dati:
        st.error("Il consenso al trattamento dati è obbligatorio.")
        return

    # Parsing data
    data_iso = None
    if data_str.strip():
        d = _parse_data(data_str.strip())
        if not d:
            st.error("Data non valida — usa GG/MM/AAAA (es. 15/03/1990).")
            return
        data_iso = d.isoformat()

    cf_clean = cf.strip().upper() or None

    try:
        cur = conn.cursor()

        # Inserimento paziente
        cur.execute("""
            INSERT INTO Pazienti
            (Cognome, Nome, Data_Nascita, Sesso, Telefono, Email,
             Indirizzo, CAP, Citta, Provincia, Codice_Fiscale, Stato_Paziente)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            cognome.strip(), nome.strip(), data_iso, sesso,
            telefono.strip(), email.strip(), indirizzo.strip(),
            cap.strip(), citta.strip(),
            provincia.strip().upper(), cf_clean, "ATTIVO",
        ))
        row = cur.fetchone()
        paz_id = int(row["id"] if isinstance(row, dict) else row[0])

        # Consenso privacy
        cur.execute("""
            INSERT INTO consensi_privacy
            (paziente_id, tipo_soggetto, consenso_trattamento,
             consenso_comunicazioni, consenso_marketing,
             Canale_Email, Canale_SMS, Canale_WhatsApp,
             Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
             Note, Data_Ora)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """, (
            paz_id, tipo_privacy,
            1 if consenso_dati  else 0,
            1 if consenso_comm  else 0,
            1 if consenso_mkt   else 0,
            1 if canale_email   else 0,
            1 if canale_sms     else 0,
            1 if canale_wa      else 0,
            tutore_nome, tutore_cf, tutore_tel, tutore_email,
            note_priv,
        ))
        conn.commit()

        st.success(f"✅ Paziente **{cognome} {nome}** salvato (ID: {paz_id})")
        st.markdown("---")

        # ── Link privacy immediato ────────────────────────────────────
        st.markdown("### 🔗 Invia link firma privacy")
        st.caption(
            "Il paziente apre il link sul telefono, legge il consenso, "
            "firma con il dito e invia. La firma viene salvata automaticamente."
        )
        _genera_link_privacy(conn, paz_id, tipo_privacy,
                             email.strip(), tutore_email.strip(),
                             cognome, nome)

        # Reset session state cap
        st.session_state["cap_lookup_result"] = {}
        st.session_state.pop("_last_cap", None)

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore salvataggio: {e}")


def _genera_link_privacy(conn, paz_id: int, doc_type: str,
                         email_paz: str, email_tut: str,
                         cognome: str, nome: str) -> None:
    """Genera e mostra il link di firma privacy appena dopo il salvataggio."""
    try:
        import hashlib, hmac, secrets as _sec
        from zoneinfo import ZoneInfo

        token_secret = st.secrets.get("privacy", {}).get("TOKEN_SECRET", "fallback")
        expire_sec   = int(st.secrets.get("privacy", {}).get("TOKEN_EXPIRE_SECONDS", 172800))
        base_url     = st.secrets.get("public_links", {}).get("BASE_URL", "").rstrip("/")

        if not base_url:
            st.warning("BASE_URL non configurata nei Secrets — impossibile generare il link.")
            return

        # Crea token
        token = _sec.token_urlsafe(32)
        now   = datetime.datetime.now(ZoneInfo("Europe/Rome"))
        exp   = now + datetime.timedelta(seconds=expire_sec)

        key  = token_secret.encode() if isinstance(token_secret, str) else token_secret
        # Formato compatibile con _make_sign_token di app_core
        payload = f"{paz_id}:{doc_type}:{int(exp.timestamp())}"
        sig  = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
        full_token = f"{payload}:{sig}"
        import base64 as _b64
        encoded = _b64.urlsafe_b64encode(full_token.encode()).decode()

        url = f"{base_url}/?sign={encoded}"

        st.code(url, language="text")

        # WhatsApp
        testo = f"Gentile {cognome} {nome}, ecco il link per firmare il consenso privacy: {url}"
        wa    = f"https://wa.me/?text={testo.replace(' ','%20')}"
        st.markdown(f"[📱 Invia via WhatsApp]({wa})")

        # Email
        dest = email_tut or email_paz
        if dest:
            subj  = "Consenso privacy — Studio The Organism"
            corpo = f"Apri questo link per firmare il consenso:\n{url}"
            mailto = f"mailto:{dest}?subject={subj.replace(' ','%20')}&body={corpo.replace(' ','%20').replace('\n','%0A')}"
            st.markdown(f"[📧 Apri in client email]({mailto})")

    except Exception as e:
        st.warning(f"Link privacy non disponibile: {e}")


# ══════════════════════════════════════════════════════════════════════
#  FORM MODIFICA PAZIENTE
# ══════════════════════════════════════════════════════════════════════

def render_form_modifica_paziente(conn, paz_id: int, rec: dict) -> None:
    """Form modifica paziente esistente con le stesse migliorie."""

    st.subheader(f"✏️ Modifica — {rec.get('Cognome','')} {rec.get('Nome','')}")

    # ── CAP lookup ────────────────────────────────────────────────────
    key_cap = f"cap_lookup_{paz_id}"
    if key_cap not in st.session_state:
        st.session_state[key_cap] = {}

    c1, c2 = st.columns(2)
    with c1:
        cognome = st.text_input("Cognome *", rec.get("Cognome",""), key=f"mp_cog_{paz_id}")
    with c2:
        nome = st.text_input("Nome *", rec.get("Nome",""), key=f"mp_nom_{paz_id}")

    c3, c4, c5 = st.columns([2, 1, 2])
    with c3:
        data_str = st.text_input(
            "Data di nascita",
            value=_fmt_data_it(rec.get("Data_Nascita","")),
            key=f"mp_dat_{paz_id}",
            placeholder="GG/MM/AAAA"
        )
        if data_str:
            d = _parse_data(data_str)
            if d:
                anni = (datetime.date.today() - d).days // 365
                st.caption(f"✅ {d.strftime('%d %b %Y')} — {anni} anni")
            else:
                st.caption("⚠️ Formato non valido")
    with c4:
        sesso = st.selectbox("Sesso",
                             ["","M","F","Altro"],
                             index=["","M","F","Altro"].index(rec.get("Sesso","") or ""),
                             key=f"mp_ses_{paz_id}")
    with c5:
        cf = st.text_input("Codice fiscale",
                           rec.get("Codice_Fiscale","") or "",
                           key=f"mp_cf_{paz_id}").upper()

    indirizzo = st.text_input("Indirizzo",
                              rec.get("Indirizzo","") or "",
                              key=f"mp_ind_{paz_id}")

    c6, c7, c8 = st.columns([1, 2, 1])
    with c6:
        cap_val = st.text_input("CAP",
                                rec.get("CAP","") or "",
                                key=f"mp_cap_{paz_id}",
                                max_chars=5)
        if len(cap_val) == 5 and cap_val.isdigit():
            last_key = f"_last_cap_{paz_id}"
            if st.session_state.get(last_key) != cap_val:
                st.session_state[last_key] = cap_val
                result = _cap_lookup(cap_val)
                if result:
                    st.session_state[key_cap] = result

    lookup = st.session_state.get(key_cap, {})
    with c7:
        citta = st.text_input("Città",
                              lookup.get("citta","") or rec.get("Citta","") or "",
                              key=f"mp_cit_{paz_id}")
    with c8:
        provincia = st.text_input("Provincia",
                                  lookup.get("provincia","") or rec.get("Provincia","") or "",
                                  key=f"mp_prv_{paz_id}",
                                  max_chars=2).upper()

    c9, c10 = st.columns(2)
    with c9:
        telefono = st.text_input("Telefono", rec.get("Telefono","") or "", key=f"mp_tel_{paz_id}")
    with c10:
        email = st.text_input("Email", rec.get("Email","") or "", key=f"mp_eml_{paz_id}")

    st.markdown("---")

    if st.button("💾 Salva modifiche", type="primary", key=f"mp_salva_{paz_id}"):
        data_iso = None
        if data_str.strip():
            d = _parse_data(data_str.strip())
            if not d:
                st.error("Data non valida — usa GG/MM/AAAA.")
                return
            data_iso = d.isoformat()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE Pazienti SET
                  Cognome=%s, Nome=%s, Data_Nascita=%s, Sesso=%s,
                  Telefono=%s, Email=%s, Indirizzo=%s,
                  CAP=%s, Citta=%s, Provincia=%s, Codice_Fiscale=%s
                WHERE id=%s
            """, (
                cognome.strip(), nome.strip(), data_iso, sesso,
                telefono.strip(), email.strip(), indirizzo.strip(),
                cap_val.strip(), citta.strip(),
                provincia.strip().upper(),
                cf.strip().upper() or None,
                paz_id,
            ))
            conn.commit()
            st.success("✅ Modifiche salvate.")
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            st.error(f"Errore: {e}")

    # ── Link privacy ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔗 Link firma privacy")
    if st.button("Genera link firma privacy", key=f"mp_priv_{paz_id}"):
        tipo = "Minore" if (rec.get("Tutore_Nome") or "") else "Adulto"
        _genera_link_privacy(conn, paz_id, tipo,
                             email, "",
                             cognome, nome)


# ══════════════════════════════════════════════════════════════════════
#  LISTA PAZIENTI + ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def render_anagrafica(conn) -> None:
    """Entry point — lista pazienti + nuovo + modifica."""

    st.title("👥 Anagrafica Pazienti")

    tab_lista, tab_nuovo = st.tabs(["📋 Lista pazienti", "➕ Nuovo paziente"])

    with tab_nuovo:
        render_form_nuovo_paziente(conn)

    with tab_lista:
        _render_lista(conn)


def _render_lista(conn) -> None:
    """Lista pazienti con ricerca e modifica inline."""

    # Barra ricerca
    cerca = st.text_input("🔍 Cerca per cognome o nome",
                          placeholder="es. Rossi",
                          key="ana_cerca")

    try:
        cur = conn.cursor()
        if cerca:
            q = f"%{cerca.upper()}%"
            cur.execute(
                "SELECT id, Cognome, Nome, Data_Nascita, Telefono, Email, Stato_Paziente "
                "FROM Pazienti WHERE UPPER(Cognome) LIKE %s OR UPPER(Nome) LIKE %s "
                "ORDER BY Cognome, Nome LIMIT 100",
                (q, q)
            )
        else:
            cur.execute(
                "SELECT id, Cognome, Nome, Data_Nascita, Telefono, Email, Stato_Paziente "
                "FROM Pazienti WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' "
                "ORDER BY Cognome, Nome LIMIT 200"
            )
        rows = cur.fetchall() or []
    except Exception as e:
        st.error(f"Errore: {e}")
        return

    if not rows:
        st.info("Nessun paziente trovato.")
        return

    st.caption(f"{len(rows)} pazienti")

    for r in rows:
        if isinstance(r, dict):
            pid  = r.get("id")
            cog  = r.get("Cognome","")
            nom  = r.get("Nome","")
            dn   = r.get("Data_Nascita","")
            tel  = r.get("Telefono","") or ""
            eml  = r.get("Email","") or ""
            stato = r.get("Stato_Paziente","ATTIVO")
        else:
            pid, cog, nom, dn, tel, eml = r[0],r[1],r[2],r[3],r[4],r[5]
            stato = r[6] if len(r) > 6 else "ATTIVO"

        # Età
        eta_str = ""
        if dn:
            try:
                import datetime as _dt
                anni = (_dt.date.today() - _dt.date.fromisoformat(str(dn)[:10])).days // 365
                eta_str = f" · {anni} anni"
            except Exception:
                pass

        dn_fmt = _fmt_data_it(dn)
        label  = f"**{cog} {nom}**{eta_str} &nbsp;·&nbsp; {dn_fmt}"

        with st.expander(f"{cog} {nom}{eta_str}", expanded=False):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"📅 {dn_fmt}&nbsp;&nbsp; 📞 {tel}&nbsp;&nbsp; 📧 {eml}")
            with col_b:
                if st.button("✏️ Modifica", key=f"btn_mod_{pid}"):
                    st.session_state[f"modifica_paz_{pid}"] = True

            if st.session_state.get(f"modifica_paz_{pid}"):
                try:
                    cur2 = conn.cursor()
                    cur2.execute("SELECT * FROM Pazienti WHERE id=%s", (pid,))
                    rec = cur2.fetchone()
                    if rec:
                        if not isinstance(rec, dict):
                            cols = [d[0] for d in cur2.description]
                            rec  = dict(zip(cols, rec))
                        render_form_modifica_paziente(conn, pid, rec)
                except Exception as e:
                    st.error(f"Errore caricamento: {e}")
