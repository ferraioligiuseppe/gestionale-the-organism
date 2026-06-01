# -*- coding: utf-8 -*-
# pages/iscrizione_evento.py
#
# Pagina PUBBLICA di iscrizione a un evento.
# URL: https://testgestionale.streamlit.app/iscrizione_evento?slug=...
#
# Non richiede login. Mostra dettagli evento, form iscrizione,
# crea record, genera PDF, invia email di conferma + notifica studio.

import streamlit as st
import sys, os
import logging
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(
    page_title="Iscrizione evento — Studio The Organism",
    page_icon="📅",
    layout="centered",
)

logger = logging.getLogger(__name__)
ROME_TZ = ZoneInfo("Europe/Rome")

# =============================================================================
# CSS / HEADER pubblico (no sidebar gestionale)
# =============================================================================

st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    .main .block-container { max-width: 720px; }
    .ev-header {
        background: linear-gradient(135deg, #1D6B44, #2A8B5C);
        color: white; padding: 28px 24px; border-radius: 12px;
        margin-bottom: 24px;
    }
    .ev-header h1 { color: white; margin: 0 0 8px 0; font-size: 1.6rem; }
    .ev-header .meta { opacity: 0.92; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# LETTURA SLUG DA QUERY PARAM
# =============================================================================

qp = st.query_params
slug = qp.get("slug", "")
if isinstance(slug, list):
    slug = slug[0] if slug else ""

if not slug:
    st.error("⚠️ Link non valido: manca il parametro `slug`.")
    st.info("Apri il link completo che ti è stato inviato.")
    st.stop()


# =============================================================================
# CONNESSIONE DB + RECUPERO EVENTO
# =============================================================================

try:
    from modules.app_core import get_connection
    from modules.eventi.db_eventi import (
        get_evento_by_slug,
        crea_iscrizione,
        email_gia_iscritta,
        posti_rimasti,
        mark_email_conferma_inviata,
    )
    from modules.eventi.pdf_evento import genera_pdf_conferma
    from modules.eventi.email_eventi import (
        invia_conferma_iscritto,
        invia_notifica_studio,
    )
    conn = get_connection()
except Exception as e:
    st.error(f"Errore di sistema: {e}")
    logger.error("Init failed", exc_info=True)
    st.stop()

try:
    evento = get_evento_by_slug(conn, slug)
except Exception as e:
    st.error(f"Errore caricamento evento: {e}")
    st.stop()

if not evento:
    st.error("❌ Evento non trovato.")
    st.info("Il link potrebbe essere scaduto. Contatta lo Studio per maggiori informazioni.")
    st.stop()

if not evento.get("attivo"):
    st.warning("⚠️ Questo evento non è più disponibile.")
    st.stop()


# =============================================================================
# RENDER DETTAGLI EVENTO
# =============================================================================

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _format_data_ora(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(ROME_TZ)
    g = GIORNI[dt.weekday()]
    return f"{g} {dt.day} {MESI[dt.month - 1]} {dt.year} · ore {dt.strftime('%H:%M')}"


data_str = _format_data_ora(evento["data_ora"])

# Header con titolo evento
meta_parts = [f"📅 {data_str}"]
if evento.get("sede"):
    meta_parts.append(f"📍 {evento['sede']}")
if evento.get("conduttore"):
    meta_parts.append(f"👤 {evento['conduttore']}")

st.markdown(
    f"""
    <div class="ev-header">
        <h1>{evento.get('titolo', '')}</h1>
        <div class="meta">{' · '.join(meta_parts)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if evento.get("immagine_url"):
    try:
        st.image(evento["immagine_url"], use_container_width=True)
    except Exception:
        pass

if evento.get("descrizione"):
    st.markdown(evento["descrizione"])

# Riepilogo veloce
info_extra = []
if evento.get("durata_minuti"):
    info_extra.append(f"⏱️ Durata: {evento['durata_minuti']} minuti")
if evento.get("prezzo") is not None and float(evento["prezzo"]) > 0:
    info_extra.append(f"💶 Contributo: € {float(evento['prezzo']):.2f}")
if info_extra:
    st.info(" · ".join(info_extra))

# Posti disponibili / sold out
rimasti = posti_rimasti(conn, evento["id"])
if evento.get("posti_max"):
    if rimasti is None or rimasti > 0:
        st.success(f"✅ Posti disponibili: **{rimasti}** su {evento['posti_max']}")
    else:
        st.warning(
            f"⚠️ Posti esauriti ({evento['posti_max']} su {evento['posti_max']}). "
            "Puoi comunque iscriverti in **lista d'attesa**."
        )

# Iscrizioni chiuse?
if not evento.get("iscrizioni_aperte"):
    st.error("🔒 Le iscrizioni a questo evento sono chiuse.")
    st.stop()

st.divider()


# =============================================================================
# FORM ISCRIZIONE
# =============================================================================

# Se appena inviato con successo, mostra schermata "grazie" invece del form
if st.session_state.get("ev_iscrizione_completata", {}).get("slug") == slug:
    dati = st.session_state["ev_iscrizione_completata"]
    st.markdown("## ✅ Iscrizione registrata!")
    stato = dati.get("stato", "confermata")
    if stato == "confermata":
        st.success(
            f"Grazie **{dati.get('nome', '')}**! La tua iscrizione è confermata.\n\n"
            f"Ti abbiamo inviato una email di conferma all'indirizzo "
            f"**{dati.get('email', '')}** con il PDF in allegato."
        )
    elif stato == "lista_attesa":
        st.warning(
            f"Grazie **{dati.get('nome', '')}**! L'evento è al completo, "
            f"quindi sei in **lista d'attesa**.\n\n"
            f"Ti contatteremo appena si libera un posto. Abbiamo inviato un PDF "
            f"all'indirizzo **{dati.get('email', '')}**."
        )

    if dati.get("email_problema"):
        st.warning(
            f"⚠️ Non siamo riusciti a inviarti l'email di conferma "
            f"(causa: {dati['email_problema']}). "
            f"La tua iscrizione è comunque registrata regolarmente. "
            f"Per ricevere il PDF contatta lo Studio."
        )

    st.info(
        "**Cosa fare ora?**  \n"
        f"📅 Salva la data: {data_str}  \n"
        + (f"📍 Sede: {evento['sede']}  \n" if evento.get("sede") else "")
        + "📧 Per qualsiasi necessità rispondi all'email di conferma."
    )

    if st.button("← Nuova iscrizione"):
        del st.session_state["ev_iscrizione_completata"]
        st.rerun()
    st.stop()


st.markdown("## 📝 Iscriviti")

with st.form("form_iscrizione_pubblica"):
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome ✱", max_chars=100)
    with col2:
        cognome = st.text_input("Cognome ✱", max_chars=100)

    col3, col4 = st.columns(2)
    with col3:
        email = st.text_input("Email ✱", max_chars=200)
    with col4:
        telefono = st.text_input("Cellulare ✱", max_chars=50,
                                 placeholder="Es. 333 1234567")

    note = st.text_area("Note (opzionale)", max_chars=500, height=80,
                        placeholder="Eventuali necessità, allergie, richieste particolari...")

    st.markdown("---")
    st.markdown("### 🔒 Privacy")

    with st.expander("📖 Leggi l'informativa completa"):
        st.markdown("""
**Informativa ai sensi dell'art. 13 del Reg. UE 2016/679 (GDPR)**

**Titolare del trattamento**: Studio The Organism — Via De Rosa 46, 84016 Pagani (SA).

**Finalità del trattamento**: gestione dell'iscrizione all'evento, comunicazioni
organizzative correlate (conferme, promemoria, eventuali variazioni di sede/orario,
annullamenti), adempimento di obblighi di legge.

**Base giuridica**: esecuzione di un servizio richiesto dall'interessato (art. 6.1.b GDPR),
obblighi di legge (art. 6.1.c GDPR), consenso dell'interessato per le comunicazioni
informative (art. 6.1.a GDPR).

**Categorie di dati trattati**: dati identificativi (nome, cognome) e di contatto
(email, telefono). Eventuali ulteriori dati spontaneamente conferiti nel campo "Note".

**Modalità del trattamento**: i dati saranno trattati con strumenti elettronici e cartacei,
adottando misure di sicurezza adeguate. Non saranno diffusi né trasferiti fuori dall'UE.
Potranno essere comunicati a responsabili esterni (es. fornitore di servizi gestionali,
posta elettronica) ove necessario.

**Periodo di conservazione**: i dati relativi alla singola iscrizione saranno conservati
fino a 24 mesi dall'evento; in caso di consenso alle comunicazioni informative,
fino alla revoca del consenso.

**Diritti dell'interessato**: in qualsiasi momento è possibile esercitare i diritti
di cui agli artt. 15-22 GDPR (accesso, rettifica, cancellazione, limitazione, opposizione,
portabilità, revoca del consenso) scrivendo a info@theorganism.com.

**Reclamo**: l'interessato ha diritto di proporre reclamo al Garante per la protezione
dei dati personali (www.garanteprivacy.it).
""")

    consenso_privacy = st.checkbox(
        "✅ Ho letto l'informativa e acconsento al trattamento dei miei dati personali "
        "per le finalità di gestione dell'iscrizione (obbligatorio).",
    )
    consenso_marketing = st.checkbox(
        "📨 Acconsento a ricevere comunicazioni informative su prossimi eventi "
        "e iniziative dello Studio (facoltativo).",
    )

    submitted = st.form_submit_button("📅 Confermare iscrizione", type="primary", use_container_width=True)


# =============================================================================
# HANDLER SUBMIT
# =============================================================================

if submitted:
    # Validazioni base
    errors = []
    if not nome or not nome.strip():
        errors.append("Il **nome** è obbligatorio.")
    if not cognome or not cognome.strip():
        errors.append("Il **cognome** è obbligatorio.")
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        errors.append("L'**email** non è valida.")
    # Cellulare obbligatorio + validazione base
    tel_pulito = "".join(c for c in (telefono or "") if c.isdigit())
    if not telefono or not telefono.strip():
        errors.append("Il **cellulare** è obbligatorio.")
    elif len(tel_pulito) < 9:
        errors.append(
            "Il **cellulare** non sembra valido. Inserisci un numero di "
            "cellulare completo (es. 333 1234567)."
        )
    if not consenso_privacy:
        errors.append("Devi accettare l'**informativa privacy** per iscriverti.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # Check duplicato
    try:
        if email_gia_iscritta(conn, evento["id"], email):
            st.error(
                f"⚠️ L'email **{email}** risulta già iscritta a questo evento. "
                "Controlla la tua casella di posta per la conferma. "
                "Se non l'hai ricevuta, contatta lo Studio."
            )
            st.stop()
    except Exception as e:
        logger.error("Check duplicato fallito", exc_info=True)
        st.error(f"Errore di sistema: {e}")
        st.stop()

    # Crea iscrizione
    try:
        nuova = crea_iscrizione(
            conn,
            evento_id=evento["id"],
            nome=nome.strip(),
            cognome=cognome.strip(),
            email=email.strip().lower(),
            telefono=(telefono or "").strip() or None,
            note=(note or "").strip() or None,
            consenso_privacy=True,
            consenso_marketing=consenso_marketing,
            sorgente="web_pubblico",
        )
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()
    except Exception as e:
        logger.error("crea_iscrizione fallita", exc_info=True)
        st.error(f"Errore registrazione iscrizione: {e}")
        st.stop()

    # Genera PDF
    pdf_bytes = None
    pdf_problema = None
    try:
        pdf_bytes = genera_pdf_conferma(evento, nuova)
    except Exception as e:
        pdf_problema = str(e)
        logger.error("PDF generazione fallita", exc_info=True)

    # Invia email all'iscritto (+ Bcc allo studio)
    email_problema = None
    try:
        invia_conferma_iscritto(evento, nuova, pdf_bytes=pdf_bytes)
        mark_email_conferma_inviata(conn, nuova["id"])
    except Exception as e:
        email_problema = str(e)
        logger.error("invio email iscritto fallito", exc_info=True)

    # Invia notifica studio (best effort, non blocca)
    try:
        invia_notifica_studio(evento, nuova)
    except Exception:
        logger.error("notifica studio fallita", exc_info=True)

    # Salva stato per la pagina "grazie"
    st.session_state["ev_iscrizione_completata"] = {
        "slug": slug,
        "nome": nuova.get("nome"),
        "email": nuova.get("email"),
        "stato": nuova.get("stato"),
        "email_problema": email_problema,
        "pdf_problema": pdf_problema,
    }
    st.rerun()
