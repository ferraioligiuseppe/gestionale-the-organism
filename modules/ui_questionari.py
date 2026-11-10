# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  UI QUESTIONARI — Visualizzazione risposte + invio email link       ║
║                                                                     ║
║  • render_questionari_viewer  → legge pnev_json e mostra risposte  ║
║  • invia_link_questionario    → genera link + invia email SMTP      ║
║  • render_genera_link_email   → pannello completo con email         ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
import json
import urllib.parse
import datetime
import smtplib
from email.message import EmailMessage
from typing import Optional
import streamlit as st


# ══════════════════════════════════════════════════════════════════════
#  SMTP — invio email
# ══════════════════════════════════════════════════════════════════════

def _smtp_cfg() -> dict:
    cfg = st.secrets.get("smtp", {})
    if not all(cfg.get(k) for k in ("HOST", "PORT", "USERNAME", "PASSWORD")):
        raise RuntimeError(
            "Secrets SMTP mancanti. Aggiungi in Streamlit Cloud → Secrets:\n"
            "[smtp]\nHOST = 'smtp.gmail.com'\nPORT = 587\n"
            "USERNAME = 'tua@gmail.com'\nPASSWORD = 'app-password'\nUSE_TLS = true"
        )
    return cfg


def _invia_email(to: str, subject: str, body: str) -> None:
    """Invia email semplice via SMTP configurato nei Secrets."""
    cfg = _smtp_cfg()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = cfg.get("FROM") or cfg["USERNAME"]
    msg["To"]      = to
    msg.set_content(body)

    host     = cfg["HOST"]
    port     = int(cfg["PORT"])
    use_tls  = str(cfg.get("USE_TLS", "true")).lower() in ("1", "true", "yes", "y")

    if use_tls:
        with smtplib.SMTP(host, port) as s:
            s.ehlo()
            s.starttls()
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port) as s:
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)


# ══════════════════════════════════════════════════════════════════════
#  GENERAZIONE LINK + INVIO EMAIL
# ══════════════════════════════════════════════════════════════════════

_Q_LABELS = {
    "ANAMNESI_PNEV":   "📋 Anamnesi PNEV (Gravidanza · Sviluppo · Familiarità)",
    "INPPS":           "📋 Questionario Neurosviluppo INPP – Bambini",
    "INPPS_ADULTI":    "📋 Questionario Neurosviluppo INPP – Adulti",
    "MELILLO_BAMBINI": "🧒 Melillo Bambini (Genitori)",
    "MELILLO_ADULTI":  "🧠 Melillo Adulti (Paziente)",
    "FISHER":          "👂 Fisher Auditivo",
    "VISIONE_BAMBINI": "👁️ Visione Bambini (Genitori)",
    "VISIONE_ADULTI":  "👁️ Visione Adulti (Paziente)",
    "DIARIO_ALIM":     "🍽️ Diario alimentare (7 giorni)",
}

_CORPO_EMAIL = """\
Gentile {destinatario},

Le inviamo il link per compilare il questionario:

  📋 {titolo}

👉 {url}

Il link è personale, monouso e valido per 7 giorni.
Dopo la compilazione può chiudere la pagina.

Grazie per la collaborazione.

Studio The Organism
"""


# ══════════════════════════════════════════════════════════════════════
#  STATO DEGLI INVII — inviato / aperto / completato
# ══════════════════════════════════════════════════════════════════════
_TRACCIAMENTO_PRONTO = False


