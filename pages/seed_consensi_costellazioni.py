# -*- coding: utf-8 -*-
# pages/seed_consensi_costellazioni.py
#
# Pagina admin TEMPORANEA per seeding una tantum dei 4 template
# di consenso costellazioni familiari.
#
# COME USARE:
#   1. Accedi al gestionale come admin
#   2. Nell'URL aggiungi /seed_consensi_costellazioni
#      es. https://testgestionale.streamlit.app/seed_consensi_costellazioni
#   3. Premi il bottone "Esegui seeding"
#   4. Verifica esito
#   5. Quando vuoi, cancella questo file dal repo (non serve più)

import streamlit as st
import sys, os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(
    page_title="The Organism — Seed Consensi Costellazioni",
    page_icon="🌱",
    layout="centered",
)

st.title("🌱 Seeding template Consensi Costellazioni")
st.caption("Pagina admin temporanea — usare una sola volta dopo il primo deploy.")

# Protezione: solo utente loggato (no breakglass, no anonimi)
user = st.session_state.get("user")
if not user or not user.get("username"):
    st.error("⚠️ Devi essere loggato nel gestionale per usare questa pagina.")
    st.info("Vai prima su https://testgestionale.streamlit.app/ e fai login.")
    st.stop()

st.success(f"Login rilevato: **{user['username']}**")
st.divider()

# Stato: già seedati?
try:
    from modules.app_core import get_connection
    from modules.consensi_costellazioni import services
    conn = get_connection()

    codici = [
        "costellazioni_individuali",
        "costellazioni_gruppo",
        "costellazioni_rappresentante",
        "costellazioni_registrazione",
    ]
    presenti = []
    mancanti = []
    for c in codici:
        if services.template_attivo_per_codice(conn, c):
            presenti.append(c)
        else:
            mancanti.append(c)

    if presenti:
        st.info(f"✅ Template già presenti ({len(presenti)}/4): {', '.join(presenti)}")
    if mancanti:
        st.warning(f"⏳ Template da caricare ({len(mancanti)}/4): {', '.join(mancanti)}")
    if not mancanti:
        st.success("🎉 Tutti i 4 template sono già caricati. Niente da fare!")

except Exception as e:
    st.error(f"Errore controllo stato: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

st.divider()

# Bottone di esecuzione
st.markdown("### Esegui seeding")
st.caption(
    "Il seeder è idempotente: se i template esistono già li salta, "
    "non sovrascrive."
)

col1, col2 = st.columns(2)

with col1:
    sovrascrivi = st.checkbox(
        "Forza sovrascrittura (aggiorna template esistenti)",
        value=False,
        help="Spuntare solo se vuoi aggiornare il testo dei template già caricati."
    )

with col2:
    eseguito = st.button(
        "🌱 Esegui seeding",
        type="primary",
        use_container_width=True,
    )

if eseguito:
    try:
        from modules.consensi_costellazioni.seeders.costellazioni import seed_template

        # Cerca il file dei testi MD
        candidati = [
            "docs/consensi_costellazioni.md",
            "modules/consensi_costellazioni/docs/consensi_costellazioni.md",
            os.path.join(_ROOT, "docs/consensi_costellazioni.md"),
        ]
        percorso = None
        for c in candidati:
            if os.path.exists(c):
                percorso = c
                break

        if not percorso:
            st.error(
                f"⚠️ File `docs/consensi_costellazioni.md` non trovato!\n\n"
                f"Percorsi cercati:\n" +
                "\n".join(f"- `{p}`" for p in candidati)
            )
            st.stop()

        st.info(f"📄 Uso file dei testi: `{percorso}`")

        with st.spinner("Caricamento template in corso..."):
            risultati = seed_template(
                conn,
                percorso_md=percorso,
                sovrascrivi=sovrascrivi,
            )

        st.success("✅ Seeding completato!")
        st.json(risultati)

        st.balloons()

        # Verifica finale
        st.divider()
        st.markdown("### Verifica finale")
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
        st.error(f"Errore durante seeding: {e}")
        import traceback
        st.code(traceback.format_exc())

st.divider()
st.caption(
    "💡 Quando hai completato il seeding e tutti i template sono ✅, "
    "puoi cancellare questo file dal repo: `pages/seed_consensi_costellazioni.py`"
)
