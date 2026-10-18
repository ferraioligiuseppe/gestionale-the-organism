"""
Genosociogramma — interfaccia Streamlit.

Voce di menu «🌳 Genosociogramma» (Pazienti → Scheda clinica). Il router chiama
render_genosociogramma_router(conn, paz_id), come gli altri moduli per paziente.
"""
import streamlit as st
import streamlit.components.v1 as components

from . import db_genosociogramma as db
from .pdf_genosociogramma import genera_pdf
from .render_genosociogramma import (TIPI_LEGAME_LABEL, anni_label, geometria, ripetizioni, svg_genogramma,
                                     testo_diario)

SESSO_LABEL = {"M": "Maschio", "F": "Femmina", "?": "Non noto"}


def _nome(p):
    return f'{p.get("nome") or "senza nome"} ({anni_label(p)})'


def render_genosociogramma(conn, studio_id, paziente_id, paziente_label="", on_page=None, diario_cb=None):
    if not st.session_state.get("_geno_schema_ok"):
        db.ensure_schema(conn)
        st.session_state["_geno_schema_ok"] = True

    st.subheader("Genosociogramma")
    elenco = db.lista_genogrammi(conn, paziente_id)

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("Nuovo genosociogramma", key=f"geno_new_{paziente_id}", use_container_width=True):
            gid = db.crea_genogramma(conn, studio_id, paziente_id)
            st.session_state[f"geno_sel_{paziente_id}"] = gid
            st.rerun()
    if not elenco:
        st.info("Nessun genosociogramma per questo paziente. Creane uno con «Nuovo genosociogramma».")
        return
    ids = [e["id"] for e in elenco]
    sel = st.session_state.get(f"geno_sel_{paziente_id}")
    with c1:
        gid = st.selectbox("Genosociogramma", ids, index=ids.index(sel) if sel in ids else 0,
                           format_func=lambda i: next(f'{e["titolo"]} — aggiornato il {e["updated_at"]:%d/%m/%Y}'
                                                      for e in elenco if e["id"] == i),
                           key=f"geno_pick_{paziente_id}")
    st.session_state[f"geno_sel_{paziente_id}"] = gid
    g = db.carica_genogramma(conn, gid)
    by = {p["id"]: p for p in g["persone"]}

    t_mappa, t_pers, t_unioni, t_legami, t_rip, t_exp = st.tabs(
        ["Mappa", "Persone", "Unioni", "Legami", "Ripetizioni", "Esporta"])

    # ------------------------------------------------ mappa
    with t_mappa:
        if not g["persone"]:
            st.info("Aggiungi le persone nella scheda «Persone».")
        else:
            el = geometria(g)
            components.html(f'<div style="overflow:auto;border:1px solid #CAD4D2;border-radius:8px">'
                            f'{svg_genogramma(g)}</div>', height=min(int(el["h"]) + 30, 900), scrolling=True)
            st.caption("Quadrato = maschio · cerchio = femmina · rombo = non noto · doppio contorno = paziente · "
                       "X = deceduto · numero = età attuale o alla morte · linee viola = legami affettivi.")
        with st.expander("Titolo e note del clinico"):
            with st.form(f"geno_meta_{gid}"):
                titolo = st.text_input("Titolo", g["titolo"])
                note = st.text_area("Note", g["note"], height=120)
                c_a, c_b = st.columns(2)
                salva = c_a.form_submit_button("Salva")
                conf = c_b.checkbox("Confermo l’eliminazione")
                elimina = c_b.form_submit_button("Elimina genosociogramma")
            if salva:
                db.rinomina_genogramma(conn, gid, titolo.strip() or "Genosociogramma", note)
                st.rerun()
            if elimina and conf:
                db.elimina_genogramma(conn, gid)
                st.session_state.pop(f"geno_sel_{paziente_id}", None)
                st.rerun()

    # ------------------------------------------------ persone
    with t_pers:
        st.caption("Date come anno (1952) o giorno/mese/anno (12/03/1952): con la data completa si trovano "
                   "anche le coincidenze di giorno.")
        for p in g["persone"]:
            with st.expander(_nome(p) + ("  · paziente" if p.get("indice") else "")):
                _form_persona(conn, studio_id, gid, g, p)
        st.markdown("**Aggiungi persona**")
        _form_persona(conn, studio_id, gid, g, None)

    # ------------------------------------------------ unioni
    with t_unioni:
        st.caption("Le coppie di genitori compaiono nella mappa anche senza un’unione registrata.")
        for u in g["unioni"]:
            if u["a"] not in by or u["b"] not in by:
                continue
            with st.form(f"geno_u_{u['id']}"):
                st.markdown(f'**{by[u["a"]]["nome"]}** e **{by[u["b"]]["nome"]}**')
                c_a, c_b, c_c, c_d = st.columns([2, 1, 1, 1])
                tipo = c_a.selectbox("Tipo", db.TIPI_UNIONE, index=db.TIPI_UNIONE.index(u["tipo"]),
                                     key=f"geno_ut_{u['id']}")
                anno = c_b.text_input("Anno o data", u["anno"], key=f"geno_ua_{u['id']}")
                if c_c.form_submit_button("Salva"):
                    db.aggiorna_unione(conn, gid, u["id"], tipo, anno)
                    st.rerun()
                if c_d.form_submit_button("Elimina"):
                    db.elimina_unione(conn, gid, u["id"])
                    st.rerun()
        if len(g["persone"]) >= 2:
            with st.form(f"geno_u_new_{gid}", clear_on_submit=True):
                st.markdown("**Aggiungi unione**")
                ids = list(by)
                c_a, c_b, c_c, c_d = st.columns(4)
                a = c_a.selectbox("Partner", ids, format_func=lambda i: _nome(by[i]), key=f"geno_una_{gid}")
                b = c_b.selectbox("Partner", ids, index=1, format_func=lambda i: _nome(by[i]), key=f"geno_unb_{gid}")
                tipo = c_c.selectbox("Tipo", db.TIPI_UNIONE, key=f"geno_unt_{gid}")
                anno = c_d.text_input("Anno o data", key=f"geno_unn_{gid}")
                if st.form_submit_button("Aggiungi unione"):
                    if a == b:
                        st.error("Scegli due persone diverse.")
                    else:
                        db.aggiungi_unione(conn, studio_id, gid, a, b, tipo, anno)
                        st.rerun()

    # ------------------------------------------------ legami
    with t_legami:
        for l in g["legami"]:
            if l["a"] not in by or l["b"] not in by:
                continue
            c_a, c_b = st.columns([5, 1])
            c_a.markdown(f'{by[l["a"]]["nome"]} → {by[l["b"]]["nome"]}: **{TIPI_LEGAME_LABEL[l["tipo"]]}**')
            if c_b.button("Elimina", key=f"geno_ld_{l['id']}"):
                db.elimina_legame(conn, gid, l["id"])
                st.rerun()
        if len(g["persone"]) >= 2:
            with st.form(f"geno_l_new_{gid}", clear_on_submit=True):
                st.markdown("**Aggiungi legame affettivo**")
                ids = list(by)
                c_a, c_b, c_c = st.columns(3)
                a = c_a.selectbox("Da", ids, format_func=lambda i: _nome(by[i]), key=f"geno_lna_{gid}")
                b = c_b.selectbox("A", ids, index=1, format_func=lambda i: _nome(by[i]), key=f"geno_lnb_{gid}")
                tipo = c_c.selectbox("Tipo", db.TIPI_LEGAME, format_func=lambda t: TIPI_LEGAME_LABEL[t],
                                     key=f"geno_lnt_{gid}")
                if st.form_submit_button("Aggiungi legame"):
                    if a == b:
                        st.error("Scegli due persone diverse.")
                    else:
                        db.aggiungi_legame(conn, studio_id, gid, a, b, tipo)
                        st.rerun()

    # ------------------------------------------------ ripetizioni
    with t_rip:
        st.caption("Spunti per il colloquio, non prove: le coincidenze sono frequenti in ogni famiglia.")
        r = ripetizioni(g)
        if r["indice_eta"] is not None:
            st.markdown(f"**{r['indice_nome']} ha {r['indice_eta']} anni: che cosa è successo agli altri alla stessa età**")
            _lista(r["indice"])
        else:
            st.markdown("**Età del paziente**")
            st.write("Segna il paziente e la sua data di nascita nella scheda «Persone».")
        for k, t in (("eta", "Stessa età alla morte"), ("date", "Stesso giorno e mese"), ("nomi", "Nomi che ritornano")):
            st.markdown(f"**{t}**")
            _lista(r[k])

    # ------------------------------------------------ esporta
    with t_exp:
        pdf = genera_pdf(g, paziente_label=paziente_label, on_page=on_page)
        st.download_button("Scarica il PDF", pdf, file_name=f"genosociogramma_{paziente_id}_{gid}.pdf",
                           mime="application/pdf", key=f"geno_pdf_{gid}")
        if g["persone"]:
            st.download_button("Scarica l’immagine (SVG)", svg_genogramma(g),
                               file_name=f"genosociogramma_{paziente_id}_{gid}.svg", mime="image/svg+xml",
                               key=f"geno_svg_{gid}")
        testo = testo_diario(g)
        st.text_area("Riassunto per il diario clinico", testo, height=140, key=f"geno_diario_{gid}")
        if diario_cb and st.button("Aggiungi al diario clinico", key=f"geno_diario_btn_{gid}"):
            try:
                diario_cb(gid, testo)
                st.success("Voce aggiunta al diario clinico.")
            except Exception as e:
                st.error(f"Voce non aggiunta al diario: {e}")


