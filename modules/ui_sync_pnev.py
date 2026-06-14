# -*- coding: utf-8 -*-
"""Sincronizzazione pazienti pnev.it ↔ gestionale — The Organism.

Legge gli utenti WordPress di pnev.it tramite l'API REST ufficiale
(/wp-json/wp/v2/users) usando una Application Password, e li confronta
con la tabella `pazienti` del gestionale usando l'EMAIL come chiave unica
(normalizzata: minuscola, senza spazi).

Regole condivise (decise con Giuseppe):
- email = chiave unica; stessa email = stessa persona (niente doppioni)
- email normalizzata: .strip().lower()
- sui dati anagrafici in conflitto vince pnev.it (il paziente li ha scritti lui)
- la clinica resta SOLO nel gestionale e non viene toccata
- chi non combacia NON sparisce: finisce nella lista "da abbinare a mano"

Questo modulo NON scrive nulla da solo: mostra i gruppi e importa solo i
pazienti che l'utente seleziona esplicitamente.

Segreti richiesti in .streamlit/secrets.toml:

    [pnev_wp]
    base_url = "https://www.pnev.it"
    user = "tuo_utente_admin"
    app_password = "xxxx xxxx xxxx xxxx xxxx xxxx"   # Application Password
"""
from __future__ import annotations

import base64
import json
import urllib.request
import urllib.error

import streamlit as st

from modules.app_core import get_connection


VERDE = "#1D6B44"

# Ruoli WordPress che NON sono pazienti (li mostriamo a parte, non in "da importare")
RUOLI_NON_PAZIENTE = {"administrator", "editor", "author", "contributor", "shop_manager"}


# ════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════

def _norm_email(e) -> str:
    """Chiave unica: minuscola, senza spazi."""
    return (e or "").strip().lower()


def _split_nome(display_name: str):
    """Divide un nome visualizzato WP in (nome, cognome) alla buona.
    Primo token = nome, il resto = cognome. L'anagrafica si puo' poi
    correggere a mano nel gestionale."""
    parti = (display_name or "").strip().split()
    if len(parti) >= 2:
        return parti[0], " ".join(parti[1:])
    if len(parti) == 1:
        return parti[0], ""
    return "", ""


def _row_get(row, key, idx):
    """Legge un campo sia da row dict (RealDictCursor) sia da tupla."""
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[idx]
    except Exception:
        return None


def _wp_get_users(base_url: str, user: str, app_password: str):
    """Scarica TUTTI gli utenti WP (paginati). Ritorna lista di dict:
    {id, name, email, roles}. Solleva un'eccezione con messaggio chiaro
    in caso di errore HTTP/autenticazione."""
    base_url = (base_url or "").rstrip("/")
    token = base64.b64encode(
        f"{user}:{(app_password or '').replace(' ', '')}".encode("utf-8")
    ).decode("ascii")

    utenti = []
    page = 1
    while True:
        url = (
            f"{base_url}/wp-json/wp/v2/users"
            f"?context=edit&per_page=100&page={page}"
        )
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Basic {token}")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                dati = json.loads(resp.read().decode("utf-8"))
                tot_pagine = int(resp.headers.get("X-WP-TotalPages", "1") or "1")
        except urllib.error.HTTPError as e:
            corpo = ""
            try:
                corpo = e.read().decode("utf-8")[:300]
            except Exception:
                pass
            if e.code in (401, 403):
                raise RuntimeError(
                    "Accesso negato (401/403): controlla utente e Application "
                    "Password, e che l'utente sia amministratore."
                )
            raise RuntimeError(f"Errore HTTP {e.code} da WordPress. {corpo}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Impossibile contattare pnev.it: {e.reason}")

        if not isinstance(dati, list):
            raise RuntimeError("Risposta inattesa da WordPress (non e' una lista).")

        for u in dati:
            utenti.append({
                "id": u.get("id"),
                "name": u.get("name") or "",
                "email": u.get("email") or "",
                "roles": [r.lower() for r in (u.get("roles") or [])],
            })

        if page >= tot_pagine:
            break
        page += 1

    return utenti


