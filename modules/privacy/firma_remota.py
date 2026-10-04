# -*- coding: utf-8 -*-
"""Firma della privacy a distanza: invio del link, registro, promemoria, avvisi.

Il flusso di firma esisteva gia' (app_core.ui_public_sign_page, ?sign=TOKEN:
lettura, OTP via email, firma con il dito, PDF in Consensi_Privacy). Mancava
tutto quello che c'e' intorno:
  · il link andava copiato e mandato a mano
  · non si sapeva chi aveva firmato e chi no
  · lo studio non veniva avvisato
  · chi arrivava da pnev.it (eventi, primo contatto) non firmava nulla

Questo modulo NON importa app_core: lo usa anche l'app pubblica degli eventi
(apps/pnev_pubblico.py), che e' un'altra app Streamlit. Per questo il token
e' ricostruito qui con lo stesso formato e lo stesso segreto di
app_core._make_sign_token, cosi' la pagina ?sign= lo riconosce.

Tabella: privacy_richieste_firma (una riga per ogni link inviato).
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import urllib.parse

import streamlit as st

STUDIO_EMAIL_DEFAULT = "dr.ferraioligiuseppe@gmail.com"
ORIGINI = {"studio": "Dallo studio", "evento": "Iscrizione evento", "primo_contatto": "Primo contatto (pnev.it)"}


# ── configurazione ────────────────────────────────────────────────────

def _sec(nome):
    try:
        return st.secrets.get(nome, {}) or {}
    except Exception:
        return {}


def _scadenza_secondi() -> int:
    try:
        return int(_sec("privacy").get("TOKEN_EXPIRE_SECONDS", 172800))
    except Exception:
        return 172800


def email_studio() -> str:
    return (_sec("privacy").get("CLINIC_EMAIL") or STUDIO_EMAIL_DEFAULT).strip()


def base_url() -> str:
    return (_sec("privacy").get("PUBLIC_BASE_URL") or _sec("public_links").get("BASE_URL") or "").rstrip("/")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def crea_token(paziente_id: int, doc_type: str) -> str:
    """Stesso formato di app_core._make_sign_token."""
    segreto = _sec("privacy").get("TOKEN_SECRET")
    if not segreto:
        raise RuntimeError("manca [privacy] TOKEN_SECRET nei Secrets di questa app")
    payload = {"pid": int(paziente_id), "doc": str(doc_type),
               "exp": int(dt.datetime.utcnow().timestamp()) + _scadenza_secondi(), "v": 1}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    firma = hmac.new(segreto.encode("utf-8"), raw, hashlib.sha256).digest()
    return _b64url(raw) + "." + _b64url(firma)


def url_firma(token: str) -> str:
    b = base_url()
    if not b:
        raise RuntimeError("manca [privacy] PUBLIC_BASE_URL nei Secrets (indirizzo del gestionale)")
    return f"{b}/?sign={urllib.parse.quote(token)}"


def url_primo_contatto() -> str:
    b = base_url()
    return f"{b}/?primo_contatto=1" if b else ""


def _hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


# ── database ──────────────────────────────────────────────────────────

def assicura_tabella(conn) -> None:
    if st.session_state.get("_priv_rich_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS privacy_richieste_firma ("
            " id SERIAL PRIMARY KEY,"
            " paziente_id INTEGER NOT NULL,"
            " doc_type TEXT NOT NULL,"
            " email TEXT,"
            " origine TEXT DEFAULT 'studio',"
            " riferimento TEXT,"
            " token_hash TEXT,"
            " stato TEXT DEFAULT 'da_inviare',"
            " esito_invio TEXT,"
            " creata_il TIMESTAMP DEFAULT NOW(),"
            " inviata_il TIMESTAMP,"
            " ultimo_promemoria TIMESTAMP,"
            " n_promemoria INTEGER DEFAULT 0,"
            " firmata_il TIMESTAMP,"
            " creata_da TEXT)")
        cur.execute("CREATE INDEX IF NOT EXISTS privacy_rich_paz ON privacy_richieste_firma (paziente_id, doc_type, stato)")
        cur.execute("CREATE INDEX IF NOT EXISTS privacy_rich_tok ON privacy_richieste_firma (token_hash)")
        conn.commit()
        st.session_state["_priv_rich_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        righe = cur.fetchall() or []
        if righe and not isinstance(righe[0], dict):
            nomi = [c[0] for c in cur.description]
            righe = [dict(zip(nomi, r)) for r in righe]
        return righe
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = None
        try:
            r = cur.fetchone()
        except Exception:
            pass
        conn.commit()
        if r is not None and not isinstance(r, dict):
            r = {"id": r[0]}
        return r, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return None, str(e)


def email_paziente(conn, paziente_id) -> str:
    r = _q(conn, "SELECT email FROM pazienti WHERE id=%s", (int(paziente_id),))
    return ((r[0].get("email") if r else "") or "").strip()


def nome_paziente(conn, paziente_id) -> str:
    r = _q(conn, "SELECT cognome, nome FROM pazienti WHERE id=%s", (int(paziente_id),))
    return f"{r[0].get('nome') or ''} {r[0].get('cognome') or ''}".strip().title() if r else ""


def richiesta_da_token(conn, token):
    assicura_tabella(conn)
    r = _q(conn, "SELECT * FROM privacy_richieste_firma WHERE token_hash=%s ORDER BY id DESC LIMIT 1", (_hash(token),))
    return r[0] if r else None


def gia_firmato(conn, paziente_id, doc_type, dopo=None) -> bool:
    """True se dopo `dopo` c'e' gia' un consenso online per quel paziente."""
    par = [int(paziente_id), "MINORE" if doc_type == "minore" else "ADULTO"]
    sql = ("SELECT 1 FROM consensi_privacy WHERE paziente_id=%s AND UPPER(tipo)=%s "
           "AND firma_source='online'")
    if dopo:
        sql += " AND data_ora >= %s"
        par.append(str(dopo)[:19].replace("T", " "))
    return bool(_q(conn, sql + " LIMIT 1", tuple(par)))


