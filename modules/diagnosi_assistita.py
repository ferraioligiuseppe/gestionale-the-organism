# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  DIAGNOSI ASSISTITA — schema + bozza AI sullo storico (Mattone 4)    ║
║                                                                      ║
║  Mette insieme tutto il percorso PNEV: raccoglie lo storico del      ║
║  paziente (documenti + estrazioni AI, test funzionali, valutazioni), ║
║  lo riassume, e con un clic l'AI propone una BOZZA di diagnosi        ║
║  strutturata che il clinico corregge, integra e firma. Niente        ║
║  sostituisce il giudizio clinico: l'AI scrive una traccia, non       ║
║  decide.                                                              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

try:
    from .quadro_storico import _query, _data_di, _fmt, carica_paziente
except Exception:
    def _query(conn, sql, params=()):
        try:
            cur = conn.cursor(); cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return None
    def _data_di(d):
        for k in ("data", "data_valutazione", "data_anamnesi", "creato"):
            if d.get(k):
                return d[k]
        return None
    def _fmt(dt):
        try:
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return str(dt) if dt else ""

_SISTEMA = (
    "Sei l'assistente clinico dello Studio The Organism e redigi relazioni "
    "secondo il Metodo PNEV (Psico-Neuro-Evolutivo Integrato) del Dott. Giuseppe "
    "Ferraioli (Neuropsicologo - Optometrista). Scrivi in italiano, registro "
    "clinico-professionale, in terza persona, con la cura e lo stile delle "
    "relazioni PNEV. NON inventare dati clinici: usa SOLO le informazioni "
    "fornite nello storico e nei dati identificativi. Dove un elemento manca, "
    "scrivi «da approfondire» o «in attesa di valutazione». La tua è una BOZZA "
    "che il professionista revisionerà e firmerà."
)

# Carta intestata (apertura fissa di ogni relazione PNEV)
INTESTAZIONE = (
    "Lo Studio The Organism adotta un modello di lavoro multidisciplinare e "
    "integrato (PNEV), avvalendosi della collaborazione di professionisti di "
    "diverse aree specialistiche (neuropsicologia, logopedia, terapia "
    "miofunzionale, psicomotricità, osteopatia, dietistica, oftalmologia, "
    "optometria, posturologia, fisioterapia, odontoiatria). Tale approccio "
    "consente una lettura complessa e unitaria del funzionamento sensorimotorio, "
    "neuropsicomotorio e neuroevolutivo della persona, bambino o adulto, al fine "
    "di individuare eventuali fragilità, disarmonie o rallentamenti nei processi "
    "di sviluppo e di integrazione funzionale.\n\n"
    "PNEV by The Organism è un Metodo Psico-Neuro-Evolutivo Integrato, "
    "multidisciplinare e multisensoriale, finalizzato alla valutazione e al "
    "trattamento delle fragilità del funzionamento neuroevolutivo, sensorimotorio "
    "e neuropsicomotorio nel bambino e nell'adulto ©."
)

# Firma clinica (chiusura fissa)
FIRMA = (
    "Cordiali saluti,\n\n"
    "Metodo PNEV – Processi NeuroEvolutivi\n"
    "Studio The Organism\n"
    "Dott. Giuseppe Ferraioli\n"
    "Neuropsicologo – Optometrista\n\n"
    "Luogo e data: __________________________     Firma e timbro"
)

_SCHEMA = (
    "Redigi una bozza di RELAZIONE CLINICA PNEV per il paziente indicato, "
    "articolata ESATTAMENTE nelle seguenti sezioni, ciascuna con il suo titolo:\n"
    "1. Dati identificativi (usa i dati forniti: nome, data di nascita, età)\n"
    "2. Motivo dell'osservazione\n"
    "3. Premessa clinica\n"
    "4. Inquadramento anamnestico\n"
    "5. Documentazione specialistica disponibile\n"
    "6. Interpretazione clinico-funzionale integrata\n"
    "7. Percorso terapeutico svolto in ottica PNEV\n"
    "8. Evoluzione clinica osservata\n"
    "9. Considerazioni cliniche conclusive\n"
    "10. Indicazioni operative\n\n"
    "NON scrivere intestazione né firma: vengono aggiunte a parte. "
    "Attieniti ai dati; dove mancano, indica «da approfondire».\n\n"
    "=== DATI IDENTIFICATIVI ===\n{IDENT}\n\n"
    "=== STORICO DEL PAZIENTE ===\n"
)