def assicura_tracciamento(conn) -> bool:
    """Aggiunge a questionari_links le colonne che servono a sapere se il
    link è stato aperto. Si esegue una volta sola per avvio dell'app."""
    global _TRACCIAMENTO_PRONTO
    if _TRACCIAMENTO_PRONTO:
        return True
    cur = conn.cursor()
    try:
        for col, tipo in (("aperto_il", "TIMESTAMPTZ"), ("ultima_apertura", "TIMESTAMPTZ"),
                          ("aperture", "INTEGER"), ("inviato_a", "TEXT"), ("invio_esito", "TEXT")):
            cur.execute(f"ALTER TABLE questionari_links ADD COLUMN IF NOT EXISTS {col} {tipo}")
        conn.commit()
        _TRACCIAMENTO_PRONTO = True
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def registra_apertura(conn, link_id: int) -> None:
    """Chiamata dalla pagina pubblica quando il link personale viene aperto.
    Conta una sola volta per ogni visita (non a ogni clic nella pagina).
    Non deve mai bloccare la compilazione: ogni errore viene ignorato."""
    chiave = f"_q_apertura_registrata_{int(link_id)}"
    if st.session_state.get(chiave):
        return
    st.session_state[chiave] = True
    if not assicura_tracciamento(conn):
        return
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE questionari_links SET aperto_il = COALESCE(aperto_il, now()), "
            "ultima_apertura = now(), aperture = COALESCE(aperture, 0) + 1 "
            "WHERE id = %s", (int(link_id),))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _segna_invio(conn, token_hash: str, inviato_a: str, esito: str) -> None:
    """Annota a chi è stato mandato il link e com'è andato l'invio dell'email."""
    if not assicura_tracciamento(conn):
        return
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE questionari_links SET aperture = COALESCE(aperture, 0), "
            "inviato_a = %s, invio_esito = %s WHERE token_hash = %s",
            (inviato_a or None, esito, token_hash))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _a_roma(v):
    """Data/ora (testo o datetime) portata all'ora italiana; None se non leggibile."""
    from zoneinfo import ZoneInfo
    if not v:
        return None
    try:
        d = datetime.datetime.fromisoformat(v.replace("Z", "+00:00")) if isinstance(v, str) else v
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return d.astimezone(ZoneInfo("Europe/Rome"))
    except Exception:
        return None


def _fmt(v) -> str:
    d = _a_roma(v)
    return d.strftime("%d/%m/%Y %H:%M") if d else ""


def stato_link(used_at, expires_at, aperture, ultima_apertura, adesso=None) -> tuple[str, str]:
    """Ritorna (codice, testo) dello stato di un link personale."""
    from zoneinfo import ZoneInfo
    adesso = adesso or datetime.datetime.now(ZoneInfo("Europe/Rome"))
    if used_at:
        return "completato", f"✅ Completato il {_fmt(used_at)}"
    scad = _a_roma(expires_at)
    scaduto = bool(scad and adesso > scad)
    if aperture is None:
        return ("scaduto" if scaduto else "ignoto",
                ("⌛ Scaduto, non completato" if scaduto else "❔ Non completato")
                + " (apertura non registrata: link creato prima di questo controllo)")
    n = int(aperture)
    if n > 0:
        volte = "1 volta" if n == 1 else f"{n} volte"
        base = f"aperto {volte}, ultima il {_fmt(ultima_apertura)}, ma non completato"
        return ("scaduto_aperto", "⌛ Scaduto: " + base) if scaduto else ("aperto", "👀 " + base[0].upper() + base[1:])
    return ("scaduto_mai", "⌛ Scaduto: mai aperto") if scaduto else ("mai", "📭 Mai aperto")


