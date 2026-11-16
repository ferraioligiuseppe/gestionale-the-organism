"""Interfaccia Streamlit del modulo «Studi e ricerca».

Due punti d'ingresso:
  - render(get_conn, operatore)            → pagina interna del gestionale (solo personale autorizzato)
  - render_iscrizione_pubblica(get_conn, token) → pagina pubblica di iscrizione con il link dello studio
[get_conn] è la funzione del gestionale che restituisce una connessione PostgreSQL.
"""
import csv
import io

import streamlit as st

try:
    from . import db_studi as db
    from . import testi_privacy as tp
except ImportError:
    import db_studi as db
    import testi_privacy as tp

# indirizzo dell'area pubblica dove si apre il link di iscrizione (?azione=studio&s=<token>)
URL_PUBBLICO = "https://pnev-eventi-prova.streamlit.app"


def _csv(rows) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=";")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8-sig")


def _form_dati_base(prefix: str) -> dict:
    c1, c2 = st.columns(2)
    with c1:
        eta = st.selectbox("Fascia d'età", tp.FASCE_ETA, key=f"{prefix}_eta")
        sesso = st.selectbox("Sesso", tp.SESSO, key=f"{prefix}_sesso")
        mano = st.selectbox("Mano dominante", tp.MANO, key=f"{prefix}_mano")
    with c2:
        udito = st.selectbox("Disturbi dell'udito noti", tp.SI_NO, key=f"{prefix}_udito")
        acufene = st.selectbox("Acufene", tp.SI_NO, key=f"{prefix}_acufene")
        cuffie = st.selectbox("Cuffie che userai", tp.CUFFIE, key=f"{prefix}_cuffie")
    return {"fascia_eta": eta, "sesso": sesso, "mano": mano, "udito": udito, "acufene": acufene, "cuffie": cuffie}


def _form_consensi(prefix: str) -> dict:
    return {k: st.checkbox(testo, key=f"{prefix}_{k}") for k, testo, _ in tp.CONSENSI}


def _mostra_codice(esito):
    st.success(f"Iscrizione completata. Codice partecipante: **{esito['codice']}** · gruppo **{esito['gruppo']}**")
    if esito["gruppo"] != "A":
        st.info(f"Le sessioni si apriranno da {esito['inizio']:%d/%m/%Y}. Nel frattempo installa Pegasis e compila "
                "il questionario e le prove che l'app ti propone.")
    st.markdown("**Copia questo codice e incollalo in Pegasis** (al primo avvio: «Uso Pegasis per me» → «Il tuo programma»):")
    st.code(esito["codice_pegasis"], language=None)


# ---------------- Pagina interna ----------------

