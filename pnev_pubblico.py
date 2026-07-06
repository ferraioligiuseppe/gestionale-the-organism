# -*- coding: utf-8 -*-
"""
pnev_pubblico.py — MILESTONE 3
App Streamlit PUBBLICA per il percorso MAPS-CLEAR (pnev.it).

Nessun login del gestionale: il paziente arriva qui dal file HTML su pnev.it
tramite parametri URL (pattern degli screening tools) oppure dal suo magic link.

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

Deploy: seconda app su Streamlit Cloud, stesso repo, main file = pnev_pubblico.py,
secrets: DATABASE_URL (stessa stringa del gestionale).
NOTA MILESTONE 4: l'invio email del magic link via SendGrid sostituirà la
visualizzazione a schermo del link.
"""

import psycopg2
import streamlit as st

from modules.pnev_pubblico import db_pnev_pubblico as db

VERDE = "#1D6B44"

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


@st.cache_resource
def _init_schema():
    conn = get_connection()
    try:
        db.init_pnev_pubblico_db(conn)
    finally:
        conn.close()
    return True


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

    st.success(f"Benvenuto/a, {nome}! I tuoi progressi ora vengono salvati. 🎉")
    st.markdown("### 🔑 Il tuo link personale")
    st.markdown(
        "Salvalo nei **preferiti** o copialo in un posto sicuro: "
        "ti fa rientrare nei tuoi progressi da **qualsiasi dispositivo**, senza password."
    )
    st.code(link_dashboard(token), language=None)
    st.caption("Presto lo riceverai anche via email. Il link vale per tutta la durata del percorso.")
    st.link_button("▶ Vai ai miei progressi", link_dashboard(token))
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
    db.salva_sessione(
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


def azione_post(conn, utente_id):
    risposte = leggi_questionario_da_url()
    if risposte:
        db.salva_questionario_post(conn, utente_id, risposte)
        st.toast("Questionario finale salvato ✅")


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
