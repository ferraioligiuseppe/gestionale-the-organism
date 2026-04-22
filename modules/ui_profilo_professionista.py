# -*- coding: utf-8 -*-
"""
Profilo Professionista - The Organism
Salva titolo, nome e specializzazioni separatamente
cosi il display_name viene sempre costruito correttamente.
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
        cur.execute("SELECT profilo_json, display_name FROM auth_users WHERE id=%s", (uid,))
        row = cur.fetchone()
        if not row: return {}
        raw  = row["profilo_json"]  if isinstance(row, dict) else row[0]
        dn   = row["display_name"]  if isinstance(row, dict) else row[1]
        if not raw: return {"_display_name_db": dn or ""}
        pj = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        pj["_display_name_db"] = dn or ""
        return pj
    except Exception:
        return {}

def _salva_profilo(conn, dati: dict) -> bool:
    uid = _get_uid()
    if not uid:
        st.error("Utente non identificato.")
        return False
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                "ALTER TABLE auth_users "
                "ADD COLUMN IF NOT EXISTS profilo_json JSONB DEFAULT '{}'::jsonb"
            )
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass

        # Rimuovi chiave interna prima di salvare
        dati_clean = {k:v for k,v in dati.items() if not k.startswith("_")}

        cur.execute(
            "UPDATE auth_users SET profilo_json=%s::jsonb, display_name=%s WHERE id=%s",
            (json.dumps(dati_clean, ensure_ascii=False),
             dati_clean.get("display_name",""), uid)
        )
        conn.commit()

        # Aggiorna sessione immediatamente
        u = st.session_state.get("user") or {}
        u["display_name"]     = dati_clean.get("display_name","")
        u["specializzazioni"] = dati_clean.get("specializzazioni","")
        u["titolo"]           = dati_clean.get("titolo","")
        u["nome"]             = dati_clean.get("nome","")
        u["profilo"]          = dati_clean
        st.session_state["user"] = u
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio: {e}")
        return False


def render_profilo_professionista(conn) -> None:
    st.subheader("Il mio profilo professionale")
    st.caption(
        "Compila i campi separatamente — titolo, nome e specializzazioni "
        "vengono usati per costruire automaticamente l intestazione di ricette e relazioni."
    )

    d = _carica_profilo(conn)

    # ── Anteprima nome attuale in DB ──────────────────────────────────
    dn_db = d.get("_display_name_db","")
    if dn_db:
        st.info(f"Nome attuale nel sistema: **{dn_db}**")

    st.markdown("---")

    # ── Dati principali ───────────────────────────────────────────────
    st.markdown("#### 1. Dati principali")
    st.caption("Questi tre campi formano l intestazione dei PDF.")

    c1, c2, c3 = st.columns([1, 2, 3])
    with c1:
        titolo = st.text_input(
            "Titolo *",
            value=d.get("titolo",""),
            placeholder="Dott.",
            key="pp_titolo",
            help="Es: Dott., Dott.ssa, Prof."
        )
    with c2:
        nome = st.text_input(
            "Nome e Cognome *",
            value=d.get("nome",""),
            placeholder="Giuseppe Ferraioli",
            key="pp_nome"
        )
    with c3:
        specializzazioni = st.text_input(
            "Specializzazioni *",
            value=d.get("specializzazioni",""),
            placeholder="NeuroPsicologo - Optometrista Comportamentale",
            key="pp_spec",
            help="Appare sotto il nome nell intestazione"
        )

    # Anteprima live
    display_name = f"{titolo} {nome}".strip()
    if display_name or specializzazioni:
        st.markdown(
            f"""<div style="border:0.5px solid var(--color-border-tertiary);
            border-radius:var(--border-radius-lg);padding:14px 18px;
            background:var(--color-background-secondary);margin:8px 0">
            <div style="font-size:13px;font-weight:500;
            color:var(--color-text-primary)">{display_name or "—"}</div>
            <div style="font-size:11px;color:var(--color-text-secondary);
            margin-top:3px">{specializzazioni or "—"}</div>
            <div style="margin-top:10px;border-top:2px solid #1D6B44;
            padding-top:6px;font-size:9px;color:var(--color-text-tertiary)">
            Anteprima intestazione PDF
            </div></div>""",
            unsafe_allow_html=True
        )

    # ── Recapiti ──────────────────────────────────────────────────────
    st.markdown("#### 2. Recapiti")
    c4, c5 = st.columns(2)
    with c4:
        telefono    = st.text_input("Telefono", value=d.get("telefono",""),
                                     placeholder="389 1234567", key="pp_tel")
        email_prof  = st.text_input("Email professionale",
                                     value=d.get("email_prof",""),
                                     placeholder="dott@studio.it", key="pp_email")
    with c5:
        indirizzo   = st.text_input("Indirizzo studio",
                                     value=d.get("indirizzo",""),
                                     placeholder="Via De Rosa, 46 - 84016 Pagani (SA)",
                                     key="pp_ind")
        sito        = st.text_input("Sito web", value=d.get("sito",""),
                                     placeholder="www.theorganism.it", key="pp_sito")

    # ── Dati fiscali ──────────────────────────────────────────────────
    st.markdown("#### 3. Dati fiscali e albo")
    c6, c7, c8 = st.columns(3)
    with c6:
        piva    = st.text_input("Partita IVA", value=d.get("piva",""),
                                 placeholder="IT12345678901", key="pp_piva")
    with c7:
        albo    = st.text_input("Ordine / Albo", value=d.get("albo",""),
                                 placeholder="Ordine Psicologi Campania", key="pp_albo")
    with c8:
        n_albo  = st.text_input("N. iscrizione albo", value=d.get("n_albo",""),
                                 placeholder="n. 12345", key="pp_nalbo")
    cf_prof = st.text_input("Codice fiscale", value=d.get("cf_prof",""),
                              placeholder="FRRPPP80A01F839X", key="pp_cf")

    # ── Opzioni PDF ───────────────────────────────────────────────────
    st.markdown("#### 4. Opzioni documento")
    c9, c10 = st.columns(2)
    with c9:
        mostra_recapiti = st.checkbox(
            "Mostra recapiti personali nel piede dei PDF",
            value=d.get("mostra_recapiti_pdf", False), key="pp_recapiti")
    with c10:
        mostra_albo = st.checkbox(
            "Mostra n. iscrizione albo in firma",
            value=d.get("mostra_albo_pdf", False), key="pp_albo_pdf")

    # ── Salvataggio ───────────────────────────────────────────────────
    st.markdown("---")
    col_btn, col_msg = st.columns([1,3])
    with col_btn:
        salva = st.button("Salva profilo", type="primary", key="pp_salva")

    if salva:
        errori = []
        if not nome.strip():
            errori.append("Il nome e cognome e obbligatorio.")
        if not titolo.strip():
            errori.append("Il titolo e obbligatorio (es. Dott.).")
        if not specializzazioni.strip():
            errori.append("Le specializzazioni sono obbligatorie.")

        if errori:
            for e in errori:
                st.error(e)
        else:
            ok = _salva_profilo(conn, {
                "titolo":           titolo.strip(),
                "nome":             nome.strip(),
                "specializzazioni": specializzazioni.strip(),
                "display_name":     f"{titolo.strip()} {nome.strip()}",
                "telefono":         telefono.strip(),
                "email_prof":       email_prof.strip(),
                "indirizzo":        indirizzo.strip(),
                "sito":             sito.strip(),
                "piva":             piva.strip(),
                "albo":             albo.strip(),
                "n_albo":           n_albo.strip(),
                "cf_prof":          cf_prof.strip(),
                "mostra_recapiti_pdf": mostra_recapiti,
                "mostra_albo_pdf":     mostra_albo,
            })
            if ok:
                st.success(
                    f"Profilo salvato. Intestazione PDF: "
                    f"**{titolo.strip()} {nome.strip()}** — {specializzazioni.strip()}"
                )
                st.info(
                    "Le modifiche sono attive immediatamente — "
                    "non serve fare logout."
                )
