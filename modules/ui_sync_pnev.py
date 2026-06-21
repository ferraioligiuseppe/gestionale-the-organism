# -*- coding: utf-8 -*-
"""Sincronizzazione pazienti pnev.it ↔ gestionale — The Organism.

Legge SOLO gli iscritti al corso MAPS di pnev.it (non tutti gli utenti
WordPress, per evitare i tanti account spam), tramite un endpoint
dedicato lato WordPress (vedi pnev-maps-endpoint.php), e li confronta
con la tabella `pazienti` usando l'EMAIL come chiave unica
(normalizzata: minuscola, senza spazi).

Regole condivise:
- email = chiave unica; stessa email = stessa persona (niente doppioni)
- email normalizzata: .strip().lower()
- sui dati anagrafici in conflitto vince pnev.it
- la clinica resta SOLO nel gestionale e non viene toccata
- chi non ha email finisce in "da abbinare a mano", non sparisce
- nessuna scrittura automatica: importi solo chi spunti tu

Marche sul paziente (create in automatico, idempotenti):
- origine : 'pnev.it' / 'gestionale'
- fa_maps : 1 se sta facendo il percorso MAPS

Segreti richiesti in .streamlit/secrets.toml:

    [pnev_wp]
    base_url = "https://www.pnev.it"
    maps_key = "la-stessa-chiave-del-php"
    maps_course_id = 123      # ID del corso MAPS (lo trovi col pulsante apposito)
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import urllib.error

import streamlit as st

# NB: get_connection si importa SOLO quando serve davvero (dentro le funzioni,
# se conn non viene passata). Importarlo qui in cima tirerebbe dentro tutto
# app_core (matplotlib ecc.), che nel cron leggero non c'è.


VERDE = "#1D6B44"

# Domini "usa e getta" e parole tipiche degli account di prova/sistema
JUNK_DOMAINS = {"gufum.com", "jazipo.com", "fanwn.com", "okcdeals.com"}


def _is_test(u) -> bool:
    """Riconosce gli account di test/sistema (da escludere di default)."""
    name = (u.get("name") or "").strip().lower()
    email = (u.get("email") or "").strip().lower()
    dom = email.split("@")[-1] if "@" in email else ""
    if dom in JUNK_DOMAINS:
        return True
    if "rossiwebmedia" in dom:
        return True
    if any(kw in name for kw in ("test", "prova", "demo")):
        return True
    if name in {"pnev", "user", "stimolazione uditiva", "stimolazione uditiva1"}:
        return True
    return False


def _rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════
#  HELPERS DB
# ════════════════════════════════════════════════════════════════════

def _norm_email(e) -> str:
    return (e or "").strip().lower()


def _split_nome(display_name: str):
    parti = (display_name or "").strip().split()
    if len(parti) >= 2:
        return parti[0], " ".join(parti[1:])
    if len(parti) == 1:
        return parti[0], ""
    return "", ""


def _row_get(row, key, idx):
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[idx]
    except Exception:
        return None


def _ensure_colonne(conn):
    """Aggiunge le marche origine/fa_maps se mancano. Idempotente."""
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
#  HELPERS HTTP (endpoint pnev.it)
# ════════════════════════════════════════════════════════════════════

def _http_get_json(url: str):
    """GET JSON con messaggi d'errore chiari. Si presenta come un browser
    (alcuni plugin di protezione bloccano le richieste 'robot')."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", None) or resp.getcode()
            try:
                st.session_state["maps_debug"] = {
                    "status": status,
                    "lunghezza": len(raw),
                    "inizio_risposta": raw[:300],
                }
            except Exception:
                pass
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        corpo = ""
        try:
            corpo = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        try:
            st.session_state["maps_debug"] = {"status": e.code, "inizio_risposta": corpo}
        except Exception:
            pass
        if e.code == 403:
            raise RuntimeError("Chiave non valida o richiesta bloccata (403): "
                               "controlla 'maps_key' e il plugin di protezione su pnev.it.")
        if e.code == 404:
            raise RuntimeError("Endpoint non trovato (404): il filo PHP non è "
                               "attivo su pnev.it, oppure l'URL è sbagliato.")
        raise RuntimeError(f"Errore HTTP {e.code} da pnev.it. {corpo}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Impossibile contattare pnev.it: {e.reason}")
    except json.JSONDecodeError:
        raise RuntimeError("pnev.it ha risposto, ma non con dati validi (probabile "
                           "blocco di un plugin di protezione). Vedi «Dettagli tecnici».")


