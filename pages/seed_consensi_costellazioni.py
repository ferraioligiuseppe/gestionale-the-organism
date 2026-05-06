# -*- coding: utf-8 -*-
# pages/seed_consensi_costellazioni.py
#
# Pagina admin TEMPORANEA per:
# 1) creare le tabelle cf_* (schema)
# 2) caricare i 4 template di consenso (seed)
#
# COME USARE:
#   1. Login al gestionale come admin
#   2. URL: https://testgestionale.streamlit.app/seed_consensi_costellazioni
#   3. Premi i 2 bottoni in ordine
#   4. Cancella il file dal repo quando hai finito

import streamlit as st
import sys, os
import traceback

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(
    page_title="The Organism — Seed Consensi Costellazioni",
    page_icon="🌱",
    layout="centered",
)

st.title("🌱 Setup modulo Consensi Costellazioni")
st.caption("Pagina admin temporanea — usare una sola volta dopo il primo deploy.")

# Protezione minima: utente loggato
user = st.session_state.get("user")
if not user or not user.get("username"):
    st.error("⚠️ Devi essere loggato nel gestionale.")
    st.info("Vai su https://testgestionale.streamlit.app/ e fai login, poi torna qui.")
    st.stop()

st.success(f"Login rilevato: **{user['username']}**")
st.divider()

# Connessione DB
try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Connessione DB fallita: {e}")
    st.code(traceback.format_exc())
    st.stop()


# =============================================================================
# STEP 1: CREAZIONE TABELLE
# =============================================================================

st.markdown("## Step 1 — Crea le tabelle nel database")
st.caption(
    "Crea le 7 tabelle del modulo (cf_template, cf_firme, cf_voci, cf_gruppi, "
    "cf_gruppi_partecipanti, cf_token_firma, cf_audit_log). Idempotente."
)

# Verifica stato tabelle
def _check_tabelle(conn):
    """Verifica quali tabelle cf_* esistono."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name LIKE 'cf_%'
            ORDER BY table_name
        """)
        return [r[0] for r in cur.fetchall()]
    finally:
        try: cur.close()
        except: pass


tabelle_attese = [
    "cf_audit_log",
    "cf_firme",
    "cf_gruppi",
    "cf_gruppi_partecipanti",
    "cf_template",
    "cf_token_firma",
    "cf_voci",
]

try:
    presenti = _check_tabelle(conn)
    mancanti = [t for t in tabelle_attese if t not in presenti]

    if not mancanti:
        st.success(f"✅ Tutte le 7 tabelle sono presenti: {', '.join(presenti)}")
    else:
        st.warning(
            f"⏳ Tabelle presenti: {len(presenti)}/7\n\n"
            f"Mancanti: **{', '.join(mancanti)}**"
        )
except Exception as e:
    st.warning(f"Verifica fallita (probabilmente nessuna tabella esiste ancora): {e}")
    mancanti = tabelle_attese  # forza creazione

if mancanti:
    if st.button("🛠️ Crea tabelle mancanti", type="primary", use_container_width=True):
        try:
            from modules.consensi_costellazioni.db_schema import apply_schema

            with st.spinner("Creazione tabelle in corso..."):
                apply_schema(conn, db_backend="postgres")

            st.success("✅ Schema applicato!")

            # Verifica
            presenti2 = _check_tabelle(conn)
            st.write("Tabelle ora presenti:")
            for t in tabelle_attese:
                if t in presenti2:
                    st.markdown(f"- ✅ `{t}`")
                else:
                    st.markdown(f"- ❌ `{t}` (ancora mancante!)")

            if all(t in presenti2 for t in tabelle_attese):
                st.balloons()
                st.info("🎉 Tutte le tabelle create. Procedi al Step 2 qui sotto.")

        except Exception as e:
            st.error(f"Creazione tabelle fallita: {e}")
            st.code(traceback.format_exc())

st.divider()


# =============================================================================
# STEP 2: SEEDING TEMPLATE
# =============================================================================

st.markdown("## Step 2 — Carica i 4 template di consenso")
st.caption(
    "Popola la tabella cf_template con i testi dei 4 consensi: "
    "individuali, gruppo, rappresentante, registrazione. Idempotente."
)

# Verifica stato seeding
codici = [
    "costellazioni_individuali",
    "costellazioni_gruppo",
    "costellazioni_rappresentante",
    "costellazioni_registrazione",
]