# ── email ─────────────────────────────────────────────────────────────

def _invia(to, oggetto, corpo, allegato=None, nome_allegato=None, html=None):
    """Con o senza allegato, con [gmail] o [smtp] (stessa logica di email_otp)."""
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    try:
        from modules.email_otp import _config_invio, _spedisci
    except Exception as e:
        return False, f"modulo email non disponibile: {e}"
    conf, motivo = _config_invio()
    if not conf:
        return False, motivo
    host, porta, ssl_diretto, mittente, password = conf
    if not to or "@" not in to:
        return False, f"indirizzo non valido: {to!r}"
    msg = MIMEMultipart("mixed")
    msg["Subject"], msg["From"], msg["To"] = oggetto, mittente, to
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(corpo, "plain", "utf-8"))
    if html:
        alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)
    if allegato:
        p = MIMEApplication(allegato, _subtype="pdf")
        p.add_header("Content-Disposition", "attachment", filename=nome_allegato or "consenso.pdf")
        msg.attach(p)
    try:
        _spedisci(mittente, password, host, porta, ssl_diretto, to, msg)
        return True, f"inviata a {to}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _testo_invito(nome, doc_type, url, promemoria=False):
    chi = "di tuo figlio/a" if doc_type == "minore" else ""
    apertura = ("ti ricordiamo che non abbiamo ancora ricevuto il consenso privacy" if promemoria
                else "per completare l'iscrizione ti chiediamo di firmare il consenso privacy")
    testo = (f"Gentile {nome or 'cliente'},\n\n"
             f"{apertura} {chi} dello Studio The Organism.\n\n"
             "Ci vogliono due minuti dal telefono: apri il link, leggi il documento, "
             "inserisci il codice che ti arriva per email e firma con il dito.\n\n"
             f"{url}\n\n"
             "Il link è personale e vale 48 ore. Se scade, rispondi a questa email e te ne mandiamo uno nuovo.\n\n"
             "Studio The Organism · www.pnev.it")
    html = (f'<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.55;color:#1F2A24;max-width:520px">'
            f'<p>Gentile {nome or "cliente"},</p>'
            f'<p>{apertura} {chi} dello <b>Studio The Organism</b>.</p>'
            '<p>Ci vogliono due minuti dal telefono: apri il link, leggi il documento, inserisci il codice '
            'che ti arriva per email e firma con il dito.</p>'
            f'<p style="margin:22px 0"><a href="{url}" style="background:#1D6B44;color:#fff;text-decoration:none;'
            'padding:13px 22px;border-radius:8px;font-weight:bold;display:inline-block">✍️ Firma il consenso</a></p>'
            '<p style="font-size:13px;color:#5A6660">Il link è personale e vale 48 ore. Se scade, rispondi a questa '
            'email e te ne mandiamo uno nuovo.</p>'
            '<p style="font-size:13px;color:#5A6660">Studio The Organism · www.pnev.it</p></div>')
    oggetto = ("Promemoria: consenso privacy da firmare — Studio The Organism" if promemoria
               else "Consenso privacy da firmare — Studio The Organism")
    return oggetto, testo, html


