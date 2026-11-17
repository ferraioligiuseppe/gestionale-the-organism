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
    from . import eventi_eeg as eeg
except ImportError:
    import db_studi as db
    import testi_privacy as tp
    import eventi_eeg as eeg

# indirizzo dell'area pubblica dove si apre il link di iscrizione (?azione=studio&s=<token>)
URL_PUBBLICO = "https://pnev-iscrizioni.streamlit.app"


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

    # dati inviati da soli da Pegasis: si prendono dalla cassetta postale ogni volta che si apre la pagina
    if eeg.configurato():
        try:
            codici_studio = {r["codice"] for r in db.avanzamento(conn, sid)}
            visti = st.session_state.setdefault("studi_dati_visti", {})
            nuovi_tot = 0
            for f in eeg.elenco_dati():
                cod = f["chiave"].split("/")[-1][:-4]
                if cod not in codici_studio or visti.get(f["chiave"]) == f["caricato"]:
                    continue
                _, n = db.importa_dati(conn, sid, eeg.scarica_dati(f["chiave"]), operatore)
                visti[f["chiave"]] = f["caricato"]
                nuovi_tot += n
            if nuovi_tot:
                st.success(f"Arrivati da Pegasis {nuovi_tot} dati nuovi.")
        except Exception as e:
            st.caption(f"Sincronizzazione con Pegasis non riuscita ({e}): riprova ricaricando la pagina.")

    t_iscr, t_part, t_imp, t_eeg, t_esp, t_priv = st.tabs(
        ["Iscrizione", "Partecipanti", "Importa dati", "Registri EEG", "Esporta", "Privacy e registro"])

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
                db.revoca(conn, sid, cod, operatore)
                if eeg.configurato():
                    try:
                        eeg.cancella_codice(cod)
                    except Exception as e:  # la cassetta non risponde: va ripetuto
                        st.warning(f"Registri EEG non cancellati ({e}): riprova dal pulsante «Ritira» più tardi.")
                st.success(f"{cod}: dati cancellati."); st.rerun()

    with t_imp:
        st.info("Di solito non serve: con «Invia i dati allo studio» Pegasis salva i dati da solo (compaiono in «Partecipanti» "
                "ed «Esporta»). Usa questa scheda solo se un partecipante ti ha mandato i dati per email con «Non funziona? Invia per email».")
        st.write("Incolla qui il testo ricevuto per email:")
        testo = st.text_area("Testo ricevuto", height=220)
        if st.button("Importa", disabled=not testo.strip()):
            try:
                cod, n = db.importa_dati(conn, sid, testo, operatore)
                st.success(f"{cod}: {n} dati nuovi salvati.")
            except Exception as e:  # testo malformato o codice non iscritto
                st.error(f"Non riesco a importare: {e}")

    with t_eeg:
        st.caption("Registri dei cambi del suono inviati da Pegasis a fine brano, per allinearli con l'EEG (EmotivPRO).")
        if not eeg.configurato():
            st.info("Collega la cassetta postale: nei segreti di Streamlit aggiungi PEGASIS_EVENTI_URL e PEGASIS_EVENTI_TOKEN.")
        else:
            codici = {r["codice"] for r in db.avanzamento(conn, sid)}
            try:
                files = [f for f in eeg.elenco() if eeg.codice_da_chiave(f["chiave"]) in codici]
            except Exception as e:
                files = None
                st.error(f"La cassetta postale non risponde: {e}")
            if files is not None:
                if not files:
                    st.write("Nessun registro ancora arrivato per questo studio.")
                else:
                    files.sort(key=lambda f: f["chiave"], reverse=True)
                    st.write(f"{len(files)} registri.")
                    st.dataframe([{"codice": eeg.codice_da_chiave(f["chiave"]), "file": f["chiave"].split("/")[-1],
                                   "kB": round(f["byte"] / 1024, 1), "arrivato": str(f["caricato"])[:19].replace("T", " ")}
                                  for f in files], use_container_width=True, hide_index=True)
                    scelto_f = st.selectbox("Apri un registro", [f["chiave"] for f in files],
                                            format_func=lambda k: k.split("/", 1)[1])
                    if scelto_f:
                        testo = eeg.scarica(scelto_f)
                        info = eeg.riassunto(testo)
                        st.write(f"**{info['brano']}** · inizio {info['inizio']} · uscita {info['uscita']} · "
                                 f"{info['eventi']} eventi")
                        st.caption(info["conteggi"].replace(",", " · "))
                        if info["tonalita_stimata"]:
                            st.write(f"Tonalità stimata **{info['tonalita_stimata']}** (chiarezza {info['chiarezza_tonale']}, "
                                     f"poi {info['seconda_tonalita']}) · suono {info['carattere']} "
                                     f"({info['centroide_medio_hz']} Hz) · acuti {info['quota_acuti_pct']}% · "
                                     f"dinamica {info['dinamica_db']} dB · {info['secondi_analizzati']} s analizzati")
                            st.caption("Note nel brano (%): " + info["cromagramma"].replace(",", " · "))
                        st.download_button("Scarica il CSV", testo.encode("utf-8"), file_name=scelto_f.split("/")[-1],
                                           mime="text/csv")

    with t_esp:
        dati = db.esporta_anonimo(conn, sid)
        st.write(f"{len(dati)} righe, senza nomi né contatti.")
        st.download_button("Scarica i dati anonimi (CSV)", _csv(dati), file_name=f"studio_{sid}_anonimo.csv", mime="text/csv",
                           disabled=not dati)

    with t_priv:
        with st.expander("Cancella questo studio"):
            st.caption("Per uno studio di prova o creato per errore: si può cancellare se non ha iscritti attivi "
                       "(nessuno, oppure tutti ritirati dalla scheda Partecipanti). Scrivi il numero dello studio per confermare.")
            conferma = st.text_input(f"Numero dello studio da cancellare ({sid})", key=f"canc_{sid}")
            if st.button("Cancella lo studio", type="primary", disabled=conferma.strip() != str(sid), key=f"btn_canc_{sid}"):
                try:
                    db.elimina_studio(conn, sid, operatore)
                    st.success("Studio cancellato."); st.rerun()
                except ValueError as e:
                    st.error(str(e))
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

# ---------------- Pagina pubblica: ricezione dei dati dall'app ----------------

def render_ricezione_dati(get_conn, d: str):
    """Aperta dal pulsante «Invia i dati allo studio» di Pegasis: salva i dati e conferma."""
    conn = get_conn()
    db.crea_tabelle(conn)
    st.title("Pegasis · invio dei dati")
    if not d:
        st.error("Link incompleto: riprova dal pulsante dell'app.")
        return
    try:
        codice, nuovi, titolo = db.importa_automatico(conn, d)
    except Exception as e:
        st.error(f"Non è stato possibile salvare i dati: {e}")
        st.caption("Puoi riprovare più tardi, oppure usare «Non funziona? Invia per email» nell'app.")
        return
    st.success(f"Dati ricevuti, grazie! Codice {codice} · {titolo}")
    st.write("Nuovi dati salvati: %d. Se li avevi già inviati, quelli uguali non vengono duplicati." % nuovi)
    st.caption("Puoi chiudere questa pagina e tornare a Pegasis.")