def _riassunto_storico(conn, paz_id) -> str:
    parti = []

    docs = _query(conn, "SELECT * FROM documenti_clinici WHERE paziente_id=%s", (paz_id,))
    if docs:
        parti.append("DOCUMENTI CLINICI:")
        for d in sorted(docs, key=lambda x: str(_data_di(x)), reverse=True):
            riga = f"- {d.get('tipo','Documento')} ({_fmt(_data_di(d))})"
            if d.get("estratto"):
                riga += "\n  Dati estratti: " + " ".join(str(d["estratto"]).split())
            parti.append(riga)

    g = _query(conn, "SELECT * FROM getman_risultati WHERE paziente_id=%s", (paz_id,))
    if g:
        parti.append("\nGETMAN (manipolazione visiva):")
        for r in sorted(g, key=lambda x: str(_data_di(x)), reverse=True):
            parti.append(f"- {_fmt(_data_di(r))}: punteggio {r.get('punteggio','?')}/12"
                         + (f", classe {r.get('classe')}" if r.get('classe') else ""))

    gr = _query(conn, "SELECT * FROM groffman_risultati WHERE paziente_id=%s", (paz_id,))
    if gr:
        parti.append("\nGROFFMAN (visual tracing):")
        for r in sorted(gr, key=lambda x: str(_data_di(x)), reverse=True):
            parti.append(f"- {_fmt(_data_di(r))}: punteggio {r.get('punteggio','?')}"
                         + (f", tavola {r.get('forma')}" if r.get('forma') else "")
                         + (f", osservazioni: {r.get('osservazioni')}" if r.get('osservazioni') else ""))

    vv = _query(conn, "SELECT * FROM valutazioni_visive WHERE paziente_id=%s", (paz_id,))
    if vv:
        parti.append("\nVALUTAZIONI VISUO-PERCETTIVE:")
        for r in sorted(vv, key=lambda x: str(_data_di(x)), reverse=True):
            parti.append(f"- valutazione del {_fmt(_data_di(r))}")

    an = _query(conn, "SELECT * FROM anamnesi WHERE paziente_id=%s", (paz_id,))
    if an:
        parti.append("\nVALUTAZIONI PNEV / ANAMNESI:")
        for r in sorted(an, key=lambda x: str(_data_di(x)), reverse=True):
            txt = (r.get("pnev_summary") or r.get("Motivo") or "").strip()
            parti.append(f"- {_fmt(_data_di(r))}: {txt}" if txt else f"- {_fmt(_data_di(r))}")

    es = _query(conn, "SELECT * FROM esiti_pnev WHERE paziente_id=%s", (paz_id,))
    if es:
        parti.append("\nESITI / FOLLOW-UP (cosa ha funzionato o no — IMPORTANTE):")
        for r in sorted(es, key=lambda x: str(_data_di(x)), reverse=True):
            riga = f"- {_fmt(_data_di(r))}: {r.get('intervento','')} → {r.get('esito','')}"
            if r.get("note"):
                riga += f" ({r['note']})"
            parti.append(riga)

    return "\n".join(parti).strip()