# ── azioni ────────────────────────────────────────────────────────────

def crea_e_invia(conn, paziente_id, doc_type, email, origine="studio", riferimento="",
                 invia=True, promemoria_di=None):
    """Crea la richiesta, genera il link e (se `invia`) manda l'email.
    Ritorna (ok, motivo, url). Se manca la configurazione la richiesta resta
    «da inviare» e si vede nell'elenco del gestionale."""
    assicura_tabella(conn)
    chi = str(st.session_state.get("username") or st.session_state.get("user") or origine)
    url, token, err = "", "", ""
    try:
        token = crea_token(paziente_id, doc_type)
        url = url_firma(token)
    except Exception as e:
        err = str(e)
    if promemoria_di:
        _esegui(conn, "UPDATE privacy_richieste_firma SET token_hash=%s, email=%s WHERE id=%s",
                (_hash(token) if token else None, email, int(promemoria_di)))
        rid = int(promemoria_di)
    else:
        r, e2 = _esegui(conn,
            "INSERT INTO privacy_richieste_firma (paziente_id, doc_type, email, origine, riferimento, "
            "token_hash, stato, creata_da) VALUES (%s,%s,%s,%s,%s,%s,'da_inviare',%s) RETURNING id",
            (int(paziente_id), doc_type, email, origine, riferimento, _hash(token) if token else None, chi))
        if not r:
            return False, f"registro non scritto: {e2}", url
        rid = int(r["id"])
    if err:
        _esegui(conn, "UPDATE privacy_richieste_firma SET esito_invio=%s WHERE id=%s", (err, rid))
        return False, err, ""
    if not invia:
        return True, "link creato", url
    oggetto, testo, html = _testo_invito(nome_paziente(conn, paziente_id), doc_type, url, bool(promemoria_di))
    ok, motivo = _invia(email, oggetto, testo, html=html)
    if ok and promemoria_di:
        _esegui(conn, "UPDATE privacy_richieste_firma SET stato='inviata', esito_invio=%s, ultimo_promemoria=NOW(), "
                      "n_promemoria=COALESCE(n_promemoria,0)+1 WHERE id=%s", (motivo, rid))
    elif ok:
        _esegui(conn, "UPDATE privacy_richieste_firma SET stato='inviata', esito_invio=%s, inviata_il=NOW() "
                      "WHERE id=%s", (motivo, rid))
    else:
        _esegui(conn, "UPDATE privacy_richieste_firma SET esito_invio=%s WHERE id=%s", (motivo, rid))
    return ok, motivo, url


def dopo_firma(conn, paziente_id, doc_type, email, pdf_bytes, nome_file, token=""):
    """Chiamata dalla pagina pubblica appena il consenso e' salvato.
    Chiude le richieste aperte, manda la copia al paziente e avvisa lo studio.
    Ritorna (ok_paziente, ok_studio, messaggi)."""
    assicura_tabella(conn)
    _esegui(conn, "UPDATE privacy_richieste_firma SET stato='firmata', firmata_il=NOW() "
                  "WHERE paziente_id=%s AND doc_type=%s AND stato IN ('da_inviare','inviata')",
            (int(paziente_id), doc_type))
    nome = nome_paziente(conn, paziente_id)
    ok_p, m_p = _invia(email, "Copia del consenso privacy firmato — Studio The Organism",
                       f"Gentile {nome or 'cliente'},\n\ngrazie: in allegato trovi la copia del consenso "
                       "informato e privacy che hai appena firmato.\n\nStudio The Organism · www.pnev.it",
                       pdf_bytes, nome_file)
    ora = dt.datetime.now().strftime("%d/%m/%Y alle %H:%M")
    ok_s, m_s = _invia(email_studio(), f"[Privacy firmata] {nome or 'Paziente ' + str(paziente_id)}",
                       f"{nome or 'Il paziente'} (ID {paziente_id}) ha firmato il consenso "
                       f"{'minore' if doc_type == 'minore' else 'adulto'} il {ora}.\n"
                       f"Email verificata con OTP: {email}\n\n"
                       "Il PDF è allegato ed è già archiviato nel gestionale (Privacy & Consensi → Storico).",
                       pdf_bytes, nome_file)
    return ok_p, ok_s, [m_p, m_s]