try:
    from modules.consensi_costellazioni import services

    # Verifica solo se cf_template esiste
    if "cf_template" not in _check_tabelle(conn):
        st.info("⏳ Prima crea le tabelle (Step 1).")
    else:
        presenti_tpl = []
        mancanti_tpl = []
        for c in codici:
            if services.template_attivo_per_codice(conn, c):
                presenti_tpl.append(c)
            else:
                mancanti_tpl.append(c)

        if not mancanti_tpl:
            st.success(f"🎉 Tutti i 4 template sono già caricati!")
            for c in codici:
                tpl = services.template_attivo_per_codice(conn, c)
                st.markdown(
                    f"- ✅ **{c}** v{tpl['versione']} — "
                    f"{len(tpl.get('voci') or [])} voci"
                )

            # Permetti comunque il re-seed con sovrascrittura (utile se cambia il file MD)
            st.divider()
            st.markdown("##### 🔄 Aggiorna i template esistenti")
            st.caption(
                "Se hai modificato il file `docs/consensi_costellazioni.md` e vuoi "
                "aggiornare i template nel database con il nuovo testo, esegui un re-seed "
                "con sovrascrittura."
            )

            if st.button("🔄 Re-seed con sovrascrittura", type="secondary",
                         use_container_width=True, key="reseed_force"):
                try:
                    from modules.consensi_costellazioni.seeders.costellazioni import seed_template

                    candidati_md = [
                        "docs/consensi_costellazioni.md",
                        os.path.join(_ROOT, "docs/consensi_costellazioni.md"),
                    ]
                    percorso = next((p for p in candidati_md if os.path.exists(p)), None)

                    if not percorso:
                        st.error("⚠️ File `docs/consensi_costellazioni.md` non trovato.")
                        st.stop()

                    st.info(f"📄 Sorgente testi: `{percorso}`")

                    with st.spinner("Aggiornamento template..."):
                        risultati = seed_template(
                            conn,
                            percorso_md=percorso,
                            sovrascrivi=True,
                        )

                    st.success("✅ Template aggiornati!")
                    st.json(risultati)
                    st.balloons()

                    st.markdown("### Verifica")
                    for c in codici:
                        tpl = services.template_attivo_per_codice(conn, c)
                        if tpl:
                            st.markdown(
                                f"- ✅ **{c}** v{tpl['versione']} — "
                                f"{len(tpl.get('voci') or [])} voci"
                            )
                except Exception as e:
                    st.error(f"Errore re-seed: {e}")
                    st.code(traceback.format_exc())

        else:
            if presenti_tpl:
                st.info(f"Già caricati: {', '.join(presenti_tpl)}")
            st.warning(f"Da caricare: **{', '.join(mancanti_tpl)}**")

            sovrascrivi = st.checkbox(
                "Forza sovrascrittura",
                value=False,
                help="Spuntare se vuoi aggiornare il testo dei template già caricati."
            )

            if st.button("🌱 Esegui seeding", type="primary", use_container_width=True):
                try:
                    from modules.consensi_costellazioni.seeders.costellazioni import seed_template

                    candidati_md = [
                        "docs/consensi_costellazioni.md",
                        os.path.join(_ROOT, "docs/consensi_costellazioni.md"),
                    ]
                    percorso = next((p for p in candidati_md if os.path.exists(p)), None)

                    if not percorso:
                        st.error(
                            f"⚠️ File `docs/consensi_costellazioni.md` non trovato.\n\n"
                            f"Cercato in:\n" + "\n".join(f"- `{p}`" for p in candidati_md)
                        )
                        st.stop()

                    st.info(f"📄 Sorgente testi: `{percorso}`")

                    with st.spinner("Caricamento template..."):
                        risultati = seed_template(
                            conn,
                            percorso_md=percorso,
                            sovrascrivi=sovrascrivi,
                        )

                    st.success("✅ Seeding completato!")
                    st.json(risultati)
                    st.balloons()

                    st.markdown("### Verifica")
                    for c in codici:
                        tpl = services.template_attivo_per_codice(conn, c)
                        if tpl:
                            st.markdown(
                                f"- ✅ **{c}** v{tpl['versione']} — "
                                f"{len(tpl.get('voci') or [])} voci"
                            )
                        else:
                            st.markdown(f"- ❌ **{c}** non trovato!")

                except Exception as e:
                    st.error(f"Errore seeding: {e}")
                    st.code(traceback.format_exc())

except Exception as e:
    st.error(f"Errore: {e}")
    st.code(traceback.format_exc())

st.divider()
st.caption(
    "💡 Dopo che entrambi gli step mostrano tutti ✅, "
    "puoi cancellare questo file dal repo: "
    "`pages/seed_consensi_costellazioni.py`"
)
