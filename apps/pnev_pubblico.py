# -*- coding: utf-8 -*-
"""
pnev_pubblico.py — MILESTONE 3 + iscrizioni evento a slot
App Streamlit PUBBLICA per il percorso MAPS-CLEAR (pnev.it) e per le
iscrizioni pubbliche agli eventi (es. screening scolastico a fasce orarie).

Nessun login del gestionale: il paziente/genitore arriva qui dal file HTML
su pnev.it tramite parametri URL, oppure dal suo magic link.

Flussi (query params):
  ?azione=registra&nome=..&email=..&eta=..&mano=..&q1=..&...&q12=..
        → crea utente + salva baseline + genera magic link → mostra il link
  ?t=TOKEN
        → dashboard progressi del paziente
  ?t=TOKEN&azione=sessione&giorno=..&modalita=..&delay=..&orecchio=..
          &fpre=..&fpost=..&comfort=..&beneficio=..&note=..
        → salva la sessione del giorno → dashboard
  ?t=TOKEN&azione=orecchio&orecchio=R|L&li=..
        → salva orecchio dominante → dashboard
  ?t=TOKEN&azione=post&q1=..&...&q12=..
        → salva questionario finale → dashboard con report
  ?azione=iscrizione_evento&slug=SLUG
        → pagina pubblica di iscrizione a un evento (con scelta fascia
          oraria se l'evento la prevede) → crea l'iscrizione + l'evento
          sul Google Calendar dello studio

Deploy: seconda app su Streamlit Cloud, stesso repo, main file = pnev_pubblico.py,
secrets: DATABASE_URL (stessa stringa del gestionale), più — per le iscrizioni
evento — GOOGLE_SERVICE_ACCOUNT_JSON e GOOGLE_CALENDAR_ID.
"""

import os
import sys

import psycopg2
import streamlit as st

# L'app vive in apps/ (per non ereditare la cartella pages/ del gestionale):
# aggiungo la radice del repo al path per importare modules/
_RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RADICE not in sys.path:
    sys.path.insert(0, _RADICE)

from modules.pnev_pubblico import db_pnev_pubblico as db
from modules.pnev_pubblico import email_pnev_pubblico as mail

VERDE = "#1D6B44"

# URL pubblico di QUESTA app (per costruire il magic link assoluto nelle email).
# Sovrascrivibile dai secrets con APP_URL.
APP_URL_DEFAULT = "https://gestionale-the-organism-n77ucp3n4us2hmqke9ck7n.streamlit.app"


def _ora(dt):
    """Orario italiano. Gli eventi sono salvati come TIMESTAMPTZ e arrivano
    dal database in UTC: senza conversione un evento delle 19:00 compariva
    alle 17:00 (le 19 meno le due ore dell'ora legale)."""
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        try:
            from zoneinfo import ZoneInfo
            return dt.astimezone(ZoneInfo("Europe/Rome"))
        except Exception:
            return dt
    return dt


def app_url():
    return st.secrets.get("APP_URL", APP_URL_DEFAULT).rstrip("/")


def link_assoluto(token):
    return f"{app_url()}/?t={token}"


def invia_email_sicura(funzione, *args):
    """Invia senza mai bloccare il flusso: se Brevo non è configurato o fallisce,
    l'app continua (il link resta visibile a schermo). Ritorna (ok, dettaglio)."""
    api_key = st.secrets.get("BREVO_API_KEY")
    mitt_email = st.secrets.get("MITTENTE_EMAIL")
    mitt_nome = st.secrets.get("MITTENTE_NOME", "Studio The Organism")
    if not api_key or not mitt_email:
        return False, "email non configurata (BREVO_API_KEY/MITTENTE_EMAIL mancanti)"
    return funzione(api_key, mitt_email, mitt_nome, *args)

st.set_page_config(
    page_title="Studio The Organism · PNEV",
    page_icon="🌿",
    layout="centered",
)

