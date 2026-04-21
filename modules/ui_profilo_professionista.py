# -*- coding: utf-8 -*-
"""
Profilo Professionista - The Organism
Ogni utente gestisce i propri dati che vengono usati
automaticamente in ricette, relazioni e lettere.
"""
from __future__ import annotations
import json
import streamlit as st


def _get_uid():
    u = st.session_state.get("user") or {}
    return u.get("id")

def _carica_profilo(conn) -> dict:
    uid = _get_uid()
    if not uid:
        return {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT profilo_json FROM auth_users WHERE id=%s", (uid,))
        row = cur.fetchone()
        if not row: return {}
        raw = row["profilo_json"] if isinstance(row, dict) else row[0]
        if not raw: return {}
        return raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        return {}

def _salva_profilo(conn, dati: dict) -> None:
    uid = _get_uid()
    if not uid:
        st.error("Utente non identificato.")
        return
    try:
        cur = conn.cursor()
        # Aggiunge colonna se non esiste
        try:
            cur.execute(
                "ALTER TABLE auth_users "
                "ADD COLUMN IF NOT EXISTS profilo_json JSONB DEFAULT '{}'::jsonb"
            )
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass

        cur.execute(
            "UPDATE auth_users SET profilo_json=%s::jsonb, "
            "display_name=%s WHERE id=%s",
            (json.dumps(dati, ensure_ascii=False),
             dati.get("display_name",""), uid)
        )
        conn.commit()

        # Aggiorna sessione
        u = st.session_state.get("user") or {}
        u["display_name"] = dati.get("display_name","")
        st.session_state["user"] = u

        st.success("Profilo salvato.")
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore: {e}")


def render_profilo_professionista(conn) -> None:
    st.subheader("Il mio profilo professionale")
    st.caption(
        "Questi dati vengono usati automaticamente in ricette, "
        "relazioni cliniche e lettere."
    )

    d = _carica_profilo(conn)

    # ── Dati principali ───────────────────────────────────────────────
    st.markdown("#### Dati principali")
    c1, c2 = st.columns(2)
    with c1:
        nome = st.text_input(
            "Nome e Cognome *",
            value=d.get("nome",""),
            placeholder="Giuseppe Ferraioli",
            key="pp_nome"
        )
    with c2:
        titolo = st.text_input(
            "Titolo professionale *",
            value=d.get("titolo",""),
            placeholder="Dott.",
            key="pp_titolo"
        )

    specializzazioni = st.text_input(
        "Specializzazioni (appaiono sotto il nome in intestazione)",
        value=d.get("specializzazioni",""),
        placeholder="Neuropsicologo - Optometrista Comportamentale",
        key="pp_spec"
    )

    # Nome visualizzato (usato nei PDF)
    display_name = f"{titolo} {nome}".strip() if titolo or nome else ""
    if display_name:
        st.info(f"Intestazione PDF: **{display_name}** — {specializzazioni}")

    # ── Recapiti ──────────────────────────────────────────────────────
    st.markdown("#### Recapiti")
    c3, c4 = st.columns(2)
    with c3:
        telefono = st.text_input(
            "Telefono",
            value=d.get("telefono",""),
            placeholder="389 1234567",
            key="pp_tel"
        )
        email_prof = st.text_input(
            "Email professionale",
            value=d.get("email_prof",""),
            placeholder="dott.ferraioli@theorganism.it",
            key="pp_email"
        )
    with c4:
        indirizzo = st.text_input(
            "Indirizzo studio",
            value=d.get("indirizzo",""),
            placeholder="Via De Rosa, 46 - 84016 Pagani (SA)",
            key="pp_ind"
        )
        sito = st.text_input(
            "Sito web",
            value=d.get("sito",""),
            placeholder="www.theorganism.it",
            key="pp_sito"
        )

    # ── Dati fiscali e albo ───────────────────────────────────────────
    st.markdown("#### Dati fiscali e albo")
    c5, c6, c7 = st.columns(3)
    with c5:
        piva = st.text_input(
            "Partita IVA",
            value=d.get("piva",""),
            placeholder="IT12345678901",
            key="pp_piva"
        )
    with c6:
        albo = st.text_input(
            "Ordine/Albo",
            value=d.get("albo",""),
            placeholder="Ordine Psicologi Campania",
            key="pp_albo"
        )
    with c7:
        n_albo = st.text_input(
            "N. iscrizione albo",
            value=d.get("n_albo",""),
            placeholder="n. 12345",
            key="pp_n_albo"
        )

    cf_prof = st.text_input(
        "Codice fiscale",
        value=d.get("cf_prof",""),
        placeholder="FRRPPP90A15F839X",
        key="pp_cf"
    )

    # ── Opzioni PDF ───────────────────────────────────────────────────
    st.markdown("#### Opzioni documento")
    c8, c9 = st.columns(2)
    with c8:
        mostra_recapiti_pdf = st.checkbox(
            "Mostra recapiti personali nel piede dei PDF",
            value=d.get("mostra_recapiti_pdf", False),
            key="pp_recapiti_pdf"
        )
    with c9:
        mostra_albo_pdf = st.checkbox(
            "Mostra n. iscrizione albo in firma",
            value=d.get("mostra_albo_pdf", False),
            key="pp_albo_pdf"
        )

    # ── Anteprima intestazione ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Anteprima intestazione PDF")

    col_prev, _ = st.columns([3,1])
    with col_prev:
        st.markdown(
            f"""<div style="border:0.5px solid var(--color-border-tertiary);
            border-radius:var(--border-radius-lg);padding:16px 20px;
            background:var(--color-background-secondary)">
            <div style="font-size:13px;font-weight:500;
            color:var(--color-text-primary)">{display_name or "Nome Cognome"}</div>
            <div style="font-size:11px;color:var(--color-text-secondary);
            margin-top:2px">{specializzazioni or "Specializzazioni"}</div>
            <div style="margin-top:8px;padding-top:8px;
            border-top:2px solid #1D6B44;font-size:9px;
            color:var(--color-text-tertiary)">
            [logo The Organism] &nbsp;&nbsp; linea verde
            </div>
            </div>""",
            unsafe_allow_html=True
        )

    # ── Salvataggio ───────────────────────────────────────────────────
    st.markdown("---")
    if st.button("Salva profilo", type="primary", key="pp_salva"):
        if not nome.strip():
            st.error("Il nome e cognome e obbligatorio.")
        else:
            _salva_profilo(conn, {
                "nome": nome.strip(),
                "titolo": titolo.strip(),
                "specializzazioni": specializzazioni.strip(),
                "display_name": display_name,
                "telefono": telefono.strip(),
                "email_prof": email_prof.strip(),
                "indirizzo": indirizzo.strip(),
                "sito": sito.strip(),
                "piva": piva.strip(),
                "albo": albo.strip(),
                "n_albo": n_albo.strip(),
                "cf_prof": cf_prof.strip(),
                "mostra_recapiti_pdf": mostra_recapiti_pdf,
                "mostra_albo_pdf": mostra_albo_pdf,
            })
