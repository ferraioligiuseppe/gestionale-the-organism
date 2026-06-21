# -*- coding: utf-8 -*-
"""
modules/ui_trasferimento_pnev.py
────────────────────────────────
Trasferisce il PAZIENTE ATTIVO su pnev.it iscrivendolo a un corso MAPS.

Flusso (modalità C — la macchina prepara, l'umano conferma):
  1. legge i corsi VIVI da pnev.it (menu a tendina, niente ID fissi)
  2. "Verifica (prova)"  → chiama l'endpoint in dry-run, dice cosa farebbe
  3. "Conferma e trasferisci" → iscrive davvero e marca fa_maps=1 nel gestionale

Usa lo stesso filo PHP del sync:
  GET /wp-json/pnev/v1/enroll?key=...&email=...&course=...&name=...&dry=1
  GET /wp-json/pnev/v1/maps?key=...&list=courses

Segreti richiesti in .streamlit/secrets.toml:
    [pnev_wp]
    base_url = "https://www.pnev.it"
    maps_key = "la-stessa-chiave-del-php"
"""

import json
import urllib.request, urllib.parse, urllib.error
import streamlit as st


# ════════════════════════════════════════════════════════════════════
#  HTTP verso pnev.it  (stesso comportamento del sync)
# ════════════════════════════════════════════════════════════════════
def _http_get_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        corpo = ""
        try:
            corpo = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        if e.code == 403:
            raise RuntimeError("Chiave non valida o richiesta bloccata (403): "
                               "controlla 'maps_key' e il plugin di protezione su pnev.it.")
        if e.code == 404:
            raise RuntimeError("Endpoint non trovato (404): aggiorna il filo PHP su pnev.it "
                               "(serve la versione con la route /enroll).")
        raise RuntimeError(f"Errore HTTP {e.code} da pnev.it. {corpo}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Impossibile contattare pnev.it: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError("pnev.it ha risposto, ma non con dati validi "
                           "(probabile blocco di un plugin di protezione).")


def _base_key():
    cfg = st.secrets.get("pnev_wp", {})
    return cfg.get("base_url", "").rstrip("/"), cfg.get("maps_key", "")


def _fetch_corsi(base_url, key):
    url = f"{base_url}/wp-json/pnev/v1/maps?" + urllib.parse.urlencode({"key": key, "list": "courses"})
    data = _http_get_json(url)
    return data.get("courses", []) if isinstance(data, dict) else []


def _enroll(base_url, key, email, course, name, dry):
    q = {"key": key, "email": email, "course": int(course), "name": name or ""}
    if dry:
        q["dry"] = "1"
    url = f"{base_url}/wp-json/pnev/v1/enroll?" + urllib.parse.urlencode(q)
    return _http_get_json(url)