def _url_maps(base_url: str, key: str, **params) -> str:
    base_url = (base_url or "").rstrip("/")
    q = {"key": key}
    q.update(params)
    return f"{base_url}/wp-json/pnev/v1/maps?" + urllib.parse.urlencode(q)


def _fetch_corsi(base_url: str, key: str):
    data = _http_get_json(_url_maps(base_url, key, list="courses"))
    return data.get("courses", []) if isinstance(data, dict) else []


def _norm_course_ids(value) -> str:
    """Accetta int, stringa '10476,19535' o lista [..]; restituisce '10476,19535'."""
    if isinstance(value, (list, tuple)):
        parti = [str(int(v)) for v in value if str(v).strip().isdigit()]
    else:
        parti = [p.strip() for p in str(value).replace(" ", "").split(",") if p.strip().isdigit()]
    return ",".join(parti)


def _fetch_studenti_maps(base_url: str, key: str, course_ids):
    """Legge gli iscritti MAPS. Se la risposta torna VUOTA (tipico blocco
    momentaneo lato pnev.it), riprova fino a 3 volte prima di arrendersi."""
    corsi = _norm_course_ids(course_ids)
    ultimo = []
    for tentativo in range(3):
        try:
            data = _http_get_json(_url_maps(base_url, key, course=corsi))
            studenti = (data.get("students") or []) if isinstance(data, dict) else []
            if studenti:
                return studenti      # ok: risposta piena
            ultimo = studenti        # vuota: riprovo tra poco
        except RuntimeError:
            if tentativo == 2:
                raise                # ultimo tentativo fallito: segnalo l'errore
        if tentativo < 2:
            time.sleep(2)
    return ultimo


# ════════════════════════════════════════════════════════════════════
#  UI
# ════════════════════════════════════════════════════════════════════