def _ensure_colonne(conn):
    """Aggiunge in sicurezza le due marche sul paziente (una volta sola):
      - origine : 'pnev.it' oppure 'gestionale' (da dove e' nato il paziente)
      - fa_maps : 0/1 (sta facendo il percorso MAPS adesso)
    Usa ADD COLUMN IF NOT EXISTS: e' idempotente, si puo' richiamare sempre."""
    try:
        cur = conn.cursor()
        cur.execute(
            "ALTER TABLE pazienti "
            "ADD COLUMN IF NOT EXISTS origine TEXT DEFAULT 'gestionale'"
        )
        cur.execute(
            "ALTER TABLE pazienti "
            "ADD COLUMN IF NOT EXISTS fa_maps INTEGER DEFAULT 0"
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _carica_pazienti(conn):
    """Ritorna dict email_normalizzata -> {id, nome, cognome, email}."""
    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome, email FROM pazienti")
    out = {}
    for row in cur.fetchall():
        em = _norm_email(_row_get(row, "email", 3))
        if not em:
            continue
        out[em] = {
            "id": _row_get(row, "id", 0),
            "cognome": _row_get(row, "cognome", 1) or "",
            "nome": _row_get(row, "nome", 2) or "",
            "email": em,
        }
    return out


def _importa_paziente(conn, nome: str, cognome: str, email: str):
    """INSERT minimale di un paziente arrivato da pnev.it.
    Solo anagrafica base + email; la clinica resta vuota e si compila
    nel gestionale. Ritorna l'id nuovo, o solleva eccezione."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pazienti
            (cognome, nome, data_nascita, sesso, telefono, email,
             indirizzo, cap, citta, provincia, codice_fiscale, stato_paziente,
             origine, fa_maps)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ATTIVO',%s,%s)
        RETURNING id
        """,
        (
            (cognome or "").strip().upper(),
            (nome or "").strip().title(),
            None, None,
            "", _norm_email(email),
            "", "", "", "", None,
            "pnev.it", 1,
        ),
    )
    row = cur.fetchone()
    return int(_row_get(row, "id", 0))


# ════════════════════════════════════════════════════════════════════
#  UI
# ════════════════════════════════════════════════════════════════════