# ── gestionale: bottone nella scheda privacy ──────────────────────────

def render_invio_link(conn, paziente_id, doc_type):
    assicura_tabella(conn)
    st.markdown("**✍️ Firma a distanza**")
    st.caption("Il paziente riceve un'email con il link, firma dal telefono e il consenso torna qui da solo. "
               "Quando firma ti arriva un avviso con il PDF.")
    k = f"{paziente_id}_{doc_type}"
    if f"priv_mail_{k}" not in st.session_state:
        st.session_state[f"priv_mail_{k}"] = email_paziente(conn, paziente_id)
    c1, c2 = st.columns([3, 2])
    mail = c1.text_input("Email a cui mandare il link" + (" (genitore/tutore)" if doc_type == "minore" else ""),
                         key=f"priv_mail_{k}", placeholder="nome@esempio.it")
    c2.write("")
    c2.write("")
    if c2.button("📧 Invia link per email", key=f"priv_invia_{k}", type="primary", use_container_width=True):
        if "@" not in (mail or ""):
            st.error("Inserisci un'email valida.")
        else:
            ok, motivo, url = crea_e_invia(conn, paziente_id, doc_type, mail.strip(), "studio")
            if ok:
                st.success(f"Link inviato a {mail.strip()}. Lo trovi in «Firme privacy in attesa» finché non firma.")
            else:
                st.error(f"Email non partita: {motivo}")
            if url:
                st.session_state[f"priv_url_{k}"] = url
    url = st.session_state.get(f"priv_url_{k}")
    with st.expander("Altro: copia il link o mandalo su WhatsApp"):
        if st.button("Genera solo il link (senza email)", key=f"priv_solo_{k}"):
            ok, motivo, url = crea_e_invia(conn, paziente_id, doc_type, (mail or "").strip(), "studio", invia=False)
            if ok:
                st.session_state[f"priv_url_{k}"] = url
            else:
                st.error(motivo)
        if url:
            st.code(url, language=None)
            testo = urllib.parse.quote("Apri questo link per firmare il consenso privacy dello Studio The Organism: " + url)
            st.markdown(f"[Apri WhatsApp con il messaggio pronto](https://wa.me/?text={testo})")
    aperte = _q(conn, "SELECT stato, inviata_il, email FROM privacy_richieste_firma WHERE paziente_id=%s "
                      "AND doc_type=%s AND stato IN ('da_inviare','inviata') ORDER BY id DESC LIMIT 1",
                (int(paziente_id), doc_type))
    if aperte:
        a = aperte[0]
        quando = a.get("inviata_il").strftime("%d/%m %H:%M") if a.get("inviata_il") else "—"
        st.info(f"🟡 In attesa di firma · link inviato il {quando} a {a.get('email') or '—'}")


# ── gestionale: elenco in attesa ──────────────────────────────────────

