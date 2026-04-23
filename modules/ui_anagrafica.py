# -*- coding: utf-8 -*-
"""Anagrafica Pazienti - The Organism.
Layout a due colonne fisse: lista a sinistra, form a destra.
Il form è sempre visibile — niente scroll.
"""
from __future__ import annotations
import datetime
import streamlit as st


def _parse_data(s: str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None

def _fmt_dn(iso) -> str:
    if not iso: return ""
    try: return datetime.date.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except: return str(iso)[:10]

def _eta(dn) -> str:
    try:
        anni = (datetime.date.today() - datetime.date.fromisoformat(str(dn)[:10])).days // 365
        return f"{anni}a"
    except: return ""

def _cap_lookup(cap: str) -> dict:
    if len(cap) != 5 or not cap.isdigit(): return {}
    try:
        import requests
        r = requests.get(f"https://api.zippopotam.us/it/{cap}", timeout=3)
        if r.status_code == 200:
            places = r.json().get("places", [])
            if places:
                return {
                    "citta": places[0].get("place name","").title(),
                    "provincia": places[0].get("state abbreviation","").upper()
                }
    except: pass
    return {}

def _carica_pazienti(conn, cerca=""):
    try:
        cur = conn.cursor()
        if cerca.strip():
            q = f"%{cerca.strip().upper()}%"
            cur.execute(
                "SELECT id, cognome, nome, data_nascita, telefono, stato_paziente "
                "FROM pazienti WHERE UPPER(cognome) LIKE %s OR UPPER(nome) LIKE %s "
                "OR CAST(id AS TEXT) = %s "
                "ORDER BY cognome, nome LIMIT 100", (q, q, cerca.strip())
            )
        else:
            cur.execute(
                "SELECT id, cognome, nome, data_nascita, telefono, stato_paziente "
                "FROM pazienti ORDER BY cognome, nome LIMIT 300"
            )
        rows = cur.fetchall() or []
        result = []
        for r in rows:
            result.append(r if isinstance(r,dict) else
                          dict(zip([d[0] for d in cur.description], r)))
        return result
    except Exception as e:
        st.error(f"Errore lista: {e}")
        return []

def _carica_paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM pazienti WHERE id=%s", (paz_id,))
        row = cur.fetchone()
        if not row: return None
        if not isinstance(row, dict):
            row = dict(zip([d[0] for d in cur.description], row))
        return row
    except: return None

def _salva_nuovo(conn, d) -> int | None:
    try:
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data non valida. Usa GG/MM/AAAA")
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
        paz_id = int(row["id"] if isinstance(row,dict) else row[0])
        try:
            cur.execute("""
                INSERT INTO consensi_privacy
                (paziente_id, tipo_soggetto, consenso_trattamento, Data_Ora)
                VALUES (%s,%s,1,NOW())
            """, (paz_id, d.get("tipo_privacy","adulto")))
        except: pass
        conn.commit()
        return paz_id
    except Exception as e:
        try: conn.rollback()
        except: pass
        st.error(f"Errore: {e}")
        return None

def _salva_modifica(conn, paz_id, d) -> bool:
    try:
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data non valida. Usa GG/MM/AAAA")
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
        try: conn.rollback()
        except: pass
        st.error(f"Errore: {e}")
        return False

def _form_fields(key, r=None):
    """Campi del form. r=None per nuovo, r=dict per modifica."""
    is_nuovo = r is None
    r = r or {}

    c1, c2 = st.columns(2)
    with c1:
        cognome = st.text_input("Cognome *", value=r.get("cognome",""),
                                 key=f"{key}_cog")
    with c2:
        nome = st.text_input("Nome *", value=r.get("nome",""),
                              key=f"{key}_nom")

    c3, c4, c5 = st.columns([2,1,1])
    with c3:
        data_str = st.text_input("Data nascita",
                                  value=_fmt_dn(r.get("data_nascita","")),
                                  key=f"{key}_dn",
                                  placeholder="GG/MM/AAAA")
    with c4:
        sesso_opts = ["M","F","Altro"]
        sesso = st.selectbox("Sesso",
                              sesso_opts,
                              index=sesso_opts.index(r.get("sesso","M"))
                              if r.get("sesso") in sesso_opts else 0,
                              key=f"{key}_sex")
    with c5:
        cf = st.text_input("Cod. Fiscale",
                            value=r.get("codice_fiscale","") or "",
                            key=f"{key}_cf")

    c6, c7 = st.columns(2)
    with c6:
        tel = st.text_input("Telefono",
                             value=r.get("telefono","") or "",
                             key=f"{key}_tel")
    with c7:
        email = st.text_input("Email",
                               value=r.get("email","") or "",
                               key=f"{key}_email")

    indirizzo = st.text_input("Indirizzo",
                               value=r.get("indirizzo","") or "",
                               key=f"{key}_ind")

    c8, c9, c10 = st.columns([1,2,1])
    with c8:
        cap = st.text_input("CAP", value=r.get("cap","") or "",
                             key=f"{key}_cap", max_chars=5)
        if cap and len(cap)==5 and cap.isdigit():
            if cap != st.session_state.get(f"{key}_last_cap",""):
                st.session_state[f"{key}_last_cap"] = cap
                lk = _cap_lookup(cap)
                if lk:
                    st.session_state[f"{key}_citta_v"] = lk["citta"]
                    st.session_state[f"{key}_prov_v"]  = lk["provincia"]
    with c9:
        citta = st.text_input("Città",
                               value=st.session_state.get(f"{key}_citta_v",
                                                           r.get("citta","") or ""),
                               key=f"{key}_citta")
    with c10:
        prov = st.text_input("Prov.",
                              value=st.session_state.get(f"{key}_prov_v",
                                                         r.get("provincia","") or ""),
                              max_chars=2, key=f"{key}_prov")

    if not is_nuovo:
        stati = ["ATTIVO","DIMESSO","SOSPESO","ARCHIVIATO"]
        stato = st.selectbox("Stato",
                              stati,
                              index=stati.index(r.get("stato_paziente","ATTIVO"))
                              if r.get("stato_paziente") in stati else 0,
                              key=f"{key}_stato")
    else:
        stato = "ATTIVO"
        c11, c12 = st.columns(2)
        with c11:
            tipo_privacy = st.selectbox("Tipo soggetto",
                                         ["adulto","minore"],
                                         key=f"{key}_priv")
        with c12:
            consenso = st.checkbox("Consenso dati *",
                                    key=f"{key}_cons")

    return {
        "cognome": cognome, "nome": nome, "data_str": data_str,
        "sesso": sesso, "cf": cf, "tel": tel, "email": email,
        "indirizzo": indirizzo, "cap": cap, "citta": citta, "prov": prov,
        "stato": stato,
        "tipo_privacy": locals().get("tipo_privacy","adulto"),
        "_consenso": locals().get("consenso", True),
        "_is_nuovo": is_nuovo,
    }


def render_anagrafica(conn) -> None:
    # Stato navigazione
    if "ana_sel" not in st.session_state:
        st.session_state["ana_sel"] = None  # paz_id selezionato
    if "ana_nuovo" not in st.session_state:
        st.session_state["ana_nuovo"] = False

    # ── Header ────────────────────────────────────────────────────────
    h1, h2 = st.columns([3,1])
    with h1:
        st.subheader("Anagrafica Pazienti")
    with h2:
        if st.button("➕ Nuovo paziente", type="primary",
                     key="ana_btn_nuovo", use_container_width=True):
            st.session_state["ana_nuovo"] = True
            st.session_state["ana_sel"] = None

    # ── Layout principale ─────────────────────────────────────────────
    col_l, col_r = st.columns([1, 2], gap="medium")

    # ── COLONNA SINISTRA: lista ───────────────────────────────────────
    with col_l:
        cerca = st.text_input("🔍 Cerca", placeholder="Nome, cognome o ID...",
                               key="ana_cerca", label_visibility="collapsed")
        pazienti = _carica_pazienti(conn, cerca)
        st.caption(f"{len(pazienti)} pazienti")

        for p in pazienti:
            pid    = p.get("id")
            cog    = p.get("cognome","") or ""
            nom    = p.get("nome","") or ""
            dn     = p.get("data_nascita","")
            tel    = p.get("telefono","") or ""
            stato  = p.get("stato_paziente","ATTIVO") or "ATTIVO"

            eta    = _eta(dn)
            badge  = "🟢" if stato=="ATTIVO" else ("🟡" if stato=="SOSPESO" else "⚫")
            is_sel = st.session_state.get("ana_sel") == pid

            # Riga paziente cliccabile
            st.markdown(
                f'<div style="padding:6px 10px;margin:2px 0;border-radius:8px;'
                f'cursor:pointer;'
                f'background:{"var(--color-background-info)" if is_sel else "var(--color-background-secondary)"};'
                f'border:{"1.5px solid var(--color-border-info)" if is_sel else "0.5px solid var(--color-border-tertiary)"}">'
                f'<div style="font-weight:500;font-size:13px">{badge} {cog} {nom}</div>'
                f'<div style="font-size:11px;color:var(--color-text-secondary)">'
                f'{_fmt_dn(dn)} {("· "+eta) if eta else ""}'
                f'{(" · "+tel) if tel else ""}</div></div>',
                unsafe_allow_html=True
            )
            if st.button("Apri", key=f"sel_{pid}",
                         use_container_width=True,
                         label_visibility="collapsed"):
                st.session_state["ana_sel"] = pid
                st.session_state["ana_nuovo"] = False
                # Pulisci valori CAP del form precedente
                for k in list(st.session_state.keys()):
                    if k.startswith("mp_") and ("_citta_v" in k or "_prov_v" in k or "_last_cap" in k):
                        del st.session_state[k]
                st.rerun()

    # ── COLONNA DESTRA: form ──────────────────────────────────────────
    with col_r:

        # ── NUOVO PAZIENTE ────────────────────────────────────────────
        if st.session_state.get("ana_nuovo"):
            st.markdown("#### Nuovo paziente")
            st.markdown("---")
            dati = _form_fields("np")

            col_s1, col_s2 = st.columns([1,1])
            with col_s1:
                salva = st.button("💾 Salva", type="primary",
                                   key="np_salva_btn",
                                   use_container_width=True)
            with col_s2:
                if st.button("✕ Annulla", key="np_ann",
                              use_container_width=True):
                    st.session_state["ana_nuovo"] = False
                    st.rerun()

            if salva:
                if not dati["cognome"].strip() or not dati["nome"].strip():
                    st.error("Cognome e Nome sono obbligatori.")
                elif not dati["_consenso"]:
                    st.error("Il consenso privacy è obbligatorio.")
                else:
                    paz_id = _salva_nuovo(conn, dati)
                    if paz_id:
                        st.success(f"✅ {dati['cognome']} {dati['nome']} salvato")
                        st.session_state["ana_nuovo"] = False
                        st.session_state["ana_sel"] = paz_id
                        # Pulisci form
                        for k in list(st.session_state.keys()):
                            if k.startswith("np_"):
                                del st.session_state[k]
                        import time; time.sleep(0.3)
                        st.rerun()

        # ── MODIFICA PAZIENTE ─────────────────────────────────────────
        elif st.session_state.get("ana_sel"):
            paz_id = st.session_state["ana_sel"]
            rec = _carica_paziente(conn, paz_id)

            if not rec:
                st.warning("Paziente non trovato.")
            else:
                cog = rec.get("cognome","")
                nom = rec.get("nome","")
                dn  = rec.get("data_nascita","")
                eta = _eta(dn)

                st.markdown(f"#### {cog} {nom}")
                st.caption(f"ID: {paz_id} · {_fmt_dn(dn)} · {eta}")
                st.markdown("---")

                dati = _form_fields(f"mp_{paz_id}", rec)

                col_s1, col_s2, col_s3 = st.columns([2,1,1])
                with col_s1:
                    salva = st.button("💾 Salva modifiche", type="primary",
                                       key=f"mp_salva_{paz_id}",
                                       use_container_width=True)
                with col_s2:
                    if st.button("✕ Chiudi", key=f"mp_close_{paz_id}",
                                  use_container_width=True):
                        st.session_state["ana_sel"] = None
                        st.rerun()
                with col_s3:
                    if st.button("🗃️ Archivia", key=f"mp_arch_{paz_id}",
                                  use_container_width=True):
                        try:
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE pazienti SET stato_paziente='ARCHIVIATO' WHERE id=%s",
                                (paz_id,))
                            conn.commit()
                            st.success("Paziente archiviato.")
                            st.session_state["ana_sel"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore: {e}")

                if salva:
                    if not dati["cognome"].strip() or not dati["nome"].strip():
                        st.error("Cognome e Nome sono obbligatori.")
                    else:
                        ok = _salva_modifica(conn, paz_id, dati)
                        if ok:
                            st.success("✅ Modifiche salvate.")
                            import time; time.sleep(0.2)
                            st.rerun()

        # ── NESSUNA SELEZIONE ─────────────────────────────────────────
        else:
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM pazienti")
                row = cur.fetchone()
                n = int(row[0] if not isinstance(row,dict) else list(row.values())[0])
            except: n = 0

            st.markdown(
                f"""<div style="display:flex;flex-direction:column;align-items:center;
                justify-content:center;height:400px;color:var(--color-text-secondary)">
                <div style="font-size:3rem;margin-bottom:1rem">👥</div>
                <div style="font-size:1.2rem;font-weight:500;margin-bottom:0.5rem">
                {n} pazienti registrati</div>
                <div style="font-size:0.9rem">
                Seleziona un paziente dalla lista oppure creane uno nuovo</div>
                </div>""",
                unsafe_allow_html=True
            )
