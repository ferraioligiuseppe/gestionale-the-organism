# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  TERAPIA — Percorsi terapeutici PNEV (contenitore)                   ║
║                                                                      ║
║  Un contenitore unico per i percorsi terapeutici dello studio:       ║
║  Vision Therapy, MAPS, Stanza del sale, Osteopatia, Terapia          ║
║  miofunzionale, Sports Vision. Per ogni percorso:                    ║
║    • 📅 Diario sedute (con parte economica → confluisce in incassi)  ║
║    • 🎯 Obiettivi & monitoraggio (esiti → Apprendimento PNEV)        ║
║    • 📄 Relazione AI (carta intestata PNEV)                          ║
║                                                                      ║
║  Tutto entra nel Quadro storico e nell'Assistente PNEV.              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import datetime
import streamlit as st

TERAPIE = ["Vision Therapy", "MAPS", "Stanza del sale", "Osteopatia",
           "Terapia miofunzionale", "Sports Vision"]
RISPOSTA = ["—", "🟢 Buona", "🟡 Parziale", "🔴 Scarsa"]
STATO_OB = ["🟦 In corso", "🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"]
METODI = ["—", "Contanti", "POS / Carta", "Bonifico", "Assegno", "Altro"]


# ── Tabelle ───────────────────────────────────────────────────────────