def render_diagnosi(conn=None, paz_id=None, paziente=None):
    st.header("📝 Diagnosi assistita")
    st.caption("Lo storico del paziente diventa una bozza di relazione diagnostica "
               "PNEV, da correggere e firmare. L'AI propone, tu decidi.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    if not isinstance(paziente, dict) or not (paziente.get("Cognome") or paziente.get("Nome")):
        try:
            p = carica_paziente(conn, paz_id)
            if p:
                paziente = p
        except Exception:
            pass

    _assicura_tabella(conn)

    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()

    storico = _riassunto_storico(conn, paz_id)

    with st.expander("📚 Storico raccolto (quello che legge l'AI)",
                     expanded=not bool(storico)):
        if storico:
            st.text(storico)
        else:
            st.info("Nessuno storico ancora presente. Puoi comunque scrivere la "
                    "diagnosi a mano qui sotto.")

    st.markdown("---")

    # ── Bozza AI ──────────────────────────────────────────────────────
    try:
        from .ai_estrazione import genera_testo, ai_disponibile
    except Exception:
        genera_testo = None
        ai_disponibile = lambda: False

    key_bozza = f"diag_bozza_{paz_id}"

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("#### Bozza di relazione diagnostica")
    with c2:
        disabled = not (ai_disponibile() and storico)
        if st.button("🤖 Genera con AI", type="primary", disabled=disabled,
                     use_container_width=True):
            with st.spinner("L'AI sta scrivendo la bozza…"):
                ident = _identificativi(paziente)
                corpo = genera_testo(_SCHEMA.replace("{IDENT}", ident) + storico,
                                     sistema=_SISTEMA)
                if corpo.startswith("⚠️"):
                    testo = corpo
                else:
                    testo = INTESTAZIONE + "\n\n" + corpo.strip() + "\n\n" + FIRMA
            st.session_state[key_bozza] = testo
    if not ai_disponibile():
        st.caption("AI non configurata: la diagnosi si scrive a mano. "
                   "Per la bozza automatica serve la chiave nei Secrets.")
    elif not storico:
        st.caption("Nessuno storico da analizzare: l'AI si attiva quando il paziente "
                   "ha documenti o test salvati.")

    testo = st.text_area("Relazione (modificabile)",
                         value=st.session_state.get(key_bozza, ""),
                         height=420, key=f"diag_txt_{paz_id}")

    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("💾 Salva in cartella", key=f"diag_save_{paz_id}"):
            if testo.strip() and _salva(conn, paz_id, testo):
                st.success("Diagnosi salvata in cartella.")
            else:
                st.warning("Scrivi prima qualcosa (o salvataggio non riuscito).")
    with cc2:
        st.download_button("⬇️ Scarica (.txt)", data=testo or "",
                           file_name=f"diagnosi_{nome or paz_id}.txt",
                           mime="text/plain", key=f"diag_dl_{paz_id}")

    st.markdown("---")
    st.markdown("#### Diagnosi precedenti")
    _elenco_precedenti(conn, paz_id)


def _identificativi(paziente) -> str:
    if not isinstance(paziente, dict):
        return "Non disponibili."
    nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    dn = paziente.get("Data_Nascita") or paziente.get("data_nascita") or ""
    eta = ""
    try:
        import datetime as _dt
        d = dn
        if isinstance(d, str) and d:
            for f in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    d = _dt.datetime.strptime(d[:10], f).date(); break
                except Exception:
                    continue
        if hasattr(d, "year"):
            o = _dt.date.today()
            anni = o.year - d.year - ((o.month, o.day) < (d.month, d.day))
            eta = f"{anni} anni"
            dn = d.strftime("%d/%m/%Y")
    except Exception:
        pass
    righe = [f"Paziente: {nome or 'non indicato'}"]
    if dn:
        righe.append(f"Data di nascita: {dn}")
    if eta:
        righe.append(f"Età: {eta}")
    return "  ".join(righe)


def _assicura_tabella(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS diagnosi_assistita(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data TIMESTAMP DEFAULT NOW(), contenuto TEXT);""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _salva(conn, paz_id, testo) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO diagnosi_assistita(paziente_id, contenuto) "
                    "VALUES(%s,%s)", (paz_id, testo))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco_precedenti(conn, paz_id):
    righe = _query(conn, "SELECT id, data, contenuto FROM diagnosi_assistita "
                   "WHERE paziente_id=%s ORDER BY data DESC", (paz_id,))
    if not righe:
        st.caption("Nessuna diagnosi salvata per ora.")
        return
    for r in righe:
        with st.expander(f"Diagnosi del {_fmt(r.get('data'))}"):
            st.markdown((r.get("contenuto") or "").replace("\n", "  \n"))
            if st.button("🗑 Elimina", key=f"diag_del_{r['id']}"):
                try:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM diagnosi_assistita WHERE id=%s", (r["id"],))
                    conn.commit()
                    st.rerun()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
