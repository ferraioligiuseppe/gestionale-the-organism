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
    "INPPS":           "📋 INPPS Screening (Genitori)",
    "MELILLO_BAMBINI": "🧒 Melillo Bambini (Genitori)",
    "MELILLO_ADULTI":  "🧠 Melillo Adulti (Paziente)",
    "FISHER":          "👂 Fisher Auditivo",
    "VISIONE_BAMBINI": "👁️ Visione Bambini (Genitori)",
    "VISIONE_ADULTI":  "👁️ Visione Adulti (Paziente)",
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

    # Bottoni per ogni questionario
    cols = st.columns(2)
    for i, (q_code, q_label) in enumerate(_Q_LABELS.items()):
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
        expires = now + datetime.timedelta(days=7)

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
        wa_url = f"https://wa.me/?text={testo_wa.replace(' ', '%20')}"
        st.markdown(f"[📱 Invia via WhatsApp]({wa_url})")

        # Invio email
        if smtp_ok and email_dest:
            corpo = _CORPO_EMAIL.format(
                destinatario=nome_paziente or "Gentile utente",
                titolo=q_label,
                url=url,
            )
            try:
                _invia_email(
                    to=email_dest,
                    subject=f"Questionario {q_label} — Studio The Organism",
                    body=corpo,
                )
                st.success(f"✅ Link creato e inviato via email a **{email_dest}**")
            except Exception as e_mail:
                st.warning(f"Link creato ma email non inviata: {e_mail}")
                st.info("Copia il link sopra e invialo manualmente.")
        else:
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

    # ── DEBUG TEMPORANEO ───────────────────────────────────────
    with st.expander("🐛 Debug (rimuovere dopo test)"):
        st.write(f"paziente_id ricevuto: `{paziente_id}` (tipo: {type(paziente_id).__name__})")
        try:
            cur_d = conn.cursor()
            # Conto totale
            cur_d.execute("SELECT COUNT(*) FROM anamnesi")
            tot = cur_d.fetchone()
            st.write(f"Totale righe in anamnesi: {tot[0] if not isinstance(tot, dict) else list(tot.values())[0]}")
            # Pazienti distinti
            cur_d.execute("SELECT DISTINCT paziente_id FROM anamnesi ORDER BY paziente_id")
            ids = cur_d.fetchall()
            ids_list = [r[0] if not isinstance(r, dict) else list(r.values())[0] for r in ids]
            st.write(f"Paziente_id distinti in anamnesi: {ids_list}")
            # Match con il paziente corrente
            cur_d.execute("SELECT id, paziente_id, motivo FROM anamnesi WHERE paziente_id = %s",
                            (paziente_id,))
            match = cur_d.fetchall()
            st.write(f"Match con paziente_id={paziente_id}: {len(match)} righe")
            for m in match:
                if isinstance(m, dict):
                    st.write(f"  → id={m.get('id')}, paziente_id={m.get('paziente_id')}, motivo={m.get('motivo')}")
                else:
                    st.write(f"  → id={m[0]}, paziente_id={m[1]}, motivo={m[2]}")
        except Exception as e:
            st.error(f"Debug fallito: {e}")
    # ── FINE DEBUG ──────────────────────────────────────────────

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

    # ── INPPS ────────────────────────────────────────────────────────
    inpps = questionari.get("inpps_screening_genitori", {})
    if inpps:
        with st.expander("📋 INPPS — Screening (compilato dai genitori)", expanded=True):
            screening = inpps.get("screening", {})
            positivi  = inpps.get("positivi", {})
            score     = inpps.get("score", 0)
            soglia    = inpps.get("soglia", 7)

            col1, col2 = st.columns(2)
            col1.metric("Score totale", score)
            col2.metric("Soglia clinica", soglia)

            if score >= soglia:
                st.error(f"🔴 Score ≥ soglia ({soglia}): profilo positivo INPPS")
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
        st.session_state["go_section"] = "️ Relazioni cliniche"
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

    tab_invia, tab_risposte = st.tabs([
        "📤 Genera e invia link",
        "📊 Risposte ricevute",
    ])

    with tab_invia:
        render_genera_link_email(conn, paziente_id)

    with tab_risposte:
        render_questionari_viewer(conn, paziente_id)
