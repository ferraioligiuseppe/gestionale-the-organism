# ══════════════════════════════════════════════════════════════════════════════
# PATCH app_core.py — sostituire le funzioni indicate con queste versioni
# ══════════════════════════════════════════════════════════════════════════════

# 1. SOSTITUIRE create_questionario_link (riga ~454) con:

def create_questionario_link(cur, paziente_id: int, questionario: str, ttl_days=None) -> str:
    """Wrapper legacy → delega al nuovo sistema unificato."""
    from modules.public_questionnaires import create_public_token
    return create_public_token(
        paziente_id=int(paziente_id),
        questionario=str(questionario),
        ttl_days=ttl_days,
    )

# 2. SOSTITUIRE validate_token (riga ~471) con:

def validate_token(cur, token: str, questionario: str):
    """Wrapper legacy → delega al nuovo sistema unificato."""
    from modules.public_questionnaires import validate_public_token
    return validate_public_token(token, questionario)

# 3. SOSTITUIRE mark_token_used (riga ~500) con:

def mark_token_used(cur, link_id: int):
    """Wrapper legacy → delega al nuovo sistema unificato."""
    from modules.public_questionnaires import mark_token_used as _mark
    _mark(link_id)

# 4. SOSTITUIRE il blocco maybe_handle_public_questionario (riga ~506)
#    (tutta la funzione) con:

def maybe_handle_public_questionario(get_conn) -> bool:
    """
    Gestisce i link pubblici nella app principale (retrocompatibilità).
    I nuovi link usano pages/pnev_pubblico.py direttamente.
    Questa funzione gestisce ancora i vecchi link ?q=INPPS&t=...
    che puntano alla root dell'app.
    """
    qp = getattr(st, "query_params", {})
    q  = (qp.get("q", "") or "").upper().strip()
    t  = (qp.get("t", "") or "").strip()

    if not q or not t:
        return False

    from modules.public_questionnaires import (
        validate_public_token, mark_token_used as _mark_used,
        save_inpps_response, init_public_tokens_table, REGISTRY,
    )

    try:
        init_public_tokens_table()
    except Exception:
        pass

    if q not in REGISTRY:
        return False

    rec = validate_public_token(t, q)
    if not rec:
        st.error("Link non valido, scaduto o già utilizzato.")
        st.caption("Contatta lo studio: 📞 0815152334")
        st.stop()
        return True

    paziente_id = int(rec["paziente_id"])
    token_id    = int(rec["id"])
    nome        = rec.get("nome_paziente", "")

    st.markdown(f"## Questionario {REGISTRY[q]['label']}")
    if nome:
        st.caption(f"Paziente: **{nome}**")

    with st.form("legacy_public_form"):
        inpps_data, inpps_summary = inpps_collect_ui(
            prefix="legacy_pub", existing=None
        )
        submitted = st.form_submit_button("✅ INVIA QUESTIONARIO", type="primary")

    if submitted:
        try:
            save_inpps_response(paziente_id, inpps_data, inpps_summary)
            _mark_used(token_id)
            st.success("✅ Grazie! Questionario inviato correttamente.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")
        st.stop()

    return True

# 5. SOSTITUIRE il blocco expander "Link INPPS (genitori)" (~riga 5082)
#    nella funzione ui_anamnesi con:
#
#    from modules.public_questionnaires import ui_genera_link_pubblico
#    ui_genera_link_pubblico(paz_id, nome_paziente)
#
#    (dove paz_id e nome_paziente sono già disponibili nel contesto)
#
# ══════════════════════════════════════════════════════════════════════════════
# NOTA: non toccare nulla altro in app_core.py.
# Il vecchio sistema questionari_links NON va eliminato subito —
# i token vecchi ancora validi funzioneranno tramite i wrapper legacy.
# ══════════════════════════════════════════════════════════════════════════════