def render(get_conn, operatore: str = ""):
    st.header("Studi e ricerca")
    conn = get_conn()
    db.crea_tabelle(conn)

    studi = db.elenco_studi(conn)
    with st.expander("Nuovo studio", expanded=not studi):
        with st.form("nuovo_studio"):
            titolo = st.text_input("Titolo", "Studio pilota Pegasis — colleghi TFA")
            descr = st.text_area("Descrizione", "Lista d'attesa A/B, 20 sessioni Basic; WHO-5, questionario PNEV, prove di attenzione e memoria.")
            c1, c2, c3 = st.columns(3)
            sessioni = c1.number_input("Sessioni", 5, 100, 20)
            minuti = c2.number_input("Minuti per sessione", 10, 60, 30)
            attesa = c3.number_input("Attesa del gruppo B (giorni)", 0, 120, 35)
            c4, c5 = st.columns(2)
            blocco = c4.selectbox("Blocchi di randomizzazione", [4, 6, 8], help="In ogni blocco A e B compaiono lo stesso numero di volte")
            posti = c5.number_input("Posti nella lista", 10, 1000, 200)
            brani = st.text_input("Brani (id del catalogo, separati da virgola; vuoto = primo genere del catalogo)", "")
            comitato = st.text_input("Parere del comitato etico (numero e data, se già ottenuto)", "")
            if st.form_submit_button("Crea studio"):
                sid = db.crea_studio(conn, titolo, descr, int(sessioni), int(minuti), int(attesa), brani, "A,B",
                                     int(blocco), int(posti), comitato, operatore)
                st.success(f"Studio creato (n. {sid}).")
                st.rerun()

    if not studi:
        return
    scelto = st.selectbox("Studio", studi, format_func=lambda s: f"{s['titolo']} · {s['iscritti']} iscritti")
    sid = scelto["id"]
    s = db.studio(conn, sid)
    link = f"{URL_PUBBLICO}/?azione=studio&s={s['token_iscrizione']}"

    t_iscr, t_part, t_imp, t_esp, t_priv = st.tabs(["Iscrizione", "Partecipanti", "Importa dati", "Esporta", "Privacy e registro"])

    with t_iscr:
        st.markdown("**Link di iscrizione** da mandare al gruppo:")
        st.code(link, language=None)
        aperte = st.toggle("Iscrizioni aperte", value=s["iscrizioni_aperte"])
        if aperte != s["iscrizioni_aperte"]:
            db.imposta_iscrizioni(conn, sid, aperte, operatore); st.rerun()
        st.divider()
        st.subheader("Iscrizione in studio (modulo cartaceo firmato)")
        with st.form("iscrivi_interno"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome"); cognome = c2.text_input("Cognome")
            email = c1.text_input("Email"); tel = c2.text_input("Telefono")
            base = _form_dati_base("int")
            st.caption(f"Il partecipante ha firmato il modulo cartaceo (privacy {tp.PRIVACY_VERSIONE}):")
            cons = _form_consensi("int")
            if st.form_submit_button("Iscrivi e genera il codice"):
                if not nome.strip() or not cognome.strip():
                    st.error("Nome e cognome sono obbligatori.")
                else:
                    try:
                        _mostra_codice(db.iscrivi(conn, sid, nome, cognome, email, tel, base, cons, "cartaceo", operatore))
                    except ValueError as e:
                        st.error(str(e))

    with t_part:
        righe = db.avanzamento(conn, sid)
        st.caption("Uso interno: questa tabella contiene i nomi. Per l'analisi usa l'esportazione anonima.")
        st.dataframe(righe, use_container_width=True, hide_index=True)
        tot = len(righe)
        if tot:
            a = sum(1 for r in righe if r["gruppo"] == "A")
            st.write(f"Iscritti: {tot} · gruppo A {a} · gruppo B {tot - a}")
        with st.expander("Ritiro di un partecipante"):
            cod = st.text_input("Codice partecipante da ritirare").strip().upper()
            if st.button("Ritira e cancella i suoi dati", type="primary", disabled=not cod):
                db.revoca(conn, sid, cod, operatore); st.success(f"{cod}: dati cancellati."); st.rerun()

    with t_imp:
        st.write("Incolla qui il testo ricevuto con «Invia i dati allo studio» (email o WhatsApp).")
        testo = st.text_area("Testo ricevuto", height=220)
        if st.button("Importa", disabled=not testo.strip()):
            try:
                cod, n = db.importa_dati(conn, sid, testo, operatore)
                st.success(f"{cod}: {n} dati nuovi salvati.")
            except Exception as e:  # testo malformato o codice non iscritto
                st.error(f"Non riesco a importare: {e}")

    with t_esp:
        dati = db.esporta_anonimo(conn, sid)
        st.write(f"{len(dati)} righe, senza nomi né contatti.")
        st.download_button("Scarica i dati anonimi (CSV)", _csv(dati), file_name=f"studio_{sid}_anonimo.csv", mime="text/csv",
                           disabled=not dati)

    with t_priv:
        st.markdown(f"**Versione dei testi:** {tp.PRIVACY_VERSIONE}")
        with st.expander("Foglio informativo"):
            st.markdown(tp.FOGLIO_INFORMATIVO)
        with st.expander("Informativa privacy"):
            st.markdown(tp.INFORMATIVA)
        st.subheader("Registro delle operazioni")
        st.dataframe(db.registro(conn, sid), use_container_width=True, hide_index=True)


# ---------------- Pagina pubblica di iscrizione ----------------

def render_iscrizione_pubblica(get_conn, token: str):
    conn = get_conn()
    db.crea_tabelle(conn)
    s = db.studio(conn, token=token)
    if s is None:
        st.error("Link non valido."); return
    st.title(s["titolo"])
    if not s["iscrizioni_aperte"]:
        st.warning("Le iscrizioni a questo studio sono chiuse."); return
    if "esito_iscrizione" in st.session_state:
        _mostra_codice(st.session_state["esito_iscrizione"]); return

    st.markdown(tp.FOGLIO_INFORMATIVO)
    with st.expander("Informativa sul trattamento dei dati (da leggere)"):
        st.markdown(tp.INFORMATIVA)
    with st.form("iscrizione_pubblica"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome"); cognome = c2.text_input("Cognome")
        email = c1.text_input("Email"); tel = c2.text_input("Telefono (facoltativo)")
        st.markdown("**Qualche informazione di base** (servono all'analisi, non ti identificano):")
        base = _form_dati_base("pub")
        st.markdown("**Consenso**")
        cons = _form_consensi("pub")
        if st.form_submit_button("Partecipo"):
            if not nome.strip() or not cognome.strip() or "@" not in email:
                st.error("Servono nome, cognome e un'email valida.")
            else:
                try:
                    st.session_state["esito_iscrizione"] = db.iscrivi(conn, s["id"], nome, cognome, email, tel, base, cons, "online")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