st.markdown(f"""
<style>
  .stApp {{ background: linear-gradient(135deg, {VERDE} 0%, #14533A 100%); }}
  .stApp, .stApp p, .stApp li, .stApp label {{ color: #fff; }}
  h1, h2, h3 {{ color: #fff !important; }}
  .block-container {{ max-width: 720px; }}
  div[data-testid="stMetric"] {{
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.20);
      border-radius: 14px; padding: 12px;
  }}
  div[data-testid="stMetric"] * {{ color: #fff !important; }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# CONNESSIONE (schema self-init a ogni avvio, idempotente)
# ═══════════════════════════════════════════════════════════════

def get_connection():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    with conn.cursor() as cur:
        cur.execute("SET app.current_studio = '1'")
    return conn


_schema_pronto = False


def _init_schema():
    """Crea lo schema una sola volta per processo (senza cache Streamlit)."""
    global _schema_pronto
    if _schema_pronto:
        return
    conn = get_connection()
    try:
        db.init_pnev_pubblico_db(conn)
    except Exception:
        # Deadlock/lock contention quando più ambienti (Streamlit Cloud + Render)
        # o più utenti aprono la pagina insieme: lo schema esiste già, quindi
        # non deve bloccare l'iscrizione.
        try: conn.rollback()
        except Exception: pass
    finally:
        conn.close()
    _schema_pronto = True


_init_schema()


# ═══════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════

def qp(nome, default=None):
    """Legge un query param come stringa (o default)."""
    v = st.query_params.get(nome, default)
    return v if v not in ("", None) else default


def qp_int(nome, default=None):
    v = qp(nome)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def leggi_questionario_da_url():
    """Raccoglie q1..q12 dai parametri. Ritorna dict (anche parziale) o None."""
    risposte = {}
    for i in range(1, 13):
        v = qp(f"q{i}")
        if v is not None:
            risposte[f"q{i}"] = v
    return risposte or None


def link_dashboard(token):
    """URL della dashboard con il token (l'app conosce il proprio indirizzo solo in modo relativo)."""
    return f"?t={token}"


# ═══════════════════════════════════════════════════════════════
# AZIONI (scrittura)
# ═══════════════════════════════════════════════════════════════

def _client_ip():
    """Recupera l'IP del client dagli header del proxy (Render/Streamlit Cloud).
    Best-effort: se non disponibile ritorna stringa vuota."""
    try:
        headers = st.context.headers
        fwd = headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
        return headers.get("X-Real-Ip", "") or ""
    except Exception:
        return ""


LIMITE_REGISTRAZIONI_IP_GIORNO = 3


def azione_registra(conn):
    nome = qp("nome")
    email = qp("email")
    if not nome or not email:
        st.error("Dati di registrazione incompleti (nome ed email sono obbligatori).")
        st.stop()

    ip = _client_ip()
    if ip and db.conta_registrazioni_ip_oggi(conn, ip) >= LIMITE_REGISTRAZIONI_IP_GIORNO:
        st.error("Hai già raggiunto il numero massimo di registrazioni da questa rete oggi. "
                 "Se hai bisogno di più accessi, scrivi a apstheorganism@gmail.com.")
        st.stop()

    utente_id = db.crea_utente(
        conn, nome=nome, email=email,
        eta=qp_int("eta"), mano=qp("mano"), gdpr=True,
    )
    if ip:
        db.registra_ip(conn, ip)

    risposte = leggi_questionario_da_url()
    if risposte:
        db.salva_questionario_pre(conn, utente_id, risposte)

    orecchio = qp("orecchio")
    if orecchio in ("R", "L"):
        li = qp("li")
        db.set_orecchio_dominante(conn, utente_id, orecchio,
                                  test_li=float(li) if li else None)

    token = db.crea_magic_link(conn, utente_id)

    ok_mail, dett = invia_email_sicura(mail.invia_magic_link, email, nome, link_assoluto(token))

    st.success(f"Benvenuto/a, {nome}! I tuoi progressi ora vengono salvati. 🎉")
    if ok_mail:
        st.info(f"📧 Ti abbiamo inviato il tuo link personale via email a **{email}**. "
                "Controlla anche la posta indesiderata!")
    st.markdown("### 🔑 Il tuo link personale")
    st.markdown(
        "Salvalo nei **preferiti** o copialo in un posto sicuro: "
        "ti fa rientrare nei tuoi progressi da **qualsiasi dispositivo**, senza password."
    )
    st.code(link_dashboard(token), language=None)
    st.caption("Il link vale per tutta la durata del percorso (9 giorni).")

    # Ritorno al file del percorso su pnev.it: gli passiamo il token
    # così il salvataggio si attiva da solo (?t=TOKEN letto al caricamento)
    ritorno = qp("ritorno")
    if ritorno and ritorno.startswith("https://"):
        sep = "&" if "?" in ritorno else "?"
        st.link_button("↩ Torna al percorso e collega il salvataggio",
                       f"{ritorno}{sep}t={token}", type="primary")
    st.link_button("📊 Vai ai miei progressi", link_dashboard(token))
    st.stop()


def azione_orecchio(conn, utente_id):
    orecchio = qp("orecchio")
    if orecchio in ("R", "L"):
        li = qp("li")
        db.set_orecchio_dominante(conn, utente_id, orecchio,
                                  test_li=float(li) if li else None)
        st.toast("Orecchio dominante salvato ✅")


def azione_sessione(conn, utente_id):
    giorno = qp_int("giorno")
    if not giorno:
        st.error("Sessione senza numero di giorno: non posso salvarla.")
        return
    _, stato = db.salva_sessione(
        conn, utente_id,
        giorno=giorno,
        modalita=qp("modalita"),
        delay_ms=qp_int("delay"),
        orecchio=qp("orecchio"),
        fluency_pre=qp_int("fpre"),
        fluency_post=qp_int("fpost"),
        comfort=qp_int("comfort"),
        beneficio=qp_int("beneficio"),
        note=qp("note"),
    )
    st.toast(f"Sessione del giorno {giorno} salvata ✅")
    if stato == "completato":
        u = db.get_utente_by_id(conn, utente_id)
        token = qp("t")
        if u and token:
            invia_email_sicura(mail.invia_completamento, u[2], u[1], link_assoluto(token))


def azione_post(conn, utente_id):
    risposte = leggi_questionario_da_url()
    if risposte:
        db.salva_questionario_post(conn, utente_id, risposte)
        st.toast("Questionario finale salvato ✅")


# ═══════════════════════════════════════════════════════════════
# ISCRIZIONE PUBBLICA A EVENTI (con fasce orarie + Google Calendar)
# ═══════════════════════════════════════════════════════════════

def azione_iscrizione_evento(conn):
    from modules.eventi import db_eventi as dbev
    from modules.eventi.slots import (
        ensure_slot_schema, slot_con_disponibilita, assegna_slot, salva_gcal_event_id,
    )
    from modules.eventi.google_calendar import crea_evento_calendario

    slug = qp("slug")
    if not slug:
        st.error("Link non valido: evento non specificato.")
        st.stop()

    try:
        ensure_slot_schema(conn)
    except Exception:
        pass

    ev = dbev.get_evento_by_slug(conn, slug)
    if not ev or not ev.get("attivo"):
        st.error("Evento non trovato o non più disponibile.")
        st.stop()
    if not ev.get("iscrizioni_aperte"):
        st.warning("Le iscrizioni a questo evento sono chiuse.")
        st.stop()

    st.title(f"📋 {ev['titolo']}")
    data_str = _ora(ev["data_ora"]).strftime("%d/%m/%Y") if ev.get("data_ora") else ""
    riga_meta = " · ".join(x for x in [ev.get("sede"), data_str] if x)
    if riga_meta:
        st.caption(f"📍 {riga_meta}")
    if ev.get("descrizione"):
        st.write(ev["descrizione"])

    st.divider()

    slot_scelto = None
    opzioni_slot = None
    if ev.get("slot_abilitati"):
        slots = slot_con_disponibilita(conn, ev)
        liberi = [s for s in slots if s["liberi"] > 0]
        if not liberi:
            st.warning(
                "Tutti gli orari sono al momento occupati. "
                "Scrivici a apstheorganism@gmail.com per essere messo in lista d'attesa."
            )
            st.stop()
        opzioni_slot = {_ora(s["orario"]).strftime("%H:%M"): s["orario"] for s in liberi}
    else:
        if ev.get("data_ora"):
            st.info(f"Orario: **{_ora(ev['data_ora']).strftime('%H:%M')}**")

    # Tutto dentro un form: Streamlit NON ricarica la pagina ad ogni campo
    # compilato (prima ogni uscita da un campo rifaceva le query su evento e
    # slot, dando l'impressione di un errore/blocco).
    # Tipo di evento: per minori (screening scolastico, giornata del bambino) oppure
    # per adulti (costellazioni familiari, incontri, corsi). Determina le etichette
    # del form e il testo dei consensi.
    # Si decide dal TIPO dell'evento impostato nel gestionale: è un dato
    # esplicito, non un indovinello sul titolo. Solo per i tipi generici
    # ("altro", o tipo mancante sui vecchi eventi) si ripiega sulle parole
    # chiave del titolo/descrizione.
    _tipo_ev = (ev.get("tipo") or "").strip().lower()
    if _tipo_ev == "screening":
        evento_minori = True
    elif _tipo_ev in ("costellazioni", "webinar", "workshop"):
        evento_minori = False
    else:
        _testo_ev = f"{ev.get('titolo','')} {ev.get('descrizione','') or ''}".lower()
        _kw_minori = ("bambin", "screening", "scolastic", "pediatr", "infanzia", "ragazz")
        _kw_adulti = ("costellazion", "adulti", "genitori", "corso", "formazione", "serata")
        evento_minori = (any(k in _testo_ev for k in _kw_minori)
                         and not any(k in _testo_ev for k in _kw_adulti))

    with st.form("iscrizione_evento_form"):
        if opzioni_slot:
            st.markdown("### 🕐 Scegli l'orario")
            scelta_lbl = st.radio(
                "Orari disponibili", options=list(opzioni_slot.keys()), horizontal=True,
            )
            slot_scelto = opzioni_slot[scelta_lbl]

        if evento_minori:
            st.markdown("### 👦 Dati del bambino/a")
            c1, c2 = st.columns(2)
            nome_b = c1.text_input("Nome bambino/a *")
            cognome_b = c2.text_input("Cognome bambino/a *")
            c3, c4 = st.columns(2)
            scuola = c3.text_input("Scuola")
            classe = c4.text_input("Classe")

            st.markdown("### 👤 Dati del genitore/tutore")
            c5, c6 = st.columns(2)
            nome_g = c5.text_input("Nome genitore *")
            cognome_g = c6.text_input("Cognome genitore *")
        else:
            st.markdown("### 👤 I tuoi dati")
            c5, c6 = st.columns(2)
            nome_g = c5.text_input("Nome *")
            cognome_g = c6.text_input("Cognome *")
            nome_b = cognome_b = scuola = classe = ""

        c7, c8 = st.columns(2)
        email = c7.text_input("Email *")
        telefono = c8.text_input("Telefono *")

        st.markdown("### 🔒 Consensi")
        cons_privacy = st.checkbox(
            ("Acconsento al trattamento dei dati personali del minore per le finalità dello "
             "screening scolastico, secondo l'informativa privacy dello Studio The Organism. *")
            if evento_minori else
            ("Acconsento al trattamento dei miei dati personali per le finalità di questo "
             "incontro, secondo l'informativa privacy dello Studio The Organism. *")
        )
        st.caption("Dopo l'iscrizione ti mandiamo per email il link per firmare il consenso "
                   "privacy completo: ci vogliono due minuti dal telefono.")
        cons_contatto = st.checkbox(
            "Acconsento a essere ricontattato/a per comunicare l'esito e un eventuale approfondimento."
            if evento_minori else
            "Acconsento a essere ricontattato/a per informazioni sulle attività dello Studio."
        )

        inviato = st.form_submit_button("✅ Conferma iscrizione", type="primary",
                                         use_container_width=True)

    if inviato:
        campi = {
            "Nome": nome_g, "Cognome": cognome_g,
            "Email": email, "Telefono": telefono,
        }
        if evento_minori:
            campi = {"Nome bambino/a": nome_b, "Cognome bambino/a": cognome_b, **campi}
        mancanti = [etichetta for etichetta, valore in campi.items() if not (valore or "").strip()]
        if mancanti:
            st.error("Mancano questi campi obbligatori: **" + ", ".join(mancanti) + "**. "
                     "Se il testo appare già scritto in grigio, è il completamento automatico del "
                     "browser: clicca nel campo e riscrivilo a mano.")
            st.stop()
        if "@" not in (email or ""):
            st.error("Email non valida.")
            st.stop()
        if not cons_privacy:
            st.error("Il consenso privacy è obbligatorio.")
            st.stop()
        if ev.get("slot_abilitati") and not slot_scelto:
            st.error("Seleziona un orario.")
            st.stop()

        # Ricontrollo disponibilità (anti doppia prenotazione last-minute)
        if slot_scelto:
            from modules.eventi.slots import posti_occupati_slot
            occ = posti_occupati_slot(conn, ev["id"], slot_scelto)
            if occ >= int(ev.get("slot_posti") or 1):
                st.error("Questo orario è appena stato prenotato da un'altra persona. Ricarica la pagina e scegline un altro.")
                st.stop()

        # Avviso non bloccante: stessa email già usata per un altro bambino a questo evento
        from modules.eventi.db_eventi import email_gia_iscritta
        if email_gia_iscritta(conn, ev["id"], email):
            st.info("ℹ️ Con questa email hai già iscritto un altro bambino/a a questo evento — va bene, "
                     "l'iscrizione di un fratello/sorella diverso procede comunque.")

        try:
            with st.spinner("Stiamo confermando la tua iscrizione, un attimo…"):
                iscr = dbev.crea_iscrizione(
                    conn, ev["id"],
                    nome=nome_g, cognome=cognome_g, email=email, telefono=telefono,
                    note=(f"Bambino/a: {cognome_b.strip()} {nome_b.strip()} · Scuola: {scuola or '—'} {classe or ''}".strip()
                          if evento_minori else ""),
                    consenso_privacy=cons_privacy, consenso_marketing=cons_contatto,
                    sorgente="web_slot",
                )

                if slot_scelto:
                    assegna_slot(conn, iscr["id"], slot_scelto)

                orario_evento = slot_scelto or ev["data_ora"]
                durata = ev.get("slot_durata_minuti") if slot_scelto else (ev.get("durata_minuti") or 15)
                titolo_cal = (f"Screening — {cognome_b.strip()} {nome_b.strip()}" if evento_minori
                              else f"{ev['titolo']} — {cognome_g.strip()} {nome_g.strip()}")
                gcal_id = None
                if orario_evento:
                    gcal_id = crea_evento_calendario(
                        titolo=titolo_cal,
                        inizio=orario_evento,
                        durata_minuti=int(durata or 15),
                        descrizione=(
                            f"Genitore: {cognome_g.strip()} {nome_g.strip()} · Tel: {telefono} · Email: {email}\n"
                            + (f"Scuola: {scuola or '—'} {classe or ''}" if evento_minori else "")
                        ),
                    )
                if gcal_id:
                    salva_gcal_event_id(conn, iscr["id"], gcal_id)

                firma_url = ""
                # Anagrafica automatica: crea il paziente se non esiste già
                # (match su email o su cognome+nome del bambino), senza intervento manuale.
                try:
                    cur_an = conn.cursor()
                    cog_b = (cognome_b if evento_minori else cognome_g).strip().upper()
                    nom_b = (nome_b if evento_minori else nome_g).strip().upper()
                    # Match sul NOME della persona iscritta, non sull'email.
                    # Con l'email nella condizione OR, un genitore che iscrive
                    # il secondo figlio con lo stesso indirizzo agganciava la
                    # nuova iscrizione all'anagrafica del PRIMO figlio: due
                    # bambini diversi sullo stesso fascicolo. La pagina avvisa
                    # gia' che l'iscrizione di un fratello e' legittima, ma poi
                    # i dati finivano nel posto sbagliato. Nella scheda manuale
                    # del gestionale il match e' sempre stato su cognome+nome:
                    # ora le due strade si comportano allo stesso modo.
                    cur_an.execute(
                        "SELECT id FROM pazienti WHERE UPPER(cognome)=%s AND UPPER(nome)=%s LIMIT 1",
                        (cog_b, nom_b))
                    esistente = cur_an.fetchone()
                    if esistente:
                        paz_auto_id = int(esistente["id"] if isinstance(esistente, dict) else esistente[0])
                    else:
                        cur_an.execute(
                            "INSERT INTO pazienti (cognome, nome, telefono, email, stato_paziente) "
                            "VALUES (%s,%s,%s,%s,'ATTIVO') RETURNING id",
                            (cog_b, nom_b, telefono or None, email.strip().lower() or None))
                        r_new = cur_an.fetchone()
                        paz_auto_id = int(r_new["id"] if isinstance(r_new, dict) else r_new[0])
                        # Qui prima si registrava un consenso «firmato» che nessuno
                        # aveva firmato: era solo la casella del modulo. Ora parte
                        # la richiesta di firma vera (sotto).
                    conn.commit()
                    try:
                        from modules.eventi.db_eventi import aggancia_paziente
                        aggancia_paziente(conn, iscr["id"], paz_auto_id)
                    except Exception:
                        pass
                    # Firma della privacy: link per email, salvo che abbia gia'
                    # firmato online. Se a questa app mancano i secrets [privacy],
                    # la richiesta resta «da inviare» nel gestionale (Firme
                    # privacy in attesa) e si manda da li' con un clic.
                    try:
                        from modules.privacy import firma_remota as fr
                        _doc = "minore" if evento_minori else "adulto"
                        if not fr.gia_firmato(conn, paz_auto_id, _doc):
                            _ok_f, _mot_f, firma_url = fr.crea_e_invia(
                                conn, paz_auto_id, _doc, email.strip().lower(), "evento",
                                f"Evento: {ev['titolo']}")
                    except Exception:
                        try: conn.rollback()
                        except Exception: pass
                except Exception as _e_anag:
                    try: conn.rollback()
                    except Exception: pass
                    st.caption(f"⚠️ Anagrafica non creata automaticamente: {_e_anag}")

                # Email di conferma al genitore (non bloccante se fallisce)
                stato_iscr = iscr.get("stato", "confermata")
                try:
                    from modules.email_otp import invia_email
                    if stato_iscr == "lista_attesa":
                        corpo_email = (
                            f"Ciao {nome_g.strip()},\n\n"
                            f"la tua iscrizione a \"{ev['titolo']}\""
                            + (f" per {nome_b.strip()} {cognome_b.strip()}" if evento_minori else "")
                            + " è stata registrata in LISTA D'ATTESA (i posti disponibili sono terminati).\n"
                            "Ti contatteremo se si libera un posto.\n"
                        )
                    else:
                        corpo_email = (
                            f"Ciao {nome_g.strip()},\n\n"
                            f"la tua iscrizione a \"{ev['titolo']}\""
                            + (f" per {nome_b.strip()} {cognome_b.strip()}" if evento_minori else "")
                            + " è confermata.\n"
                        )
                    if slot_scelto:
                        corpo_email += f"Appuntamento: {_ora(slot_scelto).strftime('%d/%m/%Y alle %H:%M')}\n"
                    elif ev.get("data_ora"):
                        corpo_email += f"Data: {_ora(ev['data_ora']).strftime('%d/%m/%Y alle %H:%M')}\n"
                    if ev.get("sede"):
                        corpo_email += f"Sede: {ev['sede']}\n"
                    corpo_email += "\nPer qualsiasi domanda scrivi a apstheorganism@gmail.com.\n\nStudio The Organism"
                    oggetto_genitore = (
                        f"Sei in lista d'attesa — {ev['titolo']}" if stato_iscr == "lista_attesa"
                        else f"Iscrizione confermata — {ev['titolo']}"
                    )
                    # Stessa configurazione delle altre email degli eventi, con
                    # copia nascosta allo studio; ogni tentativo va nel registro,
                    # così nel gestionale si vede a chi è arrivata e a chi no.
                    try:
                        from modules.eventi.email_eventi import invia_testo
                        ok_m, dett_m = invia_testo(email.strip(), oggetto_genitore, corpo_email)
                    except Exception:
                        ok_m, dett_m = invia_email(email.strip(), oggetto_genitore, corpo_email,
                                                   dettaglio=True)
                    try:
                        from modules.eventi.db_eventi import registra_email
                        registra_email(conn, ev["id"], iscr["id"], "conferma", email.strip(),
                                       oggetto_genitore, ok_m, dett_m, "iscrizione online")
                    except Exception:
                        pass
                    if ok_m:
                        # Senza questo la colonna "Email conferma" nel gestionale
                        # resta "—" anche quando la mail e' partita davvero: veniva
                        # marcata solo dall'invio manuale dal pannello admin.
                        try:
                            from modules.eventi.db_eventi import mark_email_conferma_inviata
                            mark_email_conferma_inviata(conn, iscr["id"])
                        except Exception:
                            pass
                    else:
                        st.warning(f"Iscrizione salvata, ma l'email di conferma non è partita: {dett_m}")
                except Exception as _e_mail:
                    st.warning(f"Iscrizione salvata, ma l'email di conferma non è partita: {_e_mail}")

                # Notifica interna allo studio, ad ogni iscrizione (confermata o lista d'attesa)
                try:
                    from modules.email_otp import invia_email
                    riga_slot = (
                        f"Slot: {_ora(slot_scelto).strftime('%d/%m/%Y alle %H:%M')}\n" if slot_scelto
                        else (f"Data: {_ora(ev['data_ora']).strftime('%d/%m/%Y alle %H:%M')}\n" if ev.get("data_ora") else "")
                    )
                    corpo_staff = (
                        f"Nuova iscrizione — stato: {stato_iscr.upper()}\n\n"
                        f"Evento: {ev['titolo']}\n"
                        f"{riga_slot}"
                        f"Genitore: {cognome_g.strip()} {nome_g.strip()} · Tel: {telefono} · Email: {email}\n"
                        + (f"Bambino/a: {nome_b.strip()} {cognome_b.strip()}\n"
                           f"Scuola: {scuola or '—'} {classe or ''}" if evento_minori else "")
                    )
                    oggetto_staff = (
                        f"[Lista attesa] {ev['titolo']}" if stato_iscr == "lista_attesa"
                        else f"[Iscrizione] {ev['titolo']}"
                    )
                    for dest in ("dr.ferraioligiuseppe@gmail.com",):
                        try:
                            ok_s, dett_s = invia_email(dest, oggetto_staff, corpo_staff, dettaglio=True)
                            if not ok_s:
                                st.caption(f"Notifica interna a {dest} non inviata: {dett_s}")
                        except Exception as _e_staff:
                            st.caption(f"Notifica interna a {dest} non inviata: {_e_staff}")
                except Exception:
                    pass

            st.success("🎉 Iscrizione confermata!")
            if slot_scelto:
                st.markdown(f"**Il tuo appuntamento:** {_ora(slot_scelto).strftime('%d/%m/%Y alle %H:%M')}")
            st.info("Ti abbiamo inviato una email di conferma. Se non arriva controlla anche lo spam, oppure scrivi a apstheorganism@gmail.com.")
            if firma_url:
                st.markdown("**Ultimo passo: il consenso privacy.** Puoi firmarlo adesso o dal link che ti abbiamo mandato per email.")
                st.link_button("✍️ Firma ora il consenso privacy", firma_url, type="primary",
                               use_container_width=True)
            st.stop()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Errore durante l'iscrizione: {e}")


# ═══════════════════════════════════════════════════════════════
# OFFERTE STANZA DEL SALE (Aerosal) — pagina per www.pnev.it
# ═══════════════════════════════════════════════════════════════

def _euro(v):
    try:
        return f"€ {float(v):,.0f}".replace(",", ".")
    except Exception:
        return ""


def azione_offerte_sale(conn):
    """Le offerte programmate nel gestionale (Aerosal → Offerte sul sito).
    Compaiono dal primo giorno di validita' e spariscono da sole alla
    scadenza o quando i pacchetti disponibili sono finiti."""
    from html import escape
    from modules.aerosal import db_aerosal as dba
    studio = st.secrets.get("STUDIO_ID_AEROSAL") or None
    try:
        offerte = dba.offerte_pubbliche(conn, studio)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        offerte = []

    # Dentro la pagina di pnev.it: sfondo bianco e schede come quelle del sito,
    # non il verde delle altre pagine di questa app.
    st.markdown("""<style>
      .stApp{background:#fff!important}
      .stApp, .stApp p, .stApp li, .stApp label, .stApp div{color:#1F2A24}
      header, footer, [data-testid="stToolbar"]{display:none!important}
      .block-container{padding:8px 12px 16px!important;max-width:900px}
      a[data-testid="stBaseLinkButton-primary"]{background:#1D6B44!important;border:0!important;
        border-radius:6px!important;color:#fff!important}
      a[data-testid="stBaseLinkButton-primary"] *{color:#fff!important}
    </style>""", unsafe_allow_html=True)
    if not offerte:
        st.markdown('<div style="text-align:center;padding:18px;border:1px solid #D6E2DA;'
                    'border-radius:8px;font-size:15px">In questo momento non ci sono offerte attive. '
                    'Per informazioni sui pacchetti chiamaci allo 081 5152334.</div>',
                    unsafe_allow_html=True)
        st.stop()

    gruppi = {}
    for o in offerte:
        gruppi.setdefault(o.get("titolo_sito") or o.get("promo_nome") or "Offerta", []).append(o)

    for titolo, voci in gruppi.items():
        testo = next((v.get("testo_sito") for v in voci if v.get("testo_sito")), "")
        fine = max((v["valido_al"] for v in voci if v.get("valido_al")), default=None)
        schede = ""
        for v in voci:
            pieno = v.get("prezzo_pieno_rif")
            barrato = (f'<span style="text-decoration:line-through;color:#7A857E;font-size:15px">'
                       f'{_euro(pieno)}</span> ') if pieno and float(pieno) > float(v["prezzo"]) else ""
            resto = ""
            if v.get("limite_pacchetti"):
                n = int(v["limite_pacchetti"]) - int(v.get("vendute") or 0)
                resto = (f'<div style="font-size:13px;margin-top:6px;color:#1D6B44;font-weight:600">'
                         f'{"ultimo pacchetto" if n == 1 else f"ancora {n} pacchetti"} disponibili</div>')
            schede += (
                '<div style="flex:1 1 180px;background:#fff;text-align:center;'
                'border:1px solid #D6E2DA;border-radius:8px;padding:16px 18px">'
                f'<div style="font-size:15px;font-weight:700;color:#155235">{int(v["n_sedute"])} sedute</div>'
                f'<div style="margin-top:6px">{barrato}<span style="font-size:26px;font-weight:700;color:#1F2A24">'
                f'{_euro(v["prezzo"])}</span></div>{resto}</div>')
        st.markdown(
            f'<div style="margin:18px 0 26px">'
            f'<div style="text-align:center;font-size:18px;font-weight:700;color:#155235;margin:0 0 6px">{escape(titolo)}</div>'
            + (f'<p style="text-align:center;margin:0 0 12px;color:#4E5A53">{escape(testo)}</p>' if testo else "")
            + f'<div style="display:flex;flex-wrap:wrap;gap:12px">{schede}</div>'
            + (f'<div style="text-align:center;font-size:13px;margin-top:10px;color:#4E5A53">Offerta valida fino al '
               f'{fine:%d/%m/%Y}</div>' if fine else "")
            + '</div>', unsafe_allow_html=True)

    st.link_button("📞 Chiama per prenotare · 081 5152334", "tel:+390815152334",
                   type="primary", use_container_width=True)
    st.stop()


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def mostra_dashboard(conn, utente_id):
    u = db.get_utente_by_id(conn, utente_id)
    if not u:
        st.error("Utente non trovato.")
        st.stop()

    # get_utente_by_id: id, nome, email, eta, mano, gdpr, creato_il,
    #                   orecchio, test_li, test_dettaglio, giorno, stato
    nome, orecchio, giorno_corr, stato = u[1], u[7], u[10], u[11]

    st.title("🎧 MAPS-CLEAR")
    st.markdown(f"### Ciao, {nome}!")

    sessioni = db.get_sessioni(conn, utente_id)
    fatte = len(sessioni)

    c1, c2, c3 = st.columns(3)
    c1.metric("Giorni completati", f"{fatte} / 7")
    c2.metric("Orecchio", "Destro" if orecchio == "R" else
              ("Sinistro" if orecchio == "L" else "—"))
    if sessioni:
        deltas = [s[7] - s[6] for s in sessioni
                  if s[6] is not None and s[7] is not None]
        media = sum(deltas) / len(deltas) if deltas else 0
        c3.metric("Fluenza media", f"{'+' if media >= 0 else ''}{media:.1f}",
                  help="Differenza media tra auto-valutazione dopo e prima di ogni sessione (scala 1-10)")
    else:
        c3.metric("Fluenza media", "—")

    # barra dei 7 giorni
    giorni_fatti = {s[1] for s in sessioni}
    riga = " ".join("🟢" if g in giorni_fatti else "⚪" for g in range(1, 8))
    st.markdown(f"**Il tuo percorso:** {riga}")

    if stato == "completato":
        st.success("🏆 Percorso completato! Complimenti per la costanza.")

    if sessioni:
        st.markdown("### 📈 Andamento della fluenza")
        dati = {
            "Prima della sessione": [s[6] for s in sessioni],
            "Dopo la sessione": [s[7] for s in sessioni],
        }
        st.line_chart(dati, height=260)

        st.markdown("### 📋 Le tue sessioni")
        for s in sessioni:
            _, g, data_s, modalita, delay, orec, fpre, fpost, comfort, beneficio, note, _ = s
            delta = (fpost - fpre) if (fpre is not None and fpost is not None) else None
            freccia = "" if delta is None else (f" · {'▲' if delta > 0 else ('▼' if delta < 0 else '＝')} {delta:+d}")
            with st.expander(f"Giorno {g} — {modalita or '—'} ({delay or '—'} ms){freccia}"):
                st.write(f"**Data:** {data_s:%d/%m/%Y %H:%M}")
                st.write(f"**Fluenza:** prima {fpre}/10 → dopo {fpost}/10")
                st.write(f"**Comfort:** {comfort}/10 · **Beneficio percepito:** {beneficio}/10")
                if note:
                    st.write(f"**Note:** {note}")
    else:
        st.info("Nessuna sessione ancora salvata. Completa la prima sessione su pnev.it "
                "e premi «Salva i miei progressi».")

    quest = db.get_questionari(conn, utente_id)
    if quest["pre"] and quest["post"]:
        st.markdown("### 🔍 Prima e dopo")
        st.caption("Confronto tra il questionario iniziale e quello finale.")
        pre, post = quest["pre"][0], quest["post"][0]
        for chiave in ("q1", "q2", "q3"):
            if chiave in pre and chiave in post:
                try:
                    v_pre, v_post = int(pre[chiave]), int(post[chiave])
                    st.write(f"**{chiave.upper()}**: {v_pre} → {v_post} "
                             f"({'migliorato ✅' if v_post < v_pre else ('invariato' if v_post == v_pre else 'peggiorato')})")
                except (ValueError, TypeError):
                    pass

    st.divider()
    st.caption("MAPS-CLEAR · Studio The Organism · Dott. Giuseppe Ferraioli — "
               "Pagani · Piano di Sorrento · [pnev.it](https://www.pnev.it)")


# ═══════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════

def main():
    azione = qp("azione")
    token = qp("t")

    conn = get_connection()
    try:
        # 0. Iscrizione pubblica a evento (non richiede token né login)
        if azione == "iscrizione_evento":
            azione_iscrizione_evento(conn)
            return

        if azione == "offerte_sale":
            azione_offerte_sale(conn)
            return

        # 1. Registrazione (non richiede token)
        if azione == "registra":
            azione_registra(conn)
            return

        # 2. Tutto il resto richiede il magic link
        if not token:
            st.title("🎧 MAPS-CLEAR")
            st.markdown(
                "Questa è l'area personale del percorso **MAPS-CLEAR — 7 giorni per parlare chiaro**.\n\n"
                "Per accedere ai tuoi progressi usa il **link personale** che hai ricevuto "
                "al momento della registrazione.\n\n"
                "Non sei ancora iscritto? Il percorso gratuito parte da "
                "[pnev.it](https://www.pnev.it)."
            )
            st.stop()

        utente_id = db.valida_magic_link(conn, token)
        if not utente_id:
            st.error("Link non valido o scaduto. Se il tuo percorso è ancora in corso, "
                     "richiedi un nuovo link scrivendo a apstheorganism@gmail.com.")
            st.stop()

        # 3. Azioni di salvataggio prima della dashboard
        if azione == "sessione":
            azione_sessione(conn, utente_id)
        elif azione == "orecchio":
            azione_orecchio(conn, utente_id)
        elif azione == "post":
            azione_post(conn, utente_id)

        mostra_dashboard(conn, utente_id)
    finally:
        conn.close()


main()