def render_in_attesa(conn):
    st.subheader("✍️ Firme privacy in attesa")
    assicura_tabella(conn)
    righe = _q(conn,
        "SELECT r.*, p.cognome, p.nome FROM privacy_richieste_firma r "
        "LEFT JOIN pazienti p ON p.id = r.paziente_id "
        "WHERE r.stato IN ('da_inviare','inviata') ORDER BY COALESCE(r.inviata_il, r.creata_il)")
    firmate = _q(conn,
        "SELECT r.*, p.cognome, p.nome FROM privacy_richieste_firma r "
        "LEFT JOIN pazienti p ON p.id = r.paziente_id "
        "WHERE r.stato='firmata' AND r.firmata_il > NOW() - INTERVAL '30 days' ORDER BY r.firmata_il DESC")
    ora = dt.datetime.now()
    scad = dt.timedelta(seconds=_scadenza_secondi())

    def ferma_da(r):
        t = r.get("ultimo_promemoria") or r.get("inviata_il") or r.get("creata_il")
        return (ora - t) if t else dt.timedelta(0)

    da_ricordare = [r for r in righe if r.get("stato") == "inviata" and ferma_da(r) > dt.timedelta(days=2)]
    c1, c2, c3 = st.columns(3)
    c1.metric("In attesa", len(righe))
    c2.metric("Ferme da più di 2 giorni", len(da_ricordare))
    c3.metric("Firmate negli ultimi 30 giorni", len(firmate))

    if da_ricordare and st.button(f"🔔 Manda il promemoria a tutte e {len(da_ricordare)}", type="primary"):
        n_ok, errori = 0, []
        for r in da_ricordare:
            ok, motivo, _u = crea_e_invia(conn, r["paziente_id"], r["doc_type"], r.get("email"),
                                          promemoria_di=r["id"])
            n_ok += ok
            if not ok:
                errori.append(f"{r.get('cognome') or ''} {r.get('nome') or ''}: {motivo}")
        st.success(f"Promemoria inviati: {n_ok}.")
        for e in errori:
            st.caption("⚠️ " + e)
        st.rerun()

    if not righe:
        st.info("Nessuna firma in attesa.")
    for r in righe:
        nome = f"{(r.get('cognome') or '').title()} {(r.get('nome') or '').title()}".strip() or f"Paziente {r['paziente_id']}"
        if r.get("stato") == "da_inviare":
            stato = "⚪ da inviare"
        elif ferma_da(r) > scad:
            stato = "🔴 link scaduto"
        elif ferma_da(r) > dt.timedelta(days=2):
            stato = "🟠 ferma da " + str(ferma_da(r).days) + " giorni"
        else:
            stato = "🟡 inviata"
        with st.container(border=True):
            a, b = st.columns([5, 3])
            info = [ORIGINI.get(r.get("origine"), r.get("origine") or ""),
                    "minore" if r.get("doc_type") == "minore" else "adulto",
                    r.get("email") or "senza email"]
            if r.get("inviata_il"):
                info.append("inviata " + r["inviata_il"].strftime("%d/%m %H:%M"))
            if r.get("n_promemoria"):
                info.append(f"{r['n_promemoria']} promemoria")
            if r.get("riferimento"):
                info.append(r["riferimento"])
            a.markdown(f"**{nome}** · {stato}  \n<small>{' · '.join(info)}</small>", unsafe_allow_html=True)
            if r.get("esito_invio") and not str(r.get("esito_invio")).startswith("inviata"):
                a.caption("⚠️ " + str(r["esito_invio"]))
            k = r["id"]
            x, y = b.columns(2)
            if x.button("🔔 Promemoria" if r.get("stato") == "inviata" else "📧 Invia", key=f"pr_{k}"):
                ok, motivo, _u = crea_e_invia(conn, r["paziente_id"], r["doc_type"], r.get("email"),
                                              promemoria_di=k)
                (st.success if ok else st.error)(motivo)
                st.rerun()
            if y.button("Annulla", key=f"an_{k}"):
                _esegui(conn, "UPDATE privacy_richieste_firma SET stato='annullata' WHERE id=%s", (k,))
                st.rerun()

    if firmate:
        with st.expander(f"✅ Firmate negli ultimi 30 giorni ({len(firmate)})"):
            for r in firmate:
                nome = f"{(r.get('cognome') or '').title()} {(r.get('nome') or '').title()}".strip()
                st.markdown(f"- **{nome}** · {r['firmata_il'].strftime('%d/%m/%Y %H:%M')} · "
                            f"{ORIGINI.get(r.get('origine'), '')}")

    _render_prova(conn)

    st.markdown("---")
    st.markdown("**🌐 Modulo «primo contatto» per www.pnev.it**")
    u = url_primo_contatto()
    if u:
        st.caption("Chi lo compila viene registrato come nuovo paziente e firma subito il consenso. "
                   "Incolla questo blocco in un elemento HTML della pagina di pnev.it:")
        st.code(f'<a href="{u}" target="_blank" rel="noopener" style="display:inline-block;background:#1D6B44;'
                'color:#fff;padding:14px 26px;border-radius:8px;font-weight:bold;text-decoration:none">'
                '📝 Primo contatto con lo studio</a>', language="html")
    else:
        st.caption("Per creare il link serve [privacy] PUBLIC_BASE_URL nei Secrets.")


# ── pagina pubblica: primo contatto ───────────────────────────────────

_CSS_TELEFONO = """<style>
header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu{display:none!important}
.block-container{max-width:560px!important;padding:1.2rem 1rem 3rem!important}
input, textarea, select{font-size:16px!important}
.stButton>button, .stFormSubmitButton>button, a[data-testid^="stBaseLinkButton"]{width:100%;padding:14px!important;font-size:1.05rem!important}
</style>"""


