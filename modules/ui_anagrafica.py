# -*- coding: utf-8 -*-
"""Anagrafica Pazienti - The Organism.
Layout: lista sempre visibile a sinistra, form a destra.
Salva e aggiorna immediatamente senza perdere la posizione.
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
        return f"{anni} anni"
    except: return ""

def _cap_lookup(cap: str) -> dict:
    cap = cap.strip()
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
                "SELECT id, cognome, nome, data_nascita, telefono, email, "
                "COALESCE(stato_paziente,'ATTIVO') as stato_paziente "
                "FROM pazienti WHERE UPPER(cognome) LIKE %s OR UPPER(nome) LIKE %s "
                "OR CAST(id AS TEXT) = %s "
                "ORDER BY cognome, nome LIMIT 100", (q, q, cerca.strip())
            )
        else:
            cur.execute(
                "SELECT id, cognome, nome, data_nascita, telefono, email, "
                "COALESCE(stato_paziente,'ATTIVO') as stato_paziente "
                "FROM pazienti ORDER BY cognome, nome LIMIT 300"
            )
        rows = cur.fetchall() or []
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append(r)
            else:
                cols = [d[0] for d in cur.description]
                result.append(dict(zip(cols, r)))
        return result
    except Exception as e:
        st.error(f"Errore lista pazienti: {e}")
        return []

def _salva_nuovo(conn, d: dict) -> int | None:
    try:
        cur = conn.cursor()
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data non valida. Usa GG/MM/AAAA")
                return None
            data_iso = parsed.isoformat()

        cur.execute("""
            INSERT INTO pazienti
            (cognome, nome, data_nascita, sesso, telefono, email,
             indirizzo, cap, citta, provincia, codice_fiscale, stato_paziente)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ATTIVO')
            RETURNING id
        """, (
            d["cognome"].strip().upper(),
            d["nome"].strip().title(),
            data_iso,
            d["sesso"],
            d["tel"].strip(),
            d["email"].strip().lower(),
            d["indirizzo"].strip(),
            d["cap"].strip(),
            d["citta"].strip().title(),
            d["prov"].strip().upper(),
            d["cf"].strip().upper() or None,
        ))
        row = cur.fetchone()
        paz_id = int(row["id"] if isinstance(row, dict) else row[0])

        # Salva consenso privacy minimo
        try:
            cur.execute("""
                INSERT INTO consensi_privacy
                (paziente_id, tipo_soggetto, consenso_trattamento, Data_Ora)
                VALUES (%s, %s, 1, NOW())
            """, (paz_id, d.get("tipo_privacy","adulto")))
        except Exception:
            pass

        conn.commit()
        return paz_id
    except Exception as e:
        try: conn.rollback()
        except: pass
        st.error(f"Errore salvataggio: {e}")
        return None

def _salva_modifica(conn, paz_id: int, d: dict) -> bool:
    try:
        cur = conn.cursor()
        data_iso = None
        if d["data_str"].strip():
            parsed = _parse_data(d["data_str"])
            if not parsed:
                st.error("Data non valida. Usa GG/MM/AAAA")
                return False
            data_iso = parsed.isoformat()

        cur.execute("""
            UPDATE pazienti SET
                cognome=%s, nome=%s, data_nascita=%s, sesso=%s,
                telefono=%s, email=%s, indirizzo=%s, cap=%s,
                citta=%s, provincia=%s, codice_fiscale=%s,
                stato_paziente=%s
            WHERE id=%s
        """, (
            d["cognome"].strip().upper(),
            d["nome"].strip().title(),
            data_iso, d["sesso"],
            d["tel"].strip(), d["email"].strip().lower(),
            d["indirizzo"].strip(), d["cap"].strip(),
            d["citta"].strip().title(), d["prov"].strip().upper(),
            d["cf"].strip().upper() or None,
            d["stato"],
            paz_id,
        ))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except: pass
        st.error(f"Errore modifica: {e}")
        return False


def _form_paziente(conn, key_prefix: str, rec: dict | None = None) -> dict | None:
    """Form unificato nuovo/modifica. Ritorna dict dati o None se non salvato."""
    is_nuovo = rec is None
    r = rec or {}

    st.markdown("##### Dati anagrafici")
    c1, c2 = st.columns(2)
    with c1:
        cognome = st.text_input("Cognome *", value=r.get(cognome,""),
                                 key=f"{key_prefix}_cog")
    with c2:
        nome = st.text_input("Nome *", value=r.get(nome,""),
                              key=f"{key_prefix}_nom")

    c3, c4, c5 = st.columns(3)
    with c3:
        dn_val = _fmt_dn(r.get(data_nascita,""))
        data_str = st.text_input("Data nascita (GG/MM/AAAA)",
                                  value=dn_val,
                                  key=f"{key_prefix}_dn",
                                  placeholder="es. 15/03/1990")
    with c4:
        sesso = st.selectbox(sesso, ["M","F","Altro"],
                              index=["M","F","Altro"].index(r.get(sesso,"M"))
                              if r.get(sesso) in ["M","F","Altro"] else 0,
                              key=f"{key_prefix}_sex")
    with c5:
        cf = st.text_input("Codice fiscale",
                            value=r.get(codice_fiscale,"") or "",
                            key=f"{key_prefix}_cf")

    st.markdown("##### Contatti")
    c6, c7 = st.columns(2)
    with c6:
        tel = st.text_input(telefono, value=r.get(telefono,"") or "",
                             key=f"{key_prefix}_tel")
    with c7:
        email = st.text_input(email, value=r.get(email,"") or "",
                               key=f"{key_prefix}_email")

    st.markdown("##### Indirizzo")
    indirizzo = st.text_input("Via / Indirizzo",
                               value=r.get(indirizzo,"") or "",
                               key=f"{key_prefix}_ind")

    c8, c9, c10 = st.columns([1,2,1])
    with c8:
        cap_key = f"{key_prefix}_cap"
        cap = st.text_input(cap, value=r.get(cap,"") or "",
                             key=cap_key, max_chars=5)
        # Auto-lookup CAP
        if cap and len(cap)==5 and cap.isdigit():
            last_cap = st.session_state.get(f"{key_prefix}_last_cap","")
            if cap != last_cap:
                st.session_state[f"{key_prefix}_last_cap"] = cap
                lookup = _cap_lookup(cap)
                if lookup:
                    st.session_state[f"{key_prefix}_citta_auto"] = lookup.get("citta","")
                    st.session_state[f"{key_prefix}_prov_auto"]  = lookup.get("provincia","")

    with c9:
        citta_default = st.session_state.get(f"{key_prefix}_citta_auto",
                                              r.get(citta,"") or "")
        citta = st.text_input("Città", value=citta_default,
                               key=f"{key_prefix}_citta")
    with c10:
        prov_default = st.session_state.get(f"{key_prefix}_prov_auto",
                                             r.get(provincia,"") or "")
        prov = st.text_input("Prov.", value=prov_default, max_chars=2,
                              key=f"{key_prefix}_prov")

    if not is_nuovo:
        st.markdown("##### Stato")
        stato = st.selectbox("Stato paziente",
                              ["ATTIVO","DIMESSO","SOSPESO","ARCHIVIATO"],
                              index=["ATTIVO","DIMESSO","SOSPESO","ARCHIVIATO"].index(
                                  r.get(stato_paziente,"ATTIVO")
                                  if r.get(stato_paziente) in
                                  ["ATTIVO","DIMESSO","SOSPESO","ARCHIVIATO"]
                                  else "ATTIVO"),
                              key=f"{key_prefix}_stato")
    else:
        stato = "ATTIVO"
        st.markdown("##### Privacy")
        tipo_privacy = st.radio("Tipo soggetto",
                                 ["adulto","minore"],
                                 horizontal=True,
                                 key=f"{key_prefix}_priv")
        consenso = st.checkbox("Il paziente acconsente al trattamento dati *",
                                key=f"{key_prefix}_cons")

    # Bottone salva
    label_btn = "Salva nuovo paziente" if is_nuovo else "Salva modifiche"
    if st.button(label_btn, type="primary", key=f"{key_prefix}_salva"):
        if not cognome.strip() or not nome.strip():
            st.error("Cognome e Nome sono obbligatori.")
            return None
        if is_nuovo and not consenso:
            st.error("Il consenso privacy è obbligatorio.")
            return None

        return {
            "cognome": cognome, "nome": nome, "data_str": data_str,
            "sesso": sesso, "cf": cf, "tel": tel, "email": email,
            "indirizzo": indirizzo, "cap": cap, "citta": citta, "prov": prov,
            "stato": stato,
            "tipo_privacy": locals().get("tipo_privacy","adulto"),
        }
    return None


def render_anagrafica(conn) -> None:
    st.subheader("Anagrafica Pazienti")

    # Stato: quale paziente è selezionato / modalità
    if "ana_paz_sel" not in st.session_state:
        st.session_state["ana_paz_sel"] = None
    if "ana_modo" not in st.session_state:
        st.session_state["ana_modo"] = "lista"  # lista | nuovo | modifica

    # ── Layout: colonna sinistra lista, destra form ───────────────────
    col_lista, col_form = st.columns([1, 2])

    with col_lista:
        st.markdown("**Pazienti**")
        cerca = st.text_input("Cerca", placeholder="Cognome o nome...",
                               key="ana_cerca", label_visibility="collapsed")

        if st.button("➕ Nuovo paziente", key="ana_btn_nuovo",
                     use_container_width=True):
            st.session_state["ana_modo"] = "nuovo"
            st.session_state["ana_paz_sel"] = None

        pazienti = _carica_pazienti(conn, cerca)

        if not pazienti:
            st.info("Nessun paziente trovato.")
        else:
            st.caption(f"{len(pazienti)} risultati")
            for p in pazienti:
                pid = p.get("id")
                cog = p.get(cognome,"")
                nom = p.get(nome,"")
                eta = _eta(p.get(data_nascita))
                stato = p.get(stato_paziente,"ATTIVO") or "ATTIVO"

                # Badge stato
                badge = "🟢" if stato=="ATTIVO" else ("🟡" if stato=="SOSPESO" else "⚫")

                # Bottone paziente
                label = f"{badge} {cog} {nom}"
                if eta: label += f" · {eta}"

                is_sel = st.session_state.get("ana_paz_sel") == pid
                btn_type = "primary" if is_sel else "secondary"

                if st.button(label, key=f"ana_sel_{pid}",
                             use_container_width=True,
                             type=btn_type):
                    st.session_state["ana_paz_sel"] = pid
                    st.session_state["ana_modo"] = "modifica"

    with col_form:
        modo = st.session_state.get("ana_modo","lista")

        if modo == "nuovo":
            st.markdown("#### Nuovo paziente")
            dati = _form_paziente(conn, "np")
            if dati is not None:
                paz_id = _salva_nuovo(conn, dati)
                if paz_id:
                    st.success(f"✅ {dati['cognome']} {dati['nome']} salvato (ID: {paz_id})")
                    st.session_state["ana_paz_sel"] = paz_id
                    st.session_state["ana_modo"] = "modifica"
                    st.session_state["ana_cerca"] = ""
                    # Pulisci cache CAP e form
                    for k in list(st.session_state.keys()):
                        if k.startswith("np_") or k.startswith("ana_"):
                            if k not in ("ana_paz_sel","ana_modo","ana_cerca"):
                                del st.session_state[k]
                    import time; time.sleep(0.3)  # lascia tempo al commit Neon
                    st.rerun()

        elif modo == "modifica":
            paz_id = st.session_state.get("ana_paz_sel")
            if paz_id:
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM pazienti WHERE id=%s", (paz_id,))
                    row = cur.fetchone()
                    if row:
                        if not isinstance(row, dict):
                            cols = [d[0] for d in cur.description]
                            row = dict(zip(cols, row))

                        cog = row.get(cognome,"")
                        nom = row.get(nome,"")
                        dn  = _fmt_dn(row.get(data_nascita))
                        tel = row.get(telefono,"") or ""
                        eta = _eta(row.get(data_nascita))

                        st.markdown(f"#### {cog} {nom}")
                        if dn: st.caption(f"Nato/a il {dn} · {eta}")
                        if tel: st.caption(f"Tel: {tel}")

                        st.markdown("---")

                        dati = _form_paziente(conn, f"mp_{paz_id}", row)
                        if dati is not None:
                            ok = _salva_modifica(conn, paz_id, dati)
                            if ok:
                                st.success("✅ Modifiche salvate.")
                                st.rerun()

                        # Bottone elimina/archivia
                        st.markdown("---")
                        if st.button("🗃️ Archivia paziente",
                                     key=f"ana_arch_{paz_id}"):
                            try:
                                cur.execute(
                                    "UPDATE pazienti SET stato_paziente='ARCHIVIATO' WHERE id=%s",
                                    (paz_id,))
                                conn.commit()
                                st.success("Paziente archiviato.")
                                st.session_state["ana_paz_sel"] = None
                                st.session_state["ana_modo"] = "lista"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Errore: {e}")
                    else:
                        st.warning("Paziente non trovato.")
                except Exception as e:
                    st.error(f"Errore caricamento: {e}")
            else:
                st.info("Seleziona un paziente dalla lista oppure crea un nuovo paziente.")

        else:
            # Schermata iniziale
            n_paz = len(_carica_pazienti(conn))
            st.markdown(f"""
<div style="padding:2rem;text-align:center;color:var(--color-text-secondary)">
    <div style="font-size:3rem;margin-bottom:1rem">👥</div>
    <div style="font-size:1.1rem;font-weight:500;margin-bottom:0.5rem">{n_paz} pazienti nel database</div>
    <div style="font-size:0.9rem">Cerca un paziente nella lista oppure creane uno nuovo</div>
</div>
""", unsafe_allow_html=True)
