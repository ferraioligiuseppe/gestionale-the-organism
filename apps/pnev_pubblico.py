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
    page_title="MAPS-CLEAR · I miei progressi",
    page_icon="🎧",
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

def azione_registra(conn):
    nome = qp("nome")
    email = qp("email")
    if not nome or not email:
        st.error("Dati di registrazione incompleti (nome ed email sono obbligatori).")
        st.stop()

    utente_id = db.crea_utente(
        conn, nome=nome, email=email,
        eta=qp_int("eta"), mano=qp("mano"), gdpr=True,
    )

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
    data_str = ev["data_ora"].strftime("%d/%m/%Y") if ev.get("data_ora") else ""
    riga_meta = " · ".join(x for x in [ev.get("sede"), data_str] if x)
    if riga_meta:
        st.caption(f"📍 {riga_meta}")
    if ev.get("descrizione"):
        st.write(ev["descrizione"])

    st.divider()

    slot_scelto = None
    if ev.get("slot_abilitati"):
        st.markdown("### 🕐 Scegli l'orario")
        slots = slot_con_disponibilita(conn, ev)
        liberi = [s for s in slots if s["liberi"] > 0]
        if not liberi:
            st.warning(
                "Tutti gli orari sono al momento occupati. "
                "Scrivici a info@theorganism.com per essere messo in lista d'attesa."
            )
            st.stop()
        opzioni = {s["orario"].strftime("%H:%M"): s["orario"] for s in liberi}
        scelta_lbl = st.radio(
            "Orari disponibili", options=list(opzioni.keys()), horizontal=True,
        )
        slot_scelto = opzioni[scelta_lbl]
    else:
        if ev.get("data_ora"):
            st.info(f"Orario: **{ev['data_ora'].strftime('%H:%M')}**")

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
    c7, c8 = st.columns(2)
    email = c7.text_input("Email *")
    telefono = c8.text_input("Telefono *")

    st.markdown("### 🔒 Consensi")
    cons_privacy = st.checkbox(
        "Acconsento al trattamento dei dati personali del minore per le finalità dello "
        "screening scolastico, secondo l'informativa privacy dello Studio The Organism. *"
    )
    cons_contatto = st.checkbox(
        "Acconsento a essere ricontattato/a per comunicare l'esito e un eventuale approfondimento."
    )

    if st.button("✅ Confirma iscrizione", type="primary", use_container_width=True):
        obbligatori = [nome_b, cognome_b, nome_g, cognome_g, email, telefono]
        if not all((v or "").strip() for v in obbligatori):
            st.error("Compila tutti i campi obbligatori (*).")
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

        try:
            iscr = dbev.crea_iscrizione(
                conn, ev["id"],
                nome=nome_g, cognome=cognome_g, email=email, telefono=telefono,
                note=f"Bambino/a: {cognome_b.strip()} {nome_b.strip()} · Scuola: {scuola or '—'} {classe or ''}".strip(),
                consenso_privacy=cons_privacy, consenso_marketing=cons_contatto,
                sorgente="web_slot",
            )

            if slot_scelto:
                assegna_slot(conn, iscr["id"], slot_scelto)

            orario_evento = slot_scelto or ev["data_ora"]
            durata = ev.get("slot_durata_minuti") if slot_scelto else (ev.get("durata_minuti") or 15)
            titolo_cal = f"Screening — {cognome_b.strip()} {nome_b.strip()}"
            gcal_id = None
            if orario_evento:
                gcal_id = crea_evento_calendario(
                    titolo=titolo_cal,
                    inizio=orario_evento,
                    durata_minuti=int(durata or 15),
                    descrizione=(
                        f"Genitore: {cognome_g.strip()} {nome_g.strip()} · Tel: {telefono} · Email: {email}\n"
                        f"Scuola: {scuola or '—'} {classe or ''}"
                    ),
                )
            if gcal_id:
                salva_gcal_event_id(conn, iscr["id"], gcal_id)

            st.success("🎉 Iscrizione confermata!")
            if slot_scelto:
                st.markdown(f"**Il tuo appuntamento:** {slot_scelto.strftime('%d/%m/%Y alle %H:%M')}")
            st.info("Se hai domande scrivi a info@theorganism.com.")
            st.stop()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Errore durante l'iscrizione: {e}")


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
                     "richiedi un nuovo link scrivendo a info@theorganism.com.")
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