def render_stato_invii(conn, paziente_id: int) -> None:
    """Elenco dei link personali inviati, con lo stato di ognuno."""
    st.subheader("📬 Stato degli invii")
    if not assicura_tracciamento(conn):
        st.warning("Non riesco a preparare il controllo delle aperture su questo database.")
        return

    c1, c2 = st.columns([2, 1])
    ambito = c1.radio("Mostra", ["Questo paziente", "Tutti i pazienti (ultimi 30 giorni)"],
                      horizontal=True, key=f"q_stato_ambito_{paziente_id}")
    solo_aperti = c2.checkbox("Solo non completati", value=False, key=f"q_stato_solo_{paziente_id}")
    tutti = ambito.startswith("Tutti")

    campi = ("id, paziente_id, questionario, created_at, expires_at, used_at, "
             "aperto_il, ultima_apertura, aperture, inviato_a, invio_esito")
    cur = conn.cursor()
    try:
        if tutti:
            cur.execute(f"SELECT {campi} FROM questionari_links ORDER BY id DESC LIMIT 400")
        else:
            cur.execute(f"SELECT {campi} FROM questionari_links WHERE paziente_id = %s "
                        "ORDER BY id DESC LIMIT 100", (paziente_id,))
        righe = [tuple(r[i] for i in range(11)) for r in (cur.fetchall() or [])]
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore lettura invii: {e}")
        return

    from zoneinfo import ZoneInfo
    adesso = datetime.datetime.now(ZoneInfo("Europe/Rome"))
    if tutti:
        limite = adesso - datetime.timedelta(days=30)
        righe = [r for r in righe if (_a_roma(r[3]) or adesso) >= limite]

    nomi = {}
    if tutti and righe:
        try:
            ids = sorted({int(r[1]) for r in righe if r[1] is not None})
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti WHERE id = ANY(%s)", (ids,))
            for p in cur.fetchall() or []:
                nomi[int(p[0])] = f"{p[1] or ''} {p[2] or ''}".strip()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    if not righe:
        st.info("Nessun link personale inviato.")
        return

    tabella, conta = [], {"completato": 0, "aperto": 0, "mai": 0}
    for (_id, pid, q, creato, scade, usato, _ap, ultima, aperture, inviato_a, esito) in righe:
        codice, testo = stato_link(usato, scade, aperture, ultima, adesso)
        if codice == "completato":
            conta["completato"] += 1
        elif codice in ("aperto", "scaduto_aperto"):
            conta["aperto"] += 1
        elif codice in ("mai", "scaduto_mai"):
            conta["mai"] += 1
        if solo_aperti and codice == "completato":
            continue
        riga = {}
        if tutti:
            riga["Paziente"] = nomi.get(int(pid), f"#{pid}") if pid is not None else ""
        riga["Questionario"] = _Q_LABELS.get(q, q)
        riga["Inviato il"] = _fmt(creato)
        riga["Stato"] = testo
        riga["Scade il"] = _fmt(scade)
        riga["Mandato a"] = inviato_a or ""
        riga["Email"] = esito or ""
        tabella.append(riga)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Link inviati", len(righe))
    m2.metric("Completati", conta["completato"])
    m3.metric("Aperti e non completati", conta["aperto"])
    m4.metric("Mai aperti", conta["mai"])

    if tabella:
        st.dataframe(tabella, use_container_width=True, hide_index=True)
    else:
        st.success("Tutti i link di questo elenco sono stati completati.")
    st.caption(
        "«Aperto» vuol dire che la pagina del questionario è stata aperta con quel link. "
        "L'apertura si registra per i link aperti da oggi in poi. "
        "I link aperti riutilizzabili (QR) non hanno un destinatario e non compaiono qui.")


def render_genera_link_email(conn, paziente_id: int) -> None:
    """
    Pannello per generare link questionari e inviarli via email.
    Sostituisce il vecchio expander — mostra email del paziente
    e permette di inviare direttamente.
    """
    st.subheader("🔗 Questionari per genitore / paziente")

    # Leggi email e dati paziente
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT Cognome, Nome, Email FROM Pazienti WHERE id = %s",
            (paziente_id,)
        )
        row = cur.fetchone()
    except Exception as e:
        st.error(f"Errore lettura paziente: {e}")
        return

    if not row:
        st.warning("Paziente non trovato.")
        return

    if isinstance(row, dict):
        cognome      = row.get("Cognome", "") or row.get("cognome", "")
        nome         = row.get("Nome", "") or row.get("nome", "")
        email_paz    = (row.get("Email") or row.get("email") or "").strip()
    else:
        cognome      = row[0] or ""
        nome         = row[1] or ""
        email_paz    = (row[2] or "").strip()

    # Email tutore: cercata nel record di consenso privacy più recente
    email_tutore = ""
    try:
        cur.execute(
            "SELECT Tutore_Email FROM Consensi_Privacy "
            "WHERE Paziente_ID = %s "
            "ORDER BY Data_Ora DESC NULLS LAST, ID DESC LIMIT 1",
            (paziente_id,)
        )
        rt = cur.fetchone()
        if rt:
            if isinstance(rt, dict):
                email_tutore = (rt.get("Tutore_Email") or rt.get("tutore_email") or "").strip()
            else:
                email_tutore = (rt[0] or "").strip()
    except Exception:
        email_tutore = ""

    nome_completo = f"{cognome} {nome}".strip()

    # Email destinatario
    email_default = email_tutore or email_paz
    col1, col2 = st.columns([2, 1])
    with col1:
        email_dest = st.text_input(
            "📧 Email destinatario (genitore o paziente)",
            value=email_default,
            key=f"q_email_dest_{paziente_id}",
            placeholder="esempio@gmail.com"
        )
    with col2:
        st.markdown("")
        st.caption(
            "Email dal profilo paziente" if email_default
            else "⚠️ Nessuna email nel profilo"
        )

    # Base URL
    base_url = st.secrets.get("public_links", {}).get("BASE_URL", "").rstrip("/")
    if not base_url:
        st.error("BASE_URL mancante nei Secrets → [public_links] BASE_URL = 'https://...'")
        return

    st.markdown("#### Seleziona questionario da inviare")

    # Verifica SMTP disponibile
    smtp_ok = True
    try:
        _smtp_cfg()
    except RuntimeError:
        smtp_ok = False
        st.warning(
            "⚠️ SMTP non configurato — il link verrà mostrato ma non inviato via email. "
            "Aggiungi [smtp] nei Secrets per l'invio automatico."
        )

    # Solo i questionari adatti all'età del paziente (regole in filtro_eta)
    voci_q = list(_Q_LABELS.items())
    try:
        from .filtro_eta import eta_paziente, questionario_pertinente
        _eta = eta_paziente(conn, paziente_id)
    except Exception:
        _eta = None
    if _eta is not None:
        tutti = st.checkbox("Mostra tutti i questionari", key=f"q_tutti_{paziente_id}")
        if not tutti:
            voci_q = [(c, l) for c, l in voci_q if questionario_pertinente(c, _eta)]
            st.caption(f"Paziente di {_eta} anni: mostro solo i questionari "
                       f"{'per adulti' if _eta >= 17 else 'per bambini (compilati dai genitori)'}.")

    # Bottoni per ogni questionario
    cols = st.columns(2)
    for i, (q_code, q_label) in enumerate(voci_q):
        with cols[i % 2]:
            if st.button(f"Genera + Invia — {q_label}",
                        key=f"q_btn_{q_code}_{paziente_id}",
                        type="primary" if smtp_ok and email_dest else "secondary"):
                _genera_e_invia(
                    conn=conn,
                    cur=cur,
                    paziente_id=paziente_id,
                    q_code=q_code,
                    q_label=q_label,
                    base_url=base_url,
                    email_dest=email_dest,
                    nome_paziente=nome_completo,
                    smtp_ok=smtp_ok,
                )