def render_genosociogramma_router(conn, paz_id):
    """Ingresso dal router del gestionale: ricava studio, paziente e diario."""
    try:
        conn.rollback()
    except Exception:
        pass
    studio_id = db.studio_corrente(conn) or st.session_state.get("studio_id")
    if not studio_id:
        st.error("Studio non identificato: impossibile aprire il genosociogramma.")
        return
    paziente_label = ""
    try:
        cur = conn.cursor()
        cur.execute("SELECT Nome, Cognome FROM Pazienti WHERE id = %s", (paz_id,))
        r = cur.fetchone()
        if r:
            paziente_label = f"Paziente: {r[0] or ''} {r[1] or ''}".strip()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    def _diario(gid, testo):
        from modules.diario_clinico import registra_voce_diario
        autore = st.session_state.get("utente_nome") or st.session_state.get("username")
        registra_voce_diario(conn, studio_id, paz_id, "valutazione", "genosociogramma", gid,
                             riassunto=testo.split("\n")[0], testo=testo,
                             titolo="Genosociogramma", autore=autore)

    try:
        render_genosociogramma(conn, studio_id, paz_id, paziente_label=paziente_label, diario_cb=_diario)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        import traceback
        st.error(f"Errore genosociogramma: {e}")
        with st.expander("Dettagli tecnici"):
            st.code(traceback.format_exc())


