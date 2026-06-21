# -*- coding: utf-8 -*-
"""
modules/ui_screening_link.py
────────────────────────────
Apre lo SCREENING uditivo (questionari) già impostato sul paziente attivo:
costruisce il link con nome + data di nascita, così il test salta la scelta
Bambino/Adulto e precompila i dati (come il lettore MAPS legge l'URL).

Segreti in .streamlit/secrets.toml:
    [pnev_wp]
    screening_url        = "https://www.pnev.it/wp-content/uploads/screening_pnev.html"
    # opzionale, il test in cuffia:
    screening_cuffie_url = "https://www.pnev.it/wp-content/uploads/screening_cuffie_pnev.html"
"""

import datetime
import urllib.parse
import streamlit as st


def _iso_nascita(valore):
    """Riduce la data di nascita a 'YYYY-MM-DD' qualunque sia il tipo in anagrafica."""
    if valore is None:
        return ""
    if isinstance(valore, (datetime.date, datetime.datetime)):
        return valore.strftime("%Y-%m-%d")
    s = str(valore).strip()
    # prende i primi 10 caratteri se è tipo '2015-09-23 00:00:00'
    return s[:10] if len(s) >= 10 and s[4] == "-" and s[7] == "-" else s


def _link(base, nome, nascita):
    q = {}
    if nascita:
        q["nascita"] = nascita
    if nome:
        q["nome"] = nome
    sep = "&" if "?" in base else "?"
    return base + (sep + urllib.parse.urlencode(q) if q else "")


def render_screening_link(conn):
    st.subheader("🎧 Screening uditivo")
    st.caption("Apre lo screening già impostato sul paziente attivo "
               "(salta la scelta Bambino/Adulto e precompila i dati).")

    from .paziente_attivo import header_paziente_attivo
    paz_id = header_paziente_attivo(conn)
    if not paz_id:
        st.info("Seleziona prima un paziente (banner in alto: «Cambia paziente»).")
        return

    rec = st.session_state.get("paziente_attivo_record", {}) or {}
    nome = (rec.get("nome") or "").strip()
    cognome = (rec.get("cognome") or "").strip()
    nome_completo = (f"{nome} {cognome}").strip()
    nascita = _iso_nascita(rec.get("data_nascita") or rec.get("nascita"))

    cfg = st.secrets.get("pnev_wp", {})
    base_q = (cfg.get("screening_url") or "").strip()
    base_c = (cfg.get("screening_cuffie_url") or "").strip()

    if not base_q:
        st.warning("Manca l'indirizzo dello screening. Aggiungi in `.streamlit/secrets.toml`:\n\n"
                   '[pnev_wp]\nscreening_url = '
                   '"https://www.pnev.it/wp-content/uploads/screening_pnev.html"')
        return

    # riepilogo dati che verranno passati
    eta_txt = ""
    if nascita:
        try:
            d = datetime.date.fromisoformat(nascita)
            oggi = datetime.date.today()
            anni = oggi.year - d.year - ((oggi.month, oggi.day) < (d.month, d.day))
            gruppo = "adulti" if anni >= 14 else "bambini"
            eta_txt = f" · {anni} anni → strumenti **{gruppo}**"
        except Exception:
            pass

    st.markdown(f"**Paziente:** {nome_completo or '—'}{eta_txt}", unsafe_allow_html=True)
    if not nascita:
        st.caption("⚠️ Data di nascita assente in anagrafica: il test si aprirà sulla scelta "
                   "manuale Bambino/Adulto (ma il nome verrà comunque precompilato).")

    # ── questionari ──────────────────────────────────────────────
    url_q = _link(base_q, nome_completo, nascita)
    st.markdown(
        f'<a href="{url_q}" target="_blank" rel="noopener" '
        f'style="display:inline-block;background:#1D6B44;color:#fff;text-decoration:none;'
        f'padding:10px 18px;border-radius:10px;font-weight:600;margin:6px 0;">'
        f'🧠 Apri i questionari di screening</a>', unsafe_allow_html=True)
    with st.expander("Link diretto (da copiare)"):
        st.code(url_q, language=None)

    # ── test in cuffia (se configurato) ──────────────────────────
    if base_c:
        url_c = _link(base_c, nome_completo, nascita)
        st.markdown(
            f'<a href="{url_c}" target="_blank" rel="noopener" '
            f'style="display:inline-block;background:#fff;color:#1D6B44;border:1px solid #1D6B44;'
            f'text-decoration:none;padding:10px 18px;border-radius:10px;font-weight:600;margin:6px 0;">'
            f'🎧 Apri il test in cuffia</a>', unsafe_allow_html=True)
        with st.expander("Link diretto test in cuffia (da copiare)"):
            st.code(url_c, language=None)

    st.divider()
    st.caption("Il risultato dello screening, per ora, si legge a schermo e si copia/stampa. "
               "Il salvataggio automatico dell'esito nell'anagrafica sarà un passo successivo.")