def css_telefono():
    st.markdown(_CSS_TELEFONO, unsafe_allow_html=True)


def render_primo_contatto(conn):
    css_telefono()
    st.markdown("#### Studio The Organism")
    st.title("Primo contatto")
    st.caption("Lascia i tuoi dati: ti registriamo come nuovo paziente e firmi subito il consenso privacy. "
               "Poi ti richiamiamo noi per fissare l'appuntamento.")
    if st.session_state.get("pc_fatto"):
        st.success("Dati ricevuti, grazie.")
        u = st.session_state.get("pc_url")
        if u:
            st.link_button("✍️ Firma ora il consenso", u, type="primary")
            st.caption("Ti abbiamo mandato lo stesso link anche per email.")
        st.stop()

    with st.form("primo_contatto"):
        per_chi = st.radio("Per chi è l'appuntamento?", ["Per me", "Per mio figlio / mia figlia"], horizontal=True)
        minore = per_chi.startswith("Per mio")
        st.markdown("**" + ("Dati del bambino/a" if minore else "I tuoi dati") + "**")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome *")
        cognome = c2.text_input("Cognome *")
        nascita = st.date_input("Data di nascita *", value=None, min_value=dt.date(1920, 1, 1),
                                max_value=dt.date.today(), format="DD/MM/YYYY")
        if minore:
            st.markdown("**Dati del genitore / tutore**")
            g1, g2 = st.columns(2)
            nome_g = g1.text_input("Nome genitore *")
            cognome_g = g2.text_input("Cognome genitore *")
        else:
            nome_g = cognome_g = ""
        c3, c4 = st.columns(2)
        email = c3.text_input("Email *")
        tel = c4.text_input("Telefono *")
        motivo = st.text_area("Per cosa ci contatti? (facoltativo)", height=90)
        sito = st.text_input("Sito web", key="pc_hp", label_visibility="collapsed",
                             placeholder="lascia vuoto")  # trappola per i robot
        letto = st.checkbox("Ho letto l'informativa privacy e acconsento al trattamento dei dati per essere ricontattato/a. *")
        inviato = st.form_submit_button("Invia e firma il consenso", type="primary")

    if not inviato:
        return
    if sito.strip():
        st.success("Dati ricevuti, grazie.")
        st.stop()
    mancanti = [n for n, v in (("Nome", nome), ("Cognome", cognome), ("Email", email), ("Telefono", tel))
                if not (v or "").strip()]
    if minore:
        mancanti += [n for n, v in (("Nome genitore", nome_g), ("Cognome genitore", cognome_g)) if not (v or "").strip()]
    if not nascita:
        mancanti.append("Data di nascita")
    if mancanti:
        st.error("Mancano: " + ", ".join(mancanti) + ".")
        return
    if "@" not in email:
        st.error("Email non valida.")
        return
    if not letto:
        st.error("Serve la presa visione dell'informativa.")
        return
    if st.session_state.get("pc_tentativi", 0) >= 3:
        st.error("Troppi invii da questa pagina. Chiamaci allo 081 5152334.")
        return
    st.session_state["pc_tentativi"] = st.session_state.get("pc_tentativi", 0) + 1

    cog, nom = cognome.strip().upper(), nome.strip().upper()
    esist = _q(conn, "SELECT id FROM pazienti WHERE UPPER(cognome)=%s AND UPPER(nome)=%s AND data_nascita=%s LIMIT 1",
               (cog, nom, nascita))
    if esist:
        pid = int(esist[0]["id"])
    else:
        r, err = _esegui(conn,
            "INSERT INTO pazienti (cognome, nome, data_nascita, telefono, email, stato_paziente) "
            "VALUES (%s,%s,%s,%s,%s,'ATTIVO') RETURNING id",
            (cog, nom, nascita, tel.strip(), email.strip().lower()))
        if not r:
            st.error(f"Non siamo riusciti a registrare i dati. Chiamaci allo 081 5152334. ({err})")
            return
        pid = int(r["id"])
    doc = "minore" if minore else "adulto"
    rif = (f"Genitore: {cognome_g.strip()} {nome_g.strip()}" if minore else "") + \
          (f" · Motivo: {motivo.strip()[:300]}" if motivo.strip() else "")
    ok, mot, url = crea_e_invia(conn, pid, doc, email.strip().lower(), "primo_contatto", rif.strip(" ·"))
    _invia(email_studio(), f"[Primo contatto] {cognome.strip().title()} {nome.strip().title()}",
           f"Nuovo contatto da pnev.it ({'nuovo paziente' if not esist else 'paziente già in anagrafica'}, ID {pid}).\n\n"
           f"{'Bambino/a' if minore else 'Persona'}: {nome.strip()} {cognome.strip()} · nato/a il {nascita:%d/%m/%Y}\n"
           + (f"Genitore: {nome_g.strip()} {cognome_g.strip()}\n" if minore else "")
           + f"Email: {email.strip()} · Telefono: {tel.strip()}\n"
           + (f"\nMotivo:\n{motivo.strip()}\n" if motivo.strip() else "")
           + f"\nLink firma privacy: {'inviato' if ok else 'NON inviato — ' + mot}")
    st.session_state["pc_fatto"] = True
    st.session_state["pc_url"] = url
    st.rerun()