def render_sync_pnev(conn=None):
    if conn is None:
        conn = get_connection()

    _ensure_colonne(conn)   # crea origine/fa_maps se mancano (idempotente)

    st.markdown(
        f"<h2 style='color:{VERDE};margin-bottom:0'>🔗 Sincronizza pazienti pnev.it</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Confronta gli iscritti a pnev.it con i pazienti del gestionale, "
        "usando l'email come chiave unica. Nessuna scrittura automatica: "
        "importi solo i pazienti che spunti tu."
    )

    cfg = st.secrets.get("pnev_wp", {})
    base_url = cfg.get("base_url", "")
    wp_user = cfg.get("user", "")
    wp_pass = cfg.get("app_password", "")

    if not (base_url and wp_user and wp_pass):
        st.warning("Credenziali pnev.it non configurate.")
        st.markdown(
            "Aggiungi nei **Secrets** del gestionale:\n\n"
            "```toml\n"
            "[pnev_wp]\n"
            'base_url = "https://www.pnev.it"\n'
            'user = "tuo_utente_admin"\n'
            'app_password = "xxxx xxxx xxxx xxxx xxxx xxxx"\n'
            "```\n\n"
            "La Application Password si crea su pnev.it in "
            "**Utenti → Profilo → Password applicazione**."
        )
        return

    if not st.button("📥 Leggi pazienti da pnev.it", type="primary"):
        st.info("Premi il pulsante per scaricare l'elenco da pnev.it.")
        return

    with st.spinner("Lettura utenti da pnev.it…"):
        try:
            utenti = _wp_get_users(base_url, wp_user, wp_pass)
        except RuntimeError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"Errore imprevisto: {e}")
            return
        pazienti = _carica_pazienti(conn)

    # Classificazione
    agganciati, nuovi, senza_email, non_pazienti = [], [], [], []
    for u in utenti:
        em = _norm_email(u["email"])
        is_paziente = not (set(u["roles"]) & RUOLI_NON_PAZIENTE)
        if not em:
            senza_email.append(u)
        elif em in pazienti:
            agganciati.append((u, pazienti[em]))
        elif not is_paziente:
            non_pazienti.append(u)
        else:
            nuovi.append(u)

    email_wp = {_norm_email(u["email"]) for u in utenti if u["email"]}
    solo_gestionale = [p for em, p in pazienti.items() if em not in email_wp]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Agganciati", len(agganciati))
    c2.metric("🆕 Nuovi da pnev.it", len(nuovi))
    c3.metric("🗂 Solo nel gestionale", len(solo_gestionale))
    c4.metric("⚠️ Senza email", len(senza_email))

    st.divider()

    # --- NUOVI: importabili ---
    st.subheader("🆕 Nuovi su pnev.it — da importare nel gestionale")
    if not nuovi:
        st.success("Nessun nuovo paziente da importare: sei in pari. 🎉")
    else:
        st.caption("Spunta chi vuoi importare, poi premi «Importa selezionati».")
        sel = []
        for u in nuovi:
            nome, cognome = _split_nome(u["name"])
            etichetta = f"{u['name']}  ·  {u['email']}"
            if st.checkbox(etichetta, key=f"imp_{u['id']}", value=True):
                sel.append((u, nome, cognome))

        if st.button(f"⬇️ Importa selezionati ({len(sel)})", type="primary",
                     disabled=not sel):
            ok, ko = 0, []
            for u, nome, cognome in sel:
                try:
                    _importa_paziente(conn, nome, cognome, u["email"])
                    ok += 1
                except Exception as e:
                    ko.append(f"{u['email']}: {e}")
            try:
                conn.commit()
            except Exception:
                pass
            if ok:
                st.success(f"Importati {ok} pazienti. Ricarica per aggiornare i conteggi.")
            if ko:
                st.error("Alcuni non importati:")
                for r in ko:
                    st.write("•", r)

    st.divider()

    # --- AGGANCIATI ---
    with st.expander(f"✅ Già agganciati per email ({len(agganciati)})"):
        for u, p in agganciati:
            st.write(f"• **{u['name']}** ({u['email']}) ↔ gestionale: "
                     f"{p['cognome']} {p['nome']}")
        if agganciati and st.button("🎧 Segna questi come «in percorso MAPS»"):
            emails = [p["email"] for _, p in agganciati]
            try:
                cur = conn.cursor()
                cur.executemany(
                    "UPDATE pazienti SET fa_maps=1 WHERE email=%s",
                    [(e,) for e in emails],
                )
                conn.commit()
                st.success(f"Segnati {len(emails)} pazienti come in percorso MAPS.")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Errore: {e}")

    # --- SOLO GESTIONALE ---
    with st.expander(f"🗂 Solo nel gestionale, non su pnev.it ({len(solo_gestionale)})"):
        st.caption("Pazienti che hai nel gestionale ma non risultano iscritti a pnev.it.")
        for p in solo_gestionale:
            st.write(f"• {p['cognome']} {p['nome']} ({p['email']})")

    # --- DA ABBINARE A MANO ---
    with st.expander(f"⚠️ Su pnev.it senza email — da abbinare a mano ({len(senza_email)})"):
        st.caption("Senza email non si possono agganciare in automatico.")
        for u in senza_email:
            st.write(f"• {u['name']} (id WP {u['id']})")

    # --- NON PAZIENTI (admin/redattori) ---
    if non_pazienti:
        with st.expander(f"👤 Altri utenti WP (non pazienti) ({len(non_pazienti)})"):
            for u in non_pazienti:
                st.write(f"• {u['name']} — ruoli: {', '.join(u['roles'])}")


# Alias di comodo, nel caso il router lo richiami col nome del modulo
ui_sync_pnev = render_sync_pnev