def _genera_e_invia(conn, cur, paziente_id: int, q_code: str, q_label: str,
                    base_url: str, email_dest: str, nome_paziente: str,
                    smtp_ok: bool) -> None:
    """Genera token, costruisce URL, invia email, mostra link."""
    try:
        import hashlib, hmac, secrets as _sec
        from zoneinfo import ZoneInfo

        token = _sec.token_urlsafe(32)

        # Hash del token per DB
        token_secret = st.secrets.get("privacy", {}).get("TOKEN_SECRET", "fallback_secret")
        key = token_secret.encode("utf-8") if isinstance(token_secret, str) else token_secret
        token_hash = hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()

        now     = datetime.datetime.now(ZoneInfo("Europe/Rome"))
        # Il diario si compila per una settimana: il link deve durare di più.
        expires = now + datetime.timedelta(days=10 if q_code == "DIARIO_ALIM" else 7)

        cur.execute(
            "INSERT INTO questionari_links "
            "(paziente_id, questionario, token_hash, created_at, expires_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (paziente_id, q_code, token_hash,
             now.isoformat(), expires.isoformat())
        )
        conn.commit()

        url = f"{base_url}/?q={q_code}&t={token}"

        # Mostra link sempre
        st.code(url, language="text")
        st.caption(f"Link valido fino al {expires.strftime('%d/%m/%Y %H:%M')}")

        # WhatsApp link
        testo_wa = f"Gentile genitore, la preghiamo di compilare il questionario {q_label}: {url}"
        wa_url = f"https://wa.me/?text={urllib.parse.quote(testo_wa, safe='')}"
        st.markdown(f"[📱 Invia via WhatsApp]({wa_url})")

        # Invio email
        if smtp_ok and email_dest:
            corpo = _CORPO_EMAIL.format(
                destinatario=nome_paziente or "Gentile utente",
                titolo=q_label,
                url=url,
            )
            if q_code == "DIARIO_ALIM":
                corpo = corpo.replace(
                    "Il link è personale, monouso e valido per 7 giorni.\nDopo la compilazione può chiudere la pagina.",
                    "Ogni sera aprite questo stesso link e scrivete cosa è stato mangiato e bevuto quel giorno.\n"
                    "Dopo 7 giorni premete «Ho finito». Il link è personale e vale 10 giorni.")
            try:
                _invia_email(
                    to=email_dest,
                    subject=f"Questionario {q_label} — Studio The Organism",
                    body=corpo,
                )
                _segna_invio(conn, token_hash, email_dest, "inviata")
                st.success(f"✅ Link creato e inviato via email a **{email_dest}**")
            except Exception as e_mail:
                _segna_invio(conn, token_hash, email_dest, "NON inviata: " + str(e_mail)[:120])
                st.warning(f"Link creato ma email non inviata: {e_mail}")
                st.info("Copia il link sopra e invialo manualmente.")
        else:
            _segna_invio(conn, token_hash, "", "non inviata (link da mandare a mano)")
            st.success("✅ Link creato. Copialo e invialo manualmente.")

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Errore: {e}")