def render_sync_pnev(conn=None):
    if conn is None:
        from modules.app_core import get_connection
        conn = get_connection()

    _ensure_colonne(conn)

    st.markdown(
        f"<h2 style='color:{VERDE};margin-bottom:0'>🔗 Sincronizza pazienti pnev.it</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Legge SOLO gli iscritti al corso MAPS (niente account spam) e li "
        "confronta coi pazienti del gestionale per email. Nessuna scrittura "
        "automatica: importi solo chi spunti tu."
    )

    cfg = st.secrets.get("pnev_wp", {})
    base_url = cfg.get("base_url", "")
    maps_key = cfg.get("maps_key", "")
    course_id = cfg.get("maps_course_id", "")

    # --- Credenziali base mancanti ---
    if not (base_url and maps_key):
        st.warning("Configurazione pnev.it incompleta.")
        st.markdown(
            "**1)** Attiva su pnev.it il filo `pnev-maps-endpoint.php` "
            "(snippet WPCode o mu-plugin) e scegli una chiave segreta.\n\n"
            "**2)** Aggiungi nei **Secrets** del gestionale:\n\n"
            "```toml\n"
            "[pnev_wp]\n"
            'base_url = "https://www.pnev.it"\n'
            'maps_key = "la-stessa-chiave-del-php"\n'
            'maps_course_id = "10476,19535,18643"   # uno o piu\u0301 corsi MAPS, separati da virgola\n'
            "```"
        )
        return

    # --- Aiuto: trova l'ID del corso MAPS ---
    with st.expander("🔎 Non sai l'ID del corso MAPS? Cliccami"):
        if st.button("Elenca i corsi di pnev.it"):
            try:
                corsi = _fetch_corsi(base_url, maps_key)
                if not corsi:
                    st.info("Nessun corso trovato.")
                else:
                    st.write("Copia l'ID del corso MAPS in `maps_course_id` nei Secrets:")
                    for c in corsi:
                        st.write(f"• **ID {c.get('ID')}** — {c.get('post_title')}")
            except RuntimeError as e:
                st.error(str(e))

    if not course_id:
        st.info("Imposta `maps_course_id` nei Secrets (usa il pulsante qui sopra per trovarlo).")
        return

    # --- Lettura iscritti MAPS (resta in memoria, non sparisce) ---
    cc = st.columns([2, 1])
    if cc[0].button("📥 Leggi pazienti MAPS da pnev.it", type="primary"):
        with st.spinner("Lettura iscritti MAPS…"):
            try:
                st.session_state["maps_studenti"] = _fetch_studenti_maps(
                    base_url, maps_key, course_id)
                st.session_state.pop("maps_import_result", None)
            except RuntimeError as e:
                st.error(str(e)); return
            except Exception as e:
                st.error(f"Errore imprevisto: {e}"); return
    if cc[1].button("🧹 Pulisci schermata"):
        st.session_state.pop("maps_studenti", None)
        st.session_state.pop("maps_import_result", None)

    # Messaggio persistente dell'ultimo import
    res = st.session_state.get("maps_import_result")
    if res:
        ok, ko = res
        if ok:
            st.success(f"✅ Importati {ok} pazienti (origine pnev.it, in percorso MAPS). "
                       "Premi di nuovo «Leggi pazienti MAPS» per aggiornare i conteggi.")
        if ko:
            st.error("Alcuni non importati:")
            for r in ko:
                st.write("•", r)

    studenti = st.session_state.get("maps_studenti")

    # Riquadro diagnostico: cosa ha risposto pnev.it
    dbg = st.session_state.get("maps_debug")
    if dbg:
        with st.expander("🔧 Dettagli tecnici (cosa ha risposto pnev.it)"):
            st.write(f"Stato HTTP: **{dbg.get('status')}** · lunghezza risposta: "
                     f"{dbg.get('lunghezza','?')} caratteri")
            st.code((dbg.get("inizio_risposta") or "")[:300] or "(vuota)")

    if studenti is None:
        st.info("Premi «Leggi pazienti MAPS» per scaricare gli iscritti al corso MAPS.")
        return

    pazienti = _carica_pazienti(conn)

    # Classificazione (i NUOVI sono deduplicati per email: la chiave è una sola)
    agganciati, nuovi, senza_email = [], [], []
    visti = set()
    for u in studenti:
        em = _norm_email(u.get("email"))
        if not em:
            senza_email.append(u)
        elif em in pazienti:
            agganciati.append((u, pazienti[em]))
        elif em not in visti:
            visti.add(em)
            nuovi.append(u)

    email_maps = {_norm_email(u.get("email")) for u in studenti if u.get("email")}
    solo_gestionale = [p for em, p in pazienti.items() if em not in email_maps]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Agganciati", len(agganciati))
    c2.metric("🆕 Nuovi da MAPS", len(nuovi))
    c3.metric("🗂 Solo nel gestionale", len(solo_gestionale))
    c4.metric("⚠️ Senza email", len(senza_email))

    st.divider()

    # --- NUOVI: importabili (tutti, tranne i test esclusi) ---
    st.subheader("🆕 Iscritti MAPS non ancora nel gestionale")
    if not nuovi:
        st.success("Nessun nuovo paziente da importare: sei in pari. 🎉")
    else:
        def _lab(u):
            return f"{u.get('name','')} · {u.get('email','')}"
        lab2u = {_lab(u): u for u in nuovi}
        esclusi_def = [_lab(u) for u in nuovi if _is_test(u)]

        st.caption("Li importo tutti. Gli account di test sono già esclusi qui sotto: "
                   "puoi toglierne o aggiungerne. La lista NON sparisce più quando li tocchi.")
        esclusi = st.multiselect(
            "🚫 Da NON importare (test/sistema):",
            options=list(lab2u.keys()),
            default=esclusi_def,
        )
        esclusi_set = set(esclusi)
        da_importare = [u for lab, u in lab2u.items() if lab not in esclusi_set]
        st.write(f"➡️ **{len(da_importare)}** da importare · 🚫 **{len(esclusi)}** esclusi")

        if st.button(f"⬇️ Importa {len(da_importare)} pazienti", type="primary",
                     disabled=not da_importare):
            ok, ko = 0, []
            for u in da_importare:
                nome, cognome = _split_nome(u.get("name", ""))
                try:
                    _importa_paziente(conn, nome, cognome, u.get("email"))
                    ok += 1
                except Exception as e:
                    ko.append(f"{u.get('email')}: {e}")
            try:
                conn.commit()
            except Exception:
                pass
            st.session_state["maps_import_result"] = (ok, ko)
            st.session_state.pop("maps_studenti", None)  # forza una rilettura pulita
            _rerun()

    st.divider()

    # --- AGGANCIATI ---
    with st.expander(f"✅ Già agganciati per email ({len(agganciati)})"):
        for u, p in agganciati:
            st.write(f"• **{u.get('name','')}** ({u.get('email','')}) ↔ gestionale: "
                     f"{p['cognome']} {p['nome']}")
        if agganciati and st.button("🎧 Segna questi come «in percorso MAPS»"):
            emails = [p["email"] for _, p in agganciati]
            try:
                cur = conn.cursor()
                cur.executemany(
                    "UPDATE pazienti SET fa_maps=1, origine=COALESCE(origine,'gestionale') "
                    "WHERE email=%s",
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
    with st.expander(f"🗂 Solo nel gestionale, non iscritti a MAPS ({len(solo_gestionale)})"):
        for p in solo_gestionale:
            st.write(f"• {p['cognome']} {p['nome']} ({p['email']})")

    # --- SENZA EMAIL ---
    with st.expander(f"⚠️ Iscritti MAPS senza email — da abbinare a mano ({len(senza_email)})"):
        for u in senza_email:
            st.write(f"• {u.get('name','')} (id WP {u.get('id')})")


# ════════════════════════════════════════════════════════════════════
#  SYNC AUTOMATICO (chiamato dal cron notturno)
# ════════════════════════════════════════════════════════════════════

def processa_sync_pnev(conn=None, dry_run: bool = False) -> dict:
    """Sync automatico: legge gli iscritti MAPS da pnev.it, esclude spam/test,
    salta chi c'e' gia\u0300 (per email) e importa i nuovi (origine pnev.it, fa_maps=1).
    Pensata per il cron notturno. Ritorna un report.

    Se dry_run=True non scrive nulla: dice solo cosa farebbe.
    """
    if conn is None:
        from modules.app_core import get_connection
        conn = get_connection()

    report = {
        "letti": 0,
        "gia_presenti": 0,
        "esclusi_test": 0,
        "importati": 0,
        "errori": [],
        "dettaglio": [],
    }

    cfg = st.secrets.get("pnev_wp", {})
    base_url = cfg.get("base_url", "")
    maps_key = cfg.get("maps_key", "")
    course_id = cfg.get("maps_course_id", "")
    if not (base_url and maps_key and course_id):
        report["errori"].append(
            "Config pnev_wp incompleta (base_url / maps_key / maps_course_id).")
        return report

    _ensure_colonne(conn)

    try:
        studenti = _fetch_studenti_maps(base_url, maps_key, course_id)
    except Exception as e:
        report["errori"].append(f"Lettura pnev.it: {e}")
        return report

    report["letti"] = len(studenti)
    pazienti = _carica_pazienti(conn)

    visti = set()
    for u in studenti:
        em = _norm_email(u.get("email"))
        if not em:
            continue
        if em in pazienti:
            report["gia_presenti"] += 1
            continue
        if em in visti:
            continue
        visti.add(em)
        if _is_test(u):
            report["esclusi_test"] += 1
            continue

        nome, cognome = _split_nome(u.get("name", ""))
        if dry_run:
            report["importati"] += 1
            report["dettaglio"].append(
                {"azione": "IMPORTEREBBE", "nome": u.get("name", ""), "email": em})
            continue
        try:
            _importa_paziente(conn, nome, cognome, em)
            conn.commit()                      # ogni paziente confermato subito
            report["importati"] += 1
            report["dettaglio"].append(
                {"azione": "importato", "nome": u.get("name", ""), "email": em})
        except Exception as e:
            try:
                conn.rollback()                # pulisce la transazione: il prossimo riparte pulito
            except Exception:
                pass
            report["errori"].append(f"{em}: {e}")

    if not dry_run:
        try:
            conn.commit()
        except Exception:
            pass

    return report


# Alias di comodo
ui_sync_pnev = render_sync_pnev