def _assicura_tabelle(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS terapia_sedute(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT, terapia TEXT,
            data_seduta DATE, numero INT, professionista TEXT,
            obiettivo TEXT, attivita TEXT, risposta TEXT,
            costo REAL, sconto REAL, incassato REAL, metodo TEXT,
            note TEXT, creato TIMESTAMP DEFAULT NOW());""")
        cur.execute("""CREATE TABLE IF NOT EXISTS terapia_obiettivi(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT, terapia TEXT,
            descrizione TEXT, baseline INT, attuale INT, target INT,
            stato TEXT, data_inizio DATE, data_rivalut DATE,
            note TEXT, creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def render_terapia(conn=None, paz_id=None, paziente=None):
    st.header("🧘 Percorsi terapeutici")
    st.caption("Vision Therapy, MAPS, Stanza del sale, Osteopatia, Miofunzionale, "
               "Sports Vision. Diario, obiettivi e relazione — tutto in cartella.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    _assicura_tabelle(conn)

    terapia = st.selectbox("Percorso terapeutico", TERAPIE, key="ter_tipo")
    modo = st.radio("Sezione", ["📅 Diario sedute", "🎯 Obiettivi & monitoraggio",
                                "📄 Relazione PDF"],
                    horizontal=True, key="ter_modo")

    if modo == "📅 Diario sedute":
        _render_diario(conn, paz_id, terapia)
    elif modo == "🎯 Obiettivi & monitoraggio":
        _render_obiettivi(conn, paz_id, terapia)
    else:
        _render_relazione(conn, paz_id, paziente, terapia)


# ── Diario sedute ─────────────────────────────────────────────────────

def _render_diario(conn, paz_id, terapia):
    st.caption(f"Sedute di **{terapia}**. La parte economica confluisce negli incassi.")

    _blocco_programma_settimana(conn, paz_id)

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM terapia_sedute WHERE paziente_id=%s AND terapia=%s",
                    (paz_id, terapia))
        n_fatte = cur.fetchone()[0] or 0
    except Exception:
        n_fatte = 0
        try:
            conn.rollback()
        except Exception:
            pass

    with st.expander("➕ Nuova seduta", expanded=True):
        with st.form("ter_seduta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                data_s = st.date_input("Data", value=datetime.date.today(), key="ter_sd_data")
            with c2:
                numero = st.number_input("N° seduta", min_value=1, step=1,
                                         value=int(n_fatte) + 1, key="ter_sd_num")
            with c3:
                prof = st.text_input("Professionista", key="ter_sd_prof")
            obiettivo = st.text_input("Obiettivo della seduta", key="ter_sd_ob")
            attivita = st.text_area("Attività svolte", height=80, key="ter_sd_att")
            risposta = st.selectbox("Risposta del paziente", RISPOSTA, key="ter_sd_risp")

            st.markdown("**💶 Incasso**")
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                costo = st.number_input("Listino €", min_value=0.0, step=5.0, key="ter_sd_costo")
            with e2:
                sconto = st.number_input("Sconto €", min_value=0.0, step=5.0, key="ter_sd_sconto")
            with e3:
                incassato = st.number_input("Incassato €", min_value=0.0, step=5.0, key="ter_sd_inc")
            with e4:
                metodo = st.selectbox("Metodo", METODI, key="ter_sd_met")
            note = st.text_area("Note", height=70, key="ter_sd_note")

            if st.form_submit_button("💾 Salva seduta", type="primary"):
                ok = _salva_seduta(conn, paz_id, terapia, data_s, numero, prof,
                                   obiettivo, attivita, risposta, costo, sconto,
                                   incassato, metodo, note)
                if ok:
                    st.success(f"Seduta n° {numero} di {terapia} salvata.")
                    st.rerun()
                else:
                    st.error("Salvataggio non riuscito.")

    st.markdown(f"#### Sedute di {terapia} ({n_fatte})")
    _elenco_sedute(conn, paz_id, terapia)


def _blocco_programma_settimana(conn, paz_id):
    """Mostra i protocolli assegnati al paziente e la settimana in corso, e
    permette di SCEGLIERE le procedure di questa settimana da assegnare a casa
    (pronte da inviare su pnev.it)."""
    import json as _json
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS programma_casa(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            protocollo TEXT, settimana INT, procedure JSONB,
            data_assegnazione DATE DEFAULT CURRENT_DATE,
            inviato BOOLEAN DEFAULT FALSE, creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
        cur.execute("""SELECT nome, settimana_corrente, struttura FROM protocolli_assegnati
            WHERE paziente_id=%s AND stato='In corso' ORDER BY creato DESC""", (paz_id,))
        protos = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        protos = []

    if not protos:
        st.info("Nessun protocollo assegnato a questo paziente. Vai in **🧩 Programma "
                "PNEV → 📋 Protocolli** per assegnarne uno (es. Apprendimento 10 settimane).")
        return

    with st.expander("📋 Programma di questa settimana (da assegnare a casa)", expanded=True):
        for _i, (nome, sett_cur, strut) in enumerate(protos):
            settimane = strut if isinstance(strut, list) else (_json.loads(strut) if strut else [])
            cur_s = next((s for s in settimane if s.get("sett") == (sett_cur or 1)), None)
            st.markdown(f"**{nome}** — Settimana {sett_cur or 1}"
                        + (f" · {cur_s.get('fase','')}" if cur_s else ""))
            proc_sett = cur_s.get("procedure", []) if cur_s else []
            if not proc_sett:
                st.caption("Nessuna procedura per questa settimana.")
                continue
            scelte = st.multiselect(
                "Procedure da assegnare a casa questa settimana",
                proc_sett, default=proc_sett, key=f"casa_sel_{_i}_{nome}_{sett_cur}")
            if st.button(f"📲 Assegna a casa (pronto per pnev.it) — {nome}",
                         key=f"casa_btn_{_i}_{nome}_{sett_cur}", type="primary"):
                if _salva_programma_casa(conn, paz_id, nome, sett_cur or 1, scelte):
                    st.success("Programma della settimana assegnato. Sarà disponibile "
                               "su pnev.it quando attiviamo la pagina di casa.")
                else:
                    st.error("Salvataggio non riuscito.")


def _salva_programma_casa(conn, paz_id, protocollo, settimana, procedure) -> bool:
    import json as _json
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO programma_casa(paziente_id, protocollo, settimana, procedure)
            VALUES(%s,%s,%s,%s)""",
            (paz_id, protocollo, int(settimana),
             _json.dumps(procedure, ensure_ascii=False)))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _salva_seduta(conn, paz_id, terapia, data_s, numero, prof, ob, att, risp,
                  costo, sconto, incassato, metodo, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO terapia_sedute(paziente_id, terapia, data_seduta,
            numero, professionista, obiettivo, attivita, risposta,
            costo, sconto, incassato, metodo, note)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, terapia, data_s, int(numero), prof, ob, att, risp,
             float(costo or 0), float(sconto or 0), float(incassato or 0), metodo, note))
        conn.commit()
        # confluenza negli incassi: riga nella tabella Sedute (canonica)
        try:
            cur.execute("""INSERT INTO Sedute(paziente_id, Data_Seduta, Terapia,
                Professionista, Costo, Pagato, Note) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (paz_id, data_s.strftime("%Y-%m-%d"), terapia, prof or "",
                 float(costo or 0), int(round(incassato or 0)),
                 f"[{terapia}] {ob or ''}".strip()))
            conn.commit()
        except Exception:
            conn.rollback()  # se Sedute ha schema diverso, non blocco il salvataggio
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco_sedute(conn, paz_id, terapia):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, data_seduta, numero, professionista, obiettivo,
            attivita, risposta, costo, sconto, incassato, metodo, note
            FROM terapia_sedute WHERE paziente_id=%s AND terapia=%s
            ORDER BY data_seduta DESC, numero DESC""", (paz_id, terapia))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try:
            conn.rollback()
        except Exception:
            pass
    if not righe:
        st.caption("Nessuna seduta registrata per questo percorso.")
        return
    for (rid, ds, num, prof, ob, att, risp, costo, sconto, inc, met, note) in righe:
        ds_str = ds.strftime("%d/%m/%Y") if ds else ""
        cap = f"Seduta n° {num} — {ds_str}"
        if risp and risp != "—":
            cap += f"  ·  {risp}"
        if inc:
            cap += f"  ·  💶 {inc:.0f}€"
        with st.expander(cap):
            e1, e2, e3 = st.columns(3)
            with e1:
                n_data = st.date_input("Data", value=ds or datetime.date.today(),
                                       key=f"ter_ed_data_{rid}")
            with e2:
                n_num = st.number_input("N° seduta", min_value=1, step=1,
                                        value=int(num or 1), key=f"ter_ed_num_{rid}")
            with e3:
                n_prof = st.text_input("Professionista", value=prof or "",
                                       key=f"ter_ed_prof_{rid}")
            n_ob = st.text_input("Obiettivo", value=ob or "", key=f"ter_ed_ob_{rid}")
            n_att = st.text_area("Attività svolte", value=att or "", height=80,
                                 key=f"ter_ed_att_{rid}")
            r1, r2 = st.columns(2)
            with r1:
                n_risp = st.selectbox("Risposta", RISPOSTA,
                                      index=RISPOSTA.index(risp) if risp in RISPOSTA else 0,
                                      key=f"ter_ed_risp_{rid}")
            with r2:
                n_met = st.selectbox("Metodo pagamento", METODI,
                                     index=METODI.index(met) if met in METODI else 0,
                                     key=f"ter_ed_met_{rid}")
            m1, m2, m3 = st.columns(3)
            with m1:
                n_costo = st.number_input("Listino €", min_value=0.0, step=5.0,
                                          value=float(costo or 0), key=f"ter_ed_costo_{rid}")
            with m2:
                n_sconto = st.number_input("Sconto €", min_value=0.0, step=5.0,
                                           value=float(sconto or 0), key=f"ter_ed_sc_{rid}")
            with m3:
                n_inc = st.number_input("Incassato €", min_value=0.0, step=5.0,
                                        value=float(inc or 0), key=f"ter_ed_inc_{rid}")
            n_note = st.text_area("Note", value=note or "", height=70,
                                  key=f"ter_ed_note_{rid}")
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("💾 Salva modifiche", key=f"ter_ed_save_{rid}", type="primary"):
                    if _aggiorna_seduta(conn, rid, n_data, n_num, n_prof, n_ob, n_att,
                                        n_risp, n_costo, n_sconto, n_inc, n_met, n_note):
                        st.success("Seduta aggiornata.")
                        st.rerun()
                    else:
                        st.error("Aggiornamento non riuscito.")
            with b2:
                if st.button("🗑 Elimina", key=f"ter_sd_del_{rid}"):
                    try:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM terapia_sedute WHERE id=%s", (rid,))
                        conn.commit()
                        st.rerun()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass


def _aggiorna_seduta(conn, rid, data_s, num, prof, ob, att, risp,
                     costo, sconto, inc, met, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""UPDATE terapia_sedute SET data_seduta=%s, numero=%s,
            professionista=%s, obiettivo=%s, attivita=%s, risposta=%s,
            costo=%s, sconto=%s, incassato=%s, metodo=%s, note=%s WHERE id=%s""",
            (data_s, int(num), prof, ob, att, risp, float(costo or 0),
             float(sconto or 0), float(inc or 0), met, note, rid))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ── Obiettivi & monitoraggio ──────────────────────────────────────────

def _render_obiettivi(conn, paz_id, terapia):
    st.caption(f"Obiettivi di **{terapia}** (scala 0–10). Alla chiusura l'esito "
               "confluisce nell'Apprendimento PNEV.")

    with st.expander("➕ Nuovo obiettivo", expanded=True):
        with st.form("ter_ob_new", clear_on_submit=True):
            descr = st.text_input("Obiettivo (osservabile)", key="ter_ob_descr")
            c1, c2, c3 = st.columns(3)
            with c1:
                baseline = st.slider("Livello iniziale", 0, 10, 2, key="ter_ob_base")
            with c2:
                target = st.slider("Target", 0, 10, 8, key="ter_ob_targ")
            with c3:
                data_riv = st.date_input("Rivalutazione",
                                         value=datetime.date.today() + datetime.timedelta(weeks=10),
                                         key="ter_ob_riv")
            if st.form_submit_button("💾 Crea obiettivo", type="primary"):
                if descr.strip():
                    if _salva_obiettivo(conn, paz_id, terapia, descr, baseline, target, data_riv):
                        st.success("Obiettivo creato.")
                        st.rerun()
                    else:
                        st.error("Salvataggio non riuscito.")
                else:
                    st.warning("Scrivi l'obiettivo.")

    st.markdown(f"#### Obiettivi di {terapia}")
    _elenco_obiettivi(conn, paz_id, terapia)


def _salva_obiettivo(conn, paz_id, terapia, descr, baseline, target, data_riv) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO terapia_obiettivi(paziente_id, terapia, descrizione,
            baseline, attuale, target, stato, data_inizio, data_rivalut)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, terapia, descr, int(baseline), int(baseline), int(target),
             "🟦 In corso", datetime.date.today(), data_riv))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco_obiettivi(conn, paz_id, terapia):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, descrizione, baseline, attuale, target, stato, data_rivalut
            FROM terapia_obiettivi WHERE paziente_id=%s AND terapia=%s
            ORDER BY creato DESC""", (paz_id, terapia))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try:
            conn.rollback()
        except Exception:
            pass
    if not righe:
        st.caption("Nessun obiettivo definito.")
        return
    for rid, descr, base, attuale, target, stato, driv in righe:
        st.markdown(f"**{descr}**")
        rng = max(1, (target or 10) - (base or 0))
        prog = min(1.0, max(0.0, ((attuale or 0) - (base or 0)) / rng))
        st.progress(prog, text=f"{stato}  ·  {attuale}/{target} (partenza {base})")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            nuovo = st.slider("Livello attuale", 0, 10, int(attuale or 0),
                              key=f"ter_ob_upd_{rid}")
        with c2:
            nuovo_stato = st.selectbox("Stato", STATO_OB,
                                       index=STATO_OB.index(stato) if stato in STATO_OB else 0,
                                       key=f"ter_ob_st_{rid}")
        with c3:
            st.write("")
            st.write("")
            if st.button("💾", key=f"ter_ob_save_{rid}", help="Aggiorna"):
                _aggiorna_obiettivo(conn, rid, nuovo, nuovo_stato, paz_id, descr, terapia)
                st.rerun()
        if driv:
            st.caption(f"Rivalutazione: {driv.strftime('%d/%m/%Y') if hasattr(driv,'strftime') else driv}")
        if st.button("🗑 Elimina", key=f"ter_ob_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM terapia_obiettivi WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)


def _aggiorna_obiettivo(conn, rid, attuale, stato, paz_id, descr, terapia):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE terapia_obiettivi SET attuale=%s, stato=%s WHERE id=%s",
                    (int(attuale), stato, rid))
        conn.commit()
        if stato in ("🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"):
            esito = {"🟢 Raggiunto": "🟢 Migliorato", "🟡 Parziale": "🟡 Stabile / fermo",
                     "⏸️ Sospeso": "⚪ Non valutabile"}.get(stato, "⚪ Non valutabile")
            try:
                cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
                    id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
                    data TIMESTAMP DEFAULT NOW(),
                    intervento TEXT, esito TEXT, note TEXT);""")
                cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                            "VALUES(%s,%s,%s,%s)",
                            (paz_id, f"{terapia}: {descr}", esito, "Da obiettivo terapeutico"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


# ── Relazione AI ──────────────────────────────────────────────────────

def _dati_terapia(conn, paz_id, terapia) -> str:
    parti = []
    try:
        cur = conn.cursor()
        cur.execute("""SELECT numero, data_seduta, obiettivo, risposta FROM terapia_sedute
            WHERE paziente_id=%s AND terapia=%s ORDER BY data_seduta DESC LIMIT 20""",
            (paz_id, terapia))
        sd = cur.fetchall()
        if sd:
            parti.append("SEDUTE:")
            for num, ds, ob, risp in sd:
                parti.append(f"- n°{num} {ds}: {ob or ''} ({risp or ''})")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        cur = conn.cursor()
        cur.execute("""SELECT descrizione, baseline, attuale, target, stato
            FROM terapia_obiettivi WHERE paziente_id=%s AND terapia=%s""", (paz_id, terapia))
        ob = cur.fetchall()
        if ob:
            parti.append("\nOBIETTIVI:")
            for descr, base, att, targ, stato in ob:
                parti.append(f"- {descr}: {stato} {att}/{targ} (da {base})")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    return "\n".join(parti).strip()


def _render_relazione(conn, paz_id, paziente, terapia):
    st.caption(f"Bozza di relazione del percorso **{terapia}**, con carta intestata "
               "e firma PNEV. L'AI scrive, tu correggi.")

    try:
        from .ai_estrazione import genera_testo, ai_disponibile
        from .diagnosi_assistita import INTESTAZIONE, FIRMA, _identificativi
    except Exception as e:
        st.error(f"Moduli AI/diagnosi non disponibili: {e}")
        return

    if not isinstance(paziente, dict) or not (paziente.get("Cognome") or paziente.get("Nome")):
        try:
            from .quadro_storico import carica_paziente
            p = carica_paziente(conn, paz_id)
            if p:
                paziente = p
        except Exception:
            pass

    dati = _dati_terapia(conn, paz_id, terapia)
    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()

    if not dati:
        st.info("Nessun dato ancora salvato per questo percorso: registra prima "
                "sedute o obiettivi.")

    key = f"ter_rel_{paz_id}_{terapia}"
    disabled = not (ai_disponibile() and dati)
    if st.button("🤖 Genera bozza relazione", type="primary", disabled=disabled):
        ident = _identificativi(paziente)
        schema = (
            f"Redigi una bozza di RELAZIONE del percorso terapeutico «{terapia}» "
            "secondo il Metodo PNEV, sui dati qui sotto. Sezioni:\n"
            "1. Dati identificativi\n2. Percorso e finalità\n"
            "3. Andamento delle sedute\n4. Obiettivi e avanzamento\n"
            "5. Considerazioni e indicazioni\n\n"
            "NON scrivere intestazione né firma. Attieniti ai dati; dove mancano, "
            "scrivi «da approfondire».\n\n"
            f"=== DATI IDENTIFICATIVI ===\n{ident}\n\n=== DATI {terapia.upper()} ===\n")
        sistema = ("Sei un terapeuta dello Studio The Organism (Metodo PNEV). "
                   "Italiano, registro clinico, terza persona. NON inventare dati.")
        with st.spinner("L'AI sta scrivendo la relazione…"):
            corpo = genera_testo(schema + dati, sistema=sistema)
        if corpo.startswith("⚠️"):
            st.session_state[key] = corpo
        else:
            st.session_state[key] = INTESTAZIONE + "\n\n" + corpo.strip() + "\n\n" + FIRMA
    if not ai_disponibile():
        st.caption("AI non configurata: la relazione automatica richiede la chiave nei Secrets.")

    testo = st.text_area("Relazione (modificabile)",
                         value=st.session_state.get(key, ""), height=440,
                         key=f"ter_rel_txt_{paz_id}")
    st.download_button("⬇️ Scarica (.txt)", data=testo or "",
                       file_name=f"relazione_{terapia}_{nome or paz_id}.txt".replace(" ", "_"),
                       mime="text/plain", key=f"ter_rel_dl_{paz_id}")