# ══════════════════════════════════════════════════════════════════════
#  VISUALIZZATORE RISPOSTE QUESTIONARI
# ══════════════════════════════════════════════════════════════════════

def render_questionari_viewer(conn, paziente_id: int) -> None:
    """
    Mostra le risposte dei questionari compilati dal paziente/genitore
    come anamnesi strutturata, pronta per diventare relazione AI.
    """
    st.subheader("📋 Risposte Questionari — Anamnesi")

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, data_anamnesi, motivo, pnev_json, pnev_summary "
            "FROM anamnesi WHERE paziente_id = %s "
            "ORDER BY data_anamnesi DESC, id DESC LIMIT 1",
            (paziente_id,)
        )
        row = cur.fetchone()
    except Exception as e:
        st.error(f"Errore lettura anamnesi: {e}")
        return

    if not row:
        st.info("Nessun questionario compilato ancora per questo paziente.")
        st.caption(
            "Quando il genitore/paziente compila il questionario tramite il link, "
            "le risposte appariranno qui."
        )
        return

    if isinstance(row, dict):
        an_id      = row.get("id")
        data_an    = row.get("data_anamnesi", "")
        pnev_raw   = row.get("pnev_json") or {}
        summary    = row.get("pnev_summary") or ""
    else:
        an_id      = row[0]
        data_an    = row[1]
        pnev_raw   = row[3] or {}
        summary    = row[4] or ""

    # Parse pnev_json
    if isinstance(pnev_raw, str):
        try:
            pnev_obj = json.loads(pnev_raw)
        except Exception:
            pnev_obj = {}
    else:
        pnev_obj = pnev_raw or {}

    questionari = pnev_obj.get("questionari", {})

    if not questionari:
        st.info("Nessuna risposta ai questionari ancora disponibile.")
        return

    st.caption(f"Ultima compilazione: {data_an}")

    # Mostra summary se presente
    if summary:
        with st.expander("📄 Sintesi automatica (per AI relazione)", expanded=True):
            st.markdown(summary)
            st.caption(
                "Questo testo viene utilizzato automaticamente dall'Assistente AI "
                "quando genera la relazione clinica."
            )

    st.markdown("---")

    # ── ANAMNESI PNEV ──────────────────────────────────────────────────
    anam_pnev = questionari.get("anamnesi_pnev", {})
    if anam_pnev:
        with st.expander("📋 Anamnesi PNEV (compilata online)", expanded=True):
            st.caption(f"Fascia d'età indicata: {anam_pnev.get('fascia', '—')}")
            _mostra_questionario_generico(anam_pnev, "anamnesi_pnev")

    # ── INPPS ────────────────────────────────────────────────────────
    inpps = questionari.get("inpps_screening_genitori", {})
    if inpps:
        with st.expander("📋 INPP-R — Screening (compilato dai genitori)", expanded=True):
            screening = inpps.get("screening", {})
            positivi  = inpps.get("positivi", {})
            score     = screening.get("totale_positivi", 0)
            soglia    = screening.get("cutoff", 7)

            col1, col2 = st.columns(2)
            col1.metric("Score totale", score)
            col2.metric("Soglia clinica", soglia)

            if score >= soglia:
                st.error(f"🔴 Score ≥ soglia ({soglia}): profilo positivo INPP-R")
            else:
                st.success(f"🟢 Score < soglia: profilo nella norma")

            if positivi:
                st.markdown("**Aree positive:**")
                for area, val in positivi.items():
                    st.markdown(f"- {area}: **{val}**")

            if screening:
                st.markdown("**Dettaglio risposte:**")
                for domanda, risposta in list(screening.items())[:20]:
                    if risposta:
                        st.markdown(
                            f"<span style='color:#9a6700'>• {domanda}: {risposta}</span>",
                            unsafe_allow_html=True
                        )

    # ── MELILLO BAMBINI ───────────────────────────────────────────────
    mel_b = questionari.get("melillo_bambini", {})
    if mel_b:
        with st.expander("🧒 Melillo Bambini (compilato dai genitori)", expanded=False):
            _mostra_questionario_generico(mel_b, "melillo_bambini")

    # ── MELILLO ADULTI ────────────────────────────────────────────────
    mel_a = questionari.get("melillo_adulti", {})
    if mel_a:
        with st.expander("🧠 Melillo Adulti (compilato dal paziente)", expanded=False):
            _mostra_questionario_generico(mel_a, "melillo_adulti")

    # ── FISHER ───────────────────────────────────────────────────────
    fisher = questionari.get("fisher_auditivo_bambini", {})
    if fisher:
        with st.expander("👂 Fisher Auditivo (compilato)", expanded=False):
            _mostra_questionario_generico(fisher, "fisher")

    # ── VISIONE BAMBINI ───────────────────────────────────────────────
    vis_b = questionari.get("visione_bambini", {})
    if vis_b:
        with st.expander("👁️ Visione Bambini (compilato)", expanded=False):
            _mostra_questionario_generico(vis_b, "visione_bambini")

    # ── VISIONE ADULTI ────────────────────────────────────────────────
    vis_a = questionari.get("visione_adulti", {})
    if vis_a:
        with st.expander("👁️ Visione Adulti (compilato)", expanded=False):
            _mostra_questionario_generico(vis_a, "visione_adulti")

    # ── PULSANTE → RELAZIONE AI ───────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 Da anamnesi a relazione clinica")
    st.info(
        "Le risposte ai questionari sono già disponibili all'Assistente AI. "
        "Vai in **Relazioni Cliniche** e genera la relazione — l'AI leggerà "
        "automaticamente tutti i questionari compilati."
    )
    if st.button("→ Vai a Relazioni Cliniche", key=f"goto_relazioni_{paziente_id}"):
        try:
            from modules.app_menu import AREA_REPORT_AI
        except Exception:
            AREA_REPORT_AI = "🤖 Report & AI"
        st.session_state["nav_area"] = AREA_REPORT_AI
        st.session_state[f"nav_sotto_{AREA_REPORT_AI}"] = "🤖 Relazioni cliniche (AI)"
        st.rerun()