# ── prova senza toccare i pazienti veri ───────────────────────────────

PROVA_COGNOME, PROVA_NOME = "PROVA", "FIRMA PRIVACY"


def _id_prova(conn, crea=False):
    r = _q(conn, "SELECT id FROM pazienti WHERE cognome=%s AND nome=%s ORDER BY id LIMIT 1",
           (PROVA_COGNOME, PROVA_NOME))
    if r:
        return int(r[0]["id"])
    if not crea:
        return None
    r, err = _esegui(conn, "INSERT INTO pazienti (cognome, nome, stato_paziente) VALUES (%s,%s,'PROVA') RETURNING id",
                     (PROVA_COGNOME, PROVA_NOME))
    if not r:
        raise RuntimeError(err)
    return int(r["id"])


def _render_prova(conn):
    st.markdown("---")
    with st.expander("🧪 Prova la firma (paziente di prova, i pazienti veri non vengono toccati)"):
        st.caption(f"Usa un paziente finto, «{PROVA_COGNOME} {PROVA_NOME}». Metti la TUA email, firma dal "
                   "telefono, poi torna qui: la riga deve passare tra le firmate e devono arrivarti due email "
                   "(la copia e l'avviso). Alla fine cancella tutto con il bottone in fondo.")
        c1, c2 = st.columns([3, 2])
        mail = c1.text_input("La tua email", key="prova_firma_mail")
        doc = c2.radio("Tipo", ["adulto", "minore"], horizontal=True, key="prova_firma_doc")
        if st.button("📧 Mandami il link di prova", key="prova_firma_invia", type="primary"):
            if "@" not in (mail or ""):
                st.error("Inserisci la tua email.")
            else:
                try:
                    pid = _id_prova(conn, crea=True)
                    ok, motivo, url = crea_e_invia(conn, pid, doc, mail.strip(), "studio", "PROVA")
                    (st.success if ok else st.error)(("Inviato: " if ok else "Non inviato: ") + motivo)
                    if url:
                        st.code(url, language=None)
                except Exception as e:
                    st.error(f"Paziente di prova non creato: {e}")
        pid = _id_prova(conn)
        if pid:
            r = _q(conn, "SELECT stato, firmata_il FROM privacy_richieste_firma WHERE paziente_id=%s ORDER BY id DESC LIMIT 1", (pid,))
            n = _q(conn, "SELECT COUNT(*) AS n FROM consensi_privacy WHERE paziente_id=%s", (pid,))
            if r:
                st.info(f"Ultima prova: **{r[0]['stato']}**"
                        + (f" il {r[0]['firmata_il']:%d/%m %H:%M}" if r[0].get("firmata_il") else "")
                        + f" · consensi archiviati per il paziente di prova: {n[0]['n'] if n else 0}")
            if st.button("🗑 Cancella tutti i dati di prova", key="prova_firma_pulisci"):
                for sql in ("DELETE FROM privacy_richieste_firma WHERE paziente_id=%s",
                            "DELETE FROM consensi_privacy WHERE paziente_id=%s",
                            "DELETE FROM documenti WHERE paziente_id=%s",
                            "DELETE FROM pazienti WHERE id=%s AND cognome='PROVA'"):
                    _esegui(conn, sql, (pid,))
                st.success("Dati di prova cancellati.")
                st.rerun()