def _marca_trasferito(conn, paz_id):
    """Segna nel gestionale che il paziente è passato a pnev.it (fa_maps=1)."""
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pazienti SET fa_maps = 1 WHERE id = %s", (paz_id,))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ════════════════════════════════════════════════════════════════════
#  PAGINA
# ════════════════════════════════════════════════════════════════════
def render_trasferimento_pnev(conn):
    st.subheader("🚀 Trasferisci a pnev.it")
    st.caption("Iscrive il paziente attivo a un corso MAPS su pnev.it. "
               "La macchina prepara, l'iscrizione la confermi tu.")

    # paziente attivo (stesso banner del resto del gestionale)
    from .paziente_attivo import header_paziente_attivo
    paz_id = header_paziente_attivo(conn)
    if not paz_id:
        st.info("Seleziona prima un paziente (banner in alto: «Cambia paziente»).")
        return

    rec = st.session_state.get("paziente_attivo_record", {}) or {}
    email = (rec.get("email") or "").strip()
    nome = (rec.get("nome") or "").strip()
    cognome = (rec.get("cognome") or "").strip()
    nome_completo = (f"{nome} {cognome}").strip() or "Paziente"

    if not email:
        st.error("Questo paziente non ha un'email in anagrafica. "
                 "L'email è la chiave del trasferimento: aggiungila prima di procedere.")
        return

    base_url, key = _base_key()
    if not (base_url and key):
        st.warning("Configurazione mancante. Aggiungi in `.streamlit/secrets.toml`:\n\n"
                   '[pnev_wp]\nbase_url = "https://www.pnev.it"\nmaps_key = "la-stessa-chiave-del-php"')
        return

    st.markdown(f"**Paziente:** {nome_completo} &nbsp;·&nbsp; **email:** `{email}`",
                unsafe_allow_html=True)

    # ── corsi vivi da pnev.it ────────────────────────────────────────
    if st.button("🔄 Carica i corsi da pnev.it") or "tp_corsi" not in st.session_state:
        try:
            st.session_state["tp_corsi"] = _fetch_corsi(base_url, key)
        except Exception as e:
            st.error(f"Non riesco a leggere i corsi: {e}")
            return

    corsi = st.session_state.get("tp_corsi", [])
    if not corsi:
        st.info("Nessun corso trovato su pnev.it. Premi «Carica i corsi da pnev.it».")
        return

    opzioni = {f"{c.get('post_title','(senza nome)')}  ·  id {c.get('ID')}": int(c.get("ID"))
               for c in corsi if str(c.get("ID", "")).strip().isdigit()}
    if not opzioni:
        st.info("La lista corsi è arrivata vuota o senza ID validi.")
        return

    scelta = st.selectbox("Corso a cui iscrivere il paziente", list(opzioni.keys()))
    course_id = opzioni[scelta]

    col1, col2 = st.columns(2)

    # ── VERIFICA (dry-run) ───────────────────────────────────────────
    with col1:
        if st.button("🔍 Verifica (prova)", use_container_width=True):
            try:
                r = _enroll(base_url, key, email, course_id, nome_completo, dry=True)
                az = r.get("azione", "—")
                if r.get("already_enrolled"):
                    st.info(f"Già iscritto a questo corso. Azione: **{az}**.")
                else:
                    st.success(f"Prova ok — azione prevista: **{az}**.")
                with st.expander("Dettagli prova"):
                    st.json(r)
                st.session_state["tp_verificato"] = (email, course_id)
            except Exception as e:
                st.error(f"Verifica fallita: {e}")

    # ── CONFERMA (scrive davvero) ────────────────────────────────────
    with col2:
        pronto = st.session_state.get("tp_verificato") == (email, course_id)
        conferma = st.checkbox("Confermo l'iscrizione di questo paziente al corso selezionato",
                               value=False, disabled=not pronto,
                               help="Fai prima «Verifica (prova)» per abilitare la conferma.")
        if st.button("✅ Conferma e trasferisci", use_container_width=True,
                     disabled=not (pronto and conferma)):
            try:
                r = _enroll(base_url, key, email, course_id, nome_completo, dry=False)
                stato = r.get("enrolled")
                if stato == "new":
                    st.success(f"🎉 Trasferito! {nome_completo} è ora iscritto al corso "
                               f"(id {course_id}) su pnev.it."
                               + ("  Nuovo utente creato." if r.get("created") else ""))
                elif stato == "already":
                    st.info(f"Era già iscritto a questo corso (id {course_id}). Nessun doppione.")
                else:
                    st.warning(f"Risposta inattesa da pnev.it: {r}")
                if _marca_trasferito(conn, paz_id):
                    st.caption("Nel gestionale: paziente marcato come iscritto MAPS (fa_maps = 1).")
                with st.expander("Dettagli risposta"):
                    st.json(r)
                st.session_state.pop("tp_verificato", None)
            except Exception as e:
                st.error(f"Trasferimento fallito: {e}")

    st.divider()
    st.caption("Nota: l'iscrizione è idempotente (riaprendola non crea doppioni). "
               "La proposta automatica del corso giusto in base alla curva si potrà "
               "aggiungere più avanti, quando i dati dello screening entreranno nel gestionale.")