def _lista(voci):
    if voci:
        st.markdown("\n".join(f"- {v}" for v in voci))
    else:
        st.write("Nessuna rilevata.")


def _form_persona(conn, studio_id, gid, g, p):
    nuovo = p is None
    p = p or {"nome": "", "sesso": "M", "nascita": "", "morte": "", "causa": "", "padre": None,
              "madre": None, "indice": False, "note": ""}
    k = f"{gid}_{p.get('id', 'new')}"
    altri = [x for x in g["persone"] if x["id"] != p.get("id")]
    padri = [None] + [x["id"] for x in altri if x["sesso"] in ("M", "?")]
    madri = [None] + [x["id"] for x in altri if x["sesso"] in ("F", "?")]
    by = {x["id"]: x for x in altri}
    fmt = lambda i: "—" if i is None else _nome(by[i])
    with st.form(f"geno_p_{k}", clear_on_submit=nuovo):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", p["nome"], key=f"geno_pn_{k}")
        sesso = c2.selectbox("Sesso", list(SESSO_LABEL), index=list(SESSO_LABEL).index(p["sesso"]),
                             format_func=SESSO_LABEL.get, key=f"geno_ps_{k}")
        nascita = c1.text_input("Nascita", p["nascita"], placeholder="gg/mm/aaaa o aaaa", key=f"geno_pb_{k}")
        morte = c2.text_input("Morte", p["morte"], placeholder="vuoto se in vita", key=f"geno_pm_{k}")
        causa = st.text_input("Causa di morte o malattia", p["causa"], key=f"geno_pc_{k}")
        padre = c1.selectbox("Padre", padri, index=padri.index(p["padre"]) if p["padre"] in padri else 0,
                             format_func=fmt, key=f"geno_pf_{k}")
        madre = c2.selectbox("Madre", madri, index=madri.index(p["madre"]) if p["madre"] in madri else 0,
                             format_func=fmt, key=f"geno_pmo_{k}")
        note = st.text_area("Eventi, ruolo, segreti", p["note"], key=f"geno_pno_{k}")
        indice = st.checkbox("Paziente (chi costruisce il genosociogramma)", p["indice"], key=f"geno_pi_{k}")
        if nuovo:
            invia = st.form_submit_button("Aggiungi persona")
            elimina = conferma = False
        else:
            cc1, cc2, cc3 = st.columns([1, 1, 1])
            invia = cc1.form_submit_button("Salva")
            conferma = cc2.checkbox("Confermo l’eliminazione", key=f"geno_pdc_{k}")
            elimina = cc3.form_submit_button("Elimina persona")
    if invia:
        if not nome.strip():
            st.error("Il nome è obbligatorio.")
            return
        db.salva_persona(conn, studio_id, gid, {"id": p.get("id"), "nome": nome, "sesso": sesso, "nascita": nascita,
                                                "morte": morte, "causa": causa, "padre": padre, "madre": madre,
                                                "indice": indice, "note": note})
        st.rerun()
    if elimina:
        if not conferma:
            st.warning("Spunta «Confermo l’eliminazione» per eliminare la persona.")
            return
        db.elimina_persona(conn, gid, p["id"])
        st.rerun()