def _mostra_questionario_generico(dati: dict, nome: str) -> None:
    """Mostra le risposte di un questionario generico in formato leggibile."""
    if not dati:
        st.info("Nessuna risposta disponibile.")
        return

    # Score / punteggio se presente
    for chiave_score in ("score", "punteggio", "totale", "total"):
        if chiave_score in dati:
            st.metric("Score", dati[chiave_score])
            break

    # Risposte positive/significative
    positive = dati.get("positivi") or dati.get("positive") or {}
    if positive:
        st.markdown("**Risposte significative:**")
        for k, v in positive.items():
            st.markdown(f"- {k}: **{v}**")

    # Tutte le risposte
    risposte = dati.get("risposte") or dati.get("answers") or dati.get("screening") or {}
    if risposte and isinstance(risposte, dict):
        st.markdown("**Tutte le risposte:**")
        for domanda, risposta in list(risposte.items())[:30]:
            if risposta and risposta not in ("no", "No", False, 0, "0", ""):
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"• {domanda}")
                col2.markdown(f"**{risposta}**")

    # JSON grezzo come fallback
    if not positive and not risposte:
        st.json(dati)


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT — sezione completa
# ══════════════════════════════════════════════════════════════════════

def render_questionari_section(conn, paziente_id: int) -> None:
    """
    Entry point completo: genera link + visualizza risposte.
    Chiama da app_main_router.py.
    """
    st.title("📋 Questionari — Anamnesi Remota")

    tab_invia, tab_stato, tab_risposte = st.tabs([
        "📤 Genera e invia link",
        "📬 Stato degli invii",
        "📊 Risposte ricevute",
    ])

    with tab_stato:
        render_stato_invii(conn, paziente_id)

    with tab_invia:
        render_genera_link_email(conn, paziente_id)

    with tab_risposte:
        render_questionari_viewer(conn, paziente_id)

    st.markdown("---")
    try:
        from modules.questionari_cartacei import render_questionari_cartacei
        render_questionari_cartacei()
    except Exception as _e:
        st.caption(f"Versione cartacea non disponibile: {_e}")
